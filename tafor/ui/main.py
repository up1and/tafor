"""
Main Window: a passive view.
It builds its widgets and holds no behaviour beyond rendering and answering
questions. Nothing here talks to the context, the database or the network --
every method below is either a render the presenters ask for, or a question
they ask.

Main Window's behaviour: one presenter per concern.
"""
import os
import sys
import json
import datetime
import logging

from PyQt5.QtCore import QCoreApplication, QObject, QEvent, QTimer, QProcess, QSysInfo, Qt, QUrl, pyqtSignal
from PyQt5.QtGui import QColor, QDesktopServices, QIcon
from PyQt5.QtWidgets import QMainWindow, QMenu, QMessageBox, QSizePolicy, QSpacerItem, QSystemTrayIcon

from tafor import __version__, root
from tafor.core.utils.time import utcnow
from tafor.core.utils.common import iconPath, revision, checkVersion
from tafor.core.repositories import SigmetFilter, subscribedTypes
from tafor.ui.components.chart import ChartViewer
from tafor.ui.components.send import CustomSender, SigmetSender, TafSender, TrendSender
from tafor.ui.components.setting import SettingDialog
from tafor.ui.components.sigmet import SigmetEditor
from tafor.ui.components.taf import TafEditor
from tafor.ui.components.trend import TrendEditor
from tafor.ui.qt import Ui_main
from tafor.ui.widgets.misc import Clock, LicenseEditor, RemindMessageBox, TafBoard
from tafor.ui.widgets.recent import RecentBoard, NotificationModel, ReviewModel
from tafor.ui.widgets.sound import Sound
from tafor.ui.widgets.table import AirmetTable, MetarTable, SigmetTable, TafTable
from tafor.ui.workers import CheckUpgradeWorker, LayerWorker, MessageWorker

logger = logging.getLogger('tafor.main')


def restartArgs():
    """The argv this process was started with, replayed to the child.

    Read, never popped. Mutating the environment of a running process to talk
    to its replacement is a side effect waiting to surprise someone, and it
    also means a second restart has nothing left to replay.
    """
    raw = os.environ.get('TAFOR_ARGS') or '[]'
    try:
        return json.loads(raw)
    except ValueError:
        logger.warning('Ignoring malformed TAFOR_ARGS, %r', raw)
        return []


class ReminderPresenter(QObject):
    """Nags about TAF and SIGMET messages that are due.

    Policy and dialog stay together on purpose: the policy is three lines and
    reads better next to the question it produces.
    """

    def __init__(self, view, context, conf, parent=None):
        super().__init__(parent)
        self.view = view
        self.context = context
        self.conf = conf

        self.snooze = QTimer(self)
        self.snooze.setSingleShot(True)
        self.snooze.timeout.connect(self.remindTaf)

    def initialize(self):
        self.context.event.tafReminderTriggered.connect(self.remindTaf)
        self.view.reminderToggled.connect(self.setReminder)
        # A sent message can bring a SIGMET reminder forward or cancel it
        self.view.messageSent.connect(self.remindSigmet)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.remindSigmet)
        self.timer.start(60 * 1000)

    def remindTaf(self):
        if not self.conf.remindTaf or self.view.reminderVisible('taf'):
            return

        if not self.context.taf.shouldRemind():
            return

        spec = self.context.taf.spec.designator
        period = self.context.taf.period()
        mark = spec + period[2:4] + period[7:]
        text = QCoreApplication.translate('MainWindow', 'Time to issue {}').format(mark)

        if self.view.showReminder('taf', text) == QMessageBox.RejectRole:
            self.snooze.start(self.conf.remindSnoozeMinutes * 60 * 1000)

    def remindSigmet(self):
        if not self.conf.remindSigmet or self.view.reminderVisible('sigmet'):
            return

        for due in self.context.sigmet.outdate():
            parser = due['text']
            mark = '{} {}'.format(parser.category(), parser.sequence())
            text = QCoreApplication.translate('MainWindow', 'Time to update {}').format(mark)

            if self.view.showReminder('sigmet', text) == QMessageBox.AcceptRole:
                self.removeReminder(due['uuid'])
            else:
                self.context.sigmet.update(
                    due['uuid'],
                    due['time'] + datetime.timedelta(minutes=self.conf.remindSnoozeMinutes),
                )

    def setReminder(self, message, enabled):
        """Add or remove a reminder for a stored message. Also the slot for a
        card's bell toggle."""
        if enabled:
            self.context.sigmet.add(message.uuid, message.parser(), message.expired())
        else:
            self.context.sigmet.remove(message.uuid)

        self.view.setSigmetReminder(message.uuid, enabled)

    def removeReminder(self, uuid):
        """The user dismissed the alarm for a SIGMET that is already stored.

        Separate from setReminder because there is no message to read here:
        the due entry only carries the uuid. Passing the parser instead is what
        the old code did, and it raised AttributeError on every dismissal.
        """
        self.context.sigmet.remove(uuid)
        self.view.setSigmetReminder(uuid, False)


class MessagePresenter(QObject):
    """Incoming telegrams: store them, alert the user, and hand a message the
    API pushed in to the sender that can show it.

    Owns the message worker. The fetch runs off the GUI thread and hands its
    payload to the bridge, which is the only door into the context.
    """

    def __init__(self, view, context, conf, repositories, workers, bridge, parent=None):
        super().__init__(parent)
        self.view = view
        self.context = context
        self.conf = conf
        self.repositories = repositories
        self.workers = workers
        self.bridge = bridge

    def initialize(self):
        self.worker, self.thread = self.workers.create(
            MessageWorker, self.conf, workerId='message', reusable=True
        )
        self.worker.fetched.connect(self.bridge.updateMessage)
        self.worker.finished.connect(self.connectionLost)
        self.context.event.remoteMessageChanged.connect(self.store)
        self.context.event.otherMessageReceived.connect(self.presentCustom)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.poll)
        self.timer.start(60 * 1000)
        self.poll()

    def poll(self):
        if not self.thread.isRunning():
            self.thread.start()

    def store(self):
        types = subscribedTypes(self.conf.tafSpec, self.conf.sigmetEnabled)
        items = self.repositories.message.available(self.context.message.message(), types=types)
        alert = False

        for item in items:
            logger.info('{} {} {}'.format('Confirm' if item.id else 'Save', item.type, item.text))
            if item.type in ('SA', 'SP'):
                self.context.notification.metar.clear()
            else:
                alert = True
            self.repositories.message.add(item)

        if alert:
            self.view.updateSound('notification', True)
            self.view.closeReminder('taf')

    def presentCustom(self, message):
        """A message submitted through the API. Unlike a telegram it is not
        stored -- it goes straight to the custom sender for the operator."""
        self.view.handleCustomMessage(message)

    def connectionLost(self):
        """An empty payload means the fetch failed -- the client swallows the
        real error, so 'no data' and 'no connection' are indistinguishable
        here. Worth fixing in the client, not by guessing in the UI."""
        if self.context.message.message():
            return

        self.view.notify(
            QCoreApplication.translate('MainWindow', 'Connection Error'),
            QCoreApplication.translate('MainWindow', 'Unable to connect remote message data source, please check the settings or network status.'),
            'warning',
        )


class NotificationPresenter(QObject):
    """The live notification channel: a METAR or SIGMET that just arrived and
    has not been stored yet.

    METAR: clear the notification once the same observation has been stored,
    otherwise validate the trend group. SIGMET: refresh the editor's custom
    text and alert the user.

    Deliberately does not touch the trend sound. SoundPresenter owns every
    continuous channel, so there is exactly one writer per audio stream.
    """

    def __init__(self, view, context, repositories, parent=None):
        super().__init__(parent)
        self.view = view
        self.context = context
        self.repositories = repositories

    def initialize(self):
        self.context.event.notificationChanged.connect(self.notificationChanged)

    def notificationChanged(self, category):
        # category() also answers SPECI and AIRMET; matching only METAR and
        # SIGMET left those two notifications with no handler at all
        if category in ('METAR', 'SPECI'):
            self.reloadMetar()
        elif category in ('SIGMET', 'AIRMET'):
            self.notifySigmet()

    def reloadMetar(self):
        notification = self.context.notification.metar
        parser = notification.parser()
        metar = self.repositories.metar.latest()

        # An observation already in the database needs no notification
        if parser and metar and parser.isSameObservation(metar.text):
            notification.clear()
            return

        if parser and notification.validation():
            parser.validate()
            if parser.hasTrend() and not parser.isValid():
                self.context.flash.warning(
                    QCoreApplication.translate('MainWindow', 'Trend Validation Failed'),
                    QCoreApplication.translate('MainWindow', 'The trend has been cleared, please resend'),
                )

        self.context.event.trendReloadRequested.emit()

    def notifySigmet(self):
        self.view.renderSigmetText()

        if not self.context.notification.sigmet.message():
            return

        self.view.updateSound('incoming', True)
        self.view.notify(
            QCoreApplication.translate('MainWindow', 'Message Received'),
            QCoreApplication.translate('MainWindow', 'Received a {} message').format(
                self.context.notification.sigmet.category()
            ),
        )


class RecentEntryBuilder:
    """Query -> view models. No view, no widgets, no Qt: unit-testable as is.

    Querying, modelling, computing the map geometry and drawing the result all
    used to happen in one 47-line method. Only the last of those needs a
    widget, so only the last of them is left in the view.
    """

    def __init__(self, context, conf, repositories):
        self.context = context
        self.conf = conf
        self.repositories = repositories

    def build(self):
        parser = self.context.notification.metar.parser()
        entries = []

        if parser:
            parser.validate()
            entries.append(NotificationModel(
                created=self.context.notification.metar.created(),
                validations={
                    'html': parser.renderer(style='html'),
                    'tips': parser.tips,
                    'pass': parser.isValid(),
                    'validation': self.context.notification.metar.validation(),
                },
            ))

        for message in self.reviewables(parser):
            if message:
                entries.append(ReviewModel(
                    uuid=message.uuid,
                    type=message.type,
                    created=message.created,
                    message=message,
                    text=message.report,
                    geo=self.sigmetGeometry(message),
                ))

        return entries

    def reviewables(self, parser):
        messages = self.recentMessages()
        # The stored metar only shows while no live notification replaces it
        stored = [] if parser else [messages['metar']]
        return stored + [messages['trend'], messages['taf']] + messages['sigmets']

    def recentMessages(self):
        recent = utcnow() - datetime.timedelta(hours=24)
        spec = self.context.taf.spec.designator

        sigmets = []
        if self.conf.sigmetEnabled:
            sigmets = self.context.current.filterSigmets(SigmetFilter(includeCancelled=True))

        return self.repositories.message.recent(
            spec, recent,
            includeSigmet=self.conf.sigmetEnabled,
            currentSigmets=sigmets,
        )

    def sigmetGeometry(self, message):
        """Pre-render the SIGMET area features for the recent-board card."""
        if message.category not in ('SIGMET', 'AIRMET') or message.isCnl():
            return None

        try:
            parser = message.parser()
            geos = parser.geo(self.context.layer.boundaries(), trim=True)
            return geos if geos['features'] else None
        except Exception as e:
            logger.error('Failed to draw SIGMET area, {}, {}'.format(message.text, e))
            return None


class BoardPresenter(QObject):
    """Keeps everything that shows stored records in step with the database:
    the four tables, the recent board, and the monitor state the reminder
    policy reads (context.taf and context.current).

    The monitor feed lives here rather than in a class of its own because the
    two must happen in one order -- the recent board reads context.current, so
    the state has to be refreshed before the cards are built -- and splitting
    them would leave that order to be decided by connection order.
    """

    def __init__(self, view, context, conf, repositories, parent=None):
        super().__init__(parent)
        self.view = view
        self.context = context
        self.conf = conf
        self.repositories = repositories
        self.builder = RecentEntryBuilder(context, conf, repositories)

    def initialize(self):
        self.context.event.remoteMessageChanged.connect(self.refresh)
        self.context.event.notificationChanged.connect(self.render)
        self.context.event.currentSigmetChanged.connect(self.renderSigmetGraphic)
        self.view.notificationExpired.connect(self.expire)
        self.view.messageSent.connect(self.refresh)

        # Deliberately not refresh(): refreshing the TAF monitor state raises
        # context.taf.shouldRemind, which fires tafReminderTriggered and opens
        # the reminder dialog before the window has even settled. The original
        # startup never read the TAF status either, so this matches it.
        self.refreshSigmet()
        self.render()

    def refresh(self):
        """Read the database, push the monitor state, then draw."""
        self.refreshTaf()
        self.refreshSigmet()
        self.render()

    def refreshTaf(self):
        status = self.repositories.taf.status(
            self.context.taf.spec, delayMinutes=self.conf.delayMinutes
        )
        self.context.taf.setState(status)

    def refreshSigmet(self):
        try:
            sigmets = self.repositories.sigmet.current()
        except Exception as e:
            logger.error('Sigmet cannot be updated, {}'.format(e))
            return

        self.context.current.setState(sigmets)

    def renderSigmetGraphic(self):
        """context.current only announces a change when the set of SIGMETs
        actually differs, so this fires on real edits and not on every poll."""
        self.view.renderSigmetGraphic()

    def render(self, *args):
        entries = self.builder.build()
        self.view.renderTafBoard()
        self.view.renderTables()
        self.view.renderRecent(entries)

        # Reminder state lives in context.sigmet.entries; sync the bells
        for entry in entries:
            if entry.type in ('WS', 'WC', 'WV', 'WA'):
                self.view.setSigmetReminder(
                    entry.uuid, entry.uuid in self.context.sigmet.entries
                )

    def expire(self):
        """The notification card timed out; fall back to the stored METAR."""
        self.context.notification.metar.clear()
        self.render()


class SoundPresenter(QObject):
    """What the app sounds like.

    Ticked once a second, and the only writer of the two continuous channels.
    The old code had both singer() and loadMetar() calling trendSound
    play/stop -- two writers racing over one sound.
    """

    def __init__(self, view, context, conf, parent=None):
        super().__init__(parent)
        self.view = view
        self.context = context
        self.conf = conf

    def initialize(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(1000)

    def tick(self):
        self.view.updateSound('trend', self.isTrendActive())
        self.view.updateSound('alarm', self.isAlarmActive())

    def isTrendActive(self):
        if not self.conf.remindTrend:
            return False
        if self.context.notification.metar.message():
            return True
        return utcnow().minute in (57, 58, 59)

    def isAlarmActive(self):
        return self.view.alarmEnabled() and self.context.taf.isExpired()


class LayerPresenter(QObject):
    """FIR layers: fetch them in the background, then tell the editor."""

    def __init__(self, view, context, conf, workers, bridge, parent=None):
        super().__init__(parent)
        self.view = view
        self.context = context
        self.conf = conf
        self.workers = workers
        self.bridge = bridge

    def initialize(self):
        self.worker, self.thread = self.workers.create(
            LayerWorker, self.conf, workerId='layer', reusable=True
        )
        self.worker.fetched.connect(self.bridge.updateLayer)
        self.thread.finished.connect(self.refresh)
        self.context.event.layerRefreshRequested.connect(self.poll)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.poll)
        self.timer.start(2 * 60 * 1000)
        self.poll()

    def poll(self):
        if self.conf.layerUrl and not self.thread.isRunning():
            self.thread.start()

    def refresh(self):
        self.view.renderLayer()

        if not self.conf.layerUrl or self.context.layer.currentLayers():
            return

        self.view.notify(
            QCoreApplication.translate('MainWindow', 'Connection Error'),
            QCoreApplication.translate('MainWindow', 'Unable to connect FIR information data source, please check the settings or network status.'),
            'warning',
        )


class LicensePresenter(QObject):
    """Keeps the license menu in step with the stored license.

    The 'enter a key' entry needs no context at all, so it stays a plain
    window action; only removal and the menu state live here.
    """

    def __init__(self, view, context, parent=None):
        super().__init__(parent)
        self.view = view
        self.context = context

    def initialize(self):
        self.view.removeLicenseAction.triggered.connect(self.remove)
        self.view.licenseChanged.connect(self.updateMenu)
        self.updateMenu()

    def updateMenu(self):
        self.view.setLicenseMenuState(bool(self.context.license.license()))

    def remove(self):
        title = QCoreApplication.translate('MainWindow', 'Remove license key? ')
        text = QCoreApplication.translate('MainWindow', 'Remove license key? This will revert tafor to an unregistered state.')
        if self.view.confirm(title, text):
            self.view.removeLicense()


class UpgradePresenter(QObject):
    """Check for a newer release and offer to download it."""

    def __init__(self, view, workers, parent=None):
        super().__init__(parent)
        self.view = view
        self.workers = workers

    def initialize(self):
        self.view.checkUpgradeAction.triggered.connect(self.check)

        self.worker, self.thread = self.workers.create(
            CheckUpgradeWorker, workerId='upgrade', reusable=True
        )
        self.worker.done.connect(self.report)

    def check(self):
        if not self.thread.isRunning():
            self.thread.start()

    def report(self, data):
        title = QCoreApplication.translate('MainWindow', 'Check for Updates')
        release = data.get('tag_name')

        if not release:
            self.view.notify(title, QCoreApplication.translate('MainWindow', 'Unable to get the latest version information.'))
            return

        if not checkVersion(release, __version__):
            self.view.notify(title, QCoreApplication.translate('MainWindow', 'The current version is already the latest version.'))
            return

        text = QCoreApplication.translate('MainWindow', 'New version found {}, do you want to download now?').format(release)
        if self.view.confirm(title, text):
            QDesktopServices.openUrl(QUrl('https://github.com/up1and/tafor/releases'))


class MainWindow(QMainWindow, Ui_main.Ui_MainWindow):
    """The window itself. It is handed conf, context and the repositories so
    that the widgets it builds can be given them, and for nothing else."""

    # Signals for the presenters, under the window's own names: three child
    # signals passed through, and the three senders merged into messageSent.
    notificationExpired = pyqtSignal()
    reminderToggled = pyqtSignal(object, bool)
    licenseChanged = pyqtSignal()
    messageSent = pyqtSignal()

    def __init__(self, conf, context, repositories, parent=None):
        super().__init__(parent)
        self.conf = conf
        self.context = context
        self.setupUi(self)

        self.sysInfo = QSysInfo.prettyProductName()
        self.repositories = repositories

        self.setupFrame()
        self.setupReminders()
        self.setupSenders()
        self.setupEditors()
        self.setupRecent()
        self.setupTables()
        self.setupSounds()
        self.setupTray()
        self.bindSignal()

    def setupFrame(self):
        self.setWindowIcon(QIcon(iconPath('logo.png')))

        # White content background via palette
        self.scrollContents.setAutoFillBackground(True)
        palette = self.scrollContents.palette()
        palette.setColor(self.scrollContents.backgroundRole(), QColor('white'))
        self.scrollContents.setPalette(palette)

        if not self.conf.sigmetEnabled:
            self.sigmetAction.setVisible(False)
            # Remove by widget identity: a literal index silently deletes the
            # wrong tab when the page order changes in Designer
            for page in (self.sigmetTab, self.airmetTab):
                index = self.mainTab.indexOf(page)
                if index != -1:
                    self.mainTab.removeTab(index)

    def setupReminders(self):
        """One alarm dialog per kind. The kind is also the sound to play."""
        self.reminders = {
            'taf': RemindMessageBox(self),
            'sigmet': RemindMessageBox(self),
        }

    def setupSenders(self):
        repository = self.repositories.message
        self.settingDialog = SettingDialog(self, self.conf, self.context)
        self.tafSender = TafSender(self, self.context, self.conf, repository=repository)
        self.trendSender = TrendSender(self, self.context, self.conf, repository=repository)
        self.sigmetSender = SigmetSender(self, self.context, self.conf, repository=repository)
        self.customSender = CustomSender(self, self.context, self.conf, repository=repository)

    def setupEditors(self):
        self.tafEditor = TafEditor(self, self.tafSender, self.conf, self.context,
                                   repository=self.repositories.taf)
        self.trendEditor = TrendEditor(self, self.trendSender, self.conf, self.context)
        self.sigmetEditor = SigmetEditor(self, self.sigmetSender, self.conf, self.context,
                                         repository=self.repositories.sigmet)
        self.licenseEditor = LicenseEditor(self, conf=self.conf, context=self.context)
        self.chartViewer = ChartViewer(self, repository=self.repositories.metar)

    def setupRecent(self):
        self.clock = Clock(self, self.tipsLayout, context=self.context)
        self.tipsLayout.addSpacerItem(
            QSpacerItem(10, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))
        self.tafBoard = TafBoard(self, self.tipsLayout, conf=self.conf, context=self.context)

        self.recentBoard = RecentBoard(self, conf=self.conf)
        self.scrollLayout.insertWidget(1, self.recentBoard)
        self.scrollLayout.setAlignment(Qt.AlignTop)

    def setupTables(self):
        self.tafTable = TafTable(self, self.tafLayout, reviewer=self.tafSender,
                                 conf=self.conf, context=self.context,
                                 repository=self.repositories.taf)
        self.metarTable = MetarTable(self, self.metarLayout, conf=self.conf,
                                     context=self.context, repository=self.repositories.metar)
        self.sigmetTable = SigmetTable(self, self.sigmetLayout, reviewer=self.sigmetSender,
                                       conf=self.conf, context=self.context,
                                       repository=self.repositories.sigmet)
        self.airmetTable = AirmetTable(self, self.airmetLayout, reviewer=self.sigmetSender,
                                       conf=self.conf, context=self.context,
                                       repository=self.repositories.sigmet)

    def setupSounds(self):
        conf = self.conf
        self.sounds = {
            'notification': Sound('notification.wav', loop=False),
            'incoming': Sound('notification-incoming.wav', loop=False),
            'alarm': Sound('alarm.wav', volume=lambda: conf.alarmVolume),
            'taf': Sound('taf.wav', volume=lambda: conf.tafVolume),
            'trend': Sound('trend.wav', volume=lambda: conf.trendVolume),
            'sigmet': Sound('sigmet.wav', volume=lambda: conf.sigmetVolume),
        }

        # A slider previews its own sound at the volume it is being dragged to,
        # which is why the preview takes the control's value and not the one
        # the channel falls back on
        for name in ('alarm', 'taf', 'trend', 'sigmet'):
            control = getattr(self.settingDialog, name + 'Volume')
            control.valueChanged.connect(self.sounds[name].preview)

    def setupTray(self):
        self.tray = QSystemTrayIcon(self)
        self.setTrayIcon(self.trayStyle())
        self.tray.show()

        self.trayMenu = QMenu(self)
        self.trayMenu.addAction(self.settingAction)
        self.trayMenu.addAction(self.aboutAction)
        self.trayMenu.addSeparator()
        self.trayMenu.addAction(self.quitAction)
        self.tray.setContextMenu(self.trayMenu)
        self.tray.setToolTip('Tafor {}'.format(__version__))

    def trayStyle(self):
        if self.sysInfo.startswith(('Windows 10', 'Windows 11', 'Ubuntu')):
            return 'light'
        if self.sysInfo.startswith('macOS'):
            return 'dark'
        return 'normal'

    def bindSignal(self):
        """Signals the window can handle itself: no state, no services.

        Everything that needs the context or a worker is connected by the
        presenter that owns it.
        """
        self.tafAction.triggered.connect(self.tafEditor.show)
        self.trendAction.triggered.connect(self.trendEditor.show)
        self.sigmetAction.triggered.connect(self.sigmetEditor.show)

        self.settingAction.triggered.connect(self.openSetting)
        self.settingAction.setIcon(QIcon(iconPath('setting.png')))
        self.openDocsAction.triggered.connect(self.openDocs)
        self.reportIssueAction.triggered.connect(self.openIssueTracker)
        self.aboutAction.triggered.connect(self.showAbout)
        self.enterLicenseAction.triggered.connect(self.licenseEditor.enter)

        self.tray.activated.connect(self.showNormal)
        self.tray.messageClicked.connect(self.showNormal)
        if self.sysInfo.startswith('macOS'):
            self.trayMenu.aboutToShow.connect(lambda: self.setTrayIcon('light'))
            self.trayMenu.aboutToHide.connect(lambda: self.setTrayIcon('dark'))

        self.metarTable.chartClicked.connect(self.chartViewer.show)

        # A sent message changes what the tables and the board should show
        for sender in (self.tafSender, self.trendSender, self.sigmetSender):
            sender.succeeded.connect(self.messageSent)

        # Re-emit the child signals the presenters subscribe to
        self.recentBoard.expired.connect(self.notificationExpired)
        self.recentBoard.reminderToggled.connect(self.reminderToggled)
        self.licenseEditor.licenseChanged.connect(self.licenseChanged)
        self.recentBoard.reviewRequested.connect(self.review)
        self.recentBoard.replyRequested.connect(self.trendEditor.edit)

        self.conf.restartRequired.connect(self.restart)
        self.conf.reloadRequired.connect(self.closeSenders)

    def setTrayIcon(self, style='normal'):
        files = {
            'dark': iconPath('logo-dark.png'),
            'light': iconPath('logo-light.png'),
            'normal': iconPath('logo.png'),
        }
        icon = QIcon(files.get(style, files['normal']))
        if style == 'dark':
            icon.setIsMask(True)
        self.tray.setIcon(icon)

    def reminderVisible(self, kind):
        return self.reminders[kind].isVisible()

    def showReminder(self, kind, text):
        """Ask the user about a message that is due, and hand back the button
        they pressed: the caller compares it with QMessageBox.AcceptRole."""
        box = self.reminders[kind]
        sound = self.sounds[kind]

        sound.play()
        box.setText(text)
        answer = box.exec()
        if not box.isVisible():
            sound.stop()

        return answer

    def closeReminder(self, kind):
        self.reminders[kind].close()

    def setSigmetReminder(self, uuid, enabled):
        self.recentBoard.setReminderEnabled(uuid, enabled)

    def updateSound(self, name, playing):
        """Turn one channel on or off.

        The alarms and the two reminder dialogs loop until something stops
        them; the notification and incoming alerts play once. Which is which
        is now a property of the channel, so this only has to say play or
        stop. Each sound still has exactly one writer.
        """
        sound = self.sounds[name]
        if playing:
            sound.play()
        else:
            sound.stop()

    def alarmEnabled(self):
        return self.warnTafAction.isChecked()

    def renderTafBoard(self):
        self.tafBoard.updateGui()

    def renderTables(self):
        for table in (self.tafTable, self.metarTable, self.sigmetTable, self.airmetTable):
            table.updateGui()

    def renderRecent(self, entries):
        self.recentBoard.sync(entries)

    def renderLayer(self):
        self.sigmetEditor.updateLayer()

    def renderSigmetGraphic(self):
        self.sigmetEditor.updateGraphicCanvas()

    def renderSigmetText(self):
        self.sigmetEditor.updateCustomText()

    def notify(self, title, text, level='information'):
        icons = ['noicon', 'information', 'warning', 'critical']
        icon = QSystemTrayIcon.MessageIcon(icons.index(level))
        self.tray.showMessage(title, text, icon)

    def status(self, text, timeout=5000):
        self.statusBar.showMessage(text, timeout)

    def confirm(self, title, text):
        return QMessageBox.question(self, title, text) == QMessageBox.Yes

    def handleCustomMessage(self, message):
        self.ensureVisible()
        self.updateSound('incoming', True)
        self.customSender.receive(message)
        self.customSender.show()
        self.notify(
            QCoreApplication.translate('MainWindow', 'Message Received'),
            QCoreApplication.translate('MainWindow', 'Received a custom message.'),
        )

    def setLicenseMenuState(self, registered):
        self.enterLicenseAction.setVisible(not registered)
        self.removeLicenseAction.setVisible(registered)

    def removeLicense(self):
        self.licenseEditor.removeLicense()

    def ensureVisible(self):
        if not self.isVisible():
            self.showNormal()

    def openSetting(self):
        self.ensureVisible()
        self.settingDialog.reopen()

    def showAbout(self):
        title = QCoreApplication.translate('MainWindow', 'About')
        license = self.context.license.license()
        if license:
            register = QCoreApplication.translate('MainWindow', '{} days remaining').format(
                license.remaining if license.remaining is not None else 0)
        else:
            register = QCoreApplication.translate('MainWindow', 'Unregistered')
        html = """
        <div style="text-align:center">
        <img src="{logo}">
        <h2 style="margin:5px 0">Tafor</h2>
        <p style="margin:0;color:#444;font-size:13px">A Terminal Aerodrome Forecast Encoding Software</p>
        <p style="margin:5px 0"><a href="https://github.com/up1and/tafor" style="text-decoration:none;color:#0078d7">{} {} {}</a></p>
        <p style="margin:5px 0;color:#444">{}</p>
        <p style="margin-top:25px;color:#444">Copyright © 2022 <a href="mailto:piratecb@gmail.com" style="text-decoration:none;color:#444">up1and</a></p>
        </div>
        """.format(QCoreApplication.translate('MainWindow', 'Version'), __version__, revision(), register,
            logo=QUrl.fromLocalFile(iconPath('logo.png')).toString())

        box = QMessageBox(self)
        box.setWindowTitle(title)
        box.setTextFormat(Qt.RichText)
        box.setText(html)
        layout = box.layout()
        if layout.itemAt(0).spacerItem():
            layout.takeAt(0)
        box.addButton(QMessageBox.Ok)
        self.ensureVisible()
        box.exec()

    def openDocs(self):
        devDocs = os.path.join(root, '../docs/_build/html/index.html')
        releaseDocs = os.path.join(root, 'docs/_build/html/index.html')

        if os.path.exists(devDocs):
            url = QUrl.fromLocalFile(devDocs)
        elif os.path.exists(releaseDocs):
            url = QUrl.fromLocalFile(releaseDocs)
        else:
            url = QUrl('https://tafor.readthedocs.io')

        QDesktopServices.openUrl(url)

    def openIssueTracker(self):
        QDesktopServices.openUrl(QUrl('https://github.com/up1and/tafor/issues'))

    def restart(self):
        title = QCoreApplication.translate('Settings', 'Restart Required')
        text = QCoreApplication.translate(
            'Settings', 'Program need to restart to apply the configuration, do you wish to restart now?')
        if QMessageBox.information(self, title, text, QMessageBox.Yes | QMessageBox.No) == QMessageBox.No:
            return

        program = sys.executable
        args = [] if hasattr(sys, '_MEIPASS') else [os.path.join(root, '__main__.py')]
        args.extend(restartArgs())

        if not QProcess.startDetached(program, args):
            self.notify(title, QCoreApplication.translate(
                'Settings', 'Could not restart automatically, please start tafor again.'), 'warning')

    def closeSenders(self):
        for sender in (self.tafSender, self.trendSender, self.sigmetSender):
            sender.close()

    def closeDialogs(self):
        """Close every dialog the app owns, in one pass.

        Nothing gets Qt.WA_DeleteOnClose: the reminder boxes and the custom
        sender are closed and then handed back to the user, so deleting them
        on close would leave a dangling C++ object behind. Shutdown runs once
        the event loop has returned, on the way out of the process, so there
        is nothing to gain by destroying them early either.
        """
        for dialog in (
            self.tafSender, self.trendSender, self.sigmetSender, self.customSender,
            self.tafEditor, self.trendEditor, self.sigmetEditor, self.licenseEditor,
            self.settingDialog, self.chartViewer,
            *self.reminders.values(),
        ):
            dialog.close()

    def hideTray(self):
        self.tray.hide()

    def review(self, model):
        """Open the right sender for a card the user asked to review."""
        if model.type in ('FC', 'FT'):
            sender = self.tafSender
        elif model.type in ('WS', 'WC', 'WV', 'WA'):
            sender = self.sigmetSender
        else:
            return

        sender.receive(model.message)
        sender.show()

    def event(self, event):
        if event.type() == QEvent.WindowStateChange and self.isMinimized():
            # The window is already minimised; take it off the taskbar
            self.setWindowFlags(self.windowFlags() & Qt.Tool)
            self.tray.show()
            return True
        return super().event(event)

    def closeEvent(self, event):
        """Closing the window hides it; only a real quit tears things down."""
        if event.spontaneous():
            event.ignore()
            self.hide()
        else:
            event.accept()
