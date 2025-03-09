#ifndef MAINWINDOW_H
#define MAINWINDOW_H

#include "ImageProcessor.h"
#include "Synchronizer.h"
#include "TcpServer.h"
#include "UsbDevice.h"

#include <QMainWindow>

class Ui_MainWindow;

class MainWindow : public QMainWindow {
  Q_OBJECT

public:
  explicit MainWindow(UsbContext *usbContext, QWidget *parent = nullptr);
  ~MainWindow() override;

private:
  void connectDevice();
  void isConnectedChanged();
  void showDeviceError(UsbDevice::Error error);
  void showDevicePropertiesModal();
  void tcpServerToggled();
  void applyZoom();
  void applyFullscreen();
  void processReceivedImage(QImage image);

  // Preset programs.
  bool waitNotBusy();
  void execPresetHelloWorld40();
  void execPresetHelloWorld80();
  void execPresetUniformColor();
  void execPresetColorBands();

  Ui_MainWindow *m_ui;
  UsbContext *m_usbContext;
  UsbDeviceShim *m_usbDevice;
  Synchronizer *m_synchonizer;
  ImageProcessor *m_imageProcessor;
  TcpServer *m_tcpServer;
  QString m_tcpServerInputText = "127.0.0.1:1234";
};

#endif
