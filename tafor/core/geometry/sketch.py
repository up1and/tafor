"""Geometry model classes for hand-drawn areas on the map.

Each subclass implements a specific drawing mode (polygon, line, circle,
corridor, rectangular, entire) and emits signals on state changes.
"""
from tafor.core.events import Signal
from tafor.core.geometry.algorithm import (
    buffer, circle, clipLine, clipPolygon, depth, encode, flattenLine,
    simplifyPolygon, wgs84, geodesicDistance
)
from tafor.core.geometry.coordinate import decimalToDegree


def mergeGeometries(geometries):
    collections = {
        'type': 'GeometryCollection',
        'geometries': []
    }
    for geometry in geometries:
        if geometry:
            collections['geometries'].append(geometry)
    return collections


class Sketch:

    maxPoint = 7

    def __init__(self, name):
        self.name = name
        self.coordinates = []
        self.radius = 0
        self.done = False
        self.stickers = []
        self.changed = Signal()
        self.finished = Signal()

    def __bool__(self):
        return bool(self.coordinates)

    def addPoint(self, lonlat):
        pass

    def removePoint(self):
        pass

    def clip(self, boundaries):
        pass

    def resize(self, ratio):
        pass

    def restore(self, **kwargs):
        raise NotImplementedError

    def geometry(self):
        raise NotImplementedError

    def text(self, boundaries):
        raise NotImplementedError

    def empty(self):
        self.done = False
        self.radius = 0
        self.coordinates = []
        self.stickers = []

    def clear(self):
        self.empty()
        self.finished.emit()
        self.changed.emit()


class PathSketch(Sketch):

    def addPoint(self, lonlat):
        if self.done:
            return
        if len(self.coordinates) < self.maxPoint:
            self.coordinates.append(lonlat)
            self.changed.emit()

    def removePoint(self):
        if self.done:
            self.coordinates = self.editableCoordinates()
            self.done = False
            self.radius = 0
        elif self.coordinates:
            self.coordinates.pop()
        if self.stickers:
            self.stickers = []
        self.changed.emit()


class PolygonSketch(PathSketch):

    def clip(self, boundaries):
        self.coordinates = clipPolygon(boundaries, self.coordinates, mode='single')
        self.coordinates = simplifyPolygon(self.coordinates, maxPoint=self.maxPoint, extend=True)
        self.coordinates.reverse()
        self.done = len(self.coordinates) > 2
        self.finished.emit()
        self.changed.emit()

    def editableCoordinates(self):
        return self.coordinates[:self.maxPoint]

    def geometry(self):
        geometries = []
        if not self.done:
            if len(self.coordinates) == 1:
                geometries = [{'type': 'Point', 'coordinates': self.coordinates[0]}]
            elif len(self.coordinates) > 1:
                geometries = [{'type': 'LineString', 'coordinates': self.coordinates}]
        else:
            geometries = [{'type': 'Polygon', 'coordinates': self.coordinates}]
        return {'type': 'GeometryCollection', 'geometries': geometries}

    def text(self, boundaries):
        points = [(decimalToDegree(lon, fmt='longitude'), decimalToDegree(lat))
                  for lon, lat in self.coordinates]
        if self.done:
            coords = ['{} {}'.format(p[1], p[0]) for p in points]
            return 'WI ' + ' - '.join(coords)
        else:
            coords = ['{} {}'.format(p[1], p[0]) for p in points]
            return ' - '.join(coords)

    def restore(self, coordinates=None):
        if coordinates:
            self.coordinates = coordinates
            self.done = True
            self.finished.emit()
            self.changed.emit()


class LineSketch(PathSketch):

    def clip(self, boundaries):
        self.coordinates = clipPolygon(boundaries, self.coordinates, mode='multi')
        if depth(self.coordinates) > 1:
            self.done = True
        else:
            self.done = len(self.coordinates) > 2
        self.finished.emit()
        self.changed.emit()

    def editableCoordinates(self):
        if depth(self.coordinates) > 1:
            return self.coordinates[0]
        return self.coordinates[:self.maxPoint]

    def geometry(self):
        geometries = []
        if not self.done:
            if len(self.coordinates) == 1:
                geometries = [{'type': 'Point', 'coordinates': self.coordinates[0]}]
            elif len(self.coordinates) > 1:
                geometries = [{'type': 'LineString', 'coordinates': self.coordinates}]
        else:
            if depth(self.coordinates) > 1:
                shapeType = 'MultiPolygon'
            else:
                shapeType = 'Polygon'
            geometries = [{'type': shapeType, 'coordinates': self.coordinates}]
        return {'type': 'GeometryCollection', 'geometries': geometries}

    def text(self, boundaries):
        points = [(decimalToDegree(lon, fmt='longitude'), decimalToDegree(lat))
                  for lon, lat in self.coordinates]
        if self.done:
            area = encode(boundaries, self.coordinates, mode='line')
            lines = []
            for identifier, *pts in area:
                pts = [(decimalToDegree(lon, fmt='longitude'), decimalToDegree(lat))
                       for lon, lat in pts]
                coords = []
                for lon, lat in pts:
                    coords.append('{} {}'.format(lat, lon))
                line = '{} OF LINE {}'.format(identifier, ' - '.join(coords))
                lines.append(line)
            return ' AND '.join(lines)
        else:
            coords = ['{} {}'.format(p[1], p[0]) for p in points]
            return ' - '.join(coords)

    def restore(self, coordinates=None):
        if coordinates:
            self.coordinates = coordinates
            self.done = True
            self.finished.emit()
            self.changed.emit()


class CircleSketch(Sketch):

    deviation = 5000

    def addPoint(self, lonlat):
        self.coordinates.append(lonlat)

        if len(self.coordinates) == 2:
            self.completeFromTwoPoints()
            self.finished.emit()

        if self.radius and len(self.coordinates) == 1:
            lon, lat, _ = wgs84.fwd(self.coordinates[0][0], self.coordinates[0][1],
                                     0, self.radius)
            self.coordinates.append((lon, lat))
            self.done = True
            self.finished.emit()

        self.changed.emit()

    def completeFromTwoPoints(self):
        dist = geodesicDistance(self.coordinates[0], self.coordinates[1])
        self.radius = round(dist / self.deviation) * self.deviation
        lon, lat, _ = wgs84.fwd(self.coordinates[0][0], self.coordinates[0][1],
                                 0, self.radius)
        self.coordinates[-1] = (lon, lat)
        self.done = True

    def removePoint(self):
        if self.done:
            self.coordinates.pop()
            self.radius = 0
            self.done = False
        elif self.coordinates:
            self.coordinates.pop()
        if self.stickers:
            self.stickers = []
        self.changed.emit()

    def resize(self, ratio):
        if not self.done:
            return
        if ratio > 0 or self.radius > self.deviation * 4:
            self.radius += self.deviation * ratio
            lon, lat, _ = wgs84.fwd(self.coordinates[0][0], self.coordinates[0][1],
                                     0, self.radius)
            self.coordinates[-1] = [lon, lat]
            self.changed.emit()

    def geometry(self):
        geometries = []
        if self.done:
            polygon = circle(self.coordinates[0], self.radius)
            geometries = [
                {'type': 'Polygon', 'coordinates': list(polygon.exterior.coords)},
                {'type': 'Point', 'coordinates': self.coordinates[0]},
            ]
        elif self.coordinates:
            geometries = [{'type': 'Point', 'coordinates': self.coordinates[0]}]
        return {'type': 'GeometryCollection', 'geometries': geometries}

    def text(self, boundaries):
        points = [(decimalToDegree(lon, fmt='longitude'), decimalToDegree(lat))
                  for lon, lat in self.coordinates]
        if self.done:
            center = points[0]
            msg = 'PSN {} {}'.format(center[1], center[0])
            if self.name == 'initial':
                msg += ' / WI {}{} OF CENTRE'.format(round(self.radius / 1000), 'KM')
            return msg
        else:
            coords = ['{} {}'.format(p[1], p[0]) for p in points]
            return ' - '.join(coords)

    def restore(self, center=None, radius=None):
        self.done = False
        if center:
            self.coordinates = [center]
        else:
            self.coordinates = []

        if radius:
            self.radius = int(radius) * 1000
        else:
            self.radius = 0

        if center and radius:
            lon, lat, _ = wgs84.fwd(center[0], center[1], 0, self.radius)
            self.coordinates.append((lon, lat))
            self.done = True

        self.finished.emit()
        self.changed.emit()

    def feature(self):
        return {
            'type': 'Feature',
            'geometry': {
                'type': 'Point',
                'coordinates': self.coordinates[0] if self.coordinates else (),
            },
            'properties': {
                'radius': round(self.radius / 1000),
                'location': self.name,
            },
        }


class CorridorSketch(PathSketch):

    maxPoint = 4
    deviation = 5000

    def removePoint(self):
        if self.done:
            self.radius = 0
            self.done = False
        elif self.coordinates:
            self.coordinates.pop()
        if self.stickers:
            self.stickers = []
        self.changed.emit()

    def resize(self, ratio):
        if not self.done:
            return

        if ratio > 0:
            polygon = buffer(self.coordinates, self.radius + self.deviation * ratio)
            if len(self.coordinates) * 2 + 1 == len(polygon.exterior.coords):
                self.radius += self.deviation * ratio
                self.changed.emit()
        elif ratio < 0 and self.radius > self.deviation:
            self.radius += self.deviation * ratio
            self.changed.emit()

    def clip(self, boundaries):
        if self.done:
            return

        if len(self.coordinates) > 1:
            self.coordinates = clipLine(boundaries, self.coordinates)
            if len(self.coordinates) > 1:
                self.radius = self.deviation
                self.done = True
                self.finished.emit()
            else:
                self.radius = 0
                self.done = False

            self.changed.emit()

    def editableCoordinates(self):
        return self.coordinates

    def geometry(self):
        geometries = []
        if not self.done:
            if len(self.coordinates) == 1:
                geometries = [{'type': 'Point', 'coordinates': self.coordinates[0]}]
            elif len(self.coordinates) > 1:
                geometries = [{'type': 'LineString', 'coordinates': self.coordinates}]
        else:
            polygon = buffer(self.coordinates, self.radius)
            geometries = [{
                'type': 'Polygon',
                'coordinates': list(polygon.exterior.coords),
            }]
        return {'type': 'GeometryCollection', 'geometries': geometries}

    def text(self, boundaries):
        points = [(decimalToDegree(lon, fmt='longitude'), decimalToDegree(lat))
                  for lon, lat in self.coordinates]
        if self.done:
            coords = ['{} {}'.format(p[1], p[0]) for p in points]
            line = ' - '.join(coords)
            return 'APRX {}{} WID LINE BTN {}'.format(
                round(self.radius * 2 / 1000), 'KM', line)
        else:
            coords = ['{} {}'.format(p[1], p[0]) for p in points]
            return ' - '.join(coords)

    def restore(self, coordinates=None, radius=None):
        if coordinates:
            self.coordinates = coordinates
        if radius:
            self.radius = int(radius) * 1000 / 2
        if coordinates and radius:
            self.done = True
            self.finished.emit()
            self.changed.emit()


class RectangularSketch(Sketch):

    def addPoint(self, lonlat):
        self.coordinates.append(lonlat)
        if len(self.coordinates) == 2:
            self.done = True
            self.finished.emit()
        self.changed.emit()

    def removePoint(self):
        self.coordinates = []
        self.done = False
        if self.stickers:
            self.stickers = []
        self.changed.emit()

    def clip(self, boundaries):
        if len(self.coordinates) == 2:
            topLeft, bottomRight = self.coordinates
            topRight = [bottomRight[0], topLeft[1]]
            bottomLeft = [topLeft[0], bottomRight[1]]
            polygon = [topLeft, topRight, bottomRight, bottomLeft]
            self.coordinates = clipPolygon(boundaries, polygon, mode='multi')
            self.done = True

        if depth(self.coordinates) > 1:
            self.done = True
        else:
            self.done = len(self.coordinates) > 2

        self.finished.emit()
        self.changed.emit()

    def geometry(self):
        if not self.done:
            return {'type': 'GeometryCollection', 'geometries': []}
        if depth(self.coordinates) > 1:
            shapeType = 'MultiPolygon'
        else:
            shapeType = 'Polygon'
        geometries = [{'type': shapeType, 'coordinates': self.coordinates}]
        return {'type': 'GeometryCollection', 'geometries': geometries}

    def text(self, boundaries):
        if depth(self.coordinates) > 1:
            self.done = True
        else:
            self.done = len(self.coordinates) > 2

        if self.done:
            area = encode(boundaries, self.coordinates, mode='rectangular')
            lines = []
            for identifier, *pts in area:
                pts = [(decimalToDegree(lon, fmt='longitude'), decimalToDegree(lat))
                       for lon, lat in pts]
                lonlat = flattenLine(pts)
                if lonlat:
                    line = '{} OF {}'.format(identifier, lonlat)
                    lines.append(line)
            return ' AND '.join(lines)
        return ''

    def restore(self, coordinates=None):
        if coordinates:
            self.coordinates = coordinates
            self.done = True
            self.finished.emit()
            self.changed.emit()


class EntireSketch(Sketch):

    def geometry(self):
        if self.done:
            geometries = [{'type': 'Polygon', 'coordinates': self.coordinates}]
        else:
            geometries = []
        return {'type': 'GeometryCollection', 'geometries': geometries}

    def text(self, boundaries):
        return 'ENTIRE FIR' if self.done else ''

    def restore(self, boundaries=None):
        if boundaries:
            self.coordinates = list(boundaries)
            self.done = True
            self.finished.emit()
            self.changed.emit()
