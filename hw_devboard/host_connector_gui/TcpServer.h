#ifndef TCPSERVER_H
#define TCPSERVER_H

#include "ImageProcessor.h"
#include "UsbDevice.h"

#include <QTcpServer>
#include <QTcpSocket>

class TcpServer : public QObject {
  Q_OBJECT

public:
  TcpServer(UsbDeviceShim *usbDev, ImageProcessor *imgProc,
            QObject *parent = nullptr);
  ~TcpServer() override;

  static bool parseAddressAndPort(const QString &text, QHostAddress *host,
                                  uint16_t *port);

  bool startListening(const QHostAddress &address, uint16_t port,
                      QString *errorText);
  void stopListening();

private:
  void onNewConnection();
  void onReadyRead(QTcpSocket *client);
  void onReadChannelFinished(QTcpSocket *client);

  UsbDeviceShim *m_usbDev;
  ImageProcessor *m_imgProc;

  QTcpServer *m_server;
  QSet<QTcpSocket *> m_clients;
};

#endif
