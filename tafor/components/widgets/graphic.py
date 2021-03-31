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
    QActionGroup, QAction, QSpacerItem, QSizePolicy, QGraphicsPixmapItem)
from PyQt5.QtGui import QIcon, QPainter, QPolygonF, QBrush, QPen, QColor, QPixmap
from PyQt5.QtCore import QCoreApplication, QObject, QPoint, QPointF, Qt, QRect, QRectF, QSize, QSizeF, pyqtSignal

from tafor import root
from tafor.states import context
from tafor.utils.convert import listToPoint, pointToList, decimalToDegree, degreeToDecimal
from tafor.utils.sigmet import encodeSigmetArea, decodeSigmetLocation, simplifyLine, clipLine, clipPolygon, simplifyPolygon
from tafor.components.widgets.geometry import BackgroundImage, Coastline, Country, Fir, SigmetLocation, PlottedPoint, PlottedCircle, PlottedLine, PlottedShadowLine, PlottedPolygon



def distanceBetweenPoints(point1, point2):
    x = point1.x() - point2.x()
    y = point1.y() - point2.y()
    return math.sqrt(x ** 2 + y ** 2)

def bearing(origin, point):
    return math.atan2(origin.y() - point.y(), origin.x() - point.x())

def centroid(points):
    point = [0, 0]

    if not points:
        return point

    length = len(points)
    for p in points:
        point[0] += p.x()
        point[1] += p.y()

    point = QPointF(point[0] / length, point[1] / length)
    return point

class Drawing(QObject):

    finished = pyqtSignal()
    changed = pyqtSignal()

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
        for lon, lat in context.fir.boundaries():
            px, py = self.canvas.toCanvasCoordinates(lon, lat)
            points.append(self.canvas.mapFromScene(px, py))

        return points

    @property
    def approximateLatitude(self):
        if self.done:
            if self.canvas.mode == 'corridor':
                center = centroid(self.coordinates[:-1])
                center = self.canvas.toGeographicalCoordinates(center.x(), center.y())

            if self.canvas.mode == 'circle':
                center = self.coordinates[0]
                center = self.canvas.toGeographicalCoordinates(center.x(), center.y())

        else:
            center = centroid([QPointF(p[0], p[1]) for p in context.fir.boundaries()])
            center = [center.x(), center.y()]

        return center[1]

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
        # clip the polygon with boundaries
        if self.canvas.mode in ['polygon', 'line']:
            coordinates = [self.canvas.mapFromScene(p) for p in self.coordinates]
            coordinates = clipPolygon(pointToList(self.boundaries), pointToList(coordinates))

            if self.canvas.mode == 'polygon':
                coordinates = simplifyPolygon(coordinates, maxPoint=self.maxPoint, extend=True)
            # make the points clockwise
            coordinates.reverse()
            self.coordinates = [self.canvas.mapToScene(*p) for p in coordinates]
            self.done = True if len(self.coordinates) > 2 else False

        if self.canvas.mode == 'rectangular':
            rect = QRectF(*self.coordinates)
            polygon = [rect.topLeft(), rect.topRight(), rect.bottomRight(), rect.bottomLeft()]
            coordinates = [self.canvas.mapFromScene(p) for p in polygon]
            coordinates = clipPolygon(pointToList(self.boundaries), pointToList(coordinates))
            self.coordinates = [self.canvas.mapToScene(*p) for p in coordinates]
            self.done = True

        self.finished.emit()
        self.redraw()

    def clear(self):
        self.done = False
        self.coordinates = []
        self.finished.emit()
        self.redraw()

    def redraw(self, silent=False):
        items = []

        shapeColors = {
            'default': QColor(240, 156, 0, 178),
            'forecast': QColor(154, 205, 50, 100)
        }

        if self.canvas.mode in ['polygon', 'line', 'corridor']:
            if self.done:
                items.append(PlottedPolygon(self.coords, color=shapeColors[self.canvas.type]))
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
                items.append(PlottedPolygon(self.coordinates, color=shapeColors[self.canvas.type]))

        if self.canvas.mode == 'circle':
            if self.done:
                items.append(PlottedCircle(self.coordinates[0], self.radius, color=shapeColors[self.canvas.type]))
                items.append(PlottedLine(*self.coordinates))
            else:
                if self.coordinates:
                    items.append(PlottedPoint(self.coordinates[0]))

        if self.elements:
            self.canvas.scene.removeItem(self.elements)

        self.elements = self.canvas.scene.createItemGroup(items)

        if not silent:
            self.changed.emit()

    def text(self):
        message = ''

        if self.canvas.mode == 'rectangular':
            # boundaries = context.fir._state['boundaries']
            points = [self.canvas.toGeographicalCoordinates(p.x(), p.y()) for p in self.coordinates]
            area = encodeSigmetArea(context.fir.boundaries(), points, mode='rectangular')

            lines = []
            for identifier, *points in area:
                points = [(decimalToDegree(lng, fmt='longitude'), decimalToDegree(lat)) for lng, lat in points]
                lnglat = simplifyLine(points)

                if lnglat:
                    line = '{} OF {}'.format(identifier, lnglat)
                    lines.append(line)

            message = ' AND '.join(lines)

        if self.canvas.mode == 'line':
            if self.done:
                points = [self.canvas.toGeographicalCoordinates(p.x(), p.y()) for p in self.coordinates]
                area = encodeSigmetArea(context.fir.boundaries(), points, mode='line')

                lines = []
                for identifier, *points in area:
                    points = [(decimalToDegree(lng, fmt='longitude'), decimalToDegree(lat)) for lng, lat in points]
                    coordinates = []
                    for lng, lat in points:
                        coordinates.append('{} {}'.format(lat, lng))

                    line = '{} OF LINE {}'.format(identifier, ' - '.join(coordinates))
                    lines.append(line)

                message = ' AND '.join(lines)
            else:
                points = [self.canvas.toGeographicalCoordinates(p.x(), p.y()) for p in self.coordinates]
                points = [(decimalToDegree(lng, fmt='longitude'), decimalToDegree(lat)) for lng, lat in points]
                coordinates = ['{} {}'.format(p[1], p[0]) for p in points]
                message = ' - '.join(coordinates)

        if self.canvas.mode == 'polygon':
            points = [self.canvas.toGeographicalCoordinates(p.x(), p.y()) for p in self.coordinates]
            points = [(decimalToDegree(lng, fmt='longitude'), decimalToDegree(lat)) for lng, lat in points]
            if self.done:
                coordinates = ['{} {}'.format(p[1], p[0]) for p in points]
                message = 'WI ' + ' - '.join(coordinates)
            else:
                coordinates = ['{} {}'.format(p[1], p[0]) for p in points]
                message = ' - '.join(coordinates)

        if self.canvas.mode == 'corridor':
            points = [self.canvas.toGeographicalCoordinates(p.x(), p.y()) for p in self.coordinates[:-1]]
            points = [(decimalToDegree(lng, fmt='longitude'), decimalToDegree(lat)) for lng, lat in points]
            if self.done:
                unit = 'KM'
                width = self.canvas.groundResolution(self.approximateLatitude) * self.radius / 1000
                width = round(width)
                # width = round(width / 5) * 5
                coordinates = ['{} {}'.format(p[1], p[0]) for p in points]
                line = ' - '.join(coordinates)
                message = 'APRX {}{} WID LINE BTN {}'.format(width, unit, line)
            else:
                coordinates = ['{} {}'.format(p[1], p[0]) for p in points]
                message = ' - '.join(coordinates)

        if self.canvas.mode == 'circle':
            points = [self.canvas.toGeographicalCoordinates(p.x(), p.y()) for p in self.coordinates]
            points = [(decimalToDegree(lng, fmt='longitude'), decimalToDegree(lat)) for lng, lat in points]
            if self.done:
                unit = 'KM'
                radius = self.canvas.groundResolution(self.approximateLatitude) * self.radius / 1000
                radius = round(radius)
                center = points[0]
                items = ['PSN {} {}'.format(center[1], center[0]), 'WI {}{} OF CENTRE'.format(radius, unit)]
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

        # +proj=merc +lon_0=0 +k=1 +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs 
        self.projection = Proj('+proj=eqc +datum=WGS84')
        self.ratio, self.offset = 1/1113, (0, 0)
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

    def extentBound(self, extent):
        minlon, minlat, maxlon, maxlat = extent
        minx, miny = self.toCanvasCoordinates(minlon, minlat)
        maxx, maxy = self.toCanvasCoordinates(maxlon, maxlat)
        return minx, miny, maxx, maxy

    def maxZoomFactor(self):
        extent = [98, 0, 137, 30]
        # extent = context.fir.maxLayerExtent()
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
            if len(self.drawing.coordinates) > 2:
                deviation = 12
                initPoint = self.mapFromScene(self.drawing.coordinates[0])
                dx = abs(event.pos().x() - initPoint.x())
                dy = abs(event.pos().y() - initPoint.y())

                if dx < deviation and dy < deviation:
                    self.drawing.clip()

            if not self.drawing.done and len(self.drawing.coordinates) < self.drawing.maxPoint:
                self.drawing.append(event.pos())

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

        if self.lock and self.mode == 'rectangular' and event.button() == Qt.LeftButton:
            self.rubberBand.hide()
            self.drawing.append(event.pos())
            self.drawing.clip()

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

    def groundResolution(self, latitude):
        resolution = math.cos(latitude * math.pi / 180) * 2 * math.pi * 6378137 / self.scene.width()
        return resolution

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

    def addCoastlines(self):
        filename = os.path.join(root, 'shapes', 'coastline.shp')
        sf = shapefile.Reader(filename)
        shapes = sf.shapes()
        extent = [98, 0, 137, 30]
        bound = shapely.geometry.box(*extent)
        # bound = None

        for polygons in shapes:
            polygons = shapely.geometry.shape(polygons)
            if bound:
                polygons = bound.intersection(polygons)
            if polygons.geom_type == 'LineString':
                polygons = [polygons]
            for shape in polygons:
                if not shape.is_empty:
                    p = Coastline(shape.coords)
                    p.addTo(self, self.coastlines)

    def updateLayer(self):
        layer = context.fir.currentLayer()
        if layer:
            background = BackgroundImage(layer)
            background.addTo(self, self.backgrounds)

            self.backgroundsGroup = self.scene.createItemGroup(self.backgrounds)
            self.backgroundsGroup.setZValue(-1)

    def drawBoundaries(self):
        p = Fir(context.fir.boundaries())
        p.addTo(self, self.firs)

    def drawSigmets(self, sigmets):
        brushes = {
            'ts': QBrush(QColor(240, 156, 0, 100)),
            'turb': QBrush(QColor(37, 238, 44, 100)),
            'ice': QBrush(QColor(67, 255, 255, 100)),
            'ash': QBrush(QColor(250, 0, 25, 100)),
            'typhoon': QBrush(QColor(250, 50, 250, 100)),
            'other': QBrush(QColor(250, 250, 50, 100))
        }

        for i, sig in enumerate(sigmets):
            for key, location in sig['locations'].items():
                if not location:
                    continue

                p = SigmetLocation(location)
                p.addTo(self, self.sigmets)

                points = listToPoint(area)
                pol = QPolygon(points)
                center = Polygon(area).centroid
                met = context.fir.sigmets()[i]
                parser = met.parser()
                sequence = parser.sequence()

                if key == 'default':
                    pen = QPen(QColor(204, 204, 204), 1, Qt.DashLine)
                    brush = brushes.get(sig['phenomenon'], brushes['other'])
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
        
        self.sigmets = self.scene.createItemGroup(self.sigmets)

    def updateDrawing(self):
        self.scene.addItem(self.drawing)

    def redraw(self):
        self.addCoastlines()
        self.drawBoundaries()
        self.polygonsGroup = self.scene.createItemGroup(self.coastlines)
        self.firsGroup = self.scene.createItemGroup(self.firs)

    def clear(self):
        pass


class GraphicsWindow(QWidget):

    drawingChanged = pyqtSignal(dict)

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

        self.showSigmet = True
        self.trimShapes = True

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

        for _, drawing in self.canvas.drawings.items():
            drawing.changed.connect(lambda: self.drawingChanged.emit(self.drawingText()))

    def drawingText(self):
        messages = {}

        for key, drawing in self.canvas.drawings.items():
            messages[key] = [drawing.text(), drawing.done]

        return messages

    def location(self):
        locations = {}
        keynames = {
            'default': 'location',
            'forecast': 'forecastLocation'
        }

        for key, drawing in self.canvas.drawings.items():
            if drawing.done:
                locations[keynames[key]] = drawing.text()

        return locations

    def hasAcceptableGraphic(self):
        default = self.canvas.drawings['default']
        forecast = self.canvas.drawings['forecast']

        drawings = [default.done and default.text()]
        if self.canvas.type == 'forecast':
            drawings.append(forecast.done and forecast.text())

        return all(drawings)

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

    def updateTyphoonGraphic(self, circle):
        drawing = self.canvas.drawings['default']
        drawing.updateCircle(circle)

    def updateSigmetGraphic(self, sigmets):
        infos = []
        for sig in sigmets:
            locations = {}
            parser = sig.parser()
            for key, item in parser.location().items():
                polygon = decodeSigmetLocation(context.fir.boundaries(), item['location'], item['type'], self.trimShapes)
                locations[key] = polygon

            infos.append({
                'phenomenon': parser.phenomenon(),
                'locations': locations
            })

        self.canvas.drawSigmets(infos)

    def updateLayer(self):
        self.canvas.updateLayer()

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

