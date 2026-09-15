"""Tests for the main window and its presenters.

tafor/ui/main.py is a passive view plus one presenter per concern: the window
renders and answers questions, the presenters own the behaviour. The
presenters are handed a fake view that implements exactly the methods they
call, and the window is built for real -- headless -- with its children
swapped for recording doubles wherever a test is about the window's own
wiring rather than about a child widget.
"""
import os
import sys
import logging
import datetime

from types import SimpleNamespace

import pytest

from PyQt5.QtCore import QEvent, QObject, QUrl, pyqtSignal
from PyQt5.QtWidgets import QAction, QMessageBox, QSizePolicy, QSystemTrayIcon

from tafor import __version__
from tafor.core.config import createConfig
from tafor.core.models import Metar, Sigmet, Taf, createDatabase
from tafor.core.repositories import Repositories
from tafor.core.states import createContext
from tafor.ui import main as main_module
from tafor.ui.main import (
    BoardPresenter,
    LayerPresenter,
    LicensePresenter,
    MainWindow,
    MessagePresenter,
    NotificationPresenter,
    RecentEntryBuilder,
    ReminderPresenter,
    SoundPresenter,
    UpgradePresenter,
    restartArgs,
)
from tafor.ui.widgets.recent import (
    NotificationCard, NotificationModel, RecentBoard, ReviewCard, ReviewModel,
)
from tafor.ui.workers import CheckUpgradeWorker
from tests.mocks import MockConfig


TAF_TEXT = 'TAF ZPPP 100800Z 1009/1018 32008G15MPS 9999 SCT020='
METAR_TEXT = 'METAR ZJHK 210900Z 14004MPS 4500 -RA BKN030='
SIGMET_ACTIVE = ('ZJSA SIGMET 2 VALID 100730/101430 ZJHK-\n'
                 'ZJSA SANYA FIR OBSC TS FCST WI E11223 N1829 - E11142 N1916 TOP FL030 MOV N 300KMH NC=')

MOMENT = datetime.datetime(2026, 6, 10, 8, 0)


class FakeReminderView(QObject):
    """The methods ReminderPresenter calls."""

    reminderToggled = pyqtSignal(object, bool)
    messageSent = pyqtSignal()

    def __init__(self, answer=QMessageBox.AcceptRole):
        super().__init__()
        self.answer = answer
        self.visible = False
        self.prompts = []
        self.bells = []

    def reminderVisible(self, kind):
        return self.visible

    def showReminder(self, kind, text):
        self.prompts.append((kind, text))
        return self.answer

    def setSigmetReminder(self, uuid, enabled):
        self.bells.append((uuid, enabled))


class FakeBoardView(QObject):
    """The methods BoardPresenter calls."""

    notificationExpired = pyqtSignal()
    messageSent = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.boards = 0
        self.tables = 0
        self.graphics = 0
        self.entries = None
        self.bells = []

    def renderTafBoard(self):
        self.boards += 1

    def renderTables(self):
        self.tables += 1

    def renderRecent(self, entries):
        self.entries = entries

    def renderSigmetGraphic(self):
        self.graphics += 1

    def setSigmetReminder(self, uuid, enabled):
        self.bells.append((uuid, enabled))


class FakeMessageView(QObject):
    """The methods MessagePresenter calls."""

    def __init__(self):
        super().__init__()
        self.sounds = []
        self.closed = []
        self.notices = []
        self.custom = []

    def updateSound(self, name, playing):
        self.sounds.append((name, playing))

    def closeReminder(self, kind):
        self.closed.append(kind)

    def notify(self, title, text, level='information'):
        self.notices.append((title, text, level))

    def handleCustomMessage(self, message):
        self.custom.append(message)


class FakeLayerView(QObject):
    """The methods LayerPresenter calls."""

    def __init__(self):
        super().__init__()
        self.layers = 0
        self.notices = []

    def renderLayer(self):
        self.layers += 1

    def notify(self, title, text, level='information'):
        self.notices.append((title, text, level))


class FakeWorker(QObject):
    """Carries the signals the real workers emit, and nothing else."""

    fetched = pyqtSignal(object)
    finished = pyqtSignal()
    done = pyqtSignal(object)


class FakeThread(QObject):
    finished = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.running = False
        self.starts = 0

    def isRunning(self):
        return self.running

    def start(self):
        self.starts += 1
        self.running = True


class FakePool:
    """A WorkerPool handing back inert workers instead of real threads."""

    def __init__(self):
        self.created = []
        self.threads = []

    def create(self, workerClass, *args, workerId=None, reusable=False, **kwargs):
        worker, thread = FakeWorker(), FakeThread()
        self.created.append(workerClass)
        self.threads.append(thread)
        return worker, thread


class FakeBridge(QObject):
    """The ContextBridge, recording what the workers pushed through it."""

    def __init__(self):
        super().__init__()
        self.messages = []
        self.layers = []

    def updateMessage(self, data):
        self.messages.append(data)

    def updateLayer(self, data):
        self.layers.append(data)


def cardModel(uuid, type='FT', created=None, **kwargs):
    message = SimpleNamespace(uuid=uuid, confirmed=False, type=type)
    return ReviewModel(
        uuid=uuid,
        type=type,
        created=created or datetime.datetime.utcnow(),
        message=message,
        text=kwargs.pop('text', 'TAF YUSO 231200Z 2312/2412='),
        **kwargs)


def notificationModel(expired=False):
    delta = datetime.timedelta(minutes=20) if expired else datetime.timedelta(minutes=1)
    validations = {'html': '<p>METAR</p>', 'tips': [], 'pass': True, 'validation': False}
    return NotificationModel(
        created=datetime.datetime.utcnow() - delta,
        validations=validations)


def polygonGeo(lat=0.0, hazard='ts'):
    return {'features': [{'geometry': {'type': 'Polygon',
           'coordinates': [[0, lat], [2, lat], [2, 1 + lat], [0, 1 + lat], [0, lat]]},
           'properties': {'hazard': hazard, 'location': 'initial'}}]}


def titles(board):
    return [board.cardLayout.itemAt(i).widget().model.type
            for i in range(board.cardLayout.count())]


def addStoredMetar(repositories):
    metar = Metar(type='SA', text=METAR_TEXT)
    repositories.message.add(metar)
    return metar


def render(builder, board):
    """What BoardPresenter.render() does with the board, without the rest."""
    board.sync(builder.build())


@pytest.fixture
def repositories(database):
    return Repositories(database)


@pytest.fixture
def builder(conf, context, repositories):
    return RecentEntryBuilder(context, conf, repositories)


@pytest.fixture
def board(qtbot, conf):
    board = RecentBoard(None, conf=conf, expiryMinutes=10)
    qtbot.addWidget(board)
    return board


@pytest.fixture
def remind_conf(conf):
    yield conf
    conf.remindTaf = True
    conf.remindSigmet = True


class TestBoardPresenter:

    @pytest.fixture
    def view(self, qtbot):
        return FakeBoardView()

    @pytest.fixture
    def board(self, view, conf, context, repositories):
        return BoardPresenter(view, context, conf, repositories)

    def test_refresh_taf_feeds_the_monitor(self, board, context, frozen_time):
        # context.taf.spec is ft24; at 08:00 the current period is 0606,
        # valid 1006/1106, and its issue window (03:00 + delay) has passed
        board.refreshTaf()

        assert context.taf.period() == '1006/1106'
        assert context.taf.message is None
        assert context.taf.isExpired() is True
        assert context.taf.shouldRemind() is True

    def test_refresh_sigmet_feeds_current_sigmets(self, board, context, database, frozen_time):
        with database.session() as session:
            session.add(Sigmet(type='WS', text=SIGMET_ACTIVE, created=MOMENT))

        board.refreshSigmet()

        assert [s.text for s in context.current.state.sigmets] == [SIGMET_ACTIVE]

    def test_refresh_pushes_state_then_draws(self, board, view, context, database, frozen_time):
        with database.session() as session:
            session.add(Sigmet(type='WS', text=SIGMET_ACTIVE, created=MOMENT))

        board.refresh()

        assert [s.text for s in context.current.state.sigmets] == [SIGMET_ACTIVE]
        assert view.boards == 1
        assert view.tables == 1
        assert [entry.type for entry in view.entries] == ['WS']

    def test_a_failed_sigmet_read_does_not_stop_the_render(self, board, view, monkeypatch):
        def explode():
            raise RuntimeError('database is gone')

        monkeypatch.setattr(board.repositories.sigmet, 'current', explode)

        board.refresh()

        assert view.boards == 1

    def test_initialize_renders_once(self, board, view):
        board.initialize()

        assert view.boards == 1
        assert view.tables == 1

    def test_initialize_does_not_raise_the_taf_reminder(self, board, context):
        """Reading the TAF status flips shouldRemind, which fires
        tafReminderTriggered and opens the reminder dialog -- with the alarm
        looping -- before the window has settled. The startup refresh must
        leave the TAF monitor state alone, as the original did."""
        fired = []
        context.event.tafReminderTriggered.connect(lambda: fired.append(True))

        board.initialize()

        assert fired == []
        assert context.taf.shouldRemind() is False

    def test_a_later_refresh_does_raise_the_taf_reminder(self, board, context):
        fired = []
        context.event.tafReminderTriggered.connect(lambda: fired.append(True))
        board.initialize()

        board.refresh()

        assert fired == [True]

    def test_remote_message_changed_refreshes(self, board, view, context):
        board.initialize()
        view.boards = 0

        context.event.remoteMessageChanged.emit()

        assert view.boards == 1

    def test_a_sent_message_refreshes(self, board, view):
        board.initialize()
        view.boards = 0

        view.messageSent.emit()

        assert view.boards == 1

    def test_changed_sigmets_redraw_the_graphic(self, board, view, context, database, frozen_time):
        board.initialize()

        with database.session() as session:
            session.add(Sigmet(type='WS', text=SIGMET_ACTIVE, created=MOMENT))
        board.refreshSigmet()

        assert view.graphics == 1

    def test_an_unchanged_sigmet_set_does_not_redraw(self, board, view):
        board.initialize()

        # Nothing was added, so setState sees no change and stays quiet
        board.refreshSigmet()

        assert view.graphics == 0

    def test_expired_notification_falls_back_to_the_stored_metar(self, board, view, context):
        context.notification.metar.setState({'message': METAR_TEXT, 'validation': True})
        board.initialize()

        view.notificationExpired.emit()

        assert context.notification.metar.message() is None

    def test_sigmet_cards_get_their_bell_state(self, board, view, context, database, frozen_time):
        with database.session() as session:
            session.add(Sigmet(type='WS', text=SIGMET_ACTIVE, created=MOMENT))

        board.refresh()

        assert len(view.bells) == 1
        assert view.bells[0][1] is False


class TestRecentEntryBuilder:
    """build() turns the stored messages into view models, keeping the metar
    card mutually exclusive with the live notification."""

    def test_sigmet_geometry_skips_cnl(self, builder):
        cnl = Sigmet(type='WS', heading='ZJSA SIGMET 1 VALID 100930/101430 ZJHK-',
                     text='ZJSA SANYA FIR CNL SIGMET 2 100730/101430=')

        assert builder.sigmetGeometry(cnl) is None

    def test_a_failed_area_render_is_swallowed(self, builder, caplog):
        def explode():
            raise RuntimeError('bad geometry')

        message = SimpleNamespace(
            category='SIGMET', isCnl=lambda: False, text=SIGMET_ACTIVE, parser=explode)

        with caplog.at_level(logging.ERROR, logger='tafor.main'):
            assert builder.sigmetGeometry(message) is None

        assert 'Failed to draw SIGMET area' in caplog.text

    def test_build_is_empty_without_messages(self, builder):
        assert builder.build() == []

    def test_stored_metar_shows_without_notification(self, builder, board, repositories):
        metar = addStoredMetar(repositories)

        render(builder, board)

        assert titles(board) == ['SA']
        card = board.cards[metar.uuid]
        assert isinstance(card, ReviewCard)
        assert card.text.text() == METAR_TEXT

    def test_notification_replaces_stored_metar(self, builder, board, repositories, context):
        metar = addStoredMetar(repositories)
        context.notification.metar.setState({'message': METAR_TEXT, 'validation': True})

        render(builder, board)

        assert titles(board) == [None]
        assert isinstance(board.cards[None], NotificationCard)
        assert metar.uuid not in board.cards

    def test_stored_metar_returns_after_notification_clears(self, builder, board, repositories, context):
        metar = addStoredMetar(repositories)
        context.notification.metar.setState({'message': METAR_TEXT, 'validation': True})
        render(builder, board)
        assert titles(board) == [None]

        context.notification.metar.clear()
        render(builder, board)

        assert titles(board) == ['SA']
        assert board.cards[metar.uuid].text.text() == METAR_TEXT


class TestRecentBoard:
    """The board the presenters render into."""

    def test_sync_creates_cards_in_order(self, board):
        board.sync([cardModel('a', 'FT'), cardModel('b', 'TREND'), cardModel('c', 'WS')])

        assert titles(board) == ['FT', 'TREND', 'WS']

    def test_sync_removes_stale_cards(self, board):
        board.sync([cardModel('a', 'FT'), cardModel('b', 'TREND'), cardModel('c', 'WS')])
        board.sync([cardModel('a', 'FT'), cardModel('c', 'WS')])

        assert titles(board) == ['FT', 'WS']

    def test_sync_reorders_existing_cards(self, board):
        board.sync([cardModel('a', 'FT'), cardModel('b', 'TREND')])
        board.sync([cardModel('b', 'TREND'), cardModel('a', 'FT')])

        assert titles(board) == ['TREND', 'FT']

    def test_sync_refreshes_incrementally(self, board):
        board.sync([cardModel('a', text='OLD')])
        board.sync([cardModel('a', text='NEW')])

        card = board.cards['a']
        assert card.model.text == 'NEW'
        assert card.text.text() == 'NEW'

    def test_review_card_renders_report(self, board):
        board.sync([cardModel('a', 'FT', text='TAF YUSO 231200Z 2312/2412=')])

        card = board.cards['a']
        assert card.group.title() == 'FT'
        assert card.text.text() == 'TAF YUSO 231200Z 2312/2412='
        assert card.timeLabel.text() == card.model.created.strftime('%Y-%m-%d %H:%M:%S')

    def test_metar_review_card_hides_action_buttons(self, board):
        board.sync([cardModel('m', 'SA', text=METAR_TEXT)])

        card = board.cards['m']
        assert card.group.title() == 'SA'
        assert card.text.text() == METAR_TEXT
        assert card.markButton.isHidden()
        assert card.replyButton.isHidden()
        assert card.reminderButton.isHidden()
        assert card.signLabel.isHidden()

    def test_notification_card_renders_html(self, board):
        board.sync([notificationModel()])

        card = board.cards[None]
        assert isinstance(card, NotificationCard)
        assert card.text.text() == '<p>METAR</p>'
        assert card.timeLabel.text()  # relative timestamp

    def test_notification_refreshes_in_place(self, board):
        board.sync([notificationModel(expired=False)])
        board.sync([notificationModel(expired=True)])

        assert board.cardLayout.count() == 1
        card = board.cards[None]
        assert card.expired is False

    def test_set_reminder_enabled(self, board):
        board.sync([cardModel('s', 'WS')])

        board.setReminderEnabled('s', True)

        assert board.cards['s'].remind is True

    def test_expired_notification_emits_once(self, board):
        expired = []
        board.expired.connect(expired.append)
        board.sync([notificationModel(expired=True)])

        board.tick()
        assert expired == [None]

        board.tick()
        assert expired == [None]  # no repeated emission

    def test_fresh_notification_does_not_expire(self, board):
        expired = []
        board.expired.connect(expired.append)
        board.sync([notificationModel(expired=False)])

        board.tick()

        assert expired == []

    def test_expired_state_resets_on_model_refresh(self, board):
        board.sync([notificationModel(expired=True)])
        board.tick()

        board.sync([notificationModel(expired=False)])
        board.tick()

        card = board.cards[None]
        assert card.expired is False

    def test_sigmet_card_embeds_map(self, board):
        board.sync([cardModel('s', 'WS', geo=polygonGeo())])

        card = board.cards['s']
        assert card.map is not None
        assert card.map.parent() is card.group
        assert card.map.width() == 200
        assert card.group.title() == 'WS'

    def test_sigmet_map_overlays_full_height(self, board, qtbot):
        board.sync([cardModel('s', 'WS', geo=polygonGeo())])
        board.resize(800, board.heightForWidth(800))
        board.show()
        qtbot.waitExposed(board)

        card = board.cards['s']
        inner = card.group.contentsRect()
        assert card.map.height() == inner.height() > 50
        assert card.map.y() == inner.y()
        assert card.map.x() + card.map.width() == inner.x() + inner.width()

    def test_sigmet_map_sits_below_tools_buttons(self, board):
        board.sync([cardModel('s', 'WS', geo=polygonGeo())])

        card = board.cards['s']
        children = card.group.children()
        assert children.index(card.toolsWidget) > children.index(card.map)

    def test_sigmet_card_replaces_map_on_geo_change(self, board):
        board.sync([cardModel('s', 'WS', geo=polygonGeo())])
        card = board.cards['s']
        original = card.map

        board.sync([cardModel('s', 'WS', geo=polygonGeo(lat=1.0))])

        assert card.map is not original
        assert card.map.parent() is card.group

    def test_sigmet_card_removes_map_when_geo_cleared(self, board):
        board.sync([cardModel('s', 'WS', geo=polygonGeo())])
        card = board.cards['s']
        assert card.map is not None

        board.sync([cardModel('s', 'WS', geo=None)])

        assert card.map is None

    def test_card_without_geo_has_no_map(self, board):
        board.sync([cardModel('a', 'FT')])

        assert board.cards['a'].map is None

    def test_card_grows_with_long_text(self, board):
        board.sync([
            cardModel('short', text='TAF YUSO 231200Z 2312/2412='),
            cardModel('long', text='TAF YUSO ' + ' '.join(['11111'] * 120) + '='),
        ])

        short = board.cards['short']
        long = board.cards['long']
        assert short.sizePolicy().verticalPolicy() == QSizePolicy.Minimum
        assert long.heightForWidth(800) > short.heightForWidth(800)


class TestMessagePresenter:

    @pytest.fixture
    def view(self, qtbot):
        return FakeMessageView()

    @pytest.fixture
    def bridge(self, qtbot):
        return FakeBridge()

    @pytest.fixture
    def message(self, view, conf, context, repositories, bridge):
        presenter = MessagePresenter(view, context, conf, repositories, FakePool(), bridge)
        yield presenter
        # initialize() arms a one-minute poll; leave no timer running
        if hasattr(presenter, 'timer'):
            presenter.timer.stop()

    def test_store_saves_new_messages_with_a_sound(self, message, view, database, context):
        context.message.setState({'FT': TAF_TEXT})

        message.store()

        assert view.sounds == [('notification', True)]
        assert view.closed == ['taf']

        with database.session() as session:
            stored = session.query(Taf).filter(Taf.type == 'FT').first()
            assert stored is not None
            assert stored.text == TAF_TEXT

    def test_store_confirms_known_messages(self, message, database, context):
        created = datetime.datetime.utcnow() - datetime.timedelta(hours=1)
        with database.session() as session:
            session.add(Taf(type='FT', text=TAF_TEXT, created=created))
        context.message.setState({'FT': TAF_TEXT})

        message.store()

        with database.session() as session:
            stored = session.query(Taf).filter(Taf.type == 'FT').first()
            assert stored.confirmed is not None

    def test_store_clears_metar_notification_without_sound(self, message, view, database, context):
        context.notification.metar.setState({'message': METAR_TEXT, 'validation': True})
        context.message.setState({'SA': METAR_TEXT})

        message.store()

        assert view.sounds == []
        assert context.notification.metar.message() is None

        with database.session() as session:
            assert session.query(Metar).filter(Metar.text == METAR_TEXT).first() is not None

    def test_initialize_subscribes_to_the_remote_feed(self, message, view, context):
        message.initialize()

        context.message.setState({'FT': TAF_TEXT})

        assert view.sounds == [('notification', True)]

    def test_initialize_starts_the_fetch(self, message):
        message.initialize()

        assert message.thread.isRunning() is True

    def test_an_api_message_reaches_the_custom_sender(self, message, view, context):
        message.initialize()
        payload = SimpleNamespace(text=TAF_TEXT)

        context.event.otherMessageReceived.emit(payload)

        assert view.custom == [payload]

    def test_a_failed_fetch_reports_a_connection_error(self, message, view, context):
        message.initialize()
        view.notices = []

        message.connectionLost()

        assert view.notices[0][2] == 'warning'
        assert 'Connection Error' in view.notices[0][0]

    def test_a_successful_fetch_reports_nothing(self, message, view, context):
        context.message.setState({'FT': TAF_TEXT})
        message.initialize()
        view.notices = []

        message.connectionLost()

        assert view.notices == []


class TestLayerPresenter:

    @pytest.fixture
    def view(self, qtbot):
        return FakeLayerView()

    @pytest.fixture
    def pool(self):
        return FakePool()

    @pytest.fixture
    def bridge(self, qtbot):
        return FakeBridge()

    @pytest.fixture
    def layer_conf(self, conf):
        yield conf
        conf.layerUrl = MockConfig.defaults['Interface/LayerURL']

    @pytest.fixture
    def layer(self, view, conf, context, pool, bridge):
        presenter = LayerPresenter(view, context, conf, pool, bridge)
        yield presenter
        if hasattr(presenter, 'timer'):
            presenter.timer.stop()

    def test_initialize_fetches_straight_away(self, layer):
        layer.initialize()

        assert layer.thread.isRunning() is True

    def test_initialize_arms_the_refresh_timer(self, layer):
        layer.initialize()

        assert layer.timer.isActive() is True
        assert layer.timer.interval() == 2 * 60 * 1000

    def test_a_layer_request_fetches_again(self, layer, context):
        layer.initialize()
        layer.thread.running = False

        context.event.layerRefreshRequested.emit()

        assert layer.thread.isRunning() is True

    def test_refresh_hands_the_layers_to_the_editor(self, layer, view):
        layer.initialize()

        layer.refresh()

        assert view.layers == 1

    def test_a_fetch_that_returns_nothing_reports_a_connection_error(self, layer, view, context):
        layer.initialize()
        view.notices = []

        layer.refresh()

        assert view.notices[0][2] == 'warning'

    def test_refresh_without_a_layer_url_only_renders(self, layer, view, layer_conf):
        layer_conf.layerUrl = ''
        layer.initialize()
        view.notices = []

        layer.refresh()

        assert view.layers == 1
        assert view.notices == []

    def test_refresh_with_layers_already_present_reports_nothing(self, layer, view, context, monkeypatch):
        monkeypatch.setattr(context.layer, 'currentLayers', lambda: [object()])
        layer.initialize()
        view.notices = []

        layer.refresh()

        assert view.layers == 1
        assert view.notices == []


class TestReminderPresenter:

    @pytest.fixture
    def view(self, qtbot):
        return FakeReminderView()

    @pytest.fixture
    def remind(self, remind_conf, context, view):
        presenter = ReminderPresenter(view, context, remind_conf)
        yield presenter
        presenter.snooze.stop()
        if hasattr(presenter, 'timer'):
            presenter.timer.stop()

    def test_remind_taf_returns_when_the_switch_is_off(self, remind, remind_conf, view):
        remind_conf.remindTaf = False

        assert remind.remindTaf() is None
        assert view.prompts == []

    def test_remind_taf_returns_when_already_visible(self, remind, view):
        view.visible = True

        assert remind.remindTaf() is None
        assert view.prompts == []

    def test_remind_taf_fires_when_due(self, remind, context, view):
        context.taf.setState({'shouldRemind': True, 'message': None})

        remind.remindTaf()

        assert len(view.prompts) == 1
        assert view.prompts[0][0] == 'taf'
        assert 'FT' in view.prompts[0][1]

    def test_remind_taf_snoozes_on_reject(self, remind, remind_conf, context, view):
        context.taf.setState({'shouldRemind': True, 'message': None})
        view.answer = QMessageBox.RejectRole

        remind.remindTaf()

        assert remind.snooze.isActive() is True
        assert remind.snooze.interval() == remind_conf.remindSnoozeMinutes * 60 * 1000

    def test_remind_taf_does_not_snooze_on_accept(self, remind, context, view):
        context.taf.setState({'shouldRemind': True, 'message': None})

        remind.remindTaf()

        assert remind.snooze.isActive() is False

    def test_set_reminder_adds_and_removes(self, remind, context, view):
        sigmet = Sigmet(type='WS', heading='ZJSA SIGMET 2 VALID 100930/101430 ZJHK-',
                        text='ZJSA SANYA FIR OBSC TS=')

        remind.setReminder(sigmet, True)
        assert sigmet.uuid in context.sigmet.entries
        assert view.bells == [(sigmet.uuid, True)]

        remind.setReminder(sigmet, False)
        assert sigmet.uuid not in context.sigmet.entries
        assert view.bells == [(sigmet.uuid, True), (sigmet.uuid, False)]

    def test_initialize_routes_a_card_bell_to_set_reminder(self, remind, context, view):
        sigmet = Sigmet(type='WS', heading='ZJSA SIGMET 2 VALID 100930/101430 ZJHK-',
                        text='ZJSA SANYA FIR OBSC TS=')
        remind.initialize()

        view.reminderToggled.emit(sigmet, True)

        assert sigmet.uuid in context.sigmet.entries

    def test_initialize_routes_a_sent_message_to_the_sigmet_check(self, remind, context, view):
        due = Sigmet(type='WS', heading='ZJSA SIGMET 2 VALID 100930/101430 ZJHK-',
                     text='ZJSA SANYA FIR OBSC TS=')
        context.sigmet.add(due.uuid, due.parser(), MOMENT)
        remind.initialize()

        view.messageSent.emit()

        assert view.prompts[0][0] == 'sigmet'
        # Dismissing the alarm drops the entry and clears the card's bell
        assert due.uuid not in context.sigmet.entries
        assert view.bells == [(due.uuid, False)]

    def test_remind_sigmet_snoozes_on_reject(self, remind, context, view):
        due = Sigmet(type='WS', heading='ZJSA SIGMET 2 VALID 100930/101430 ZJHK-',
                     text='ZJSA SANYA FIR OBSC TS=')
        context.sigmet.add(due.uuid, due.parser(), MOMENT)
        view.answer = QMessageBox.RejectRole

        remind.remindSigmet()

        assert context.sigmet.entries[due.uuid]['time'] == MOMENT + datetime.timedelta(minutes=5)
        assert view.bells == []

    def test_remind_sigmet_returns_when_the_switch_is_off(self, remind, remind_conf, context, view):
        due = Sigmet(type='WS', heading='ZJSA SIGMET 2 VALID 100930/101430 ZJHK-',
                     text='ZJSA SANYA FIR OBSC TS=')
        context.sigmet.add(due.uuid, due.parser(), MOMENT)
        remind_conf.remindSigmet = False

        remind.remindSigmet()

        assert view.prompts == []

    def test_initialize_arms_the_sigmet_timer(self, remind):
        remind.initialize()

        assert remind.timer.isActive() is True
        assert remind.timer.interval() == 60 * 1000

    def test_initialize_subscribes_to_the_taf_trigger(self, remind, context, view):
        context.taf.setState({'shouldRemind': True, 'message': None})
        remind.initialize()

        context.event.tafReminderTriggered.emit()

        assert len(view.prompts) == 1

    def test_remind_taf_returns_when_nothing_is_due(self, remind, context, view):
        assert context.taf.shouldRemind() is False

        remind.remindTaf()

        assert view.prompts == []


class TestRestartArgs:
    """The argv this process was started with, replayed to its replacement."""

    def test_nothing_recorded(self, monkeypatch):
        monkeypatch.delenv('TAFOR_ARGS', raising=False)

        assert restartArgs() == []

    def test_the_recorded_arguments_are_replayed(self, monkeypatch):
        monkeypatch.setenv('TAFOR_ARGS', '["--debug", "--port", "1"]')

        assert restartArgs() == ['--debug', '--port', '1']

    def test_malformed_arguments_are_ignored(self, monkeypatch, caplog):
        monkeypatch.setenv('TAFOR_ARGS', 'not json')

        with caplog.at_level(logging.WARNING, logger='tafor.main'):
            assert restartArgs() == []

        assert 'Ignoring malformed TAFOR_ARGS' in caplog.text


class FakeNotificationView(QObject):
    """The methods NotificationPresenter calls."""

    def __init__(self):
        super().__init__()
        self.sigmetTexts = 0
        self.sounds = []
        self.notices = []

    def renderSigmetText(self):
        self.sigmetTexts += 1

    def updateSound(self, name, playing):
        self.sounds.append((name, playing))

    def notify(self, title, text, level='information'):
        self.notices.append((title, text, level))


class StubMetarParser:
    """A metar parser with the three answers reloadMetar asks for, handed in."""

    def __init__(self, same=False, hasTrend=False, valid=True):
        self.same = same
        self.trend = hasTrend
        self.valid = valid
        self.validated = 0

    def isSameObservation(self, text):
        return self.same

    def validate(self):
        self.validated += 1

    def hasTrend(self):
        return self.trend

    def isValid(self):
        return self.valid


class TestNotificationPresenter:
    """The live notification channel: a message that just arrived and has not
    been stored yet."""

    @pytest.fixture
    def view(self, qtbot):
        return FakeNotificationView()

    @pytest.fixture
    def notification(self, view, context, repositories):
        return NotificationPresenter(view, context, repositories)

    def test_a_metar_notification_reloads_the_trend(self, notification, context):
        reloads = []
        context.event.trendReloadRequested.connect(lambda: reloads.append(True))
        notification.initialize()

        context.notification.metar.setState({'message': METAR_TEXT, 'validation': True})

        assert reloads == [True]

    def test_a_speci_notification_is_handled_like_a_metar(self, notification, context):
        """category() also answers SPECI; matching only METAR left it with no
        handler at all."""
        reloads = []
        context.event.trendReloadRequested.connect(lambda: reloads.append(True))
        notification.initialize()

        context.notification.metar.setState(
            {'message': 'SPECI ZJHK 210900Z 14004MPS 4500 -RA BKN030=', 'validation': True})

        assert reloads == [True]

    def test_a_custom_notification_is_ignored(self, notification, view, context):
        reloads = []
        context.event.trendReloadRequested.connect(lambda: reloads.append(True))
        notification.initialize()

        context.notification.metar.setState({'message': 'NOT A WEATHER REPORT', 'validation': True})

        assert reloads == []
        assert view.sigmetTexts == 0

    def test_a_sigmet_notification_refreshes_the_editor_and_alerts(self, notification, view, context):
        notification.initialize()

        context.notification.sigmet.setState({'message': SIGMET_ACTIVE})

        assert view.sigmetTexts == 1
        assert view.sounds == [('incoming', True)]
        assert view.notices[0][1] == 'Received a SIGMET message'

    def test_an_airmet_notification_is_handled_too(self, notification, view, context):
        airmet = ('ZJSA AIRMET 1 VALID 100730/101430 ZJHK-\n'
                  'ZJSA SANYA FIR MOD TURB FCST WI E11223 N1829 - E11142 N1916=')
        notification.initialize()

        context.notification.sigmet.setState({'message': airmet})

        assert view.sigmetTexts == 1
        assert view.notices[0][1] == 'Received a AIRMET message'

    def test_a_stored_observation_clears_the_notification(self, notification, context, repositories):
        repositories.message.add(Metar(type='SA', text=METAR_TEXT))
        notification.initialize()

        context.notification.metar.setState({'message': METAR_TEXT, 'validation': True})

        assert context.notification.metar.message() is None

    def test_a_stored_observation_does_not_reload_the_trend(self, notification, context, repositories):
        repositories.message.add(Metar(type='SA', text=METAR_TEXT))
        reloads = []
        context.event.trendReloadRequested.connect(lambda: reloads.append(True))
        notification.initialize()

        context.notification.metar.setState({'message': METAR_TEXT, 'validation': True})

        assert reloads == []

    def test_a_failed_trend_validation_warns(self, notification, context, monkeypatch):
        parser = StubMetarParser(hasTrend=True, valid=False)
        monkeypatch.setattr(context.notification.metar, 'parser', lambda: parser)
        messages = []
        context.event.systemMessage.connect(
            lambda title, text, level='information': messages.append((title, text, level)))
        notification.initialize()

        context.notification.metar.setState({'message': METAR_TEXT, 'validation': True})

        assert parser.validated == 1
        assert messages == [
            ('Trend Validation Failed', 'The trend has been cleared, please resend', 'warning')]

    def test_a_valid_trend_does_not_warn(self, notification, context, monkeypatch):
        parser = StubMetarParser(hasTrend=True, valid=True)
        monkeypatch.setattr(context.notification.metar, 'parser', lambda: parser)
        messages = []
        reloads = []
        context.event.systemMessage.connect(
            lambda title, text, level='information': messages.append((title, text, level)))
        context.event.trendReloadRequested.connect(lambda: reloads.append(True))
        notification.initialize()

        context.notification.metar.setState({'message': METAR_TEXT, 'validation': True})

        assert parser.validated == 1
        assert messages == []
        assert reloads == [True]

    def test_a_sigmet_notification_without_a_message_only_refreshes(self, notification, view):
        notification.notifySigmet()

        assert view.sigmetTexts == 1
        assert view.sounds == []
        assert view.notices == []


class FakeSoundView(QObject):
    """The methods SoundPresenter calls."""

    def __init__(self, alarm=False):
        super().__init__()
        self.alarm = alarm
        self.sounds = []

    def alarmEnabled(self):
        return self.alarm

    def updateSound(self, name, playing):
        self.sounds.append((name, playing))


class TestSoundPresenter:
    """The only writer of the two continuous channels."""

    @pytest.fixture
    def view(self, qtbot):
        return FakeSoundView()

    @pytest.fixture
    def sound_conf(self, conf):
        yield conf
        conf.remindTrend = True

    @pytest.fixture
    def sound(self, view, sound_conf, context):
        presenter = SoundPresenter(view, context, sound_conf)
        yield presenter
        if hasattr(presenter, 'timer'):
            presenter.timer.stop()

    def test_initialize_ticks_every_second(self, sound):
        sound.initialize()

        assert sound.timer.isActive() is True
        assert sound.timer.interval() == 1000

    def test_the_trend_channel_follows_the_switch(self, sound, sound_conf):
        sound_conf.remindTrend = False

        assert sound.isTrendActive() is False

    def test_a_live_metar_keeps_the_trend_channel_on(self, sound, context):
        context.notification.metar.setState({'message': METAR_TEXT, 'validation': True})

        assert sound.isTrendActive() is True

    def test_the_trend_channel_opens_near_the_hour(self, sound, time_machine):
        time_machine.move_to(datetime.datetime(2026, 6, 10, 8, 57), tick=False)

        assert sound.isTrendActive() is True

    def test_the_trend_channel_is_quiet_earlier(self, sound, time_machine):
        time_machine.move_to(datetime.datetime(2026, 6, 10, 8, 56), tick=False)

        assert sound.isTrendActive() is False

    def test_the_alarm_channel_needs_the_switch(self, sound, view, context):
        view.alarm = False
        context.taf.setState({'isExpired': True})

        assert sound.isAlarmActive() is False

    def test_the_alarm_channel_needs_an_expired_taf(self, sound, view, context):
        view.alarm = True
        context.taf.setState({'isExpired': False})

        assert sound.isAlarmActive() is False

    def test_the_alarm_channel_sounds_when_both_hold(self, sound, view, context):
        view.alarm = True
        context.taf.setState({'isExpired': True})

        assert sound.isAlarmActive() is True

    def test_a_tick_pushes_both_channels(self, sound, view, context):
        view.alarm = True
        context.taf.setState({'isExpired': True})
        context.notification.metar.setState({'message': METAR_TEXT, 'validation': True})

        sound.tick()

        assert view.sounds == [('trend', True), ('alarm', True)]


class FakeLicenseView(QObject):
    """The methods LicensePresenter calls."""

    licenseChanged = pyqtSignal()

    def __init__(self, confirm=True):
        super().__init__()
        self.removeLicenseAction = QAction()
        self.answer = confirm
        self.menuStates = []
        self.prompts = []
        self.removed = 0

    def setLicenseMenuState(self, registered):
        self.menuStates.append(registered)

    def confirm(self, title, text):
        self.prompts.append((title, text))
        return self.answer

    def removeLicense(self):
        self.removed += 1


class TestLicensePresenter:
    """Only removal and the menu state live here; entering a key is a plain
    window action."""

    @pytest.fixture
    def view(self, qtbot):
        return FakeLicenseView()

    @pytest.fixture
    def license(self, view, context):
        return LicensePresenter(view, context)

    def test_initialize_syncs_the_menu(self, license, view):
        license.initialize()

        assert view.menuStates == [False]

    def test_a_registered_copy_shows_the_remove_entry(self, license, view, context, monkeypatch):
        monkeypatch.setattr(context.license, 'license', lambda: {'register': 'YUSO'})

        license.initialize()

        assert view.menuStates == [True]

    def test_a_license_change_resyncs_the_menu(self, license, view):
        license.initialize()
        view.menuStates.clear()

        view.licenseChanged.emit()

        assert view.menuStates == [False]

    def test_removal_asks_first(self, license, view):
        view.answer = False
        license.initialize()

        view.removeLicenseAction.trigger()

        assert view.prompts[0][0] == 'Remove license key? '
        assert view.removed == 0

    def test_a_confirmed_removal_removes_the_license(self, license, view):
        view.answer = True
        license.initialize()

        view.removeLicenseAction.trigger()

        assert view.removed == 1


class FakeUpgradeView(QObject):
    """The methods UpgradePresenter calls."""

    def __init__(self, confirm=False):
        super().__init__()
        self.checkUpgradeAction = QAction()
        self.answer = confirm
        self.notices = []
        self.prompts = []

    def notify(self, title, text, level='information'):
        self.notices.append((title, text, level))

    def confirm(self, title, text):
        self.prompts.append((title, text))
        return self.answer


class TestUpgradePresenter:

    @pytest.fixture
    def view(self, qtbot):
        return FakeUpgradeView()

    @pytest.fixture
    def pool(self):
        return FakePool()

    @pytest.fixture
    def upgrade(self, view, pool):
        return UpgradePresenter(view, pool)

    def test_initialize_creates_the_worker(self, upgrade, pool):
        upgrade.initialize()

        assert pool.created == [CheckUpgradeWorker]

    def test_initialize_arms_the_menu_action(self, upgrade, view):
        upgrade.initialize()

        view.checkUpgradeAction.trigger()

        assert upgrade.thread.isRunning() is True

    def test_a_running_check_is_not_started_twice(self, upgrade):
        upgrade.initialize()
        upgrade.thread.running = True

        upgrade.check()

        assert upgrade.thread.starts == 0

    def test_a_release_without_a_tag_is_reported(self, upgrade, view):
        upgrade.report({})

        assert view.notices == [
            ('Check for Updates', 'Unable to get the latest version information.', 'information')]

    def test_the_current_version_is_reported_as_latest(self, upgrade, view):
        upgrade.report({'tag_name': __version__})

        assert view.notices == [
            ('Check for Updates', 'The current version is already the latest version.', 'information')]

    def test_a_newer_release_is_offered(self, upgrade, view, monkeypatch):
        opened = []
        monkeypatch.setattr(main_module, 'QDesktopServices', SimpleNamespace(openUrl=opened.append))
        view.answer = True

        upgrade.report({'tag_name': 'v3.1'})

        assert view.prompts == [
            ('Check for Updates', 'New version found v3.1, do you want to download now?')]
        assert opened == [QUrl('https://github.com/up1and/tafor/releases')]

    def test_a_declined_download_opens_nothing(self, upgrade, view, monkeypatch):
        opened = []
        monkeypatch.setattr(main_module, 'QDesktopServices', SimpleNamespace(openUrl=opened.append))
        view.answer = False

        upgrade.report({'tag_name': 'v3.1'})

        assert opened == []


class FakeWidget:
    """A child widget reduced to a recorder: every call is captured."""

    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        def record(*args, **kwargs):
            self.calls.append((name, args, kwargs))
        return record


class FakeSound:
    """A channel double. Which channels loop is the channel's own business
    now, so the window only ever says play or stop."""

    def __init__(self):
        self.plays = 0
        self.stops = 0

    def play(self):
        self.plays += 1

    def stop(self):
        self.stops += 1


class FakeTray:

    def __init__(self):
        self.messages = []
        self.hidden = 0
        self.shown = 0
        self.icon = None

    def showMessage(self, title, text, icon):
        self.messages.append((title, text, icon))

    def setIcon(self, icon):
        self.icon = icon

    def hide(self):
        self.hidden += 1

    def show(self):
        self.shown += 1


class FakeCloseEvent:

    def __init__(self, spontaneous):
        self._spontaneous = spontaneous
        self.ignored = 0
        self.accepted = 0

    def spontaneous(self):
        return self._spontaneous

    def ignore(self):
        self.ignored += 1

    def accept(self):
        self.accepted += 1


class FakeReminderBox:
    """A reminder dialog that answers without ever opening."""

    def __init__(self, answer=QMessageBox.AcceptRole, visible=False):
        self.answer = answer
        self.visible = visible
        self.text = None
        self.closed = 0

    def setText(self, text):
        self.text = text

    def exec(self):
        return self.answer

    def isVisible(self):
        return self.visible

    def close(self):
        self.closed += 1


def buildMainWindow(database, **settings):
    """A real MainWindow over a private conf, context and repositories.

    Private on purpose: the window subscribes to conf's restart and reload
    signals, so a shared conf would collect handlers pointing at every window
    the suite ever built.
    """
    conf = createConfig(settings=MockConfig())
    for name, value in settings.items():
        setattr(conf, name, value)

    return MainWindow(conf, createContext(conf), Repositories(database))


@pytest.fixture(scope='class')
def windowDatabase():
    database = createDatabase(uri='sqlite:///:memory:')
    yield database
    database.engine.dispose()


@pytest.fixture(scope='class')
def sharedWindow(windowDatabase):
    """One real MainWindow for a whole test class.

    Building it costs about 0.4s -- five editors, four senders, six sounds --
    and it is a passive view, so a test that swaps a child out only has to
    put it back. The tests below do that with monkeypatch, which restores
    automatically.
    """
    window = buildMainWindow(windowDatabase)
    yield window
    window.hideTray()
    window.closeDialogs()


@pytest.fixture
def buildWindow(qtbot, database):
    """A one-off window, for the cases that need their own conf or platform."""
    built = []

    def build(**settings):
        window = buildMainWindow(database, **settings)
        qtbot.addWidget(window)
        built.append(window)
        return window

    yield build

    for window in built:
        window.hideTray()
        window.closeDialogs()


class TestMainWindow:
    """The window itself: a passive view. Every method is either a render the
    presenters ask for, or a question they ask."""

    @pytest.fixture(autouse=True)
    def window(self, sharedWindow):
        yield sharedWindow
        sharedWindow.hide()

    def test_the_widgets_are_given_the_windows_own_collaborators(self, window):
        assert window.tafTable.repository is window.repositories.taf
        assert window.metarTable.repository is window.repositories.metar
        assert window.sigmetTable.repository is window.repositories.sigmet
        assert window.airmetTable.repository is window.repositories.sigmet
        assert window.chartViewer.repository is window.repositories.metar
        assert window.tafBoard.context is window.context
        assert window.clock.context is window.context

    def test_the_tray_carries_the_standard_menu(self, window):
        actions = window.trayMenu.actions()

        assert window.settingAction in actions
        assert window.aboutAction in actions
        assert window.quitAction in actions

    def test_the_tray_tooltip_names_the_version(self, window):
        assert window.tray.toolTip() == 'Tafor {}'.format(__version__)

    def test_the_frame_paints_a_white_content_area(self, window):
        assert window.scrollContents.autoFillBackground() is True

    @pytest.mark.parametrize('product, expected', [
        ('Windows 10 (10.0)', 'light'),
        ('Windows 11 (10.0)', 'light'),
        ('Ubuntu 22.04', 'light'),
        ('macOS 14.0', 'dark'),
        ('FreeBSD 14.0', 'normal'),
    ])
    def test_the_tray_style_follows_the_platform(self, window, monkeypatch, product, expected):
        monkeypatch.setattr(window, 'sysInfo', product)

        assert window.trayStyle() == expected

    def test_a_dark_tray_icon_is_a_mask(self, window, monkeypatch):
        tray = FakeTray()
        monkeypatch.setattr(window, 'tray', tray)

        window.setTrayIcon('dark')

        assert tray.icon.isMask() is True

    def test_an_unknown_style_falls_back_to_the_normal_icon(self, window, monkeypatch):
        tray = FakeTray()
        monkeypatch.setattr(window, 'tray', tray)

        window.setTrayIcon('nonsense')

        assert tray.icon.isNull() is False
        assert tray.icon.isMask() is False

    def test_hide_tray_hides_the_icon(self, window, monkeypatch):
        tray = FakeTray()
        monkeypatch.setattr(window, 'tray', tray)

        window.hideTray()

        assert tray.hidden == 1

    def test_the_macos_tray_menu_swaps_the_icon(self, buildWindow, monkeypatch):
        """macOS draws the menu bar icon against a light background, so the
        dark mask is swapped in only while the menu is open."""
        monkeypatch.setattr(main_module.QSysInfo, 'prettyProductName', lambda: 'macOS 14.0')
        window = buildWindow()
        assert window.sysInfo == 'macOS 14.0'
        assert window.tray.icon().isMask() is True

        window.trayMenu.aboutToShow.emit()

        assert window.tray.icon().isMask() is False

        window.trayMenu.aboutToHide.emit()

        assert window.tray.icon().isMask() is True

    @pytest.mark.parametrize('level, expected', [
        ('noicon', QSystemTrayIcon.NoIcon),
        ('information', QSystemTrayIcon.Information),
        ('warning', QSystemTrayIcon.Warning),
        ('critical', QSystemTrayIcon.Critical),
    ])
    def test_notify_uses_the_matching_tray_icon(self, window, monkeypatch, level, expected):
        tray = FakeTray()
        monkeypatch.setattr(window, 'tray', tray)

        window.notify('Title', 'Text', level)

        assert tray.messages == [('Title', 'Text', expected)]

    @pytest.fixture
    def sounds(self, window, monkeypatch):
        sounds = {name: FakeSound() for name in (
            'notification', 'incoming', 'alarm', 'taf', 'trend', 'sigmet')}
        monkeypatch.setattr(window, 'sounds', sounds)
        return sounds

    def test_stopping_a_channel_stops_it(self, window, sounds):
        window.updateSound('trend', False)

        assert sounds['trend'].stops == 1
        assert sounds['trend'].plays == 0

    @pytest.mark.parametrize('name', [
        'notification', 'incoming', 'alarm', 'taf', 'trend', 'sigmet'])
    def test_starting_a_channel_plays_it(self, window, sounds, name):
        window.updateSound(name, True)

        assert sounds[name].plays == 1
        assert sounds[name].stops == 0

    def test_the_alarm_switch_reads_the_menu_action(self, window):
        window.warnTafAction.setChecked(True)
        assert window.alarmEnabled() is True

        window.warnTafAction.setChecked(False)
        assert window.alarmEnabled() is False

    def test_render_taf_board_updates_the_board(self, window, monkeypatch):
        board = FakeWidget()
        monkeypatch.setattr(window, 'tafBoard', board)

        window.renderTafBoard()

        assert board.calls == [('updateGui', (), {})]

    def test_render_tables_updates_every_table(self, window, monkeypatch):
        tables = [FakeWidget() for _ in range(4)]
        for name, table in zip(
                ('tafTable', 'metarTable', 'sigmetTable', 'airmetTable'), tables):
            monkeypatch.setattr(window, name, table)

        window.renderTables()

        assert [table.calls for table in tables] == [[('updateGui', (), {})]] * 4

    def test_render_recent_syncs_the_board(self, window, monkeypatch):
        board = FakeWidget()
        monkeypatch.setattr(window, 'recentBoard', board)
        entries = [object()]

        window.renderRecent(entries)

        assert board.calls == [('sync', (entries,), {})]

    def test_render_layer_updates_the_editor(self, window, monkeypatch):
        editor = FakeWidget()
        monkeypatch.setattr(window, 'sigmetEditor', editor)

        window.renderLayer()

        assert editor.calls == [('updateLayer', (), {})]

    def test_render_sigmet_graphic_updates_the_canvas(self, window, monkeypatch):
        editor = FakeWidget()
        monkeypatch.setattr(window, 'sigmetEditor', editor)

        window.renderSigmetGraphic()

        assert editor.calls == [('updateGraphicCanvas', (), {})]

    def test_render_sigmet_text_updates_the_custom_text(self, window, monkeypatch):
        editor = FakeWidget()
        monkeypatch.setattr(window, 'sigmetEditor', editor)

        window.renderSigmetText()

        assert editor.calls == [('updateCustomText', (), {})]

    def test_a_reminder_starts_hidden(self, window):
        assert window.reminderVisible('taf') is False
        assert window.reminderVisible('sigmet') is False

    def test_close_reminder_closes_the_right_box(self, window, monkeypatch):
        boxes = {'taf': FakeWidget(), 'sigmet': FakeWidget()}
        monkeypatch.setattr(window, 'reminders', boxes)

        window.closeReminder('taf')

        assert boxes['taf'].calls == [('close', (), {})]
        assert boxes['sigmet'].calls == []

    def test_show_reminder_plays_the_sound_and_stops_it_after(self, window, monkeypatch):
        box = FakeReminderBox(answer=QMessageBox.AcceptRole, visible=False)
        sound = FakeSound()
        monkeypatch.setitem(window.reminders, 'taf', box)
        monkeypatch.setitem(window.sounds, 'taf', sound)

        answer = window.showReminder('taf', 'Time to issue FT1012')

        assert box.text == 'Time to issue FT1012'
        assert sound.plays == 1
        assert sound.stops == 1
        assert answer == QMessageBox.AcceptRole

    def test_a_reminder_left_open_keeps_playing(self, window, monkeypatch):
        box = FakeReminderBox(answer=QMessageBox.RejectRole, visible=True)
        sound = FakeSound()
        monkeypatch.setitem(window.reminders, 'taf', box)
        monkeypatch.setitem(window.sounds, 'taf', sound)

        answer = window.showReminder('taf', 'Time to issue FT1012')

        assert sound.stops == 0
        assert answer == QMessageBox.RejectRole

    def test_a_card_bell_goes_to_the_board(self, window, monkeypatch):
        board = FakeWidget()
        monkeypatch.setattr(window, 'recentBoard', board)

        window.setSigmetReminder('uuid-1', True)

        assert board.calls == [('setReminderEnabled', ('uuid-1', True), {})]

    def test_status_goes_to_the_status_bar(self, window):
        window.status('Saved', 1000)

        assert window.statusBar.currentMessage() == 'Saved'

    def test_confirm_reads_the_answer(self, window, monkeypatch):
        monkeypatch.setattr(main_module.QMessageBox, 'question',
                            lambda *args, **kwargs: QMessageBox.Yes)
        assert window.confirm('Title', 'Text') is True

        monkeypatch.setattr(main_module.QMessageBox, 'question',
                            lambda *args, **kwargs: QMessageBox.No)
        assert window.confirm('Title', 'Text') is False

    def test_a_custom_message_opens_the_sender(self, window, monkeypatch):
        sender = FakeWidget()
        sounds = {name: FakeSound() for name in window.sounds}
        tray = FakeTray()
        monkeypatch.setattr(window, 'customSender', sender)
        monkeypatch.setattr(window, 'sounds', sounds)
        monkeypatch.setattr(window, 'tray', tray)
        message = object()

        window.handleCustomMessage(message)

        assert sender.calls == [('receive', (message,), {}), ('show', (), {})]
        assert sounds['incoming'].plays == 1
        assert tray.messages[0][0] == 'Message Received'

    def test_the_license_menu_tracks_the_registration(self, window):
        window.setLicenseMenuState(True)

        assert window.removeLicenseAction.isVisible() is True
        assert window.enterLicenseAction.isVisible() is False

        window.setLicenseMenuState(False)

        assert window.removeLicenseAction.isVisible() is False
        assert window.enterLicenseAction.isVisible() is True

    def test_open_setting_reopens_the_dialog(self, window, monkeypatch):
        dialog = FakeWidget()
        monkeypatch.setattr(window, 'settingDialog', dialog)

        window.openSetting()

        assert dialog.calls == [('reopen', (), {})]

    def test_removing_a_license_delegates_to_the_editor(self, window, monkeypatch):
        editor = FakeWidget()
        monkeypatch.setattr(window, 'licenseEditor', editor)

        window.removeLicense()

        assert editor.calls == [('removeLicense', (), {})]

    def test_ensure_visible_shows_a_hidden_window(self, window, monkeypatch):
        calls = []
        window.hide()
        monkeypatch.setattr(window, 'showNormal', lambda: calls.append(True))

        window.ensureVisible()

        assert calls == [True]

    def test_ensure_visible_leaves_a_visible_window_alone(self, window, monkeypatch):
        calls = []
        window.show()
        monkeypatch.setattr(window, 'showNormal', lambda: calls.append(True))

        window.ensureVisible()

        assert calls == []

    def test_review_routes_a_taf_card_to_the_taf_sender(self, window, monkeypatch):
        taf, sigmet = FakeWidget(), FakeWidget()
        monkeypatch.setattr(window, 'tafSender', taf)
        monkeypatch.setattr(window, 'sigmetSender', sigmet)
        message = object()

        window.review(SimpleNamespace(type='FT', message=message))

        assert taf.calls == [('receive', (message,), {}), ('show', (), {})]
        assert sigmet.calls == []

    def test_review_routes_a_sigmet_card_to_the_sigmet_sender(self, window, monkeypatch):
        taf, sigmet = FakeWidget(), FakeWidget()
        monkeypatch.setattr(window, 'tafSender', taf)
        monkeypatch.setattr(window, 'sigmetSender', sigmet)
        message = object()

        window.review(SimpleNamespace(type='WS', message=message))

        assert sigmet.calls == [('receive', (message,), {}), ('show', (), {})]
        assert taf.calls == []

    def test_review_ignores_other_card_types(self, window, monkeypatch):
        taf, sigmet = FakeWidget(), FakeWidget()
        monkeypatch.setattr(window, 'tafSender', taf)
        monkeypatch.setattr(window, 'sigmetSender', sigmet)

        window.review(SimpleNamespace(type='SA', message=object()))

        assert taf.calls == []
        assert sigmet.calls == []

    def test_open_issue_tracker_opens_github(self, window, monkeypatch):
        opened = []
        monkeypatch.setattr(main_module, 'QDesktopServices', SimpleNamespace(openUrl=opened.append))

        window.openIssueTracker()

        assert opened == [QUrl('https://github.com/up1and/tafor/issues')]

    def test_open_docs_prefers_the_development_build(self, window, monkeypatch):
        opened = []
        monkeypatch.setattr(main_module, 'QDesktopServices', SimpleNamespace(openUrl=opened.append))
        monkeypatch.setattr(main_module, 'os', SimpleNamespace(
            path=SimpleNamespace(join=os.path.join, exists=lambda path: os.pardir in path)))

        window.openDocs()

        assert opened == [QUrl.fromLocalFile(os.path.join(
            main_module.root, os.pardir, 'docs', '_build', 'html', 'index.html'))]

    def test_open_docs_falls_back_to_the_release_build(self, window, monkeypatch):
        opened = []
        monkeypatch.setattr(main_module, 'QDesktopServices', SimpleNamespace(openUrl=opened.append))
        monkeypatch.setattr(main_module, 'os', SimpleNamespace(
            path=SimpleNamespace(join=os.path.join, exists=lambda path: os.pardir not in path)))

        window.openDocs()

        assert opened == [QUrl.fromLocalFile(os.path.join(
            main_module.root, 'docs', '_build', 'html', 'index.html'))]

    def test_open_docs_falls_back_to_readthedocs(self, window, monkeypatch):
        opened = []
        monkeypatch.setattr(main_module, 'QDesktopServices', SimpleNamespace(openUrl=opened.append))
        monkeypatch.setattr(main_module, 'os', SimpleNamespace(
            path=SimpleNamespace(join=os.path.join, exists=lambda path: False)))

        window.openDocs()

        assert opened == [QUrl('https://tafor.readthedocs.io')]

    def test_close_senders_closes_the_three_senders(self, window, monkeypatch):
        senders = [FakeWidget() for _ in range(3)]
        for name, sender in zip(('tafSender', 'trendSender', 'sigmetSender'), senders):
            monkeypatch.setattr(window, name, sender)

        window.closeSenders()

        assert [sender.calls for sender in senders] == [[('close', (), {})]] * 3

    def test_close_dialogs_closes_everything_the_app_owns(self, window, monkeypatch):
        names = ['tafSender', 'trendSender', 'sigmetSender', 'customSender',
                 'tafEditor', 'trendEditor', 'sigmetEditor', 'licenseEditor',
                 'settingDialog', 'chartViewer']
        dialogs = [FakeWidget() for _ in names]
        for name, dialog in zip(names, dialogs):
            monkeypatch.setattr(window, name, dialog)

        reminders = {'taf': FakeWidget(), 'sigmet': FakeWidget()}
        monkeypatch.setattr(window, 'reminders', reminders)

        window.closeDialogs()

        for dialog in dialogs + list(reminders.values()):
            assert dialog.calls == [('close', (), {})]

    def test_a_user_close_hides_the_window(self, window):
        window.show()
        event = FakeCloseEvent(spontaneous=True)

        window.closeEvent(event)

        assert event.ignored == 1
        assert event.accepted == 0
        assert window.isVisible() is False

    def test_a_programmatic_close_is_accepted(self, window):
        event = FakeCloseEvent(spontaneous=False)

        window.closeEvent(event)

        assert event.accepted == 1
        assert event.ignored == 0

    def test_a_minimised_window_leaves_the_taskbar(self, window, monkeypatch):
        tray = FakeTray()
        monkeypatch.setattr(window, 'tray', tray)
        monkeypatch.setattr(window, 'isMinimized', lambda: True)

        handled = window.event(QEvent(QEvent.WindowStateChange))

        assert handled is True
        assert tray.shown == 1

    def test_an_ordinary_state_change_is_left_to_qt(self, window, monkeypatch):
        tray = FakeTray()
        monkeypatch.setattr(window, 'tray', tray)
        monkeypatch.setattr(window, 'isMinimized', lambda: False)

        window.event(QEvent(QEvent.WindowStateChange))

        assert tray.shown == 0

    def test_restart_requires_the_users_consent(self, window, monkeypatch):
        starts = []
        monkeypatch.setattr(main_module.QMessageBox, 'information',
                            lambda *args, **kwargs: QMessageBox.No)
        monkeypatch.setattr(main_module.QProcess, 'startDetached',
                            lambda *args, **kwargs: starts.append((args, kwargs)) or True)

        window.restart()

        assert starts == []

    def test_a_confirmed_restart_relaunches_with_the_saved_arguments(self, window, monkeypatch):
        starts = []
        monkeypatch.setattr(main_module.QMessageBox, 'information',
                            lambda *args, **kwargs: QMessageBox.Yes)
        monkeypatch.setenv('TAFOR_ARGS', '["--debug"]')
        monkeypatch.setattr(main_module.QProcess, 'startDetached',
                            lambda program, args: starts.append((program, args)) or True)

        window.restart()

        program, args = starts[0]
        assert program == sys.executable
        assert args[0] == os.path.join(main_module.root, '__main__.py')
        assert args[1:] == ['--debug']

    def test_a_failed_restart_is_reported(self, window, monkeypatch):
        tray = FakeTray()
        monkeypatch.setattr(window, 'tray', tray)
        monkeypatch.setattr(main_module.QMessageBox, 'information',
                            lambda *args, **kwargs: QMessageBox.Yes)
        monkeypatch.setattr(main_module.QProcess, 'startDetached', lambda *args, **kwargs: False)

        window.restart()

        assert tray.messages == [
            ('Restart Required',
             'Could not restart automatically, please start tafor again.',
             QSystemTrayIcon.Warning)]

    def test_about_reports_the_unregistered_state(self, window, monkeypatch):
        boxes = installAboutBox(monkeypatch)

        window.showAbout()

        assert boxes[0].title == 'About'
        assert 'Unregistered' in boxes[0].text
        assert __version__ in boxes[0].text
        assert boxes[0].executed == 1

    def test_about_reports_the_days_remaining_when_registered(self, window, monkeypatch):
        boxes = installAboutBox(monkeypatch)
        monkeypatch.setattr(window.context.license, 'license', lambda: {'register': 'YUSO'})
        monkeypatch.setattr(window.context.license, 'exp', 12)

        window.showAbout()

        assert '12 days remaining' in boxes[0].text


class FakeAboutBox:
    """A QMessageBox stub: it captures the text and never blocks."""

    def __init__(self, parent=None):
        self.parent = parent
        self.title = None
        self.text = None
        self.format = None
        self.executed = 0

    def setWindowTitle(self, title):
        self.title = title

    def setTextFormat(self, format):
        self.format = format

    def setText(self, text):
        self.text = text

    def layout(self):
        return SimpleNamespace(itemAt=lambda index: SimpleNamespace(spacerItem=lambda: None))

    def addButton(self, button):
        pass

    def exec(self):
        self.executed += 1
        return 0


def installAboutBox(monkeypatch):
    """Replace QMessageBox in main's namespace with a non-blocking stub, and
    keep the Ok button constant the about box reaches for."""
    boxes = []

    def build(parent=None):
        boxes.append(FakeAboutBox(parent))
        return boxes[-1]

    build.Ok = QMessageBox.Ok
    monkeypatch.setattr(main_module, 'QMessageBox', build)
    return boxes


class TestMainWindowWithoutSigmet:
    """A copy built with SIGMET turned off drops the action and the two tabs,
    and leaves the rest of the window alone."""

    @pytest.fixture(scope='class')
    def window(self, windowDatabase):
        window = buildMainWindow(windowDatabase, sigmetEnabled=False)
        yield window
        window.hideTray()
        window.closeDialogs()

    def test_the_sigmet_action_is_hidden(self, window):
        assert window.sigmetAction.isVisible() is False

    def test_the_sigmet_tabs_are_removed(self, window):
        pages = [window.mainTab.widget(i) for i in range(window.mainTab.count())]

        assert window.sigmetTab not in pages
        assert window.airmetTab not in pages

    def test_the_remaining_tabs_are_kept(self, window):
        pages = [window.mainTab.widget(i) for i in range(window.mainTab.count())]

        assert window.tafTab in pages
        assert window.metarTab in pages
        assert window.recentTab in pages


if __name__ == '__main__':
    pytest.main([__file__])
