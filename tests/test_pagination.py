import datetime
import uuid

import pytest
from sqlalchemy.orm import Query

from tafor.core.models import Metar, createDatabase
from tafor.core.repositories import Repository


@pytest.fixture
def repository():
    database = createDatabase(uri='sqlite:///:memory:')
    with database.session() as session:
        for i in range(30):
            session.add(Metar(
                type='SA',
                text='METAR ZBAD 25{:02d}00Z 30006KT 9999 FEW040='.format(i % 24),
                created=datetime.datetime(2026, 8, 1) + datetime.timedelta(hours=i),
            ))
    return Repository(database)


class TestPaginated(object):

    def test_total_computed_when_not_cached(self, repository):
        pagination = repository.paginated(Metar, page=1, perPage=12)
        assert pagination.total == 30
        assert len(pagination.items) == 12

    def test_cached_total_skips_count_query(self, monkeypatch, repository):
        def boom(*args, **kwargs):
            raise AssertionError('count() should not be called when total is cached')

        monkeypatch.setattr(Query, 'count', boom)

        pagination = repository.paginated(Metar, page=2, perPage=12, total=30)
        assert pagination.total == 30
        assert pagination.page == 2
        assert len(pagination.items) == 12

    def test_cached_total_pages_and_navigation(self, repository):
        pagination = repository.paginated(Metar, page=3, perPage=12, total=30)
        assert pagination.pages == 3
        assert not pagination.hasNext
        assert len(pagination.items) == 6
