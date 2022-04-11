import os
import sys
import json
import datetime

from PyQt5.QtGui import QIcon, QDesktopServices
from PyQt5.QtCore import QCoreApplication, QTranslator, QLocale, QEvent, QTimer, Qt, QUrl, QSysInfo, QProcess
from PyQt5.QtWidgets import (QMainWindow, QApplication, QSpacerItem, QSizePolicy, QActionGroup, QAction,
        QSystemTrayIcon, QMenu, QMessageBox, QStyleFactory)
from PyQt5.QtNetwork import QLocalSocket, QLocalServer

from tafor import root, conf, logger, __version__
from tafor.models import db, Metar, Taf, Trend
from tafor.states import context
from tafor.utils import boolean, checkVersion, latestMetar, currentSigmet, findAvailables, createTafStatus
from tafor.utils.thread import WorkThread, LayerThread, CheckUpgradeThread, RpcThread

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
        self.painterTimer.start(5 * 60 * 1000)

        self.setup()
        self.bindSignal()
        self.updateGui()
        self.worker()
        self.painter()

    def setup(self):
        self.setWindowIcon(QIcon(':/logo.png'))

        self.clip = QApplication.clipboard()
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

        self.setRecent()
        self.setTable()
        self.setAboutMenu()
        self.setSysTray()
        self.setThread()
        self.setSound()

    def bindSignal(self):
        context.taf.reminded.connect(self.remindTaf)
        context.other.messageChanged.connect(self.loadCustomMessage)
        context.notification.metar.messageChanged.connect(self.loadMetar)
        context.notification.sigmet.messageChanged.connect(self.loadSigmetNotification)
        context.message.sigmetChanged.connect(self.sigmetEditor.updateGraphicCanvas)
        context.layer.refreshed.connect(self.painter)

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

    def setRecent(self):
        self.clock = Clock(self, self.tipsLayout)
        self.tipsLayout.addSpacerItem(QSpacerItem(10, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))
        self.tafBoard = TafBoard(self, self.tipsLayout)
        self.scrollLayout.setAlignment(Qt.AlignTop)

    def setTable(self):
        self.tafTable = TafTable(self, self.tafLayout)
        self.metarTable = MetarTable(self, self.metarLayout)
        self.sigmetTable = SigmetTable(self, self.sigmetLayout)
        self.airmetTable = AirmetTable(self, self.airmetLayout)

    def setAboutMenu(self):
        registered = context.environ.license()
        if registered:
            self.enterLicenseAction.setVisible(False)
            self.removeLicenseAction.setVisible(True)
        else:
            self.enterLicenseAction.setVisible(True)
            self.removeLicenseAction.setVisible(False)

    def setSysTray(self):
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

    def setThread(self):
        self.workThread = WorkThread()
        self.workThread.finished.connect(self.updateMessage)
        self.workThread.finished.connect(self.notifier)

        self.layerThread = LayerThread()

        self.checkUpgradeThread = CheckUpgradeThread()
        self.checkUpgradeThread.done.connect(self.checkUpgrade)

    def loadCustomMessage(self):
        if not self.isVisible():
            self.showNormal()

        self.incomingSound.play(loop=False)
        self.customSender.load()
        self.customSender.show()
        self.showNotificationMessage(QCoreApplication.translate('MainWindow', 'Message Received'),
                QCoreApplication.translate('MainWindow', 'Received a custom message.'))

    def loadMetar(self):
        parser = context.notification.metar.parser()
        metar = latestMetar()

        # when local metar is same as the notification metar, clear the state and show nothing.
        isSimilar = parser and metar and parser.isSimilar(metar.text)
        if isSimilar:
            context.notification.metar.clear()
            return

        # when local metar is not similar to the notification metar, update the recent.
        if not isSimilar:
            self.updateRecent()

        # if there is notification, show the notification.
        if parser:
            self.notifyMetar()

    def notifyMetar(self):
        parser = context.notification.metar.parser()
        parser.validate()
        level='information'
        self.incomingSound.play(loop=False)

        if parser.hasTrend():
            if parser.isValid():
                title = QCoreApplication.translate('MainWindow', 'Trend Validation Success')
                description = QCoreApplication.translate('MainWindow', 'The trend has been successfully attached')
            else:
                title = QCoreApplication.translate('MainWindow', 'Trend Validation Failed')
                description = QCoreApplication.translate('MainWindow', 'The trend has been cleared, please resend')
                level = 'warning'
        else:
            title = QCoreApplication.translate('MainWindow', 'Message Received')
            description = QCoreApplication.translate('MainWindow', 'Received a {} message.'.format(context.notification.metar.type()))
        
        self.showNotificationMessage(title, description, level)

    def loadSigmetNotification(self):
        self.incomingSound.play(loop=False)
        self.sigmetEditor.loadNotification()
        self.showNotificationMessage(QCoreApplication.translate('MainWindow', 'Message Received'),
                QCoreApplication.translate('MainWindow', 'Received a {} message.').format(context.notification.sigmet.type()))

    def setSound(self):
        self.ringSound = Sound('ring.wav', conf.value('Monitor/RemindTAFVolume'))
        self.notificationSound = Sound('notification.wav', 100)
        self.incomingSound = Sound('notification-incoming.wav', 100)
        self.alarmSound = Sound('alarm.wav', conf.value('Monitor/WarnTAFVolume'))
        self.trendSound = Sound('trend.wav', conf.value('Monitor/RemindTrendVolume'))
        self.sigmetSound = Sound('sigmet.wav', conf.value('Monitor/RemindSIGMETVolume'))

        self.settingDialog.warnTafVolume.valueChanged.connect(lambda vol: self.alarmSound.play(volume=vol, loop=False))
        self.settingDialog.remindTafVolume.valueChanged.connect(lambda vol: self.ringSound.play(volume=vol, loop=False))
        self.settingDialog.remindTrendVolume.valueChanged.connect(lambda vol: self.trendSound.play(volume=vol, loop=False))
        self.settingDialog.remindSigmetVolume.valueChanged.connect(lambda vol: self.sigmetSound.play(volume=vol, loop=False))

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
            self.remindTafBox = None
            self.remindSigmetBox = None

            self.tray.hide()
            event.accept()

    def singer(self):
        warnSwitch = self.warnTafAction.isChecked()
        trendSwitch = boolean(conf.value('Monitor/RemindTrend'))

        # 管理趋势声音
        utc = datetime.datetime.utcnow()
        if trendSwitch and utc.minute in (57, 58, 59):
            self.trendSound.play()
        else:
            self.trendSound.stop()

        # 管理报文告警声音
        if warnSwitch and context.taf.hasExpired():
            self.alarmSound.play()
        else:
            self.alarmSound.stop()

    def worker(self):
        self.workThread.start()

    def painter(self):
        if conf.value('Monitor/FirApiURL') and not self.layerThread.isRunning():
            self.layerThread.start()

    def notifier(self):
        connectionError = QCoreApplication.translate('MainWindow', 'Connection Error')
        if not context.message.message():
            self.showNotificationMessage(connectionError,
                QCoreApplication.translate('MainWindow', 'Unable to connect remote message data source, please check the settings or network status.'), 'warning')

        if conf.value('Monitor/FirApiURL') and not context.layer.currentLayers() and not self.layerThread.isRunning():
            self.showNotificationMessage(connectionError,
                QCoreApplication.translate('MainWindow', 'Unable to connect FIR information data source, please check the settings or network status.'), 'warning')

    def remindTaf(self):
        remindSwitch = boolean(conf.value('Monitor/RemindTAF'))
        if not remindSwitch:
            return None

        type = context.taf.spec[:2].upper()
        period = context.taf.period()

        if context.taf.needReminded():
            current = type + period[2:4] + period[7:]
            text = QCoreApplication.translate('MainWindow', 'Time to issue {}').format(current)
            self.ringSound.play()
            self.remindTafBox.setText(text)
            ret = self.remindTafBox.exec_()
            if not ret:
                QTimer.singleShot(1000 * 60 * 5, self.remindTaf)

            if not self.remindTafBox.isVisible():
                self.ringSound.stop()

    def remindSigmet(self, sig):
        remindSwitch = boolean(conf.value('Monitor/RemindSIGMET'))
        sigmets = [sig.report.strip() for sig in context.message.sigmets()]
        if not remindSwitch or sig.message not in sigmets:
            return None

        mark = '{} {}'.format(sig.reportType(), sig.sequence())
        text = QCoreApplication.translate('MainWindow', 'Time to update {}').format(mark)
        self.sigmetSound.play()
        self.remindSigmetBox.setText(text)
        ret = self.remindSigmetBox.exec_()
        if not ret:
            QTimer.singleShot(1000 * 60 * 5, lambda: self.remindSigmet(sig))

        if not self.remindSigmetBox.isVisible():
            self.sigmetSound.stop()

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
                logger.info('Auto confirm {} {}'.format(item.type, item.text))
            else:
                logger.info('Auto Save {} {}'.format(item.type, item.text))

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
        sigmets = currentSigmet()
        context.message.setSigmet(sigmets)

    def updateGui(self):
        self.updateTaf()
        self.updateSigmet()
        self.updateTable()
        self.updateRecent()

    def updateRecent(self):
        self.tafBoard.updateGui()

        for i in range(self.scrollLayout.count()):
            if i > 0:
                widget = self.scrollLayout.itemAt(i).widget()
                if widget:
                    widget.deleteLater()

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
            created = context.notification.metar.created()
            validation = context.notification.metar.validation()
            metar = Metar(rpt=parser.message, created=created)
            parser.validate()
            metar.validations = {
                'html': parser.renderer(style='html', showDiff=True),
                'tips': parser.tips,
                'pass': parser.isValid(),
                'validation': validation
            }
        else:
            metar = db.query(Metar).filter(Metar.created > recent).order_by(Metar.created.desc()).first()

        queryset = [metar, taf, trend] + sigmets
        for query in queryset:
            if query:
                RecentMessage(self, self.scrollLayout, query)

    def updateTable(self):
        self.tafTable.updateGui()
        self.metarTable.updateGui()
        self.sigmetTable.updateGui()
        self.airmetTable.updateGui()

    def showNotificationMessage(self, title, content, level='information'):
        icons = ['noicon', 'information', 'warning', 'critical']
        icon = QSystemTrayIcon.MessageIcon(icons.index(level))
        self.tray.showMessage(title, content, icon)

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
        tokenButton = aboutBox.addButton(QCoreApplication.translate('MainWindow', 'Token'), QMessageBox.ResetRole)
        aboutBox.addButton(QMessageBox.Ok)
        if not self.isVisible():
            self.showNormal()
        aboutBox.exec()

        if aboutBox.clickedButton() == tokenButton:
            token = context.environ.token()
            self.clip.setText(token)
            QMessageBox.information(self, QCoreApplication.translate('MainWindow', 'Authentication Token'),
                QCoreApplication.translate('MainWindow',
                    'The authentication token for the RPC service has been copied to the clipboard.\n\n{}\n'
                    ).format(token))

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
            conf.setValue('License', '')
            self.setAboutMenu()


def main():
    scale = conf.value('General/InterfaceScaling') or 0
    os.environ['QT_SCALE_FACTOR'] = str(int(scale) * 0.25 + 1)
    os.environ['TAFOR_ARGS'] = json.dumps(sys.argv[1:])

    app = QApplication(sys.argv)

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

    if boolean(conf.value('General/RPC')):
        rpc = RpcThread()
        rpc.start()
        app.aboutToQuit.connect(rpc.terminate)

    versions = context.environ.environment()
    logger.info('Version {version}+{revision}, Python {python} {bitness}, Qt {qt} on {system} {release}'.format(**versions))

    try:
        window = MainWindow()
        window.show()
        code = app.exec_()
        sys.exit(code)
    except Exception as e:
        logger.error(e, exc_info=True)
    finally:
        socket.close()
        localServer.close()


if __name__ == "__main__":
    main()
