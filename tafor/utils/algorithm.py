import math

from shapely.ops import split, linemerge
from shapely.geometry import Polygon, LineString, MultiLineString, Point

from pyproj import Geod


wgs84 = Geod(ellps='WGS84')

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

def buffer(lines, dist):
    line = LineString(lines)
    center = line.centroid
    _, lat, _ =wgs84.fwd(center.x, center.y, 0, dist)
    lon, _, _ =wgs84.fwd(center.x, center.y, 90, dist)
    deg = (lat - center.x + lon - center.y) / 2

    polygon = line.buffer(deg, cap_style=2, join_style=2)
    if polygon.is_empty:
        return []
    return list(polygon.exterior.coords)

def perpendicularFoot(p1, p2, p3):
    ratio = ((p3[0]- p1[0]) * (p2[0] - p1[0]) + (p3[1] - p1[1]) * (p2[1] - p1[1])) / ((p2[0] - p1[0]) * (p2[0] - p1[0]) + (p2[1] - p1[1]) * (p2[1] - p1[1]))
    x = p1[0] + ratio * (p2[0] - p1[0])
    y = p1[1] + ratio * (p2[1] - p1[1])
    return (x, y)

def perpendicularVector(line, center):
    vector = [0, 0]
    for p, q in zip(line, line[1:]):
        point = perpendicularFoot(p, q, center)
        radian = bearing(center, point)
        scale = distance(p, q)
        vec = (math.cos(radian) * scale, math.sin(radian) * scale)
        vector[0] += vec[0]
        vector[1] += vec[1]

    return vector

def subAngle(direction, angle):
    if abs(direction - angle) > 1:
        degree = min(direction, angle) + 2 - max(direction, angle)
    else:
        degree = abs(direction - angle)
    return degree

def shiftPoint(p1, p2, offset):
    """
    shift points with offset in orientation of line p1 -> p2
    """
    x1, y1 = p1
    x2, y2 = p2

    if ((x1 - x2) == 0) and ((y1 - y2) == 0):  # zero length line
        x, y = x1, y1
    else:
        length = offset / math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)
        x = x1 + (x2 - x1) * length
        y = y1 + (y2 - y1) * length
    return x, y

def extendLine(line, offset, side='both'):
    """
    extend line in same orientation
    """
    if side == 'both':
        sides = ['start', 'end']
    else:
        sides = [side]

    for side in sides:
        coords = line.coords
        if side == 'start':
            point = shiftPoint(coords[0], coords[1], -1. * offset)
            line = LineString([point] + coords[:])
        elif side == 'end':
            point = shiftPoint(coords[-1], coords[-2], -1. * offset)
            line = LineString(coords[:] + [point])
    return line

def lineIntersection(line1, line2, offset=10):
    """
    Intersection of lines
    """
    line1 = extendLine(line1, offset)
    line2 = extendLine(line2, offset)

    return line1.intersection(line2)

def flattenLine(line):
    values = []
    for p in line:
        values += list(p)

    for v in values:
        if values.count(v) > 1:
            return v

    return line

def mergeLine(lines):
    points = []
    lines = MultiLineString(lines)
    merged = linemerge(lines)

    if merged.geom_type == 'LineString':
        points = [list(merged.coords)]

    elif merged.geom_type == 'MultiLineString':
        for line in merged.geoms:
            points.append(list(line.coords))

    return points

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

    def __init__(self, maxPoint=7):
        self.maxPoint = maxPoint
        self.tolerance = 0.1

    def simplify(self, points):
        polygon = Polygon(points) if isinstance(points, list) else points
        try:
            polygon = polygon.simplify(self.tolerance)
            while len(polygon.exterior.coords) > self.maxPoint:
                self.tolerance += 0.1
                polygon = polygon.simplify(self.tolerance)

            outputs = list(polygon.exterior.coords)
        except Exception as e:
            outputs = []

        return outputs

    def findBaselines(self, points, simples):
        baseshape = Polygon(simples).buffer(0.01, cap_style=2, join_style=2)
        baselines = []
        outsides = []
        for p, q in zip(simples, simples[1:]):
            pidx = points.index(p)
            qidx = points.index(q)

            if pidx < qidx:
                line = points[pidx:qidx]
            else:
                line = points[qidx:] + points[:pidx]

            vertices = []

            if len(line) > 1:
                for v in line[1:]:
                    vertex = Point(v)
                    # vertex not insede the simplified polygon, means that the corresponding line is simplified
                    if not baseshape.contains(vertex):
                        newline = LineString([p, q])
                        if newline not in baselines:
                            baselines.append(newline)

                        # the vertex not inside the simplified polygon
                        vertices.append(vertex)

            if vertices:
                outsides.append(vertices)

        # caculate the max distance from vertices to baseline
        distances = []
        for i, line in enumerate(baselines):
            distance = 0
            for vertex in outsides[i]:
                distance = max(distance, line.distance(vertex))

            distances.append(distance)

        return baselines, distances

    def extend(self, points):
        simples = self.simplify(points)
        outputs = simples[:-1]
        baselines, distances = self.findBaselines(points, simples[:-1])

        for i, line in enumerate(baselines):
            distance = distances[i]

            # get the index of the baseline vertex
            start, end = line.coords
            sidx, eidx = simples.index(start), simples.index(end)

            # find the closest vertex to the baseline
            prev = outputs[(sidx - 1) % len(outputs)]
            next = outputs[(eidx + 1) % len(outputs)]

            # update the baseline and nearby lines
            start = outputs[sidx]
            end = outputs[eidx]
            line = LineString([start, end])
            prevline = LineString([prev, start])
            nextline = LineString([end, next])

            # parallel baseline with distance
            newline = line.parallel_offset(distance, 'left', resolution=1, join_style=2)
            newline = LineString([lineIntersection(prevline, newline), lineIntersection(newline, nextline)])
            outputs[sidx], outputs[eidx] = newline.coords

        outputs.append(outputs[0])
        return outputs

    def __call__(self, points, extend=False):
        if len(points) <= self.maxPoint:
            return points

        if extend:
            return self.extend(points)

        return self.simplify(points)


def simplifyPolygon(points, maxPoint=7, extend=False):
    """简化多边形

    :param points: 列表，多边形的坐标集
    :param maxPoint: 数字，交集允许的最大点
    :param extend: 布尔值，边界的做标集，如果存在则简化多边形包含边界
    :return: 列表，简化后的多边形坐标集和简化的误差值
    """
    return SimplifyPolygon(maxPoint=maxPoint)(points, extend=extend)

def decodePolygon(boundary, polygon, trim):
    polygon = Polygon(polygon)
    if trim:
        polygon = polygon.intersection(boundary)
    return list(polygon.exterior.coords)

def decodeLine(boundary, lines):
    polygons = []
    directions = {'SE': -0.25, 'NE': 0.25, 'N': 0.5, 'SW': -0.75, 'W': 1.0, 'NW': 0.75, 'E': 0.0, 'S': -0.5}
    for identifier, points in lines:
        line = LineString(points)
        line = extendLine(line, 10)
        parts = split(boundary, line)
        direction = directions[identifier]

        def tolerance(part):
            center = [part.centroid.x, part.centroid.y]
            vector = perpendicularVector(points, center)
            angle = bearing(vector, [0, 0]) / math.pi
            degree = subAngle(direction, angle)
            return degree

        polygon = min(parts, key=tolerance)
        polygons.append(polygon)

    for i, polygon in enumerate(polygons):
        if i == 0:
            current = polygon
        else:
            current = current.intersection(polygon)

    return list(current.exterior.coords)

def circle(center, radius):
    circles = []
    for i in range(0, 360):
        lon, lat, _ = wgs84.fwd(center[0], center[1], i, radius)
        circles.append([lon, lat])

    return circles

def decode(boundaries, locations, mode, trim=True):
    from tafor.utils.convert import degreeToDecimal
    boundary = Polygon(boundaries)

    if mode == 'polygon':
        points = [(degreeToDecimal(lon), degreeToDecimal(lat)) for lat, lon in locations]
        return decodePolygon(boundary, points, trim)

    if mode == 'line':
        lines = []
        for identifier, *points in locations:
            points = [(degreeToDecimal(lon), degreeToDecimal(lat)) for lat, lon in points]
            lines.append((identifier, points))

        return decodeLine(boundary, lines)

    if mode == 'rectangular':
        lines = []
        minx, miny, maxx, maxy = boundary.bounds
        for identifier, deg in locations:
            dec = degreeToDecimal(deg)
            if identifier in ['N', 'S']:
                line = [
                    (minx, dec),
                    (maxx, dec)
                ]
            else:
                line = [
                    (dec, miny),
                    (dec, maxy)
                ]

            lines.append((identifier, line))

        return decodeLine(boundary, lines)

    if mode == 'circle':
        point, (radius, unit) = locations
        center = [degreeToDecimal(point[1]), degreeToDecimal(point[0])]
        width = int(radius) * 1.852 if unit == 'NM' else int(radius)
        return circle(center, width * 1000) 

    if mode == 'corridor':
        points, (radius, unit) = locations
        lines = [(degreeToDecimal(lon), degreeToDecimal(lat)) for lat, lon in points]
        width = int(radius) * 1.852 if unit == 'NM' else int(radius)
        return buffer(lines, width * 1000)

    if mode == 'entire':
        return boundaries

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
            value = subAngle(v, bearing)
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
            vector = perpendicularVector(line, center)
            identifier = self.bearingToDirection(bearing(vector, [0, 0]))
            segment.append([identifier] + line)

        return segment

    def rectangular(self):
        lines = self.nonOverlappingLines()
        segment = self.createArea(lines)
        return segment

    def line(self):
        lines = self.nonOverlappingLines()
        lines = mergeLine(lines)

        if self.centerNotInPolygon() or self.lineIntersectsSameBoundary(lines):
            return []

        segment = self.createArea(lines)

        return segment

    def encode(self):
        if self.mode == 'rectangular':
            return self.rectangular()

        if self.mode == 'line':
            return self.line()


def encode(boundaries, area, mode='rectangular'):
    return EncodeSigmetArea(boundaries, area, mode=mode).encode()
