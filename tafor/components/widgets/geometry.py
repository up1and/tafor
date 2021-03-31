from PyQt5.QtGui import QPen, QColor, QPolygon, QBrush, QPolygonF, QPainterPath, QPixmap
from PyQt5.QtCore import Qt, QPoint, QPointF
from PyQt5.QtWidgets import QGraphicsPolygonItem, QGraphicsEllipseItem, QGraphicsPathItem, QGraphicsLineItem, QGraphicsPixmapItem


class PlottedPoint(QGraphicsEllipseItem):

    def __init__(self, center, radius=2):
        super(PlottedPoint, self).__init__()
        self.setRect(center.x() - radius, center.y() - radius, radius * 2.0, radius * 2.0)
        self.setPen(QPen(QColor(0, 0, 0, 127), 1))
        self.setBrush(QBrush(Qt.white, 1))


class PlottedCircle(QGraphicsEllipseItem):

    def __init__(self, center, radius, color=Qt.yellow):
        super(PlottedCircle, self).__init__()
        self.setRect(center.x() - radius, center.y() - radius, radius * 2.0, radius * 2.0)
        self.setPen(QPen(Qt.white))
        self.setBrush(QBrush(color))


class PlottedLine(QGraphicsLineItem):

    def __init__(self, point1, point2):
        super(PlottedLine, self).__init__()
        self.setLine(point1.x(), point1.y(), point2.x(), point2.y())
        self.setPen(QPen(Qt.white, 1, Qt.DashLine))


class PlottedShadowLine(QGraphicsLineItem):

    def __init__(self, point1, point2):
        super(PlottedShadowLine, self).__init__()
        self.setLine(point1.x(), point1.y(), point2.x(), point2.y())
        self.setPen(QPen(QColor(0, 0, 0, 127), 2))


class PlottedPolygon(QGraphicsPolygonItem):

    def __init__(self, coordinates, color=Qt.yellow):
        super(PlottedPolygon, self).__init__()
        polygon = QPolygonF()
        for p in coordinates:
            polygon.append(p)

        self.setPolygon(polygon)
        brush = QBrush(color)
        self.setBrush(brush)
        self.setPen(QPen(Qt.white))


class Polygon(QGraphicsPolygonItem):

    def __init__(self, lonlats):
        super(Polygon, self).__init__()
        self.lonlats = lonlats
        self.setZValue(1)

    def addTo(self, canvas, group):
        self.coordinates = QPolygonF()
        for lon, lat in self.lonlats:
            px, py = canvas.toCanvasCoordinates(lon, lat)
            if px > 1e+10:
                continue
            self.coordinates.append(QPointF(px, py))

        self.setPolygon(self.coordinates)
        group.append(self)


class Country(Polygon):

    def __init__(self, lonlats):
        super(Country, self).__init__(lonlats)
        self.pen = QPen(QColor(130, 130, 130))
        self.brush = QBrush(QColor(219, 219, 219))
        self.setPen(self.pen)
        self.setBrush(self.brush)


# class Coastline(Polygon):

#     def __init__(self, lonlats):
#         super(Coastline, self).__init__(lonlats)
#         self.pen = QPen(QColor(130, 130, 130))
#         self.setPen(self.pen)


class Coastline(QGraphicsPathItem):

    def __init__(self, lonlats):
        super(Coastline, self).__init__()
        self.lonlats = lonlats
        self.setZValue(1)
        # self.pen = QPen(QColor(130, 130, 130))
        # self.setPen(self.pen)

    def addTo(self, canvas, group):
        path = QPainterPath()
        for i, (lon, lat) in enumerate(self.lonlats):
            px, py = canvas.toCanvasCoordinates(lon, lat)
            if px > 1e+10:
                continue

            if i == 0:
                path.moveTo(QPointF(px, py))

            path.lineTo(QPointF(px, py))

        self.setPath(path)
        group.append(self)


class BackgroundImage(QGraphicsPixmapItem):

    def __init__(self, layer):
        super(BackgroundImage, self).__init__()
        self.layer = layer
        self.setZValue(-1)
        self.setTransformationMode(Qt.SmoothTransformation)

    def addTo(self, canvas, group):
        raw = QPixmap()
        raw.loadFromData(self.layer.image)
        # print(raw.size())
        minx, miny, maxx, maxy = canvas.extentBound(self.layer.extent)
        width = abs(maxx - minx)
        height = abs(maxy - miny)
        raw = raw.scaled(width, height)
        print(width, height)
        self.setPixmap(raw)
        # height has -15 pixels offset, don't know why
        self.setPos(minx, maxy)
        group.append(self)


class Fir(Polygon):

    def __init__(self, lonlats):
        super(Fir, self).__init__(lonlats)
        self.pen = QPen(QColor(255, 255, 255))
        # self.brush = QBrush(QColor(255, 255, 255, 75))
        self.setPen(self.pen)
        # self.setBrush(self.brush)


class SigmetLocation(Polygon):

    def __init__(self, lonlats):
        super(SigmetLocation, self).__init__(lonlats)
        self.pen = QPen(QColor(128, 128, 128))
        self.brush = QBrush(QColor(255, 255, 255, 75))
        self.setPen(self.pen)
        self.setBrush(self.brush)
        
