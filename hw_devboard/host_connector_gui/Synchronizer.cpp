#include "Synchronizer.h"

#include "VideoChip.h"

#include <QtGlobal>

Synchronizer::Synchronizer(QObject *parent) : QObject(parent) {
}

void Synchronizer::reset() {
  m_prevSample = 0xff;
  m_currentRow.clear();
  m_prevVSYNC = true;
  m_screenRows.clear();
  m_isFirstFrame = true;
}

void Synchronizer::pushSamples(QByteArrayView samples,
                               VideoChipChannelMapping channels) {
  // Reset state if the channel mapping has changed.
  if (m_channels != channels) {
    m_channels = channels;
    reset();
  }

  // Only attempt to process the signal if HVS is actually available.
  const char hvs_mask = m_channels.hvs_mask;
  if (!hvs_mask) {
    qCritical("The channel mapping does not have HVS, skipping samples");
    return;
  }

  // Process new samples.
  for (char sample : samples) {
    // Is this sample at the beginning of a HSYNC (i.e. on a new row)? If so,
    // flush the previous row before processing it.
    if ((m_prevSample & hvs_mask) && !(sample & hvs_mask)) {
      handleRow();
    }

    m_currentRow.append(sample);
    m_prevSample = sample;

    // Reject obviously wrong runs with too many consecutive samples without
    // HSYNC in between.
    if (Q_UNLIKELY(m_currentRow.size() > 4096)) {
      qCritical("Failed to horizontally sync, dropping buffers");
      reset();
    }
  }
}

void Synchronizer::handleRow() {
  if (m_currentRow.isEmpty()) {
    return;
  }

  // Was this row carrying a VSYNC? If so, it means we already have an entire
  // screen in our buffer. Let's flush it first.
  bool VSYNC =
      (m_currentRow[m_currentRow.size() / 2] & m_channels.hvs_mask) != 0;
  // qInfo("LINE: %llu samples (VSYNC=%d)", m_currentRow.size(), VSYNC);

  if (m_prevVSYNC && !VSYNC) { // VSYNC started
    handleScreen();
  }

  m_prevVSYNC = VSYNC;
  m_screenRows.append(m_currentRow);
  m_currentRow.clear();

  // Reject obviously wrong runs with too many consecutive rows without
  // VSYNC in between.
  if (Q_UNLIKELY(m_screenRows.size() > 1000)) {
    qCritical("Failed to vertically sync, dropping buffers");
    reset();
  }
}

void Synchronizer::handleScreen() {
  if (m_screenRows.isEmpty()) {
    return;
  }

  int width = 0, height = m_screenRows.size();
  for (const QByteArray &row : m_screenRows) {
    width = std::max<int>(width, row.size());
  }

  // qInfo("Received image %dx%d", width, height);

  QImage image(width, height, QImage::Format_Indexed8);
  image.fill(-1);
  for (int y = 0; y < height; ++y) {
    memcpy(image.scanLine(y), m_screenRows[y], m_screenRows[y].size());
  }
  m_screenRows.clear();

  if (m_isFirstFrame) {
    m_isFirstFrame = false;
  } else {
    emit imageReceived(image);
  }
}
