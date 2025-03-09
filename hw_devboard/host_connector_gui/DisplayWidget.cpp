#include "DisplayWidget.h"

#include "VideoChip.h"

#include <QPaintEvent>
#include <QPainter>

DisplayWidget::DisplayWidget(QWidget *parent)
    : QGraphicsView(parent), m_scalingEnabled(false) {
  m_scene = new QGraphicsScene(this);
  setScene(m_scene);

  m_textItem = m_scene->addText("");
  m_pixmapItem = m_scene->addPixmap(QPixmap());

  setBackgroundBrush(Qt::GlobalColor::darkGray);
}

DisplayWidget::~DisplayWidget() {
  setScene(nullptr);
  delete m_scene;
}

void DisplayWidget::setContentsText(QString text) {
  m_pixmapItem->setPixmap(QPixmap());
  m_textItem->setHtml("<div style=\""
                      "background-color: darkred;"
                      "padding: 2px;"
                      "color: yellow;"
                      "\">" +
                      text.toHtmlEscaped());
  updateZoom();
}

void DisplayWidget::setContentsImage(QImage img) {
  QSize oldSize = m_pixmapItem->pixmap().size();
  m_pixmapItem->setPixmap(QPixmap::fromImage(img));
  if (oldSize == img.size()) {
    return;
  }

  m_textItem->setPlainText(QString());
  updateZoom();
}

void DisplayWidget::setScalingEnabled(bool on) {
  if (m_scalingEnabled == on) {
    return;
  }

  m_scalingEnabled = on;
  updateZoom();
}

void DisplayWidget::resizeEvent(QResizeEvent *event) {
  (void)event;
  updateZoom();
}

void DisplayWidget::updateZoom() {
  QGraphicsItem *currentItem = m_pixmapItem->pixmap().isNull()
                                   ? static_cast<QGraphicsItem *>(m_textItem)
                                   : static_cast<QGraphicsItem *>(m_pixmapItem);
  setSceneRect(currentItem->boundingRect());

  if (m_scalingEnabled && currentItem == m_pixmapItem) {
    fitInView(sceneRect(), Qt::KeepAspectRatio);
  } else {
    setTransform(QTransform());
  }
}
