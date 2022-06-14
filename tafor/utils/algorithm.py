import math

from shapely.ops import split, linemerge
from shapely.geometry import Polygon, MultiPolygon, LineString, LinearRing, MultiLineString, Point

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
    if isinstance(origin, Point):
        origin = [origin.x, origin.y]

    if isinstance(point, Point):
        point = [point.x, point.y]

    return math.atan2(origin[1] - point[1], origin[0] - point[0])

def distance(p1, p2):
    length = (p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2
    return math.sqrt(length)

def depth(l):
    if isinstance(l, list):
        return max(map(depth, l)) + 1 if l else 1
    else:
        return 0

def slope(line, ndigits=5):
    x1, y1 = line.coords[0]
    x2, y2 = line.coords[-1]

    if x2 - x1 == 0:
        return None

    s = (y2 - y1) / (x2 - x1)
    return round(s, ndigits)

def buffer(lines, dist):
    line = LineString(lines)
    center = line.centroid
    _, lat, _ =wgs84.fwd(center.x, center.y, 0, dist)
    lon, _, _ =wgs84.fwd(center.x, center.y, 90, dist)
    deg = (lat - center.x + lon - center.y) / 2

    polygon = line.buffer(deg, cap_style=2, join_style=2)
    return polygon

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

def clipLine(polygon, points):
    subj = Polygon(polygon)
    clip = LineString(points)
    if subj.intersects(clip):
        intersection = subj.intersection(clip)
        if isinstance(intersection, MultiLineString):
            intersection = intersection[0]
        points = list(intersection.coords)

    return points

def whichSide(line, point):
    # form a LinearRing with the end-points of the splitter and a point
    # determine which side of the line the point is on
    coords = line + [point]
    ring = LinearRing(coords)
    if ring.is_ccw:
        return 'right'
    else:
        return 'left'

def clipPolygon(subj, clip, mode='single'):
    """计算两个多边形之间的交集，并根据允许的最大点平滑多边形

    :param subj: 列表，目标多边形的坐标集
    :param clip: 列表，相切多边形的坐标集
    :param clockwise: 布尔值，点坐标是否顺时针排序，默认否
    :return: 列表，新的多边形坐标集
    """
    subj = Polygon(subj)
    clip = Polygon(clip)
    points = []
    try:
        polygon = subj.intersection(clip)

        if polygon.geom_type == 'MultiPolygon':
            if mode == 'single':
                polygon = max(polygon.geoms, key=lambda p: p.area)
            else:
                for p in polygon.geoms:
                    points.append(list(p.exterior.coords))

        if polygon.geom_type == 'Polygon':
            points = list(polygon.exterior.coords)

    except Exception as e:
        print(e)

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

    # there can be only one area in polygon sigmet
    if polygon.geom_type == 'MultiPolygon':
        polygon = max(polygon.geoms, key=lambda p: p.area)

    return polygon

def decodeLine(boundary, lines):
    polygons = []
    directions = {'SE': -0.25, 'NE': 0.25, 'N': 0.5, 'SW': -0.75, 'W': 1.0, 'NW': 0.75, 'E': 0.0, 'S': -0.5}
    for identifier, points in lines:
        line = LineString(points)
        line = extendLine(line, 10)
        parts = split(boundary, line)
        direction = directions[identifier]

        refPoint = (line.centroid.x + math.cos(direction * math.pi) * 10, line.centroid.y + math.sin(direction * math.pi) * 10)
        side = whichSide(points, refPoint)

        shapes = []
        for part in parts.geoms:
            center = (part.centroid.x, part.centroid.y)
            if side == whichSide(points, center):
                shapes.append(part)

        if shapes:
            polygons.append(MultiPolygon(shapes))

    for i, polygon in enumerate(polygons):
        if i == 0:
            current = polygon
        else:
            current = current.intersection(polygon)

    return current

def circle(center, radius):
    circles = []
    for i in range(0, 360):
        lon, lat, _ = wgs84.fwd(center[0], center[1], i, radius)
        circles.append([lon, lat])

    return Polygon(circles)

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
        return boundary

def mergeSameSlopeLines(lines):
    points = []
    for line in lines:
        points += line.coords

    points = [Point(p) for p in points]
    box = LineString(points).envelope
    center = box.centroid

    while len(points) > 2:
        target = min(points, key=lambda p: p.distance(center))
        points.remove(target)

    return LineString(points)

def findNonOverlappingLines(boundaries, points):
    lines = []
    boundary = LineString(boundaries).buffer(0.3)
    for p, q in zip(points, points[1:]):
        line = LineString([p, q])
        if not boundary.contains(line):
            lines.append(line)

    return lines

def findLines(boundaries, polygons):

    def _contains(origin, lines):
        for line in lines:
            polyline = line.buffer(0.1)
            if polyline.contains(origin):
                return True

        return False

    # find the lines that not overlap with the boundary based on the polygon
    lines = []
    for points in polygons:
        geoms = findNonOverlappingLines(boundaries, points)
        for line in geoms:
            lines.append(line)
    
    # find the same slope line
    slopes = [slope(line) for line in lines]
    slopeLines = []
    for s in set(slopes):
        if slopes.count(s) > 1:
            parallelLines = []
            for line in lines:
                if s == slope(line):
                    parallelLines.append(line)

            slopeLines.append(parallelLines)

    # remove the parallel line
    mergeLines = []
    for parallelLines in slopeLines:
        sameLines = []
        for line in parallelLines:
            extendLines = [extendLine(l, offset=100) for l in parallelLines if l is not line]
            if _contains(line, extendLines):
                sameLines.append(line)

        if sameLines:
            mergeLines.append(sameLines)

    # merge the same line
    for sameLines in mergeLines:
        keep, *removes = sameLines
        idx = lines.index(keep)
        lines[idx] = mergeSameSlopeLines(sameLines)
        for r in removes:
            lines.remove(r)

    return lines

def bearingToDirection(angle):
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

def determineDirection(lines, polygons):

    def _average(angles):
        # calculate the average value based on the area
        areas = [area for _, area in angles]
        totalArea = sum(areas)
        num = 0
        for angle, area in angles:
            num += angle * area / totalArea
        return num

    # determine the polygon corresponding to each line, then calculate slope and area
    geoms = []
    for line in lines:
        angles = []
        for points in polygons:
            polygon = Polygon(points)
            polyline = line.buffer(0.1)
            if polyline.intersects(polygon):
                if len(line.coords) > 2:
                    # optional, use line centroid to calculate angle
                    intersect = polyline.intersection(polygon)
                    angle = bearing(polygon.centroid, intersect.centroid)
                else:
                    # use perpendicular foot to calculate angle
                    center = polygon.centroid
                    vector = perpendicularVector(line.coords, (center.x, center.y))
                    angle = bearing(vector, [0, 0])

                angles.append((angle, polygon.area))

        geoms.append([line, angles])

    # find the direction of the line
    segment = []
    for line, angles in geoms:
        angle = _average(angles)
        identifier = bearingToDirection(angle)
        segment.append([identifier] + list(line.coords))

    return segment

def encodeRectangular(boundaries, polygons):
    lines = findLines(boundaries, polygons)
    segment = determineDirection(lines, polygons)
    return segment

def encodeLine(boundaries, polygons):
    lines = findLines(boundaries, polygons)
    # merge the line with same point
    merged = linemerge(MultiLineString(lines))
    if merged.geom_type == 'MultiLineString':
        lines = merged.geoms
    else:
        lines = [merged]

    segment = determineDirection(lines, polygons)
    return segment

def encode(boundaries, coordinates, mode):
    if depth(coordinates) < 2:
        polygons = [coordinates]
    else:
        polygons = coordinates

    if mode == 'rectangular':
        return encodeRectangular(boundaries, polygons)

    if mode == 'line':
        return encodeLine(boundaries, polygons)
