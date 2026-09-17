import pytest

from tafor.core.taf.states import GroupState, PrimaryState, SegmentState, TemperatureState, TrendState


# One representative value per content field of SegmentState. "Acceptable"
# means "there is something to transmit", so any one of these alone is enough.
CONTENT = {
    'wind': '27010',
    'visibility': '5000',
    'weather': 'RA',
    'weatherWithIntensity': '-RA',
    'isCavok': True,
    'isNsc': True,
    'clouds': ['BKN010'],
}

# The CB layer is not a field of its own: it is an entry of `clouds`, marked
# by its 'CB' suffix.
CB_LAYER = ['BKN030CB']


def group(period='1012/1016', **fields):
    state = GroupState('MPS')
    state.period = period
    for name, value in fields.items():
        setattr(state, name, value)
    return state


def trend(period='1012/1016', **fields):
    state = TrendState('MPS')
    state.period = period
    for name, value in fields.items():
        setattr(state, name, value)
    return state


def primary(**fields):
    """A primary that satisfies everything a test does not change."""
    state = PrimaryState('MPS')
    state.icao = 'ZSSS'
    state.date = '101200'
    state.period = '1012/1021'
    state.wind = '27010'
    state.visibility = '9999'
    state.clouds = ['SCT020']
    for name, value in fields.items():
        setattr(state, name, value)
    return state


def temperature(mode='max', value='12', time='1012'):
    state = TemperatureState(mode)
    state.value = value
    state.time = time
    return state


def temperatures(*pairs):
    """One group per (mode, value, time); '' for a field left blank."""
    return [temperature(*pair) for pair in pairs]


class TestComposeWeather:

    def test_wind_and_unit_are_joined(self):
        state = SegmentState('MPS')
        state.wind = '27010'
        assert state.composeWeather() == '27010MPS'

    def test_gust_is_inserted_after_the_wind(self):
        state = SegmentState('MPS')
        state.wind = '27010'
        state.gust = '25'
        assert state.composeWeather() == '27010G25MPS'

    def test_cavok_replaces_visibility_and_clouds(self):
        state = SegmentState('MPS')
        state.wind = '27010'
        state.visibility = '5000'
        state.clouds = ['BKN010']
        state.isCavok = True
        assert state.composeWeather() == '27010MPS CAVOK'

    def test_nsc_with_a_real_visibility_prints_nsc(self):
        state = SegmentState('MPS')
        state.wind = '27010'
        state.visibility = '5000'
        state.isNsc = True
        assert state.composeWeather() == '27010MPS 5000 NSC'

    def test_nsc_without_a_real_visibility_collapses_to_cavok(self):
        state = SegmentState('MPS')
        state.wind = '27010'
        state.isNsc = True
        assert state.composeWeather() == '27010MPS CAVOK'

        state.visibility = '9999'
        assert state.composeWeather() == '27010MPS CAVOK'

    def test_nsc_with_weather_prints_nsc(self):
        state = SegmentState('MPS')
        state.wind = '27010'
        state.weather = 'RA'
        state.isNsc = True
        assert state.composeWeather() == '27010MPS RA NSC'

    def test_clouds_are_ordered_by_height_not_by_row(self):
        state = SegmentState('MPS')
        state.clouds = ['OVC040', 'BKN010', 'SCT020']
        assert state.composeWeather() == 'BKN010 SCT020 OVC040'

    def test_the_cb_layer_takes_part_in_the_height_order(self):
        state = SegmentState('MPS')
        state.clouds = ['OVC040', 'BKN010CB']
        assert state.composeWeather() == 'BKN010CB OVC040'

    def test_an_unparsable_height_sorts_first(self):
        state = SegmentState('MPS')
        state.clouds = ['BKN010', 'VV///']
        assert state.composeWeather() == 'VV/// BKN010'


class TestPrimaryStateIsAcceptable:
    """The temperature groups are necessary conditions, all of them.

    The rule used to live in `TafPrimarySegment.hasAcceptableInput`, which read
    `all([date, period, wind] + [t.hasAcceptableInput() for t in self.temperatures])`.
    Extracting it into `PrimaryState` added `if t.value or t.time`, which turns
    "every group is filled" into "every *started* group is finished" -- and an
    `all()` over an empty sequence is True, so a TAF with no temperature at all
    was accepted. Restored 2026-09-18; see `.workbuddy/probe-6/`.
    """

    def test_a_complete_report_is_acceptable(self):
        assert primary(temperatures=temperatures(('max', '12', '1012'),
                                                 ('min', 'M03', '1015'))).isAcceptable() is True

    def test_no_temperature_group_at_all_is_not_acceptable(self):
        state = primary(temperatures=temperatures(('max', '', ''), ('min', '', '')))
        assert state.isAcceptable() is False

    def test_a_missing_temperature_group_is_not_acceptable(self):
        state = primary(temperatures=temperatures(('max', '12', '1012'), ('min', '', '')))
        assert state.isAcceptable() is False

    def test_a_half_filled_temperature_group_is_not_acceptable(self):
        # the pre-existing half of the rule: a started group has to be finished
        state = primary(temperatures=temperatures(('max', '12', '1012'), ('min', 'M03', '')))
        assert state.isAcceptable() is False

    def test_a_third_group_is_required_too(self):
        # the 30 hour spec offers three; every one of them counts
        state = primary(temperatures=temperatures(('max', '12', '1012'),
                                                  ('min', 'M03', '1015'),
                                                  ('max', '', '')))
        assert state.isAcceptable() is False

    def test_cancelling_needs_no_temperature(self):
        state = primary(modifier='CNL', sequence='AAA',
                        temperatures=temperatures(('max', '', ''), ('min', '', '')))
        assert state.isAcceptable() is True

    def test_an_amendment_needs_them_as_well(self):
        state = primary(modifier='AMD', sequence='AAA',
                        temperatures=temperatures(('max', '12', '1012'), ('min', '', '')))
        assert state.isAcceptable() is False


class TestGroupStateIsAcceptable:

    def test_a_period_alone_is_not_enough(self):
        assert group().isAcceptable() is False

    def test_content_alone_is_not_enough(self):
        assert group(period='', wind='27010').isAcceptable() is False

    def test_a_cb_layer_alone_is_enough(self):
        assert group(clouds=CB_LAYER).isAcceptable() is True

    @pytest.mark.parametrize('field', sorted(CONTENT))
    def test_any_single_content_field_is_enough(self, field):
        assert group(**{field: CONTENT[field]}).isAcceptable() is True

    @pytest.mark.parametrize('field', sorted(CONTENT))
    def test_a_blank_content_field_is_ignored(self, field):
        blank = '' if isinstance(CONTENT[field], str) else (False if CONTENT[field] is True else [])
        assert group(**{field: blank}).isAcceptable() is False


class TestTrendStateIsAcceptable:

    def test_nosig_is_acceptable_on_its_own(self):
        state = trend(period='', isNosig=True)
        assert state.isAcceptable() is True

    @pytest.mark.parametrize('field', sorted(CONTENT))
    def test_any_single_content_field_is_enough(self, field):
        assert trend(**{field: CONTENT[field]}).isAcceptable() is True

    def test_an_empty_trend_is_not_acceptable(self):
        assert trend(period='').isAcceptable() is False

    def test_a_cb_layer_alone_is_enough(self):
        assert trend(clouds=CB_LAYER).isAcceptable() is True

    @pytest.mark.parametrize('flag', ['atChecked', 'fmChecked', 'tlChecked'])
    def test_a_time_flag_demands_a_period(self, flag):
        assert trend(period='', wind='27010', **{flag: True}).isAcceptable() is False
        assert trend(period='1012/1016', wind='27010', **{flag: True}).isAcceptable() is True
