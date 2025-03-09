#ifndef USBDEVICE_H
#define USBDEVICE_H

#include "UsbContext.h"
#include "VideoChip.h"

#include <QMap>
#include <QObject>
#include <QSet>

class UsbDevice : public QObject {
  Q_OBJECT

public:
  enum class Error {
    DeviceInUseError,
    IoError,

    // Emitted when the USB device is detected correctly, but the USB device
    // itself failed to detect any connected video chip (e.g. because of bad
    // connections or the socket is empty).
    NoVideoChipDetected,
  };

  explicit UsbDevice(UsbContext::DeviceHandle devHandle,
                     QObject *parent = nullptr);
  ~UsbDevice() override;

  // Set only if the device has failed.
  //
  // The constructor may set it, if the device fails to initialize.
  // If the error happens after the constructor has completed, the failed(Error)
  // signal will be emitted too.
  std::optional<Error> error() const;

  // What type of video chip it is connected to, how its channels are encoded
  // in the samples and its mode.
  std::optional<VideoChipType> videoChipType() const;
  std::optional<VideoChipChannelMapping> videoChipChannels() const;
  std::optional<VideoChipMode> videoChipMode() const;

  // Perform raw I/O to the video chip's registers.
  std::optional<uint8_t> busRead(VideoChipRegister regnum);
  bool busWrite(VideoChipRegister regnum, uint8_t data);

signals:
  void failed(Error error);

  // Emitted when new samples arrive from the USB device's logic analyzer
  // function.
  void newSamples(QByteArrayView samples);

private:
  void stopAndFreeAllTransfers();
  void markDeviceForClosing();
  void emitError(Error error);
  void loadStatusBytes(const uint8_t status_bytes[6]);
  void onLibUsbTransferDone(libusb_transfer *transfer);
  void submitTransfer(libusb_transfer *transfer);
  static void transferCallback(libusb_transfer *transfer);

  // The libusb device we're connected to.
  UsbContext::DeviceHandle m_devHandle;

  // If set, the error that made this device fail.
  //
  // Important: Set this through emitError(), which ensures that only the first
  // error is reported and that the failed(...) signal is generated!
  std::optional<Error> m_error;

  // Set either by the destructor or as a consequence of an error. Once set, no
  // new transfers will be submitted and all requests are dropped.
  bool m_devIsClosing;

  // Info about the video chip device and its channels.
  VideoChipType m_videoChipType;
  VideoChipChannelMapping m_videoChipChannelMapping;
  VideoChipMode m_videoChipMode;

  // At any point in time, each transfer will always belong to one of these two
  // sets.
  QSet<libusb_transfer *> m_idleTransfers, m_pendingTransfers;
};

// Shim class that redirects API calls to the real UsbDevice, if connected, or
// just returns failure otherwise.
//
// Unlike the underlying UsbDevice class, it does not get destroyed and
// recreated when a new device is connected.
class UsbDeviceShim : public QObject {
  Q_OBJECT

public:
  explicit UsbDeviceShim(QObject *parent = nullptr);

  void connectDevice(UsbContext::DeviceHandle devHandle);
  void disconnectDevice() {
    connectDevice(UsbContext::DeviceHandle());
  }

  bool isConnected() const;

  // Exposed methods from UsbDevice.
  std::optional<VideoChipType> videoChipType() const;
  std::optional<VideoChipChannelMapping> videoChipChannels() const;
  std::optional<VideoChipMode> videoChipMode() const;
  std::optional<uint8_t> busRead(VideoChipRegister regnum);
  bool busWrite(VideoChipRegister regnum, uint8_t data);

signals:
  void isConnectedChanged(bool newValue);
  void failed(UsbDevice::Error error);
  void newSamples(QByteArrayView samples);

private:
  void handleFailure(UsbDevice::Error error);

  std::unique_ptr<UsbDevice> m_connectedDevice;
};

#endif
