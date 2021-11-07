import os
import math

import shapefile
import shapely.geometry

from itertools import cycle

from pyproj import Proj, Geod

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGraphicsView, QGraphicsScene, QRubberBand, 
    QStyleOptionGraphicsItem, QPushButton, QToolButton, QLabel, QMenu, QActionGroup, QAction)
from PyQt5.QtGui import QIcon, QPainter
from PyQt5.QtCore import QCoreApplication, QObject, QPointF, Qt, QRect, QRectF, QSize, pyqtSignal

from tafor import root
from tafor.states import context
from tafor.utils.convert import decimalToDegree, degreeToDecimal
from tafor.utils.sigmet import encode, buffer, circle, simplifyLine, clipLine, clipPolygon, simplifyPolygon
from tafor.components.widgets.geometry import BackgroundImage, Coastline, Country, Fir, Sigmet, SketchGraphic


wgs84 = Geod(ellps='WGS84')

def distance(start, end):
    *_, dist = wgs84.inv(start[0], start[1], end[0], end[1])
    return dist

def bearing(origin, point):
    return math.atan2(origin[1] - point[1], origin[0] - point[0])


class SketchManager(object):

    def __init__(self, canvas, sketchNum=2):
        super(SketchManager).__init__()
        self.canvas = canvas
        self.graphic = SketchGraphic()
        self.sketchs = []
        self.index = 0

        for _ in range(sketchNum):
            sketch = Sketch(canvas)
            self.addSketch(sketch)

    def __iter__(self):
        for s in self.sketchs:
            yield s

    def addSketch(self, sketch):
        self.sketchs.append(sketch)
        sketch.changed.connect(self.update)

    def currentSketch(self):
        return self.sketchs[self.index]

    def first(self):
        return self.sketchs[0]

    def last(self):
        return self.sketchs[-1]

    def update(self):
        collections = self.geo()
        self.graphic.updateGeometry(collections, self.canvas)

        if self.graphic.scene():
            self.canvas.scene.removeItem(self.graphic)

        self.canvas.scene.addItem(self.graphic)

    def geo(self):
        collections = {
            'type': 'GeometryCollection',
            'geometries': []
        }
        for s in self.sketchs:
            geometry = s.geo()
            if geometry:
                collections['geometries'].append(geometry)

        return collections

    def clear(self):
        for s in self.sketchs:
            s.clear()


class Sketch(QObject):

    finished = pyqtSignal()
    changed = pyqtSignal()

    def __init__(self, canvas):
        super(Sketch, self).__init__()
        self.canvas = canvas
        self.done = False
        self.elements = None
        self.coordinates = []
        self.radius = 0

    @property
    def maxPoint(self):
        if self.canvas.mode == 'corridor':
            return 4
        else:
            return 7

    @property
    def boundaries(self):
        return context.fir.boundaries()

    def append(self, point):
        if self.done:
            return

        pos = self.canvas.mapToScene(point)
        lonlat = self.canvas.toGeographicalCoordinates(pos.x(), pos.y())

        if self.canvas.mode in ['polygon', 'line', 'corridor']:
            if len(self.coordinates) < self.maxPoint:
                self.coordinates.append(lonlat)
                self.redraw()

        if self.canvas.mode in ['rectangular', 'circle']:
            self.coordinates.append(lonlat)
            if len(self.coordinates) == 2:
                self.done = True
                self.finished.emit()

            if self.canvas.mode == 'circle' and self.done:
                # make sure the radius always multiple of 5
                radius = distance(self.coordinates[0], self.coordinates[1])
                self.radius = round(radius / 5000) * 5000
                lon, lat, _ = wgs84.fwd(self.coordinates[0][0], self.coordinates[0][1], 0, self.radius)
                self.coordinates[-1] = [lon, lat]

            self.redraw()

    def pop(self):
        if self.canvas.mode in ['polygon', 'line', 'corridor', 'circle']:
            if self.done:
                if self.canvas.mode == 'corridor':
                    self.radius = 0
                elif self.canvas.mode == 'circle':
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

        if self.canvas.mode in ['rectangular', 'entire']:
            self.coordinates = []
            self.done = False
            self.finished.emit()
            self.redraw()

    def resize(self, ratio):
        if self.canvas.mode == 'circle':
            deviation = 5000
            if self.done:
                if ratio > 0 or self.radius > deviation * 4:
                    self.radius += deviation * ratio
                    lon, lat, _ = wgs84.fwd(self.coordinates[0][0], self.coordinates[0][1], 0, self.radius)
                    self.coordinates[-1] = [lon, lat]
                    self.redraw()

        if self.canvas.mode == 'corridor':
            deviation = 5000
            if self.done:
                coords = buffer(self.coordinates, self.radius + deviation * ratio)
                if ratio > 0 and len(self.coordinates) * 2 + 1 == len(coords):
                    self.radius += deviation * ratio

                if ratio < 0 and self.radius > deviation:
                    self.radius += deviation * ratio
            else:
                self.radius = deviation
                self.done = True
                self.finished.emit()

            self.redraw()

    def clip(self):
        # clip the polygon with boundaries
        if self.canvas.mode in ['polygon', 'line']:
            self.coordinates = clipPolygon(self.boundaries, self.coordinates)

            if self.canvas.mode == 'polygon':
                self.coordinates = simplifyPolygon(self.coordinates, maxPoint=self.maxPoint, extend=True)
            # make the points clockwise
            self.coordinates.reverse()
            self.done = True if len(self.coordinates) > 2 else False

        if self.canvas.mode == 'rectangular':
            topLeft, bottomRight = self.coordinates
            topRight, bottomLeft = [bottomRight[0], topLeft[1]], [topLeft[0], bottomRight[1]]
            polygon = [topLeft, topRight, bottomRight, bottomLeft]
            self.coordinates = clipPolygon(self.boundaries, polygon)
            self.done = True

        self.finished.emit()
        self.redraw()

    def clear(self):
        self.done = False
        self.radius = 0
        self.coordinates = []
        self.finished.emit()
        self.redraw()

    def geo(self):
        geometry = {}
        if self.canvas.mode in ['polygon', 'line', 'corridor']:
            if self.done:
                geometry = {
                    'type': 'Polygon',
                    'coordinates': self.coordinates
                }
            else:
                if len(self.coordinates) == 1:
                    geometry = {
                        'type': 'Point',
                        'coordinates': self.coordinates[0]
                    }

                if len(self.coordinates) > 1:
                    geometry = {
                        'type': 'LineString',
                        'coordinates': self.coordinates
                    }

        if self.canvas.mode == 'rectangular':
            if self.done:
                geometry = {
                    'type': 'Polygon',
                    'coordinates': self.coordinates
                }

        if self.canvas.mode == 'circle':
            if self.done:
                circles = circle(self.coordinates[0], self.radius)
                geometry = {
                    'type': 'Polygon',
                    'coordinates': circles
                }
            else:
                if self.coordinates:
                    geometry = {
                        'type': 'Point',
                        'coordinates': self.coordinates[0]
                    }

        if self.canvas.mode == 'corridor':
            if self.done:
                points = buffer(self.coordinates, self.radius)
                
                geometry = {
                    'type': 'Polygon',
                    'coordinates': points
                }

        return geometry

    def redraw(self, silent=False):
        if not silent:
            self.changed.emit()

    def text(self):
        message = ''

        if self.canvas.mode == 'rectangular':
            area = encode(context.fir.boundaries(), self.coordinates, mode='rectangular')

            lines = []
            for identifier, *points in area:
                points = [(decimalToDegree(lon, fmt='longitude'), decimalToDegree(lat)) for lon, lat in points]
                lonlat = simplifyLine(points)

                if lonlat:
                    line = '{} OF {}'.format(identifier, lonlat)
                    lines.append(line)

            message = ' AND '.join(lines)

        if self.canvas.mode == 'line':
            if self.done:
                area = encode(context.fir.boundaries(), self.coordinates, mode='line')

                lines = []
                for identifier, *points in area:
                    points = [(decimalToDegree(lon, fmt='longitude'), decimalToDegree(lat)) for lon, lat in points]
                    coordinates = []
                    for lon, lat in points:
                        coordinates.append('{} {}'.format(lat, lon))

                    line = '{} OF LINE {}'.format(identifier, ' - '.join(coordinates))
                    lines.append(line)

                message = ' AND '.join(lines)
            else:
                points = [(decimalToDegree(lon, fmt='longitude'), decimalToDegree(lat)) for lon, lat in self.coordinates]
                coordinates = ['{} {}'.format(p[1], p[0]) for p in points]
                message = ' - '.join(coordinates)

        if self.canvas.mode == 'polygon':
            points = [(decimalToDegree(lon, fmt='longitude'), decimalToDegree(lat)) for lon, lat in self.coordinates]
            if self.done:
                coordinates = ['{} {}'.format(p[1], p[0]) for p in points]
                message = 'WI ' + ' - '.join(coordinates)
            else:
                coordinates = ['{} {}'.format(p[1], p[0]) for p in points]
                message = ' - '.join(coordinates)

        if self.canvas.mode == 'corridor':
            points = [(decimalToDegree(lon, fmt='longitude'), decimalToDegree(lat)) for lon, lat in self.coordinates]
            if self.done:
                unit = 'KM'
                coordinates = ['{} {}'.format(p[1], p[0]) for p in points]
                line = ' - '.join(coordinates)
                message = 'APRX {}{} WID LINE BTN {}'.format(round(self.radius / 1000), unit, line)
            else:
                coordinates = ['{} {}'.format(p[1], p[0]) for p in points]
                message = ' - '.join(coordinates)

        if self.canvas.mode == 'circle':
            points = [(decimalToDegree(lon, fmt='longitude'), decimalToDegree(lat)) for lon, lat in self.coordinates]
            if self.done:
                unit = 'KM'
                center = points[0]
                items = ['PSN {} {}'.format(center[1], center[0]), 'WI {}{} OF CENTRE'.format(round(self.radius / 1000), unit)]
                message = ' - '.join(items)
            else:
                coordinates = ['{} {}'.format(p[1], p[0]) for p in points]
                message = ' - '.join(coordinates)

        return message

    def updateCircle(self, circle):
        if self.canvas.mode == 'circle':
            if 'center' in circle:
                center = [degreeToDecimal(circle['center'][0]), degreeToDecimal(circle['center'][1])]
                center = self.canvas.toCanvasCoordinates(*center)
                center = QPointF(*center)

                if self.coordinates:
                    self.coordinates[0] = center
                else:
                    self.coordinates = [center]

            if 'radius' in circle:
                radius = int(circle['radius']) * 1000 / self.canvas.groundResolution(self.approximateLatitude)

                if len(self.coordinates) == 1:
                    self.coordinates.append(QPointF(center.x() + radius, center.y()))

                point = self.coordinates[-1]
                radian = bearing(point, center)
                self.coordinates[-1] = QPointF(center.x() + math.cos(radian) * radius, center.y() + math.sin(radian) * radius)
                self.done = True

            self.redraw(silent=True)

    def geographicalCircle(self):
        if self.canvas.mode == 'circle':
            points = [self.canvas.toGeographicalCoordinates(p.x(), p.y()) for p in self.coordinates]
            points = [(decimalToDegree(lng, fmt='longitude'), decimalToDegree(lat)) for lng, lat in points]

            if points:
                radius = self.canvas.groundResolution(self.approximateLatitude) * self.radius / 1000
                radius = round(radius)
                coords = {
                    'center': points[0],
                    'radius': radius
                }

                return coords


class Canvas(QGraphicsView):

    mouseMoved = pyqtSignal(tuple)

    def __init__(self):
        super(Canvas, self).__init__()
        self.maps = []

        self.coastlines = []
        self.firs = []
        self.sigmets = []
        self.backgrounds = []

        self.type = 'default'
        self.mode = 'polygon'
        self.lock = False
        self.maxPoint = 7

        self.maxLayerExtent = context.fir.maxLayerExtent()

        # +proj=merc +lon_0=0 +k=1 +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs 
        self.projection = Proj('+proj=eqc +datum=WGS84')
        if self.projection.crs.is_geographic:
            self.ratio = 100
        else:
            self.ratio = 1/1113

        self.offset = (0, 0)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setTransformationAnchor(QGraphicsView.AnchorViewCenter)
        self.setRenderHint(QPainter.Antialiasing)
        self.setFocusPolicy(Qt.StrongFocus)

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.setMouseTracking(True)

        self.rubberBand = QRubberBand(QRubberBand.Rectangle, self)

        self.sketchManager = SketchManager(self)

    @property
    def sketch(self):
        return self.sketchManager.currentSketch()

    def extentBound(self, extent):
        minlon, minlat, maxlon, maxlat = extent
        minx, miny = self.toCanvasCoordinates(minlon, minlat)
        maxx, maxy = self.toCanvasCoordinates(maxlon, maxlat)
        return minx, miny, maxx, maxy

    def maxZoomFactor(self):
        extent = context.fir.maxLayerExtent()
        if not extent:
            return 0

        minx, miny, maxx, maxy = self.extentBound(extent)
        rect = QRectF(0, 0, abs(maxx - minx), abs(maxy - miny))
        viewrect = self.viewport().rect()
        scenerect = self.transform().mapRect(rect)
        factor = max(viewrect.width() / scenerect.width(),
                             viewrect.height() / scenerect.height())

        return factor

    def zoomIn(self):
        zoom = QStyleOptionGraphicsItem.levelOfDetailFromTransform(self.transform())
        if zoom < 5:
            self.scale(1.25, 1.25)

    def zoomOut(self):
        zoom = QStyleOptionGraphicsItem.levelOfDetailFromTransform(self.transform())
        factor = self.maxZoomFactor()

        if factor < 0.9 and zoom > 0.15:
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

    def polygonMousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if len(self.sketch.coordinates) > 2:
                deviation = 12
                canvasPoint = self.toCanvasCoordinates(*self.sketch.coordinates[0])
                initPoint = self.mapFromScene(*canvasPoint)
                dx = abs(event.pos().x() - initPoint.x())
                dy = abs(event.pos().y() - initPoint.y())

                if dx < deviation and dy < deviation:
                    self.sketch.clip()

            if not self.sketch.done and len(self.sketch.coordinates) < self.sketch.maxPoint:
                self.sketch.append(event.pos())

        if event.button() == Qt.RightButton:
            self.sketch.pop()

    def rectangularMousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.pos = event.pos()
            self.rubberBand.setGeometry(QRect(self.pos, QSize()))
            self.rubberBand.show()
            self.sketch.append(event.pos())

        if event.button() == Qt.RightButton:
            self.sketch.pop()

    def circleMousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.sketch.append(event.pos())

        if event.button() == Qt.RightButton:
            self.sketch.pop()

    def corridorMousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
           self.sketch.append(event.pos())

        if event.button() == Qt.RightButton:
            self.sketch.pop()

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
        self.setDragMode(QGraphicsView.NoDrag)

        if self.lock and self.mode == 'rectangular' and event.button() == Qt.LeftButton:
            self.rubberBand.hide()
            self.sketch.append(event.pos())
            self.sketch.clip()

        super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        if self.lock:
            if self.mode in ['circle', 'corridor']:
                ratio = 1 if event.angleDelta().y() > 0 else -1
                self.sketch.resize(ratio)
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

    def groundResolution(self, latitude):
        resolution = math.cos(latitude * math.pi / 180) * 2 * math.pi * 6378137 / self.scene.width()
        return resolution

    def setMode(self, mode):
        self.mode = mode
        self.sketch.clear()

    def setType(self, key):
        needToResetSketch = key != 'forecast' and self.type == 'forecast'
        self.type = key

        if needToResetSketch:
            # clear last sketch
            self.sketchManager.last().clear()

    def isDefaultLocationFinished(self):
        # shoud check the shape can be encode to text
        sketch = self.sketchManager.first()
        return sketch.done

    def updateCoastline(self):
        if self.coastlines:
            self.coastlines = []
            self.scene.removeItem(self.coastlinesGroup)

        filename = os.path.join(root, 'shapes', 'coastline.shp')
        sf = shapefile.Reader(filename)
        shapes = sf.shapes()
        extent = context.fir.maxLayerExtent()
        if extent:
            bound = shapely.geometry.box(*extent)
        else:
            bound = None

        for polygons in shapes:
            polygons = shapely.geometry.shape(polygons)
            if bound:
                polygons = bound.intersection(polygons)
            if polygons.geom_type == 'Polygon':
                polygons = [polygons]
            for shape in polygons:
                if not shape.is_empty:
                    gemoetry = {
                        'type': 'Polygon',
                        'coordinates': shape.exterior.coords
                    }
                    p = Coastline(gemoetry)
                    p.addTo(self, self.coastlines)

        self.coastlinesGroup = self.scene.createItemGroup(self.coastlines)
        self.setSceneRect(self.scene.itemsBoundingRect())

    def updateLayer(self):
        layer = context.fir.currentLayer()
        if layer:
            background = BackgroundImage(layer)
            background.addTo(self, self.backgrounds)

            self.backgroundsGroup = self.scene.createItemGroup(self.backgrounds)
            self.backgroundsGroup.setZValue(-1)

    def drawBoundaries(self):
        geometry = {
            'type': 'Polygon',
            'coordinates': context.fir.boundaries()
        }
        p = Fir(geometry)
        p.addTo(self, self.firs)

        self.firsGroup = self.scene.createItemGroup(self.firs)
        self.centerOn(self.firsGroup.boundingRect().center())

    def drawSigmets(self, sigmets):
        for sig in sigmets:
            parser = sig.parser()
            geo = parser.geo(context.fir.boundaries())
            p = Sigmet(geo=geo)
            p.addTo(self, self.sigmets)
        
        self.sigmetsGroup = self.scene.createItemGroup(self.sigmets)
        self.sigmetsGroup.setZValue(1)

    def redraw(self):
        self.updateCoastline()
        self.drawBoundaries()

    def clear(self):
        self.sketchManager.clear()

    def showEvent(self, event):
        extent = context.fir.maxLayerExtent()
        if extent != self.maxLayerExtent:
            self.maxLayerExtent = extent
            self.updateCoastline()


class GraphicsWindow(QWidget):

    sketchChanged = pyqtSignal(list)

    def __init__(self, parent=None):
        super(GraphicsWindow, self).__init__()
        self.canvas = Canvas()
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

        self.operationLayout = QHBoxLayout()
        self.operationLayout.addWidget(self.layerButton)
        self.operationLayout.addWidget(self.fcstButton)
        self.operationLayout.addWidget(self.modeButton)
        self.operationLayout.setGeometry(QRect(700, 16, 90, 30))

        self.positionLabel = QLabel(self)
        self.positionLabel.setAttribute(Qt.WA_TransparentForMouseEvents)

        self.showSigmet = True
        self.trimShapes = True

        self.setLayersMenu()
        self.setModeButton()
        self.load()
        self.bindSignal()

    def bindSignal(self):
        self.zoomOutButton.clicked.connect(self.canvas.zoomOut)
        self.zoomInButton.clicked.connect(self.canvas.zoomIn)
        self.modeButton.clicked.connect(self.nextMode)
        self.fcstButton.clicked.connect(self.switchLocationType)
        self.canvas.mouseMoved.connect(self.updatePositionLabel)

        self.canvas.sketchManager.first().finished.connect(self.setFcstButton)

        for sketch in self.canvas.sketchManager:
            sketch.changed.connect(lambda: self.sketchChanged.emit(self.drawingText()))

    def drawingText(self):
        messages = []
        for s in self.canvas.sketchManager.sketchs:
            messages.append(s.text())

        return messages

    def location(self):
        locations = {}
        names = ['location', 'forecastLocation']

        for i, sketch in enumerate(self.canvas.sketchManager.sketchs):
            if sketch.done:
                locations[names[i]] = sketch.text()

        return locations

    def hasAcceptableGraphic(self):
        default = self.canvas.sketchManager.first()
        forecast = self.canvas.sketchManager.last()

        sketchs = [default.done and default.text()]
        if self.canvas.type == 'forecast':
            sketchs.append(forecast.done and forecast.text())

        return all(sketchs)

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
        else:
            self.canvas.lock = True

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

    def updateTyphoonGraphic(self, circle):
        drawing = self.canvas.drawings['default']
        drawing.updateCircle(circle)

    def updateSigmetGraphic(self, sigmets):
        self.canvas.drawSigmets(sigmets)

    def updateLayer(self):
        self.canvas.updateLayer()

    def updateCoastline(self):
        self.canvas.updateCoastline()

    def resizeEvent(self, event):
        self.positionLabel.move(self.width() - self.positionLabel.width(), self.height() - self.positionLabel.height() - 10)
        super(GraphicsWindow, self).resizeEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Control:
            self.canvas.lock = True

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_Control:
            self.canvas.lock = False

    def load(self):
        self.canvas.redraw()

    def clear(self):
        self.canvas.clear()

