import copy

from PyQt5.QtCore import QSize, Qt, QRect, QCoreApplication, QPoint, pyqtSignal
from PyQt5.QtGui import QPainter, QPainterPath, QPolygon, QPen, QColor, QBrush, QFont
from PyQt5.QtWidgets import QWidget, QGridLayout, QLabel

from shapely.geometry import Polygon, LineString, Point

from tafor import conf
from tafor.states import context
from tafor.utils.convert import listToPoint, pointToList, degreeToDecimal, distanceBetweenPoints
from tafor.utils.sigmet import encodeSigmetArea, simplifyLine, clipLine, clipPolygon, simplifyPolygon


class Canvas(QWidget):
    pointsChanged = pyqtSignal()
    stateChanged = pyqtSignal()

    def __init__(self, parent=None):
        super(Canvas, self).__init__(parent)
        self.coords = {
            'default': {'points': [], 'radius': 0, 'diagonal': [], 'done': False},
            'forecast': {'points': [], 'radius': 0, 'diagonal': [], 'done': False}
        }
        self.areaType = 'default'
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
    def radius(self):
        return self.coords[self.areaType]['radius']

    @radius.setter
    def radius(self, value):
        self.coords[self.areaType]['radius'] = value

    @property
    def diagonal(self):
        return self.coords[self.areaType]['diagonal']

    @diagonal.setter
    def diagonal(self, value):
        self.coords[self.areaType]['diagonal'] = value

    @property
    def boundaryColor(self):
        return Qt.red if self.fir.image() else Qt.white

    @property
    def shapes(self):
        coordinates = copy.deepcopy(self.coords)

        if self.mode == 'circle':
            for key, coords in coordinates.items():
                if coords['done']:
                    center = coords['points'][0]
                    polygon = Point(*center).buffer(coords['radius'])
                    coordinates[key]['points'] = list(polygon.exterior.coords)

        if self.mode == 'corridor':
            for key, coords in coordinates.items():
                if coords['done']:
                    polygon = LineString(coords['points']).buffer(coords['radius'], cap_style=2, join_style=2)
                    coordinates[key]['points'] = list(polygon.exterior.coords)

        return coordinates

    def setCircleCenter(self, point):
        if self.points:
            self.points[0] = point
        else:
            self.points.append(point)

        self.update()

    def setCircleRadius(self, radius):
        self.radius = radius
        self.done = True
        self.update()

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

        if self.mode == 'circle':
            self.circleMousePressEvent(event)

        if self.mode == 'corridor':
            self.corridorMousePressEvent(event)

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
            pos = (event.x(), event.y())
            if not self.diagonal:
                self.diagonal = [pos, pos]

        if event.button() == Qt.RightButton:
            self.diagonal = []
            self.done = False
            self.pointsChanged.emit()
            self.stateChanged.emit()

    def circleMousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            pos = [event.x(), event.y()]

            if self.points:
                if not self.done:
                    center = self.points[0]
                    self.radius = distanceBetweenPoints(center, pos)
                    self.done = True
                    self.stateChanged.emit()
            else:
                self.points.append(pos)
                self.pointsChanged.emit()

        if event.button() == Qt.RightButton:
            if self.done:
                self.done = False
                self.radius = 0
                self.stateChanged.emit()
            else:
                self.points = []
                self.pointsChanged.emit()

    def corridorMousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            pos = (event.x(), event.y())
            if not self.done:
                if len(self.points) < 4:
                    self.points.append(pos)
                    self.pointsChanged.emit()

        if event.button() == Qt.RightButton and self.points:
            if self.done:
                self.done = False
                self.radius = 0
                self.stateChanged.emit()
            else:
                self.points.pop()
                self.pointsChanged.emit()

    def mouseMoveEvent(self, event):
        if self.mode == 'rectangular':
            if self.done or len(self.diagonal) != 2:
                return

            self.diagonal[1] = (event.x(), event.y())
            self.update()

    def mouseReleaseEvent(self, event):
        if self.mode == 'rectangular':
            diagonal = listToPoint(self.diagonal)
            rect = QRect(*diagonal)
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

    def wheelEvent(self, event):
        if self.mode == 'circle':
            if not self.done:
                return

            move = event.angleDelta().y()
            deviation = 5
            if move > 0:
                self.radius += deviation

            if move < 0 and self.radius - deviation > 5:
                self.radius -= deviation

            self.pointsChanged.emit()
            self.update()

        if self.mode == 'corridor':
            if len(self.points) < 2:
                return

            if not self.done:
                self.points = clipLine(self.fir.boundaries(), self.points)

            move = event.angleDelta().y()
            deviation = 2
            if move > 0:
                points = self.shapes[self.areaType]['points']
                if self.points == points or len(self.points) * 2 + 1 == len(points):
                    self.radius += deviation

            if move < 0:
                self.radius -= deviation

                if self.radius < 0:
                    self.radius = 0

            if self.radius > 0:
                self.done = True
            else:
                self.done = False

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
        for key, coords in self.shapes.items():
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
        brushes = {
            'ts': QBrush(QColor(240, 156, 0, 100)),
            'turb': QBrush(QColor(37, 238, 44, 100)),
            'ice': QBrush(QColor(67, 255, 255, 100)),
            'ash': QBrush(QColor(250, 0, 25, 100)),
            'typhoon': QBrush(QColor(250, 50, 250, 100)),
            'other': QBrush(QColor(250, 250, 50, 100))
        }

        isAirmet = True if self.parent.parent.tt == 'WA' else False
        sigmets = self.fir.sigmetsInfo(isAirmet=isAirmet)
        for i, sig in enumerate(sigmets):
            for key, area in sig['area'].items():
                if not area:
                    continue

                points = listToPoint(area)
                pol = QPolygon(points)
                center = Polygon(area).centroid
                met = self.fir.sigmets()[i]
                parser = met.parser()
                sequence = parser.sequence()

                if key == 'default':
                    pen = QPen(QColor(204, 204, 204), 1, Qt.DashLine)
                    brush = brushes.get(sig['type'], brushes['other'])
                    painter.setPen(pen)

                if key == 'forecast':
                    pen = QPen(QColor(204, 204, 204, 150), 0, Qt.DashLine)
                    brush = QBrush(QColor(154, 205, 50, 70))
                    painter.setPen(pen)

                painter.setBrush(brush)
                painter.drawPolygon(pol)
                if sequence:
                    path = QPainterPath()
                    font = QFont()
                    font.setBold(True)
                    path.addText(center.x - 5, center.y + 5, font, sequence)
                    pen = QPen(QColor(0, 0, 0, 120), 2)
                    brush = QBrush(QColor(204, 204, 204))
                    painter.strokePath(path, pen)
                    painter.fillPath(path, brush)

    def drawRectangular(self, painter):
        pen = QPen(QColor(0, 120, 215))
        brush = QBrush(QColor(0, 120, 215, 40))
        painter.setPen(pen)
        painter.setBrush(brush)
        points = listToPoint(self.diagonal)
        rect = QRect(*points)
        painter.drawRect(rect)

    def setAreaType(self, areaType):
        forecastToDefault = areaType != 'forecast' and self.areaType == 'forecast'
        self.areaType = areaType

        if forecastToDefault:
            self.coords['forecast'] = {'points': [], 'radius': 0, 'diagonal': [], 'done': False}
            self.pointsChanged.emit()
            self.stateChanged.emit()
            self.update()

    def setMode(self, mode):
        self.mode = mode
        self.clear()

    def clear(self):
        self.coords = {
            'default': {'points': [], 'radius': 0, 'diagonal': [], 'done': False},
            'forecast': {'points': [], 'radius': 0, 'diagonal': [], 'done': False}
        }
        self.pointsChanged.emit()
        self.stateChanged.emit()
        self.update()

    def showEvent(self, event):
        self.updateGeometry()


class AreaBoard(QWidget):

    def __init__(self, parent=None):
        super(AreaBoard, self).__init__(parent)
        self.parent = parent
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
        return ' - ' if self.wideMode else '<br>'

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

    def setCircleCenter(self, point):
        if self.canvas.mode == 'circle':
            decimal = [degreeToDecimal(point[0]), degreeToDecimal(point[1])]
            pixel = context.fir.decimalToPixel([decimal])[0]
            self.canvas.setCircleCenter(pixel)
            self.updateArea()

    def setCircleRadius(self, radius):
        if self.canvas.mode == 'circle':
            pixel = context.fir.distanceToPixel(radius)
            self.canvas.setCircleRadius(pixel)
            self.updateArea()

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

        if self.canvas.mode == 'circle':
            points = context.fir.pixelToDegree(coords['points'])
            if coords['done']:
                radius = round(context.fir.pixelToDistance(coords['radius']) / 10) * 10
                center = points[0]
                items = ['PSN {} {}'.format(center[1], center[0]), 'WI {}KM OF CENTRE'.format(radius)]
                message = self.pointspacing.join(items)
            else:
                coordinates = ['{} {}'.format(p[1], p[0]) for p in points]
                message = self.pointspacing.join(coordinates)

        if self.canvas.mode == 'corridor':
            points = context.fir.pixelToDegree(coords['points'])
            if coords['done']:
                width = context.fir.pixelToDistance(coords['radius'])
                width = round(width / 5) * 5 
                coordinates = ['{} {}'.format(p[1], p[0]) for p in points]
                line = ' - '.join(coordinates)
                message = 'APRX {}KM WID LINE BTN {}'.format(width, line)
            else:
                coordinates = ['{} {}'.format(p[1], p[0]) for p in points]
                message = self.pointspacing.join(coordinates)

        return message

    def setBorad(self, messages):
        texts = []
        orders = ['default', 'forecast']
        labels = {
            'default': QCoreApplication.translate('Editor', 'DEFAULT'),
            'forecast': QCoreApplication.translate('Editor', 'FORECAST')
        }
        for key in orders:
            if messages[key]:
                label = '<span style="color: grey">{}</span>'.format(labels[key])
                text = label + self.wordspacing + messages[key]
                texts.append(text)

        self.board.setText('<br><br>'.join(texts))

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
