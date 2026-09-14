"""Tests for tafor/ui/main.py.

Only DataService and RemindService are covered here: MainWindow and main()
start threads, audio, the tray icon and a single-instance server from their
constructors and cannot be instantiated in a test.
"""

import datetime
import types

from types import SimpleNamespace

import pytest

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QMessageBox

from tafor.core.models import Sigmet, Taf
from tafor.core.repositories import Repositories
from tafor.ui.main import DataService, RemindService
from tafor.ui.widgets.recent import RecentBoard


TAF_TEXT = 'TAF ZPPP 100800Z 1009/1018 32008G15MPS 9999 SCT020='
METAR_TEXT = 'METAR ZJHK 210900Z 14004MPS 4500 -RA BKN030='
SIGMET_ACTIVE = ('ZJSA SIGMET 2 VALID 100730/101430 ZJHK-\n'
                 'ZJSA SANYA FIR OBSC TS FCST WI E11223 N1829 - E11142 N1916 TOP FL030 MOV N 300KMH NC=')

MOMENT = datetime.datetime(2026, 6, 10, 8, 0)


class FakeSound:

    def __init__(self):
        self.calls = []

    def play(self, volume=None, loop=True):
        self.calls.append(('play', loop))

    def stop(self):
        self.calls.append(('stop',))


def stubView():
    closed = []
    return SimpleNamespace(
        tafBoard=SimpleNamespace(updateGui=lambda: None),
        notificationSound=FakeSound(),
        trendSound=FakeSound(),
        remindTafBox=SimpleNamespace(close=lambda: closed.append(1)),
    ), closed


@pytest.fixture
def board(qtbot):
    view_conf = types.SimpleNamespace(windowsStyle='System')
    board = RecentBoard(None, conf=view_conf, expiryMinutes=10)
    qtbot.addWidget(board)
    return board


@pytest.fixture
def service(conf, context, database, board):
    repositories = Repositories(database)
    view, closed = stubView()
    view.recentBoard = board
    view.tafTable = SimpleNamespace(updateGui=lambda: None)
    view.metarTable = SimpleNamespace(updateGui=lambda: None)
    view.sigmetTable = SimpleNamespace(updateGui=lambda: None)
    view.airmetTable = SimpleNamespace(updateGui=lambda: None)
    service = DataService(view, context, conf, repositories)
    service.closed = closed
    return service


class TestDataService:

    def test_update_taf_feeds_the_monitor(self, service, database, frozen_time):
        # context.taf.spec is ft24; at 08:00 the current period is 0606,
        # valid 1006/1106, and its issue window (03:00 + delay) has passed
        service.updateTaf()

        assert service.context.taf.period() == '1006/1106'
        assert service.context.taf.message is None
        assert service.context.taf.isExpired() is True
        assert service.context.taf.shouldRemind() is True

    def test_update_sigmet_feeds_current_sigmets(self, service, database, frozen_time):
        with database.session() as session:
            session.add(Sigmet(type='WS', text=SIGMET_ACTIVE, created=MOMENT))

        service.updateSigmet()

        assert [s.text for s in service.context.current.state.sigmets] == [SIGMET_ACTIVE]

    def test_update_message_saves_new_messages_with_a_sound(self, service, database, context):
        context.message.setState({'FT': TAF_TEXT})

        service.updateMessage()

        assert service.view.notificationSound.calls == [('play', False)]
        assert service.closed == [1]

        with database.session() as session:
            stored = session.query(Taf).filter(Taf.type == 'FT').first()
            assert stored is not None
            assert stored.text == TAF_TEXT

    def test_update_message_confirms_known_messages(self, service, database, context):
        created = datetime.datetime.utcnow() - datetime.timedelta(hours=1)
        with database.session() as session:
            session.add(Taf(type='FT', text=TAF_TEXT, created=created))
        context.message.setState({'FT': TAF_TEXT})

        service.updateMessage()

        with database.session() as session:
            stored = session.query(Taf).filter(Taf.type == 'FT').first()
            assert stored.confirmed is not None

    def test_update_message_clears_metar_notification_without_sound(self, service, database, context):
        context.notification.metar.setState({'message': METAR_TEXT, 'validation': True})
        context.message.setState({'SA': METAR_TEXT})

        service.updateMessage()

        assert service.view.notificationSound.calls == []
        assert context.notification.metar.message() is None

        with database.session() as session:
            from tafor.core.models import Metar
            assert session.query(Metar).filter(Metar.text == METAR_TEXT).first() is not None

    def test_sigmet_geometry_skips_cnl(self, service):
        cnl = Sigmet(type='WS', heading='ZJSA SIGMET 1 VALID 100930/101430 ZJHK-',
                     text='ZJSA SANYA FIR CNL SIGMET 2 100730/101430=')

        assert service.sigmetGeometry(cnl) is None


class TestRemindService:

    @pytest.fixture
    def remind_conf(self, conf):
        yield conf
        conf.remindTaf = True
        conf.remindSigmet = True

    @pytest.fixture
    def remind_view(self):
        reminders = []
        view = SimpleNamespace(
            remindTafBox=SimpleNamespace(),
            remindSigmetBox=SimpleNamespace(),
            tafSound=FakeSound(),
            sigmetSound=FakeSound(),
            isReminderVisible=lambda box: False,
            showReminder=lambda box, sound, text: reminders.append(text),
            recentBoard=SimpleNamespace(setReminderEnabled=lambda uuid, enabled: reminders.append((uuid, enabled))),
        )
        view.reminders = reminders
        return view

    @pytest.fixture
    def remind(self, remind_conf, context, remind_view):
        return RemindService(remind_view, context, remind_conf)

    def test_remind_taf_returns_when_the_switch_is_off(self, remind, remind_conf, remind_view):
        remind_conf.remindTaf = False

        assert remind.remindTaf() is None
        assert remind_view.reminders == []

    def test_remind_taf_returns_when_already_visible(self, remind, remind_view):
        remind.view.isReminderVisible = lambda box: True

        assert remind.remindTaf() is None
        assert remind_view.reminders == []

    def test_remind_taf_fires_when_due(self, remind, context, remind_view):
        context.taf.setState({'shouldRemind': True, 'message': None})

        remind.remindTaf()

        assert len(remind_view.reminders) == 1
        assert 'FT' in remind_view.reminders[0]

    def test_remind_taf_snoozes_on_reject(self, remind, context, remind_view, monkeypatch):
        context.taf.setState({'shouldRemind': True, 'message': None})
        remind.view.showReminder = lambda box, sound, text: QMessageBox.RejectRole
        scheduled = []
        monkeypatch.setattr(QTimer, 'singleShot',
                            lambda msec, callback: scheduled.append(msec))

        remind.remindTaf()

        assert scheduled == [RemindService.snoozeMinutes * 60 * 1000]

    def test_set_sigmet_reminder_adds_and_removes(self, remind, context, remind_view):
        sigmet = Sigmet(type='WS', heading='ZJSA SIGMET 2 VALID 100930/101430 ZJHK-',
                        text='ZJSA SANYA FIR OBSC TS=')

        remind.setSigmetReminder(sigmet, True)
        assert sigmet.uuid in context.sigmet.entries
        assert remind_view.reminders == [(sigmet.uuid, True)]

        remind.setSigmetReminder(sigmet, False)
        assert sigmet.uuid not in context.sigmet.entries
        assert remind_view.reminders == [(sigmet.uuid, True), (sigmet.uuid, False)]


if __name__ == '__main__':
    pytest.main([__file__])
