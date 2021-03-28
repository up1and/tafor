import os
import sys
import copy
import math

import shapefile
import shapely.geometry

from itertools import cycle

from pyproj import Proj

from PyQt5.QtWidgets import (QWidget, QFrame, QApplication, QVBoxLayout, QHBoxLayout, QGraphicsView, QGraphicsScene, QRubberBand, 
    QGraphicsPolygonItem, QStyleOptionGraphicsItem, QPushButton, QToolButton, QGraphicsTextItem, QGraphicsItem, QLabel, QMenu, 
    QActionGroup, QAction, QSpacerItem, QSizePolicy)
from PyQt5.QtGui import QIcon, QPainter, QPolygonF, QBrush, QPen, QColor
from PyQt5.QtCore import QCoreApplication, QObject, QPoint, QPointF, Qt, QRect, QRectF, QSize, QSizeF, pyqtSignal

from tafor import root
from tafor.states import context
from tafor.utils.convert import listToPoint, pointToList
from tafor.utils.sigmet import encodeSigmetArea, simplifyLine, clipLine, clipPolygon, simplifyPolygon
from tafor.components.widgets.geometry import Country, Fir, PlottedPoint, PlottedCircle, PlottedLine, PlottedShadowLine, PlottedPolygon



def distanceBetweenPoints(point1, point2):
    x = point1.x() - point2.x()
    y = point1.y() - point2.y()
    return math.sqrt(x ** 2 + y ** 2)

def bearing(origin, point):
    return math.atan2(origin.y() - point.y(), origin.x() - point.x())


class AreaBoard(QWidget):

    def __init__(self, parent=None):
    	pass


boundaries = [[114.000001907,14.500001907],[112.000001908,14.500001907],[108.716665268,17.416666031],[107.683332443,18.333333969],[107.18972222,19.26777778],[107.929967,19.9567],[108.050001145,20.500001907],[111.500001908,20.500001907],[111.500001908,19.500001907],[114.000001907,16.666666031],[114.000001907,14.500001907]]


class Drawing(QObject):

    finished = pyqtSignal()
    pointsChanged = pyqtSignal()

    def __init__(self, canvas):
        super(Drawing, self).__init__()
        self.canvas = canvas
        self.done = False
        self.elements = None
        self.coordinates = []

    @property
    def maxPoint(self):
        if self.canvas.mode == 'corridor':
            return 4
        else:
            return 7

    @property
    def radius(self):
        if self.done:
            if self.canvas.mode == 'corridor':
                return self.coordinates[-1]

            if self.canvas.mode == 'circle':
                return distanceBetweenPoints(*self.coordinates)

        return 0

    @property
    def coords(self):
        coordinates = self.coordinates

        if self.canvas.mode == 'corridor':
            coords = [(p.x(), p.y()) for p in self.coordinates[:-1]]
            polygon = shapely.geometry.LineString(coords).buffer(self.radius, cap_style=2, join_style=2)
            coordinates = [QPointF(*p) for p in list(polygon.exterior.coords)]

        return coordinates

    @property
    def boundaries(self):
        points = []
        for lon, lat in boundaries:
            px, py = self.canvas.toCanvasCoordinates(lon, lat)
            points.append(self.canvas.mapFromScene(px, py))

        return points

    def append(self, point):
        if self.done:
            return

        point = self.canvas.mapToScene(point)

        if self.canvas.mode in ['polygon', 'line', 'corridor']:
            if len(self.coordinates) < self.maxPoint:
                self.coordinates.append(point)
                self.redraw()

        if self.canvas.mode in ['rectangular', 'circle']:
            self.coordinates.append(point)
            if len(self.coordinates) == 2:
                self.done = True
                self.finished.emit()
            
            self.redraw()

    def pop(self):
        if self.canvas.mode in ['polygon', 'line', 'corridor']:
            if self.done:
                if self.canvas.mode == 'corridor':
                    self.coordinates.pop()
                else:
                    if len(self.coordinates) > self.maxPoint:
                        self.coordinates = self.coordinates[:7]
                self.done = False
                self.finished.emit()
                self.redraw()

            else:
                if self.coordinates:
                    self.coordinates.pop()
                    self.redraw()

        if self.canvas.mode in ['rectangular', 'circle']:
            self.coordinates = []
            self.done = False
            self.finished.emit()
            self.redraw()

    def resize(self, ratio):
        if self.canvas.mode == 'circle':
            deviation = 5
            if self.done:
                if ratio > 0 or self.radius > deviation * 4:
                    radius = self.radius + deviation * ratio
                    center, point = self.coordinates
                    radian = bearing(point, center)
                    self.coordinates[-1] = QPointF(center.x() + math.cos(radian) * radius, center.y() + math.sin(radian) * radius)
                    self.redraw()

        if self.canvas.mode == 'corridor':
            deviation = 3
            if self.done:
                if ratio > 0:
                    if len(self.coordinates) * 2 - 1 == len(self.coords):
                        self.coordinates[-1] += deviation * ratio

                if ratio < 0 and self.coordinates[-1] > deviation:
                    self.coordinates[-1] += deviation * ratio
            else:
                self.coordinates.append(deviation)
                self.done = True
                self.finished.emit()

            self.redraw()

    def clip(self):
        # clip the area with boundaries
        coordinates = [self.canvas.mapFromScene(p) for p in self.coordinates]
        coordinates = clipPolygon(pointToList(self.boundaries), pointToList(coordinates))

        if self.canvas.mode == 'polygon':
            coordinates = simplifyPolygon(coordinates, maxPoint=self.maxPoint, extend=True)

        # make the points clockwise
        coordinates.reverse()
        self.coordinates = [self.canvas.mapToScene(*p) for p in coordinates]
        self.done = True if len(self.coordinates) > 2 else False
        self.finished.emit()
        self.redraw()

    def clear(self):
        self.done = False
        self.coordinates = []
        self.finished.emit()
        self.redraw()

    def redraw(self):
        items = []

        if self.canvas.mode in ['polygon', 'line', 'corridor']:
            if self.done:
                items.append(PlottedPolygon(self.coords))
            else:
                if len(self.coordinates) == 1:
                    items.append(PlottedPoint(self.coordinates[0]))
                else:
                    for i, point in enumerate(self.coordinates):
                        if i == 0:
                            prev = point
                            continue
                        else:
                            line = PlottedLine(prev, point)
                            shadowLine = PlottedShadowLine(prev, point)
                            items.append(shadowLine)
                            items.append(line)
                            prev = point

        if self.canvas.mode == 'rectangular':
            if self.done:
                rect = QRectF(*self.coordinates)
                polygon = [rect.topLeft(), rect.topRight(), rect.bottomRight(), rect.bottomLeft()]
                items.append(PlottedPolygon(polygon))

        if self.canvas.mode == 'circle':
            if self.done:
                items.append(PlottedCircle(self.coordinates[0], self.radius))
                items.append(PlottedLine(*self.coordinates))
            else:
                if self.coordinates:
                    items.append(PlottedPoint(self.coordinates[0]))

        if self.elements:
            self.canvas.scene.removeItem(self.elements)

        self.elements = self.canvas.scene.createItemGroup(items)

    def text(self):
        pass


class Canvas(QGraphicsView):

    mouseMoved = pyqtSignal(tuple)

    def __init__(self, path):
        super(Canvas, self).__init__()
        self.maps = []

        self.countries = []
        self.firs = []
        self.sigmets = []

        self.type = 'default'
        self.mode = 'polygon'
        self.lock = False
        self.maxPoint = 7

        self.shapefile = path
        self.projection = Proj('epsg:3395')
        self.ratio, self.offset = 1/2000, (0, 0)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setTransformationAnchor(QGraphicsView.AnchorViewCenter)
        self.setRenderHint(QPainter.Antialiasing)

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        center = self.toCanvasCoordinates(110.59724541100003, 17.78555956845455)
        self.centerOn(QPointF(*center))

        self.setMouseTracking(True)

        self.rubberBand = QRubberBand(QRubberBand.Rectangle, self)
        self.drawings = {
            'default': Drawing(self),
            'forecast': Drawing(self)
        }

    # def addGeometry(self, geometry):
    #     self.geometries.append(geometry)

    @property
    def drawing(self):
        return self.drawings[self.type]

    def zoomIn(self):
        zoom = QStyleOptionGraphicsItem.levelOfDetailFromTransform(self.transform())
        if zoom < 5:
            self.scale(1.25, 1.25)

    def zoomOut(self):
        zoom = QStyleOptionGraphicsItem.levelOfDetailFromTransform(self.transform())
        if zoom > 0.15:
            self.scale(0.8, 0.8)

    def leaveEvent(self, event):
        self.mouseMoved.emit(())

    def mouseDoubleClickEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.zoomIn()

    def mousePressEvent(self, event):
        if not self.lock and event.buttons() == Qt.LeftButton:
            self.setDragMode(QGraphicsView.ScrollHandDrag)
            self.pos = event.pos()

        if self.lock:
            if self.mode in ['polygon', 'line']:
                self.polygonMousePressEvent(event)

            if self.mode == 'rectangular':
                self.rectangularMousePressEvent(event)

            if self.mode == 'circle':
                self.circleMousePressEvent(event)

            if self.mode == 'corridor':
                self.corridorMousePressEvent(event)

        # super().mousePressEvent(event)

    def polygonMousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drawing.append(event.pos())
            if len(self.drawing.coordinates) > 2:
                deviation = 12
                initPoint = self.mapFromScene(self.drawing.coordinates[0])
                dx = abs(event.pos().x() - initPoint.x())
                dy = abs(event.pos().y() - initPoint.y())

                if dx < deviation and dy < deviation:
                    self.drawing.clip()

        if event.button() == Qt.RightButton:
            self.drawing.pop()

    def rectangularMousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.pos = event.pos()
            self.rubberBand.setGeometry(QRect(self.pos, QSize()))
            self.rubberBand.show()
            self.drawing.append(event.pos())

        if event.button() == Qt.RightButton:
            self.drawing.pop()

    def circleMousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drawing.append(event.pos())

        if event.button() == Qt.RightButton:
            self.drawing.pop()

    def corridorMousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
           self.drawing.append(event.pos())

        if event.button() == Qt.RightButton:
            self.drawing.pop()

    def mouseMoveEvent(self, event):
        self.emitMouseMoved(event)

        if not self.lock and event.buttons() == Qt.LeftButton:
            offset = self.pos - event.pos()
            self.pos = event.pos()
            x = self.horizontalScrollBar().value() + offset.x()
            y = self.verticalScrollBar().value() + offset.y()
            self.horizontalScrollBar().setValue(x)
            self.verticalScrollBar().setValue(y)

        if self.lock and self.mode == 'rectangular' and event.buttons() == Qt.LeftButton:
            self.rubberBand.setGeometry(QRect(self.pos, event.pos()).normalized())

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        # center = self.mapToScene(self.viewport().rect().center()) + QPointF(self.offset.x(), self.offset.y())
        # self.centerOn(center)
        self.setDragMode(QGraphicsView.NoDrag)

        if self.mode == 'rectangular' and event.button() == Qt.LeftButton:
            self.rubberBand.hide()
            self.drawing.append(event.pos())

        super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        if self.lock:
            if self.mode in ['circle', 'corridor']:
                ratio = 1 if event.angleDelta().y() > 0 else -1
                self.drawing.resize(ratio)
        else:
            if event.angleDelta().y() > 0:
                self.zoomIn()
            else:
                self.zoomOut()

        self.emitMouseMoved(event)

    def emitMouseMoved(self, event):
        pos = self.mapToScene(event.pos())
        self.mouseMoved.emit(self.toGeographicalCoordinates(pos.x(), pos.y()))

    def toGeographicalCoordinates(self, x, y):
        px, py = (x - self.offset[0]) / self.ratio, (self.offset[1] - y) / self.ratio
        return self.projection(px, py, inverse=True)
        
    def toCanvasCoordinates(self, longitude, latitude):
        px, py = self.projection(longitude, latitude)
        return px * self.ratio + self.offset[0], -py * self.ratio + self.offset[1]

    def setMode(self, mode):
        self.mode = mode
        self.drawing.clear()

    def setType(self, key):
        needToResetDrawing = key != 'forecast' and self.type == 'forecast'
        self.type = key

        if needToResetDrawing:
            # clear forecast drawing
            self.drawings['forecast'].clear()

    def isDefaultLocationFinished(self):
        # shoud check the shape can be encode to text
        drawing = self.drawings['default']
        return drawing.done

    def drawPolygons(self):
        sf = shapefile.Reader(self.shapefile)       
        shapes = sf.shapes()
        for polygons in shapes:
            polygons = shapely.geometry.shape(polygons)
            if polygons.geom_type == 'Polygon':
                polygons = [polygons]
            for shape in polygons:
                p = Country(shape.exterior.coords)
                p.addTo(self, self.countries)

    def drawBoundaries(self):
        p = Fir(boundaries)
        p.addTo(self, self.firs)

    def updateDrawing(self):
        self.scene.addItem(self.drawing)

    def redraw(self):
        self.drawPolygons()
        self.drawBoundaries()
        self.polygons = self.scene.createItemGroup(self.countries)
        self.firs = self.scene.createItemGroup(self.firs)

    def clear(self):
        pass


class GraphicsWindow(QWidget):

    def __init__(self, parent=None):
        super(GraphicsWindow, self).__init__()
        path = os.path.join(root, 'shapes', 'countries.shp')
        self.canvas = Canvas(path)
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 6, 0, 0)
        self.layout.addWidget(self.canvas)
        self.setLayout(self.layout)
        self.setMaximumSize(800, 500)

        self.zoomInButton = QPushButton(self)
        self.zoomInButton.setText('+')
        self.zoomOutButton = QPushButton(self)
        self.zoomOutButton.setText('-')
        self.zoomLayout = QVBoxLayout()
        self.zoomLayout.addWidget(self.zoomInButton)
        self.zoomLayout.addWidget(self.zoomOutButton)
        self.zoomLayout.setGeometry(QRect(20, 20, 24, 48))

        # self.lockButton = QPushButton(self)
        # self.lockButton.setText('Drag')

        self.layerButton = QToolButton(self)
        self.layerButton.setText('Layer')
        self.layerButton.setPopupMode(QToolButton.InstantPopup)
        self.layerButton.setIcon(QIcon(':/layers.png'))

        self.fcstButton = QToolButton(self)
        self.fcstButton.setEnabled(False)
        self.fcstButton.setText('Fcst')
        self.fcstButton.setCheckable(True)
        self.fcstButton.setIcon(QIcon(':/f.png'))

        self.modeButton = QToolButton(self)
        self.modeButton.setText('Mode')

        for button in [self.layerButton, self.fcstButton, self.modeButton]:
            button.setFixedSize(26, 26)
            button.setAutoRaise(True)

        spacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.operationLayout = QHBoxLayout()
        # self.operationLayout.addWidget(self.lockButton)
        self.operationLayout.addWidget(self.layerButton)
        self.operationLayout.addWidget(self.fcstButton)
        self.operationLayout.addWidget(self.modeButton)
        self.operationLayout.setGeometry(QRect(700, 16, 90, 30))

        self.positionLabel = QLabel(self)
        self.positionLabel.setAttribute(Qt.WA_TransparentForMouseEvents)

        self.setLayersMenu()
        self.setModeButton()
        self.load()
        self.bindSignal()

    def bindSignal(self):
        self.zoomOutButton.clicked.connect(self.canvas.zoomOut)
        self.zoomInButton.clicked.connect(self.canvas.zoomIn)
        # self.lockButton.clicked.connect(self.switchLock)
        self.modeButton.clicked.connect(self.nextMode)
        self.fcstButton.clicked.connect(self.switchLocationType)
        self.canvas.mouseMoved.connect(self.updatePositionLabel)

        self.canvas.drawings['default'].finished.connect(self.setFcstButton)

    def setModeButton(self, tt='WS'):
        if tt == 'WC':
            icons = [{'icon': ':/circle.png', 'mode': 'circle'}]
        else:
            icons = [
                {'icon': ':/polygon.png', 'mode': 'polygon'},
                {'icon': ':/line.png', 'mode': 'line'},
                {'icon': ':/rectangular.png', 'mode': 'rectangular'},
                {'icon': ':/corridor.png', 'mode': 'corridor'}
            ]

        self.icons = cycle(icons)
        self.nextMode()

    def setFcstButton(self):
        enbale = self.canvas.isDefaultLocationFinished()
        self.fcstButton.setEnabled(enbale)

    def nextMode(self):
        mode = next(self.icons)
        self.canvas.setMode(mode['mode'])
        self.modeButton.setIcon(QIcon(mode['icon']))
        # self.modeButton.setText(mode['mode'])

    def switchLocationType(self):
        if self.fcstButton.isChecked():
            self.canvas.setType('forecast')
            self.modeButton.setEnabled(False)
        else:
            self.canvas.setType('default')
            self.modeButton.setEnabled(True)

    def switchLock(self):
        if self.canvas.lock:
            self.canvas.lock = False
            # self.lockButton.setText('Drag')
        else:
            self.canvas.lock = True
            # self.lockButton.setText('Lock')

    def setShapeMode(self):
        pass

    def setLayersMenu(self):
        self.layerMenu = QMenu(self)
        self.trimShapesAction = QAction(self)
        self.trimShapesAction.setText(QCoreApplication.translate('Editor', 'Trim Shapes'))
        self.trimShapesAction.setCheckable(True)
        self.showSigmetAction = QAction(self)
        self.showSigmetAction.setText(QCoreApplication.translate('Editor', 'Latest SIGMET/AIRMET'))
        self.showSigmetAction.setCheckable(True)
        self.showSigmetAction.setChecked(True)
        self.layerActionGroup = QActionGroup(self)
        self.layerActionGroup.setExclusive(True)
        self.layerMenu.addAction(self.trimShapesAction)
        self.layerMenu.addAction(self.showSigmetAction)
        self.layerMenu.addSeparator()
        self.layerButton.setMenu(self.layerMenu)
        self.layerButton.setStyleSheet('QToolButton::menu-indicator {image: none;}')

    def setLayerSelectAction(self):
        self.layers = context.fir.layersName()
        if not self.layers or self.layerActionGroup.actions():
            return

        for i, name in enumerate(self.layers):
            setattr(self, 'layersAction' + str(i), QAction(self))
            action = getattr(self, 'layersAction' + str(i))
            action.setText(name)
            action.setCheckable(True)
            self.layerActionGroup.addAction(action)
            self.layerMenu.addAction(action)

    def loadLayersActionState(self):
        trimShapes = context.fir.trimShapes
        self.trimShapesAction.setChecked(trimShapes)

        showSigmet = context.fir.showSigmet
        self.showSigmetAction.setChecked(showSigmet)

        if self.layerActionGroup.actions():
            layerIndex = context.fir.layerIndex
            action = self.layerActionGroup.actions()[layerIndex]
            action.setChecked(True)

    def changeLayerStatus(self, action):
        checked = action.isChecked()
        if action == self.trimShapesAction:
            context.fir.trimShapes = checked

        if action == self.showSigmetAction:
            context.fir.showSigmet = checked

        if action in self.layerActionGroup.actions():
            index = self.layerActionGroup.actions().index(action)
            if context.fir.layerIndex != index:
                prevLayer = context.fir.layer
                context.fir.layerIndex = index
                self.canvasWidget.canvas.resizeCoords(prevLayer)

    def updatePositionLabel(self, pos):
        if pos:
            lon, lat = pos
            text = '{:.2f}, {:.2f}'.format(lat, lon)
            self.positionLabel.setText(text)
        else:
            self.positionLabel.clear()

    def resizeEvent(self, event):
        self.positionLabel.move(self.width() - self.positionLabel.width(), self.height() - self.positionLabel.height() - 10)
        super(GraphicsWindow, self).resizeEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Control:
            self.canvas.lock = True
            # self.lockButton.setText('Lock')

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_Control:
            self.canvas.lock = False
            # self.lockButton.setText('Drag')

    def load(self):
        self.canvas.redraw()

