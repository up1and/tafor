import os
import datetime

from PyQt5.QtGui import QIcon, QDesktopServices
from PyQt5.QtCore import QCoreApplication, QTranslator, QLocale, QEvent, QTimer, Qt, QUrl
from PyQt5.QtWidgets import (QMainWindow, QApplication, QSpacerItem, QSizePolicy, QActionGroup, QAction,
        QSystemTrayIcon, QMenu, QMessageBox, QStyleFactory)
from PyQt5.QtNetwork import QLocalSocket, QLocalServer

from tafor import root, conf, logger, __version__
from tafor.models import db, User, Taf, Trend
from tafor.states import context
from tafor.utils import boolean, checkVersion, Listen
from tafor.utils.service import currentSigmet, DelaySend
from tafor.utils.thread import WorkThread, FirInfoThread, CallThread, CheckUpgradeThread

from tafor.components.ui import Ui_main, main_rc
from tafor.components.taf import TafEditor, TaskTafEditor
from tafor.components.trend import TrendEditor
from tafor.components.sigmet import SigmetEditor
from tafor.components.send import TaskTafSender, TafSender, TrendSender, SigmetSender
from tafor.components.setting import SettingDialog
from tafor.components.task import TaskBrowser

from tafor.components.widgets.table import TafTable, MetarTable, SigmetTable
from tafor.components.widgets.widget import Clock, TafBoard, RecentMessage, RemindMessageBox
from tafor.components.widgets.status import WebAPIStatus, CallServiceStatus
from tafor.components.widgets.sound import Sound


class MainWindow(QMainWindow, Ui_main.Ui_MainWindow):

    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.setupUi(self)

        # 时钟计时器
        self.clockTimer = QTimer()
        self.clockTimer.timeout.connect(self.singer)
        self.clockTimer.start(1 * 1000)

        self.workerTimer = QTimer()
        self.workerTimer.timeout.connect(self.worker)
        if boolean(conf.value('General/Serious')):
            self.workerTimer.timeout.connect(self.sender)
        self.workerTimer.start(60 * 1000)

        self.painterTimer = QTimer()
        self.painterTimer.timeout.connect(self.painter)
        self.painterTimer.start(10 * 60 * 1000)

        self.setup()
        self.bindSignal()
        self.updateGui()
        self.worker()
        self.painter()

    def setup(self):
        self.setWindowIcon(QIcon(':/logo.png'))

        self.clip = QApplication.clipboard()
        self.remindBox = RemindMessageBox(self)

        # 初始化窗口
        self.settingDialog = SettingDialog(self)

        self.tafSender = TafSender(self)
        self.trendSender = TrendSender(self)
        self.sigmetSender = SigmetSender(self)

        self.tafEditor = TafEditor(self, self.tafSender)
        self.trendEditor = TrendEditor(self, self.trendSender)
        self.sigmetEditor = SigmetEditor(self, self.sigmetSender)

        if boolean(conf.value('General/Serious')):
            self.taskBrowser = TaskBrowser(self)
            self.taskTafSender = TaskTafSender(self)
            self.taskTafEditor = TaskTafEditor(self, self.taskTafSender)

        self.setRecent()
        self.setTable()
        self.setContractMenu() # 设置切换联系人菜单
        self.setSysTray()
        self.setStatus()
        self.setThread()
        self.setSound()

    def bindSignal(self):
        context.taf.warningSignal.connect(self.dialer)
        context.taf.clockSignal.connect(self.remindTaf)

        # 连接菜单信号
        self.tafAction.triggered.connect(self.tafEditor.show)
        self.trendAction.triggered.connect(self.trendEditor.show)
        self.sigmetAction.triggered.connect(self.sigmetEditor.show)

        # 连接设置对话框的槽
        self.settingAction.triggered.connect(self.settingDialog.exec_)
        self.settingAction.setIcon(QIcon(':/setting.png'))

        self.openDocsAction.triggered.connect(self.openDocs)
        self.reportIssueAction.triggered.connect(self.reportIssue)
        self.checkUpgradeAction.triggered.connect(self.checkUpgradeThread.start)

        # 连接关于信息的槽
        self.aboutAction.triggered.connect(self.about)

        # 连接切换联系人的槽
        self.contractsActionGroup.triggered.connect(self.changeContract)
        self.contractsActionGroup.triggered.connect(self.settingDialog.load)

        self.tray.messageClicked.connect(self.showNormal)

    def setRecent(self):
        self.clock = Clock(self, self.tipsLayout)
        self.tipsLayout.addSpacerItem(QSpacerItem(10, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))
        self.tafBoard = TafBoard(self, self.tipsLayout)
        self.recentLayout.setAlignment(Qt.AlignTop)

    def setTable(self):
        self.tafTable = TafTable(self, self.tafLayout)
        self.metarTable = MetarTable(self, self.metarLayout)
        self.sigmetTable = SigmetTable(self, self.sigmetLayout)

    def setContractMenu(self):
        self.contractsActionGroup = QActionGroup(self)
        self.contractsActionGroup.addAction(self.contractNo)

        contacts = db.query(User).all()

        for person in contacts:
            setattr(self, 'contract' + str(person.id), QAction(self))
            target = getattr(self, 'contract' + str(person.id))
            target.setText(person.name)
            target.setCheckable(True)

            self.contractsActionGroup.addAction(target)
            self.contractsMenu.addAction(target)

        self.updateContractMenu()

    def setSysTray(self):
        # 设置系统托盘
        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(QIcon(':/logo.png'))
        self.tray.show()

        # 连接系统托盘的槽
        self.tray.activated.connect(self.restoreWindow)

        self.trayMenu = QMenu(self)

        self.trayMenu.addAction(self.contractsMenu.menuAction())
        self.trayMenu.addAction(self.settingAction)
        self.trayMenu.addAction(self.aboutAction)
        self.trayMenu.addSeparator()
        self.trayMenu.addAction(self.quitAction)

        self.tray.setContextMenu(self.trayMenu)

        message =  'Tafor {}'.format(__version__)
        self.tray.setToolTip(message)

    def setStatus(self):
        self.webApiStatus = WebAPIStatus(self, self.statusBar)
        self.callServiceStatus = CallServiceStatus(self, self.statusBar, last=True)

        # self.statusBar.setStyleSheet('QStatusBar::item{border: 0px}')

    def setThread(self):
        self.workThread = WorkThread(self)
        self.workThread.finished.connect(self.updateMessage)
        self.workThread.finished.connect(self.notifier)

        self.callThread = CallThread(self)

        self.firInfoThread = FirInfoThread()

        self.checkUpgradeThread = CheckUpgradeThread(self)
        self.checkUpgradeThread.doneSignal.connect(self.checkUpgrade)

    def setSound(self):
        self.ringSound = Sound('ring.wav', conf.value('Monitor/RemindTAFVolume'))
        self.notificationSound = Sound('notification.wav', 100)
        self.alarmSound = Sound('alarm.wav', conf.value('Monitor/WarnTAFVolume'))
        self.trendSound = Sound('trend.wav', conf.value('Monitor/RemindTrendVolume'))
        self.sigmetSound = Sound('sigmet.wav', conf.value('Monitor/RemindSIGMETVolume'))

        self.settingDialog.warnTafVolume.valueChanged.connect(lambda vol: self.alarmSound.play(volume=vol, loop=False))
        self.settingDialog.remindTafVolume.valueChanged.connect(lambda vol: self.ringSound.play(volume=vol, loop=False))
        self.settingDialog.remindTrendVolume.valueChanged.connect(lambda vol: self.trendSound.play(volume=vol, loop=False))
        self.settingDialog.remindSigmetVolume.valueChanged.connect(lambda vol: self.sigmetSound.play(volume=vol, loop=False))

    def changeContract(self):
        target = self.contractsActionGroup.checkedAction()

        if self.contractNo == target:
            conf.setValue('Monitor/SelectedMobile', '')
            logger.info('Turn off phone alerts')
        else:
            name = target.text()
            person = db.query(User).filter_by(name=name).first()
            mobile = person.mobile if person else ''

            conf.setValue('Monitor/SelectedMobile', mobile)
            logger.info('Switch contacts to %s %s' % (name, mobile))

    def event(self, event):
        if event.type() == QEvent.WindowStateChange and self.isMinimized():
            # 此时窗口已经最小化,
            # 从任务栏中移除窗口
            self.setWindowFlags(self.windowFlags() & Qt.Tool)
            self.tray.show()
            return True
        else:
            return super(MainWindow, self).event(event)

    def keyPressEvent(self, event):
        if boolean(conf.value('General/Serious')):
            if event.modifiers() == (Qt.ShiftModifier | Qt.ControlModifier):
                if event.key() == Qt.Key_P:
                    self.taskTafEditor.show()
                if event.key() == Qt.Key_T:
                    self.taskBrowser.show()

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
            self.settingDialog.setAttribute(Qt.WA_DeleteOnClose)

            self.tafSender.close()
            self.trendSender.close()
            self.sigmetSender.close()
            self.tafEditor.close()
            self.trendEditor.close()
            self.sigmetEditor.close()
            self.settingDialog.close()
            self.remindBox = None

            if boolean(conf.value('General/Serious')):
                self.taskTafSender.setAttribute(Qt.WA_DeleteOnClose)
                self.taskTafEditor.setAttribute(Qt.WA_DeleteOnClose)
                self.taskBrowser.setAttribute(Qt.WA_DeleteOnClose)
                self.taskTafSender.close()
                self.taskTafEditor.close()
                self.taskBrowser.close()

            self.tray.hide()
            event.accept()

    def restoreWindow(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self.showNormal()

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
        if warnSwitch and context.taf.isWarning():
            self.alarmSound.play()
        else:
            self.alarmSound.stop()

    def worker(self):
        self.workThread.start()

    def painter(self):
        if conf.value('Monitor/FirApiURL'):
            self.firInfoThread.start()

    def dialer(self, test=False):
        callSwitch = conf.value('Monitor/SelectedMobile')

        if callSwitch and context.taf.isWarning() or test:
            self.callThread.start()

    def sender(self):
        if context.serial.busy():
            logger.info('Serial port is busy')
            return

        def afterSending(message, error=None):
            if error:
                self.showNotifyMessage(QCoreApplication.translate('MainWindow', 'Send Failed'),
                    QCoreApplication.translate('MainWindow', error))
            else:
                self.showNotifyMessage(QCoreApplication.translate('MainWindow', 'Send Completed'),
                    QCoreApplication.translate('MainWindow', message))
                self.updateGui()
                self.taskBrowser.updateGui()

        self.delaySend = DelaySend(callback=afterSending)
        self.delaySend.start()

    def notifier(self):
        connectionError = QCoreApplication.translate('MainWindow', 'Connection Error')
        if not context.webApi.isOnline():
            self.showNotificationMessage(connectionError,
                QCoreApplication.translate('MainWindow', 'Unable to connect remote message data source, please check the settings or network status.'), 'warning')

        if conf.value('Monitor/FirApiURL') and context.fir.image() is None and not self.firInfoThread.isRunning():
            self.showNotificationMessage(connectionError,
                QCoreApplication.translate('MainWindow', 'Unable to connect FIR information data source, please check the settings or network status.'), 'warning')

        if not context.callService.isOnline() and self.contractsActionGroup.checkedAction() != self.contractNo:
            self.showNotificationMessage(connectionError,
                QCoreApplication.translate('MainWindow', 'Unable to connect phone call service, please check the settings or network status.'), 'warning')

    def remindTaf(self, tt):
        remindSwitch = boolean(conf.value('Monitor/RemindTAF'))
        if not remindSwitch:
            return None

        state = context.taf.state()
        clock = state[tt]['clock']
        period = state[tt]['period']
        sent = state[tt]['sent']
        warning = state[tt]['warning']

        if clock and not warning and not sent:
            current = tt + period[2:]
            text = QCoreApplication.translate('MainWindow', 'Time to issue {}').format(current)
            self.ringSound.play()
            self.remindBox.setText(text)
            ret = self.remindBox.exec_()
            if not ret:
                QTimer.singleShot(1000 * 60 * 5, lambda: self.remindTaf(tt))

            self.ringSound.stop()

    def remindSigmet(self, text):
        remindSwitch = boolean(conf.value('Monitor/RemindSIGMET'))
        if not remindSwitch:
            return None

        text = QCoreApplication.translate('MainWindow', 'Time to update {}').format(text)
        self.sigmetSound.play()
        self.remindBox.setText(text)
        ret = self.remindBox.exec_()
        if not ret:
            QTimer.singleShot(1000 * 60 * 5, lambda: self.remindSigmet(text))

        self.sigmetSound.stop()

    def updateMessage(self):

        def afterSaving():
            self.notificationSound.play(loop=False)
            self.remindBox.close()

        listen = Listen(callback=afterSaving)

        names = ['SA', 'SP']
        international = boolean(conf.value('General/InternationalAirport'))
        if international:
            names.append('FT')
        else:
            names.append('FC')

        for i in names:
            listen(i)

        self.updateGui()

    def updateSigmet(self):
        sigmets = currentSigmet(tt='WS')
        context.fir.setState({
            'sigmets': sigmets
        })

    def updateGui(self):
        self.updateTable()
        self.updateRecent()
        self.updateContractMenu()
        self.updateSigmet()

        logger.debug('Update GUI')

    def updateContractMenu(self):
        mobile = conf.value('Monitor/SelectedMobile')
        person = db.query(User).filter_by(mobile=mobile).first()
        if person:
            action = getattr(self, 'contract' + str(person.id), None)
            if action:
                action.setChecked(True)
        else:
            self.contractNo.setChecked(True)

    def updateRecent(self):
        self.tafBoard.updateGui()

        for i in range(self.recentLayout.count()):
            if i > 0:
                widget = self.recentLayout.itemAt(i).widget()
                if widget:
                    widget.deleteLater()

        recent = datetime.datetime.utcnow() - datetime.timedelta(hours=24)

        taf = db.query(Taf).filter(Taf.sent > recent).order_by(Taf.sent.desc()).first()
        sigmets = currentSigmet(order='asc', hasCnl=True)
        trend = db.query(Trend).order_by(Trend.sent.desc()).first()
        if trend and trend.isNosig():
            trend = None

        queryset = [taf, trend] + sigmets
        for query in queryset:
            if query:
                RecentMessage(self, self.recentLayout, query)

    def updateTable(self):
        self.tafTable.updateGui()
        self.metarTable.updateGui()
        self.sigmetTable.updateGui()

    def showNotificationMessage(self, title, content, level='information'):
        icons = ['noicon', 'information', 'warning', 'critical']
        icon = QSystemTrayIcon.MessageIcon(icons.index(level))
        self.tray.showMessage(title, content, icon)

    def about(self):
        title = QCoreApplication.translate('MainWindow', 'About')
        html = """
        <div style="text-align:center">
        <img src=":/logo.png">
        <h2 style="margin:5px 0">Tafor</h2>
        <p style="margin:0;color:#444;font-size:13px">A Terminal Aerodrome Forecast Encoding Software</p>
        <p style="margin:5px 0"><a href="https://github.com/up1and/tafor" style="text-decoration:none;color:#0078d7">{} {}</a></p>
        <p style="margin-top:25px;color:#444">Copyright © 2019 <a href="mailto:piratecb@gmail.com" style="text-decoration:none;color:#444">up1and</a></p>
        </div>
        """.format(QCoreApplication.translate('MainWindow', 'Version'), __version__)

        aboutBox = QMessageBox(self)
        aboutBox.setText(html)
        aboutBox.setWindowTitle(title)
        layout = aboutBox.layout()
        layout.removeItem(layout.itemAt(0))
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


def main():
    import sys
    scale = conf.value('General/InterfaceScaling') or 0
    os.environ['QT_SCALE_FACTOR'] = str(int(scale) * 0.25 + 1)

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

    try:
        window = MainWindow()
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        logger.error(e, exc_info=True)
    finally:
        localServer.close()


if __name__ == "__main__":
    main()