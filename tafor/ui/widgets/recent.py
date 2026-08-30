import datetime

from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QIcon, QPixmap
from PyQt5.QtWidgets import QHBoxLayout, QSizePolicy, QSpacerItem, QVBoxLayout, QWidget, QWIDGETSIZE_MAX

from tafor.core.utils.time import timeAgo
from tafor.core.utils.common import iconPath
from tafor.ui.fonts import fixedFont
from tafor.ui.qt import Ui_main_recent
from tafor.ui.styles import flatButtonStyle
from tafor.ui.widgets.geometry import SigmetBackground


class ReviewModel:
    """One stored report message shown as a review card (taf/trend/sigmet rows)."""

    def __init__(self, uuid, type, created, message, text, geo=None):
        self.uuid = uuid
        self.type = type
        self.created = created
        self.message = message
        self.text = text
        self.geo = geo


class NotificationModel:
    """The live METAR notification shown as a notification card.

    At most one exists on the board, and the None uuid is its key."""

    uuid = None
    type = None

    def __init__(self, created, validations):
        self.created = created
        self.validations = validations


class RecentBoard(QWidget):
    """Owns the recent-message cards: diffing, ordering and the shared
    notification countdown."""

    expired = pyqtSignal(object)
    reminderToggled = pyqtSignal(object, bool)
    reviewRequested = pyqtSignal(object)
    replyRequested = pyqtSignal()

    def __init__(self, parent=None, conf=None, expiryMinutes=10):
        super().__init__(parent)
        self.conf = conf
        self.expiryMinutes = expiryMinutes
        self.cards = {}

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignTop)
        self.setLayout(layout)
        self.cardLayout = layout

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(1 * 1000)

    def sync(self, models):
        """Sync the cards with the given view models, keeping their order."""
        incoming = {model.uuid: model for model in models}

        for uuid, card in list(self.cards.items()):
            if uuid not in incoming:
                self.cardLayout.removeWidget(card)
                card.deleteLater()
                del self.cards[uuid]

        for model in models:
            if model.uuid in self.cards:
                self.cards[model.uuid].setModel(model)
            else:
                card = CARD_TYPES[type(model)](self, model, conf=self.conf)
                card.reminderToggled.connect(self.reminderToggled)
                card.reviewRequested.connect(self.reviewRequested)
                card.replyRequested.connect(self.replyRequested)
                self.cards[model.uuid] = card
                self.cardLayout.addWidget(card)

        for index, model in enumerate(models):
            self.cardLayout.insertWidget(index, self.cards[model.uuid])

    def setReminderEnabled(self, uuid, enabled):
        card = self.cards.get(uuid)
        if card:
            card.setReminderEnabled(enabled)

    def tick(self):
        now = datetime.datetime.utcnow()
        expired = [uuid for uuid, card in self.cards.items() if card.tick(now, self.expiryMinutes)]
        for uuid in expired:
            self.expired.emit(uuid)


class RecentCard(QWidget, Ui_main_recent.Ui_Recent):
    """Base card: shared setup, fonts and the model update flow. The review
    and notification subclasses fill in the mode specifics."""

    MAP_WIDTH = 200        # Fixed overlay width; the height follows the whole card

    reminderToggled = pyqtSignal(object, bool)
    reviewRequested = pyqtSignal(object)
    replyRequested = pyqtSignal()

    def __init__(self, parent, model, conf=None):
        super().__init__(parent)
        self.setupUi(self)
        self.conf = conf
        self.model = model
        self.remind = False
        self.map = None
        self.mapGeo = None
        self.contentLayout = None
        self.expired = False

        # The generated policy is vertically Fixed, clipping long wrapped text
        sizePolicy = self.sizePolicy()
        sizePolicy.setVerticalPolicy(QSizePolicy.Minimum)
        sizePolicy.setHeightForWidth(True)
        self.setSizePolicy(sizePolicy)

        self.toolsWidget.setAttribute(Qt.WA_TranslucentBackground)
        self.timeLabel.setAttribute(Qt.WA_TranslucentBackground)
        self.text.setAttribute(Qt.WA_TranslucentBackground)

        font = fixedFont()
        self.setFont(font)
        self.timeLabel.setFont(font)
        textFont = QFont(font)
        textFont.setPointSize(12)
        self.text.setFont(textFont)

        font = QFont()
        font.setPointSize(11)
        self.tip.setFont(font)
        self.tip.setContentsMargins(0, 9, 0, 0)
        self.tip.hide()

        self.configure()
        self.bindSignal()
        self.updateText()
        self.updateButton()

    def configure(self):
        """Mode specific widget setup, run once at construction."""
        pass

    def setModel(self, model):
        self.model = model
        self.expired = False
        self.updateText()
        self.updateGui()

    def timeStamp(self):
        raise NotImplementedError

    def tick(self, now, expiryMinutes):
        """Review cards never expire."""
        return False

    def updateText(self):
        self.timeLabel.setText(self.timeStamp())
        self.updateMessage()
        self.updateMap()

    def updateMessage(self):
        pass

    def updateMap(self):
        pass

    def updateGui(self):
        pass

    def bindSignal(self):
        self.markButton.clicked.connect(lambda: self.reviewRequested.emit(self.model))
        self.replyButton.clicked.connect(lambda: self.replyRequested.emit())
        self.reminderButton.clicked.connect(self.toggleReminder)

    def updateButton(self):
        style = flatButtonStyle()
        self.replyButton.setIcon(QIcon(iconPath('reply-arrow.png')))
        self.replyButton.setStyleSheet(style)
        self.markButton.setStyleSheet(style)
        self.reminderButton.setStyleSheet(style)

    def toggleReminder(self):
        # RemindService expects the stored message with parser()/expired()
        self.reminderToggled.emit(self.model.message, not self.remind)

    def setReminderEnabled(self, enabled):
        self.remind = enabled
        self.updateReminderButton()

    def updateReminderButton(self):
        if self.remind:
            icon = iconPath('reminder.png')
        else:
            icon = iconPath('no-reminder.png')

        self.reminderButton.setIcon(QIcon(icon))


class ReviewCard(RecentCard):

    def configure(self):
        self.replyButton.hide()
        self.signLabel.hide()
        self.reminderButton.hide()
        self.updateMarkButton()

        if self.model.type in ['WS', 'WC', 'WV', 'WA']:
            self.setReminderEnabled(self.remind)
            self.reminderButton.show()

    def timeStamp(self):
        return self.model.created.strftime('%Y-%m-%d %H:%M:%S')

    def updateMessage(self):
        self.text.setText(self.model.text)
        self.group.setTitle(self.model.type)

    def updateGui(self):
        self.updateMarkButton()
        self.updateReminderButton()

    def updateMarkButton(self):
        if self.model.type not in ['FC', 'FT', 'WS', 'WC', 'WV', 'WA']:
            self.markButton.hide()
            return

        if self.model.message.confirmed:
            icon = iconPath('checkmark.png')
        else:
            icon = iconPath('questionmark.png')

        self.markButton.setIcon(QIcon(icon))

    def updateMap(self):
        """Swap the embedded map when a refresh carries another area."""
        if self.model.geo == self.mapGeo:
            return

        self.mapGeo = self.model.geo

        if self.map is not None:
            self.map.setParent(None)
            self.map.deleteLater()
            self.map = None

        if self.model.geo:
            self.embedMap()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.repositionMap()

    def embedMap(self):
        """Overlay the pre-rendered SIGMET map on the right side at full card
        height; the tools row floats above it."""
        if self.contentLayout is None:
            self.buildContentRow()

        self.map = SigmetBackground(self.model.geo, parent=self.group)
        # SigmetBackground fixes its size; the overlay follows the card instead
        self.map.setMinimumSize(0, 0)
        self.map.setMaximumSize(QWIDGETSIZE_MAX, QWIDGETSIZE_MAX)
        self.map.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.toolsWidget.raise_()
        self.repositionMap()

    def repositionMap(self):
        """Pin the map overlay to the right edge of the group at full height."""
        if self.map is None:
            return

        inner = self.group.contentsRect()
        self.map.setGeometry(
            inner.x() + inner.width() - self.MAP_WIDTH,
            inner.y(),
            self.MAP_WIDTH,
            inner.height())

    def buildContentRow(self):
        """Move text/tip into a two-column row that reserves the right side
        for the map overlay."""
        index = self.groupLayout.indexOf(self.text)
        left = QVBoxLayout()
        left.setContentsMargins(0, 0, 0, 0)
        for widget in [self.text, self.tip]:
            self.groupLayout.removeWidget(widget)
            left.addWidget(widget)

        content = QHBoxLayout()
        content.setContentsMargins(0, 0, 0, 0)
        content.addLayout(left, 1)
        content.addItem(QSpacerItem(self.MAP_WIDTH, 0, QSizePolicy.Fixed, QSizePolicy.Minimum))
        self.groupLayout.insertLayout(index, content)
        self.contentLayout = content


class NotificationCard(RecentCard):

    def configure(self):
        # Dotted border marks the card as an unconfirmed notification
        self.setStyleSheet(
            'RecentCard QGroupBox { border: 2px dotted #dcdcdc; padding: 1em; }'
        )
        self.markButton.hide()
        self.reminderButton.hide()

        if self.model.validations['validation']:
            if self.model.validations['pass']:
                icon = iconPath('protect.png')
            else:
                icon = iconPath('warning-shield.png')

            shieldIcon = QPixmap(icon)
            self.signLabel.setPixmap(shieldIcon.scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.signLabel.hide()

    def timeStamp(self, now=None):
        ago = timeAgo(self.model.created, now or datetime.datetime.utcnow())
        return ago.capitalize()

    def updateMessage(self):
        self.text.setText(self.model.validations['html'])
        if self.model.validations['tips']:
            html = '<p style="color: grey"># {}</p>'.format('<br/># '.join(self.model.validations['tips']))
            self.tip.setText(html)
            self.tip.show()

    def tick(self, now, expiryMinutes):
        """Refresh the relative timestamp; returns True on the transition to expired."""
        if self.expired:
            return False

        self.expired = now - self.model.created > datetime.timedelta(minutes=expiryMinutes)
        self.timeLabel.setText(self.timeStamp(now))
        return self.expired


CARD_TYPES = {
    ReviewModel: ReviewCard,
    NotificationModel: NotificationCard,
}
