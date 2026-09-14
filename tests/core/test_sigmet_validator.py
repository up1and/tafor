"""Tests for tafor/core/sigmet/validator.py."""

import datetime

from tafor.core.sigmet.validator import SigmetValidator


NOW = datetime.datetime(2026, 6, 10, 8, 0)


class TestValidatePeriod:

    def test_incomplete_input_passes(self):
        assert SigmetValidator.validatePeriod(None, span=4, now=NOW) is None

    def test_valid_period_passes(self):
        durations = (NOW + datetime.timedelta(hours=1), NOW + datetime.timedelta(hours=3))
        assert SigmetValidator.validatePeriod(durations, span=4, now=NOW) is None

    def test_start_over_24_hours_ahead_rejected(self):
        start = NOW + datetime.timedelta(hours=25)
        durations = (start, start + datetime.timedelta(hours=2))
        assert SigmetValidator.validatePeriod(durations, span=4, now=NOW) == SigmetValidator.START_TOO_FAR

    def test_start_in_the_distant_past_passes(self):
        # Only a future cap exists: an arbitrarily old start is accepted
        start = NOW - datetime.timedelta(days=30)
        durations = (start, start + datetime.timedelta(hours=2))
        assert SigmetValidator.validatePeriod(durations, span=4, now=NOW) is None

    def test_end_equal_to_start_rejected(self):
        durations = (NOW, NOW)
        assert SigmetValidator.validatePeriod(durations, span=4, now=NOW) == SigmetValidator.END_NOT_GREATER

    def test_end_before_start_rejected(self):
        durations = (NOW, NOW - datetime.timedelta(hours=1))
        assert SigmetValidator.validatePeriod(durations, span=4, now=NOW) == SigmetValidator.END_NOT_GREATER

    def test_period_over_span_returns_tuple_with_hours(self):
        # Inconsistent with the other outcomes: this one error carries
        # parameters and comes back as a (code, kwargs) tuple, so callers
        # have to unwrap it (see widgets/sigmet.py validatePeriod)
        durations = (NOW, NOW + datetime.timedelta(hours=5))
        error = SigmetValidator.validatePeriod(durations, span=4, now=NOW)
        assert error == (SigmetValidator.PERIOD_TOO_LONG, {'hours': 4})

    def test_period_on_span_boundary_passes(self):
        durations = (NOW, NOW + datetime.timedelta(hours=4))
        assert SigmetValidator.validatePeriod(durations, span=4, now=NOW) is None

    def test_now_defaults_to_utcnow(self):
        start = datetime.datetime.utcnow() + datetime.timedelta(hours=25)
        durations = (start, start + datetime.timedelta(hours=1))
        assert SigmetValidator.validatePeriod(durations, span=4) == SigmetValidator.START_TOO_FAR


class TestValidateFlightLevel:

    def test_missing_values_pass(self):
        assert SigmetValidator.validateFlightLevel('', '') is None
        assert SigmetValidator.validateFlightLevel('245', '') is None
        assert SigmetValidator.validateFlightLevel('', '320') is None

    def test_top_above_base_passes(self):
        assert SigmetValidator.validateFlightLevel('245', '320') is None

    def test_top_equal_to_base_rejected(self):
        assert SigmetValidator.validateFlightLevel('245', '245') == SigmetValidator.FLIGHT_LEVEL_INVALID

    def test_top_below_base_rejected(self):
        assert SigmetValidator.validateFlightLevel('320', '245') == SigmetValidator.FLIGHT_LEVEL_INVALID

    def test_non_numeric_input_raises(self):
        # The Qt regexp validator on the line edits is the only guard, the
        # validator itself does int() without handling errors
        import pytest
        with pytest.raises(ValueError):
            SigmetValidator.validateFlightLevel('abc', '320')


if __name__ == '__main__':
    import pytest
    pytest.main([__file__])
