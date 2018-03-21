from PyQt5.QtCore import QSize, Qt, QRect, QCoreApplication, pyqtSignal
from PyQt5.QtGui import QPainter, QPolygon, QPixmap, QPen
from PyQt5.QtWidgets import QWidget, QGridLayout, QLabel

from tafor import logger
from tafor.states import context
from tafor.utils.convert import decimalToDegree


class RenderArea(QWidget):
    pointsChanged = pyqtSignal()
    stateChanged = pyqtSignal()

    def __init__(self, parent=None):
        super(RenderArea, self).__init__(parent)
        self.points = []
        self.imageSize = None
        self.done = False
        self.fir = context.fir.state()

    def minimumSizeHint(self):
        return QSize(200, 200)

    def sizeHint(self):
        w, h = self.fir['rect'][-2:]
        return QSize(w, h)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        self.drawCloudImage(painter)

        if len(self.points) == 1:
            self.drawOnePoint(painter)

        if self.done:
            self.drawArea(painter)
        else:
            self.drawOutline(painter)

    def mousePressEvent(self, event):
        if not self.fir['content']:
            return 

        if event.button() == Qt.LeftButton:
            pos = event.pos()
            if len(self.points) > 2:
                deviation = 12
                initPoint = self.points[0]
                dx = abs(pos.x() - initPoint.x())
                dy = abs(pos.y() - initPoint.y())

                if dx < deviation and dy < deviation:
                    self.done = True
                    self.stateChanged.emit()

            if len(self.points) > 7:
                return

            if not self.done:
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
        pen = QPen(Qt.white, 2)
        painter.setPen(pen)
        point = self.points[0]
        painter.drawPoint(point)

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
        if self.fir['content']:
            pixmap = QPixmap()
            pixmap.loadFromData(self.fir['content'])
            self.imageSize = pixmap.size()
            rect = QRect(*self.fir['rect'])
            image = pixmap.copy(rect)
            painter.drawPixmap(0, 0, image)
        else:
            rect = QRect(0, 0, 200, 200)
            painter.setPen(Qt.DashLine)
            painter.drawRect(rect)
            painter.drawText(rect, Qt.AlignCenter, QCoreApplication.translate('Editor', 'No Satellite Image'))

    def showEvent(self, event):
        self.points = []
        self.done = False


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
            points = ['{}, {}'.format(*p) for p in self.points]
            self.info.setText('\n'.join(points))
        else:
            self.info.setText('')

    def text(self):
        if not self.renderArea.done or not self.points:
            return ''

        circles = self.points + [self.points[0]]
        points = ['{} {}'.format(*p) for p in circles]
        return 'WI ' + ' - '.join(points)

    def calcPoints(self):
        pixelPoints = self.renderArea.points
        imageSize = self.renderArea.imageSize
        fir = context.fir.state()

        try:
            initLat = fir['coordinates'][0][0]
            initLong = fir['coordinates'][0][1]
            latRange = fir['coordinates'][0][0] - fir['coordinates'][1][0]
            longRange = fir['coordinates'][1][1] - fir['coordinates'][0][1]
            dlat = latRange / imageSize.height()
            dlong = longRange / imageSize.width()
            offsetX = fir['rect'][0]
            offsetY = fir['rect'][1]

            self.points = []
            for p in pixelPoints:
                longtitude = initLong + (p.x() + offsetX) * dlong
                latitude = initLat - (p.y() + offsetY) * dlat
                self.points.append([
                    decimalToDegree(latitude), 
                    decimalToDegree(longtitude, fmt='longitude'),
                ])

            return self.points
        except Exception as e:
            logger.debug(e)

    def showEvent(self, event):
        self.points = []
        self.info.setText('')



