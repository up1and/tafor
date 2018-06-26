from PyQt5.QtCore import QSize, Qt, QRect, QCoreApplication, QPoint, pyqtSignal
from PyQt5.QtGui import QPainter, QPolygon, QPixmap, QPen, QColor, QBrush
from PyQt5.QtWidgets import QWidget, QGridLayout, QLabel

from shapely.geometry import Polygon

from tafor import logger
from tafor.states import context
from tafor.utils.convert import listToPoint, clipPolygon


class RenderArea(QWidget):
    pointsChanged = pyqtSignal()
    stateChanged = pyqtSignal()

    def __init__(self, parent=None):
        super(RenderArea, self).__init__(parent)
        self.points = []
        self.imageSize = None
        self.done = False
        self.maxPoint = 7
        self.color = Qt.white
        self.shadowColor = QColor(0, 0, 0, 127)
        self.areaColor = QColor(240, 156, 0, 178)
        self.boundaryColor = Qt.red
        self.fir = context.fir

    def minimumSizeHint(self):
        return QSize(260, 260)

    def sizeHint(self):
        *_, w, h = self.fir.rect()
        return QSize(w, h)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        self.drawCloudImage(painter)
        self.drawBoundaries(painter)
        self.drawSigmets(painter)

        if len(self.points) == 1:
            self.drawOnePoint(painter)

        if self.done:
            self.drawArea(painter)
        else:
            self.drawOutline(painter)

    def mousePressEvent(self, event):
        if not self.fir.raw():
            return 

        if event.button() == Qt.LeftButton:
            pos = [event.x(), event.y()]
            if len(self.points) > 2:
                deviation = 12
                initPoint = self.points[0]
                dx = abs(pos[0] - initPoint[0])
                dy = abs(pos[1] - initPoint[1])

                if dx < deviation and dy < deviation:
                    # Clip the area with boundaries
                    self.points = clipPolygon(self.fir.boundaries(), self.points, self.maxPoint)
                    self.done = True if len(self.points) > 2 else False

                    self.stateChanged.emit()
                    self.pointsChanged.emit()

            if not self.done:
                if len(self.points) < self.maxPoint:
                    self.points.append(pos)
                    self.pointsChanged.emit()
        
        if event.button() == Qt.RightButton and self.points:
            if self.done:
                self.done = False
                self.stateChanged.emit()
            else:
                self.points.pop()
                self.pointsChanged.emit()

        self.update()

    def drawOnePoint(self, painter):
        pen = QPen(self.color, 2)
        shadowPen = QPen(self.shadowColor, 3)
        point = listToPoint(self.points)[0]

        painter.setPen(shadowPen)
        painter.drawPoint(point)
        painter.setPen(pen)
        painter.drawPoint(point)

    def drawOutline(self, painter):
        pen = QPen(self.color, 1, Qt.DashLine)
        shadowPen = QPen(self.shadowColor, 2)
        
        points = listToPoint(self.points)
        for i, point in enumerate(points):
            if i == 0:
                prev = point
                continue
            else:
                painter.setPen(shadowPen)
                painter.drawLine(prev, point)
                painter.setPen(pen)
                painter.drawLine(prev, point)
                prev = point

    def drawArea(self, painter):
        points = listToPoint(self.points)
        pol = QPolygon(points)
        brush = QBrush(self.areaColor)
        painter.setBrush(brush)
        painter.setPen(self.color)
        painter.drawPolygon(pol)

    def drawBoundaries(self, painter):
        points = listToPoint(self.fir.boundaries())
        pol = QPolygon(points)
        painter.setPen(self.boundaryColor)
        painter.drawPolygon(pol)

    def drawCloudImage(self, painter):
        if self.fir.raw():
            pixmap = QPixmap()
            pixmap.loadFromData(self.fir.raw())
            self.imageSize = pixmap.size()
            rect = QRect(*self.fir.rect())
            image = pixmap.copy(rect)
            painter.drawPixmap(0, 0, image)
        else:
            rect = QRect(0, 0, 260, 260)
            painter.setPen(Qt.DashLine)
            painter.drawRect(rect)
            painter.drawText(rect, Qt.AlignCenter, QCoreApplication.translate('Editor', 'No Satellite Image'))

    def drawSigmets(self, painter):
        if not self.fir.raw():
            return 

        pen = QPen(QColor(204, 204, 204), 1, Qt.DashLine)
        brush = QBrush(QColor(240, 156, 0, 100))

        sigmets = self.fir.sigmetsArea()
        for i, sig in enumerate(sigmets):
            center = Polygon(sig).centroid
            met = self.fir.sigmets()[i]
            points = listToPoint(sig)
            pol = QPolygon(points)
            painter.setBrush(brush)
            painter.setPen(pen)
            painter.drawPolygon(pol)
            painter.drawText(center.x-5, center.y+5, met.sequence)

    def showEvent(self, event):
        self.points = []
        self.done = False
        self.updateGeometry()


class AreaChooser(QWidget):

    def __init__(self):
        super(AreaChooser, self).__init__()

        self.info = QLabel()
        self.info.setAlignment(Qt.AlignTop)
        self.renderArea = RenderArea()

        layout = QGridLayout()
        layout.addWidget(self.renderArea, 0, 0)
        layout.addWidget(self.info, 0, 1)

        self.setLayout(layout)

        self.renderArea.pointsChanged.connect(self.calcPoints)
        self.renderArea.pointsChanged.connect(self.updatePointsInfo)

    def updatePointsInfo(self):
        if self.points:
            points = ['{}, {}'.format(p[1], p[0]) for p in self.points]
            self.info.setText('\n'.join(points))
        else:
            self.info.setText('')

    def text(self):
        if not self.renderArea.done or not self.points:
            return ''

        circles = self.points + [self.points[0]]
        points = ['{} {}'.format(p[1], p[0]) for p in circles]
        return 'WI ' + ' - '.join(points)

    def calcPoints(self):
        pixelPoints = self.renderArea.points
        fir = context.fir
        self.points = fir.pixelToDegree(pixelPoints)
        return self.points

    def showEvent(self, event):
        self.points = []
        self.info.setText('')
