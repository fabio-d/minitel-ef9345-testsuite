#include "UsbContext.h"

#include <QEventLoop>

static constexpr uint16_t USB_PID = 0x0083;
static constexpr uint16_t USB_VID = 0x04b4;

UsbContext::UsbContext(QObject *parent)
    : QObject(parent), m_openCount(0), m_eventHandlingThread(nullptr) {
  int rc = libusb_init_context(&m_ctx, nullptr, 0);
  if (rc != LIBUSB_SUCCESS) {
    qFatal("libusb_init_context failed: %s", libusb_error_name(rc));
  }
}

UsbContext::~UsbContext() {
  // There cannot be open devices at this point.
  assert(m_openCount == 0 && m_eventHandlingThread == nullptr);

  libusb_exit(m_ctx);
}

UsbContext::DeviceHandle::DeviceHandle(UsbContext *usbContext,
                                       libusb_device_handle *devHandle)
    : m_usbContext(usbContext), m_devHandle(devHandle) {
  assert((m_usbContext != nullptr) == (m_devHandle != nullptr));
}

UsbContext::DeviceHandle::~DeviceHandle() {
  if (m_devHandle != nullptr) {
    m_usbContext->close(m_devHandle);
  }
}

UsbContext::DeviceHandle::DeviceHandle(DeviceHandle &&other) {
  m_usbContext = other.m_usbContext;
  other.m_usbContext = nullptr;

  m_devHandle = other.m_devHandle;
  other.m_devHandle = nullptr;
}

UsbContext::DeviceHandle &
UsbContext::DeviceHandle::operator=(DeviceHandle &&other) {
  if (m_devHandle != nullptr) {
    m_usbContext->close(m_devHandle);
  }

  m_usbContext = other.m_usbContext;
  other.m_usbContext = nullptr;

  m_devHandle = other.m_devHandle;
  other.m_devHandle = nullptr;

  return *this;
}

int UsbContext::open(libusb_device *dev, libusb_device_handle **devHandle) {
  // This function is not thread-safe!
  assert(QThread::currentThread() == thread());

  int rc = libusb_open(dev, devHandle);

  // If we've just opened our first device, start the event handling thread.
  if (rc == LIBUSB_SUCCESS && m_openCount++ == 0) {
    m_eventHandlingThread = new EventHandlingThread(this);
    m_eventHandlingThread->setObjectName("USB event handler");
    m_eventHandlingThread->start();
  }

  return rc;
}

void UsbContext::close(libusb_device_handle *devHandle) {
  // This function is not thread-safe!
  assert(QThread::currentThread() == thread());

  // If we're closing the last device, stop the event handling thread.
  assert(m_openCount != 0);
  bool isLast = --m_openCount == 0;

  if (isLast) {
    m_eventHandlingThread->requestInterruption();
  }

  // This will unblock libusb_handle_events in the UsbEventHandlingThread.
  libusb_close(devHandle);

  if (isLast) {
    m_eventHandlingThread->wait();
    delete m_eventHandlingThread;
    m_eventHandlingThread = nullptr;
  }
}

UsbContext::EventHandlingThread::EventHandlingThread(UsbContext *parent)
    : m_parent(parent) {
}

void UsbContext::EventHandlingThread::run() {
  qInfo("UsbContext thread started");
  while (!isInterruptionRequested()) {
    libusb_handle_events(m_parent->m_ctx);
  }
  qInfo("UsbContext thread stopped");
}

UsbContext::DeviceHandle UsbContext::findOurDevice() {
  libusb_device **list, *chosen = nullptr;
  ssize_t rc = libusb_get_device_list(m_ctx, &list);
  if (rc >= 0) {
    // TODO: dialog to pick one
    for (ssize_t i = 0; i < rc; ++i) {
      libusb_device_descriptor descriptor;
      int rc = libusb_get_device_descriptor(list[i], &descriptor);
      if (rc < 0) {
        qWarning("libusb_get_device_descriptor failed: %s",
                 libusb_error_name(rc));
        continue;
      }

      if (descriptor.idVendor == USB_VID && descriptor.idProduct == USB_PID) {
        chosen = libusb_ref_device(list[i]);
        break;
      }
    }
  } else {
    qCritical("libusb_get_device_list failed: %s", libusb_error_name((int)rc));
  }
  libusb_free_device_list(list, true);

  DeviceHandle result;
  if (chosen) {
    libusb_device_handle *devHandle;
    int rc = open(chosen, &devHandle);
    if (rc == LIBUSB_SUCCESS) {
      result = DeviceHandle(this, devHandle);
    } else {
      qCritical("libusb_open failed: %s", libusb_error_name(rc));
    }

    libusb_unref_device(chosen);
  }

  return result;
}
