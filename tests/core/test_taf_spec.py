import datetime

import pytest

from tafor.core.taf import CurrentTaf, SpecFC, SpecFT24, SpecFT30


WHEN = datetime.datetime(2026, 6, 10, 8, 0)


class TestSpecs:

    def test_designator_is_the_message_type(self):
        assert SpecFC.designator == 'FC'
        assert SpecFT24.designator == 'FT'
        assert SpecFT30.designator == 'FT'

    def test_duration_is_what_separates_the_two_ft_specs(self):
        # the judgement the widget and groupSpan use, instead of a group-count
        # field (design doc §2.1)
        assert SpecFC.duration == datetime.timedelta(hours=9)
        assert SpecFT24.duration == datetime.timedelta(hours=24)
        assert SpecFT30.duration == datetime.timedelta(hours=30)


class TestCurrentTaf:

    def test_period(self):
        assert CurrentTaf(SpecFC, time=WHEN).period() == '1009/1018'
        assert CurrentTaf(SpecFT24, time=WHEN).period() == '1006/1106'
        assert CurrentTaf(SpecFT30, time=WHEN).period() == '1006/1112'

    def test_key_is_the_window_identity(self):
        # the label the table is indexed by, and the short mark a report is
        # referred to by -- not a period with the day filed off
        assert CurrentTaf(SpecFC, time=WHEN).key() == '0918'
        assert CurrentTaf(SpecFT24, time=WHEN).key() == '0606'

    def test_durations(self):
        start, end = CurrentTaf(SpecFT30, time=WHEN).durations()
        assert start == datetime.datetime(2026, 6, 10, 6, 0)
        assert end == datetime.datetime(2026, 6, 11, 12, 0)

    def test_repr_uses_the_designator(self):
        assert repr(CurrentTaf(SpecFT30, time=WHEN)) == '<Current TAF FT1006/1112>'

    def test_period_has_no_strict_variant(self):
        # period(strict=True) was unreachable — the only caller passed
        # strict=False — so the argument and _strict() were removed
        taf = CurrentTaf(SpecFC, time=WHEN)
        assert not hasattr(taf, '_strict')
        with pytest.raises(TypeError):
            taf.period(strict=True)

    def test_a_window_that_runs_to_midnight_keeps_its_day(self):
        # '0024' means 00:00 to 24:00, so the window ends on the 11th rather than
        # rolling into the 12th. The hour fields are the label's own; only the
        # days are substituted.
        taf = CurrentTaf(SpecFT24, time=datetime.datetime(2026, 6, 10, 22, 0))
        assert taf.key() == '0024'
        assert taf.period() == '1100/1124'

    def test_the_deadline_counts_the_spec_delay(self):
        # SpecFC's delay is 50 minutes and its 09:00 window opens at 07:00, so
        # with 30 minutes of tolerance the report is not late until 08:20. The
        # old formula floored the delay to whole hours -- 50 minutes became 0 --
        # and called it late from 07:30 on.
        assert CurrentTaf(SpecFC, time=datetime.datetime(2026, 6, 10, 8, 0)).isExpired(30) is False
        assert CurrentTaf(SpecFC, time=datetime.datetime(2026, 6, 10, 8, 25)).isExpired(30) is True

    def test_zero_minutes_is_expressible(self):
        # `offset = int(offset) if offset else 30` used to make 0 unreachable
        taf = CurrentTaf(SpecFC, time=datetime.datetime(2026, 6, 10, 7, 51))
        assert taf.isExpired(0) is True
        assert taf.isExpired(5) is False


class TestSpecInvariants:
    """The two facts that make the loop in `key()` always win."""

    def test_the_windows_span_exactly_a_day(self):
        # consecutive windows are `interval` apart, so this is what stops a gap
        # opening between the last window and the first of the next day
        for spec in (SpecFC, SpecFT24, SpecFT30):
            assert len(spec.periods) * spec.interval == datetime.timedelta(hours=24)

    def test_the_default_is_the_last_window(self):
        # only the window that wraps past midnight is the one the table is
        # shifted back a day for
        for spec in (SpecFC, SpecFT24, SpecFT30):
            assert spec.default == spec.periods[-1]

    def test_every_instant_of_the_day_lands_in_a_window(self):
        """The sweep behind the fallback in `key()` being unreachable.

        probe-10 walked all 120,960 minutes of a month; this is the version that
        ships with the suite.
        """
        for spec in (SpecFC, SpecFT24, SpecFT30):
            for minute in range(0, 24 * 60, 5):
                time = datetime.datetime(2026, 6, 10) + datetime.timedelta(minutes=minute)
                taf = CurrentTaf(spec, time=time)
                key = taf.key()
                assert taf.openings[key] <= time < taf.openings[key] + spec.interval


if __name__ == '__main__':
    pytest.main()
