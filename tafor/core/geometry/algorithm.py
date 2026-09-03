import math
import logging

from shapely.ops import linemerge, nearest_points, polylabel, transform
from shapely.geometry import Polygon, LineString, LinearRing, MultiLineString, GeometryCollection, Point

from pyproj import CRS, Transformer, Geod

from tafor.core.utils.units import toKm


logger = logging.getLogger('tafor.geometry')


geod = Geod(ellps='WGS84')

# bearing of each direction identifier, as a fraction of pi
directions = {'SE': -0.25, 'NE': 0.25, 'N': 0.5, 'SW': -0.75, 'W': 1.0, 'NW': 0.75, 'E': 0.0, 'S': -0.5}

def depth(l):
    if isinstance(l, list):
        return max(map(depth, l)) + 1 if l else 1
    else:
        return 0

def geodesicDistance(p1, p2):
    """Geodesic distance in meters between two (lon, lat) points on the WGS84 ellipsoid."""
    *_, length = geod.inv(p1[0], p1[1], p2[0], p2[1])
    return length

def angularDistance(first, second):
    """Shortest angular distance between two angles, as a fraction of pi."""
    if abs(first - second) > 1:
        distance = min(first, second) + 2 - max(first, second)
    else:
        distance = abs(first - second)
    return distance

def crossProduct(origin, a, b):
    """Cross product of vectors OA and OB, its sign tells on which side of OA the point b lies."""
    return (a[0] - origin[0]) * (b[1] - origin[1]) - (a[1] - origin[1]) * (b[0] - origin[0])

def collinearWith(line, other, tolerance=0.1):
    """True when the two segments lie on the same infinite line.

    Judged with the cross product instead of the slope: both endpoints of the
    other segment must be within the tolerance (in degrees) of the line, so
    vertical lines work as well.
    """
    start, end = line.coords[0], line.coords[-1]
    length = LineString([start, end]).length
    return all(abs(crossProduct(start, end, point)) / length <= tolerance
               for point in (other.coords[0], other.coords[-1]))

def overlaps(line, other):
    """True when the two segments share more than nothing, including a
    single touching point.

    Collinear pieces split by the FIR boundary may merely touch at their
    endpoints, and those must merge back into one drawn line.
    """
    return not line.intersection(other).is_empty

def groupCollinearLines(lines, tolerance=0.1):
    """Group the lines that lie on the same infinite line."""
    groups = []
    for line in lines:
        for group in groups:
            if collinearWith(group[0], line, tolerance):
                group.append(line)
                break
        else:
            groups.append([line])

    return groups

def mergeCollinearLines(lines):
    """Merge collinear pieces into the segment spanning their union.

    All pieces lie on the same line, so the endpoints with the extreme
    projections onto the direction of the first piece span every piece.
    """
    points = [point for line in lines for point in (line.coords[0], line.coords[-1])]
    start, end = lines[0].coords[0], lines[0].coords[-1]
    dx, dy = end[0] - start[0], end[1] - start[1]

    def _projection(point):
        return dx * point[0] + dy * point[1]

    return LineString([min(points, key=_projection), max(points, key=_projection)])

def corridor(lines, width):
    """Buffer the line into a corridor polygon extending ``width`` metres
    outwards on each side of the centre line.

    The line is projected onto a local azimuthal equidistant projection
    centred on the line centroid, buffered in metres there, and projected
    back. Metres are true in every direction from the centre of that
    projection, so the corridor keeps its width at any latitude — a plain
    degree-space buffer would grow north-south and shrink east-west by
    up to 50% at 60 degrees north.

    :param lines: list, coordinates of the centre line (lon, lat)
    :param width: number, distance from the centre line outwards in
        metres, i.e. half of the width reported as ``WID n KM``
    :return: Polygon, the corridor around the line
    """
    line = LineString(lines)
    center = line.centroid

    aeqd = CRS(f"+proj=aeqd +lat_0={center.y} +lon_0={center.x} +datum=WGS84 +units=m")
    wgs84 = CRS("EPSG:4326")

    toMeters = Transformer.from_crs(wgs84, aeqd, always_xy=True).transform
    toWgs84 = Transformer.from_crs(aeqd, wgs84, always_xy=True).transform

    projected = transform(toMeters, line)
    buffered = projected.buffer(width, cap_style=2, join_style=2)
    return transform(toWgs84, buffered)

def circle(center, radius):
    circles = []
    for i in range(0, 360):
        lon, lat, _ = geod.fwd(center[0], center[1], i, radius)
        circles.append([lon, lat])

    return Polygon(circles)

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

def clipLine(polygon, points):
    """Clip the line to the polygon and return the longest kept piece.

    A concave polygon can cut the line into several pieces; only the
    longest one survives and the rest are dropped with a warning, because
    the caller expects a single segment (e.g. a corridor centre line).

    :param polygon: list, coordinates of the clipping polygon
    :param points: list, coordinates of the line
    :return: list, coordinates of the clipped line, empty when the line
        misses the polygon
    """
    poly = Polygon(polygon)
    line = LineString(points)
    if poly.intersects(line):
        intersection = poly.intersection(line)
        if isinstance(intersection, GeometryCollection):
            # keep only the line pieces (a grazing corner yields points too)
            parts = [part for part in intersection.geoms
                     if part.geom_type == 'LineString']
            intersection = MultiLineString(parts) if parts else None
        if isinstance(intersection, MultiLineString):
            if len(intersection.geoms) > 1:
                logger.warning('Clipped line breaks into %d pieces, '
                               'keeping the longest one', len(intersection.geoms))
            intersection = max(intersection.geoms, key=lambda part: part.length)
        if intersection is None or intersection.is_empty:
            return []

        points = list(intersection.coords)
    elif not poly.covers(line):
        points = []

    return points

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

    Douglas-Peucker cannot control the vertex count directly, but the
    vertex count shrinks as the tolerance grows, so the smallest tolerance
    that satisfies ``maxPoint`` is found with a binary search over the
    tolerance. Every step simplifies the original polygon, which keeps the
    resulting vertices a subset of the original ones (a property
    ``findCutEdges`` relies on when it matches them back by index).
    Shapes that can never reach ``maxPoint`` (a ring has at least 4
    exterior coordinates) exhaust the search and give up with an empty
    list instead of returning a shape that violates ``maxPoint``.

    :param points: list, coordinates of the polygon
    :param maxPoint: int, maximum number of exterior coordinates allowed
    :return: list, coordinates of the simplified polygon, or an empty list
        when the polygon cannot be simplified
    """
    polygon = Polygon(points) if isinstance(points, list) else points

    if len(polygon.exterior.coords) <= maxPoint:
        return list(polygon.exterior.coords)

    # search bounds: no simplification at all, up to the bounding box
    # diagonal which flattens any shape inside it
    maxIters = 20
    minx, miny, maxx, maxy = polygon.bounds
    low, high = 0.0, math.hypot(maxx - minx, maxy - miny)
    bestCoords = []

    for _ in range(maxIters):
        mid = (low + high) / 2.0
        simplified = polygon.simplify(mid, preserve_topology=True)

        # preserve_topology keeps the geometry valid, this only guards
        # against a degenerate collapse to a line or a point
        if simplified.is_empty or simplified.geom_type != 'Polygon':
            high = mid
            continue

        coords = list(simplified.exterior.coords)

        if len(simplified.exterior.coords) <= maxPoint:
            # feasible: keep it and try a smaller tolerance for detail
            bestCoords = coords
            high = mid
        else:
            low = mid

        if high - low < 1e-6:
            break

    return bestCoords

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
        if polygon.geom_type not in ('Polygon', 'MultiPolygon'):
            # the area may lie outside the boundary entirely and touch it
            # at an edge or a point only
            return Polygon()

    # there can be only one area in polygon sigmet
    if polygon.geom_type == 'MultiPolygon':
        polygon = max(polygon.geoms, key=lambda p: p.area)

    return polygon

def halfPlane(identifier, points, boundary):
    """Build the polygon covering the side of the polyline that the
    direction identifier points to.

    The whole polyline is treated as one edge of the area: it is extended
    beyond the boundary at both ends, then closed with a copy of itself
    shifted towards the direction of the identifier. A concave polyline
    keeps its concave area, which per-segment half-planes would flatten
    into a convex one.

    :param identifier: str, one of the direction identifiers like 'N'
    :param points: list, coordinates of the reported line
    :param boundary: Polygon, the FIR boundary
    :return: Polygon, or None when no area can be built, e.g. a line
        parallel to the direction keeps no area on either side
    """
    minx, miny, maxx, maxy = boundary.bounds
    span = math.hypot(maxx - minx, maxy - miny)
    angle = directions[identifier] * math.pi
    dx, dy = math.cos(angle), math.sin(angle)

    def _extend(base, other):
        ux, uy = base[0] - other[0], base[1] - other[1]
        length = math.hypot(ux, uy)
        if length == 0:
            return base
        return (base[0] + ux / length * span, base[1] + uy / length * span)

    start = _extend(points[0], points[1])
    end = _extend(points[-1], points[-2])
    path = [start] + list(points) + [end]

    shape = Polygon(path + [(p[0] + dx * span, p[1] + dy * span) for p in reversed(path)])
    if not shape.is_valid:
        # a path doubling back on itself makes the curtain self-intersect
        shape = shape.buffer(0)

    if shape.is_empty or shape.area < 1e-9:
        logger.warning('Direction %s keeps no area along the line %s, skipping it',
                       identifier, points)
        return None

    return shape

def decodeLine(boundary, lines):
    """Decode line locations into the area within the boundary.

    Each line describes a half-plane: the side that its direction identifier
    points to. The area is the intersection of all the half-planes with the
    boundary, so multiple lines narrow the area down step by step.
    """
    planes = []
    for identifier, points in lines:
        plane = halfPlane(identifier, points, boundary)
        if plane is not None:
            planes.append(plane)

    if not planes:
        return Polygon()

    current = planes[0]
    for plane in planes[1:]:
        current = current.intersection(plane)

    return current.intersection(boundary)

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
        return corridor(lines, width * 1000 / 2)

    if mode == 'entire':
        return boundary

def findDrawnLineEdges(boundaries, points):
    """Return the edges of the polygon that do not lie on the FIR boundary.

    A polygon drawn for a line model (e.g. an area north of a line) is clipped
    by the FIR boundary, so its perimeter consists of the drawn line plus FIR
    boundary arcs. An edge that lies along the boundary has almost its whole
    length covered by the boundary ring, while an edge that merely starts and
    ends on the boundary (the drawn line) crosses it only at the endpoints.
    """
    ring = LineString(boundaries)
    lines = []
    for p, q in zip(points, points[1:]):
        edge = LineString([p, q])
        midpoint = edge.interpolate(0.5, normalized=True)
        if ring.distance(midpoint) > 1e-5:
            lines.append(edge)

    return lines

def findLines(boundaries, polygons):
    """Find the drawn line of a line-model area.

    The user draws a polygon but the area is reported as a line (e.g. an area
    north of a line). The polygon is clipped by the FIR boundary, so the edges
    that do not lie on the boundary are the drawn line. A polygon that lies
    entirely inside the boundary was never clipped and is skipped, otherwise
    every edge would be mistaken for the drawn line.

    Some FIR boundaries split the drawn line into several pieces, so pieces
    that are collinear and overlap are merged back together afterwards.
    """
    lines = []
    boundary = LinearRing(boundaries)
    for points in polygons:
        polygon = Polygon(points)
        # skip polygons entirely inside the boundary: they were never clipped,
        # so every edge would be mistaken for the drawn line
        if boundary.intersects(polygon):
            lines += findDrawnLineEdges(boundaries, points)

    # merge collinear overlapping pieces split by the FIR boundary
    merged = []
    for group in groupCollinearLines(lines):
        clusters = []
        for line in group:
            for cluster in clusters:
                if any(overlaps(line, other) for other in cluster):
                    cluster.append(line)
                    break
            else:
                clusters.append([line])

        merged += [mergeCollinearLines(cluster) for cluster in clusters]

    return merged

def bearingToDirection(angle):
    """Map a bearing in radians to the closest direction identifier."""
    fraction = angle / math.pi

    deviation = float('inf')
    identifier = ''
    for k, v in directions.items():
        value = angularDistance(v, fraction)
        if value < deviation or (value == deviation and len(k) < len(identifier)):
            deviation = value
            identifier = k

    return identifier

def principalAxis(line):
    """Straighten a line or polyline into a single centerline.

    The minimum rotated rectangle brackets the line's overall extent; the
    segment joining the midpoints of its two short sides smooths out bends
    in a polyline. When the rectangle degenerates (the line is already
    straight), the line itself is the axis.
    """
    rectangle = line.minimum_rotated_rectangle
    if rectangle.geom_type != 'Polygon' or rectangle.area <= 0:
        return line

    corners = list(rectangle.exterior.coords)[:-1]
    edges = sorted((LineString([corners[i], corners[(i + 1) % 4]])
                    for i in range(4)), key=lambda edge: edge.length)
    mids = [edges[0].interpolate(0.5, normalized=True),
            edges[1].interpolate(0.5, normalized=True)]
    return LineString([mids[0].coords[0], mids[1].coords[0]])

def lineDirection(line, polygons):
    """Sum of the unit vectors pointing from the line towards each touching
    polygon's pole of inaccessibility, or None when no polygon contributes.

    The vectors start on the principal axis of the line, so a bent polyline
    is measured against its overall course instead of a bending corner.
    Accumulating unit vectors instead of averaging angles keeps directions
    near +/-pi from wrapping around (areas west of a line stay west instead
    of averaging into east). The pole of inaccessibility stands in for the
    centroid, which can fall outside hollow or bent shapes.
    """
    axis = principalAxis(line)
    total = [0.0, 0.0]
    for points in polygons:
        polygon = Polygon(points)
        if polygon.area <= 0 or not line.intersects(polygon):
            continue

        pole = polylabel(polygon)
        origin = nearest_points(axis, pole)[0]
        angle = math.atan2(pole.y - origin.y, pole.x - origin.x)
        total[0] += math.cos(angle)
        total[1] += math.sin(angle)

    if math.hypot(total[0], total[1]) < 1e-9:
        return None

    return total

def determineDirection(lines, polygons):
    """Determine on which side of each line the drawn areas lie.

    Every polygon touching the line contributes a unit vector from the line
    towards the polygon. The direction of the vector sum is mapped to the
    closest direction identifier. Lines no polygon touches, or where the
    vectors cancel out (areas pulling to both sides), are skipped.
    """
    segment = []
    for line in lines:
        vector = lineDirection(line, polygons)
        if vector is None:
            logger.error('No area to determine the direction of the line, %s',
                         list(line.coords))
            continue

        angle = math.atan2(vector[1], vector[0])
        segment.append([bearingToDirection(angle)] + list(line.coords))

    return segment

def encodeRectangular(boundaries, polygons):
    """Encode a drawn area as its boundary-parallel lines with directions."""
    lines = findLines(boundaries, polygons)
    segment = determineDirection(lines, polygons)
    return segment

def encodeLine(boundaries, polygons):
    """Encode a drawn area as the drawn line with its direction.

    The line can come back in several pieces; linemerge stitches the
    connected ones into a single line or polyline first. More than three
    lines mean the drawn area is fragmented beyond what a line report
    can describe, so nothing is encoded instead of a garbage message.
    """
    lines = findLines(boundaries, polygons)
    if len(lines) > 3:
        logger.error('Too many lines to encode, %s',
                     [list(line.coords) for line in lines])
        return []

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
    """Encode drawn coordinates into ``[direction, *points]`` segments."""
    if depth(coordinates) < 2:
        polygons = [coordinates]
    else:
        polygons = coordinates

    if mode == 'rectangular':
        return encodeRectangular(boundaries, polygons)

    if mode == 'line':
        return encodeLine(boundaries, polygons)
