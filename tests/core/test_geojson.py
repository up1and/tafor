import json

import pytest

import shapely.geometry

from tafor.core.geometry import geojson


class TestConstruction:

    def test_point_normalises_the_coordinate_to_a_list(self):
        assert geojson.point((110.0, 20.0)) == {
            'type': 'Point', 'coordinates': [110.0, 20.0]}

    def test_line_string_holds_the_points_in_order(self):
        points = [(110.0, 20.0), (111.0, 21.0)]
        assert geojson.lineString(points) == {
            'type': 'LineString', 'coordinates': points}

    def test_polygon_takes_a_single_ring(self):
        ring = [(110.0, 20.0), (111.0, 21.0), (112.0, 20.0)]
        assert geojson.polygon(ring) == {'type': 'Polygon', 'coordinates': ring}

    def test_multi_polygon_takes_one_ring_per_area(self):
        rings = [[(0, 0), (1, 0), (1, 1)], [(5, 5), (6, 5), (6, 6)]]
        assert geojson.multiPolygon(rings) == {
            'type': 'MultiPolygon', 'coordinates': rings}

    def test_feature_carries_the_properties_the_map_reads(self):
        assert geojson.feature(geojson.point((1, 2)), location='initial') == {
            'type': 'Feature',
            'geometry': {'type': 'Point', 'coordinates': [1, 2]},
            'properties': {'location': 'initial'},
        }

    def test_feature_without_a_geometry_omits_the_key(self):
        assert geojson.feature(location='initial') == {
            'type': 'Feature',
            'properties': {'location': 'initial'},
        }

    def test_collections_hold_what_they_are_given(self):
        assert geojson.featureCollection([]) == {
            'type': 'FeatureCollection', 'features': []}
        assert geojson.geometryCollection([]) == {
            'type': 'GeometryCollection', 'geometries': []}

    def test_sequences_are_copied_into_lists(self):
        ring = (point for point in [(0, 0), (1, 0), (1, 1)])
        assert geojson.polygon(ring)['coordinates'] == [(0, 0), (1, 0), (1, 1)]


class TestHasGeometry:

    def test_the_missing_sentinel_has_nothing_to_draw(self):
        assert geojson.hasGeometry(None) is False

    def test_an_empty_dict_has_nothing_to_draw(self):
        assert geojson.hasGeometry({}) is False

    def test_a_feature_without_a_geometry_has_nothing_to_draw(self):
        assert geojson.hasGeometry(geojson.feature(location='initial')) is False

    def test_a_feature_with_a_geometry_draws(self):
        assert geojson.hasGeometry(geojson.feature(geojson.point((1, 2)))) is True


class TestRepresentation:

    def test_every_document_survives_json(self):
        documents = [
            geojson.point((1.0, 2.0)),
            geojson.lineString([(1.0, 2.0)]),
            geojson.polygon([(0.0, 0.0), (1.0, 0.0), (1.0, 1.0)]),
            geojson.multiPolygon([[(0.0, 0.0), (1.0, 0.0), (1.0, 1.0)]]),
            geojson.feature(geojson.point((1.0, 2.0)), location='initial'),
            geojson.featureCollection([]),
            geojson.geometryCollection([]),
        ]
        for document in documents:
            json.dumps(document)

    @pytest.mark.xfail(
        strict=True,
        reason='geojson.polygon writes a bare ring; RFC 7946 wraps that ring in a '
               'list, so shapely treats each position as a ring and rejects the '
               'shape. Delete this marker once polygon() nests its ring.',
    )
    def test_a_polygon_is_nested_the_way_rfc_7946_reads_it(self):
        ring = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0)]
        shapely.geometry.shape(geojson.polygon(ring))
