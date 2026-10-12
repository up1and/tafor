import datetime

import pytest

from tafor.core.utils.common import checkVersion
from tafor.core.utils.pagination import Pagination
from tafor.core.utils.time import ceilTime, parsePeriod, parseTime, parseTimez, timeAgo
from tafor.core.models import Taf


def test_frozen_clock_reaches_column_defaults_and_parsers(database, frozen_time):
    """Spike: time-machine must reach both import-time captured references
    (SQLAlchemy column default) and the parser basetime fallbacks."""
    with database.session() as session:
        item = Taf(type='FT', text='TAF ZPPP 100800Z 1009/1018 32008G15MPS 9999 SCT020=')
        session.add(item)

    assert item.created == frozen_time
    assert parseTime('100800') == frozen_time


def test_parse_timez_accepts_basetime():
    basetime = datetime.datetime(2026, 6, 5, 3, 0)
    assert parseTimez('100800', basetime=basetime) == datetime.datetime(2026, 6, 10, 8, 0)


def test_check_version():
    assert checkVersion('1.1.1', '1.1')
    assert checkVersion('1.3', '1.1.2')
    assert checkVersion('1.2.dev', '1.1.dev')
    assert checkVersion('v1.1.dev', 'v1.1')
    assert not checkVersion('1.0.1', '1.0.1.dev')

def test_basic_pagination():
    p = Pagination(None, 1, 20, 500, [])
    assert p.page == 1
    assert not p.hasPrev
    assert p.hasNext
    assert p.total == 500
    assert p.pages == 25
    assert p.nextNum == 2

def test_parse_time_interval():
    time = datetime.datetime(2018, 5, 1)
    assert parsePeriod('0312', time) == (datetime.datetime(2018, 5, 1, 3), datetime.datetime(2018, 5, 1, 12))


class TestCeilTime:

    """ceilTime snaps to a 5-minute grid, then adds `amount` minutes.

    The grid is hard-coded to 5 while `amount` only sets the offset, so a
    value already on a 5-minute mark still moves forward. These tests pin
    that down: core/sigmet/compose.py uses it to pick the valid period.
    """

    def test_snaps_down_to_the_five_minute_grid_then_adds_amount(self):
        value = datetime.datetime(2026, 10, 12, 11, 3)
        assert ceilTime(value) == datetime.datetime(2026, 10, 12, 11, 10)

    def test_amount_sets_the_offset(self):
        value = datetime.datetime(2026, 10, 12, 11, 3)
        assert ceilTime(value, amount=5) == datetime.datetime(2026, 10, 12, 11, 5)
        assert ceilTime(value, amount=15) == datetime.datetime(2026, 10, 12, 11, 15)

    def test_exact_grid_mark_still_moves_forward(self):
        # 11:05 is already on the grid, so the 10 minute offset is added in full
        value = datetime.datetime(2026, 10, 12, 11, 5)
        assert ceilTime(value) == datetime.datetime(2026, 10, 12, 11, 15)

    def test_seconds_and_microseconds_are_dropped(self):
        value = datetime.datetime(2026, 10, 12, 11, 0, 30, 123456)
        assert ceilTime(value) == datetime.datetime(2026, 10, 12, 11, 10)

    def test_rolls_over_the_hour(self):
        value = datetime.datetime(2026, 10, 12, 11, 58)
        assert ceilTime(value) == datetime.datetime(2026, 10, 12, 12, 5)


class TestTimeAgo:

    """timeAgo used .seconds, which drops the days field of a timedelta.

    Anything three or more days old collapsed to 'just now', so every
    unit past hours was unreachable.
    """

    def ago(self, base, **kwargs):
        return timeAgo(base - datetime.timedelta(**kwargs))

    def test_seconds_minutes_hours(self, frozen_time):
        assert self.ago(frozen_time, seconds=30) == '30 seconds ago'
        assert self.ago(frozen_time, minutes=5) == '5 minutes ago'
        assert self.ago(frozen_time, hours=2) == '2 hours ago'

    def test_days_are_not_lost(self, frozen_time):
        # days=3 gives timedelta.seconds == 0, which used to read as 'just now'
        assert self.ago(frozen_time, days=1) == '1 day ago'
        assert self.ago(frozen_time, days=3) == '3 days ago'
        assert self.ago(frozen_time, hours=25) == '1 day ago'

    def test_weeks_months_years(self, frozen_time):
        assert self.ago(frozen_time, weeks=2) == '2 weeks ago'
        assert self.ago(frozen_time, days=366) == '1 year ago'
        assert self.ago(frozen_time, days=1100) == '3 years ago'

    def test_under_ten_seconds_reads_as_just_now(self, frozen_time):
        assert timeAgo(frozen_time) == 'just now'
        assert self.ago(frozen_time, seconds=9) == 'just now'
        assert self.ago(frozen_time, seconds=10) == '10 seconds ago'

    def test_future_dates_read_as_in(self, frozen_time):
        assert timeAgo(frozen_time + datetime.timedelta(minutes=5)) == 'in 5 minutes'
        assert timeAgo(frozen_time + datetime.timedelta(days=3)) == 'in 3 days'

    def test_aware_date_against_the_naive_clock(self, frozen_time):
        # A date carrying a tzinfo used to raise against the naive utcnow().
        aware = frozen_time.replace(tzinfo=datetime.timezone.utc)

        assert timeAgo(aware - datetime.timedelta(hours=3)) == '3 hours ago'
        assert timeAgo(aware + datetime.timedelta(hours=3)) == 'in 3 hours'

    def test_aware_clock_against_a_naive_date(self, frozen_time):
        # The mirror case: `now` is aware while the stored date is naive.
        awareNow = frozen_time.replace(tzinfo=datetime.timezone.utc)
        naive = frozen_time - datetime.timedelta(hours=3)

        assert timeAgo(naive, awareNow) == '3 hours ago'


if __name__ == "__main__":
    pytest.main()
