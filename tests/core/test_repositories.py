import datetime

from tafor.core.models import Taf
from tafor.core.repositories import Repositories


TAF_TEXT = 'TAF ZPPP 060500Z 0606/0712 32008G15MPS 9999 SCT020='


class TestTafRepository:

    def test_available_confirms_existing_message(self, database):
        repos = Repositories(database)
        created = datetime.datetime.utcnow() - datetime.timedelta(hours=1)
        with database.session() as session:
            session.add(Taf(type='FC', text=TAF_TEXT, source='api', created=created))

        taf = repos.taf.available('FC', TAF_TEXT)

        assert taf is not None
        assert taf.type == 'FC'
        assert taf.confirmed is not None

    def test_available_does_not_confirm_across_types(self, database):
        repos = Repositories(database)
        created = datetime.datetime.utcnow() - datetime.timedelta(hours=1)
        with database.session() as session:
            session.add(Taf(type='FC', text=TAF_TEXT, source='api', created=created))

        taf = repos.taf.available('FT', TAF_TEXT)

        assert taf.type == 'FT'
        assert taf.source == 'api'

        with database.session() as session:
            fc = session.query(Taf).filter(Taf.type == 'FC').first()
            assert fc.confirmed is None

    def test_available_ignores_outdated_message(self, database):
        repos = Repositories(database)
        created = datetime.datetime.utcnow() - datetime.timedelta(hours=33)
        with database.session() as session:
            session.add(Taf(type='FC', text=TAF_TEXT, source='api', created=created))

        taf = repos.taf.available('FC', TAF_TEXT)

        assert taf.type == 'FC'
        assert taf.id is None
