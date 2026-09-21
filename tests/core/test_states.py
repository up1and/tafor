"""Tests for the services in tafor/core/states.py.

Only the layer projection is covered here. It is the one place that turns the
Layer/Projection setting into a plane the canvas can draw on, and the fallback
for a setting the geometry layer refuses lives here rather than in the
projection module: what to draw when the setting cannot be served is a
configuration decision, not a geometric one.
"""

import logging

import pytest

from tafor.core.geometry import projection


@pytest.fixture
def restore_projection(conf):
    """conf is session-scoped: restore the setting after each test."""
    yield
    conf.projection = type(conf).projection.default


class TestLayerProjection:

    def test_serves_the_configured_projection(self, conf, context, restore_projection):
        conf.projection = '+proj=eqc'

        assert type(context.layer.projection()) is projection.Equirectangular

    def test_the_shipped_default_is_served(self, conf, context, restore_projection):
        # guards config.py: a default the geometry layer refuses would mean
        # every fresh install starts on the fallback
        conf.projection = type(conf).projection.default

        assert type(context.layer.projection()) is projection.WebMercator

    @pytest.mark.parametrize('definition', [
        '+proj=lcc +lat_1=30 +lat_2=60 +datum=WGS84',   # a projection we do not implement
        '+proj=webmerc +R=6371000',                     # known name, radius override
        '',                                             # empty setting
    ])
    def test_unserved_settings_fall_back_to_web_mercator(
            self, definition, conf, context, restore_projection, caplog):
        conf.projection = definition

        with caplog.at_level(logging.WARNING):
            assert type(context.layer.projection()) is projection.WebMercator

        assert 'Cannot serve' in caplog.text

    def test_the_setting_is_left_untouched(self, conf, context, restore_projection):
        # the fallback used to be written back into the setting, which would
        # replace what the user typed with something they did not
        conf.projection = '+proj=lcc +lat_1=30 +lat_2=60'

        context.layer.projection()

        assert conf.projection == '+proj=lcc +lat_1=30 +lat_2=60'
