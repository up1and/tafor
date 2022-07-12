from turtle import shape
import shapely

from PyQt5.QtGui import QPen, QColor, QBrush, QPolygonF, QPainterPath, QPixmap, QFont, QPainter
from PyQt5.QtCore import Qt, QPointF, QRectF
from PyQt5.QtWidgets import QGraphicsItem, QGraphicsPolygonItem, QGraphicsPixmapItem, QWidget


class CanvasMixin(object):

    def toCanvasCoordinates(self, canvas, lonlats):
        coordinates = QPolygonF()
        for lon, lat in lonlats:
            px, py = canvas.toCanvasCoordinates(lon, lat)
            if px > 1e+10:
                continue
            coordinates.append(QPointF(px, py))

        if len(coordinates) == 1:
            coordinates = coordinates[0]
        
        return coordinates

    def toCanvasGeometry(self, canvas, geometry):
        lonlats = geometry['coordinates']
        if geometry['type'] == 'Point':
            lonlats = [lonlats]

        points = []
        for lon, lat in lonlats:
            px, py = canvas.toCanvasCoordinates(lon, lat)
            if px > 1e+10:
                continue
            points.append(QPointF(px, py))

        if geometry['type'] == 'Point':
            shape = points[0]

        if geometry['type'] == 'LineString':
            shape = QPainterPath()
            for i, p in enumerate(points):
                if i == 0:
                    shape.moveTo(p)

                shape.lineTo(p)

        if geometry['type'] == 'Polygon':
            shape = QPolygonF(points)

        return shape


class ColorMixin(object):

    def findPalette(self, hazard, location):
        brushes = {
            'ts': QBrush(QColor(240, 156, 0, 100)),
            'turb': QBrush(QColor(37, 238, 44, 100)),
            'ice': QBrush(QColor(67, 255, 255, 100)),
            'ash': QBrush(QColor(250, 0, 25, 100)),
            'typhoon': QBrush(QColor(250, 50, 250, 100)),
            'other': QBrush(QColor(250, 250, 50, 100))
        }

        palettes = {
            'initial': [QPen(QColor(204, 204, 204), 1, Qt.DashLine), brushes.get(hazard, brushes['other'])],
            'final': [QPen(QColor(204, 204, 204, 150), 1, Qt.DashLine), QBrush(QColor(154, 205, 50, 70))]
        }

        return palettes[location]


class Polygon(QGraphicsPolygonItem, CanvasMixin):

    def __init__(self, geometry):
        super(Polygon, self).__init__()
        self.geometry = geometry

    def addTo(self, canvas, group):
        polygon = self.toCanvasGeometry(canvas, self.geometry)
        self.setPolygon(polygon)
        group.append(self)


class Country(Polygon):

    def __init__(self, geometry):
        super(Country, self).__init__(geometry)
        self.pen = QPen(QColor(130, 130, 130))
        self.brush = QBrush(QColor(219, 219, 219))
        self.setPen(self.pen)
        self.setBrush(self.brush)


class Coastline(Polygon):

    def __init__(self, geometry):
        super(Coastline, self).__init__(geometry)
        self.geometry = geometry
        self.setZValue(1)
        # self.pen = QPen(QColor(130, 130, 130))
        # self.setPen(self.pen)


class BackgroundImage(QGraphicsPixmapItem):

    def __init__(self, layer, opacity=1):
        super(BackgroundImage, self).__init__()
        self.layer = layer
        self.setZValue(-1)
        self.setTransformationMode(Qt.SmoothTransformation)
        self.setOpacity(opacity)

    def addTo(self, canvas, group):
        raw = QPixmap()
        raw.loadFromData(self.layer.image)
        minx, miny, maxx, maxy = canvas.extentBound(self.layer.extent)
        width = abs(maxx - minx)
        height = abs(maxy - miny)
        raw = raw.scaled(width, height)
        self.setPixmap(raw)
        self.setPos(minx, maxy)
        group.append(self)


class Fir(Polygon):

    def __init__(self, geometry):
        super(Fir, self).__init__(geometry)
        pen = QPen(QColor(200, 200, 200), 2)
        self.setPen(pen)


class SketchGraphic(QGraphicsItem, CanvasMixin):

    def __init__(self, geo=None):
        super(SketchGraphic, self).__init__()
        self.geo = geo
        self.geometries = []

    def boundingRect(self):
        rect = QRectF()
        for g in self.geometries:
            if isinstance(g, QPointF):
                grect = QRectF(g.x(), g.y(), 1, 1).normalized()
            else:
                grect = g.boundingRect()
            rect = rect.united(grect)
        return rect

    def paint(self, painter, option, widget):
        defaultBrush = painter.brush()
        for g in self.geometries:
            if isinstance(g, QPointF):
                radius = 2
                painter.setPen(QPen(QColor(0, 0, 0, 127), 1))
                painter.setBrush(QBrush(Qt.white, 1))
                painter.drawEllipse(g.x() - radius, g.y() - radius, radius * 2.0, radius * 2.0)

            if isinstance(g, QPolygonF):
                colors = {
                    'initial': QColor(240, 156, 0, 178),
                    'final': QColor(154, 205, 50, 100)
                }
                color = colors[g.properties['location']]
                brush = QBrush(color)
                painter.setBrush(brush)
                painter.setPen(QPen(Qt.white))
                painter.drawPolygon(g)

            if isinstance(g, QPainterPath):
                painter.setBrush(defaultBrush)
                painter.setPen(QPen(Qt.white, 3))
                painter.drawPath(g)
                painter.setPen(QPen(QColor(0, 0, 0, 127), 2, Qt.DashLine))
                painter.drawPath(g)

    def updateGeometry(self, geo, canvas):
        self.geo = geo
        self.geometries = []
        for i, geo in enumerate(self.geo['geometries']):
            geometries = []
            if geo['type'] == 'MultiPolygon':
                for coords in geo['coordinates']:
                    geometries.append({
                        'type': 'Polygon',
                        'coordinates': coords
                })
            else:
                geometries = [geo]

            location = 'initial' if i == 0 else 'final'
            properties = {'location': location}

            for geometry in geometries:
                shape = self.toCanvasGeometry(canvas, geometry)
                shape.properties = properties
                self.geometries.append(shape)


class Sigmet(QGraphicsItem, CanvasMixin, ColorMixin):

    def __init__(self, geo):
        super(Sigmet, self).__init__()
        self.geo = geo
        self.geometries = []

    def boundingRect(self):
        rect = QRectF()
        for g in self.geometries:
            rect = rect.united(g.boundingRect())
        return rect

    def paint(self, painter, option, widget):
        for geo in self.geometries:
            hazard = geo.properties['hazard']
            location = geo.properties['location']
            pen, brush = self.findPalette(hazard, location)
            painter.setPen(pen)
            painter.setBrush(brush)
            painter.drawPolygon(geo)

            if location == 'initial':
                sequence = geo.properties['sequence']
                path = QPainterPath()
                font = QFont()
                font.setBold(True)
                font.setPointSize(16)
                path.addText(geo.boundingRect().center(), font, sequence)
                pen = QPen(QColor(0, 0, 0, 120))
                brush = QBrush(Qt.white)
                painter.strokePath(path, pen)
                painter.fillPath(path, brush)

    def addTo(self, canvas, group):
        for feature in self.geo['features']:
            if feature['geometry']['type'] == 'Polygon':
                polygons = [feature['geometry']['coordinates']]
            else:
                polygons = feature['geometry']['coordinates']

            for polygon in polygons:
                geometry = {'type': 'Polygon', 'coordinates': polygon}
                geo = self.toCanvasGeometry(canvas, geometry)
                geo.properties = feature['properties']
                self.geometries.append(geo)
                
        group.append(self)


class SigmetBackground(QWidget, ColorMixin):

    def __init__(self, geo, parent=None):
        super().__init__(parent)
        self.setFixedSize(200, 120)
        self.parent = parent
        self.geo = geo
        self.geometries = []
        self.fitSize()

    def toCanvasCoordinates(self, lonlats):
        poly = shapely.geometry.Polygon(lonlats)
        poly = shapely.affinity.scale(poly, xfact=self.ratio, yfact=-self.ratio, origin=self.centroid)
        poly = shapely.affinity.translate(poly, 
            xoff=-self.rect.x() + self.width() / 2, yoff=-self.rect.y() + self.height() / 2)

        polygon = QPolygonF()
        for p in poly.exterior.coords:
            polygon.append(QPointF(*p))

        return polygon

    def fitSize(self):

        def toPolygons(feature):
            if feature['geometry']['type'] == 'Polygon':
                polygons = [feature['geometry']['coordinates']]
            else:
                polygons = feature['geometry']['coordinates']

            return polygons

        box = shapely.geometry.Polygon()
        for feature in self.geo['features']:
            polygons = toPolygons(feature)
            for polygon in polygons:
                geom = shapely.geometry.Polygon(polygon)
                box = box.union(geom)

        rect = box.envelope
        self.centroid = rect.centroid
        minx, miny, maxx, maxy = rect.bounds
        self.rect = QRectF(minx, miny, maxx - minx, maxy - miny)
        self.ratio = min(self.width() / self.rect.width(), self.height() / self.rect.height())

        self.geometries = []
        for feature in self.geo['features']:
            polygons = toPolygons(feature)
            for polygon in polygons:
                geom = self.toCanvasCoordinates(polygon)
                geom.properties = feature['properties']
                self.geometries.append(geom)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)

        for geo in self.geometries:
            hazard = geo.properties['hazard']
            location = geo.properties['location']
            _, brush = self.findPalette(hazard, location)
            painter.setPen(Qt.NoPen)
            painter.setBrush(brush)
            painter.drawPolygon(geo)
