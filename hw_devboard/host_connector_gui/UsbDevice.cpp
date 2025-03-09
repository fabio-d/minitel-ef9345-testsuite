#include "UsbDevice.h"

#include <QEventLoop>
#include <QTimer>

// This must match the interface number.
static constexpr uint8_t INTERFACE_NUM = 0;

// This must match the device's interrupt endpoint number.
static constexpr uint8_t INT_ENDPOINT = 0x81;

// This must match the INT_ENDPOINT's wMaxPacketSize (i.e. 6 bytes).
static constexpr size_t INT_PACKET_SIZE = 6;

// This must match the device's isochronous endpoint number.
static constexpr uint8_t ISO_ENDPOINT = 0x82;

// This must match the ISO_ENDPOINT's wMaxPacketSize (i.e. up to two 1024-byte
// packets per microframe).
static constexpr size_t ISO_PACKET_SIZE = 2 * 1024;

static constexpr size_t ISO_TRANSFERS = 500;
static constexpr size_t ISO_PACKETS = 16;

UsbDevice::UsbDevice(UsbContext::DeviceHandle devHandle, QObject *parent)
    : QObject(parent), m_devHandle(std::move(devHandle)), m_error(std::nullopt),
      m_devIsClosing(false) {
  qInfo("UsbDevice CTOR");

  // Tell the OS that we want exclusive control over the connected device.
  int rc = libusb_claim_interface(m_devHandle, INTERFACE_NUM);
  if (rc != LIBUSB_SUCCESS) {
    qWarning("libusb_claim_interface failed: %s", libusb_error_name(rc));
    emitError(Error::DeviceInUseError);
    return;
  }

  // Blockingly get the status bytes from the firmware, which tells what chip
  // has been autodetected (if any) and what channels.
  constexpr uint8_t requestType = (uint8_t)LIBUSB_ENDPOINT_IN |
                                  (uint8_t)LIBUSB_REQUEST_TYPE_VENDOR |
                                  (uint8_t)LIBUSB_RECIPIENT_INTERFACE;
  uint8_t fw_status[7];
  rc = libusb_control_transfer(m_devHandle, requestType, 0x11, 0, INTERFACE_NUM,
                               fw_status, sizeof(fw_status), 0);
  if (rc != sizeof(fw_status)) {
    qWarning("libusb_control_transfer failed: %s", libusb_error_name(rc));
    emitError(Error::IoError);
    return;
  }

  // Select the alternate interface config that can actually transfer data.
  rc = libusb_set_interface_alt_setting(m_devHandle, 0, 1);
  if (rc != LIBUSB_SUCCESS) {
    qWarning("libusb_set_interface_alt_setting failed: %s",
             libusb_error_name(rc));
    emitError(Error::IoError);
    return;
  }

  switch (fw_status[6]) {
  case 1:
    qInfo("Detected EF9345");
    m_videoChipType = EF9345;
    break;
  case 2:
    qInfo("Detected TS9347");
    m_videoChipType = TS9347;
    break;
  default: // no video chip detected
    qCritical("Got unexpected status byte from firmware: %d", fw_status[0]);
    emitError(Error::NoVideoChipDetected);
    return;
  }

  loadStatusBytes(fw_status);

  // Allocate and prefill the isochronous transfers.
  for (size_t i = 0; i < ISO_TRANSFERS; ++i) {
    libusb_transfer *transfer = libusb_alloc_transfer(ISO_PACKETS);
    if (transfer == nullptr) {
      qFatal("libusb_alloc_transfer failed");
    }

    libusb_fill_iso_transfer(transfer, m_devHandle, ISO_ENDPOINT,
                             new uint8_t[ISO_PACKETS * ISO_PACKET_SIZE],
                             ISO_PACKETS *ISO_PACKET_SIZE, ISO_PACKETS,
                             transferCallback, this, 0 /* no timeout */);
    libusb_set_iso_packet_lengths(transfer, ISO_PACKET_SIZE);

    m_idleTransfers.insert(transfer);
  }

  // Allocate and prefill the interrupt transfers.
  libusb_transfer *transfer = libusb_alloc_transfer(0);
  if (transfer == nullptr) {
    qFatal("libusb_alloc_transfer failed");
  }
  libusb_fill_interrupt_transfer(transfer, m_devHandle, INT_ENDPOINT,
                                 new uint8_t[INT_PACKET_SIZE], INT_PACKET_SIZE,
                                 transferCallback, this, 0 /* no timeout */);
  m_idleTransfers.insert(transfer);

  // Submit all the transfers, immediately stopping on failure.
  while (!m_devIsClosing) {
    auto it = m_idleTransfers.begin();
    if (it == m_idleTransfers.end()) {
      break;
    }
    submitTransfer(*it);
  }
  if (m_devIsClosing) {
    // We failed to submit all the transfers.
    stopAndFreeAllTransfers();
    return;
  }
}

UsbDevice::~UsbDevice() {
  qInfo("UsbDevice DTOR");
  stopAndFreeAllTransfers();
}

std::optional<UsbDevice::Error> UsbDevice::error() const {
  return m_error;
}

std::optional<VideoChipType> UsbDevice::videoChipType() const {
  if (m_devIsClosing) {
    return std::nullopt;
  }
  return m_videoChipType;
}

std::optional<VideoChipChannelMapping> UsbDevice::videoChipChannels() const {
  if (m_devIsClosing) {
    return std::nullopt;
  }
  return m_videoChipChannelMapping;
}

std::optional<VideoChipMode> UsbDevice::videoChipMode() const {
  if (m_devIsClosing) {
    return std::nullopt;
  }
  return m_videoChipMode;
}

std::optional<uint8_t> UsbDevice::busRead(VideoChipRegister regnum) {
  if (m_devIsClosing) {
    return std::nullopt;
  }

  constexpr uint8_t requestType = (uint8_t)LIBUSB_ENDPOINT_IN |
                                  (uint8_t)LIBUSB_REQUEST_TYPE_VENDOR |
                                  (uint8_t)LIBUSB_RECIPIENT_INTERFACE;
  uint8_t data;
  int rc = libusb_control_transfer(m_devHandle, requestType, 0x10,
                                   (uint8_t)regnum, INTERFACE_NUM, &data, 1, 0);
  if (rc != 1) {
    markDeviceForClosing();
    qWarning("libusb_control_transfer failed: %s", libusb_error_name(rc));
  }
  return data;
}

bool UsbDevice::busWrite(VideoChipRegister regnum, uint8_t data) {
  if (m_devIsClosing) {
    return false;
  }

  constexpr uint8_t requestType = (uint8_t)LIBUSB_ENDPOINT_OUT |
                                  (uint8_t)LIBUSB_REQUEST_TYPE_VENDOR |
                                  (uint8_t)LIBUSB_RECIPIENT_INTERFACE;
  int rc = libusb_control_transfer(m_devHandle, requestType, 0x10,
                                   ((uint16_t)data << 8) | (uint8_t)regnum,
                                   INTERFACE_NUM, nullptr, 0, 0);
  if (rc != LIBUSB_SUCCESS) {
    markDeviceForClosing();
    qWarning("libusb_control_transfer failed: %s", libusb_error_name(rc));
    return false;
  }
  return true;
}

void UsbDevice::stopAndFreeAllTransfers() {
  markDeviceForClosing();

  // Wait for all pending transfers to complete.
  QEventLoop eventLoop;
  while (!m_pendingTransfers.empty()) {
    eventLoop.processEvents(QEventLoop::WaitForMoreEvents);
  }

  // Free all the transfers.
  for (libusb_transfer *transfer : m_idleTransfers) {
    delete[] transfer->buffer;
    libusb_free_transfer(transfer);
  }
  m_idleTransfers.clear();
}

void UsbDevice::markDeviceForClosing() {
  if (m_devIsClosing) {
    return; // already being closed, nothing to do.
  }

  m_devIsClosing = true;

  // Explicitly cancel all transfers that are still pending, instead of waiting
  // for them to naturally complete (which may never happen, if the device is
  // stuck).
  for (libusb_transfer *transfer : m_pendingTransfers) {
    libusb_cancel_transfer(transfer);
  }
}

void UsbDevice::emitError(Error error) {
  if (m_devIsClosing) {
    return;
  }

  markDeviceForClosing();
  m_error = error;
  emit failed(error);
}

void UsbDevice::loadStatusBytes(const uint8_t status_bytes[6]) {
  qInfo("UsbDevice received status_bytes: %02x %02x %02x %02x %02x %02x",
        status_bytes[0], status_bytes[1], status_bytes[2], status_bytes[3],
        status_bytes[4], status_bytes[5]);

  m_videoChipChannelMapping.red_mask = status_bytes[0];
  m_videoChipChannelMapping.green_mask = status_bytes[1];
  m_videoChipChannelMapping.blue_mask = status_bytes[2];
  m_videoChipChannelMapping.insert_mask = status_bytes[3];
  m_videoChipChannelMapping.hvs_mask = status_bytes[4];
  m_videoChipMode =
      (status_bytes[5] & 0x01) ? VIDEO_MODE_40_COLUMNS : VIDEO_MODE_80_COLUMNS;
}

void UsbDevice::onLibUsbTransferDone(libusb_transfer *transfer) {
  m_pendingTransfers.remove(transfer);
  m_idleTransfers.insert(transfer);

  if (transfer->status == LIBUSB_TRANSFER_COMPLETED) {
    if (!m_devIsClosing) {
      switch (transfer->endpoint) {
      case INT_ENDPOINT:
        loadStatusBytes(transfer->buffer);
        break;
      case ISO_ENDPOINT:
        for (int i = 0; i < transfer->num_iso_packets; ++i) {
          if (transfer->iso_packet_desc[i].status ==
              LIBUSB_TRANSFER_COMPLETED) {
            QByteArrayView data(
                reinterpret_cast<const char *>(
                    libusb_get_iso_packet_buffer_simple(transfer, i)),
                transfer->iso_packet_desc[i].actual_length);
            emit newSamples(data);
          }
        }
        break;
      default:
        abort();
      }
    }
  } else {
    emitError(Error::IoError);
    return;
  }

  // Resubmit for a new transfer if the device is still operational.
  if (!m_devIsClosing) {
    submitTransfer(transfer);
  }
}

void UsbDevice::submitTransfer(libusb_transfer *transfer) {
  int rc = libusb_submit_transfer(transfer);
  if (rc == LIBUSB_SUCCESS) {
    m_idleTransfers.remove(transfer);
    m_pendingTransfers.insert(transfer);
  } else {
    qInfo("libusb_submit_transfer failed: %s", libusb_error_name(rc));
    emitError(Error::IoError);
  }
}

void UsbDevice::transferCallback(libusb_transfer *transfer) {
  UsbDevice *self = (UsbDevice *)transfer->user_data;
  QMetaObject::invokeMethod(self, &UsbDevice::onLibUsbTransferDone, transfer);
}

UsbDeviceShim::UsbDeviceShim(QObject *parent) : QObject(parent) {
}

void UsbDeviceShim::connectDevice(UsbContext::DeviceHandle devHandle) {
  if (m_connectedDevice != nullptr) {
    m_connectedDevice.reset();
    emit isConnectedChanged(false);
  }

  if (devHandle == nullptr) {
    return;
  }

  UsbDevice *dev = new UsbDevice(std::move(devHandle), this);
  if (std::optional<UsbDevice::Error> error = dev->error(); error.has_value()) {
    delete dev;
    emit failed(*error);
  } else {
    connect(dev, &UsbDevice::failed, this, &UsbDeviceShim::handleFailure);
    connect(dev, &UsbDevice::newSamples, this, &UsbDeviceShim::newSamples);

    m_connectedDevice.reset(dev);
    emit isConnectedChanged(true);
  }
}

bool UsbDeviceShim::isConnected() const {
  return m_connectedDevice != nullptr;
}

std::optional<VideoChipType> UsbDeviceShim::videoChipType() const {
  if (m_connectedDevice != nullptr) {
    return m_connectedDevice->videoChipType();
  } else {
    return std::nullopt;
  }
}

std::optional<VideoChipChannelMapping>
UsbDeviceShim::videoChipChannels() const {
  if (m_connectedDevice != nullptr) {
    return m_connectedDevice->videoChipChannels();
  } else {
    return std::nullopt;
  }
}

std::optional<VideoChipMode> UsbDeviceShim::videoChipMode() const {
  if (m_connectedDevice != nullptr) {
    return m_connectedDevice->videoChipMode();
  } else {
    return std::nullopt;
  }
}

std::optional<uint8_t> UsbDeviceShim::busRead(VideoChipRegister regnum) {
  if (m_connectedDevice != nullptr) {
    return m_connectedDevice->busRead(regnum);
  } else {
    return std::nullopt;
  }
}

bool UsbDeviceShim::busWrite(VideoChipRegister regnum, uint8_t data) {
  if (m_connectedDevice != nullptr) {
    return m_connectedDevice->busWrite(regnum, data);
  } else {
    return false;
  }
}

void UsbDeviceShim::handleFailure(UsbDevice::Error error) {
  m_connectedDevice.reset();
  emit isConnectedChanged(false);
  emit failed(error);
}
