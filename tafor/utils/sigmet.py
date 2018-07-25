import math

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

def pointsToPolygon(points):
    origin = centroid(points)

    def compare(origin, point):
        distance = (origin[0] - point[0]) * (origin[0] - point[0]) + (origin[1] - point[1]) * (origin[1] - point[1])
        angle = math.atan2(point[1] - origin[1], point[0] - origin[0])
        return angle, distance

    points = sorted(points, key=lambda p: compare(origin, p))
    points = list(map(tuple, points))
    return points

def simplifyLine(line):
    values = []
    for p in line:
        values += list(p)

    for v in values:
        if values.count(v) > 1:
            return v

def expandLine(line, rng):
    p1, p2 = line
    ratio = (p1[1] - p2[1]) / (p1[0] - p2[0])
    const = (p1[0] * p2[1] - p2[0] * p1[1]) / (p1[0] - p2[0])
    equation = lambda x: ratio * x + const
    points = [
        [rng[0], equation(rng[0])],
        [rng[1], equation(rng[1])]
    ]
    return points

def insertPoints(points, boundaries):
    origin = centroid(points + boundaries)

    def compare(origin, point):
        distance = (origin[0] - point[0]) * (origin[0] - point[0]) + (origin[1] - point[1]) * (origin[1] - point[1])
        angle = math.atan2(point[1] - origin[1], point[0] - origin[0])
        return angle, distance

    def insert(boundaries, p):
        point = compare(origin, p)
        polygon = boundaries.copy()
        for i, b in enumerate(boundaries, start=1):
            bound = compare(origin, b)

            if p in polygon:
                continue

            if point[0] < bound[0] or (point[0] == bound[0] and point[1] < bound[1]):
                index = polygon.index(b)
                polygon.insert(index, p)
            elif len(polygon) == i:
                polygon.append(p)

        return polygon

    initial = min(boundaries, key=lambda p: compare(origin, p))
    boundaries.reverse()
    start = boundaries.index(initial)
    polygon = boundaries[start:] + boundaries[:start]

    for p in points:
        polygon = insert(polygon, p)

    return polygon

def onSameSide(line, direction, point):
    angle = lambda origin, point: math.atan2(point[1] - origin[1], (point[0] - origin[0])) / math.pi

    startAngle = angle(*line)
    endAngle = startAngle + 1
    if endAngle > 1:
        endAngle = endAngle - 2

    start, end = min(startAngle, endAngle), max(startAngle, endAngle)
    section = [start, end]

    origin = centroid(line)
    originBearing = angle(origin, direction)
    side = start <= originBearing <= end

    pointBearing = angle(origin, point)
    sameside = start <= pointBearing <= end

    return sameside == side

def decodeSigmetArea(boundaries, area):
    boundary = Polygon(boundaries)
    polygons = []
    for identifier, points in area:
        line = LineString(points)
        intersection = boundary.intersection(line)

        if not intersection:
            continue

        straightLine = [points[0], points[-1]]
        direction = centroid(straightLine)

        if 'N' in identifier:
            direction[1] += 1

        if 'S' in identifier:
            direction[1] -= 1

        if 'W' in identifier:
            direction[0] -= 1 

        if 'E' in identifier:
            direction[0] += 1

        bounds = []
        for point in boundaries:
            if onSameSide(straightLine, direction, point):
                bounds.append(point)

        polygon = insertPoints(list(intersection.coords), bounds)
        polygons.append(polygon)
            
    for i, polygon in enumerate(polygons):
        if i == 0:
            current = Polygon(polygon)
        else:
            current = current.intersection(Polygon(polygon))

    return list(current.exterior.coords)

def encodeSigmetArea(boundaries, area, mode='rectangular'):

    def foot(p1, p2, p3):
        ratio = ((p3[0]- p1[0]) * (p2[0] - p1[0]) + (p3[1] - p1[1]) * (p2[1] - p1[1])) / ((p2[0] - p1[0]) * (p2[0] - p1[0]) + (p2[1] - p1[1]) * (p2[1] - p1[1]))
        x = p1[0] + ratio * (p2[0] - p1[0])
        y = p1[1] + ratio * (p2[1] - p1[1])
        return (x, y)

    def bearing(origin, point):
        directions = {'SE': -0.25, 'NE': 0.25, 'N': 0.5, 'SW': -0.75, 'W': 1.0, 'NW': 0.75, 'E': 0.0, 'S': -0.5}
        angle = math.atan2(origin[1] - point[1], origin[0] - point[0]) / math.pi
        
        deviation = 10
        identifier = ''
        for k, v in directions.items():
            value = abs(angle - v)
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
        for line in lines:
            exclude = set(area) - set(line)
            origin = centroid(list(exclude))
            point = foot(line[0], line[-1], origin)
            identifier = bearing(origin, point)
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
