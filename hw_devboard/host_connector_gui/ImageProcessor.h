#ifndef IMAGEPROCESSOR_H
#define IMAGEPROCESSOR_H

#include "VideoChip.h"

#include <QImage>
#include <QObject>

class ImageProcessor : public QObject {
  Q_OBJECT

public:
  explicit ImageProcessor(QObject *parent = nullptr);

  void setInputImage(QImage image, VideoChipChannelMapping channels,
                     VideoChipMode mode);

  QImage rgbUncroppedImage() const;
  QImage rgbCroppedImage() const;
  QImage grayscaleUncroppedImage() const;
  QImage grayscaleCroppedImage() const;
  QImage insertUncroppedImage() const;
  QImage insertCroppedImage() const;

private:
  void updateColorTables();

  VideoChipChannelMapping m_inputChannels;
  QList<QRgb> m_rgbColorTable, m_grayscaleColorTable, m_insertColorTable;
  QImage m_inputImage, m_croppedInputImage;
};

#endif
