"""Tests for tafor/core/repositories.py."""

import datetime

import pytest

from tafor.core.models import Metar, Sigmet, Taf, Trend
from tafor.core.repositories import (Repositories, SigmetFilter, subscribedTypes)


TAF_TEXT = 'TAF ZPPP 060500Z 0606/0712 32008G15MPS 9999 SCT020='
METAR_TEXT = 'METAR ZJHK 210900Z 14004MPS 4500 -RA BKN030='

# A SIGMET valid 100730/101430: parsed against its row's created time
SIGMET_ACTIVE = ('ZJSA SIGMET 2 VALID 100730/101430 ZJHK-\n'
                 'ZJSA SANYA FIR OBSC TS FCST WI E11223 N1829 - E11142 N1916 TOP FL030 MOV N 300KMH NC=')
SIGMET_CANCEL = ('ZJSA SIGMET 1 VALID 101200/101900 ZJHK-\n'
                 'ZJSA SANYA FIR CNL SIGMET 2 100730/101430=')
SIGMET_ORPHAN_CANCEL = ('ZJSA SIGMET 4 VALID 101200/101900 ZJHK-\n'
                        'ZJSA SANYA FIR CNL SIGMET 9 100730/101430=')
SIGMET_EXPIRED = ('ZJSA SIGMET 3 VALID 100130/100230 ZJHK-\n'
                  'ZJSA SANYA FIR OBSC TS FCST WI E11223 N1829 - E11142 N1916 TOP FL030 MOV N 300KMH NC=')

# Frozen clock (via the shared frozen_time fixture) for the time-sensitive
# repository methods. The 08:00 moment puts the current FC period ('0918'
# -> 1009/1018) past its issue window.
MOMENT = datetime.datetime(2026, 6, 10, 8, 0)
PERIOD = '1009/1018'


def add(session, model, **kwargs):
    item = model(**kwargs)
    session.add(item)
    return item


class TestSubscribedTypes:

    def test_full_subscription(self):
        assert subscribedTypes(True, True) == ['SA', 'SP', 'FT', 'WS', 'WC', 'WV', 'WA']

    def test_short_taf_spec_uses_fc(self):
        assert subscribedTypes(False, False) == ['SA', 'SP', 'FC']

    def test_sigmet_opt_out(self):
        assert subscribedTypes(True, False) == ['SA', 'SP', 'FT']


class TestSigmetFilter:

    def test_explicit_designator(self):
        assert SigmetFilter(designator='WS').designators() == ['WS']

    def test_sigmet_category_designators(self):
        assert SigmetFilter(category='SIGMET').designators() == ['WS', 'WC', 'WV']

    def test_airmet_category_designators(self):
        assert SigmetFilter(category='AIRMET').designators() == ['WA']

    def test_no_category_means_no_designators(self):
        assert SigmetFilter().designators() == []


class TestTafRepository:

    def test_available_confirms_existing_message(self, database):
        repos = Repositories(database)
        created = datetime.datetime.utcnow() - datetime.timedelta(hours=1)
        with database.session() as session:
            add(session, Taf, type='FC', text=TAF_TEXT, source='api', created=created)

        taf = repos.taf.available('FC', TAF_TEXT)

        assert taf is not None
        assert taf.type == 'FC'
        assert taf.confirmed is not None

    def test_available_does_not_confirm_across_types(self, database):
        repos = Repositories(database)
        created = datetime.datetime.utcnow() - datetime.timedelta(hours=1)
        with database.session() as session:
            add(session, Taf, type='FC', text=TAF_TEXT, source='api', created=created)

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
            add(session, Taf, type='FC', text=TAF_TEXT, source='api', created=created)

        taf = repos.taf.available('FC', TAF_TEXT)

        assert taf.type == 'FC'
        assert taf.id is None

    def test_has_recent(self, database):
        repos = Repositories(database)
        created = datetime.datetime.utcnow() - datetime.timedelta(hours=1)
        with database.session() as session:
            add(session, Taf, type='FC', text=TAF_TEXT, created=created)

        assert repos.taf.hasRecent('0606/0712') is not None
        assert repos.taf.hasRecent('0606/0713') is None

    def test_has_recent_respects_window(self, database):
        repos = Repositories(database)
        created = datetime.datetime.utcnow() - datetime.timedelta(hours=33)
        with database.session() as session:
            add(session, Taf, type='FC', text=TAF_TEXT, created=created)

        assert repos.taf.hasRecent('0606/0712') is None

    def test_amend_sequence_starts_at_aaa(self, database):
        repos = Repositories(database)
        assert repos.taf.amendSequence('0606/0712', 'AMD') == 'AAA'

    def test_amend_sequence_counts_amendments(self, database):
        repos = Repositories(database)
        created = datetime.datetime.utcnow() - datetime.timedelta(hours=1)
        with database.session() as session:
            add(session, Taf, type='FT', text='TAF AMD ZPPP 060500Z 0606/0712 32008G15MPS=', created=created)
            add(session, Taf, type='FT', text='TAF AMD ZPPP 060600Z 0606/0712 32012MPS=', created=created)

        assert repos.taf.amendSequence('0606/0712', 'AMD') == 'AAC'

    def test_amend_sequence_prefixes_corrections_with_cc(self, database):
        repos = Repositories(database)
        created = datetime.datetime.utcnow() - datetime.timedelta(hours=1)
        with database.session() as session:
            add(session, Taf, type='FT', text='TAF COR ZPPP 060500Z 0606/0712 32008G15MPS=', created=created)

        assert repos.taf.amendSequence('0606/0712', 'COR') == 'CCB'


class TestTafRepositoryStatus:
    """status() drives the TAF alarm: freeze utcnow at 08:00 so the current
    FC period is 1009/1018 and its issue window (07:00 + delay) has passed."""

    @pytest.fixture
    def repos(self, database, frozen_time):
        return Repositories(database)

    def seed(self, database, text, created, confirmed=None):
        with database.session() as session:
            add(session, Taf, type='FC', text=text, created=created, confirmed=confirmed)

    def test_status_without_message(self, repos):
        status = repos.taf.status('fc', delayMinutes=30)

        assert status['period'] == PERIOD
        assert status['message'] is None
        assert status['isExpired'] is True
        assert status['shouldRemind'] is True

    def test_unconfirmed_message_keeps_alarm(self, repos, database):
        self.seed(database, TAF_TEXT.replace('0606/0712', PERIOD),
                  created=MOMENT - datetime.timedelta(hours=1))

        status = repos.taf.status('fc', delayMinutes=30)

        assert status['message'] is not None
        assert status['isExpired'] is True

    def test_confirmed_message_clears_alarm(self, repos, database):
        self.seed(database, TAF_TEXT.replace('0606/0712', PERIOD),
                  created=MOMENT - datetime.timedelta(hours=1),
                  confirmed=MOMENT - datetime.timedelta(minutes=30))

        status = repos.taf.status('fc', delayMinutes=30)

        assert status['isExpired'] is False

    def test_amended_message_is_ignored(self, repos, database):
        amended = 'TAF AMD ZPPP 100800Z {} 32008G15MPS='.format(PERIOD)
        self.seed(database, amended, created=MOMENT - datetime.timedelta(hours=1),
                  confirmed=MOMENT - datetime.timedelta(minutes=30))

        status = repos.taf.status('fc', delayMinutes=30)

        assert status['message'] is None
        assert status['isExpired'] is True

    def test_cnl_suppresses_alarm(self, repos, database):
        self.seed(database, TAF_TEXT.replace('0606/0712', PERIOD),
                  created=MOMENT - datetime.timedelta(hours=1))
        # A TAF cancel message ends in CNL without a closing '=' so that
        # Taf.isCnl() finds the CNL token
        self.seed(database, 'TAF ZPPP 101000Z {} CNL'.format(PERIOD),
                  created=MOMENT - datetime.timedelta(minutes=30))

        status = repos.taf.status('fc', delayMinutes=30)

        assert status['isExpired'] is False
        assert status['shouldRemind'] is False


class TestMetarRepository:

    def test_available_returns_transient_for_new_message(self, database):
        repos = Repositories(database)

        metar = repos.metar.available('SA', METAR_TEXT)

        assert metar is not None
        assert metar.type == 'SA'
        assert metar.id is None

    def test_available_skips_unchanged_message(self, database):
        repos = Repositories(database)
        with database.session() as session:
            add(session, Metar, type='SA', text=METAR_TEXT, created=datetime.datetime.utcnow())

        assert repos.metar.available('SA', METAR_TEXT) is None

    def test_latest_within_hours(self, database):
        repos = Repositories(database)
        with database.session() as session:
            add(session, Metar, type='SA', text=METAR_TEXT, created=datetime.datetime.utcnow())

        assert repos.metar.latest(hours=2) is not None
        assert repos.metar.latest(hours=0) is None


class TestSigmetRepository:

    def test_count_today_returns_rows_of_the_day(self, database):
        # Despite the name, countToday returns a list
        repos = Repositories(database)
        now = datetime.datetime.utcnow()
        with database.session() as session:
            add(session, Sigmet, type='WS', text=SIGMET_ACTIVE, created=now)
            add(session, Sigmet, type='WC', text=SIGMET_CANCEL, created=now)
            add(session, Sigmet, type='WA', text=SIGMET_ORPHAN_CANCEL, created=now)

        assert len(repos.sigmet.countToday('WS')) == 2
        assert len(repos.sigmet.countToday('WA')) == 1

    def test_latest_skips_cnl_by_default(self, database):
        repos = Repositories(database)
        now = datetime.datetime.utcnow()
        with database.session() as session:
            add(session, Sigmet, type='WS', text=SIGMET_ACTIVE, created=now - datetime.timedelta(minutes=5))
            add(session, Sigmet, type='WS', text=SIGMET_CANCEL, created=now)

        assert repos.sigmet.latest('WS').isCnl() is False
        assert repos.sigmet.latest('WS', excludeCnl=False).isCnl() is True

    def test_latest_ignores_other_types(self, database):
        repos = Repositories(database)
        with database.session() as session:
            add(session, Sigmet, type='WS', text=SIGMET_ACTIVE, created=datetime.datetime.utcnow())

        assert repos.sigmet.latest('WC') is None

    @pytest.fixture
    def frozen_repos(self, database, frozen_time):
        return Repositories(database)

    def seed_sigmet(self, database, text, created, confirmed=None):
        with database.session() as session:
            return add(session, Sigmet, type='WS', text=text, created=created, confirmed=confirmed)

    def test_current_keeps_active_sigmet(self, frozen_repos, database):
        stored = self.seed_sigmet(database, SIGMET_ACTIVE, created=MOMENT)

        currents = frozen_repos.sigmet.current()

        assert [s.id for s in currents] == [stored.id]

    def test_cancellation_removes_both_messages(self, frozen_repos, database):
        self.seed_sigmet(database, SIGMET_ACTIVE, created=MOMENT)
        self.seed_sigmet(database, SIGMET_CANCEL, created=MOMENT)

        assert frozen_repos.sigmet.current() == []

    def test_orphan_cancellation_is_kept(self, frozen_repos, database):
        stored = self.seed_sigmet(database, SIGMET_ORPHAN_CANCEL, created=MOMENT)

        currents = frozen_repos.sigmet.current()

        assert [s.id for s in currents] == [stored.id]

    def test_expired_sigmet_is_dropped(self, frozen_repos, database):
        # created early enough that 100230 is in the past of the frozen clock
        self.seed_sigmet(database, SIGMET_EXPIRED, created=MOMENT - datetime.timedelta(hours=7))

        assert frozen_repos.sigmet.current() == []

    def test_current_sorts_by_created(self, frozen_repos, database):
        active = self.seed_sigmet(database, SIGMET_ACTIVE, created=MOMENT)
        orphan = self.seed_sigmet(database, SIGMET_ORPHAN_CANCEL,
                                  created=MOMENT + datetime.timedelta(minutes=1))

        currents = frozen_repos.sigmet.current()

        assert [s.id for s in currents] == [active.id, orphan.id]

    def test_available_adds_new_message(self, database):
        repos = Repositories(database)

        items = repos.sigmet.available('WS', [SIGMET_ACTIVE])

        assert len(items) == 1
        item = items[0]
        assert item.type == 'WS'
        assert item.source == 'api'
        assert item.confirmed is not None
        assert item.id is None
        assert item.text.endswith('=')
        assert 'ZJHK-' in item.text

    def test_available_confirms_stored_unconfirmed(self, database):
        repos = Repositories(database)
        stored = self.seed_sigmet(database, SIGMET_ACTIVE,
                                  created=datetime.datetime.utcnow() - datetime.timedelta(hours=1))

        items = repos.sigmet.available('WS', [SIGMET_ACTIVE])

        assert len(items) == 1
        assert items[0].id == stored.id
        assert items[0].confirmed is not None

    def test_available_normalizes_whitespace(self, database):
        repos = Repositories(database)
        stored = self.seed_sigmet(database, SIGMET_ACTIVE,
                                  created=datetime.datetime.utcnow() - datetime.timedelta(hours=1))

        spaced = ' '.join(SIGMET_ACTIVE.split()) + '  '
        items = repos.sigmet.available('WS', [spaced])

        assert len(items) == 1
        assert items[0].id == stored.id

    def test_available_ignores_stored_beyond_window(self, database):
        repos = Repositories(database)
        self.seed_sigmet(database, SIGMET_ACTIVE,
                         created=datetime.datetime.utcnow() - datetime.timedelta(hours=25))

        items = repos.sigmet.available('WS', [SIGMET_ACTIVE])

        assert len(items) == 1
        assert items[0].id is None


class TestMessageRepository:

    def test_available_dispatches_by_key(self, database):
        repos = Repositories(database)

        # Message values are strings for metar/taf keys and lists of
        # messages for sigmet keys (the shape fetchMessage produces)
        items = repos.message.available({
            'SA': METAR_TEXT,
            'FT': TAF_TEXT,
            'WS': [SIGMET_ACTIVE],
        })

        kinds = sorted(type(item).__name__ for item in items)
        assert kinds == ['Metar', 'Sigmet', 'Taf']

    def test_available_filters_by_types(self, database):
        repos = Repositories(database)

        items = repos.message.available({
            'SA': METAR_TEXT,
            'FT': TAF_TEXT,
        }, types=['FT'])

        assert [type(item).__name__ for item in items] == ['Taf']

    def test_available_skips_unchanged_metar(self, database):
        repos = Repositories(database)
        with database.session() as session:
            add(session, Metar, type='SA', text=METAR_TEXT, created=datetime.datetime.utcnow())

        items = repos.message.available({'SA': METAR_TEXT, 'FT': TAF_TEXT})

        assert [type(item).__name__ for item in items] == ['Taf']

    def test_recent_returns_latest_of_each_kind(self, database):
        repos = Repositories(database)
        now = datetime.datetime.utcnow()
        with database.session() as session:
            add(session, Taf, type='FC', text=TAF_TEXT, created=now - datetime.timedelta(hours=1))
            add(session, Metar, type='SA', text=METAR_TEXT, created=now - datetime.timedelta(minutes=30))
            add(session, Trend, text='BECMG 1418 9999 NSW=', created=now - datetime.timedelta(minutes=10))

        recent = repos.message.recent('FC', since=now - datetime.timedelta(hours=24))

        assert recent['taf'].text == TAF_TEXT
        assert recent['metar'].text == METAR_TEXT
        assert recent['trend'].text == 'BECMG 1418 9999 NSW='
        assert recent['sigmets'] == []

    def test_recent_drops_nosig_trend(self, database):
        repos = Repositories(database)
        with database.session() as session:
            add(session, Trend, text='NOSIG=', created=datetime.datetime.utcnow())

        recent = repos.message.recent('FC', since=datetime.datetime.utcnow() - datetime.timedelta(hours=24))

        assert recent['trend'] is None

    def test_recent_passes_through_current_sigmets(self, database):
        repos = Repositories(database)
        sigmet = Sigmet(type='WS', text=SIGMET_ACTIVE)

        recent = repos.message.recent(
            'FC', since=datetime.datetime.utcnow() - datetime.timedelta(hours=24),
            includeSigmet=True, currentSigmets=[sigmet])

        assert recent['sigmets'] == [sigmet]

    def test_recent_without_sigmet_flag(self, database):
        repos = Repositories(database)
        sigmet = Sigmet(type='WS', text=SIGMET_ACTIVE)

        recent = repos.message.recent(
            'FC', since=datetime.datetime.utcnow() - datetime.timedelta(hours=24),
            currentSigmets=[sigmet])

        assert recent['sigmets'] == []

    def test_add_persists_transient_model(self, database):
        repos = Repositories(database)
        metar = repos.metar.available('SA', METAR_TEXT)

        repos.message.add(metar)

        with database.session() as session:
            stored = session.query(Metar).first()
            assert stored is not None
            assert stored.text == METAR_TEXT


if __name__ == '__main__':
    pytest.main([__file__])
