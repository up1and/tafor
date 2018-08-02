import math

from shapely.ops import split
from shapely.geometry import Polygon, LineString


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

def simplifyLine(line):
    values = []
    for p in line:
        values += list(p)

    for v in values:
        if values.count(v) > 1:
            return v

    return line

def extrapolatePoint(origin, point):
    ratio = 10
    result = (point[0] + ratio * (point[0] - origin[0]), point[1] + ratio * (point[1] - origin[1]))
    return result

def expandLine(points):
    line = points.copy()
    line[0] = extrapolatePoint(points[1], points[0])
    line[-1] = extrapolatePoint(points[-2], points[-1])
    return line

def onBoundary(boundaries, line):
    for points in zip(boundaries, boundaries[1:]):
        bound = LineString(points).buffer(0.1)
        line = LineString(line)

        if bound.contains(line):
            return True

    return False

def decodeSigmetArea(boundaries, area, mode='rectangular'):
    boundary = Polygon(boundaries)
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

def encodeSigmetArea(boundaries, area, mode='rectangular'):

    def angle(origin, point):
        return math.atan2(origin[1] - point[1], origin[0] - point[0])

    def distance(p1, p2):
        length = (p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2
        return math.sqrt(length)

    def foot(p1, p2, p3):
        ratio = ((p3[0]- p1[0]) * (p2[0] - p1[0]) + (p3[1] - p1[1]) * (p2[1] - p1[1])) / ((p2[0] - p1[0]) * (p2[0] - p1[0]) + (p2[1] - p1[1]) * (p2[1] - p1[1]))
        x = p1[0] + ratio * (p2[0] - p1[0])
        y = p1[1] + ratio * (p2[1] - p1[1])
        return (x, y)

    def findBearing(angle):
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

    def nonOverlappingLines(boundaries, area):
        lines = []
        boundary = LineString(boundaries).buffer(0.3)
        for p, q in zip(area, area[1:]):
            line = LineString([p, q])
            if not boundary.contains(line):
                lines.append(list(line.coords))

        return lines

    def suitableForLine(boundaries, lines):
        for line in lines:
            straightLine = [line[0], line[-1]]
            if onBoundary(boundaries, straightLine):
                return False

        return True

    def connectLine(lines):
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

    def createArea(lines):
        segment = []

        points = []
        for line in lines:
            points += line

        exlude = set(area) - set(points)
        if not exlude:
            exlude = area
        center = centroid(exlude)

        for line in lines:
            vector = [0, 0]
            for p, q in zip(line, line[1:]):
                point = foot(p, q, center)
                radian = angle(center, point)
                scale = distance(p, q)
                vec = (math.cos(radian) * scale, math.sin(radian) * scale)
                vector[0] += vec[0]
                vector[1] += vec[1]

            identifier = findBearing(angle(vector, [0, 0]))
            segment.append([identifier] + line)

        return segment

    def rectangular():
        lines = nonOverlappingLines(boundaries, area)
        segment = createArea(lines)
        return segment

    def line():
        segment = []
        lines = nonOverlappingLines(boundaries, area)
        lines = connectLine(lines)
        segment = createArea(lines)
        return segment

    func = locals().get(mode, rectangular)
    return func()
