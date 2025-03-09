#ifndef SYNCHRONIZER_H
#define SYNCHRONIZER_H

#include "VideoChip.h"

#include <QImage>
#include <QObject>

class Synchronizer : public QObject {
  Q_OBJECT

public:
  explicit Synchronizer(QObject *parent = nullptr);

  void reset();
  void pushSamples(QByteArrayView samples, VideoChipChannelMapping channels);

signals:
  void imageReceived(QImage img);

private:
  void handleRow();
  void handleScreen();

  VideoChipChannelMapping m_channels;

  // HSYNC detection.
  uint8_t m_prevSample;
  QByteArray m_currentRow;

  // VSYNC alignment.
  bool m_prevVSYNC;
  QList<QByteArray> m_screenRows;

  // Skipping the first frame (which might be partial).
  bool m_isFirstFrame;
};

#endif
