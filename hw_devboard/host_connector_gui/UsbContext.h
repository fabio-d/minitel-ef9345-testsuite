#ifndef USBCONTEXT_H
#define USBCONTEXT_H

#include <QObject>
#include <QThread>

#include <libusb-1.0/libusb.h>

// Wraps the libusb_context and hands out smart device handles that
// transparently start/stop the event handling thread as needed. See
// https://libusb.sourceforge.io/api-1.0/group__libusb__asyncio.html#eventthread
class UsbContext : public QObject {
  Q_OBJECT

public:
  explicit UsbContext(QObject *parent = nullptr);
  ~UsbContext() override;

  // Smart libusb_device_handle pointer that closes the device and stops the
  // event handling thread when destroyed.
  class DeviceHandle {
    friend class UsbContext;

  public:
    constexpr DeviceHandle() : m_usbContext(nullptr), m_devHandle(nullptr) {
    }
    ~DeviceHandle();

    // Forbid copy.
    DeviceHandle(const DeviceHandle &other) = delete;
    DeviceHandle &operator=(const DeviceHandle &other) = delete;

    // Allow move.
    DeviceHandle(DeviceHandle &&other);
    DeviceHandle &operator=(DeviceHandle &&other);

    operator libusb_device_handle *() const {
      return m_devHandle;
    }

  private:
    DeviceHandle(UsbContext *usbContext, libusb_device_handle *devHandle);

    UsbContext *m_usbContext;
    libusb_device_handle *m_devHandle;
  };

  DeviceHandle findOurDevice();

private:
  class EventHandlingThread : public QThread {
  public:
    explicit EventHandlingThread(UsbContext *parent);

  protected:
    void run() override;

  private:
    UsbContext *m_parent;
  };

  // Call this instead libusb_open to correctly maintain the device count.
  int open(libusb_device *dev, libusb_device_handle **devHandle);

  // Call this instead libusb_close to correctly maintain the device count.
  void close(libusb_device_handle *devHandle);

  libusb_context *m_ctx;
  size_t m_openCount;
  EventHandlingThread *m_eventHandlingThread;
};

#endif
