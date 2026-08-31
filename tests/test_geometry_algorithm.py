from shapely.geometry import LineString, Point, Polygon

from tafor.core.geometry.algorithm import (
    findCutEdges, linesIntersection, simplifyPolygon, simplifyToMaxPoint,
)


def jagged_coast_ring():
    """A rectangle whose left edge is a jagged 'coastline' crossing the seam."""
    ring = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    for y in range(9, 0, -1):
        ring.append((-1.0 if y % 2 else 0.0, float(y)))
    return ring


def assert_covers_all(result, points):
    polygon = Polygon(result)
    assert polygon.is_valid
    for vertex in points:
        assert polygon.covers(Point(vertex)), '{} not covered'.format(vertex)


def test_lines_intersection():
    line1 = LineString([(0, 0), (10, 0)])
    line2 = LineString([(5, -5), (5, 5)])
    assert linesIntersection(line1, line2) == (5.0, 0.0)

    parallel = LineString([(0, 1), (10, 1)])
    assert linesIntersection(line1, parallel) is None


def test_simplify_reduces_to_max_point():
    simplified = simplifyToMaxPoint(jagged_coast_ring(), maxPoint=7)

    assert len(simplified) <= 7
    assert simplified[0] == simplified[-1]  # closed ring
    assert Polygon(simplified).is_valid


def test_simplify_polygon_without_expand():
    ring = jagged_coast_ring()
    assert simplifyPolygon(ring, maxPoint=7) == simplifyToMaxPoint(ring, maxPoint=7)


def test_small_polygon_returned_unchanged():
    ring = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    assert simplifyPolygon(ring, maxPoint=7) == ring


def test_simplify_gives_up_instead_of_looping_forever():
    # a square can never be reduced below 5 exterior coordinates
    ring = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    assert len(simplifyToMaxPoint(ring, maxPoint=3)) == 5


def test_expand_covers_cut_vertices():
    # a bump on the right side, the cut edge is not the closing edge
    ring = [(0.0, 0.0), (0.0, 10.0), (10.0, 10.0), (11.0, 5.0), (10.0, 0.0)]
    result = simplifyPolygon(ring, maxPoint=5, expand=True)

    assert len(result) <= 5
    assert_covers_all(result, ring)


def test_expand_covers_seam_vertices():
    # the outside vertices sit on the closing edge arc, which the old
    # implementation never inspected
    ring = jagged_coast_ring()
    result = simplifyPolygon(ring, maxPoint=7, expand=True)

    assert len(result) <= 7
    assert_covers_all(result, ring)


def test_expand_covers_adjacent_cut_edges():
    # two consecutive simplified edges cut off vertices
    ring = [
        (0.0, 0.0), (0.0, 10.0), (10.0, 10.0), (13.0, 7.5),
        (15.0, 5.0), (13.0, 2.5), (10.0, 0.0),
    ]
    result = simplifyPolygon(ring, maxPoint=6, expand=True)

    assert len(result) <= 6
    assert_covers_all(result, ring)


def test_expand_outward_for_both_orientations():
    # the outward side must follow the ring orientation, not always 'left'
    ccw = [(0.0, 0.0), (10.0, 0.0), (11.0, 5.0), (10.0, 10.0), (0.0, 10.0)]
    for ring in (ccw, list(reversed(ccw))):
        result = simplifyPolygon(ring, maxPoint=5, expand=True)

        assert_covers_all(result, ring)
        assert Polygon(result).exterior.is_ccw == Polygon(ring).exterior.is_ccw


def test_expand_without_cut_edges_returns_simplified():
    # a wiggle smaller than the tolerance never produces cut edges
    ring = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0)]
    for x in range(9, 0, -1):
        ring.append((float(x), 10.0 + (0.05 if x % 2 else -0.05)))
    ring.append((0.0, 10.0))

    assert simplifyPolygon(ring, maxPoint=7, expand=True) == simplifyToMaxPoint(ring, maxPoint=7)


def test_expand_with_duplicated_vertices():
    ring = jagged_coast_ring()
    ring = ring[:4] + [ring[3]] + ring[4:]  # duplicate a vertex on the ring

    result = simplifyPolygon(ring, maxPoint=7, expand=True)
    assert_covers_all(result, ring)


def test_find_cut_edges_includes_closing_edge():
    ring = jagged_coast_ring()
    simplified = simplifyToMaxPoint(ring, maxPoint=7)

    cuts = findCutEdges(ring, simplified)
    assert len(cuts) == 1
    assert cuts[0]['index'] == len(simplified) - 2  # the closing edge
    assert cuts[0]['distance'] > 0.8  # the seam vertices stick out by 1.0 horizontally
