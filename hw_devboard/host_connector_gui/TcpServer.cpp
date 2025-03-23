#include "TcpServer.h"

#include <QBuffer>
#include <QRegularExpression>

TcpServer::TcpServer(UsbDeviceShim *usbDev, ImageProcessor *imgProc,
                     QObject *parent)
    : QObject(parent), m_usbDev(usbDev), m_imgProc(imgProc), m_server(nullptr) {
}

TcpServer::~TcpServer() {
  stopListening();
}

bool TcpServer::parseAddressAndPort(const QString &text, QHostAddress *host,
                                    uint16_t *port) {
  int colon = text.lastIndexOf(':');
  if (colon == -1) {
    return false;
  }

  if (!host->setAddress(text.sliced(0, colon))) {
    return false;
  }

  bool portOk = false;
  *port = text.sliced(colon + 1).toUShort(&portOk);

  return portOk && port != 0;
}

bool TcpServer::startListening(const QHostAddress &address, uint16_t port,
                               QString *errorText) {

  m_server = new QTcpServer(this);
  if (!m_server->listen(address, port)) {
    *errorText = m_server->errorString();

    delete m_server;
    m_server = nullptr;

    return false;
  }

  connect(m_server, &QTcpServer::newConnection, this,
          &TcpServer::onNewConnection);
  return true;
}

void TcpServer::stopListening() {
  qDeleteAll(m_clients);
  m_clients.clear();

  delete m_server;
  m_server = nullptr;
}

void TcpServer::onNewConnection() {
  while (QTcpSocket *client = m_server->nextPendingConnection()) {
    m_clients.insert(client);

    client->setSocketOption(QAbstractSocket::LowDelayOption, 1);

    connect(client, &QTcpSocket::readyRead, this,
            [this, client]() { onReadyRead(client); });
    connect(client, &QTcpSocket::readChannelFinished, this,
            [this, client]() { onReadChannelFinished(client); });
  }
}

void TcpServer::onReadyRead(QTcpSocket *client) {
  static const QRegularExpression query_re("^(E?)R([0-7])\\?$");
  static const QRegularExpression set_re("^(E?)R([0-7])=([0-9A-F]{2})$");
  while (client->canReadLine()) {
    QString line = QString::fromLatin1(client->readLine()).trimmed();
    bool busError = false;

    if (line == "TYPE?") {
      std::optional<VideoChipType> videoChipType = m_usbDev->videoChipType();
      if (videoChipType == EF9345) {
        client->write("EF9345\n");
      } else if (videoChipType == TS9347) {
        client->write("TS9347\n");
      } else {
        busError = true;
      }
    } else if (line == "RGB?") {
      QImage result = m_imgProc->rgbCroppedImage();
      QByteArray data;
      QBuffer buffer(&data);
      result.save(&buffer, "PNG");
      client->write(data.toBase64());
      client->write("\n");
    } else if (QRegularExpressionMatch m = query_re.match(line); m.hasMatch()) {
      bool execBit = m.capturedLength(1) != 0;
      uint8_t regnum = m.capturedView(2).toInt();
      std::optional<uint8_t> result =
          m_usbDev->busRead(static_cast<VideoChipRegister>(
              (execBit ? REG_ER0 : REG_R0) | regnum));
      if (result.has_value()) {
        char buf[4];
        sprintf(buf, "%02X\n", *result);
        client->write(buf);
      } else {
        busError = true;
      }
    } else if (QRegularExpressionMatch m = set_re.match(line); m.hasMatch()) {
      bool execBit = m.capturedLength(1) != 0;
      uint8_t regnum = m.capturedView(2).toInt();
      uint8_t data = m.capturedView(3).toInt(nullptr, 16);
      if (!m_usbDev->busWrite(static_cast<VideoChipRegister>(
                                  (execBit ? REG_ER0 : REG_R0) | regnum),
                              data)) {
        busError = true;
      }
    } else {
      client->write("Invalid request, ignoring\n");
    }

    if (busError) {
      client->write("Device not connected, ignoring\n");
    }
  }
}

void TcpServer::onReadChannelFinished(QTcpSocket *client) {
  m_clients.remove(client);
  client->deleteLater();
}
