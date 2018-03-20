
from PyQt5.QtCore import QSize, Qt, QRect
from PyQt5.QtGui import QPainter, QPolygon, QPixmap, QPen
from PyQt5.QtWidgets import QWidget


class AreaChooser(QWidget):
    
    def __init__(self, parent=None):
        super(AreaChooser, self).__init__(parent)
        self.points = []
        self.done = False

    def minimumSizeHint(self):
        return QSize(200, 200)

    def sizeHint(self):
        return QSize(200, 200)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        self.drawCloudImage(painter)

        if self.done:
            self.drawArea(painter)
        else:
            self.drawOutline(painter)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            pos = event.pos()
            if len(self.points) > 2:
                deviation = 20
                initPoint = self.points[0]
                dx = abs(pos.x() - initPoint.x())
                dy = abs(pos.y() - initPoint.y())

                if dx < deviation and dy < deviation:
                    self.done = True

            if len(self.points) > 7:
                return

            if not self.done:
                self.points.append(pos)
        
        if event.button() == Qt.RightButton and self.points:
            if self.done:
                self.done = False
            else:
                self.points.pop()

        self.update()

    def drawOutline(self, painter):
        pen = QPen(Qt.white, 1, Qt.DashLine)
        painter.setPen(pen)
        
        for i, point in enumerate(self.points):
            if i == 0:
                prev = point
                continue
            else:
                painter.drawLine(prev, point)
                prev = point

    def drawArea(self, painter):
        pol = QPolygon(self.points)
        painter.setPen(Qt.white)
        painter.drawPolygon(pol)

    def drawCloudImage(self, painter):
        pixmap = QPixmap()
        pixmap.load('satillite.jpg')
        rect = QRect(475, 210, 200, 200)
        image = pixmap.copy(rect)
        painter.drawPixmap(0, 0, image)
