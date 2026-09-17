import datetime

from tafor.core.taf import (
    GroupState,
    PrimaryState,
    SpecFC,
    SpecFT24,
    SpecFT30,
    amendSequence,
    completeGroupPeriod,
    composeHeading,
    composeBody,
    groupSpan,
    isGroupStartAcceptable,
    normalizeTemperatureTime,
    segmentOrderKey,
    formatValidityEnd,
)


BASE_START = datetime.datetime(2026, 8, 10, 9)
BASE_END = datetime.datetime(2026, 8, 10, 21)
DURATIONS = (BASE_START, BASE_END)


def primary(modifier=None):
    """A filled primary state, as the presenter would hand it to compose."""
    state = PrimaryState('MPS', icao='ZBAD', spec=SpecFT24)
    state.date = '100540'
    state.period = '1009/1018'
    state.modifier = modifier
    state.wind = '27010'
    state.durations = DURATIONS
    return state


def group(indicator='TEMPO', period='1014/1016', start=BASE_START):
    state = GroupState('MPS', indicator=indicator)
    state.period = period
    state.wind = '27015'
    state.durations = (start, start + datetime.timedelta(hours=2))
    return state


class Blank:
    """A segment that has nothing to transmit, so composes to ''."""

    indicator = 'TEMPO'
    durations = DURATIONS

    def composeMessage(self):
        return ''


class TestComposeHeading:

    def test_full(self):
        assert composeHeading(SpecFC, 'PE', 'ZBAD', '102400', 'A001') == 'FCPE ZBAD 102400 A001'

    def test_spec_defaults_to_fc_when_missing(self):
        assert composeHeading(None, 'PE', 'ZBAD', '102400', '').startswith('FCPE')

    def test_filters_empty_parts(self):
        assert composeHeading(SpecFT30, 'SH', 'ZBAD', '', '') == 'FTSH ZBAD'


class TestSegmentOrderKey:

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


class TestGroupSpan:

    def test_tempo_depends_on_spec(self):
        assert groupSpan('TEMPO', SpecFC) == 4
        assert groupSpan('TEMPO', SpecFT24) == 6
        assert groupSpan('TEMPO', SpecFT30) == 6

    def test_non_tempo_fixed_two_hours(self):
        for indicator in ['FM', 'BECMG', 'PRIMARY']:
            for spec in [SpecFC, SpecFT24, SpecFT30]:
                assert groupSpan(indicator, spec) == 2


class TestFormatValidityEnd:

    def test_normal_time(self):
        assert formatValidityEnd(datetime.datetime(2026, 8, 10, 18)) == '1018'

    def test_midnight_normalizes_to_previous_day_24(self):
        assert formatValidityEnd(datetime.datetime(2026, 8, 11)) == '1024'
        assert formatValidityEnd(datetime.datetime(2026, 9, 1)) == '3124'


class TestNormalizeTemperatureTime:

    def test_non_midnight_returns_none(self):
        # only midnight times need normalising; the caller keeps the raw text
        assert normalizeTemperatureTime(datetime.datetime(2026, 8, 10, 15), DURATIONS) is None
        assert normalizeTemperatureTime(datetime.datetime(2026, 8, 10, 21), DURATIONS) is None

    def test_midnight_within_period(self):
        # midnight resolves to plain DD00 unless it is the validity end
        assert normalizeTemperatureTime(datetime.datetime(2026, 8, 11, 0), DURATIONS) == '1100'

    def test_midnight_at_validity_end_uses_previous_day_24(self):
        durations = (datetime.datetime(2026, 8, 10, 12), datetime.datetime(2026, 8, 11))
        assert normalizeTemperatureTime(datetime.datetime(2026, 8, 11), durations) == '1024'


class TestIsGroupStartAcceptable:

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


class TestCompleteGroupPeriod:

    def test_tempo_fc_span_four_hours(self):
        assert completeGroupPeriod('1012', DURATIONS, 'TEMPO', SpecFC) == '1012/1016'

    def test_tempo_ft_span_six_hours(self):
        assert completeGroupPeriod('1012', DURATIONS, 'TEMPO', SpecFT30) == '1012/1018'

    def test_tempo_clamped_to_validity_end(self):
        # 18:00 + 4 hours crosses the 21:00 end, clamped to the validity end
        assert completeGroupPeriod('1018', DURATIONS, 'TEMPO', SpecFC) == '1018/1021'

    def test_tempo_clamp_boundary_exactly_at_end(self):
        # 17:00 + 4 hours lands exactly on the end, taking the same clamp branch
        assert completeGroupPeriod('1017', DURATIONS, 'TEMPO', SpecFC) == '1017/1021'

    def test_tempo_clamp_midnight_uses_previous_day_24(self):
        durations = (datetime.datetime(2026, 8, 10, 20), datetime.datetime(2026, 8, 11))
        assert completeGroupPeriod('1022', durations, 'TEMPO', SpecFC) == '1022/1024'

    def test_becmg_spans_one_hour(self):
        assert completeGroupPeriod('1015', DURATIONS, 'BECMG', SpecFC) == '1015/1016'

    def test_becmg_overflow_returns_none(self):
        # 20:00 + 1 hour ends exactly at the validity end, treated as overflow
        assert completeGroupPeriod('1020', DURATIONS, 'BECMG', SpecFC) is None

    def test_fm_is_never_completed(self):
        assert completeGroupPeriod('1012', DURATIONS, 'FM', SpecFC) is None

    def test_month_rollover(self):
        durations = (datetime.datetime(2026, 8, 31, 20), datetime.datetime(2026, 9, 1, 6))
        assert completeGroupPeriod('0100', durations, 'TEMPO', SpecFC) == '0100/0104'


class TestAmendSequence:

    def test_first_amendment_of_a_period_is_aaa(self):
        assert amendSequence(0, 'AMD') == 'AAA'

    def test_the_count_advances_the_last_letter(self):
        assert amendSequence(2, 'AMD') == 'AAC'

    def test_corrections_use_the_cc_prefix(self):
        assert amendSequence(1, 'COR') == 'CCB'


class TestComposeBody:
    """composeBody takes states, not widgets: the caller picks the active groups."""

    def test_the_primary_segment_comes_first(self):
        text = composeBody(primary(), [group('TEMPO', '1014/1016')])

        assert text.splitlines()[0].startswith('TAF ZBAD')

    def test_groups_follow_in_chronological_order(self):
        early = group('TEMPO', '1012/1014', start=datetime.datetime(2026, 8, 10, 12))
        late = group('FM', '1016/1021', start=datetime.datetime(2026, 8, 10, 16))

        text = composeBody(primary(), [late, early])

        assert text.splitlines()[1].startswith('TEMPO 1012/1014')
        assert text.splitlines()[2].startswith('FM1016/1021')

    def test_lines_are_newline_joined_and_closed_with_equals(self):
        text = composeBody(primary(), [group('TEMPO', '1014/1016')])

        assert text.endswith('=')
        assert text.count('\n') == 1

    def test_no_groups_is_the_primary_alone(self):
        assert composeBody(primary(), []) == 'TAF ZBAD 100540Z 1009/1018 27010MPS='

    def test_an_amendment_marker_is_part_of_the_primary_segment(self):
        text = composeBody(primary(modifier='AMD'), [])

        assert text.startswith('TAF AMD ZBAD')

    def test_a_segment_with_nothing_to_say_leaves_no_blank_line(self):
        text = composeBody(primary(), [group('TEMPO', '1014/1016'), Blank()])

        assert '' not in text.splitlines()
