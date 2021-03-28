from PyQt5.QtGui import QPen, QColor, QPolygon, QBrush, QPolygonF, QPainterPath
from PyQt5.QtCore import Qt, QPoint, QPointF
from PyQt5.QtWidgets import QGraphicsPolygonItem, QGraphicsEllipseItem, QGraphicsPathItem, QGraphicsLineItem


class PlottedPoint(QGraphicsEllipseItem):

    def __init__(self, center, radius=2):
        super(PlottedPoint, self).__init__()
        self.setRect(center.x() - radius, center.y() - radius, radius * 2.0, radius * 2.0)
        self.setPen(QPen(QColor(0, 0, 0, 127), 1))
        self.setBrush(QBrush(Qt.white, 1))


class PlottedCircle(QGraphicsEllipseItem):

    def __init__(self, center, radius):
        super(PlottedCircle, self).__init__()
        self.setRect(center.x() - radius, center.y() - radius, radius * 2.0, radius * 2.0)
        self.setPen(QPen(Qt.white))
        self.setBrush(QBrush(QColor(240, 156, 0, 178)))


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

    def __init__(self, coordinates):
        super(PlottedPolygon, self).__init__()
        polygon = QPolygonF()
        for p in coordinates:
            polygon.append(p)

        self.setPolygon(polygon)
        brush = QBrush(QColor(240, 156, 0, 178))
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


class Fir(Polygon):

    def __init__(self, lonlats):
        super(Fir, self).__init__(lonlats)
        self.pen = QPen(QColor(128, 128, 128))
        self.brush = QBrush(QColor(255, 255, 255, 75))
        self.setPen(self.pen)
        self.setBrush(self.brush)
