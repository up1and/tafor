"""Tests for the Pagination class and the paginate() helper.

test_pagination.py covers repository.paginated(); this file covers the
standalone pagination module that sits under it.
"""

import datetime

import pytest

from tafor.core.models import Metar, createDatabase
from tafor.core.utils.pagination import Pagination, paginate


@pytest.fixture
def database():
    database = createDatabase(uri='sqlite:///:memory:')
    with database.session() as session:
        for i in range(30):
            session.add(Metar(
                type='SA',
                text='METAR ZBAD 25{:02d}00Z 30006KT 9999 FEW040='.format(i % 24),
                created=datetime.datetime(2026, 8, 1) + datetime.timedelta(hours=i),
            ))
    return database


@pytest.fixture
def pageOf(database):
    """Run paginate() against a live session, as the repository does."""

    def run(page=1, perPage=None, total=None):
        with database.session() as session:
            query = session.query(Metar)
            return paginate(query, page=page, perPage=perPage, total=total)

    return run


def make(page=1, perPage=10, total=30, items=None, paginate=None):
    return Pagination(paginate, page=page, perPage=perPage,
                      total=total, items=items or [])


def test_pages_round_up_to_cover_a_partial_last_page():
    assert make(total=30, perPage=12).pages == 3
    assert make(total=25, perPage=12).pages == 3


def test_no_pages_when_per_page_is_zero():
    # a zero page size would divide by zero, so it reports no pages
    pagination = make(perPage=0)

    assert pagination.pages == 0
    assert not pagination.hasNext


def test_the_first_page_has_no_previous():
    pagination = make(page=1)

    assert not pagination.hasPrev
    assert pagination.prevNum is None
    assert pagination.hasNext
    assert pagination.nextNum == 2


def test_the_last_page_has_no_next():
    pagination = make(page=3)

    assert pagination.hasPrev
    assert pagination.prevNum == 2
    assert not pagination.hasNext
    assert pagination.nextNum is None


def test_prev_and_next_delegate_to_the_paginate_callback():
    calls = []

    def callback(page, perPage):
        calls.append((page, perPage))
        return (page, perPage)

    pagination = make(page=2, paginate=callback)

    assert pagination.prev() == (1, 10)
    assert pagination.next() == (3, 10)
    assert calls == [(1, 10), (3, 10)]


def test_stepping_without_a_callback_is_an_error():
    with pytest.raises(AssertionError):
        make(page=2).prev()

    with pytest.raises(AssertionError):
        make(page=2).next()


def test_a_short_first_page_reports_its_own_length_as_the_total(pageOf):
    pagination = pageOf(page=1, perPage=50)

    assert pagination.total == 30
    assert len(pagination.items) == 30


def test_a_full_page_falls_back_to_counting_the_query(pageOf):
    pagination = pageOf(page=1, perPage=12)

    assert pagination.total == 30
    assert len(pagination.items) == 12


def test_a_page_beyond_the_first_always_counts(pageOf):
    pagination = pageOf(page=2, perPage=12)

    assert pagination.page == 2
    assert pagination.total == 30
    assert len(pagination.items) == 12


def test_a_cached_total_is_used_as_is(pageOf):
    assert pageOf(page=2, perPage=12, total=99).total == 99


def test_a_page_below_one_is_clamped(pageOf):
    assert pageOf(page=0, perPage=12).page == 1
    assert pageOf(page=-5, perPage=12).page == 1


def test_a_missing_or_negative_per_page_defaults_to_twenty(pageOf):
    assert pageOf(page=1).perPage == 20
    assert pageOf(page=1, perPage=-1).perPage == 20


def test_the_last_page_holds_the_remainder(pageOf):
    pagination = pageOf(page=3, perPage=12)

    assert len(pagination.items) == 6
    assert pagination.pages == 3
    assert not pagination.hasNext
