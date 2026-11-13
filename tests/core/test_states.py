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
from tafor.core.models import Sigmet, Taf
from tafor.core.states import SequenceService


@pytest.fixture
def restore_projection(conf):
    """conf is session-scoped: restore the setting after each test."""
    yield
    conf.projection = type(conf).projection.default


@pytest.fixture
def sequence(conf, frozen_time):
    """Built after the clock is frozen, so its checkpoint is the frozen day."""
    service = SequenceService(conf)
    yield service
    conf.set('channelSequenceNumber', '1')
    conf.set('fileSequenceNumber', '1')


class TestSequenceService:

    def test_rollover_resets_both_counters_once_a_day(self, conf, sequence, frozen_time, time_machine):
        conf.set('channelSequenceNumber', '7')
        conf.set('fileSequenceNumber', '4')

        time_machine.move_to(frozen_time + datetime.timedelta(days=1))

        assert sequence.rollover() is True
        assert conf.channelSequenceNumber == '1'
        assert conf.fileSequenceNumber == '1'

    def test_rollover_is_a_no_op_within_the_same_day(self, conf, sequence, frozen_time, time_machine):
        conf.set('channelSequenceNumber', '7')
        conf.set('fileSequenceNumber', '4')

        time_machine.move_to(frozen_time + datetime.timedelta(hours=1))

        assert sequence.rollover() is False
        assert conf.channelSequenceNumber == '7'
        assert conf.fileSequenceNumber == '4'


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


class TestReadOnlyCollections:
    """The service getters look read-only, so what they return must not be a
    handle on the shared state either."""

    def test_the_remote_feed_is_a_copy(self, context):
        context.message.setState({'FT': 'TAF ZPPP 100800Z='})

        context.message.message().clear()

        assert context.message.message() == {'FT': 'TAF ZPPP 100800Z='}

    def test_the_layer_list_is_a_copy(self, context):
        context.layer.setLayer([{'name': 'Satellite'}])

        context.layer.getLayers().clear()

        assert [layer.name for layer in context.layer.getLayers()] == ['Satellite']


class TestCurrentSigmetService:

    def test_a_poll_replaces_the_instances_even_when_the_text_matches(self, context):
        first = Sigmet(type='WS', text='WS 1')
        context.current.setState([first])
        refreshed = Sigmet(type='WS', text='WS 1')

        assert context.current.setState([refreshed]) is False
        # nothing to redraw, but nobody keeps reading the row it replaced
        assert context.current.state.sigmets[0] is refreshed

    def test_a_metadata_change_stays_quiet_but_replaces_the_row(self, context):
        context.current.setState([Sigmet(type='WS', text='WS 1')])
        seen = []
        context.event.currentSigmetChanged.connect(lambda: seen.append(1))

        confirmed = Sigmet(type='WS', text='WS 1', confirmed=datetime.datetime(2026, 6, 10, 8, 0))

        assert context.current.setState([confirmed]) is False
        assert seen == []
        # the graphic does not read confirmation, but the recent board does
        assert context.current.state.sigmets[0] is confirmed

    def test_new_text_is_announced(self, context):
        context.current.setState([Sigmet(type='WS', text='WS 1')])
        seen = []
        context.event.currentSigmetChanged.connect(lambda: seen.append(1))

        assert context.current.setState([Sigmet(type='WS', text='WS 2')]) is True
        assert seen == [1]

    def test_the_filtered_list_is_a_copy(self, context):
        context.current.setState([Sigmet(type='WS', text='WS 1')])

        context.current.filterSigmets().clear()

        assert len(context.current.filterSigmets()) == 1


class TestLayerService:

    def test_an_identical_fetch_stays_quiet(self, context):
        context.layer.setLayer([{'name': 'Satellite', 'image': b'same'}])
        first = context.layer.state.layers[0]
        seen = []
        context.event.layersChanged.connect(lambda: seen.append(1))

        context.layer.setLayer([{'name': 'Satellite', 'image': b'same'}])

        assert seen == []
        # the instances are still fresh; only the redraw is skipped
        assert context.layer.state.layers[0] is not first

    def test_a_new_image_is_announced(self, context):
        context.layer.setLayer([{'name': 'Satellite', 'image': b'old'}])
        seen = []
        context.event.layersChanged.connect(lambda: seen.append(1))

        context.layer.setLayer([{'name': 'Satellite', 'image': b'new'}])

        assert seen == [1]
        assert context.layer.getLayers()[0].image == b'new'

    def test_the_fetch_selects_the_first_standalone_layer(self, context):
        context.layer.setLayer([
            {'name': 'Radar', 'overlay': 'mixed'},
            {'name': 'Satellite', 'overlay': 'standalone'},
        ])

        assert context.layer.selected == ['Satellite']

    def test_a_fetch_that_drops_the_selected_layer_picks_a_replacement(self, context):
        context.layer.setLayer([{'name': 'Satellite'}, {'name': 'Radar'}])
        context.layer.setState({'selected': ['Radar']})
        seen = []
        context.event.layersChanged.connect(lambda: seen.append(1))

        context.layer.setLayer([{'name': 'Satellite'}])

        assert context.layer.selected == ['Satellite']
        # the fetch is the broad notification; no second one for the selection
        assert seen == [1]

    def test_a_selection_write_is_a_layer_change(self, context):
        context.layer.setLayer([{'name': 'Satellite'}, {'name': 'Radar'}])
        seen = []
        context.event.layersChanged.connect(lambda: seen.append(1))

        context.layer.setState({'selected': ['Radar']})

        assert context.layer.selected == ['Radar']
        assert seen == [1]
