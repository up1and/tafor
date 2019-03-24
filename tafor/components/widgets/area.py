from PyQt5.QtCore import QSize, Qt, QRect, QCoreApplication, QPoint, pyqtSignal
from PyQt5.QtGui import QPainter, QPainterPath, QPolygon, QPen, QColor, QBrush, QFont
from PyQt5.QtWidgets import QWidget, QGridLayout, QLabel

from shapely.geometry import Polygon

from tafor import conf
from tafor.states import context
from tafor.utils.convert import listToPoint, pointToList
from tafor.utils.sigmet import encodeSigmetArea, simplifyLine, clipPolygon, simplifyPolygon


class Canvas(QWidget):
    pointsChanged = pyqtSignal()
    stateChanged = pyqtSignal()

    def __init__(self, parent=None):
        super(Canvas, self).__init__(parent)
        self.coords = {
            'default': {'points': [], 'done': False},
            'forecast': {'points': [], 'done': False}
        }
        self.areaType = 'default'
        self.rectangular = []
        self.mode = 'polygon'
        self.maxPoint = 7
        self.color = Qt.white
        self.shadowColor = QColor(0, 0, 0, 127)
        self.areaColors = {
            'default': QColor(240, 156, 0, 178),
            'forecast': QColor(154, 205, 50, 100)
        }
        self.fir = context.fir
        self.parent = parent
        self.setSizePolicy(0, 0)

    @property
    def points(self):
        return self.coords[self.areaType]['points']

    @points.setter
    def points(self, value):
        self.coords[self.areaType]['points'] = value

    @property
    def done(self):
        return self.coords[self.areaType]['done']

    @done.setter
    def done(self, value):
        self.coords[self.areaType]['done'] = value

    @property
    def boundaryColor(self):
        return Qt.red if self.fir.image() else Qt.white

    def sizeHint(self):
        *_, w, h = self.fir.rect()
        if w == 0 or h == 0:
            width = conf.value('General/FirCanvasSize') or 300
            width = int(width)
            return QSize(width, width)
        return QSize(w, h)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        if not self.fir.drawable:
            self.drawEmpty(painter)
            return

        self.drawCloudImage(painter)
        self.drawBoundaries(painter)
        self.drawSigmets(painter)

        if len(self.points) == 1:
            self.drawOnePoint(painter)

        if not self.done:
            self.drawOutline(painter)
            self.drawRectangular(painter)

        self.drawArea(painter)

    def mousePressEvent(self, event):
        if not self.fir.drawable:
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
                if len(self.points) > self.maxPoint:
                    self.points = self.points[:self.maxPoint]
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
            self.clearRectangular()

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
        for key, coords in self.coords.items():
            if coords['done']:
                points = listToPoint(coords['points'])
                pol = QPolygon(points)
                brush = QBrush(self.areaColors[key])
                painter.setBrush(brush)
                painter.setPen(self.color)
                painter.drawPolygon(pol)

    def drawBoundaries(self, painter):
        points = listToPoint(self.fir.boundaries())
        pol = QPolygon(points)
        painter.setPen(self.boundaryColor)
        painter.drawPolygon(pol)

    def drawCloudImage(self, painter):
        image = self.fir.pixmap()
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

    def drawEmpty(self, painter):
        rect = QRect(QPoint(0, 0), self.sizeHint())
        painter.setPen(Qt.DashLine)
        painter.drawRect(rect)
        painter.drawText(rect, Qt.AlignCenter, QCoreApplication.translate('Editor', 'No Satellite Image'))

    def drawSigmets(self, painter):
        pen = QPen(QColor(204, 204, 204), 1, Qt.DashLine)
        brushes = {
            'ts': QBrush(QColor(240, 156, 0, 100)),
            'turb': QBrush(QColor(37, 238, 44, 100)),
            'ice': QBrush(QColor(67, 255, 255, 100)),
            'ash': QBrush(QColor(250, 0, 25, 100)),
            'typhoon': QBrush(QColor(250, 50, 250, 100)),
            'other': QBrush(QColor(250, 250, 50, 100))
        }

        sigmets = self.fir.sigmetsInfo()
        for i, sig in enumerate(sigmets):
            center = Polygon(sig['area']).centroid
            met = self.fir.sigmets()[i]
            points = listToPoint(sig['area'])
            pol = QPolygon(points)
            brush = brushes.get(sig['type'], 'other')
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
        painter.drawRect(rect)

    def setAreaType(self, areaType):
        forecastToDefault = areaType != 'forecast' and self.areaType == 'forecast'
        defaultToForecast = areaType != 'default' and self.areaType == 'default'
        self.areaType = areaType

        if forecastToDefault:
            self.coords['forecast'] = {'points': [], 'done': False}
            self.pointsChanged.emit()
            self.stateChanged.emit()
            self.update()

        if defaultToForecast:
            self.rectangular = []

    def setMode(self, mode):
        self.mode = mode
        self.clear()

    def clearRectangular(self):
        self.coords[self.areaType] = {'points': [], 'done': False}
        self.rectangular = []
        self.pointsChanged.emit()
        self.stateChanged.emit()
        self.update()

    def clear(self):
        self.coords = {
            'default': {'points': [], 'done': False},
            'forecast': {'points': [], 'done': False}
        }
        self.rectangular = []
        self.pointsChanged.emit()
        self.stateChanged.emit()
        self.update()

    def showEvent(self, event):
        self.updateGeometry()


class AreaBoard(QWidget):

    def __init__(self):
        super(AreaBoard, self).__init__()

        self.board = QLabel('')
        self.board.setAlignment(Qt.AlignTop)
        self.board.setWordWrap(True)
        self.board.setMinimumHeight(26)
        self.canvas = Canvas(self)
        self.layout = QGridLayout()
        self.layout.addWidget(self.canvas, 0, 0)
        self.layout.setSpacing(20)
        self.layout.setContentsMargins(0, 5, 0, 5)
        self.setLayout(self.layout)
        self.setMaximumWidth(575)

        self.message = {}
        self.wideMode = False
        self.defaultCanEncode = False

        self.canvas.pointsChanged.connect(self.updateArea)
        self.canvas.stateChanged.connect(self.updateArea)

    def showEvent(self, event):
        if self.canvas.sizeHint().width() > 440:
            self.layout.addWidget(self.board, 1, 0)
            self.wideMode = True
        else:
            self.layout.addWidget(self.board, 0, 1)
            self.wideMode = False

    @property
    def pointspacing(self):
        return ' - ' if self.wideMode else '\n'

    @property
    def wordspacing(self):
        return '  ' if self.wideMode else '<br>'

    def updateArea(self):
        for key, coords in self.canvas.coords.items():
            text = self.generateText(coords)
            self.message[key] = text

            if key == 'default':
                self.defaultCanEncode = True if text else False

        self.setBorad(self.message)

    def generateText(self, coords):
        message = ''
        if self.canvas.mode == 'rectangular' and coords['done']:

            boundaries = context.fir._state['boundaries']
            points = context.fir.pixelToDecimal(coords['points'])
            area = encodeSigmetArea(boundaries, points, mode='rectangular')

            lines = []
            for identifier, *points in area:
                points = context.fir.decimalToDegree(points)
                latlng = simplifyLine(points)

                if latlng:
                    line = '{} OF {}'.format(identifier, latlng)
                    lines.append(line)

            message = ' AND '.join(lines)

        if self.canvas.mode == 'line':
            if coords['done']:
                boundaries = context.fir._state['boundaries']
                points = context.fir.pixelToDecimal(coords['points'])
                area = encodeSigmetArea(boundaries, points, mode='line')

                lines = []
                for identifier, *points in area:
                    points = context.fir.decimalToDegree(points)
                    coordinates = []
                    for lng, lat in points:
                        coordinates.append('{} {}'.format(lat, lng))

                    line = '{} OF LINE {}'.format(identifier, ' - '.join(coordinates))
                    lines.append(line)

                message = ' AND '.join(lines)
            else:
                points = context.fir.pixelToDegree(coords['points'])
                coordinates = ['{} {}'.format(p[1], p[0]) for p in points]
                message = self.pointspacing.join(coordinates)


        if self.canvas.mode == 'polygon':
            points = context.fir.pixelToDegree(coords['points'])
            if coords['done']:
                coordinates = ['{} {}'.format(p[1], p[0]) for p in points]
                message = 'WI ' + ' - '.join(coordinates)
            else:
                coordinates = ['{} {}'.format(p[1], p[0]) for p in points]
                message = self.pointspacing.join(coordinates)

        return message

    def setBorad(self, messages):
        messages = []
        orders = ['default', 'forecast']
        labels = {
            'default': QCoreApplication.translate('Editor', 'DEFAULT'),
            'forecast': QCoreApplication.translate('Editor', 'FORECAST')
        }
        for key in orders:
            if self.message[key]:
                label = '<span style="color: grey">{}</span>'.format(labels[key])
                text = label + self.wordspacing + self.message[key]
                messages.append(text)

        self.board.setText('<br><br>'.join(messages))

    def setMode(self, mode):
        self.canvas.setMode(mode)

    def setAreaType(self, areaType):
        self.canvas.setAreaType(areaType)

    def canEnbaleFcstMode(self):
        return self.canvas.coords['default']['done'] and self.defaultCanEncode

    def texts(self):
        messages = []
        if self.canvas.areaType == 'default' and self.canvas.done:
            messages.append(self.message['default'])

        if self.canvas.areaType == 'forecast' and self.canvas.done:
            messages.append(self.message['default'])
            messages.append(self.message['forecast'])

        return messages

    def clear(self):
        self.message = {}
        self.canEncode = False
        self.board.setText('')
        self.canvas.clear()
