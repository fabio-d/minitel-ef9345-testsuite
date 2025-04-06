#include "ImageProcessor.h"

#include <QDebug>

static uint8_t rgb2grayscale(bool r, bool g, bool b) {
  int idx = (b ? 4 : 0) | (g ? 2 : 0) | (r ? 1 : 0);
  static const uint8_t table[8] = {
      0, 80, 160, 230, 40, 120, 200, 255,
  };
  return table[idx];
}

// In 40 columns mode, the pixel value is updated by the video chip every 1.5
// clock cycles. Given that we sample once per clock cycle, we end up sampling
// every other sample twice. This function removes the double samples.
static QImage removeDoubleColumns(QImage input, uint8_t dataMask) {
  // We don't know what is the "phase" of our sampling compared to the pixel
  // updates. Three cases are possible:
  // 1. ABBCDDEFF...
  // 2. AABCCDEEF...
  // 3. ABCCDEEFG...
  // Let's compute all the three resulting images and then select the one that
  // best matches.
  QSize outSize(input.width() * 2 / 3, input.height());
  QImage out1(outSize, input.format());
  QImage out2(outSize, input.format());
  QImage out3(outSize, input.format());

  size_t mismatches1 = 0, mismatches2 = 0, mismatches3 = 0;
  for (int y = 0; y < outSize.height(); ++y) {
    const uchar *inData = input.constScanLine(y);
    uchar *outData1 = out1.scanLine(y);
    uchar *outData2 = out2.scanLine(y);
    uchar *outData3 = out3.scanLine(y);

    int x1 = 0, x2 = 0, x3 = 0;
    for (int x = 0; x < outSize.width(); x++) {
      outData1[x] = inData[x1++];
      outData2[x] = inData[x2++];
      outData3[x] = inData[x3++];
      if ((x % 2) != 0) {
        mismatches1 += ((outData1[x] ^ inData[x1++]) & dataMask) ? 1 : 0;
      } else {
        mismatches2 += ((outData2[x] ^ inData[x2++]) & dataMask) ? 1 : 0;
        if (x != 0) {
          mismatches3 += ((outData3[x] ^ inData[x3++]) & dataMask) ? 1 : 0;
        }
      }
    }
  }

  // Select the one that minimized the number of mismatches (in fact, the
  // matching one usually has a mismatch count of exactly zero!).
  if (mismatches1 < mismatches2) {
    return mismatches1 < mismatches3 ? out1 : out3;
  } else {
    return mismatches2 < mismatches3 ? out2 : out3;
  }
}

static QImage applyPalette(QImage image, QList<QRgb> palette) {
  image.setColorTable(palette);
  return image;
}

ImageProcessor::ImageProcessor(QObject *parent) : QObject(parent) {
}

void ImageProcessor::setInputImage(QImage image,
                                   VideoChipChannelMapping channels,
                                   VideoChipMode mode) {
  const uint8_t dataMask = channels.red_mask | channels.green_mask |
                           channels.blue_mask | channels.insert_mask;
  m_inputImage = mode == VIDEO_MODE_40_COLUMNS
                     ? removeDoubleColumns(image, dataMask)
                     : image;

  QRect cropArea = m_inputImage.rect();
  // The input width is either 512 (40 col mode) or 768 (80 col mode).
  // This will leave 2 px of horizontal margin visible around the bulk.
  switch (m_inputImage.width()) {
  case 512:
    cropArea.setLeft(128 - 2);
    cropArea.setWidth(320 + 4);
    break;
  case 768:
    cropArea.setLeft(192 - 2);
    cropArea.setWidth(480 + 4);
    break;
  }

  // Depending on TGS0, the EF9345 can either emit 312 or 262 lines.
  // The TS9347 always emits 312 lines.
  // Let's trim the margins so that on 2 px of vertical margin is left.
  switch (m_inputImage.height()) {
  case 262:
    cropArea.setTop(35 - 2);
    cropArea.setHeight(210 + 4);
    break;
  case 312:
    cropArea.setTop(41 - 2);
    cropArea.setHeight(250 + 4);
    break;
  }

  m_croppedInputImage = m_inputImage.copy(cropArea);

  if (m_inputChannels != channels) {
    m_inputChannels = channels;
    updateColorTables();
  }
}
void ImageProcessor::updateColorTables() {
  m_rgbInsertColorTable.clear();
  m_rgbColorTable.clear();
  m_grayscaleColorTable.clear();
  m_insertColorTable.clear();

  for (int val = 0; val < 256; ++val) {
    bool red = (val & m_inputChannels.red_mask) != 0;
    bool green = (val & m_inputChannels.green_mask) != 0;
    bool blue = (val & m_inputChannels.blue_mask) != 0;
    bool insert = (val & m_inputChannels.insert_mask) != 0;

    QRgb color = qRgb(red ? 255 : 0, green ? 255 : 0, blue ? 255 : 0);
    QRgb colorNoInsert =
        qRgb(red ? 0xCC : 0x44, green ? 0xCC : 0x44, blue ? 0xCC : 0x44);
    m_rgbInsertColorTable.append(
        (!insert && m_inputChannels.insert_mask != 0) ? colorNoInsert : color);
    m_rgbColorTable.append(color);

    uint8_t gs = rgb2grayscale(red, green, blue);
    m_grayscaleColorTable.append(qRgb(gs, gs, gs));

    uint8_t ins = insert ? 255 : 0;
    m_insertColorTable.append(qRgb(ins, ins, ins));
  }
}

bool ImageProcessor::haveRed() const {
  return m_inputChannels.red_mask != 0;
}

bool ImageProcessor::haveGreen() const {
  return m_inputChannels.green_mask != 0;
}

bool ImageProcessor::haveBlue() const {
  return m_inputChannels.blue_mask != 0;
}

bool ImageProcessor::haveInsert() const {
  return m_inputChannels.insert_mask != 0;
}

QImage ImageProcessor::rgbInsertUncroppedImage() const {
  return applyPalette(m_inputImage, m_rgbInsertColorTable);
}

QImage ImageProcessor::rgbInsertCroppedImage() const {
  return applyPalette(m_croppedInputImage, m_rgbInsertColorTable);
}

QImage ImageProcessor::rgbUncroppedImage() const {
  return applyPalette(m_inputImage, m_rgbColorTable);
}

QImage ImageProcessor::rgbCroppedImage() const {
  return applyPalette(m_croppedInputImage, m_rgbColorTable);
}

QImage ImageProcessor::grayscaleUncroppedImage() const {
  return applyPalette(m_inputImage, m_grayscaleColorTable);
}

QImage ImageProcessor::grayscaleCroppedImage() const {
  return applyPalette(m_croppedInputImage, m_grayscaleColorTable);
}

QImage ImageProcessor::insertUncroppedImage() const {
  return applyPalette(m_inputImage, m_insertColorTable);
}

QImage ImageProcessor::insertCroppedImage() const {
  return applyPalette(m_croppedInputImage, m_insertColorTable);
}
