from PyQt5.QtCore import QSize, Qt, QRect, QCoreApplication, QPoint, pyqtSignal
from PyQt5.QtGui import QPainter, QPainterPath, QPolygon, QPixmap, QPen, QColor, QBrush, QFont
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel

from shapely.geometry import Polygon

from tafor import logger
from tafor.states import context
from tafor.utils.convert import listToPoint, pointToList
from tafor.utils.sigmet import encodeSigmetArea, simplifyLine, clipPolygon, simplifyPolygon


class Canvas(QWidget):
    pointsChanged = pyqtSignal()
    stateChanged = pyqtSignal()

    def __init__(self, parent=None):
        super(Canvas, self).__init__(parent)
        self.points = []
        self.rectangular = []
        self.imageSize = None
        self.done = False
        self.mode = 'polygon'
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
            self.drawRectangular(painter)

    def mousePressEvent(self, event):
        if not self.fir.raw():
            return 

        if self.mode in ['polygon', 'line']:
            self.polygonMousePressEvent(event)

        if self.mode == 'rectangular':
            self.rectangularMousePressEvent(event)

        self.update()

    def polygonMousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            pos = (event.x(), event.y())
            if len(self.points) > 2:
                deviation = 12
                initPoint = self.points[0]
                dx = abs(pos[0] - initPoint[0])
                dy = abs(pos[1] - initPoint[1])

                if dx < deviation and dy < deviation:
                    # Clip the area with boundaries
                    self.points = clipPolygon(self.fir.boundaries(), self.points)

                    if self.mode == 'polygon':
                        self.points = simplifyPolygon(self.points, maxPoint=self.maxPoint, extend=True)
                    
                    # make the points clockwise
                    self.points.reverse()
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

    def rectangularMousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if not self.rectangular:
                self.rectangular = [event.pos(), event.pos()]
        
        if event.button() == Qt.RightButton:
            self.clear()

    def mouseMoveEvent(self, event):
        if self.mode != 'rectangular' or self.done or len(self.rectangular) != 2:
            return

        self.rectangular[1] = event.pos()
        self.update()

    def mouseReleaseEvent(self, event):
        if self.mode != 'rectangular':
            return

        rect = QRect(*self.rectangular)
        points = [rect.topLeft(), rect.topRight(), rect.bottomRight(), rect.bottomLeft()]
        points = pointToList(points)
        self.points = clipPolygon(self.fir.boundaries(), points)

        if self.points:
            self.done = True
        else:
            self.done = False
        
        self.pointsChanged.emit()
        self.stateChanged.emit()

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

            updatedTime = self.fir.updatedTime()
            if updatedTime:
                rect = QRect(10, 0, image.size().width(), image.size().height() - 10)
                text = updatedTime.strftime('%H:%M')
                path = QPainterPath()
                font = QFont()
                font.setBold(True)
                path.addText(rect.bottomLeft(), font, text)
                pen = QPen(QColor(0, 0, 0, 120), 2)
                brush = QBrush(Qt.white)
                painter.strokePath(path, pen)
                painter.fillPath(path, brush)
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
            painter.drawText(center.x - 5, center.y + 5, met.sequence)

    def drawRectangular(self, painter):
        pen = QPen(QColor(0, 120, 215))
        brush = QBrush(QColor(0, 120, 215, 40))
        painter.setPen(pen)
        painter.setBrush(brush)
        rect = QRect(*self.rectangular)
        painter.drawRect(QRect(*self.rectangular))

    def clear(self):
        self.points = []
        self.rectangular = []
        self.done = False
        self.pointsChanged.emit()
        self.stateChanged.emit()
        self.update()

    def showEvent(self, event):
        self.updateGeometry()


class AreaBoard(QWidget):

    def __init__(self):
        super(AreaBoard, self).__init__()

        self.board = QLabel()
        self.board.setAlignment(Qt.AlignTop)
        self.board.setMaximumWidth(280)
        self.board.setWordWrap(True)
        self.canvas = Canvas()

        layout = QHBoxLayout()
        layout.addWidget(self.canvas)
        layout.addWidget(self.board)

        self.setLayout(layout)

        self.area = []
        self.message = ''

        self.canvas.pointsChanged.connect(self.updateArea)
        self.canvas.stateChanged.connect(self.updateArea)

    def updateArea(self):
        self.message = ''

        if self.canvas.mode == 'rectangular' and self.canvas.done:

            boundaries = context.fir._state['boundaries']
            points = context.fir.pixelToDecimal(self.canvas.points)
            self.area = encodeSigmetArea(boundaries, points, mode='rectangular')

            lines = []
            for identifier, *points in self.area:
                points = context.fir.decimalToDegree(points)
                latlng = simplifyLine(points)

                if latlng:
                    line = '{} OF {}'.format(identifier, latlng)
                    lines.append(line)

            self.message = ' AND '.join(lines)

        if self.canvas.mode == 'line':
            if self.canvas.done:
                boundaries = context.fir._state['boundaries']
                points = context.fir.pixelToDecimal(self.canvas.points)
                self.area = encodeSigmetArea(boundaries, points, mode='line')
                
                lines = []
                for identifier, *points in self.area:
                    points = context.fir.decimalToDegree(points)
                    coordinates = []
                    for lng, lat in points:
                        coordinates.append('{} {}'.format(lat, lng))

                    line = '{} OF LINE {}'.format(identifier, ' - '.join(coordinates))
                    lines.append(line)

                self.message = ' AND '.join(lines)
            else:
                points = context.fir.pixelToDegree(self.canvas.points)
                coordinates = ['{} {}'.format(p[1], p[0]) for p in points]
                self.message = '\n'.join(coordinates)


        if self.canvas.mode == 'polygon':
            points = context.fir.pixelToDegree(self.canvas.points)
            if self.canvas.done:
                coordinates = ['{} {}'.format(p[1], p[0]) for p in points]
                self.message = 'WI ' + ' - '.join(coordinates)
            else:
                coordinates = ['{} {}'.format(p[1], p[0]) for p in points]
                self.message = '\n'.join(coordinates)

        self.board.setText(self.message)

    def setMode(self, mode):
        self.canvas.mode = mode

    def text(self):
        return self.message

    def clear(self):
        self.area = []
        self.message = ''
        self.board.setText('')
        self.canvas.clear()
