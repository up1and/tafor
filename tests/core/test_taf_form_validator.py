import datetime

from tafor.core.taf.states import GroupState, PrimaryState, SegmentState, TemperatureState
from tafor.core.taf.validator import (
    TafFormValidator,
    TrendFormValidator,
    parseTemperature,
)
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
        state.clouds = ['SCT030', 'OVC030CB']
        assert TafFormValidator.checkCloud(state, 'FEW010') == TafFormValidator.CLOUD_OKTAS_EXCEED

    def test_lone_cb_at_any_height_passes(self):
        state = SegmentState('MPS')
        state.clouds = ['BKN030CB']
        assert TafFormValidator.checkCloud(state, 'OVC040') is None

    def test_editing_another_line_ignores_the_cb_self_oktas(self):
        # any ordinary row edit used to trip the okta check against the CB
        state = SegmentState('MPS')
        state.clouds = ['BKN040', 'BKN030CB']
        assert TafFormValidator.checkCloud(state, 'BKN040') is None

    def test_cb_plus_cloud_oktas_exceed(self):
        state = SegmentState('MPS')
        state.clouds = ['OVC030', 'SCT030CB']
        assert TafFormValidator.checkCloud(state, 'FEW010') == TafFormValidator.CLOUD_OKTAS_EXCEED

    def test_cloud_and_cb_at_the_same_height_pass(self):
        # a CB layer is an independent phenomena layer and may share the
        # height of an ordinary cloud layer
        state = SegmentState('MPS')
        state.clouds = ['SCT020', 'SCT020CB']
        assert TafFormValidator.checkCloud(state, 'SCT020') is None

    def test_different_cover_cb_at_the_same_height_passes(self):
        state = SegmentState('MPS')
        state.clouds = ['BKN020', 'SCT020CB']
        assert TafFormValidator.checkCloud(state, 'SCT020') is None

    def test_heavy_cb_flags_from_either_line(self):
        # the 8-okta cap still applies to a same-height cloud + CB pair,
        # no matter which line triggered the check
        state = SegmentState('MPS')
        state.clouds = ['OVC030', 'BKN030CB']
        assert TafFormValidator.checkCloud(state, 'FEW010') == TafFormValidator.CLOUD_OKTAS_EXCEED
        assert TafFormValidator.checkCloud(state, 'OVC030') == TafFormValidator.CLOUD_OKTAS_EXCEED

    def test_cb_and_cloud_at_the_same_height_still_exceed_oktas(self):
        state = SegmentState('MPS')
        state.clouds = ['OVC030', 'BKN030CB']
        assert TafFormValidator.checkCloud(state, 'FEW010') == TafFormValidator.CLOUD_OKTAS_EXCEED

    def test_featherweight_cb_still_exceeds_oktas_with_a_heavy_cloud(self):
        state = SegmentState('MPS')
        state.clouds = ['OVC030', 'FEW030CB']
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
        error = TafFormValidator.checkGroupPeriod(becmg, primary(DAY9_18), span=6)
        assert error == TafFormValidator.GROUP_END_INVALID

        # The same period is fine as TEMPO. The indicator is read off the group
        # itself, so the two calls cannot disagree about which rule applies.
        tempo = group(becmg.durations, indicator='TEMPO')
        assert TafFormValidator.checkGroupPeriod(tempo, primary(DAY9_18), span=6) is None

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
    """Three rules for a temperature's time (core-taf-design.md §3.2):

      1. inside the validity period
      2. no two temperatures share an instant -- a TX and a TN never coincide
      3. two of the same mode never share a day -- FT30 is TX TN TX

    The check takes the raw material (`temperatures`, `durations`) rather than the
    two prepared lists the old signature wanted, so the sibling lists cannot be
    built from a different batch than the one being checked.
    """

    def temperature(self, mode='max', time=''):
        state = TemperatureState(mode)
        state.time = time
        return state

    def check(self, target, others=(), durations=DAY9_18):
        return TafFormValidator.checkTemperatureTime(target, [target] + list(others), durations)

    def test_empty_time_passes(self):
        assert self.check(self.temperature()) is None

    def test_missing_primary_period_rejected(self):
        assert self.check(self.temperature(time='1012'), durations=None) == TafFormValidator.TEMP_TIME_INVALID

    def test_unparsable_time_rejected(self):
        assert self.check(self.temperature(time='9999')) == TafFormValidator.TEMP_TIME_INVALID

    def test_time_inside_primary_passes(self):
        assert self.check(self.temperature(time='1012')) is None

    def test_the_period_bounds_themselves_pass(self):
        assert self.check(self.temperature(time='1009')) is None
        assert self.check(self.temperature(time='1018')) is None

    def test_time_outside_primary_rejected(self):
        assert self.check(self.temperature(time='1019')) == TafFormValidator.TEMP_TIME_INVALID

    def test_a_time_before_the_period_is_rejected(self):
        # 1008 is earlier than the period start, so it rolls to the next month
        assert self.check(self.temperature(time='1008')) == TafFormValidator.TEMP_TIME_INVALID

    def test_time_already_used_by_other_mode_rejected(self):
        # rule 2
        target = self.temperature('max', '1012')
        assert self.check(target, [self.temperature('min', '1012')]) == TafFormValidator.TEMP_TIME_INVALID

    def test_different_modes_may_share_a_day(self):
        # why rule 2 is about the instant while rule 3 is about the day
        target = self.temperature('max', '1012')
        assert self.check(target, [self.temperature('min', '1015')]) is None

    def test_same_day_as_same_mode_sibling_rejected(self):
        # rule 3: two TX may not share a day even at different hours
        target = self.temperature('max', '1012')
        assert self.check(target, [self.temperature('max', '1015')]) == TafFormValidator.TEMP_TIME_INVALID

    def test_the_third_group_of_a_thirty_hour_report(self):
        # FT30 is TX TN TX: the second TX has to move to the next day
        spanning = (datetime.datetime(2026, 6, 10, 9, 0), datetime.datetime(2026, 6, 11, 18, 0))
        first = self.temperature('max', '1012')
        second = self.temperature('min', '1015')

        third = self.temperature('max', '1018')
        assert self.check(third, [first, second], spanning) == TafFormValidator.TEMP_TIME_INVALID

        third.time = '1118'
        assert self.check(third, [first, second], spanning) is None

    def test_a_temperature_is_not_its_own_sibling(self):
        target = self.temperature('max', '1012')
        assert TafFormValidator.checkTemperatureTime(target, [target, target], DAY9_18) is None

    def test_a_sibling_with_an_unparsable_time_is_skipped(self):
        # a sibling that does not parse is not a clash, it is simply absent
        target = self.temperature('max', '1012')
        assert self.check(target, [self.temperature('max', '9999')]) is None

    def test_a_sibling_with_a_blank_time_is_skipped(self):
        target = self.temperature('max', '1012')
        assert self.check(target, [self.temperature('max', '')]) is None


class TestCheckTemperature:
    """A max has to stay above the lowest of the others, a min below the highest."""

    def temperature(self, mode='max', value=''):
        state = TemperatureState(mode)
        state.value = value
        return state

    def check(self, target, others=()):
        return TafFormValidator.checkTemperature(target, [target] + list(others))

    def test_max_above_min_passes(self):
        assert self.check(self.temperature('max', '12'), [self.temperature('min', 'M03')]) is None

    def test_max_equal_to_min_rejected(self):
        assert self.check(self.temperature('max', '10'), [self.temperature('min', '10')]) == TafFormValidator.TEMP_MAX_LESS_MIN

    def test_max_below_min_rejected(self):
        assert self.check(self.temperature('max', 'M05'), [self.temperature('min', '10')]) == TafFormValidator.TEMP_MAX_LESS_MIN

    def test_min_below_max_passes(self):
        assert self.check(self.temperature('min', 'M08'), [self.temperature('max', 'M05')]) is None

    def test_min_equal_to_max_rejected(self):
        assert self.check(self.temperature('min', 'M05'), [self.temperature('max', 'M05')]) == TafFormValidator.TEMP_MIN_GREATER_MAX

    def test_min_above_max_rejected(self):
        assert self.check(self.temperature('min', '02'), [self.temperature('max', 'M05')]) == TafFormValidator.TEMP_MIN_GREATER_MAX

    def test_empty_value_passes(self):
        assert self.check(self.temperature('max', ''), [self.temperature('min', '10')]) is None

    def test_no_other_value_passes(self):
        assert self.check(self.temperature('max', '10')) is None

    def test_blank_siblings_are_skipped(self):
        assert self.check(self.temperature('max', '10'), [self.temperature('min', '')]) is None

    def test_a_temperature_is_not_its_own_reference(self):
        target = self.temperature('max', '10')
        assert TafFormValidator.checkTemperature(target, [target, target]) is None

    def test_the_bound_is_the_lowest_of_several(self):
        # a max is bounded by the *lowest* of the others, not by the first one
        target = self.temperature('max', 'M05')
        assert self.check(target, [self.temperature('min', '10'),
                                   self.temperature('min', 'M02')]) == TafFormValidator.TEMP_MAX_LESS_MIN

    def test_another_max_still_bounds_it(self):
        # the reference is every other temperature whatever its mode, so a second
        # TX bounds a TX exactly as a TN does. Worth pinning: it is not obvious
        # from the wording, and FT30 is the only spec with two TX.
        target = self.temperature('max', '05')
        assert self.check(target, [self.temperature('max', '10')]) == TafFormValidator.TEMP_MAX_LESS_MIN


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
