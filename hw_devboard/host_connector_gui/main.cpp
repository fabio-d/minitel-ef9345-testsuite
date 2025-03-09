#include "MainWindow.h"
#include "UsbDevice.h"

#include <QApplication>

int main(int argc, char *argv[]) {
  QApplication app(argc, argv);

  UsbContext usbContext;
  MainWindow mw(&usbContext);
  mw.show();

  return app.exec();
}
