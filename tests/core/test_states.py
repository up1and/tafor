"""Tests for the services in tafor/core/states.py.

Only the layer projection is covered here. It is the one place that turns the
Layer/Projection setting into a plane the canvas can draw on, and the fallback
for a setting the geometry layer refuses lives here rather than in the
projection module: what to draw when the setting cannot be served is a
configuration decision, not a geometric one.
"""

import datetime
import logging

import pytest

from tafor.core.geometry import projection
from tafor.core.models import Taf


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


class TestTafMonitor:
    """The monitor stores facts; time decides what they mean."""

    @pytest.fixture
    def monitor_conf(self, conf):
        spec, delay = conf.tafSpec, conf.delayMinutes
        yield conf
        conf.tafSpec, conf.delayMinutes = spec, delay

    @pytest.fixture
    def monitor(self, monitor_conf, context, frozen_time):
        monitor_conf.tafSpec = 0        # SpecFC
        monitor_conf.delayMinutes = 0   # deadline 07:50 at the frozen 08:00
        return context.taf

    def seed(self, monitor):
        monitor.setState({
            'period': monitor.period(),
            'message': None,
            'confirmed': False,
            'cancelled': False,
        })

    def test_the_clock_alone_flips_the_alarm(self, monitor, time_machine):
        time_machine.move_to(datetime.datetime(2026, 6, 10, 7, 45), tick=False)
        self.seed(monitor)
        assert monitor.isExpired() is False

        # No data event and no repository read: only the clock moved.
        time_machine.move_to(datetime.datetime(2026, 6, 10, 8, 0), tick=False)
        assert monitor.isExpired() is True
        assert monitor.shouldRemind() is True

    def test_the_operator_tolerance_is_added_to_the_spec_delay(self, monitor, monitor_conf):
        # The deadline is 07:50 at zero tolerance, so 30 minutes of tolerance
        # pushes it to 08:20 -- past the frozen 08:00.
        self.seed(monitor)
        assert monitor.isExpired() is True

        monitor_conf.delayMinutes = 30
        assert monitor.isExpired() is False

    def test_a_confirmed_report_clears_the_alarm(self, monitor):
        message = Taf(type='FC', text='TAF ZPPP 100800Z 1009/1018 32008MPS=')
        self.seed(monitor)
        monitor.setState({'message': message, 'confirmed': True})

        assert monitor.isExpired() is False
        assert monitor.shouldRemind() is False

    def test_an_unconfirmed_report_keeps_the_alarm(self, monitor):
        message = Taf(type='FC', text='TAF ZPPP 100800Z 1009/1018 32008MPS=')
        self.seed(monitor)
        monitor.setState({'message': message, 'confirmed': False})

        assert monitor.isExpired() is True
        assert monitor.shouldRemind() is False

    def test_a_cancellation_suppresses_both(self, monitor):
        self.seed(monitor)
        monitor.setState({'cancelled': True})

        assert monitor.isExpired() is False
        assert monitor.shouldRemind() is False

    def test_a_snapshot_from_another_period_is_ignored(self, monitor):
        message = Taf(type='FC', text='TAF ZPPP 100800Z 1009/1018 32008MPS=')
        monitor.setState({
            'period': 'stale/period',
            'message': message,
            'confirmed': False,
            'cancelled': False,
        })

        assert monitor.message is None
        assert monitor.isExpired() is False
        assert monitor.shouldRemind() is False

    def test_set_state_reports_only_real_changes(self, monitor):
        values = {
            'period': monitor.period(),
            'message': None,
            'confirmed': False,
            'cancelled': False,
        }
        assert monitor.setState(values) is True
        assert monitor.setState(dict(values)) is False

        values['message'] = Taf(type='FC', text='TAF ZPPP 100800Z 1009/1018 32008MPS=')
        assert monitor.setState(values) is True
