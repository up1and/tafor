import os
import sys
import json
import logging
import datetime

from uuid import uuid4

from PyQt5.QtGui import QIcon, QDesktopServices, QGuiApplication
from PyQt5.QtCore import QCoreApplication, QTranslator, QLocale, QEvent, QObject, QTimer, Qt, QUrl, QSysInfo, QProcess
from PyQt5.QtWidgets import (QMainWindow, QApplication, QSpacerItem, QSizePolicy,
        QSystemTrayIcon, QMenu, QMessageBox, QStyleFactory)
from PyQt5.QtNetwork import QLocalSocket, QLocalServer

from tafor import __version__, conf, root, context
from tafor.core.models import Metar, db
from tafor.core.utils.check import createTafStatus, findAvailables
from tafor.core.utils.common import checkVersion
from tafor.core.utils.query import SigmetFilter, currentSigmet, latestMetar, recentMessages
from tafor.core.utils.thread import (
    CheckUpgradeWorker,
    LayerWorker,
    MessageWorker,
    RpcWorker,
    threadManager,
)
from tafor.ui.components.chart import ChartViewer
from tafor.ui.components.send import CustomSender, SigmetSender, TafSender, TrendSender
from tafor.ui.components.setting import SettingDialog
from tafor.ui.components.sigmet import SigmetEditor
from tafor.ui.components.taf import TafEditor
from tafor.ui.components.trend import TrendEditor
from tafor.ui.qt import Ui_main, main_rc
from tafor.ui.widgets.misc import Clock, LicenseEditor, RecentMessage, RemindMessageBox, TafBoard
from tafor.ui.widgets.sound import Sound
from tafor.ui.widgets.table import AirmetTable, MetarTable, SigmetTable, TafTable

logger = logging.getLogger('tafor.main')


class MainPresenter(QObject):

    def __init__(self, view, context, conf):
        super(MainPresenter, self).__init__(view)
        self.view = view
        self.context = context
        self.conf = conf
        self.setupTimers()
        self.setupThreads()

    def initialize(self):
        self.worker()
        self.painter()
        self.updateSigmet()
        self.updateTable()
        self.updateRecent()
        self.updateRegisterMenu()

    def setupTimers(self):
        self.clockTimer = QTimer(self)
        self.clockTimer.timeout.connect(self.singer)
        self.clockTimer.start(1 * 1000)

        self.workerTimer = QTimer(self)
        self.workerTimer.timeout.connect(self.worker)
        self.workerTimer.start(60 * 1000)

        self.painterTimer = QTimer(self)
        self.painterTimer.timeout.connect(self.painter)
        self.painterTimer.start(2 * 60 * 1000)

    def setupThreads(self):
        self.messageWorker, self.messageThread = threadManager.createWorker(MessageWorker, workerId='message', reusable=True)
        self.messageWorker.finished.connect(self.notifier)

        self.layerWorker, self.layerThread = threadManager.createWorker(LayerWorker, workerId='layer', reusable=True)
        self.layerThread.finished.connect(self.updateLayer)

        self.checkUpgradeWorker, self.checkUpgradeThread = threadManager.createWorker(
            CheckUpgradeWorker, workerId='upgrade', reusable=True
        )
        self.checkUpgradeWorker.done.connect(self.checkUpgrade)

    def loadMetar(self):
        parser = self.context.notification.metar.parser()
        metar = latestMetar()

        if parser:
            self.view.trendSound.play()
        else:
            self.view.trendSound.stop()

        isSimilar = parser and metar and parser.isSimilar(metar.text)
        if isSimilar:
            self.context.notification.metar.clear()
            return

        if parser and self.context.notification.metar.validation():
            parser.validate()
            if parser.hasTrend() and not parser.isValid():
                title = QCoreApplication.translate('MainWindow', 'Trend Validation Failed')
                description = QCoreApplication.translate('MainWindow', 'The trend has been cleared, please resend')
                self.context.flash.warning(title, description)

        self.updateRecent()
        self.view.trendSender.reload()

    def updateMessage(self):
        wishlist = ['SA', 'SP']
        if self.conf.tafSpec:
            wishlist.append('FT')
        else:
            wishlist.append('FC')

        if self.conf.sigmetEnabled:
            wishlist.extend(['WS', 'WC', 'WV', 'WA'])

        messages = self.context.message.message()
        items = findAvailables(messages, wishlist=wishlist)
        needPlaySound = False

        with db.session() as session:
            for item in items:
                if item.id:
                    logger.info('Confirm {} {}'.format(item.type, item.text))
                else:
                    logger.info('Save {} {}'.format(item.type, item.text))

                if item.type in ['SA', 'SP']:
                    self.context.notification.metar.clear()
                else:
                    needPlaySound = True

                session.add(item)

        if needPlaySound:
            self.view.notificationSound.play(loop=False)
            self.view.remindTafBox.close()

        self.updateGui()

    def updateTaf(self):
        status = createTafStatus(self.context.taf.spec)
        self.context.taf.setState(status)

    def updateSigmet(self):
        try:
            sigmets = currentSigmet()
            self.context.current.setState(sigmets)
        except Exception as e:
            logger.error('Sigmet cannot be updated, {}'.format(e))

    def updateGui(self):
        self.updateTaf()
        self.updateSigmet()
        self.updateTable()
        self.updateRecent()
        self.remindSigmet()

    def updateRecent(self):
        self.view.tafBoard.updateGui()

        recent = datetime.datetime.utcnow() - datetime.timedelta(hours=24)
        spec = self.context.taf.spec[:2].upper()

        sigmets = []
        if self.conf.sigmetEnabled:
            sigmets = self.context.current.filterSigmets(SigmetFilter(includeCancelled=True))

        messages = recentMessages(spec, recent, includeSigmet=self.conf.sigmetEnabled, currentSigmets=sigmets)
        metar = self.notificationMetar()
        if metar:
            messages['metar'] = metar

        data = list(filter(None, [
            messages['metar'],
            messages['trend'],
            messages['taf'],
        ] + messages['sigmets']))
        self.view.renderRecentMessages(data)

    def notificationMetar(self):
        parser = self.context.notification.metar.parser()
        if not parser:
            return None

        uuid = str(uuid4())
        created = self.context.notification.metar.created()
        validation = self.context.notification.metar.validation()
        metar = Metar(uuid=uuid, text=parser.message, created=created)
        parser.validate()
        metar.validations = {
            'html': parser.renderer(style='html', showDiff=True),
            'tips': parser.tips,
            'pass': parser.isValid(),
            'validation': validation
        }
        return metar

    def updateTable(self):
        self.view.tafTable.updateGui()
        self.view.metarTable.updateGui()
        self.view.sigmetTable.updateGui()
        self.view.airmetTable.updateGui()

    def remindTaf(self):
        remindSwitch = self.conf.remindTaf
        if not remindSwitch or self.view.isReminderVisible(self.view.remindTafBox):
            return None

        type = self.context.taf.spec[:2].upper()
        period = self.context.taf.period()

        if self.context.taf.shouldRemind():
            current = type + period[2:4] + period[7:]
            text = QCoreApplication.translate('MainWindow', 'Time to issue {}').format(current)
            ret = self.view.showReminder(self.view.remindTafBox, self.view.tafSound, text)
            if ret == QMessageBox.RejectRole:
                QTimer.singleShot(1000 * 60 * 5, self.remindTaf)

    def remindSigmet(self):
        remindSwitch = self.conf.remindSigmet
        if not remindSwitch or self.view.isReminderVisible(self.view.remindSigmetBox):
            return None

        outdates = self.context.sigmet.outdate()
        for item in outdates:
            sig = item['text']
            mark = '{} {}'.format(sig.reportType(), sig.sequence())
            text = QCoreApplication.translate('MainWindow', 'Time to update {}').format(mark)
            ret = self.view.showReminder(self.view.remindSigmetBox, self.view.sigmetSound, text)
            if ret == QMessageBox.AcceptRole:
                self.setSigmetReminder(sig, False)
            else:
                time = item['time'] + datetime.timedelta(minutes=5)
                self.context.sigmet.update(item['uuid'], time)

    def setSigmetReminder(self, message, enabled):
        if enabled:
            time = message.expired()
            sig = message.parser()
            self.context.sigmet.add(message.uuid, sig, time)
        else:
            self.context.sigmet.remove(message.uuid)

        self.view.setRecentMessageReminder(message.uuid, enabled)

    def updateRegisterMenu(self):
        registered = self.context.license.license()
        self.view.enterLicenseAction.setVisible(not registered)
        self.view.removeLicenseAction.setVisible(registered)

    def singer(self):
        warnSwitch = self.view.warnTafAction.isChecked()
        trendSwitch = self.conf.remindTrend

        utc = datetime.datetime.utcnow()
        if trendSwitch and (utc.minute in (57, 58, 59) or self.context.notification.metar.message()):
            self.view.trendSound.play()
        else:
            self.view.trendSound.stop()

        if warnSwitch and self.context.taf.isExpired():
            self.view.alarmSound.play()
        else:
            self.view.alarmSound.stop()

    def worker(self):
        if not self.messageThread.isRunning():
            self.messageThread.start()

    def painter(self):
        if self.conf.layerUrl and not self.layerThread.isRunning():
            self.layerThread.start()

    def notifier(self):
        connectionError = QCoreApplication.translate('MainWindow', 'Connection Error')
        if not self.context.message.message():
            self.context.flash.warning(
                connectionError,
                QCoreApplication.translate('MainWindow', 'Unable to connect remote message data source, please check the settings or network status.')
            )

        if self.conf.layerUrl and not self.context.layer.currentLayers() and not self.layerThread.isRunning():
            self.context.flash.warning(
                connectionError,
                QCoreApplication.translate('MainWindow', 'Unable to connect FIR information data source, please check the settings or network status.')
            )

    def updateLayer(self):
        self.view.sigmetEditor.updateLayer()

    def loadCustomMessage(self):
        self.view.ensureVisible()
        self.view.incomingSound.play(loop=False)
        self.view.customSender.load()
        self.view.customSender.show()

        self.context.flash.info(
            QCoreApplication.translate('MainWindow', 'Message Received'),
            QCoreApplication.translate('MainWindow', 'Received a custom message.')
        )

    def handleNotificationChange(self, notificationType):
        if notificationType == 'metar':
            self.loadMetar()

        if notificationType == 'sigmet':
            self.view.sigmetEditor.updateCustomText()
            message = self.context.notification.sigmet.message()
            if message:
                self.view.incomingSound.play(loop=False)
                self.context.flash.info(
                    QCoreApplication.translate('MainWindow', 'Message Received'),
                    QCoreApplication.translate('MainWindow', 'Received a {} message').format(
                        self.context.notification.sigmet.getMessageType()
                    )
                )

    def openSetting(self):
        self.view.ensureVisible()
        self.view.settingDialog.exec_()

    def about(self):
        title = QCoreApplication.translate('MainWindow', 'About')
        register = QCoreApplication.translate('MainWindow', '{} days remaining').format(
            self.context.license.exp
        ) if self.context.license.license() else QCoreApplication.translate('MainWindow', 'Unregistered')
        html = """
        <div style="text-align:center">
        <img src=":/logo.png">
        <h2 style="margin:5px 0">Tafor</h2>
        <p style="margin:0;color:#444;font-size:13px">A Terminal Aerodrome Forecast Encoding Software</p>
        <p style="margin:5px 0"><a href="https://github.com/up1and/tafor" style="text-decoration:none;color:#0078d7">{} {} {}</a></p>
        <p style="margin:5px 0;color:#444">{}</p>
        <p style="margin-top:25px;color:#444">Copyright © 2022 <a href="mailto:piratecb@gmail.com" style="text-decoration:none;color:#444">up1and</a></p>
        </div>
        """.format(QCoreApplication.translate('MainWindow', 'Version'), __version__, self.context.info.ghash(), register)

        aboutBox = QMessageBox(self.view)
        aboutBox.setText(html)
        aboutBox.setWindowTitle(title)
        layout = aboutBox.layout()
        layout.removeItem(layout.itemAt(0))
        aboutBox.addButton(QMessageBox.Ok)
        self.view.ensureVisible()
        aboutBox.exec()

    def checkUpgrade(self, data):
        title = QCoreApplication.translate('MainWindow', 'Check for Updates')
        release = data.get('tag_name')
        if not release:
            text = QCoreApplication.translate('MainWindow', 'Unable to get the latest version information.')
            QMessageBox.information(self.view, title, text)
            return False

        hasNewVersion = checkVersion(release, __version__)
        if not hasNewVersion:
            text = QCoreApplication.translate('MainWindow', 'The current version is already the latest version.')
            QMessageBox.information(self.view, title, text)
            return False

        download = 'https://github.com/up1and/tafor/releases'
        text = QCoreApplication.translate('MainWindow', 'New version found {}, do you want to download now?').format(data.get('tag_name'))
        ret = QMessageBox.question(self.view, title, text)
        if ret == QMessageBox.Yes:
            QDesktopServices.openUrl(QUrl(download))

    def removeLicense(self):
        title = QCoreApplication.translate('MainWindow', 'Remove license key? ')
        text = QCoreApplication.translate('MainWindow', 'Remove license key? This will revert tafor to an unregistered state.')
        ret = QMessageBox.question(self.view, title, text)
        if ret == QMessageBox.Yes:
            self.view.licenseEditor.removeLicense()

    def shutdown(self):
        self.clockTimer.stop()
        self.workerTimer.stop()
        self.painterTimer.stop()

        for widget in [
            self.view.tafSender,
            self.view.trendSender,
            self.view.sigmetSender,
            self.view.tafEditor,
            self.view.trendEditor,
            self.view.sigmetEditor,
            self.view.licenseEditor,
            self.view.settingDialog,
            self.view.chartViewer
        ]:
            widget.setAttribute(Qt.WA_DeleteOnClose)

        for widget in [
            self.view.tafSender,
            self.view.trendSender,
            self.view.sigmetSender,
            self.view.customSender,
            self.view.tafEditor,
            self.view.trendEditor,
            self.view.sigmetEditor,
            self.view.licenseEditor,
            self.view.settingDialog,
            self.view.chartViewer,
            self.view.remindTafBox,
            self.view.remindSigmetBox
        ]:
            widget.close()

        self.view.tray.hide()


class MainWindow(QMainWindow, Ui_main.Ui_MainWindow):

    def __init__(self, conf, context parent=None):
        super(MainWindow, self).__init__(parent)
        self.conf = conf
        self.context = context
        self.setupUi(self)
        self.presenter = MainPresenter(self, context, conf)
        self.sysInfo = QSysInfo.prettyProductName()

        self.setup()
        self.bindSignal()
        self.presenter.initialize()

    def setup(self):
        self.setWindowIcon(QIcon(':/logo.png'))

        self.remindTafBox = RemindMessageBox(self)
        self.remindSigmetBox = RemindMessageBox(self)

        # 初始化窗口
        self.settingDialog = SettingDialog(self)

        self.tafSender = TafSender(self)
        self.trendSender = TrendSender(self)
        self.sigmetSender = SigmetSender(self)
        self.customSender = CustomSender(self)

        self.tafEditor = TafEditor(self, self.tafSender)
        self.trendEditor = TrendEditor(self, self.trendSender)
        self.sigmetEditor = SigmetEditor(self, self.sigmetSender)
        self.licenseEditor = LicenseEditor(self)

        self.chartViewer = ChartViewer(self)

        if not self.conf.sigmetEnabled:
            self.sigmetAction.setVisible(False)
            self.mainTab.removeTab(3)
            self.mainTab.removeTab(3)

        self.setupRecent()
        self.setupTable()
        self.setupSysTray()
        self.setupSound()

    def bindSignal(self):
        self.context.event.remoteMessageChanged.connect(self.presenter.updateMessage)
        self.context.event.tafReminderTriggered.connect(self.presenter.remindTaf)
        self.context.event.otherMessageReceived.connect(self.presenter.loadCustomMessage)
        self.context.event.notificationChanged.connect(self.presenter.handleNotificationChange)
        self.context.event.currentSigmetChanged.connect(self.sigmetEditor.updateGraphicCanvas)
        self.context.event.layerRefreshRequested.connect(self.presenter.painter)
        self.context.event.systemMessage.connect(self.showSystemNotification)
        self.context.event.statusbarMessage.connect(self.showStatusbarNotification)

        self.conf.restartRequired.connect(self.restart)
        self.conf.reloadRequired.connect(self.closeSender)

        # 连接菜单信号
        self.tafAction.triggered.connect(self.tafEditor.show)
        self.trendAction.triggered.connect(self.trendEditor.show)
        self.sigmetAction.triggered.connect(self.sigmetEditor.show)

        # 连接设置对话框的槽
        self.settingAction.triggered.connect(self.presenter.openSetting)
        self.settingAction.setIcon(QIcon(':/setting.png'))

        self.openDocsAction.triggered.connect(self.openDocs)
        self.reportIssueAction.triggered.connect(self.reportIssue)
        self.checkUpgradeAction.triggered.connect(self.presenter.checkUpgradeThread.start)
        self.enterLicenseAction.triggered.connect(self.licenseEditor.enter)
        self.removeLicenseAction.triggered.connect(self.presenter.removeLicense)
        self.aboutAction.triggered.connect(self.presenter.about)

        self.tray.activated.connect(self.showNormal)
        self.tray.messageClicked.connect(self.showNormal)
        if self.sysInfo.startswith('macOS'):
            self.trayMenu.aboutToShow.connect(lambda: self.setTrayIcon('light'))
            self.trayMenu.aboutToHide.connect(lambda: self.setTrayIcon('dark'))

        self.tafSender.succeeded.connect(self.presenter.updateGui)
        self.trendSender.succeeded.connect(self.presenter.updateGui)
        self.sigmetSender.succeeded.connect(self.presenter.updateGui)

        self.licenseEditor.licenseChanged.connect(self.presenter.updateRegisterMenu)

        self.metarTable.chartClicked.connect(self.chartViewer.show)

    def setTrayIcon(self, style='normal'):
        files = {
            'dark': ':/logo-dark.png',
            'light': ':/logo-light.png',
            'normal': ':/logo.png'
        }
        file = files.get(style, ':/logo.png')
        icon = QIcon(file)
        if style == 'dark':
            icon.setIsMask(True)
        self.tray.setIcon(icon)

    def setupRecent(self):
        self.clock = Clock(self, self.tipsLayout)
        self.tipsLayout.addSpacerItem(QSpacerItem(10, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))
        self.tafBoard = TafBoard(self, self.tipsLayout)
        self.scrollLayout.setAlignment(Qt.AlignTop)

    def setupTable(self):
        self.tafTable = TafTable(self, self.tafLayout)
        self.metarTable = MetarTable(self, self.metarLayout)
        self.sigmetTable = SigmetTable(self, self.sigmetLayout)
        self.airmetTable = AirmetTable(self, self.airmetLayout)

    def setupSysTray(self):
        self.tray = QSystemTrayIcon(self)
        if self.sysInfo.startswith('Windows 10') or self.sysInfo.startswith('Ubuntu'):
            style = 'light'
        elif self.sysInfo.startswith('macOS'):
            style = 'dark'
        else:
            style = 'normal'
        self.setTrayIcon(style)
        self.tray.show()

        self.trayMenu = QMenu(self)
        self.trayMenu.addAction(self.settingAction)
        self.trayMenu.addAction(self.aboutAction)
        self.trayMenu.addSeparator()
        self.trayMenu.addAction(self.quitAction)

        self.tray.setContextMenu(self.trayMenu)

        message =  'Tafor {}'.format(__version__)
        self.tray.setToolTip(message)

    def setupSound(self):
        self.notificationSound = Sound('notification.wav')
        self.incomingSound = Sound('notification-incoming.wav')
        self.alarmSound = Sound('alarm.wav', volumeKey='alarmVolume')
        self.tafSound = Sound('taf.wav', volumeKey='tafVolume')
        self.trendSound = Sound('trend.wav', volumeKey='trendVolume')
        self.sigmetSound = Sound('sigmet.wav', volumeKey='sigmetVolume')

        self.settingDialog.alarmVolume.valueChanged.connect(lambda vol: self.alarmSound.play(volume=vol, loop=False))
        self.settingDialog.tafVolume.valueChanged.connect(lambda vol: self.tafSound.play(volume=vol, loop=False))
        self.settingDialog.trendVolume.valueChanged.connect(lambda vol: self.trendSound.play(volume=vol, loop=False))
        self.settingDialog.sigmetVolume.valueChanged.connect(lambda vol: self.sigmetSound.play(volume=vol, loop=False))

    def ensureVisible(self):
        if not self.isVisible():
            self.showNormal()

    def event(self, event):
        if event.type() == QEvent.WindowStateChange and self.isMinimized():
            # 此时窗口已经最小化,
            # 从任务栏中移除窗口
            self.setWindowFlags(self.windowFlags() & Qt.Tool)
            self.tray.show()
            return True
        else:
            return super(MainWindow, self).event(event)

    def closeEvent(self, event):
        if event.spontaneous():
            event.ignore()
            self.hide()
        else:
            self.presenter.shutdown()
            event.accept()

    def recentWidgets(self):
        recents = []
        for i in range(self.scrollLayout.count()):
            widget = self.scrollLayout.itemAt(i).widget()
            if isinstance(widget, RecentMessage):
                recents.append(widget)

        return recents

    def renderRecentMessages(self, messages):
        uuids = [message.uuid for message in messages]
        reminderStates = {message.uuid: message.uuid in self.context.sigmet.entries for message in messages}
        for widget in self.recentWidgets():
            if widget.uuid() not in uuids:
                widget.deleteLater()
            else:
                widget.setReminderEnabled(reminderStates.get(widget.uuid(), False))
                widget.updateGui()

        uuids = [widget.uuid() for widget in self.recentWidgets()]
        for i, message in enumerate(messages):
            if message.uuid not in uuids:
                layerBoundaries = self.context.layer.boundaries() if hasattr(self.context, 'layer') else None
                widget = RecentMessage(
                    self,
                    self.scrollLayout,
                    message,
                    fixedFont=self.context.resource.fixedFont(),
                    layerBoundaries=layerBoundaries,
                    clearNotification=self.context.notification.metar.clear,
                    reminderEnabled=reminderStates.get(message.uuid, False),
                    index=i+1,
                )
                widget.reviewRequested.connect(self.reviewRecentMessage)
                widget.replyRequested.connect(self.trendEditor.quote)
                widget.reminderToggled.connect(self.presenter.setSigmetReminder)

    def isReminderVisible(self, box):
        return box.isVisible()

    def showReminder(self, box, sound, text):
        sound.play()
        box.setText(text)
        ret = box.exec_()
        if not box.isVisible():
            sound.stop()
        return ret

    def setRecentMessageReminder(self, uuid, enabled):
        for widget in self.recentWidgets():
            if uuid == widget.uuid():
                widget.setReminderEnabled(enabled)
                break

    def reviewRecentMessage(self, message):
        reviewer = None
        if message.type in ['FC', 'FT']:
            reviewer = self.tafSender
        elif message.type in ['WS', 'WC', 'WV', 'WA']:
            reviewer = self.sigmetSender

        if reviewer:
            reviewer.receive(message)
            reviewer.show()

    def closeSender(self):
        self.tafSender.close()
        self.trendSender.close()
        self.sigmetSender.close()

    def showSystemNotification(self, title, content, level='information'):
        icons = ['noicon', 'information', 'warning', 'critical']
        icon = QSystemTrayIcon.MessageIcon(icons.index(level))
        self.tray.showMessage(title, content, icon)

    def showStatusbarNotification(self, text, timeout):
        self.statusBar.showMessage(text, timeout)

    def restart(self):
        title = QCoreApplication.translate('Settings', 'Restart Required')
        text = QCoreApplication.translate('Settings', 'Program need to restart to apply the configuration, do you wish to restart now?')
        ret = QMessageBox.information(self, title, text, QMessageBox.Yes | QMessageBox.No)
        if ret == QMessageBox.No:
            return

        program = sys.executable
        args = []
        if not hasattr(sys, '_MEIPASS'):
            args.append(os.path.join(root, '__main__.py'))

        scripts = json.loads(os.environ.pop('TAFOR_ARGS'))
        args.extend(scripts)
        QProcess.startDetached(program, args)

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

    def reportIssue(self):
        QDesktopServices.openUrl(QUrl('https://github.com/up1and/tafor/issues'))

def main():
    os.environ['QT_ENABLE_HIGHDPI_SCALING'] = '1'
    os.environ['QT_SCALE_FACTOR_ROUNDING_POLICY'] = 'PassThrough'

    scale = conf.interfaceScaling or 0
    if scale:
        os.environ['QT_SCALE_FACTOR'] = str(int(scale) * 0.25 + 1)

    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    if hasattr(QGuiApplication, 'setHighDpiScaleFactorRoundingPolicy'):
        QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )

    os.environ['TAFOR_ARGS'] = json.dumps(sys.argv[1:])

    app = QApplication(sys.argv)

    font = context.resource.uiFont(pointSize=9)
    app.setFont(font)

    translator = QTranslator()
    locale = QLocale.system().name()
    translateFile = os.path.join(root, 'resources', 'i18n', '{}.qm'.format(locale))
    if translator.load(translateFile):
        app.installTranslator(translator)

    if conf.windowsStyle == 'Fusion':
        app.setStyle(QStyleFactory.create('Fusion'))

    serverName = 'Tafor'
    socket = QLocalSocket()
    socket.connectToServer(serverName)

    if socket.waitForConnected(500):
        return app.quit()

    localServer = QLocalServer()
    localServer.listen(serverName)

    if conf.rpc:
        rpcWorker, rpcThread = threadManager.createWorker(RpcWorker, workerId='rpc', reusable=True)
        rpcThread.start()
    
    app.aboutToQuit.connect(threadManager.cleanup)

    versions = context.info.environment()
    logger.info('Version {version}+{revision}, Python {python} {machine}, Qt {qt} on {system} {release}'.format(**versions))

    try:
        window = MainWindow(conf, context)
        window.show()
        code = app.exec_()
        sys.exit(code)
    except Exception as e:
        logger.exception('On startup {}'.format(e))
    finally:
        socket.close()
        localServer.close()


if __name__ == "__main__":
    main()
