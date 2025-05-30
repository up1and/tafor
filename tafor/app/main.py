import os
import sys
import json
import datetime

from uuid import uuid4

from PyQt5.QtGui import QIcon, QFont, QDesktopServices
from PyQt5.QtCore import QCoreApplication, QTranslator, QLocale, QEvent, QTimer, Qt, QUrl, QSysInfo, QProcess
from PyQt5.QtWidgets import (QMainWindow, QApplication, QSpacerItem, QSizePolicy,
        QSystemTrayIcon, QMenu, QMessageBox, QStyleFactory)
from PyQt5.QtNetwork import QLocalSocket, QLocalServer

from tafor import root, conf, logger, __version__
from tafor.models import db, Metar, Taf, Trend
from tafor.states import context
from tafor.utils import boolean, checkVersion, latestMetar, currentSigmet, findAvailables, createTafStatus
from tafor.utils.thread import (MessageWorker, LayerWorker, CheckUpgradeWorker, RpcWorker, threadManager)

from tafor.components.ui import Ui_main, main_rc
from tafor.components.taf import TafEditor
from tafor.components.trend import TrendEditor
from tafor.components.sigmet import SigmetEditor
from tafor.components.send import TafSender, TrendSender, SigmetSender, CustomSender
from tafor.components.setting import SettingDialog
from tafor.components.chart import ChartViewer

from tafor.components.widgets.table import TafTable, MetarTable, SigmetTable, AirmetTable
from tafor.components.widgets.widget import Clock, TafBoard, RecentMessage, RemindMessageBox, LicenseEditor
from tafor.components.widgets.sound import Sound


class MainWindow(QMainWindow, Ui_main.Ui_MainWindow):

    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.setupUi(self)
        self.sysInfo = QSysInfo.prettyProductName()

        # 时钟计时器
        self.clockTimer = QTimer()
        self.clockTimer.timeout.connect(self.singer)
        self.clockTimer.start(1 * 1000)

        self.workerTimer = QTimer()
        self.workerTimer.timeout.connect(self.worker)
        self.workerTimer.start(60 * 1000)

        self.painterTimer = QTimer()
        self.painterTimer.timeout.connect(self.painter)
        self.painterTimer.start(2 * 60 * 1000)

        self.setup()
        self.bindSignal()
        self.worker()
        self.painter()

        self.updateSigmet()
        self.updateTable()
        self.updateRecent()
        self.updateRegisterMenu()

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

        if not boolean(conf.value('General/Sigmet')):
            self.sigmetAction.setVisible(False)
            self.mainTab.removeTab(3)
            self.mainTab.removeTab(3)

        self.setupRecent()
        self.setupTable()
        self.setupSysTray()
        self.setupThread()
        self.setupSound()

    def bindSignal(self):
        context.taf.reminded.connect(self.remindTaf)
        context.other.messageChanged.connect(self.loadCustomMessage)
        context.notification.metar.messageChanged.connect(self.loadMetar)
        context.notification.sigmet.messageChanged.connect(self.loadSigmetNotification)
        context.message.sigmetChanged.connect(self.sigmetEditor.updateGraphicCanvas)
        context.layer.refreshed.connect(self.painter)
        context.flash.systemMessageChanged.connect(self.showSystemNotification)
        context.flash.statusbarMessageChanged.connect(self.showStatusbarNotification)

        # 连接菜单信号
        self.tafAction.triggered.connect(self.tafEditor.show)
        self.trendAction.triggered.connect(self.trendEditor.show)
        self.sigmetAction.triggered.connect(self.sigmetEditor.show)

        # 连接设置对话框的槽
        self.settingAction.triggered.connect(self.openSetting)
        self.settingAction.setIcon(QIcon(':/setting.png'))

        self.openDocsAction.triggered.connect(self.openDocs)
        self.reportIssueAction.triggered.connect(self.reportIssue)
        self.checkUpgradeAction.triggered.connect(self.checkUpgradeThread.start)
        self.enterLicenseAction.triggered.connect(self.licenseEditor.enter)
        self.removeLicenseAction.triggered.connect(self.removeLicense)
        self.aboutAction.triggered.connect(self.about)

        self.tray.activated.connect(self.showNormal)
        self.tray.messageClicked.connect(self.showNormal)
        if self.sysInfo.startswith('macOS'):
            self.trayMenu.aboutToShow.connect(lambda: self.setTrayIcon('light'))
            self.trayMenu.aboutToHide.connect(lambda: self.setTrayIcon('dark'))

        self.tafSender.succeeded.connect(self.updateGui)
        self.tafSender.succeeded.connect(self.updateGui)
        self.trendSender.succeeded.connect(self.updateGui)
        self.sigmetSender.succeeded.connect(self.updateGui)

        self.settingDialog.restarted.connect(self.restart)
        self.settingDialog.settingChanged.connect(self.closeSender)

        self.licenseEditor.licenseChanged.connect(self.updateRegisterMenu)

        self.metarTable.chartClicked.connect(self.chartViewer.show)

        self.layerThread.finished.connect(self.sigmetEditor.updateLayer)

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

    def setupThread(self):
        # Create workers using the new thread manager
        self.messageWorker, self.messageThread = threadManager.createWorker(MessageWorker, 'message')
        self.messageWorker.finished.connect(self.updateMessage)
        self.messageWorker.finished.connect(self.notifier)

        self.layerWorker, self.layerThread = threadManager.createWorker(LayerWorker, 'layer')

        self.checkUpgradeWorker, self.checkUpgradeThread = threadManager.createWorker(CheckUpgradeWorker, 'upgrade')
        self.checkUpgradeWorker.done.connect(self.checkUpgrade)

    def setupSound(self):
        self.notificationSound = Sound('notification.wav')
        self.incomingSound = Sound('notification-incoming.wav')
        self.alarmSound = Sound('alarm.wav', 'Monitor/AlarmVolume')
        self.tafSound = Sound('taf.wav', 'Monitor/TAFVolume')
        self.trendSound = Sound('trend.wav', 'Monitor/TrendVolume')
        self.sigmetSound = Sound('sigmet.wav', 'Monitor/SIGMETVolume')

        self.settingDialog.alarmVolume.valueChanged.connect(lambda vol: self.alarmSound.play(volume=vol, loop=False))
        self.settingDialog.tafVolume.valueChanged.connect(lambda vol: self.tafSound.play(volume=vol, loop=False))
        self.settingDialog.trendVolume.valueChanged.connect(lambda vol: self.trendSound.play(volume=vol, loop=False))
        self.settingDialog.sigmetVolume.valueChanged.connect(lambda vol: self.sigmetSound.play(volume=vol, loop=False))

    def loadCustomMessage(self):
        if not self.isVisible():
            self.showNormal()

        self.incomingSound.play(loop=False)
        self.customSender.load()
        self.customSender.show()

        context.flash.info(QCoreApplication.translate('MainWindow', 'Message Received'),
                QCoreApplication.translate('MainWindow', 'Received a custom message.'))

    def loadMetar(self):
        parser = context.notification.metar.parser()
        metar = latestMetar()

        # if there is notification, play reminder sound.
        if parser:
            self.trendSound.play()
        else:
            self.trendSound.stop()

        # when local metar is same as the notification metar, clear the state and show nothing.
        isSimilar = parser and metar and parser.isSimilar(metar.text)
        if isSimilar:
            context.notification.metar.clear()
            return

        # when validation does not pass, enable system warning notification.
        if parser and context.notification.metar.validation():
            parser.validate()
            if parser.hasTrend() and not parser.isValid():
                title = QCoreApplication.translate('MainWindow', 'Trend Validation Failed')
                description = QCoreApplication.translate('MainWindow', 'The trend has been cleared, please resend')
                context.flash.warning(title, description)

        # when local metar is not similar to the notification metar, update the recent and trend sender.
        self.updateRecent()
        self.trendSender.reload()

    def loadSigmetNotification(self):
        self.sigmetEditor.updateCustomText()
        message = context.notification.sigmet.message()
        if message:
            self.incomingSound.play(loop=False)
            context.flash.info(QCoreApplication.translate('MainWindow', 'Message Received'),
                QCoreApplication.translate('MainWindow', 'Received a {} message').format(context.notification.sigmet.type()))

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
            # Stop all timers first
            self.clockTimer.stop()
            self.workerTimer.stop()
            self.painterTimer.stop()

            self.tafSender.setAttribute(Qt.WA_DeleteOnClose)
            self.trendSender.setAttribute(Qt.WA_DeleteOnClose)
            self.sigmetSender.setAttribute(Qt.WA_DeleteOnClose)
            self.tafEditor.setAttribute(Qt.WA_DeleteOnClose)
            self.trendEditor.setAttribute(Qt.WA_DeleteOnClose)
            self.sigmetEditor.setAttribute(Qt.WA_DeleteOnClose)
            self.licenseEditor.setAttribute(Qt.WA_DeleteOnClose)
            self.settingDialog.setAttribute(Qt.WA_DeleteOnClose)
            self.chartViewer.setAttribute(Qt.WA_DeleteOnClose)

            self.tafSender.close()
            self.trendSender.close()
            self.sigmetSender.close()
            self.customSender.close()
            self.tafEditor.close()
            self.trendEditor.close()
            self.sigmetEditor.close()
            self.licenseEditor.close()
            self.settingDialog.close()
            self.chartViewer.close()
            self.remindTafBox.close()
            self.remindSigmetBox.close()

            self.tray.hide()

            # Clean up thread manager
            threadManager.cleanup()

            event.accept()

    def singer(self):
        warnSwitch = self.warnTafAction.isChecked()
        trendSwitch = boolean(conf.value('Monitor/RemindTrend'))

        # 管理趋势声音
        utc = datetime.datetime.utcnow()
        if trendSwitch and (utc.minute in (57, 58, 59) or context.notification.metar.message()):
            self.trendSound.play()
        else:
            self.trendSound.stop()

        # 管理报文告警声音
        if warnSwitch and context.taf.hasExpired():
            self.alarmSound.play()
        else:
            self.alarmSound.stop()

    def worker(self):
        threadManager.startWorker('message')

    def painter(self):
        if conf.value('Interface/LayerURL') and not threadManager.isWorkerRunning('layer'):
            threadManager.startWorker('layer')

    def notifier(self):
        connectionError = QCoreApplication.translate('MainWindow', 'Connection Error')
        if not context.message.message():
            context.flash.warning(connectionError,
                QCoreApplication.translate('MainWindow', 'Unable to connect remote message data source, please check the settings or network status.'))

        if conf.value('Interface/LayerURL') and not context.layer.currentLayers() and not threadManager.isWorkerRunning('layer'):
            context.flash.warning(connectionError,
                QCoreApplication.translate('MainWindow', 'Unable to connect FIR information data source, please check the settings or network status.'))

    def recentWidget(self):
        recents = []
        for i in range(self.scrollLayout.count()):
            widget = self.scrollLayout.itemAt(i).widget()
            if isinstance(widget, RecentMessage):
                recents.append(widget)

        return recents

    def remindTaf(self):
        remindSwitch = boolean(conf.value('Monitor/RemindTAF'))
        if not remindSwitch or self.remindTafBox.isVisible():
            return None

        type = context.taf.spec[:2].upper()
        period = context.taf.period()

        if context.taf.needReminded():
            current = type + period[2:4] + period[7:]
            text = QCoreApplication.translate('MainWindow', 'Time to issue {}').format(current)
            self.tafSound.play()
            self.remindTafBox.setText(text)
            ret = self.remindTafBox.exec_()
            if ret == QMessageBox.RejectRole:
                QTimer.singleShot(1000 * 60 * 5, self.remindTaf)

            if not self.remindTafBox.isVisible():
                self.tafSound.stop()

    def remindSigmet(self):
        remindSwitch = boolean(conf.value('Monitor/RemindSIGMET'))
        if not remindSwitch or self.remindSigmetBox.isVisible():
            return None

        outdates = context.sigmet.outdate()
        for item in outdates:
            sig = item['text']
            mark = '{} {}'.format(sig.reportType(), sig.sequence())
            text = QCoreApplication.translate('MainWindow', 'Time to update {}').format(mark)
            self.sigmetSound.play()
            self.remindSigmetBox.setText(text)
            ret = self.remindSigmetBox.exec_()
            if ret == QMessageBox.AcceptRole:
                context.sigmet.remove(item['uuid'])
                for widget in self.recentWidget():
                    if item['uuid'] == widget.uuid():
                        widget.removeRemind()
            else:
                time = item['time'] + datetime.timedelta(minutes=5)
                context.sigmet.update(item['uuid'], time)

        if not self.remindSigmetBox.isVisible():
            self.sigmetSound.stop()

    def updateRegisterMenu(self):
        registered = context.environ.license()
        if registered:
            self.enterLicenseAction.setVisible(False)
            self.removeLicenseAction.setVisible(True)
        else:
            self.enterLicenseAction.setVisible(True)
            self.removeLicenseAction.setVisible(False)

    def updateMessage(self):
        wishlist = ['SA', 'SP']
        if conf.value('General/TAFSpec'):
            wishlist.append('FT')
        else:
            wishlist.append('FC')

        if boolean(conf.value('General/Sigmet')):
            wishlist.extend(['WS', 'WC', 'WV', 'WA'])

        messages = context.message.message()
        items = findAvailables(messages, wishlist=wishlist)
        needPlaySound = False

        for item in items:
            if item.id:
                logger.info('Confirm {} {}'.format(item.type, item.text))
            else:
                logger.info('Save {} {}'.format(item.type, item.text))

            if item.type in ['SA', 'SP']:
                context.notification.metar.clear()
            else:
                needPlaySound = True

            db.add(item)

        db.commit()

        if needPlaySound:
            self.notificationSound.play(loop=False)
            self.remindTafBox.close()

        self.updateGui()

    def updateTaf(self):
        status = createTafStatus(context.taf.spec)
        context.taf.setState(status)

    def updateSigmet(self):
        try:
            sigmets = currentSigmet()
            context.message.setSigmet(sigmets)
        except Exception as e:
            logger.error('Sigmet cannot be updated, {}'.format(e))

    def updateGui(self):
        self.updateTaf()
        self.updateSigmet()
        self.updateTable()
        self.updateRecent()
        self.remindSigmet()

    def updateRecent(self):
        self.tafBoard.updateGui()

        recent = datetime.datetime.utcnow() - datetime.timedelta(hours=24)
        spec = context.taf.spec[:2].upper()
        taf = db.query(Taf).filter(Taf.created > recent, Taf.type == spec).order_by(Taf.created.desc()).first()
        if boolean(conf.value('General/Sigmet')):
            sigmets = context.message.sigmets(show='all')
        else:
            sigmets = []

        trend = db.query(Trend).order_by(Trend.created.desc()).first()
        if trend and trend.isNosig():
            trend = None

        parser = context.notification.metar.parser()
        if parser:
            uuid = str(uuid4())
            created = context.notification.metar.created()
            validation = context.notification.metar.validation()
            metar = Metar(uuid=uuid, text=parser.message, created=created)
            parser.validate()
            metar.validations = {
                'html': parser.renderer(style='html', showDiff=True),
                'tips': parser.tips,
                'pass': parser.isValid(),
                'validation': validation
            }
        else:
            metar = db.query(Metar).filter(Metar.created > recent).order_by(Metar.created.desc()).first()

        queryset = list(filter(None, [metar, trend, taf] + sigmets))
        uuids = [q.uuid for q in queryset]
        for widget in self.recentWidget():
            if widget.uuid() not in uuids:
                widget.deleteLater()
            else:
                widget.updateGui()

        widgetUuids = [widget.uuid() for widget in self.recentWidget()]
        for i, query in enumerate(queryset):
            if query.uuid not in widgetUuids:
                RecentMessage(self, self.scrollLayout, query, index=i+1)

    def updateTable(self):
        self.tafTable.updateGui()
        self.metarTable.updateGui()
        self.sigmetTable.updateGui()
        self.airmetTable.updateGui()

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

    def openSetting(self):
        if not self.isVisible():
            self.showNormal()
        self.settingDialog.exec_()

    def restart(self):
        self.close()
        program = sys.executable
        args = []
        if not hasattr(sys, '_MEIPASS'):
            args.append(os.path.join(root, '__main__.py'))

        scripts = json.loads(os.environ.pop('TAFOR_ARGS'))
        args.extend(scripts)
        QProcess.startDetached(program, args)

    def about(self):
        title = QCoreApplication.translate('MainWindow', 'About')
        register = QCoreApplication.translate('MainWindow', '{} days remaining').format(
            context.environ.exp) if context.environ.license() else QCoreApplication.translate('MainWindow', 'Unregistered')
        html = """
        <div style="text-align:center">
        <img src=":/logo.png">
        <h2 style="margin:5px 0">Tafor</h2>
        <p style="margin:0;color:#444;font-size:13px">A Terminal Aerodrome Forecast Encoding Software</p>
        <p style="margin:5px 0"><a href="https://github.com/up1and/tafor" style="text-decoration:none;color:#0078d7">{} {} {}</a></p>
        <p style="margin:5px 0;color:#444">{}</p>
        <p style="margin-top:25px;color:#444">Copyright © 2022 <a href="mailto:piratecb@gmail.com" style="text-decoration:none;color:#444">up1and</a></p>
        </div>
        """.format(QCoreApplication.translate('MainWindow', 'Version'), __version__, context.environ.ghash(), register)

        aboutBox = QMessageBox(self)
        aboutBox.setText(html)
        aboutBox.setWindowTitle(title)
        layout = aboutBox.layout()
        layout.removeItem(layout.itemAt(0))
        aboutBox.addButton(QMessageBox.Ok)
        if not self.isVisible():
            self.showNormal()
        aboutBox.exec()

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

    def checkUpgrade(self, data):
        title = QCoreApplication.translate('MainWindow', 'Check for Updates')
        release = data.get('tag_name')
        if not release:
            text = QCoreApplication.translate('MainWindow', 'Unable to get the latest version information.')
            QMessageBox.information(self, title, text)
            return False

        hasNewVersion = checkVersion(release, __version__)
        if not hasNewVersion:
            text = QCoreApplication.translate('MainWindow', 'The current version is already the latest version.')
            QMessageBox.information(self, title, text)
            return False

        download = 'https://github.com/up1and/tafor/releases'
        text = QCoreApplication.translate('MainWindow', 'New version found {}, do you want to download now?').format(data.get('tag_name'))
        ret = QMessageBox.question(self, title, text)
        if ret == QMessageBox.Yes:
            QDesktopServices.openUrl(QUrl(download))

    def removeLicense(self):
        title = QCoreApplication.translate('MainWindow', 'Remove license key? ')
        text = QCoreApplication.translate('MainWindow', 'Remove license key? This will revert tafor to an unregistered state.')
        ret = QMessageBox.question(self, title, text)
        if ret == QMessageBox.Yes:
            self.licenseEditor.removeLicense()


def main():
    scale = conf.value('General/InterfaceScaling') or 0
    os.environ['QT_SCALE_FACTOR'] = str(int(scale) * 0.25 + 1)
    os.environ['TAFOR_ARGS'] = json.dumps(sys.argv[1:])

    app = QApplication(sys.argv)

    font = QFont('Microsoft YaHei', 9)
    font.setStyleHint(QFont.System)
    app.setFont(font)

    translator = QTranslator()
    locale = QLocale.system().name()
    translateFile = os.path.join(root, 'i18n', '{}.qm'.format(locale))
    if translator.load(translateFile):
        app.installTranslator(translator)

    if conf.value('General/WindowsStyle') == 'Fusion':
        app.setStyle(QStyleFactory.create('Fusion'))

    serverName = 'Tafor'
    socket = QLocalSocket()
    socket.connectToServer(serverName)

    if socket.waitForConnected(500):
        return app.quit()

    localServer = QLocalServer()
    localServer.listen(serverName)

    if boolean(conf.value('Interface/RPC')):
        rpcWorker, rpcThread = threadManager.createWorker(RpcWorker, 'rpc')
        threadManager.startWorker('rpc')
        app.aboutToQuit.connect(lambda: threadManager.stopWorker('rpc'))

    versions = context.environ.environment()
    logger.info('Version {version}+{revision}, Python {python} {bitness}, Qt {qt} on {system} {release}'.format(**versions))

    try:
        window = MainWindow()
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
