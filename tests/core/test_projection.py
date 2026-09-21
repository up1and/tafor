"""Tests for tafor/core/geometry/projection.py.

The canvas projections are closed forms, so the values are pinned against
their definitions rather than recomputed from the same formula: Web Mercator
is the sphere of radius 6378137 unrolled, equirectangular keeps the degree
spacing, and longlat is the identity. The expected numbers were cross-checked
against pyproj's ``+proj=webmerc`` / ``+proj=eqc`` bit for bit before pyproj
was dropped from the dependencies.

A configured string the canvas cannot serve is refused here rather than
silently drawn as something else. What the canvas falls back to instead is
decided where the setting is read, and is covered by test_states.py.
"""

import pytest

from tafor.core.geometry import projection


class TestWebMercator:
    """EPSG:3857 -- the sphere of radius 6378137 unrolled."""

    def test_forward_matches_the_definition(self):
        proj = projection.proj('+proj=webmerc +datum=WGS84')

        assert proj.forward(110.0, 15.0) == pytest.approx((12245143.987260, 1689200.139608), abs=1e-5)

    def test_origin_is_exactly_the_origin(self):
        # the canvas asserts no pixel offset at (0, 0); the textbook
        # ln(tan(pi/4 + lat/2)) form misses by 7e-10 there and would carry
        # that drift onto the canvas
        proj = projection.proj('+proj=webmerc')

        assert proj.forward(0.0, 0.0) == (0.0, 0.0)

    def test_y_grows_northward_and_is_symmetric(self):
        proj = projection.proj('+proj=webmerc')

        assert proj.forward(0.0, 15.0)[1] == pytest.approx(-proj.forward(0.0, -15.0)[1], abs=1e-9)

    def test_is_not_geographic(self):
        assert projection.proj('+proj=webmerc').geographic is False

    def test_round_trip(self):
        proj = projection.proj('+proj=webmerc')

        for lon, lat in [(110.0, 15.0), (-73.5, 40.7), (0.0, 60.0), (0.0, 0.0)]:
            assert proj.inverse(*proj.forward(lon, lat)) == pytest.approx((lon, lat), abs=1e-9)


class TestEquirectangular:
    """EPSG:32662 -- degrees scaled by the radius."""

    def test_forward_matches_the_definition(self):
        proj = projection.proj('+proj=eqc')

        # the same x as Web Mercator, y linear in latitude instead
        assert proj.forward(110.0, 15.0) == pytest.approx((12245143.987260, 1669792.361899), abs=1e-5)

    def test_origin_is_exactly_the_origin(self):
        proj = projection.proj('+proj=eqc')

        assert proj.forward(0.0, 0.0) == (0.0, 0.0)

    def test_is_not_geographic(self):
        assert projection.proj('+proj=eqc').geographic is False

    def test_round_trip(self):
        proj = projection.proj('+proj=eqc')

        for lon, lat in [(110.0, 15.0), (-73.5, 40.7), (137.0, 30.0)]:
            assert proj.inverse(*proj.forward(lon, lat)) == pytest.approx((lon, lat), abs=1e-9)


class TestLongLat:
    """Geographic coordinates -- the plane stays in degrees."""

    def test_forward_is_the_identity(self):
        proj = projection.proj('+proj=longlat +ellps=WGS84')

        assert proj.forward(110.0, 15.0) == (110.0, 15.0)
        assert proj.inverse(110.0, 15.0) == (110.0, 15.0)

    def test_is_geographic(self):
        # this is what tells the canvas to scale by 100 rather than 1/1000
        assert projection.proj('+proj=longlat +ellps=WGS84').geographic is True


class TestProj:
    """The ``+proj`` name picks the class, everything else is refused."""

    @pytest.mark.parametrize('definition, served', [
        ('+proj=webmerc +datum=WGS84', projection.WebMercator),
        ('+proj=eqc +ellps=WGS84 +no_defs', projection.Equirectangular),
        ('+proj=longlat +datum=WGS84', projection.LongLat),
    ])
    def test_the_name_selects_the_class(self, definition, served):
        assert type(projection.proj(definition)) is served

    def test_datum_ellps_and_units_do_not_trip_the_refusal(self):
        # they leave the closed forms alone, so they must be accepted even
        # though the projection is not named on its own
        assert type(projection.proj('+proj=webmerc +datum=WGS84 +units=m +no_defs')) \
            is projection.WebMercator

    @pytest.mark.parametrize('definition', [
        '+proj=lcc +lat_1=30 +lat_2=60 +datum=WGS84',   # a projection we do not implement
        '+proj=aeqd +lat_0=15 +lon_0=110 +units=m',     # unknown name, and an offset too
        '+proj=eqc +lat_ts=30',                         # known name, reshaping parameter
        '+proj=webmerc +R=6371000',                     # known name, radius override
        '',                                             # empty setting
        None,                                           # never configured
    ])
    def test_unserved_strings_are_refused(self, definition):
        with pytest.raises(projection.UnsupportedProjection):
            projection.proj(definition)

    def test_the_message_says_which_part_was_refused(self):
        # the caller logs this message, so it has to name the actual reason
        with pytest.raises(projection.UnsupportedProjection, match='unknown projection'):
            projection.proj('+proj=lcc +lat_1=30')

        with pytest.raises(projection.UnsupportedProjection, match='unsupported parameter lat_ts'):
            projection.proj('+proj=eqc +lat_ts=30')


class TestSplit:
    """The proj string is read as a name plus the parameters that matter."""

    def test_reads_the_name_and_the_offset_parameters(self):
        assert projection.split('+proj=eqc +lat_ts=30 +datum=WGS84') == ('eqc', ['lat_ts'])

    def test_parameters_that_do_not_move_the_plane_are_not_offset(self):
        assert projection.split('+proj=webmerc +datum=WGS84 +units=m') == ('webmerc', [])

    def test_a_string_without_a_name_has_no_offset(self):
        assert projection.split('+datum=WGS84') == ('', [])
