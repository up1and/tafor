import datetime

from tafor.core.taf import (
    completeGroupPeriod,
    composeHeading,
    groupSpan,
    isGroupStartAcceptable,
    segmentOrderKey,
    formatValidityEnd,
)


BASE_START = datetime.datetime(2026, 8, 10, 9)
BASE_END = datetime.datetime(2026, 8, 10, 21)
DURATIONS = (BASE_START, BASE_END)


class TestComposeHeading(object):

    def test_full(self):
        assert composeHeading('fc', 'PE', 'ZBAD', '102400', 'A001') == 'FCPE ZBAD 102400 A001'

    def test_spec_defaults_to_fc_when_missing(self):
        assert composeHeading('', 'PE', 'ZBAD', '102400', '').startswith('FCPE')

    def test_filters_empty_parts(self):
        assert composeHeading('ft30', 'SH', 'ZBAD', '', '') == 'FTSH ZBAD'


class TestSegmentOrderKey(object):

    def test_primary_always_first(self):
        start = datetime.datetime(2026, 8, 10, 12)
        assert segmentOrderKey('PRIMARY', start) < segmentOrderKey('FM', start)

    def test_identifier_priority_on_tie(self):
        start = datetime.datetime(2026, 8, 10, 12)
        keys = [segmentOrderKey(i, start) for i in ['FM', 'BECMG', 'TEMPO']]
        assert keys == sorted(keys)

    def test_chronological_by_start(self):
        early = segmentOrderKey('TEMPO', datetime.datetime(2026, 8, 10, 11))
        late = segmentOrderKey('FM', datetime.datetime(2026, 8, 10, 13))
        assert early < late

    def test_unknown_identifier_sorts_last(self):
        start = datetime.datetime(2026, 8, 10, 12)
        assert segmentOrderKey('MYSTERY', start) > segmentOrderKey('TEMPO', start)


class TestGroupSpan(object):

    def test_tempo_depends_on_spec(self):
        assert groupSpan('TEMPO', 'fc') == 4
        assert groupSpan('TEMPO', 'ft24') == 6
        assert groupSpan('TEMPO', 'ft30') == 6

    def test_non_tempo_fixed_two_hours(self):
        for indicator in ['FM', 'BECMG', 'PRIMARY']:
            for spec in ['fc', 'ft24', 'ft30']:
                assert groupSpan(indicator, spec) == 2


class TestFormatValidityEnd(object):

    def test_normal_time(self):
        assert formatValidityEnd(datetime.datetime(2026, 8, 10, 18)) == '1018'

    def test_midnight_normalizes_to_previous_day_24(self):
        assert formatValidityEnd(datetime.datetime(2026, 8, 11)) == '1024'
        assert formatValidityEnd(datetime.datetime(2026, 9, 1)) == '3124'


class TestIsGroupStartAcceptable(object):

    def test_accepts_digits_within_validity(self):
        assert isGroupStartAcceptable('1012', DURATIONS) is True

    def test_rejects_wrong_length(self):
        assert isGroupStartAcceptable('121', DURATIONS) is False
        assert isGroupStartAcceptable('10125', DURATIONS) is False

    def test_rejects_non_digits(self):
        assert isGroupStartAcceptable('ABCD', DURATIONS) is False

    def test_rejects_start_at_or_after_validity_end(self):
        # validity ends at 21:00 on the 10th; later days are out of range
        assert isGroupStartAcceptable('2100', DURATIONS) is False
        assert isGroupStartAcceptable('1100', DURATIONS) is False

    def test_rejects_hour_24_resolving_past_validity(self):
        # '1024' resolves to midnight on the 11th, past the current period
        assert isGroupStartAcceptable('1024', DURATIONS) is False


class TestCompleteGroupPeriod(object):

    def test_tempo_fc_span_four_hours(self):
        assert completeGroupPeriod('1012', DURATIONS, 'TEMPO', 'fc') == '1012/1016'

    def test_tempo_ft_span_six_hours(self):
        assert completeGroupPeriod('1012', DURATIONS, 'TEMPO', 'ft30') == '1012/1018'

    def test_tempo_clamped_to_validity_end(self):
        # 18:00 + 4 hours crosses the 21:00 end, clamped to the validity end
        assert completeGroupPeriod('1018', DURATIONS, 'TEMPO', 'fc') == '1018/1021'

    def test_tempo_clamp_boundary_exactly_at_end(self):
        # 17:00 + 4 hours lands exactly on the end, taking the same clamp branch
        assert completeGroupPeriod('1017', DURATIONS, 'TEMPO', 'fc') == '1017/1021'

    def test_tempo_clamp_midnight_uses_previous_day_24(self):
        durations = (datetime.datetime(2026, 8, 10, 20), datetime.datetime(2026, 8, 11))
        assert completeGroupPeriod('1022', durations, 'TEMPO', 'fc') == '1022/1024'

    def test_becmg_spans_one_hour(self):
        assert completeGroupPeriod('1015', DURATIONS, 'BECMG', 'fc') == '1015/1016'

    def test_becmg_overflow_returns_none(self):
        # 20:00 + 1 hour ends exactly at the validity end, treated as overflow
        assert completeGroupPeriod('1020', DURATIONS, 'BECMG', 'fc') is None

    def test_fm_is_never_completed(self):
        assert completeGroupPeriod('1012', DURATIONS, 'FM', 'fc') is None

    def test_month_rollover(self):
        durations = (datetime.datetime(2026, 8, 31, 20), datetime.datetime(2026, 9, 1, 6))
        assert completeGroupPeriod('0100', durations, 'TEMPO', 'fc') == '0100/0104'
