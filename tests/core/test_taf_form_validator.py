import datetime

from tafor.core.taf.states import GroupState, PrimaryState, SegmentState, TemperatureState
from tafor.core.taf.validator import TafFormValidator, TrendFormValidator, parseTemperature
from tafor.core.utils.time import parseTime


def primary(durations, period='1009/1018'):
    state = PrimaryState('MPS')
    state.period = period
    state.durations = durations
    return state


def group(durations, period='1012/1016', indicator='TEMPO'):
    state = GroupState('MPS', indicator)
    state.period = period
    state.durations = durations
    return state


DAY9 = datetime.datetime(2026, 6, 10, 9, 0)
DAY9_18 = (datetime.datetime(2026, 6, 10, 9, 0), datetime.datetime(2026, 6, 10, 18, 0))


def test_parse_temperature_negative():
    assert parseTemperature('M03') == -3


def test_parse_temperature_positive():
    assert parseTemperature('18') == 18


class TestCheckWeather:

    def test_thunderstorm_with_precipitation_conflicts(self):
        state = SegmentState('MPS')
        state.weather = 'TS'
        state.weatherWithIntensity = 'TSRA'
        assert TafFormValidator.checkWeather(state) == TafFormValidator.WEATHER_CONFLICT

    def test_thunderstorm_with_rain_conflicts(self):
        state = SegmentState('MPS')
        state.weather = 'TS'
        state.weatherWithIntensity = '-RA'
        assert TafFormValidator.checkWeather(state) == TafFormValidator.WEATHER_CONFLICT

    def test_thunderstorm_alone_passes(self):
        state = SegmentState('MPS')
        state.weather = 'TS'
        state.weatherWithIntensity = 'NSW'
        assert TafFormValidator.checkWeather(state) is None

    def test_empty_side_passes(self):
        state = SegmentState('MPS')
        state.weather = 'TS'
        assert TafFormValidator.checkWeather(state) is None

        state.weather = ''
        state.weatherWithIntensity = 'TSRA'
        assert TafFormValidator.checkWeather(state) is None


class TestCheckGust:

    def test_p49_always_allowed(self):
        state = SegmentState('MPS')
        state.wind = '0800'
        state.gust = 'P49'
        assert TafFormValidator.checkGust(state) is None

    def test_gust_below_threshold_rejected(self):
        state = SegmentState('MPS')
        state.wind = '0805'
        state.gust = '08'
        assert TafFormValidator.checkGust(state) == TafFormValidator.GUST_SPEED_INSUFFICIENT

    def test_gust_equal_to_wind_rejected(self):
        state = SegmentState('MPS')
        state.wind = '0810'
        state.gust = '10'
        assert TafFormValidator.checkGust(state) == TafFormValidator.GUST_SPEED_INSUFFICIENT

    def test_calm_wind_rejected(self):
        state = SegmentState('MPS')
        state.wind = '0800'
        state.gust = '30'
        assert TafFormValidator.checkGust(state) == TafFormValidator.GUST_SPEED_INSUFFICIENT

    def test_sufficient_gust_passes(self):
        state = SegmentState('MPS')
        state.wind = '0810'
        state.gust = '18'
        assert TafFormValidator.checkGust(state) is None


class TestCheckCloud:

    def test_duplicate_height_rejected(self):
        state = SegmentState('MPS')
        state.clouds = ['FEW030', 'SCT030']
        assert TafFormValidator.checkCloud(state, 'BKN030') == TafFormValidator.CLOUD_HEIGHT_CONFLICT

    def test_cb_and_cloud_oktas_exceed(self):
        state = SegmentState('MPS')
        state.clouds = ['SCT030']
        state.cb = 'OVC030CB'
        assert TafFormValidator.checkCloud(state, 'FEW010') == TafFormValidator.CLOUD_OKTAS_EXCEED

    def test_cb_is_compared_against_itself(self):
        # BUG: otherClouds excludes only the edited line, not state.cb, so
        # the okta loop compares the CB with itself: 5+5 > 8 flags a lone
        # BKN CB even with no other cloud at that height
        state = SegmentState('MPS')
        state.clouds = []
        state.cb = 'BKN030CB'
        assert TafFormValidator.checkCloud(state, 'OVC040') == TafFormValidator.CLOUD_OKTAS_EXCEED

    def test_cb_plus_cloud_oktas_exceed(self):
        state = SegmentState('MPS')
        state.clouds = ['OVC030']
        state.cb = 'SCT030CB'
        assert TafFormValidator.checkCloud(state, 'FEW010') == TafFormValidator.CLOUD_OKTAS_EXCEED

    def test_cloud_above_ovc_rejected(self):
        state = SegmentState('MPS')
        state.clouds = ['OVC030', 'BKN040']
        assert TafFormValidator.checkCloud(state, 'FEW010') == TafFormValidator.CLOUD_ABOVE_OVC

    def test_ordinary_stacking_passes(self):
        state = SegmentState('MPS')
        state.clouds = ['FEW030']
        assert TafFormValidator.checkCloud(state, 'SCT040') is None

    def test_empty_line_value_passes(self):
        state = SegmentState('MPS')
        state.clouds = ['FEW030']
        assert TafFormValidator.checkCloud(state, '') is None


class TestCheckGroupPeriod:

    def test_within_primary_period_passes(self):
        error = TafFormValidator.checkGroupPeriod(
            group((datetime.datetime(2026, 6, 10, 10), datetime.datetime(2026, 6, 10, 16))),
            primary(DAY9_18), span=6)
        assert error is None

    def test_period_longer_than_span_rejected(self):
        error = TafFormValidator.checkGroupPeriod(
            group((datetime.datetime(2026, 6, 10, 10), datetime.datetime(2026, 6, 10, 17))),
            primary(DAY9_18), span=6)
        assert error == TafFormValidator.GROUP_PERIOD_EXCEED

    def test_start_before_primary_rejected(self):
        error = TafFormValidator.checkGroupPeriod(
            group((datetime.datetime(2026, 6, 10, 8, 30), datetime.datetime(2026, 6, 10, 12))),
            primary(DAY9_18), span=6)
        assert error == TafFormValidator.GROUP_START_INVALID

    def test_end_after_primary_rejected(self):
        error = TafFormValidator.checkGroupPeriod(
            group((datetime.datetime(2026, 6, 10, 15), datetime.datetime(2026, 6, 10, 19))),
            primary(DAY9_18), span=6)
        assert error == TafFormValidator.GROUP_END_INVALID

    def test_becmg_may_not_end_with_primary(self):
        becmg = group((datetime.datetime(2026, 6, 10, 12), datetime.datetime(2026, 6, 10, 18)), indicator='BECMG')
        error = TafFormValidator.checkGroupPeriod(becmg, primary(DAY9_18), span=6, isBecmg=True)
        assert error == TafFormValidator.GROUP_END_INVALID

        # The same group is fine as TEMPO
        assert TafFormValidator.checkGroupPeriod(becmg, primary(DAY9_18), span=6) is None

    def test_missing_period_passes(self):
        empty = group(None, period='')
        assert TafFormValidator.checkGroupPeriod(empty, primary(DAY9_18), span=6) is None


class TestCheckGroupOverlap:

    def test_overlapping_siblings_rejected(self):
        error = TafFormValidator.checkGroupOverlap(
            group((datetime.datetime(2026, 6, 10, 10), datetime.datetime(2026, 6, 10, 12))),
            [group((datetime.datetime(2026, 6, 10, 11), datetime.datetime(2026, 6, 10, 13)))])
        assert error == TafFormValidator.GROUP_OVERLAP

    def test_touching_groups_pass(self):
        # isOverlap only reports a positive intersection
        error = TafFormValidator.checkGroupOverlap(
            group((datetime.datetime(2026, 6, 10, 10), datetime.datetime(2026, 6, 10, 12))),
            [group((datetime.datetime(2026, 6, 10, 12), datetime.datetime(2026, 6, 10, 14)))])
        assert error is None

    def test_sibling_without_period_ignored(self):
        error = TafFormValidator.checkGroupOverlap(
            group((datetime.datetime(2026, 6, 10, 10), datetime.datetime(2026, 6, 10, 12))),
            [group(None)])
        assert error is None


class TestCheckFmPeriod:

    def test_start_inside_primary_passes(self):
        error = TafFormValidator.checkFmPeriod(
            group((datetime.datetime(2026, 6, 10, 12), datetime.datetime(2026, 6, 10, 12)), indicator='FM'),
            primary(DAY9_18))
        assert error is None

    def test_start_on_primary_end_rejected(self):
        error = TafFormValidator.checkFmPeriod(
            group((datetime.datetime(2026, 6, 10, 18), datetime.datetime(2026, 6, 10, 18)), indicator='FM'),
            primary(DAY9_18))
        assert error == TafFormValidator.FM_TIME_INVALID

    def test_start_before_primary_rejected(self):
        error = TafFormValidator.checkFmPeriod(
            group((datetime.datetime(2026, 6, 10, 7), datetime.datetime(2026, 6, 10, 7)), indicator='FM'),
            primary(DAY9_18))
        assert error == TafFormValidator.FM_TIME_INVALID

    def test_missing_durations_passes(self):
        assert TafFormValidator.checkFmPeriod(group(None, indicator='FM'), primary(None)) is None


class TestCheckFmOverlap:

    def test_instant_inside_sibling_rejected(self):
        error = TafFormValidator.checkFmOverlap(
            group((datetime.datetime(2026, 6, 10, 12), datetime.datetime(2026, 6, 10, 12)), indicator='FM'),
            [group((datetime.datetime(2026, 6, 10, 11), datetime.datetime(2026, 6, 10, 13)))])
        assert error == TafFormValidator.GROUP_OVERLAP

    def test_instant_outside_siblings_passes(self):
        error = TafFormValidator.checkFmOverlap(
            group((datetime.datetime(2026, 6, 10, 12), datetime.datetime(2026, 6, 10, 12)), indicator='FM'),
            [group((datetime.datetime(2026, 6, 10, 13), datetime.datetime(2026, 6, 10, 15)))])
        assert error is None

    def test_instant_on_sibling_start_rejected(self):
        # FM bounds are inclusive, unlike checkGroupOverlap
        error = TafFormValidator.checkFmOverlap(
            group((datetime.datetime(2026, 6, 10, 13), datetime.datetime(2026, 6, 10, 13)), indicator='FM'),
            [group((datetime.datetime(2026, 6, 10, 13), datetime.datetime(2026, 6, 10, 15)))])
        assert error == TafFormValidator.GROUP_OVERLAP


class TestCheckTemperatureTime:

    def test_empty_time_passes(self):
        temp = TemperatureState('max')
        assert TafFormValidator.checkTemperatureTime(temp, DAY9_18) is None

    def test_missing_primary_period_rejected(self):
        temp = TemperatureState('max')
        temp.time = '1012'
        assert TafFormValidator.checkTemperatureTime(temp, None) == TafFormValidator.TEMP_TIME_INVALID

    def test_unparsable_time_rejected(self):
        temp = TemperatureState('max')
        temp.time = '9999'
        assert TafFormValidator.checkTemperatureTime(temp, DAY9_18) == TafFormValidator.TEMP_TIME_INVALID

    def test_time_inside_primary_passes(self):
        temp = TemperatureState('max')
        temp.time = '1012'
        assert TafFormValidator.checkTemperatureTime(temp, DAY9_18) is None

    def test_time_outside_primary_rejected(self):
        temp = TemperatureState('max')
        temp.time = '1019'
        assert TafFormValidator.checkTemperatureTime(temp, DAY9_18) == TafFormValidator.TEMP_TIME_INVALID

    def test_time_already_used_by_other_mode_rejected(self):
        temp = TemperatureState('max')
        temp.time = '1012'
        siblings = [datetime.datetime(2026, 6, 10, 12, 0)]
        assert TafFormValidator.checkTemperatureTime(temp, DAY9_18, siblings=siblings) == TafFormValidator.TEMP_TIME_INVALID

    def test_same_day_as_same_mode_sibling_rejected(self):
        # The caller passes parsed datetime objects here (see
        # widgets/taf.py findTemperatureTime)
        temp = TemperatureState('max')
        temp.time = '1012'
        sameType = [datetime.datetime(2026, 6, 10, 14, 0)]
        assert TafFormValidator.checkTemperatureTime(temp, DAY9_18, sameTypeSiblings=sameType) == TafFormValidator.TEMP_TIME_INVALID

    def test_other_day_than_same_mode_sibling_passes(self):
        primarySpanning = (datetime.datetime(2026, 6, 10, 9, 0), datetime.datetime(2026, 6, 11, 9, 0))
        temp = TemperatureState('max')
        temp.time = '1108'
        sameType = [datetime.datetime(2026, 6, 10, 8, 0)]
        assert TafFormValidator.checkTemperatureTime(temp, primarySpanning, sameTypeSiblings=sameType) is None


class TestCheckTemperature:

    def test_max_above_min_passes(self):
        temp = TemperatureState('max')
        temp.value = '12'
        assert TafFormValidator.checkTemperature(temp, 10) is None

    def test_max_equal_to_min_rejected(self):
        temp = TemperatureState('max')
        temp.value = '10'
        assert TafFormValidator.checkTemperature(temp, 10) == TafFormValidator.TEMP_MAX_LESS_MIN

    def test_max_below_min_rejected(self):
        temp = TemperatureState('max')
        temp.value = 'M05'
        assert TafFormValidator.checkTemperature(temp, 10) == TafFormValidator.TEMP_MAX_LESS_MIN

    def test_min_below_max_passes(self):
        temp = TemperatureState('min')
        temp.value = 'M08'
        assert TafFormValidator.checkTemperature(temp, -5) is None

    def test_min_equal_to_max_rejected(self):
        temp = TemperatureState('min')
        temp.value = 'M05'
        assert TafFormValidator.checkTemperature(temp, -5) == TafFormValidator.TEMP_MIN_GREATER_MAX

    def test_min_above_max_rejected(self):
        temp = TemperatureState('min')
        temp.value = '02'
        assert TafFormValidator.checkTemperature(temp, -5) == TafFormValidator.TEMP_MIN_GREATER_MAX

    def test_empty_value_passes(self):
        temp = TemperatureState('max')
        assert TafFormValidator.checkTemperature(temp, 10) is None

    def test_missing_reference_passes(self):
        temp = TemperatureState('max')
        temp.value = '10'
        assert TafFormValidator.checkTemperature(temp, None) is None


class TestTrendFormValidatorPeriod:
    """TrendFormValidator.checkPeriod receives the raw trend group text from the
    TAF trend editor: 'HHMM' for AT/FM/TL groups and 'HHMM/HHMM' for FM+TL
    (see widgets/taf.py validatePeriod). parseTime resolves 4-digit groups
    against the real clock, so expectations are built relative to utcnow().
    """

    def now(self):
        return datetime.datetime.utcnow()

    def test_empty_passes(self):
        assert TrendFormValidator.checkPeriod('') is None

    def test_single_time_within_horizon_passes(self):
        value = (self.now() + datetime.timedelta(hours=1)).strftime('%H%M')
        assert TrendFormValidator.checkPeriod(value, now=self.now()) is None

    def test_single_time_beyond_horizon_rejected(self):
        value = (self.now() + datetime.timedelta(hours=5)).strftime('%H%M')
        assert TrendFormValidator.checkPeriod(value, now=self.now()) == TrendFormValidator.TREND_TIME_INVALID

    def test_span_within_two_hours_passes(self):
        start = (self.now() + datetime.timedelta(minutes=10)).strftime('%H%M')
        end = (self.now() + datetime.timedelta(hours=2)).strftime('%H%M')
        value = '{}/{}'.format(start, end)
        assert TrendFormValidator.checkPeriod(value, now=self.now()) is None

    def test_span_over_two_hours_rejected(self):
        start = (self.now() + datetime.timedelta(minutes=10)).strftime('%H%M')
        end = (self.now() + datetime.timedelta(minutes=140)).strftime('%H%M')
        value = '{}/{}'.format(start, end)
        assert TrendFormValidator.checkPeriod(value, now=self.now()) == TrendFormValidator.TREND_TIME_INVALID

    def test_end_text_before_start_text_is_rejected(self):
        # The validator bumps a non-increasing end by one day, which lands
        # the span far beyond the 2h limit
        start = (self.now() + datetime.timedelta(minutes=140)).strftime('%H%M')
        end = (self.now() + datetime.timedelta(minutes=30)).strftime('%H%M')
        value = '{}/{}'.format(start, end)
        assert TrendFormValidator.checkPeriod(value, now=self.now()) == TrendFormValidator.TREND_TIME_INVALID


if __name__ == '__main__':
    import pytest
    pytest.main([__file__])
