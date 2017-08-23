# -*- coding: utf-8 -*-
import os
import datetime

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtNetwork import QLocalSocket, QLocalServer
from PyQt5.QtMultimedia import QSound, QSoundEffect

from tafor.widgets.ui import Ui_main, main_rc
from tafor.widgets.taf import TAFEdit, TaskTAFEdit
from tafor.widgets.trend import TrendEdit
from tafor.widgets.send import TaskTAFSend, TAFSend, TrendSend
from tafor.widgets.settings import SettingDialog
from tafor.widgets.tasks import TaskTable
from tafor.models import Session, Tafor, Task, Metar, User
from tafor.widgets.common import Clock, CurrentTAF, RecentTAF
from tafor.widgets.status import WebAPIStatus, CallServiceStatus
from tafor.utils import CheckTAF, Listen, remote_message
from tafor import BASEDIR, setting, log, boolean, __version__


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

        self.db = Session()

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

        # # 添加定时任务菜单
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

        # 联系人选项组
        self.contracts_action_group = QtWidgets.QActionGroup(self)
        self.contracts_action_group.addAction(self.contract_no)

        # 连接切换联系人的槽
        self.contracts_action_group.triggered.connect(self.change_phone_number)
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

        # 设置上下文
        self.context()

        # 载入声音
        self.sounds = {}
        self.sound_ring = self.setup_sound('ring')
        self.sound_notify = self.setup_sound('notify')
        self.sound_alarm = self.setup_sound('alarm')
        self.sound_trend = self.setup_sound('trend')
        self.sound_sigmet = self.setup_sound('sigmet')

        self.setting_dialog.clock_volume.valueChanged.connect(lambda vol: self.play_sound('ring', volume=vol, loop=False))
        self.setting_dialog.warn_taf_volume.valueChanged.connect(lambda vol: self.play_sound('alarm', volume=vol, loop=False))
        self.setting_dialog.remind_trend_volume.valueChanged.connect(lambda vol: self.play_sound('trend', volume=vol, loop=False))
        self.setting_dialog.remind_sigmet_volume.valueChanged.connect(lambda vol: self.play_sound('sigmet', volume=vol, loop=False))

        # 自动发送报文的计时器
        self.auto_sent = QtCore.QTimer()
        self.auto_sent.timeout.connect(self.task_taf_send_dialog.auto_send)
        self.auto_sent.start(30 * 1000)

        # 时钟计时器
        self.clock_timer = QtCore.QTimer()
        self.clock_timer.timeout.connect(self.taf_edit_dialog.update_date)
        self.clock_timer.timeout.connect(self.manage_sound)
        self.clock_timer.start(1 * 1000)

        self.worker_timer = QtCore.QTimer()
        self.worker_timer.timeout.connect(self.update_gui)
        self.worker_timer.timeout.connect(self.task_table_dialog.update_gui)
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
        contacts = self.db.query(User).all()

        for person in contacts:
            setattr(self, 'contract_' + str(person.id), QtWidgets.QAction(self))
            target = getattr(self, 'contract_' + str(person.id))
            target.setText(person.name)
            target.setCheckable(True)

            self.contracts_action_group.addAction(target)
            self.contracts_menu.addAction(target)

        phone_number = setting.value('monitor/phone/select_phone_number')
        person = self.db.query(User).filter_by(phone_number=phone_number).first()
        if setting.value('monitor/phone/phone_warn_taf') and person:
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

    def change_phone_number(self):
        target = self.contracts_action_group.checkedAction()

        if self.contract_no == target:
            setting.setValue('monitor/phone/phone_warn_taf', False)
        else:
            name = target.text()
            person = self.db.query(User).filter_by(name=name).first()
            phone_number = person.phone_number if person else ''

            setting.setValue('monitor/phone/phone_warn_taf', True)
            setting.setValue('monitor/phone/select_phone_number', phone_number)

    def copy_select_item(self, item):
        self.clip.setText(item.text())
        self.statusbar.showMessage(item.text(), 5000)

    def handle_taf_edit(self, message):
        log.debug('Receive from taf edit ' + message['full'])
        self.taf_edit_dialog.hide()
        self.taf_send_dialog.receive(message)
        self.taf_send_dialog.show()

    def handle_task_taf_edit(self, message):
        log.debug('Receive from task taf edit ' + message['full'])
        self.task_taf_send_dialog.receive(message)
        self.task_taf_send_dialog.show()

    def handle_trend_edit(self, message):
        log.debug('Receive from task taf edit ' + message['full'])
        self.trend_edit_dialog.hide()
        self.trend_send_dialog.receive(message)
        self.trend_send_dialog.show()

    def handle_task_taf_send(self):
        self.task_taf_edit_dialog.hide()
        self.task_taf_send_dialog.hide()
        self.task_table_dialog.show()
        self.task_table_dialog.update_gui()

    def setup_sound(self, name):
        sounds = {
            'alarm': 'alarm.wav',
            'notify': 'notify.wav',
            'ring': 'ring.wav',
            'sigmet': 'sigmet.wav',
            'trend': 'trend.wav'
        }

        volume = {
            'alarm': setting.value('monitor/sound/warn_taf_volume') or 0,
            'notify': 100,
            'ring': setting.value('monitor/clock/clock_volume') or 0,
            'sigmet': setting.value('monitor/sound/remind_sigmet_volume') or 0,
            'trend': setting.value('monitor/sound/remind_trend_volume') or 0
        }

        file = os.path.join(BASEDIR, 'sounds', sounds[name])

        effect = QSoundEffect()
        effect.setSource(QtCore.QUrl.fromLocalFile(file))

        self.sounds[name] = [effect, volume[name]]

        return effect

    def play_sound(self, name, volume=None, loop=True):
        sound = self.sounds[name][0]
        volume = self.sounds[name][1] if volume is None else volume
        sound.setLoopCount(0)
        sound.setVolume(int(volume)/100)

        if loop:
            sound.setLoopCount(QSoundEffect.Infinite)
        else:
            sound.setLoopCount(1)
        
        if not sound.isPlaying():
            sound.play()

    def stop_sound(self, name):
        sound = self.sounds[name][0]
        sound.stop()

    def manage_sound(self):
        trend_switch = setting.value('monitor/sound/remind_trend')
        taf_switch = setting.value('monitor/sound/warn_taf')
        sigmet_switch = setting.value('monitor/sound/remind_sigmet')
        clock_switch = setting.value('monitor/sound/clock')

        # 管理趋势声音
        utc = datetime.datetime.utcnow()
        if trend_switch and utc.minute in (58, 59):
            self.play_sound('trend')
        else:
            self.stop_sound('trend')

        # 管理报文告警声音
        if taf_switch and any([self.ctx['FC']['warn'], self.ctx['FT']['warn']]):
            self.play_sound('alarm')
        else:
            self.stop_sound('alarm')

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
        self.thread = WorkThread()
        self.thread.done.connect(self.context)
        self.thread.done.connect(self.update_gui)
        self.thread.start()

    def context(self, ctx=None):
        if ctx is None:
            self.ctx = {
                'FC': {'warn': False},
                'FT': {'warn': False}
            }
        else:
            self.ctx = ctx

    def update_gui(self):
        self.update_taf_table()
        self.update_metar_table()
        self.update_recent()

        log.debug('Update GUI')

    def update_recent(self):
        self.current_taf.update_gui()
        self.recent_ft.update_gui()
        self.recent_fc.update_gui()

    def update_taf_table(self):
        recent = datetime.datetime.utcnow() - datetime.timedelta(hours=24)
        items = self.db.query(Tafor).filter(Tafor.sent > recent).order_by(Tafor.sent.desc()).all()
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
        items = self.db.query(Metar).filter(Metar.created > recent).order_by(Metar.created.desc()).all()
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
        QtWidgets.QMessageBox.about(self, u"预报报文发布软件",
                u"""<b>预报报文发布软件</b> v %s
                <p>本软件用于智能发布预报报文、趋势报文、重要气象情报、低空气象情报，监控预报报文，以声音或电话的方式返回告警
                <p>本项目遵循 GPL-2.0 协议 
                <p>项目源码 <a href="http://git.oschina.net/piratecb/tafor">http://git.oschina.net/piratecb/tafor</a>
                <p>联系邮箱 <a href="mailto:piratecb@gmail.com">piratecb@gmail.com</a>
                """ % (__version__))


class WorkThread(QtCore.QThread):
    """
    检查预报报文线程类
    """
    done = QtCore.pyqtSignal(dict)

    def __init__(self, parent=None):
        super(WorkThread, self).__init__(parent)

    def run(self):
        remote = remote_message()

        if not (boolean(setting.value('monitor/db/web_api')) and remote):
            remote = {}

        fc = Listen('FC', remote=remote.get('FC', None))
        ft = Listen('FT', remote=remote.get('FT', None))
        sa = Listen('SA', remote=remote.get('SA', None))
        sp = Listen('SP', remote=remote.get('SP', None))

        ctx = {
            'FC': {'warn': fc.warn},
            'FT': {'warn': ft.warn}
        }

        self.done.emit(ctx)


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
        log.error(e, exc_info=True)
    finally:  
        local_server.close()


if __name__ == "__main__":
    main()