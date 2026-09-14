import datetime

import pytest

from tafor.core.utils.common import checkVersion
from tafor.core.utils.pagination import Pagination
from tafor.core.utils.time import ceilTime, parsePeriod, parseTime, parseTimez
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


if __name__ == "__main__":
    pytest.main()
