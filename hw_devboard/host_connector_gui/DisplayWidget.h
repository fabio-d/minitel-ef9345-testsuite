#ifndef DISPLAYWIDGET_H
#define DISPLAYWIDGET_H

#include <QGraphicsPixmapItem>
#include <QGraphicsScene>
#include <QGraphicsTextItem>
#include <QGraphicsView>

class DisplayWidget : public QGraphicsView {
  Q_OBJECT

public:
  explicit DisplayWidget(QWidget *parent = nullptr);
  ~DisplayWidget() override;

  void setContentsText(QString text);
  void setContentsImage(QImage img);

  void setScalingEnabled(bool on);

protected:
  void resizeEvent(QResizeEvent *event);

private:
  void updateZoom();

  QGraphicsScene *m_scene;
  QGraphicsTextItem *m_textItem;
  QGraphicsPixmapItem *m_pixmapItem;

  bool m_scalingEnabled;
};

#endif
