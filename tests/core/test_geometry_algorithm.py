import math

import pytest
from shapely.geometry import LineString, Point, Polygon

from tafor.core.geometry.algorithm import (
    bearingToDirection, circle, clipLine, clipPolygon, collinearWith, corridor,
    decode, decodeLine, decodePolygon, determineDirection, encode,
    expandToCover, findCutEdges, findDrawnLineEdges, findLines,
    geodesicDistance, groupCollinearLines, halfPlane, linesIntersection,
    mergeCollinearLines, overlaps, principalAxis, simplifyPolygon,
    simplifyToMaxPoint, geod,
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
    points = jagged_coast_ring()
    simplified = simplifyToMaxPoint(points, maxPoint=7)

    assert len(simplified) <= 7
    assert simplified[0] == simplified[-1]  # closed ring
    assert Polygon(simplified).is_valid
    # every vertex must be an original vertex: findCutEdges matches the
    # simplified edges back to the original ring by index
    assert all(vertex in points for vertex in simplified)


def test_simplify_keeps_the_polygon_that_is_small_enough():
    points = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0), (0.0, 0.0)]

    assert simplifyToMaxPoint(points, maxPoint=7) == points


def test_clip_line_keeps_the_longest_piece_of_a_concave_polygon():
    # a U-shaped polygon (two columns on a bar) cuts the y=3 line into two
    # pieces: (0,3)-(4,3) and (8,3)-(13,3); the longer right one must survive
    polygon = [(0.0, 0.0), (13.0, 0.0), (13.0, 6.0), (8.0, 6.0),
               (8.0, 2.0), (4.0, 2.0), (4.0, 6.0), (0.0, 6.0)]
    points = clipLine(polygon, [(-2.0, 3.0), (15.0, 3.0)])

    # the ends sit a hair outside the original edges: the clip runs
    # against the tolerance-grown boundary
    assert points[0] == pytest.approx((8.0, 3.0), abs=1e-4)
    assert points[1] == pytest.approx((13.0, 3.0), abs=1e-4)


def test_clip_line_keeps_the_line_inside_the_polygon():
    polygon = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    points = clipLine(polygon, [(2.0, 5.0), (8.0, 5.0)])

    assert points == [(2.0, 5.0), (8.0, 5.0)]


def test_clip_line_keeps_a_line_on_the_boundary():
    # a line lying exactly on an edge must survive the clip
    polygon = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]

    assert clipLine(polygon, [(2.0, 10.0), (8.0, 10.0)]) == [(2.0, 10.0), (8.0, 10.0)]


def test_clip_line_tolerates_floating_point_error_on_the_boundary():
    # a line a floating point hair above the top edge used to be clipped
    # away entirely; the tolerance-grown polygon keeps it
    polygon = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    edge = [(2.0, 10.0 + 1e-12), (8.0, 10.0 + 1e-12)]

    assert clipLine(polygon, edge) == edge


def test_clip_line_with_a_two_corner_graze_returns_no_usable_line():
    # the line passes exactly through two polygon corners without
    # entering: the tolerance grows the intersection into tiny slivers
    # around the corners, which fall below the noise floor
    polygon = [(0.0, 0.0), (10.0, 0.0), (10.0, 5.0), (5.0, 5.0), (5.0, 10.0), (0.0, 10.0)]

    assert clipLine(polygon, [(0.0, 15.0), (15.0, 0.0)]) == []


def test_clip_line_with_a_single_corner_graze_returns_no_usable_line():
    # a lone corner touch yields a bare point intersection; there is no
    # usable segment, so the clip degrades to an empty line
    polygon = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]

    assert clipLine(polygon, [(-5.0, 5.0), (5.0, 15.0)]) == []


def test_clip_line_ignores_point_touches_in_a_mixed_intersection():
    # an L-shaped polygon: the line clips the left column and afterwards
    # only grazes past the bar corner, so the intersection mixes a line
    # piece with point geometries and slivers; only the line piece
    # survives
    polygon = [(0.0, 0.0), (10.0, 0.0), (10.0, 5.0), (5.0, 5.0), (5.0, 10.0), (0.0, 10.0)]

    clipped = clipLine(polygon, [(-5.0, 8.0), (15.0, 4.0)])
    assert clipped[0] == pytest.approx((0.0, 7.0), abs=1e-4)
    assert clipped[1] == pytest.approx((5.0, 6.0), abs=1e-4)


def test_clip_line_with_a_degenerate_line_returns_no_usable_line():
    polygon = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]

    assert clipLine(polygon, [(5.0, 5.0), (5.0, 5.0)]) == []


def test_clip_line_misses_the_polygon():
    polygon = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]

    assert clipLine(polygon, [(-5.0, 3.0), (-1.0, 3.0)]) == []


def test_clip_polygon_keeps_the_largest_piece():
    # a horizontal bar clipped by a U-shaped subject cuts through both
    # arms and leaves two pieces, the wider right one must survive
    subj = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (7.0, 10.0),
            (7.0, 2.0), (2.0, 2.0), (2.0, 10.0), (0.0, 10.0)]
    clip = [(-2.0, 4.0), (12.0, 4.0), (12.0, 6.0), (-2.0, 6.0)]

    points = clipPolygon(subj, clip)

    assert points == [(10.0, 4.0), (7.0, 4.0), (7.0, 6.0), (10.0, 6.0), (10.0, 4.0)]


def test_clip_polygon_multi_mode_returns_every_ring():
    subj = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (7.0, 10.0),
            (7.0, 2.0), (2.0, 2.0), (2.0, 10.0), (0.0, 10.0)]
    clip = [(-2.0, 4.0), (12.0, 4.0), (12.0, 6.0), (-2.0, 6.0)]

    points = clipPolygon(subj, clip, mode='multi')

    assert len(points) == 2
    assert sorted(Polygon(ring).area for ring in points) == [4.0, 6.0]


def test_clip_polygon_without_overlap_returns_empty():
    subj = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    clip = [(20.0, 20.0), (30.0, 20.0), (30.0, 30.0), (20.0, 30.0)]

    assert clipPolygon(subj, clip) == []


def test_corridor_width_is_metric_at_any_latitude():
    # width extends outwards on each side: 200 km means 400 km across
    polygon = corridor([(0.0, 0.0), (1.0, 0.0)], 200000)

    assert polygon.geom_type == 'Polygon'
    assert polygon.area > 0
    _, _, distance = geod.inv(0.5, polygon.bounds[1], 0.5, polygon.bounds[3])
    assert distance / 1000 == pytest.approx(400.0, abs=0.1)

    # the degree-space approximation used to be 25% off at 60 degrees north
    polygon = corridor([(0.0, 60.0), (2.0, 60.0)], 50000)

    _, _, distance = geod.inv(1.0, polygon.bounds[1], 1.0, polygon.bounds[3])
    assert distance / 1000 == pytest.approx(100.0, abs=0.1)


def test_geodesic_distance_is_metric():
    # one degree of longitude at the equator, one degree of latitude
    assert geodesicDistance((0.0, 0.0), (1.0, 0.0)) == pytest.approx(111319.49, abs=1.0)
    assert geodesicDistance((0.0, 0.0), (0.0, 1.0)) == pytest.approx(110574.39, abs=1.0)


def test_circle_is_a_geodesic_ring_around_the_center():
    ring = circle((120.0, 30.0), 111000)

    assert ring.geom_type == 'Polygon'
    assert ring.is_valid
    for lon, lat in list(ring.exterior.coords)[:-1]:
        assert geodesicDistance((120.0, 30.0), (lon, lat)) == pytest.approx(111000.0, abs=1.0)

    # 111 km is one degree; at 30N a degree of longitude shrinks to cos(30)
    minx, miny, maxx, maxy = ring.bounds
    assert (maxy - miny) / 2 == pytest.approx(1.0, abs=0.01)
    assert (maxx - minx) / 2 == pytest.approx(1.1547, abs=0.01)


def test_simplify_polygon_without_expand():
    ring = jagged_coast_ring()
    assert simplifyPolygon(ring, maxPoint=7) == simplifyToMaxPoint(ring, maxPoint=7)


def test_small_polygon_returned_unchanged():
    ring = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    assert simplifyPolygon(ring, maxPoint=7) == ring


def test_simplify_gives_up_on_an_impossible_max_point():
    # a square ring has at least 5 exterior coordinates, 3 can never be
    # reached: give up with an empty list instead of returning a shape
    # that violates maxPoint (the old behaviour)
    ring = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    assert simplifyToMaxPoint(ring, maxPoint=3) == []


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


def test_expand_without_simplified_returns_it_unchanged():
    # nothing to expand: the simplification gave up entirely
    ring = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0)]

    assert expandToCover(ring, []) == []


def test_find_cut_edges_includes_closing_edge():
    ring = jagged_coast_ring()
    simplified = simplifyToMaxPoint(ring, maxPoint=7)

    cuts = findCutEdges(ring, simplified)
    assert len(cuts) == 1
    assert cuts[0]['index'] == len(simplified) - 2  # the closing edge
    assert cuts[0]['distance'] > 0.8  # the seam vertices stick out by 1.0 horizontally


def test_collinear_with_accepts_same_line_and_rejects_parallel():
    base = LineString([(0.0, 0.0), (10.0, 0.0)])
    assert collinearWith(base, LineString([(2.0, 0.0), (6.0, 0.0)]))
    assert collinearWith(base, LineString([(11.0, 0.0), (15.0, 0.0)]))  # gapped, same line
    assert not collinearWith(base, LineString([(2.0, 1.0), (6.0, 1.0)]))  # parallel, offset
    assert not collinearWith(base, LineString([(2.0, 0.0), (6.0, 0.5)]))  # tilted beyond tolerance


def test_collinear_with_handles_vertical_lines():
    # the old slope() approach returned None for vertical lines
    base = LineString([(5.0, 0.0), (5.0, 10.0)])
    assert collinearWith(base, LineString([(5.0, 2.0), (5.0, 4.0)]))
    assert not collinearWith(base, LineString([(6.0, 2.0), (6.0, 4.0)]))


def test_overlaps_counts_touching_segments():
    a = LineString([(0.0, 0.0), (10.0, 0.0)])
    assert overlaps(a, LineString([(5.0, 0.0), (15.0, 0.0)]))
    assert overlaps(a, LineString([(10.0, 0.0), (15.0, 0.0)]))  # touching at a point
    assert not overlaps(a, LineString([(15.0, 0.0), (20.0, 0.0)]))  # collinear but disjoint
    # note: any touching counts, even a crossing; the predicate is only
    # meaningful for pieces already grouped as collinear


def test_group_collinear_lines():
    lines = [
        LineString([(0.0, 0.0), (5.0, 0.0)]),
        LineString([(0.0, 1.0), (5.0, 1.0)]),  # parallel, own group
        LineString([(2.0, 0.0), (7.0, 0.0)]),  # collinear with the first
        LineString([(7.0, 0.0), (7.0, 5.0)]),  # vertical, own group
    ]

    groups = groupCollinearLines(lines)
    assert sorted(len(group) for group in groups) == [1, 1, 2]


def test_merge_collinear_lines_spans_the_union():
    merged = mergeCollinearLines([
        LineString([(2.0, 0.0), (6.0, 0.0)]),
        LineString([(4.0, 0.0), (12.0, 0.0)]),
        LineString([(-3.0, 0.0), (1.0, 0.0)]),
    ])

    assert sorted([merged.coords[0], merged.coords[-1]]) == [(-3.0, 0.0), (12.0, 0.0)]


def test_find_drawn_line_edges_strips_boundary_arcs():
    fir = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    polygon = [(0.0, 0.0), (10.0, 0.0), (10.0, 5.0), (0.0, 5.0)]

    edges = findDrawnLineEdges(fir, polygon)

    assert len(edges) == 1
    assert edges[0].coords[0] == (10.0, 5.0)
    assert edges[0].coords[-1] == (0.0, 5.0)


def test_find_lines_merges_collinear_overlapping_pieces():
    fir = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    polygons = [
        [(0.0, 0.0), (10.0, 0.0), (10.0, 5.0), (0.0, 5.0)],
        [(0.0, 5.0), (10.0, 5.0), (10.0, 8.0), (0.0, 8.0)],
    ]

    lines = findLines(fir, polygons)

    # the duplicated y=5 pieces collapse into the piece spanning the union
    at5 = [line for line in lines
           if abs(line.coords[0][1] - 5.0) < 1e-9 and abs(line.coords[-1][1] - 5.0) < 1e-9]
    assert len(at5) == 1
    assert sorted([at5[0].coords[0][0], at5[0].coords[-1][0]]) == [0.0, 10.0]
    assert len(lines) == 2  # plus the y=8 edge of the second polygon


def test_bearing_to_direction():
    assert bearingToDirection(0.0) == 'E'
    assert bearingToDirection(math.pi / 2) == 'N'
    assert bearingToDirection(math.pi) == 'W'
    assert bearingToDirection(-math.pi / 2) == 'S'


def test_encode_line_mode_reports_line_with_direction():
    fir = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    polygon = [(0.0, 0.0), (10.0, 0.0), (10.0, 5.0), (0.0, 5.0)]

    assert encode(fir, polygon, 'line') == [['S', (10.0, 5.0), (0.0, 5.0)]]


def test_encode_line_gives_up_on_too_many_lines():
    # two blocks sitting on the FIR bottom edge: each contributes three
    # non-boundary edges, six lines in total, too fragmented for a line
    # report
    fir = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    polygons = [
        [(1.0, 0.0), (3.0, 0.0), (3.0, 1.0), (1.0, 1.0)],
        [(5.0, 0.0), (7.0, 0.0), (7.0, 1.0), (5.0, 1.0)],
    ]

    assert encode(fir, polygons, 'line') == []


def test_encode_line_reports_exactly_three_lines():
    # the closing edge is not examined, so a fifth vertex is needed to cut
    # exactly three non-boundary edges: at the limit, still encoded as the
    # stitched polyline around the area
    fir = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    polygon = [(1.0, 0.0), (3.0, 0.0), (3.0, 2.0), (1.0, 2.0), (1.0, 1.0)]

    segment = encode(fir, polygon, 'line')

    assert segment == [['SW', (3.0, 0.0), (3.0, 2.0), (1.0, 2.0), (1.0, 1.0)]]


def test_encode_line_reports_separate_pieces_with_own_directions():
    # one block with two connected edges and one triangle with a single
    # edge: linemerge cannot stitch the pieces into one line, each piece
    # is reported with the direction of its own area
    fir = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    polygons = [
        [(1.0, 0.0), (3.0, 0.0), (3.0, 1.0), (1.0, 1.0)],
        [(5.0, 0.0), (7.0, 0.0), (7.0, 1.0)],
    ]

    assert encode(fir, polygons, 'line') == [
        ['E', (3.0, 0.0), (3.0, 1.0), (1.0, 1.0)],
        ['W', (7.0, 0.0), (7.0, 1.0)],
    ]


def test_encode_rectangular_mode_reports_boundary_lines_with_direction():
    fir = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    polygon = [(0.0, 0.0), (10.0, 0.0), (10.0, 5.0), (0.0, 5.0)]

    assert encode(fir, polygon, 'rectangular') == [['S', (10.0, 5.0), (0.0, 5.0)]]


def test_find_lines_skips_polygon_entirely_inside_boundary():
    # a polygon that was never clipped has no FIR boundary edges, every edge
    # would be mistaken for the drawn line
    fir = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    polygon = [(2.0, 2.0), (8.0, 2.0), (8.0, 5.0), (2.0, 5.0)]

    assert findLines(fir, [polygon]) == []


def test_find_drawn_line_edges_keeps_line_parallel_near_boundary():
    # an edge parallel to and within the old 0.3 degree buffer of the boundary
    # is the drawn line, not a boundary arc
    fir = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    polygon = [(0.0, 0.0), (10.0, 0.0), (10.0, 9.8), (0.0, 9.8)]

    edges = findDrawnLineEdges(fir, polygon)

    assert len(edges) == 1
    assert edges[0].coords[0][1] == 9.8


def test_determine_direction_two_point_line():
    line = LineString([(0.0, 5.0), (10.0, 5.0)])
    polygon = [(0.0, 5.0), (10.0, 5.0), (10.0, 8.0), (0.0, 8.0)]

    assert determineDirection([line], [polygon]) == [['N', (0.0, 5.0), (10.0, 5.0)]]


def test_determine_direction_offset_polygon_reports_perpendicular():
    # the area hugs the west end of the line, the direction is still the
    # perpendicular one, not the bearing seen from the line midpoint
    line = LineString([(0.0, 5.0), (10.0, 5.0)])
    polygon = [(0.0, 5.0), (4.0, 5.0), (4.0, 8.0), (0.0, 8.0)]

    assert determineDirection([line], [polygon]) == [['N', (0.0, 5.0), (10.0, 5.0)]]


def test_determine_direction_polyline():
    line = LineString([(0.0, 5.0), (5.0, 5.0), (10.0, 5.0)])
    polygon = [(0.0, 5.0), (10.0, 5.0), (10.0, 8.0), (0.0, 8.0)]

    assert determineDirection([line], [polygon]) == [
        ['N', (0.0, 5.0), (5.0, 5.0), (10.0, 5.0)]]


def test_determine_direction_south_side():
    line = LineString([(0.0, 5.0), (10.0, 5.0)])
    polygon = [(0.0, 2.0), (10.0, 2.0), (10.0, 5.0), (0.0, 5.0)]

    assert determineDirection([line], [polygon]) == [['S', (0.0, 5.0), (10.0, 5.0)]]


def test_determine_direction_opposite_areas_cancel_out():
    # areas pulling to both sides: the vectors cancel and the line has no
    # well-defined direction, so it is skipped
    line = LineString([(0.0, 5.0), (10.0, 5.0)])
    north = [(0.0, 5.0), (10.0, 5.0), (10.0, 11.0), (0.0, 11.0)]
    south = [(0.0, 4.0), (4.0, 4.0), (4.0, 5.0), (0.0, 5.0)]

    assert determineDirection([line], [north, south]) == []


def test_determine_direction_areas_across_the_pi_seam():
    # bearings near +180 and -180: averaging the angles would yield 'E',
    # accumulating the unit vectors yields 'W'
    line = LineString([(5.0, 0.0), (5.0, 5.0), (5.0, 10.0)])
    north = [(1.0, 6.0), (5.0, 6.0), (5.0, 10.0), (1.0, 10.0)]
    south = [(1.0, 0.0), (3.0, 0.0), (3.0, 2.0), (5.0, 2.0), (5.0, 4.0), (1.0, 4.0)]

    assert determineDirection([line], [north, south]) == [
        ['W', (5.0, 0.0), (5.0, 5.0), (5.0, 10.0)]]


def test_determine_direction_skips_line_without_contributions():
    line = LineString([(0.0, 5.0), (10.0, 5.0)])
    far = [(0.0, 20.0), (10.0, 20.0), (10.0, 25.0), (0.0, 25.0)]

    assert determineDirection([line], [far]) == []


def test_determine_direction_ignores_degenerate_polygon():
    # a collinear ring has zero area, it contributes no direction
    line = LineString([(0.0, 5.0), (10.0, 5.0)])
    degenerate = [(0.0, 5.0), (5.0, 5.0), (10.0, 5.0)]
    good = [(0.0, 5.0), (10.0, 5.0), (10.0, 8.0), (0.0, 8.0)]

    assert determineDirection([line], [degenerate, good]) == [['N', (0.0, 5.0), (10.0, 5.0)]]


def test_principal_axis_returns_the_line_when_already_straight():
    line = LineString([(0.0, 5.0), (10.0, 5.0)])

    assert principalAxis(line) == line


def test_principal_axis_straightens_a_bent_polyline():
    # midpoints of the two short sides of the minimum rotated rectangle
    line = LineString([(0.0, 5.0), (5.0, 5.0), (5.0, 6.0), (10.0, 6.0)])
    axis = principalAxis(line)

    start, end = axis.coords
    for got, want in zip((start, end), ((9.9038, 6.4808), (0.0962, 4.5192))):
        assert all(abs(g - w) < 1e-3 for g, w in zip(got, want))


def test_determine_direction_bent_polyline_measured_against_its_axis():
    # the vector origin sits on the principal axis of the bent polyline,
    # not snapped to the bending corner
    line = LineString([(0.0, 5.0), (5.0, 5.0), (5.0, 6.0), (10.0, 6.0)])
    polygon = [(0.0, 5.0), (10.0, 6.0), (10.0, 9.0), (0.0, 8.0)]

    assert determineDirection([line], [polygon]) == [
        ['N', (0.0, 5.0), (5.0, 5.0), (5.0, 6.0), (10.0, 6.0)]]


# ---------------------------------------------------------------------------
# decode chain


def test_decode_line_north_side():
    boundary = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    area = decodeLine(Polygon(boundary), [('N', [(2.0, 5.0), (8.0, 5.0)])])

    assert area.area == 50.0
    assert area.covers(Point(5.0, 7.5))
    assert not area.intersects(Point(5.0, 2.5))


def test_decode_line_spans_a_large_boundary():
    # the line ends inside the boundary, the half-plane must still cover
    # the whole side: a fixed extension length used to miss large FIRs
    boundary = [(100.0, 0.0), (130.0, 0.0), (130.0, 15.0), (100.0, 15.0)]
    area = decodeLine(Polygon(boundary), [('N', [(105.0, 7.5), (125.0, 7.5)])])

    assert area.area == 225.0
    assert area.covers(Point(115.0, 14.0))
    assert not area.intersects(Point(115.0, 1.0))


def test_decode_line_intersects_multiple_lines():
    boundary = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    lines = [('N', [(2.0, 5.0), (8.0, 5.0)]), ('W', [(3.0, 2.0), (3.0, 8.0)])]
    area = decodeLine(Polygon(boundary), lines)

    assert area.area == 15.0
    assert area.covers(Point(1.5, 7.5))
    assert not area.intersects(Point(5.0, 7.5))
    assert not area.intersects(Point(1.5, 2.5))


def test_decode_line_polyline_keeps_the_whole_side():
    # north of the whole chevron path: the area is bounded below by the
    # polyline itself, not by the intersection of per-segment half-planes
    boundary = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    area = decodeLine(Polygon(boundary), [('N', [(2.0, 4.0), (6.0, 8.0), (10.0, 4.0)])])

    assert abs(area.area - 46.0) < 1e-9
    assert area.covers(Point(6.0, 9.0))
    assert area.covers(Point(5.0, 9.0))
    assert not area.intersects(Point(5.0, 5.0))


def test_decode_line_polyline_keeps_concave_area():
    # a step line bounds an L-shaped area; per-segment half-planes would
    # flatten it to the y >= 6 half-plane and lose the western wing
    boundary = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    area = decodeLine(Polygon(boundary),
                      [('N', [(0.0, 2.0), (5.0, 2.0), (5.0, 6.0), (10.0, 6.0)])])

    assert abs(area.area - 60.0) < 1e-9
    assert area.covers(Point(2.5, 4.0))
    assert area.covers(Point(7.5, 8.0))
    assert not area.intersects(Point(7.5, 4.0))
    assert not area.intersects(Point(2.5, 1.0))


def test_decode_line_parallel_direction_returns_empty():
    boundary = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    area = decodeLine(Polygon(boundary), [('N', [(5.0, 2.0), (5.0, 8.0)])])

    assert area.is_empty


def test_decode_rectangular_mode():
    # a FIR crossing the prime meridian, west of W003 and north of N05
    boundary = [(-10.0, 0.0), (10.0, 0.0), (10.0, 10.0), (-10.0, 10.0)]
    area = decode(boundary, [('N', 'N05'), ('W', 'W003')], 'rectangular')

    assert area.area == 35.0
    assert area.covers(Point(-5.0, 7.5))
    assert not area.intersects(Point(0.0, 7.5))
    assert not area.intersects(Point(-5.0, 2.5))


def test_decode_polygon_mode_parses_degree_strings():
    # locations come as (latitude, longitude) degree string pairs
    boundary = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    area = decode(boundary, [('N0500', 'E0500'), ('N0500', 'E1500'),
                             ('N1500', 'E1500'), ('N1500', 'E0500')], 'polygon')

    assert area.area == 25.0
    assert area.covers(Point(7.0, 7.0))
    assert not area.intersects(Point(12.0, 12.0))


def test_decode_line_mode_parses_degree_strings():
    # each line is the identifier followed by (latitude, longitude) pairs
    boundary = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    area = decode(boundary, [('N', ('N0500', 'E0200'), ('N0500', 'E0800'))], 'line')

    assert area.area == 50.0
    assert area.covers(Point(5.0, 7.5))
    assert not area.intersects(Point(5.0, 2.5))


def test_decode_circle_mode():
    # the report gives the center as degree strings and the radius in km
    boundary = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    area = decode(boundary, [('N3000', 'E12000'), (111, 'KM')], 'circle')

    minx, miny, maxx, maxy = area.bounds
    # 111 km is one degree; at 30N a degree of longitude shrinks to cos(30)
    assert (maxy - miny) / 2 == pytest.approx(1.0, abs=0.01)
    assert (maxx - minx) / 2 == pytest.approx(1.1547, abs=0.01)


def test_decode_corridor_mode():
    # a 100 km wide corridor along the diagonal, the width spans both sides
    boundary = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    area = decode(boundary, [[('N0000', 'E0000'), ('N0200', 'E0200')], (100, 'KM')], 'corridor')

    assert area.geom_type == 'Polygon'
    assert area.area > 0
    assert area.covers(Point(1.0, 1.0))


def test_decode_entire_mode_returns_the_boundary():
    boundary = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]

    assert decode(boundary, [], 'entire').area == 100.0


def test_decode_line_mode_without_boundary():
    # an invalid boundary cannot be split, so the line area is unknown
    assert decode([], [('N', ['N0500', 'N0800'])], 'line').is_empty


def test_decode_polygon_clips_to_boundary():
    boundary = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    area = decodePolygon(Polygon(boundary), [(5.0, 5.0), (15.0, 5.0), (15.0, 15.0), (5.0, 15.0)], True)

    assert area.area == 25.0
    assert area.covers(Point(7.0, 7.0))
    assert not area.intersects(Point(12.0, 12.0))


def test_decode_polygon_keeps_the_largest_piece():
    # a C-shaped polygon hooked over the right boundary edge leaves two pieces
    boundary = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    points = [(8.0, -2.0), (8.0, 2.0), (11.0, 2.0), (11.0, 8.0),
              (8.0, 8.0), (8.0, 12.0), (12.0, 12.0), (12.0, -2.0)]
    area = decodePolygon(Polygon(boundary), points, True)

    assert area.geom_type == 'Polygon'
    assert area.area == 4.0


def test_decode_polygon_touching_the_boundary_only():
    # the intersection is a line, not an area
    boundary = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    area = decodePolygon(Polygon(boundary), [(10.0, 0.0), (20.0, 0.0), (20.0, 10.0), (10.0, 10.0)], True)

    assert area.is_empty


def test_decode_polygon_without_trim_keeps_the_area():
    boundary = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    points = [(10.0, 0.0), (20.0, 0.0), (20.0, 10.0), (10.0, 10.0)]
    area = decodePolygon(Polygon(boundary), points, False)

    assert area.area == 100.0


def test_half_plane_is_not_limited_by_the_extension_of_old_code():
    boundary = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    plane = halfPlane('N', [(4.0, 5.0), (6.0, 5.0)], Polygon(boundary))

    # the plane extends far beyond the boundary on every side
    assert plane.covers(Point(0.0, 9.9))
    assert plane.covers(Point(9.9, 9.9))
    assert not plane.intersects(Point(5.0, 1.0))


def test_half_plane_repairs_a_self_intersecting_curtain():
    # a polyline with a north-going leg folds the curtain over itself;
    # buffer(0) untangles it into the band north/east of the line
    boundary = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    plane = halfPlane('N', [(5.0, 0.0), (5.0, 8.0), (10.0, 8.0)], Polygon(boundary))

    assert plane.is_valid
    assert plane.area == pytest.approx(270.7107, abs=0.01)
    assert plane.covers(Point(7.0, 9.0))
    assert not plane.intersects(Point(2.0, 2.0))


def test_half_plane_with_a_degenerate_line_keeps_no_area():
    # both endpoints identical: the curtain collapses, nothing is reported
    boundary = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]

    assert halfPlane('N', [(5.0, 5.0), (5.0, 5.0)], Polygon(boundary)) is None

