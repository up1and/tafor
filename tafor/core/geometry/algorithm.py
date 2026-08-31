import math
import logging

from shapely.ops import split, linemerge
from shapely.geometry import Polygon, MultiPolygon, LineString, LinearRing, MultiLineString, Point

from pyproj import Geod

from tafor.core.utils.units import toKm


logger = logging.getLogger('tafor.geometry')


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

def euclideanDistance(p1, p2):
    """Euclidean straight-line distance between two (x, y) points in planar coordinates."""
    length = (p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2
    return math.sqrt(length)

def geodesicDistance(p1, p2):
    """Geodesic distance in meters between two (lon, lat) points on the WGS84 ellipsoid."""
    *_, length = wgs84.inv(p1[0], p1[1], p2[0], p2[1])
    return length

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
    _, lat, _ = wgs84.fwd(center.x, center.y, 0, dist)
    lon, _, _ = wgs84.fwd(center.x, center.y, 90, dist)
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
        scale = euclideanDistance(p, q)
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

def linesIntersection(line1, line2):
    """
    Intersection point of the two infinite lines defined by the line
    coordinates, or None when the lines are parallel
    """
    (x1, y1), (x2, y2) = line1.coords[0], line1.coords[-1]
    (x3, y3), (x4, y4) = line2.coords[0], line2.coords[-1]

    denominator = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if denominator == 0:
        return None

    offset1 = x1 * y2 - y1 * x2
    offset2 = x3 * y4 - y3 * x4
    x = (offset1 * (x3 - x4) - (x1 - x2) * offset2) / denominator
    y = (offset1 * (y3 - y4) - (y1 - y2) * offset2) / denominator
    # adding 0.0 turns -0.0 into 0.0
    return (x + 0.0, y + 0.0)

def flattenLine(line):
    values = []
    for p in line:
        values += list(p)

    for v in values:
        if values.count(v) > 1:
            return v

def clipLine(polygon, points):
    poly = Polygon(polygon)
    line = LineString(points)
    if poly.intersects(line):
        intersection = poly.intersection(line)
        if isinstance(intersection, MultiLineString):
            intersection = intersection[0]
        points = list(intersection.coords)
    elif not poly.covers(line):
        points = []

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
    """Intersect two polygons and return the exterior coordinates.

    :param subj: list, coordinates of the subject polygon
    :param clip: list, coordinates of the clip polygon
    :param mode: str, ``'single'`` keeps only the largest piece when the
        intersection is a MultiPolygon, otherwise all pieces are returned
    :return: list, coordinates of the clipped polygon; a list of rings when
        ``mode`` is not ``'single'``, an empty list on failure
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
        logger.error('Failed to clip polygon, {}'.format(e))

    return points


def simplifyToMaxPoint(points, maxPoint=7):
    """Reduce the polygon with Douglas-Peucker until it has at most
    ``maxPoint`` exterior coordinates.

    Douglas-Peucker cannot control the vertex count directly, so the
    tolerance is increased step by step (a pragmatic workaround) until the
    simplified polygon has few enough vertices. Shapes that can never reach
    ``maxPoint`` (a square has at least 5 exterior coordinates) give up
    after a bounded number of steps instead of looping forever.

    :param points: list, coordinates of the polygon
    :param maxPoint: int, maximum number of exterior coordinates allowed
    :return: list, coordinates of the simplified polygon, or an empty list
        when the polygon cannot be simplified
    """
    polygon = Polygon(points) if isinstance(points, list) else points
    tolerance = 0.1
    steps = 0
    try:
        polygon = polygon.simplify(tolerance)
        while len(polygon.exterior.coords) > maxPoint and steps < 1000:
            steps += 1
            tolerance += 0.1
            polygon = polygon.simplify(tolerance)

        outputs = list(polygon.exterior.coords)
    except Exception as e:
        logger.error('Failed to simplify polygon, {}'.format(e))
        outputs = []

    return outputs

def findCutEdges(points, simplified, tolerance=0.1):
    """Find the simplified edges that cut off original vertices.

    The simplified edges inevitably cut through the original shape, so this
    collects the original vertices that fall outside the simplified polygon
    and groups them by the simplified edge they were cut off by. The closing
    edge of the ring is inspected as well. Vertices within ``tolerance`` of
    the simplified polygon are considered covered.

    :param points: list, coordinates of the original polygon
    :param simplified: list, coordinates of the simplified polygon
    :param tolerance: number, accepted distance between a vertex and the
        simplified polygon before the vertex counts as cut off
    :return: list, one dict per cut edge with the edge start index in
        ``simplified``, the edge and the largest distance from its outside
        vertices to the edge
    """
    simplifiedShape = Polygon(simplified).buffer(tolerance, cap_style=2, join_style=2)
    ring = simplified[:-1]
    cuts = []

    for i, start in enumerate(ring):
        end = ring[(i + 1) % len(ring)]
        sidx = points.index(start)
        eidx = points.index(end)

        # the original vertices between the edge end-points along the ring
        if sidx < eidx:
            arc = points[sidx:eidx]
        else:
            arc = points[sidx:] + points[:eidx + 1]

        # vertices outside the simplified polygon means the edge was simplified
        vertices = [Point(v) for v in arc[1:] if not simplifiedShape.contains(Point(v))]
        if vertices:
            edge = LineString([start, end])
            distance = max(edge.distance(vertex) for vertex in vertices)
            cuts.append({'index': i, 'edge': edge, 'distance': distance})

    return cuts

def expandToCover(points, simplified):
    """Expand the simplified polygon until it covers all original vertices.

    Each edge that cut off original vertices is shifted outward by the
    largest distance of the vertices it cut off (plus a small margin, so the
    farthest vertex is strictly covered instead of lying on the edge). The
    shifted edges and the untouched edges close up naturally: every vertex
    of the result is the intersection of two adjacent edge lines. The
    outward side is derived from the ring orientation instead of assuming a
    clockwise ring.

    :param points: list, coordinates of the original polygon
    :param simplified: list, coordinates of the simplified polygon
    :return: list, coordinates of the expanded polygon
    """
    if not simplified:
        return simplified

    cuts = {cut['index']: cut for cut in findCutEdges(points, simplified)}
    if not cuts:
        return simplified

    ring = simplified[:-1]
    count = len(ring)
    outward = 'right' if LinearRing(simplified).is_ccw else 'left'

    # decide the geometry line of every edge: cut edges move outward, the
    # others stay in place
    lines = []
    for i in range(count):
        edge = LineString([ring[i], ring[(i + 1) % count]])
        if i in cuts:
            offset = cuts[i]['distance'] * 1.01
            edge = edge.parallel_offset(offset, outward, resolution=1, join_style=2)
            if edge.is_empty:
                logger.error('Failed to offset the cut edge, {}'.format(list(cuts[i]['edge'].coords)))
        lines.append(edge)

    # every corner is the intersection of the two adjacent edge lines
    vertices = []
    for i in range(count):
        vertex = linesIntersection(lines[(i - 1) % count], lines[i])
        if vertex is not None:
            vertices.append(vertex)

    if len(vertices) < 3:
        logger.error('Failed to expand the polygon to cover the original vertices')
        return simplified

    polygon = Polygon(vertices)
    if not polygon.is_valid:
        polygon = polygon.buffer(0)
        if polygon.geom_type == 'MultiPolygon':
            polygon = max(polygon.geoms, key=lambda p: p.area)

    if polygon.is_empty:
        logger.error('Failed to expand the polygon to cover the original vertices')
        return simplified

    # keep the ring orientation of the simplified polygon
    if not polygon.is_empty and LinearRing(simplified).is_ccw != LinearRing(polygon.exterior).is_ccw:
        polygon = Polygon(list(polygon.exterior.coords)[::-1])

    return list(polygon.exterior.coords)


def simplifyPolygon(points, maxPoint=7, expand=False):
    """Simplify a polygon to at most ``maxPoint`` vertices.

    :param points: list, coordinates of the polygon
    :param maxPoint: int, maximum number of vertices allowed in the result
    :param expand: bool, when True the simplified polygon is expanded
        outward so that it covers all of the original vertices
    :return: list, coordinates of the simplified polygon
    """
    if len(points) <= maxPoint:
        return points

    simplified = simplifyToMaxPoint(points, maxPoint)
    if expand:
        return expandToCover(points, simplified)

    return simplified

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

        refLine = [points[0], points[-1]]
        refPoint = (line.centroid.x + math.cos(direction * math.pi) * 10, line.centroid.y + math.sin(direction * math.pi) * 10)
        side = whichSide(refLine, refPoint)

        shapes = []
        for part in parts.geoms:
            center = part.representative_point()
            if len(points) > 2:
                polyline = Polygon(points)
                if polyline.intersects(part):
                    other = part.difference(polyline)
                    if not other.is_empty:
                        center = other.representative_point()

            center = (center.x, center.y)
            if side == whichSide(refLine, center):
                shapes.append(part)

        if shapes:
            polygons.append(MultiPolygon(shapes))

    current = Polygon()
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
    from tafor.core.geometry.coordinate import degreeToDecimal
    boundary = Polygon(boundaries)
    hasBoundary = boundary.is_valid and not boundary.is_empty
    if not hasBoundary:
        trim = False
        if mode in ['line', 'rectangular', 'entire']:
            return Polygon()

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
        width = toKm(int(radius), unit)
        return circle(center, width * 1000) 

    if mode == 'corridor':
        points, (radius, unit) = locations
        lines = [(degreeToDecimal(lon), degreeToDecimal(lat)) for lat, lon in points]
        width = toKm(int(radius), unit)
        return buffer(lines, width * 1000 / 2)

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
    boundary = LinearRing(boundaries)
    for points in polygons:
        polyline = Polygon(points)
        # lines must intersect with boundary
        if boundary.intersects(polyline):
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
                    # use line centroid to calculate angle
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
    if lines:
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
