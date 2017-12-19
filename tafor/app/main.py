# -*- coding: utf-8 -*-
import os
import datetime

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtNetwork import QLocalSocket, QLocalServer
from PyQt5.QtMultimedia import QSound, QSoundEffect

from tafor import BASEDIR, conf, logger, boolean, __version__
from tafor.models import db, Tafor, Task, Metar, User
from tafor.utils import CheckTAF, Listen, remote_message, call_service, call_up
from tafor.widgets.ui import Ui_main, main_rc
from tafor.widgets.taf import TAFEdit, TaskTAFEdit
from tafor.widgets.trend import TrendEdit
from tafor.widgets.send import TaskTAFSend, TAFSend, TrendSend
from tafor.widgets.settings import SettingDialog
from tafor.widgets.tasks import TaskTable
from tafor.widgets.widget import Clock, CurrentTAF, RecentTAF
from tafor.widgets.status import WebAPIStatus, CallServiceStatus
from tafor.widgets.sound import Sound


class Context(QtCore.QObject):
    warned = QtCore.pyqtSignal()

    def __init__(self):
        super(Context, self).__init__()
        self._message = None
        self._web_api = None
        self._call_service = None
        self._warn = False

    @property
    def message(self):
        return self._message

    @message.setter
    def message(self, msg):
        self._message = msg

    @property
    def web_api(self):
        return True if self._message else False

    @property
    def call_service(self):
        return self._call_service

    @call_service.setter
    def call_service(self, value):
        self._call_service = value

    @property
    def warn(self):
        return self._warn

    @warn.setter
    def warn(self, value):
        self._warn = value
        self.warned.emit()
        

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

        self.ctx = Context()
        self.ctx.warned.connect(self.dialer)

        # 初始化剪贴板
        self.clip = QtWidgets.QApplication.clipboard()

        # 初始TAF对话框
        self.taf_edit_dialog = TAFEdit(self)
        self.task_taf_edit_dialog = TaskTAFEdit(self)
        self.trend_edit_dialog = TrendEdit(self)

        self.taf_send_dialog = TAFSend(self)
        self.task_taf_send_dialog = TaskTAFSend(self)
        self.trend_send_dialog = TrendSend(self)

        self.task_table_dialog = TaskTable(self)
        self.setting_dialog = SettingDialog(self)

        # 连接TAF对话框信号
        self.taf_edit_dialog.signal_preview.connect(self.handle_taf_edit)
        self.taf_send_dialog.signal_send.connect(self.update_gui)
        self.taf_send_dialog.signal_back.connect(self.taf_edit_dialog.show)
        self.taf_send_dialog.signal_close.connect(self.taf_edit_dialog.close)

        self.task_taf_edit_dialog.signal_preview.connect(self.handle_task_taf_edit)
        self.task_taf_send_dialog.signal_send.connect(self.handle_task_taf_send)

        self.trend_edit_dialog.signal_preview.connect(self.handle_trend_edit)
        self.trend_send_dialog.signal_send.connect(self.update_gui)
        self.trend_send_dialog.signal_back.connect(self.trend_edit_dialog.show)
        self.trend_send_dialog.signal_close.connect(self.trend_edit_dialog.close)

        # 连接菜单信号
        self.taf_action.triggered.connect(self.taf_edit_dialog.show)
        self.trend_action.triggered.connect(self.trend_edit_dialog.show)

        # 添加定时任务菜单
        # self.task_taf_action = QtWidgets.QAction(self)
        # self.post_menu.addAction(self.task_taf_action)
        # self.task_taf_action.setText('定时任务')
        # self.task_taf_action.triggered.connect(self.task_taf_edit_dialog.show)

        # 连接设置对话框的槽
        self.setting_action.triggered.connect(self.setting_dialog.exec_)
        self.setting_action.triggered.connect(self.show_window)
        self.setting_action.setIcon(QtGui.QIcon(':/setting.png'))

        # 连接关于信息的槽
        self.about_action.triggered.connect(self.about)
        self.about_action.triggered.connect(self.show_window)

        self.report_issue_action.triggered.connect(self.report_issue)

        # 联系人选项组
        self.contracts_action_group = QtWidgets.QActionGroup(self)
        self.contracts_action_group.addAction(self.contract_no)

        # 连接切换联系人的槽
        self.contracts_action_group.triggered.connect(self.change_contract)
        self.contracts_action_group.triggered.connect(self.setting_dialog.update_contract)

        # 连接报文表格复制的槽
        self.taf_table.itemDoubleClicked.connect(self.copy_select_item)
        self.metar_table.itemDoubleClicked.connect(self.copy_select_item)

        # 设置主窗口文字图标
        self.setWindowTitle('预报发报软件')
        self.setWindowIcon(QtGui.QIcon(':/logo.png'))

        self.setup_recent()

        # 设置切换联系人菜单
        self.setup_change_contract_menu()

        # 设置系统托盘
        self.setup_sys_tray()

        # 设置系统托盘
        self.setup_statusbar()

        # 载入声音
        self.sound_ring = Sound('ring.wav', conf.value('monitor/clock/clock_volume'))
        self.sound_notify = Sound('notify.wav', 100)
        self.sound_alarm = Sound('alarm.wav', conf.value('monitor/sound/warn_taf_volume'))
        self.sound_trend = Sound('trend.wav', conf.value('monitor/sound/remind_trend_volume'))
        self.sound_sigmet = Sound('sigmet.wav', conf.value('monitor/sound/remind_sigmet_volume'))

        self.setting_dialog.clock_volume.valueChanged.connect(lambda vol: self.sound_ring.play(volume=vol, loop=False))
        self.setting_dialog.warn_taf_volume.valueChanged.connect(lambda vol: self.sound_alarm.play(volume=vol, loop=False))
        self.setting_dialog.remind_trend_volume.valueChanged.connect(lambda vol: self.sound_trend.play(volume=vol, loop=False))
        self.setting_dialog.remind_sigmet_volume.valueChanged.connect(lambda vol: self.sound_sigmet.play(volume=vol, loop=False))

        # 时钟计时器
        self.clock_timer = QtCore.QTimer()
        self.clock_timer.timeout.connect(self.singer)
        self.clock_timer.start(1 * 1000)

        self.worker_timer = QtCore.QTimer()
        self.worker_timer.timeout.connect(self.worker)
        self.worker_timer.start(60 * 1000)

        self.update_gui()
        self.worker()

    def setup_recent(self):
        self.clock = Clock(self, self.tips_layout)
        self.tips_layout.addSpacerItem(QtWidgets.QSpacerItem(10, 10, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum))
        self.current_taf = CurrentTAF(self, self.tips_layout)
        self.recent_ft = RecentTAF(self, self.recent_layout, 'FT')
        self.recent_fc = RecentTAF(self, self.recent_layout, 'FC')

    def setup_change_contract_menu(self):
        contacts = db.query(User).all()

        for person in contacts:
            setattr(self, 'contract_' + str(person.id), QtWidgets.QAction(self))
            target = getattr(self, 'contract_' + str(person.id))
            target.setText(person.name)
            target.setCheckable(True)

            self.contracts_action_group.addAction(target)
            self.contracts_menu.addAction(target)

        mobile = conf.value('monitor/phone/selected_mobile')
        person = db.query(User).filter_by(mobile=mobile).first()
        if conf.value('monitor/phone/phone_warn_taf') and person:
            getattr(self, 'contract_' + str(person.id)).setChecked(True)
        else:
            self.contract_no.setChecked(True)

    def setup_sys_tray(self):
        # 设置系统托盘
        self.tray = QtWidgets.QSystemTrayIcon(self)
        self.tray.setIcon(QtGui.QIcon(':/logo.png'))
        self.tray.show()

        # 连接系统托盘的槽
        self.tray.activated.connect(self.restore_window)

        self.tray_menu = QtWidgets.QMenu(self)

        self.tray_menu.addAction(self.contracts_menu.menuAction())
        self.tray_menu.addAction(self.setting_action)
        self.tray_menu.addAction(self.about_action)
        self.tray_menu.addSeparator()
        self.tray_menu.addAction(self.quit_action)

        self.tray.setContextMenu(self.tray_menu)

        message = '预报发报软件 v' + __version__
        self.tray.setToolTip(message)

    def setup_statusbar(self):
        self.web_api_status = WebAPIStatus(self, self.statusbar)
        self.call_service_status = CallServiceStatus(self, self.statusbar)

        # self.statusbar.setStyleSheet('QStatusBar::item{border: 0px}')

    def change_contract(self):
        target = self.contracts_action_group.checkedAction()

        if self.contract_no == target:
            conf.setValue('monitor/phone/selected_mobile', '')
            logger.info('关闭电话提醒')
        else:
            name = target.text()
            person = db.query(User).filter_by(name=name).first()
            mobile = person.mobile if person else ''

            conf.setValue('monitor/phone/selected_mobile', mobile)
            logger.info('切换联系人 %s %s' % (name, mobile))

    def copy_select_item(self, item):
        self.clip.setText(item.text())
        self.statusbar.showMessage(item.text(), 5000)

    def handle_taf_edit(self, message):
        logger.debug('Receive from taf edit ' + message['full'])
        self.taf_edit_dialog.hide()
        self.taf_send_dialog.receive(message)
        self.taf_send_dialog.show()

    def handle_task_taf_edit(self, message):
        logger.debug('Receive from task taf edit ' + message['full'])
        self.task_taf_send_dialog.receive(message)
        self.task_taf_send_dialog.show()

    def handle_trend_edit(self, message):
        logger.debug('Receive from task taf edit ' + message['full'])
        self.trend_edit_dialog.hide()
        self.trend_send_dialog.receive(message)
        self.trend_send_dialog.show()

    def handle_task_taf_send(self):
        self.task_taf_edit_dialog.hide()
        self.task_taf_send_dialog.hide()
        self.task_table_dialog.show()
        self.task_table_dialog.update_gui()

    def singer(self):
        trend_switch = conf.value('monitor/sound/remind_trend')
        taf_switch = conf.value('monitor/sound/warn_taf')
        sigmet_switch = conf.value('monitor/sound/remind_sigmet')
        clock_switch = conf.value('monitor/sound/clock')

        # 管理趋势声音
        utc = datetime.datetime.utcnow()
        if trend_switch and utc.minute in (58, 59):
            self.sound_trend.play()
        else:
            self.sound_trend.stop()

        # 管理报文告警声音
        if taf_switch and self.ctx.warn:
            self.sound_alarm.play()
        else:
            self.sound_alarm.stop()

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
                self.task_taf_edit_dialog.show()
            if event.key() == QtCore.Qt.Key_T:
                self.task_table_dialog.show()

    def closeEvent(self, event):
        if event.spontaneous():
            event.ignore()
            self.hide()
        else:
            self.taf_edit_dialog.setAttribute(QtCore.Qt.WA_DeleteOnClose)
            self.task_taf_edit_dialog.setAttribute(QtCore.Qt.WA_DeleteOnClose)
            self.taf_send_dialog.setAttribute(QtCore.Qt.WA_DeleteOnClose)
            self.task_taf_send_dialog.setAttribute(QtCore.Qt.WA_DeleteOnClose)
            self.task_table_dialog.setAttribute(QtCore.Qt.WA_DeleteOnClose)
            self.setting_dialog.setAttribute(QtCore.Qt.WA_DeleteOnClose)

            self.taf_edit_dialog.close()
            self.task_taf_edit_dialog.close()
            self.taf_send_dialog.close()
            self.task_taf_send_dialog.close()
            self.task_table_dialog.close()
            self.setting_dialog.close()

            self.tray.hide()
            event.accept()

    def restore_window(self, reason):
        """
        恢复窗口
        """
        if reason == QtWidgets.QSystemTrayIcon.Trigger:
            self.showNormal()

    def show_window(self):
        if self.isMinimized():
            self.showNormal()

    def worker(self):
        thread = WorkThread(self)
        thread.done.connect(self.update_message)
        thread.start()

    def dialer(self, test=False):
        call_switch = boolean(conf.value('monitor/phone/phone_warn_taf'))

        if call_switch and self.ctx.warn or test:
            thread = CallThread(self)
            thread.start()

    def update_message(self):
        listen = Listen(self.ctx)
        [listen(i) for i in ('FC', 'FT', 'SA', 'SP')]

        self.update_gui()

    def update_gui(self):
        self.update_taf_table()
        self.update_metar_table()
        self.update_recent()

        logger.debug('Update GUI')

    def update_recent(self):
        self.current_taf.update_gui()
        self.recent_ft.update_gui()
        self.recent_fc.update_gui()

    def update_taf_table(self):
        recent = datetime.datetime.utcnow() - datetime.timedelta(hours=24)
        items = db.query(Tafor).filter(Tafor.sent > recent).order_by(Tafor.sent.desc()).all()
        header = self.taf_table.horizontalHeader()
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        self.taf_table.setRowCount(len(items))
        self.taf_table.setColumnWidth(0, 50)
        self.taf_table.setColumnWidth(2, 140)
        self.taf_table.setColumnWidth(3, 50)
        self.taf_table.setColumnWidth(4, 50)

        for row, item in enumerate(items):
            self.taf_table.setItem(row, 0,  QtWidgets.QTableWidgetItem(item.tt))
            self.taf_table.setItem(row, 1,  QtWidgets.QTableWidgetItem(item.rpt_inline))
            if item.sent:
                sent = item.sent.strftime("%Y-%m-%d %H:%M:%S")
                self.taf_table.setItem(row, 2,  QtWidgets.QTableWidgetItem(sent))

            if item.confirmed:
                check_item = QtWidgets.QTableWidgetItem()
                check_item.setTextAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
                check_item.setIcon(QtGui.QIcon(':/checkmark.png'))
                self.taf_table.setItem(row, 3, check_item)
            else:
                check_item = QtWidgets.QTableWidgetItem()
                check_item.setTextAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
                check_item.setIcon(QtGui.QIcon(':/cross.png'))
                self.taf_table.setItem(row, 3, check_item)

            # if item.task:
            #     task_item = QtWidgets.QTableWidgetItem('√')
            #     # schedule_item.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
            #     # schedule_item.setIcon(QIcon(':/time.png'))
            #     self.taf_table.setItem(row, 4, task_item)


        self.taf_table.setStyleSheet("QTableWidget::item {padding: 5px 0;}")
        self.taf_table.resizeRowsToContents()


    def update_metar_table(self):
        recent = datetime.datetime.utcnow() - datetime.timedelta(hours=24)
        items = db.query(Metar).filter(Metar.created > recent).order_by(Metar.created.desc()).all()
        header = self.metar_table.horizontalHeader()
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        self.metar_table.setRowCount(len(items))
        self.metar_table.setColumnWidth(0, 50)

        for row, item in enumerate(items):
            self.metar_table.setItem(row, 0,  QtWidgets.QTableWidgetItem(item.tt))
            self.metar_table.setItem(row, 1,  QtWidgets.QTableWidgetItem(item.rpt))
            if item.tt == 'SP':
                self.metar_table.item(row, 0).setForeground(QtCore.Qt.red)
                self.metar_table.item(row, 1).setForeground(QtCore.Qt.red)

        self.metar_table.setStyleSheet("QTableWidget::item {padding: 5px 0;}")
        self.metar_table.resizeRowsToContents()

    def about(self):
        QtWidgets.QMessageBox.about(self, "预报报文发布软件",
                """<b>预报报文发布软件</b> v <a href="https://github.com/up1and/tafor">%s</a>
                <p>本软件用于智能发布预报报文、趋势报文、重要气象情报、低空气象情报，监控预报报文，以声音或电话的方式返回告警
                <p>项目遵循 GPL-2.0 协议，欢迎提交 Pull Request 或者 Issue
                <p>
                """ % (__version__))

    def report_issue(self):
        QtGui.QDesktopServices.openUrl(QtCore.QUrl('https://github.com/up1and/tafor/issues'))

class WorkThread(QtCore.QThread):
    """
    检查预报报文线程类
    """
    done = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super(WorkThread, self).__init__(parent)
        self.parent = parent

    def run(self):
        if (boolean(conf.value('monitor/db/web_api'))):
            self.parent.ctx.message = remote_message()

        if (boolean(conf.value('monitor/phone/phone_warn_taf'))):
            self.parent.ctx.call_service = call_service()

        self.done.emit()


class CallThread(QtCore.QThread):
    def __init__(self, parent=None):
        super(CallThread, self).__init__(parent)
        self.parent = parent

    def run(self):
        mobile = conf.value('monitor/phone/selected_mobile')
        call_up(mobile)



def main():
    import sys
    app = QtWidgets.QApplication(sys.argv)

    server_name = 'Tafor'  
    socket = QLocalSocket()  
    socket.connectToServer(server_name)

    # 如果连接成功，表明server已经存在，当前已有实例在运行
    if socket.waitForConnected(500):
        return(app.quit())

    # 没有实例运行，创建服务器     
    local_server = QLocalServer()
    local_server.listen(server_name)

    try:          
        window = MainWindow()
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        logger.error(e, exc_info=True)
    finally:  
        local_server.close()


if __name__ == "__main__":
    main()