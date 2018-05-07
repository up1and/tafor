import os
import datetime

from PyQt5.QtGui import QIcon, QFont, QDesktopServices
from PyQt5.QtCore import QCoreApplication, QTranslator, QLocale, QEvent, QTimer, Qt, QUrl
from PyQt5.QtWidgets import (QMainWindow, QApplication, QSpacerItem, QSizePolicy, QActionGroup, QAction, 
        QSystemTrayIcon, QMenu, QMessageBox)
from PyQt5.QtNetwork import QLocalSocket, QLocalServer

from tafor import BASEDIR, conf, logger, boolean, __version__
from tafor.models import db, User
from tafor.states import context
from tafor.utils import Listen, checkVersion
from tafor.utils.thread import WorkThread, FirInfoThread, CallThread, CheckUpgradeThread

from tafor.components.ui import Ui_main, main_rc
from tafor.components.taf import TafEditor, TaskTafEditor
from tafor.components.trend import TrendEditor
from tafor.components.sigmet import SigmetEditor
from tafor.components.send import TaskTafSender, TafSender, TrendSender, SigmetSender, ReSender
from tafor.components.setting import SettingDialog
from tafor.components.task import TaskBrowser

from tafor.components.widgets.table import TafTable, MetarTable, SigmetTable
from tafor.components.widgets.widget import Clock, CurrentTaf, RecentMessage, RemindMessageBox
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
        self.workerTimer.start(60 * 1000)

        self.setup()
        self.bindSignal()
        self.updateGui()
        self.worker()
        self.painter()

    def setup(self):
        self.setWindowIcon(QIcon(':/logo.png'))

        # 初始化剪贴板
        self.clip = QApplication.clipboard()

        # 闹钟提示框
        self.remindBox = RemindMessageBox(self)

        # 初始化窗口
        self.settingDialog = SettingDialog(self)

        self.tafSender = TafSender(self)
        self.trendSender = TrendSender(self)
        self.sigmetSender = SigmetSender(self)
        self.reSender = ReSender(self)

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

    def setRecent(self):
        self.clock = Clock(self, self.tipsLayout)
        self.tipsLayout.addSpacerItem(QSpacerItem(10, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))
        self.currentTaf = CurrentTaf(self, self.tipsLayout)
        self.recentFt = RecentMessage(self, self.recentLayout, 'FT')
        self.recentFc = RecentMessage(self, self.recentLayout, 'FC')
        self.recentSigmet = RecentMessage(self, self.recentLayout, 'WS')
        self.recentTrend = RecentMessage(self, self.recentLayout, 'TREND')

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

        title = QCoreApplication.translate('MainWindow', 'Terminal Aerodrome Forecast Encoding Software')
        message =  '{} v {}'.format(title, __version__)
        self.tray.setToolTip(message)

    def setStatus(self):
        self.webApiStatus = WebAPIStatus(self, self.statusBar)
        self.callServiceStatus = CallServiceStatus(self, self.statusBar, last=True)

        # self.statusBar.setStyleSheet('QStatusBar::item{border: 0px}')

    def setThread(self):
        self.workThread = WorkThread(self)
        self.workThread.finished.connect(self.updateMessage)

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
            logger.info('关闭电话提醒')
        else:
            name = target.text()
            person = db.query(User).filter_by(name=name).first()
            mobile = person.mobile if person else ''

            conf.setValue('Monitor/SelectedMobile', mobile)
            logger.info('切换联系人 %s %s' % (name, mobile))

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
            self.reSender.setAttribute(Qt.WA_DeleteOnClose)
            self.tafEditor.setAttribute(Qt.WA_DeleteOnClose)
            self.trendEditor.setAttribute(Qt.WA_DeleteOnClose)
            self.sigmetEditor.setAttribute(Qt.WA_DeleteOnClose)
            self.settingDialog.setAttribute(Qt.WA_DeleteOnClose)

            self.tafSender.close()
            self.trendSender.close()
            self.sigmetSender.close()
            self.reSender.close()
            self.tafEditor.close()
            self.trendEditor.close()
            self.sigmetEditor.close()
            self.settingDialog.close()

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
        if trendSwitch and utc.minute in (58, 59):
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
        utc = datetime.datetime.utcnow()
        nextTime = utc.replace(microsecond=0, second=0, minute=0) + datetime.timedelta(hours=1, minutes=10)
        delta = nextTime - utc
        QTimer.singleShot(delta.total_seconds() * 1000, self.painter)
        if conf.value('Monitor/FirApiURL'):
            self.firInfoThread.start()

    def dialer(self, test=False):
        callSwitch = conf.value('Monitor/SelectedMobile')

        if callSwitch and context.taf.isWarning() or test:
            self.callThread.start()

    def remindTaf(self, tt):
        remindSwitch = boolean(conf.value('Monitor/RemindTAF'))
        if not remindSwitch:
            return None

        state = context.taf.state()
        clock = state[tt]['clock']
        period = state[tt]['period']
        sent = state[tt]['sent']
        warnning = state[tt]['warnning']

        if clock and not warnning and not sent:
            current = tt + period[2:]
            text = QCoreApplication.translate('MainWindow', 'Time to post {}').format(current)
            self.ringSound.play()
            self.remindBox.setText(text)
            ret = self.remindBox.exec_()
            if not ret:
                QTimer.singleShot(1000 * 60 * 5, lambda: self.remindTaf(tt))

            self.ringSound.stop()

    def remindSigmet(self):
        remindSwitch = boolean(conf.value('Monitor/RemindSIGMET'))
        if not remindSwitch:
            return None

        text = QCoreApplication.translate('MainWindow', 'Time to post {}').format('SIGMET')
        self.sigmetSound.play()
        self.remindBox.setText(text)
        ret = self.remindBox.exec_()
        if not ret:
            QTimer.singleShot(1000 * 60 * 5, self.remindSigmet)

        self.sigmetSound.stop()

    def updateMessage(self):
        listen = Listen(parent=self)
        [listen(i) for i in ('FC', 'FT', 'SA', 'SP')]

        self.updateGui()

    def updateGui(self):
        self.updateTable()
        self.updateRecent()
        self.updateContractMenu()

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
        self.currentTaf.updateGui()
        self.recentFt.updateGui()
        self.recentFc.updateGui()
        self.recentSigmet.updateGui()
        self.recentTrend.updateGui()

    def updateTable(self):
        self.tafTable.updateGui()
        self.metarTable.updateGui()
        self.sigmetTable.updateGui()

    def about(self):
        title = QCoreApplication.translate('MainWindow', 'Terminal Aerodrome Forecast Encoding Software')
        head = '<b>{}</b> v <a href="https://github.com/up1and/tafor">{}</a>'.format(title, __version__)
        description = QCoreApplication.translate('MainWindow', 
                    '''The software is used to encode and post terminal aerodrome forecast, trend forecast, 
                    significant meteorological information, monitor the message, return the alarm by sound or telephone''')
        tail = QCoreApplication.translate('MainWindow', 
                    '''The project is under GPL-2.0 License, Pull Request and Issue are welcome''')
        copyright = '<br/>© UP1AND 2018'
        text = '<p>'.join([head, description, tail, copyright])

        self.showNormal()
        QMessageBox.about(self, title, text)

    def openDocs(self):
        devDocs = os.path.join(BASEDIR, '../docs/_build/html/index.html')
        releaseDocs = os.path.join(BASEDIR, 'docs/_build/html/index.html')

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
    app = QApplication(sys.argv)
    translator = QTranslator()
    locale = QLocale.system().name()
    translateFile = os.path.join(BASEDIR, 'i18n\\translations', '{}.qm'.format(locale))
    if translator.load(translateFile):
        app.installTranslator(translator)

    # QApplication.setStyle(QStyleFactory.create('Fusion'))

    if boolean(conf.value('General/LargeFont')):
        font = QFont('Courier New', 14)
        app.setFont(font)

    serverName = 'Tafor'
    socket = QLocalSocket()
    socket.connectToServer(serverName)

    # 如果连接成功，表明server已经存在，当前已有实例在运行
    if socket.waitForConnected(500):
        return(app.quit())

    # 没有实例运行，创建服务器     
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