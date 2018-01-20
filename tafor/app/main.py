# -*- coding: utf-8 -*-
import os
import datetime

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtNetwork import QLocalSocket, QLocalServer
from PyQt5.QtMultimedia import QSound, QSoundEffect

from tafor import BASEDIR, conf, logger, boolean, __version__
from tafor.models import db, Tafor, Task, Metar, User
from tafor.utils import CheckTAF, Listen, remoteMessage, callService, callUp

from tafor.components.ui import Ui_main, main_rc
from tafor.components.taf import TAFEditor, TaskTAFEditor
from tafor.components.trend import TrendEditor
from tafor.components.send import TaskTAFSender, TAFSender, TrendSender
from tafor.components.setting import SettingDialog
from tafor.components.task import TaskBrowser

from tafor.components.widgets.widget import Clock, CurrentTAF, RecentTAF
from tafor.components.widgets.status import WebAPIStatus, CallServiceStatus
from tafor.components.widgets.sound import Sound


class Store(QtCore.QObject):
    warningSignal = QtCore.pyqtSignal()

    def __init__(self):
        super(Store, self).__init__()
        self._message = {}
        self._callService = None
        self._warning = False

    @property
    def message(self):
        return self._message

    @message.setter
    def message(self, msg):
        self._message = msg

    @property
    def webApi(self):
        return True if self._message else False

    @property
    def callService(self):
        return self._callService

    @callService.setter
    def callService(self, value):
        self._callService = value

    @property
    def warning(self):
        return self._warning

    @warning.setter
    def warning(self, value):
        self._warn = value
        self.warningSignal.emit()
        

class MainWindow(QtWidgets.QMainWindow, Ui_main.Ui_MainWindow):
    """
    主窗口
    """
    def __init__(self, parent=None):
        """
        初始化主窗口
        """
        super(MainWindow, self).__init__(parent)
        self.setupUi(self)

        self.store = Store()
        self.store.warningSignal.connect(self.dialer)

        # 初始化剪贴板
        self.clip = QtWidgets.QApplication.clipboard()

        # 初始TAF对话框
        self.tafEditDialog = TAFEditor(self)
        self.taskTafEditDialog = TaskTAFEditor(self)
        self.trendEditDialog = TrendEditor(self)

        self.tafSendDialog = TAFSender(self)
        self.taskTafSendDialog = TaskTAFSender(self)
        self.trendSendDialog = TrendSender(self)

        self.taskBrowserDialog = TaskBrowser(self)
        self.settingDialog = SettingDialog(self)

        # 连接TAF对话框信号
        self.tafEditDialog.previewSignal.connect(self.handleTafEdit)
        self.tafSendDialog.sendSignal.connect(self.updateGUI)
        self.tafSendDialog.backSignal.connect(self.tafEditDialog.show)
        self.tafSendDialog.closeSignal.connect(self.tafEditDialog.close)

        self.taskTafEditDialog.previewSignal.connect(self.handleTaskTafEdit)
        self.taskTafSendDialog.sendSignal.connect(self.handleTaskTafSend)

        self.trendEditDialog.previewSignal.connect(self.handleTrendEdit)
        self.trendSendDialog.sendSignal.connect(self.updateGUI)
        self.trendSendDialog.backSignal.connect(self.trendEditDialog.show)
        self.trendSendDialog.closeSignal.connect(self.trendEditDialog.close)

        # 连接菜单信号
        self.tafAction.triggered.connect(self.tafEditDialog.show)
        self.trendAction.triggered.connect(self.trendEditDialog.show)

        # 添加定时任务菜单
        # self.task_taf_action = QtWidgets.QAction(self)
        # self.post_menu.addAction(self.task_taf_action)
        # self.task_taf_action.setText('定时任务')
        # self.task_taf_action.triggered.connect(self.task_tafEditDialog.show)

        # 连接设置对话框的槽
        self.settingAction.triggered.connect(self.settingDialog.exec_)
        self.settingAction.triggered.connect(self.showWindow)
        self.settingAction.setIcon(QtGui.QIcon(':/setting.png'))

        # 连接关于信息的槽
        self.aboutAction.triggered.connect(self.about)
        self.aboutAction.triggered.connect(self.showWindow)

        self.reportIssueAction.triggered.connect(self.reportIssue)

        # 联系人选项组
        self.contractsActionGroup = QtWidgets.QActionGroup(self)
        self.contractsActionGroup.addAction(self.contractNo)

        # 连接切换联系人的槽
        self.contractsActionGroup.triggered.connect(self.changeContract)
        self.contractsActionGroup.triggered.connect(self.settingDialog.updateContract)

        # 连接报文表格复制的槽
        self.tafTable.itemDoubleClicked.connect(self.copySelectItem)
        self.metarTable.itemDoubleClicked.connect(self.copySelectItem)

        # 设置主窗口文字图标
        self.setWindowTitle('预报发报软件')
        self.setWindowIcon(QtGui.QIcon(':/logo.png'))

        self.setupRecent()

        # 设置切换联系人菜单
        self.setupChangeContractMenu()

        # 设置系统托盘
        self.setupSysTray()

        # 设置系统托盘
        self.setupStatusbar()

        # 载入声音
        self.ringSound = Sound('ring.wav', conf.value('Monitor/RemindTAFVolume'))
        self.notificationSound = Sound('notification.wav', 100)
        self.alarmSound = Sound('alarm.wav', conf.value('Monitor/WarnTAFVolume'))
        self.trendSound = Sound('trend.wav', conf.value('Monitor/RemindTrendVolume'))
        self.sigmetSound = Sound('sigmet.wav', conf.value('Monitor/RemindSIGMETVolume'))

        self.settingDialog.warnTAFVolume.valueChanged.connect(lambda vol: self.alarmSound.play(volume=vol, loop=False))
        self.settingDialog.remindTAFVolume.valueChanged.connect(lambda vol: self.ringSound.play(volume=vol, loop=False))
        self.settingDialog.remindTrendVolume.valueChanged.connect(lambda vol: self.trendSound.play(volume=vol, loop=False))
        self.settingDialog.remindSIGMETVolume.valueChanged.connect(lambda vol: self.sigmetSound.play(volume=vol, loop=False))

        # 时钟计时器
        self.clockTimer = QtCore.QTimer()
        self.clockTimer.timeout.connect(self.singer)
        self.clockTimer.start(1 * 1000)

        self.workerTimer = QtCore.QTimer()
        self.workerTimer.timeout.connect(self.worker)
        self.workerTimer.start(60 * 1000)

        self.updateGUI()
        self.worker()

    def setupRecent(self):
        self.clock = Clock(self, self.tipsLayout)
        self.tipsLayout.addSpacerItem(QtWidgets.QSpacerItem(10, 10, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum))
        self.currentTAF = CurrentTAF(self, self.tipsLayout)
        self.recentFT = RecentTAF(self, self.recentLayout, 'FT')
        self.recentFC = RecentTAF(self, self.recentLayout, 'FC')

    def setupChangeContractMenu(self):
        contacts = db.query(User).all()

        for person in contacts:
            setattr(self, 'contract' + str(person.id), QtWidgets.QAction(self))
            target = getattr(self, 'contract' + str(person.id))
            target.setText(person.name)
            target.setCheckable(True)

            self.contractsActionGroup.addAction(target)
            self.contractsMenu.addAction(target)

        mobile = conf.value('Monitor/SelectedMobile')
        person = db.query(User).filter_by(mobile=mobile).first()
        if person:
            getattr(self, 'contract' + str(person.id)).setChecked(True)
        else:
            self.contractNo.setChecked(True)

    def setupSysTray(self):
        # 设置系统托盘
        self.tray = QtWidgets.QSystemTrayIcon(self)
        self.tray.setIcon(QtGui.QIcon(':/logo.png'))
        self.tray.show()

        # 连接系统托盘的槽
        self.tray.activated.connect(self.restoreWindow)

        self.trayMenu = QtWidgets.QMenu(self)

        self.trayMenu.addAction(self.contractsMenu.menuAction())
        self.trayMenu.addAction(self.settingAction)
        self.trayMenu.addAction(self.aboutAction)
        self.trayMenu.addSeparator()
        self.trayMenu.addAction(self.quitAction)

        self.tray.setContextMenu(self.trayMenu)

        message = '预报发报软件 v' + __version__
        self.tray.setToolTip(message)

    def setupStatusbar(self):
        self.webApiStatus = WebAPIStatus(self, self.statusBar)
        self.callServiceStatus = CallServiceStatus(self, self.statusBar)

        # self.statusBar.setStyleSheet('QStatusBar::item{border: 0px}')

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

    def copySelectItem(self, item):
        self.clip.setText(item.text())
        self.statusBar.showMessage(item.text(), 5000)

    def handleTafEdit(self, message):
        logger.debug('Receive from taf edit ' + message['full'])
        self.tafEditDialog.hide()
        self.tafSendDialog.receive(message)
        self.tafSendDialog.show()

    def handleTaskTafEdit(self, message):
        logger.debug('Receive from task taf edit ' + message['full'])
        self.taskTafSendDialog.receive(message)
        self.taskTafSendDialog.show()

    def handleTrendEdit(self, message):
        logger.debug('Receive from task taf edit ' + message['full'])
        self.trendEditDialog.hide()
        self.trendSendDialog.receive(message)
        self.trendSendDialog.show()

    def handleTaskTafSend(self):
        self.taskTafEditDialog.hide()
        self.taskTafSendDialog.hide()
        self.taskTableDialog.show()
        self.taskTableDialog.update_gui()

    def singer(self):
        warnSwitch = conf.value('Monitor/WarnTAF')
        trendSwitch = conf.value('Monitor/RemindTrend')
        sigmetSwitch = conf.value('Monitor/RemindSIGMET')
        tafSwitch = conf.value('Monitor/RemindTAF')

        # 管理趋势声音
        utc = datetime.datetime.utcnow()
        if trendSwitch and utc.minute in (58, 59):
            self.trendSound.play()
        else:
            self.trendSound.stop()

        # 管理报文告警声音
        if warnSwitch and self.store.warning:
            self.alarmSound.play()
        else:
            self.alarmSound.stop()

    def event(self, event):
        """
        捕获事件
        """
        if event.type() == QtCore.QEvent.WindowStateChange and self.isMinimized():
            # 此时窗口已经最小化,
            # 从任务栏中移除窗口
            self.setWindowFlags(self.windowFlags() & QtCore.Qt.Tool)
            self.tray.show()
            return True
        else:
            return super(self.__class__, self).event(event)

    def keyPressEvent(self, event):
        if event.modifiers() == (QtCore.Qt.ShiftModifier | QtCore.Qt.ControlModifier):
            if event.key() == QtCore.Qt.Key_P:
                self.taskTafEditDialog.show()
            if event.key() == QtCore.Qt.Key_T:
                self.task_table_dialog.show()

    def closeEvent(self, event):
        if event.spontaneous():
            event.ignore()
            self.hide()
        else:
            self.tafEditDialog.setAttribute(QtCore.Qt.WA_DeleteOnClose)
            self.taskTafEditDialog.setAttribute(QtCore.Qt.WA_DeleteOnClose)
            self.tafSendDialog.setAttribute(QtCore.Qt.WA_DeleteOnClose)
            self.taskTafSendDialog.setAttribute(QtCore.Qt.WA_DeleteOnClose)
            self.taskBrowserDialog.setAttribute(QtCore.Qt.WA_DeleteOnClose)
            self.settingDialog.setAttribute(QtCore.Qt.WA_DeleteOnClose)

            self.tafEditDialog.close()
            self.taskTafEditDialog.close()
            self.tafSendDialog.close()
            self.taskTafSendDialog.close()
            self.taskBrowserDialog.close()
            self.settingDialog.close()

            self.tray.hide()
            event.accept()

    def restoreWindow(self, reason):
        """
        恢复窗口
        """
        if reason == QtWidgets.QSystemTrayIcon.Trigger:
            self.showNormal()

    def showWindow(self):
        if self.isMinimized():
            self.showNormal()

    def worker(self):
        thread = WorkThread(self)
        thread.doneSignal.connect(self.updateMessage)
        thread.start()

    def dialer(self, test=False):
        callSwitch = boolean(conf.value('monitor/phone/phone_warn_taf'))

        if callSwitch and self.store.warn or test:
            thread = CallThread(self)
            thread.start()

    def updateMessage(self):
        listen = Listen(self.store)
        [listen(i) for i in ('FC', 'FT', 'SA', 'SP')]

        self.updateGUI()

    def updateGUI(self):
        self.updateTafTable()
        self.updateMetarTable()
        self.updateRecent()

        logger.debug('Update GUI')

    def updateRecent(self):
        self.currentTAF.updateGUI()
        self.recentFT.updateGUI()
        self.recentFC.updateGUI()

    def updateTafTable(self):
        recent = datetime.datetime.utcnow() - datetime.timedelta(hours=24)
        items = db.query(Tafor).filter(Tafor.sent > recent).order_by(Tafor.sent.desc()).all()
        header = self.tafTable.horizontalHeader()
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        self.tafTable.setRowCount(len(items))
        self.tafTable.setColumnWidth(0, 50)
        self.tafTable.setColumnWidth(2, 140)
        self.tafTable.setColumnWidth(3, 50)
        self.tafTable.setColumnWidth(4, 50)

        for row, item in enumerate(items):
            self.tafTable.setItem(row, 0,  QtWidgets.QTableWidgetItem(item.tt))
            self.tafTable.setItem(row, 1,  QtWidgets.QTableWidgetItem(item.rptInline))
            if item.sent:
                sent = item.sent.strftime("%Y-%m-%d %H:%M:%S")
                self.tafTable.setItem(row, 2,  QtWidgets.QTableWidgetItem(sent))

            if item.confirmed:
                checkedItem = QtWidgets.QTableWidgetItem()
                checkedItem.setTextAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
                checkedItem.setIcon(QtGui.QIcon(':/checkmark.png'))
                self.tafTable.setItem(row, 3, checkedItem)
            else:
                checkedItem = QtWidgets.QTableWidgetItem()
                checkedItem.setTextAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
                checkedItem.setIcon(QtGui.QIcon(':/cross.png'))
                self.tafTable.setItem(row, 3, checkedItem)

            # if item.task:
            #     task_item = QtWidgets.QTableWidgetItem('√')
            #     # schedule_item.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
            #     # schedule_item.setIcon(QIcon(':/time.png'))
            #     self.tafTable.setItem(row, 4, task_item)


        self.tafTable.setStyleSheet("QTableWidget::item {padding: 5px 0;}")
        self.tafTable.resizeRowsToContents()


    def updateMetarTable(self):
        recent = datetime.datetime.utcnow() - datetime.timedelta(hours=24)
        items = db.query(Metar).filter(Metar.created > recent).order_by(Metar.created.desc()).all()
        header = self.metarTable.horizontalHeader()
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        self.metarTable.setRowCount(len(items))
        self.metarTable.setColumnWidth(0, 50)

        for row, item in enumerate(items):
            self.metarTable.setItem(row, 0,  QtWidgets.QTableWidgetItem(item.tt))
            self.metarTable.setItem(row, 1,  QtWidgets.QTableWidgetItem(item.rpt))
            if item.tt == 'SP':
                self.metarTable.item(row, 0).setForeground(QtCore.Qt.red)
                self.metarTable.item(row, 1).setForeground(QtCore.Qt.red)

        self.metarTable.setStyleSheet("QTableWidget::item {padding: 5px 0;}")
        self.metarTable.resizeRowsToContents()

    def about(self):
        QtWidgets.QMessageBox.about(self, "预报报文发布软件",
                """<b>预报报文发布软件</b> v <a href="https://github.com/up1and/tafor">%s</a>
                <p>本软件用于智能发布预报报文、趋势报文、重要气象情报、低空气象情报，监控预报报文，以声音或电话的方式返回告警
                <p>项目遵循 GPL-2.0 协议，欢迎提交 Pull Request 或者 Issue
                <p>
                """ % (__version__))

    def reportIssue(self):
        QtGui.QDesktopServices.openUrl(QtCore.QUrl('https://github.com/up1and/tafor/issues'))

class WorkThread(QtCore.QThread):
    """
    检查预报报文线程类
    """
    doneSignal = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super(WorkThread, self).__init__(parent)
        self.parent = parent

    def run(self):
        if (boolean(conf.value('Monitor/WebApi'))):
            self.parent.ctx.message = remoteMessage()

        if (boolean(conf.value('Monitor/SelectedMobile'))):
            self.parent.ctx.callService = callService()

        self.doneSignal.emit()


class CallThread(QtCore.QThread):
    def __init__(self, parent=None):
        super(CallThread, self).__init__(parent)
        self.parent = parent

    def run(self):
        mobile = conf.value('Monitor/SelectedMobile')
        callUp(mobile)



def main():
    import sys
    app = QtWidgets.QApplication(sys.argv)

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