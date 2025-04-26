#ifndef IMAGEPROCESSOR_H
#define IMAGEPROCESSOR_H

#include "VideoChip.h"

#include <QImage>
#include <QObject>

class ImageProcessor : public QObject {
  Q_OBJECT

public:
  explicit ImageProcessor(QObject *parent = nullptr);

  void setInputImage(QImage image, VideoChipType videoChipType,
                     VideoChipChannelMapping channels, VideoChipMode mode);

  bool haveRed() const;
  bool haveGreen() const;
  bool haveBlue() const;
  bool haveInsert() const;

  QImage rgbInsertUncroppedImage() const;
  QImage rgbInsertCroppedImage() const;
  QImage rgbUncroppedImage() const;
  QImage rgbCroppedImage() const;
  QImage grayscaleUncroppedImage() const;
  QImage grayscaleCroppedImage() const;
  QImage insertUncroppedImage() const;
  QImage insertCroppedImage() const;

private:
  void updateColorTables();

  VideoChipChannelMapping m_inputChannels;
  QList<QRgb> m_rgbInsertColorTable;
  QList<QRgb> m_rgbColorTable;
  QList<QRgb> m_grayscaleColorTable;
  QList<QRgb> m_insertColorTable;
  QImage m_inputImage, m_croppedInputImage;
};

#endif
