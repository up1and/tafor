import datetime

import pytest

from tafor.utils import checkVersion
from tafor.utils.pagination import Pagination
from tafor.utils.convert import parseTimeInterval, parseTime, parseDateTime, parseTimez, ceilTime


def test_check_version():
    assert checkVersion('1.1.1', '1.1')
    assert checkVersion('1.3', '1.1.2')
    assert checkVersion('1.2.dev', '1.1.dev')
    assert not checkVersion('1.0.1', '1.0.1.dev')
    assert not checkVersion('1.1', '1.1')

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
    assert parseTimeInterval('0312', time) == (datetime.datetime(2018, 5, 1, 3), datetime.datetime(2018, 5, 1, 12))


if __name__ == "__main__":
    pytest.main()
