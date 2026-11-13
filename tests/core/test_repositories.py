"""Tests for tafor/core/repositories.py."""

import datetime
import logging

import pytest

from tafor.core.models import Metar, Sigmet, Taf, Trend
from tafor.core.repositories import (Repositories, SigmetFilter, subscribedTypes)
from tafor.core.taf import PrimaryState, SpecFC, composeBody
from tafor.core.utils.time import utcnow


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

# Same sequence and validity as SIGMET_ACTIVE, but an AIRMET: the number
# space is per product, so the two are distinct reports.
AIRMET_SAME_NUMBER = ('ZJSA AIRMET 2 VALID 100730/101430 ZJHK-' + chr(92) + 'n'
                      'ZJSA SANYA FIR ISOL TS WI E11223 N1829 - E11142 N1916 TOP FL030=')
# A cancellation of the AIRMET above. Before the key carried the product
# category it also matched -- and removed -- the SIGMET with the same number.
AIRMET_CANCEL = ('ZJSA AIRMET 7 VALID 101200/101900 ZJHK-' + chr(92) + 'n'
                 'ZJSA SANYA FIR CNL AIRMET 2 100730/101430=')
# A report from another unit, same number and validity as SIGMET_ACTIVE.
OTHER_FIR_REPORT = ('ZBPE SIGMET 2 VALID 100730/101430 ZBAA-' + chr(92) + 'n'
                    'ZBPE BEIJING FIR SEV TURB FCST WI N4000 E11600 - N4100 E11700 TOP FL030 MOV E 20KT NC=')
OTHER_FIR_CANCEL = ('ZBPE SIGMET 9 VALID 101200/101900 ZBAA-' + chr(92) + 'n'
                    'ZBPE BEIJING FIR CNL SIGMET 2 100730/101430=')

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

    def test_save_confirms_existing_message(self, database):
        repos = Repositories(database)
        created = datetime.datetime.utcnow() - datetime.timedelta(hours=1)
        with database.session() as session:
            add(session, Taf, type='FC', text=TAF_TEXT, source='api', created=created)

        changes = repos.message.save({'FC': TAF_TEXT})

        assert len(changes) == 1
        taf = changes[0]
        assert taf.type == 'FC'
        assert taf.confirmed is not None

    def test_save_does_not_confirm_across_types(self, database):
        repos = Repositories(database)
        created = datetime.datetime.utcnow() - datetime.timedelta(hours=1)
        with database.session() as session:
            add(session, Taf, type='FC', text=TAF_TEXT, source='api', created=created)

        changes = repos.message.save({'FT': TAF_TEXT})

        taf = changes[0]
        assert taf.type == 'FT'
        assert taf.source == 'api'

        with database.session() as session:
            fc = session.query(Taf).filter(Taf.type == 'FC').first()
            assert fc.confirmed is None

    def test_save_ignores_outdated_message(self, database):
        repos = Repositories(database)
        created = datetime.datetime.utcnow() - datetime.timedelta(hours=33)
        with database.session() as session:
            add(session, Taf, type='FC', text=TAF_TEXT, source='api', created=created)

        changes = repos.message.save({'FC': TAF_TEXT})

        # The old row is outside the window, so a second row is stored
        taf = changes[0]
        assert taf.type == 'FC'

        with database.session() as session:
            assert session.query(Taf).count() == 2

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

    def test_amend_count_is_zero_without_amendments(self, database):
        repos = Repositories(database)
        assert repos.taf.amendCount('0606/0712', 'AMD') == 0

    def test_amend_count_counts_amendments(self, database):
        repos = Repositories(database)
        created = datetime.datetime.utcnow() - datetime.timedelta(hours=1)
        with database.session() as session:
            add(session, Taf, type='FT', text='TAF AMD ZPPP 060500Z 0606/0712 32008G15MPS=', created=created)
            add(session, Taf, type='FT', text='TAF AMD ZPPP 060600Z 0606/0712 32012MPS=', created=created)

        assert repos.taf.amendCount('0606/0712', 'AMD') == 2

    def test_amend_count_is_per_modifier(self, database):
        # Only the notation is built in core/taf; what the repository owes is
        # "how many of *this* marker went out for this period".
        repos = Repositories(database)
        created = datetime.datetime.utcnow() - datetime.timedelta(hours=1)
        with database.session() as session:
            add(session, Taf, type='FT', text='TAF COR ZPPP 060500Z 0606/0712 32008G15MPS=', created=created)

        assert repos.taf.amendCount('0606/0712', 'COR') == 1
        assert repos.taf.amendCount('0606/0712', 'AMD') == 0


class TestTafRepositoryStatus:
    """status() returns the facts the monitor predicates read.

    Whether those facts mean "expired" or "due" is a function of the clock,
    and is covered in test_states.py.
    """

    @pytest.fixture
    def repos(self, database, frozen_time):
        return Repositories(database)

    def seed(self, database, text, created, confirmed=None):
        with database.session() as session:
            add(session, Taf, type='FC', text=text, created=created, confirmed=confirmed)

    def test_status_without_message(self, repos):
        status = repos.taf.status(SpecFC)

        assert status['period'] == PERIOD
        assert status['message'] is None
        assert status['confirmed'] is False
        assert status['cancelled'] is False

    def test_unconfirmed_message_is_reported_unconfirmed(self, repos, database):
        self.seed(database, TAF_TEXT.replace('0606/0712', PERIOD),
                  created=MOMENT - datetime.timedelta(hours=1))

        status = repos.taf.status(SpecFC)

        assert status['message'] is not None
        assert status['confirmed'] is False

    def test_confirmed_message_is_reported_confirmed(self, repos, database):
        self.seed(database, TAF_TEXT.replace('0606/0712', PERIOD),
                  created=MOMENT - datetime.timedelta(hours=1),
                  confirmed=MOMENT - datetime.timedelta(minutes=30))

        status = repos.taf.status(SpecFC)

        assert status['confirmed'] is True

    def test_amended_message_is_ignored(self, repos, database):
        amended = 'TAF AMD ZPPP 100800Z {} 32008G15MPS='.format(PERIOD)
        self.seed(database, amended, created=MOMENT - datetime.timedelta(hours=1),
                  confirmed=MOMENT - datetime.timedelta(minutes=30))

        status = repos.taf.status(SpecFC)

        assert status['message'] is None
        assert status['confirmed'] is False

    def test_cnl_is_reported(self, repos, database):
        self.seed(database, TAF_TEXT.replace('0606/0712', PERIOD),
                  created=MOMENT - datetime.timedelta(hours=1))
        # The composed cancel ends in 'CNL='; the terminator must not hide it
        self.seed(database, 'TAF AMD ZPPP 101000Z {} CNL='.format(PERIOD),
                  created=MOMENT - datetime.timedelta(minutes=30))

        assert repos.taf.status(SpecFC)['cancelled'] is True

    def test_a_core_composed_cancel_is_recognised(self, repos, database):
        state = PrimaryState('MPS', icao='ZPPP', spec=SpecFC)
        state.date = '101000'
        state.period = PERIOD
        state.modifier = 'CNL'
        state.durations = (MOMENT, MOMENT + datetime.timedelta(hours=12))
        text = composeBody(state, [])
        assert text.endswith('CNL=')

        self.seed(database, text, created=MOMENT - datetime.timedelta(minutes=30))

        assert repos.taf.status(SpecFC)['cancelled'] is True

    def test_a_cancellation_from_another_period_is_ignored(self, repos, database):
        # The previous window's CNL must not silence this window's reminder.
        self.seed(database, 'TAF ZPPP 100500Z 1006/1009 CNL',
                  created=MOMENT - datetime.timedelta(hours=1))

        assert repos.taf.status(SpecFC)['cancelled'] is False


class TestMetarRepository:

    def test_save_returns_new_message(self, database):
        repos = Repositories(database)

        changes = repos.message.save({'SA': METAR_TEXT})

        metar = changes[0]
        assert metar.type == 'SA'

    def test_save_skips_unchanged_message(self, database):
        repos = Repositories(database)
        with database.session() as session:
            add(session, Metar, type='SA', text=METAR_TEXT, created=datetime.datetime.utcnow())

        assert repos.message.save({'SA': METAR_TEXT}) == []

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

    def seed_sigmet(self, database, text, created, confirmed=None, type='WS'):
        with database.session() as session:
            return add(session, Sigmet, type=type, text=text, created=created, confirmed=confirmed)

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

    def test_a_cancellation_only_cancels_its_own_product_category(
            self, frozen_repos, database):
        """A SIGMET 2 and an AIRMET 2 can share a number and a window.

        Regression: the key was sequence + validity only, so cancelling the
        AIRMET also took the SIGMET off the current list.
        """
        sigmet = self.seed_sigmet(database, SIGMET_ACTIVE, created=MOMENT, type='WS')
        airmet = self.seed_sigmet(database, AIRMET_SAME_NUMBER, created=MOMENT, type='WA')

        assert {s.id for s in frozen_repos.sigmet.current()} == {sigmet.id, airmet.id}

        cancel = self.seed_sigmet(database, AIRMET_CANCEL, created=MOMENT, type='WA')

        after = frozen_repos.sigmet.current()

        assert [s.id for s in after] == [sigmet.id]
        assert cancel.id not in {s.id for s in after}

    def test_a_cancellation_only_cancels_its_own_unit(self, frozen_repos, database):
        """Two units can each issue a report 2 for the same window.

        Regression: without the originator in the key, one unit's
        cancellation removed the other unit's report.
        """
        ours = self.seed_sigmet(database, SIGMET_ACTIVE, created=MOMENT)
        theirs = self.seed_sigmet(database, OTHER_FIR_REPORT, created=MOMENT)

        assert {s.id for s in frozen_repos.sigmet.current()} == {ours.id, theirs.id}

        self.seed_sigmet(database, OTHER_FIR_CANCEL, created=MOMENT)

        assert [s.id for s in frozen_repos.sigmet.current()] == [ours.id]

    def test_current_sorts_by_created(self, frozen_repos, database):
        active = self.seed_sigmet(database, SIGMET_ACTIVE, created=MOMENT)
        orphan = self.seed_sigmet(database, SIGMET_ORPHAN_CANCEL,
                                  created=MOMENT + datetime.timedelta(minutes=1))

        currents = frozen_repos.sigmet.current()

        assert [s.id for s in currents] == [active.id, orphan.id]

    def test_save_adds_new_message(self, database):
        repos = Repositories(database)

        changes = repos.message.save({'WS': [SIGMET_ACTIVE]})

        assert len(changes) == 1
        item = changes[0]
        assert item.type == 'WS'
        assert item.source == 'api'
        assert item.confirmed is not None
        assert item.text.endswith('=')
        assert 'ZJHK-' in item.text

        with database.session() as session:
            assert session.query(Sigmet).count() == 1

    def test_save_confirms_stored_unconfirmed(self, database):
        repos = Repositories(database)
        stored = self.seed_sigmet(database, SIGMET_ACTIVE,
                                  created=datetime.datetime.utcnow() - datetime.timedelta(hours=1))

        changes = repos.message.save({'WS': [SIGMET_ACTIVE]})

        assert len(changes) == 1
        item = changes[0]
        assert item.id == stored.id
        assert item.confirmed is not None

    def test_save_normalizes_whitespace(self, database):
        repos = Repositories(database)
        stored = self.seed_sigmet(database, SIGMET_ACTIVE,
                                  created=datetime.datetime.utcnow() - datetime.timedelta(hours=1))

        spaced = ' '.join(SIGMET_ACTIVE.split()) + '  '
        changes = repos.message.save({'WS': [spaced]})

        assert len(changes) == 1
        assert changes[0].id == stored.id

    def test_save_ignores_stored_beyond_window(self, database):
        repos = Repositories(database)
        self.seed_sigmet(database, SIGMET_ACTIVE,
                         created=datetime.datetime.utcnow() - datetime.timedelta(hours=25))

        changes = repos.message.save({'WS': [SIGMET_ACTIVE]})

        assert len(changes) == 1
        assert changes[0].type == 'WS'

    def test_save_stores_a_report_repeated_in_one_payload_once(self, database):
        repos = Repositories(database)

        changes = repos.message.save({'WS': [SIGMET_ACTIVE, SIGMET_ACTIVE]})

        assert len(changes) == 1
        assert changes[0].type == 'WS'

        with database.session() as session:
            assert session.query(Sigmet).count() == 1

    def test_reconcile_does_not_write(self, database):
        # The decision and the write are split, so a reconcile that is never
        # followed by a save leaves the database untouched.
        repos = Repositories(database)

        with database.session() as session:
            result = repos.sigmet.reconcile(session, 'WS', [SIGMET_ACTIVE], utcnow())

        assert len(result) == 1
        assert result[0].id is None
        with database.session() as session:
            assert session.query(Sigmet).count() == 0

    def test_reconcile_reports_a_stored_unconfirmed_report(self, database):
        # A stored report comes back as itself, with an id, and still
        # unconfirmed: stamping it is save()'s job.
        repos = Repositories(database)
        stored = self.seed_sigmet(database, SIGMET_ACTIVE,
                                  created=datetime.datetime.utcnow() - datetime.timedelta(hours=1))

        with database.session() as session:
            result = repos.sigmet.reconcile(session, 'WS', [SIGMET_ACTIVE], utcnow())

        assert [sig.id for sig in result] == [stored.id]
        with database.session() as session:
            assert session.query(Sigmet).first().confirmed is None


class TestMessageRepository:

    def test_save_dispatches_by_key(self, database):
        repos = Repositories(database)

        # Message values are strings for metar/taf keys and lists of
        # messages for sigmet keys (the shape fetchMessage produces)
        changes = repos.message.save({
            'SA': METAR_TEXT,
            'FT': TAF_TEXT,
            'WS': [SIGMET_ACTIVE],
        })

        kinds = sorted(type(message).__name__ for message in changes)
        assert kinds == ['Metar', 'Sigmet', 'Taf']

    def test_save_filters_by_types(self, database):
        repos = Repositories(database)

        changes = repos.message.save({
            'SA': METAR_TEXT,
            'FT': TAF_TEXT,
        }, types=['FT'])

        assert [type(message).__name__ for message in changes] == ['Taf']

    def test_save_skips_unchanged_metar(self, database):
        repos = Repositories(database)
        with database.session() as session:
            add(session, Metar, type='SA', text=METAR_TEXT, created=datetime.datetime.utcnow())

        changes = repos.message.save({'SA': METAR_TEXT, 'FT': TAF_TEXT})

        assert [type(message).__name__ for message in changes] == ['Taf']

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
        metar = Metar(type='SA', text=METAR_TEXT)

        repos.message.add(metar)

        with database.session() as session:
            stored = session.query(Metar).first()
            assert stored is not None
            assert stored.text == METAR_TEXT

    def test_save_persists_new_messages_in_one_transaction(self, database):
        repos = Repositories(database)

        changes = repos.message.save({'SA': METAR_TEXT, 'FT': TAF_TEXT})

        assert len(changes) == 2
        with database.session() as session:
            assert session.query(Metar).count() == 1
            assert session.query(Taf).count() == 1

    def test_a_failure_rolls_back_the_whole_batch(self, database, monkeypatch):
        # The METAR is reconciled before the TAF blows up. One transaction for
        # the payload means the METAR must not survive the failure.
        repos = Repositories(database)

        def explode(*args, **kwargs):
            raise RuntimeError('boom')

        monkeypatch.setattr(repos.message.taf, 'reconcile', explode)

        with pytest.raises(RuntimeError):
            repos.message.save({'SA': METAR_TEXT, 'FT': TAF_TEXT})

        with database.session() as session:
            assert session.query(Metar).count() == 0

    def test_a_rolled_back_batch_logs_nothing(self, database, monkeypatch, caplog):
        # Logging inside the transaction would announce a message that the
        # rollback then discards.
        repos = Repositories(database)

        def explode(*args, **kwargs):
            raise RuntimeError('boom')

        monkeypatch.setattr(repos.message.taf, 'reconcile', explode)

        with caplog.at_level(logging.INFO, logger='tafor.repositories'):
            with pytest.raises(RuntimeError):
                repos.message.save({'SA': METAR_TEXT, 'FT': TAF_TEXT})

        assert caplog.text == ''

    def test_save_logs_each_outcome_it_writes(self, database, caplog):
        # The repository owns this line now, so a caller that only wants the
        # messages does not have to reconstruct the wording.
        repos = Repositories(database)
        created = datetime.datetime.utcnow() - datetime.timedelta(hours=1)
        with database.session() as session:
            add(session, Taf, type='FC', text=TAF_TEXT, created=created)

        with caplog.at_level(logging.INFO, logger='tafor.repositories'):
            repos.message.save({'FC': TAF_TEXT, 'SA': METAR_TEXT})

        assert 'Confirm FC {}'.format(TAF_TEXT) in caplog.text
        assert 'Save SA {}'.format(METAR_TEXT) in caplog.text

    def test_save_logs_nothing_when_the_feed_repeats_itself(self, database, caplog):
        repos = Repositories(database)
        with database.session() as session:
            add(session, Metar, type='SA', text=METAR_TEXT, created=datetime.datetime.utcnow())

        with caplog.at_level(logging.INFO, logger='tafor.repositories'):
            assert repos.message.save({'SA': METAR_TEXT}) == []

        assert caplog.text == ''


if __name__ == '__main__':
    pytest.main([__file__])
