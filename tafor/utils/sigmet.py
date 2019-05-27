import math

from itertools import chain

from shapely.ops import split
from shapely.geometry import Polygon, LineString, MultiLineString, Point


def centroid(points):
    point = [0, 0]

    if not points:
    	return point

    length = len(points)
    for x, y in points:
        point[0] += x
        point[1] += y

    point = [point[0] / length, point[1] / length]
    return point

def bearing(origin, point):
    return math.atan2(origin[1] - point[1], origin[0] - point[0])

def distance(p1, p2):
    length = (p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2
    return math.sqrt(length)

def perpendicularFoot(p1, p2, p3):
    ratio = ((p3[0]- p1[0]) * (p2[0] - p1[0]) + (p3[1] - p1[1]) * (p2[1] - p1[1])) / ((p2[0] - p1[0]) * (p2[0] - p1[0]) + (p2[1] - p1[1]) * (p2[1] - p1[1]))
    x = p1[0] + ratio * (p2[0] - p1[0])
    y = p1[1] + ratio * (p2[1] - p1[1])
    return (x, y)

def extrapolatePoint(origin, point, ratio=10):
    result = (point[0] + ratio * (point[0] - origin[0]), point[1] + ratio * (point[1] - origin[1]))
    return result

def expandLine(points, ratio=10):
    line = points.copy()
    line[0] = extrapolatePoint(points[1], points[0], ratio)
    line[-1] = extrapolatePoint(points[-2], points[-1], ratio)
    return line

def simplifyLine(line):
    values = []
    for p in line:
        values += list(p)

    for v in values:
        if values.count(v) > 1:
            return v

    return line

def connectLine(lines):

    def canConnect(lines):
        points = list(chain(*lines))
        return len(points) != len(set(points))

    def connect(lines):
        for line in lines:
            for current in lines:
                if line[-1] == current[0]:
                    points = line[:-1] + current
                elif line[0] == current[-1]:
                    points = current[:-1] + line

                if line[-1] == current[0] or line[0] == current[-1]:
                    lines.append(points)
                    lines.remove(line)
                    lines.remove(current)

        return lines

    while canConnect(lines):
        try:
            lines = connect(lines)
        except Exception as e:
            lines = []

    return lines

def clipLine(polygon, points):
    subj = Polygon(polygon)
    clip = LineString(points)
    if subj.intersects(clip):
        intersection = subj.intersection(clip)
        if isinstance(intersection, MultiLineString):
            intersection = intersection[0]
        points = list(intersection.coords)

    return points

def clipPolygon(subj, clip):
    """计算两个多边形之间的交集，并根据允许的最大点平滑多边形

    :param subj: 列表，目标多边形的坐标集
    :param clip: 列表，相切多边形的坐标集
    :param clockwise: 布尔值，点坐标是否顺时针排序，默认否
    :return: 列表，新的多边形坐标集
    """
    subj = Polygon(subj)
    clip = Polygon(clip)
    try:
        intersection = subj.intersection(clip)
        points = list(intersection.exterior.coords)
    except Exception as e:
        points = []

    return points

class SimplifyPolygon(object):

    def __init__(self, maxPoint=7, extend=False):
        self.maxPoint = maxPoint
        self.extend = extend
        self.tolerance = 3

    def simplify(self, points):
        polygon = Polygon(points) if isinstance(points, list) else points
        try:
            polygon = polygon.simplify(self.tolerance)
            while len(polygon.exterior.coords) > self.maxPoint:
                self.tolerance += 1
                polygon = polygon.simplify(self.tolerance)

            outputs = list(polygon.exterior.coords)
        except Exception as e:
            outputs = []

        return outputs

    def findBaseline(self, points, simples):
        baseshape = Polygon(simples)
        baselines = []
        for p, q in zip(simples, simples[1:]):
            pidx = points.index(p)
            qidx = points.index(q)

            if pidx < qidx:
                line = points[pidx:qidx]
            else:
                line = points[qidx:] + points[:pidx]

            if len(line) > 1:
                for v in line[1:]:
                    vertex = Point(v)
                    if not baseshape.contains(vertex):
                        baselines.append([p, q])
                        break

        baselines = connectLine(baselines)
        return baselines

    def unionParts(self, baselines, simples, bufferSize):
        parts = []
        for lines in baselines:
            prev = simples.index(lines[0]) - 1
            foward = (simples.index(lines[-1]) + 1) % len(simples)
            prevTangent = expandLine([simples[prev], lines[0]], ratio=100)
            fowardTangent = expandLine([simples[foward], lines[-1]], ratio=100)
            tangents = [LineString(prevTangent), LineString(fowardTangent)]

            part = LineString(lines).buffer(bufferSize, resolution=1, cap_style=2, join_style=2)

            for t in tangents:
                shapes = split(part, t)
                part = max(shapes, key=lambda p: p.area)
                part = part.buffer(0.5, resolution=1, cap_style=2, join_style=2)

            parts.append(part)

        return parts

    def removeStraightLine(self, points):
        outputs = points[:-1]
        deviation = bearing(outputs[-1], outputs[0]) - bearing(outputs[0], outputs[1])

        if abs(deviation) < 0.04:
            outputs = outputs[1:]

        outputs.append(outputs[0])
        return outputs

    def expand(self, points):
        simples = self.simplify(points)
        simples = simples[:-1]

        origin = Polygon(points)
        bufferSize = self.tolerance
        maxBufferSize = self.tolerance + 5
        baselines = self.findBaseline(points, simples)

        while bufferSize < maxBufferSize:
            parts = self.unionParts(baselines, simples, bufferSize)
            extended = Polygon()
            for part in parts:
                extended = extended.union(part)

            segment = Polygon(simples).union(extended)
            outputs = self.simplify(segment)
            bufferSize += 2

            if Polygon(outputs).buffer(1).contains(origin):
                break

        outputs = self.removeStraightLine(outputs)

        return outputs

    def process(self, points):
        if len(points) <= self.maxPoint:
            return points

        if self.extend:
            return self.expand(points)

        return self.simplify(points)

    def __call__(self, points):
        return self.process(points)


def simplifyPolygon(points, maxPoint=7, extend=False):
    """简化多边形

    :param points: 列表，多边形的坐标集
    :param maxPoint: 数字，交集允许的最大点
    :param extend: 布尔值，边界的做标集，如果存在则简化多边形包含边界
    :return: 列表，简化后的多边形坐标集和简化的误差值
    """
    return SimplifyPolygon(maxPoint=maxPoint, extend=extend)(points)

def decodeSigmetArea(boundaries, area, mode='rectangular', trim=True):
    boundary = Polygon(boundaries)

    if mode == 'polygon':
        polygon = Polygon(area)
        if trim:
            polygon = polygon.intersection(boundary)
        return list(polygon.exterior.coords)

    if mode == 'circle':
        center, radius = area
        polygon = Point(*center).buffer(radius)
        return list(polygon.exterior.coords)

    if mode == 'corridor':
        points, width = area
        polygon = LineString(points).buffer(width, cap_style=2, join_style=2)
        if trim:
            polygon = polygon.intersection(boundary)
        return list(polygon.exterior.coords)

    polygons = []
    for identifier, points in area:
        expands = expandLine(points)
        line = LineString(expands)
        parts = split(boundary, line)
        lat = lambda p: p.centroid.y
        lng = lambda p: p.centroid.x

        shapes = []
        if 'N' in identifier:
            shapes.append(max(parts, key=lat))

        if 'S' in identifier:
            shapes.append(min(parts, key=lat))

        if 'W' in identifier:
            shapes.append(min(parts, key=lng))

        if 'E' in identifier:
            shapes.append(max(parts, key=lng))

        polygon = max(shapes, key=lambda p: shapes.count(p))
        polygons.append(polygon)

    for i, polygon in enumerate(polygons):
        if i == 0:
            current = polygon
        else:
            current = current.intersection(polygon)

    return list(current.exterior.coords)


class EncodeSigmetArea(object):

    def __init__(self, boundaries, area, mode='rectangular'):
        self.boundaries = boundaries
        self.area = area
        self.mode = mode

    @classmethod
    def bearingToDirection(cls, angle):
        directions = {'SE': -0.25, 'NE': 0.25, 'N': 0.5, 'SW': -0.75, 'W': 1.0, 'NW': 0.75, 'E': 0.0, 'S': -0.5}
        bearing = angle / math.pi

        deviation = 10
        identifier = ''
        for k, v in directions.items():
            value = abs(bearing - v)
            if value < deviation or (value == deviation and len(k) < len(identifier)):
                deviation = value
                identifier = k

        return identifier

    def nonOverlappingLines(self):
        lines = []
        boundary = LineString(self.boundaries).buffer(0.3)
        for p, q in zip(self.area, self.area[1:]):
            line = LineString([p, q])
            if not boundary.contains(line):
                lines.append(list(line.coords))

        return lines

    def boundaryContainsLine(self, line):
        for points in zip(self.boundaries, self.boundaries[1:]):
            bound = LineString(points).buffer(0.1)
            line = LineString(line)
            if bound.contains(line):
                return True

        return False

    def lineIntersectsSameBoundary(self, lines):
        for line in lines:
            straightLine = [line[0], line[-1]]
            if self.boundaryContainsLine(straightLine):
                return True

        return False

    def centerNotInPolygon(self):
        polygon = Polygon(self.area)
        return polygon.disjoint(polygon.centroid)

    def createArea(self, lines):
        segment = []

        points = []
        for line in lines:
            points += line

        exlude = set(self.area) - set(points)
        if not exlude:
            exlude = self.area
        center = centroid(exlude)

        for line in lines:
            vector = [0, 0]
            for p, q in zip(line, line[1:]):
                point = perpendicularFoot(p, q, center)
                radian = bearing(center, point)
                scale = distance(p, q)
                vec = (math.cos(radian) * scale, math.sin(radian) * scale)
                vector[0] += vec[0]
                vector[1] += vec[1]

            identifier = self.bearingToDirection(bearing(vector, [0, 0]))
            segment.append([identifier] + line)

        return segment

    def rectangular(self):
        lines = self.nonOverlappingLines()
        segment = self.createArea(lines)
        return segment

    def line(self):
        lines = self.nonOverlappingLines()
        lines = connectLine(lines)

        if self.centerNotInPolygon() or self.lineIntersectsSameBoundary(lines):
            return []

        segment = self.createArea(lines)
        return segment

    def encode(self):
        if self.mode == 'rectangular':
            return self.rectangular()

        if self.mode == 'line':
            return self.line()


def encodeSigmetArea(boundaries, area, mode='rectangular'):
    return EncodeSigmetArea(boundaries, area, mode=mode).encode()
