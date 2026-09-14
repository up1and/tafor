"""Tests for the main window.

tafor/ui/main.py is the composition root and cannot be instantiated in a test:
it builds a QApplication, the tray icon and a single-instance server. The
behaviour that used to live there is covered here instead, together with the
recent board those presenters drive.

The presenters are handed the window directly and call a known set of methods
on it, so each fake view below implements exactly the methods its presenter
calls and records what it was asked to do.
"""

import datetime

from types import SimpleNamespace

import pytest

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QMessageBox, QSizePolicy

from tafor.core.models import Metar, Sigmet, Taf
from tafor.core.repositories import Repositories
from tafor.ui.main import (
    BoardPresenter,
    LayerPresenter,
    MessagePresenter,
    RecentEntryBuilder,
    ReminderPresenter,
)
from tafor.ui.widgets.recent import (
    NotificationCard, NotificationModel, RecentBoard, ReviewCard, ReviewModel,
)


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

    def isRunning(self):
        return self.running

    def start(self):
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


if __name__ == '__main__':
    pytest.main([__file__])
