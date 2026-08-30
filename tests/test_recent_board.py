import datetime
from types import SimpleNamespace

import pytest

from PyQt5.QtWidgets import QSizePolicy

from tafor.core.models import Metar
from tafor.core.repositories import Repositories
from tafor.ui.main import DataService
from tafor.ui.widgets.recent import NotificationCard, NotificationModel, RecentBoard, ReviewCard, ReviewModel

METAR = 'METAR ZJHK 210900Z 14004MPS 4500 -RA BKN030='


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


def polygonGeo(lat=0.0):
    return {'features': [{'geometry': {'type': 'Polygon',
           'coordinates': [[0, lat], [2, lat], [2, 1 + lat], [0, 1 + lat], [0, lat]]}, 'properties': {}}]}


@pytest.fixture
def board(qtbot):
    conf = SimpleNamespace(windowsStyle='System')
    board = RecentBoard(None, conf=conf, expiryMinutes=10)
    qtbot.addWidget(board)
    return board


@pytest.fixture
def service(conf, context, database, board):
    repositories = Repositories(database)
    view = SimpleNamespace(
        tafBoard=SimpleNamespace(updateGui=lambda: None),
        recentBoard=board,
    )
    return DataService(view, context, conf, repositories)


def titles(board):
    return [board.cardLayout.itemAt(i).widget().model.type
            for i in range(board.cardLayout.count())]


def addStoredMetar(service):
    metar = Metar(type='SA', text=METAR)
    service.repositories.message.add(metar)
    return metar


class TestRecentBoard:

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
        board.sync([cardModel('m', 'SA', text='METAR ZJHK 210900Z 14004MPS 4500 -RA BKN030=')])

        card = board.cards['m']
        assert card.group.title() == 'SA'
        assert card.text.text() == 'METAR ZJHK 210900Z 14004MPS 4500 -RA BKN030='
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


class TestUpdateRecent:
    """DataService.updateRecent builds the metar card and keeps it
    mutually exclusive with the live notification card."""

    def test_stored_metar_shows_without_notification(self, service, board):
        metar = addStoredMetar(service)

        service.updateRecent()

        assert titles(board) == ['SA']
        card = board.cards[metar.uuid]
        assert isinstance(card, ReviewCard)
        assert card.text.text() == METAR

    def test_notification_replaces_stored_metar(self, service, board, context):
        metar = addStoredMetar(service)
        context.notification.metar.setState({'message': METAR, 'validation': True})

        service.updateRecent()

        assert titles(board) == [None]
        assert isinstance(board.cards[None], NotificationCard)
        assert metar.uuid not in board.cards

    def test_stored_metar_returns_after_notification_clears(self, service, board, context):
        metar = addStoredMetar(service)
        context.notification.metar.setState({'message': METAR, 'validation': True})
        service.updateRecent()
        assert titles(board) == [None]

        context.notification.metar.clear()
        service.updateRecent()

        assert titles(board) == ['SA']
        assert board.cards[metar.uuid].text.text() == METAR
