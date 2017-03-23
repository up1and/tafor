# -*- coding: utf-8 -*-
import datetime

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtNetwork import QLocalSocket, QLocalServer

from ui import Ui_main, main_rc
from taf import TAFEdit, ScheduleTAFEdit
from send import ScheduleTAFSend, TAFSend
from settings import SettingDialog
from schedule import ScheduleTable
from models import Tafor, Schedule, User
from widgets import WidgetsItem
from utils import TAFPeriod, str2bool
from config import db, setting, log, __version__


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

        # 初始化剪贴板
        self.clip = QtWidgets.QApplication.clipboard()

        # 初始TAF对话框
        self.taf_edit_dialog = TAFEdit(self)
        self.sch_taf_edit_dialog = ScheduleTAFEdit(self)
        self.taf_send_dialog = TAFSend(self)
        self.sch_taf_send_dialog = ScheduleTAFSend(self)
        self.sch_table_dialog = ScheduleTable(self)
        self.setting_dialog = SettingDialog(self)

        # 连接TAF对话框信号
        self.taf_edit_dialog.signal_preview.connect(self.handle_taf_edit)
        self.taf_send_dialog.signal_send.connect(self.update_gui)

        self.sch_taf_edit_dialog.signal_preview.connect(self.handle_sch_taf_edit)
        self.sch_taf_send_dialog.signal_send.connect(self.handle_sch_taf_send)

        self.taf_send_dialog.signal_back.connect(self.taf_edit_dialog.show)
        self.taf_send_dialog.signal_close.connect(self.taf_edit_dialog.close)

        # 连接菜单信号
        self.taf_action.triggered.connect(self.taf_edit_dialog.show)

        # # 添加定时任务菜单
        # self.sch_taf_action = QtWidgets.QAction(self)
        # self.post_menu.addAction(self.sch_taf_action)
        # self.sch_taf_action.setText('定时任务')
        # self.sch_taf_action.triggered.connect(self.sch_taf_edit_dialog.show)

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

        # 设置主窗口文字图标
        self.setWindowTitle('预报发报软件')
        self.setWindowIcon(QtGui.QIcon(':/sunny.png'))

        # 设置切换联系人菜单
        self.set_change_contract_menu()

        # 设置系统托盘
        self.set_sys_tray()

        # 添加模块
        self.widget_fc = WidgetsItem()
        self.recent_layout.addWidget(self.widget_fc)

        self.widget_ft = WidgetsItem()
        self.recent_layout.addWidget(self.widget_ft)

        # 自动发送报文的计时器
        self.auto_send_timer = QtCore.QTimer()
        self.auto_send_timer.timeout.connect(self.sch_taf_send_dialog.auto_send)
        self.auto_send_timer.start(30 * 1000)

        # 时钟计时器
        self.clock_timer = QtCore.QTimer()
        self.clock_timer.timeout.connect(self.update_utc_time)
        self.clock_timer.timeout.connect(self.update_tray_tips)
        self.clock_timer.timeout.connect(self.update_current_taf)
        self.clock_timer.timeout.connect(self.taf_edit_dialog.update_date)
        self.clock_timer.start(1 * 1000)

        self.warn_timer = QtCore.QTimer()
        self.warn_timer.timeout.connect(self.update_gui)
        self.warn_timer.timeout.connect(self.sch_table_dialog.update_gui)
        self.warn_timer.start(60 * 1000)

        self.update_gui()

    def set_change_contract_menu(self):
        contacts = db.query(User).all()

        for person in contacts:
            setattr(self, 'contract_' + str(person.id), QtWidgets.QAction(self))
            target = getattr(self, 'contract_' + str(person.id))
            target.setText(person.name)
            target.setCheckable(True)

            self.contracts_action_group.addAction(target)
            self.contracts_menu.addAction(target)

        phone_number = setting.value('monitor/phone/select_phone_number')
        person = db.query(User).filter_by(phone_number=phone_number).first()
        if setting.value('monitor/phone/phone_warn_taf') and person:
            getattr(self, 'contract_' + str(person.id)).setChecked(True)
        else:
            self.contract_no.setChecked(True)

    def set_sys_tray(self):
        # 设置系统托盘
        self.tray = QtWidgets.QSystemTrayIcon(self)
        self.tray.setIcon(QtGui.QIcon(':/sunny.png'))
        self.tray.show()

        self.update_tray_tips()

        # 连接系统托盘的槽
        self.tray.activated.connect(self.restore_window)

        self.tray_menu = QtWidgets.QMenu(self)

        self.tray_menu.addAction(self.contracts_menu.menuAction())
        self.tray_menu.addAction(self.setting_action)
        self.tray_menu.addAction(self.about_action)
        self.tray_menu.addSeparator()
        self.tray_menu.addAction(self.quit_action)

        self.tray.setContextMenu(self.tray_menu)

    def change_phone_number(self):
        target = self.contracts_action_group.checkedAction()

        if self.contract_no == target:
            setting.setValue('monitor/phone/phone_warn_taf', False)
        else:
            name = target.text()
            person = db.query(User).filter_by(name=name).first()
            phone_number = person.phone_number if person else ''

            setting.setValue('monitor/phone/phone_warn_taf', True)
            setting.setValue('monitor/phone/select_phone_number', phone_number)
        
        self.update_tray_tips()

    def update_tray_tips(self):
        alarm_status = str2bool(setting.value('monitor/phone/phone_warn_taf'))

        title = '预报发报软件 v' + __version__
        taf_text = self.next_taf('FC') + ' ' + self.next_taf('FT')
        alarm_text = '告警状态：开启' if alarm_status else '告警状态：关闭'
        phone_text = '告警电话：' + setting.value('monitor/phone/select_phone_number') if alarm_status else None

        message_list = filter(None, [title, alarm_text, phone_text, taf_text])
        message = '\n'.join(message_list)

        self.tray.setToolTip(message)

    def copy_select_item(self, item):
        self.clip.setText(item.text())
        self.statusbar.showMessage('已复制  ' + item.text())

    def handle_taf_edit(self, message):
        log.debug('receive from taf edit ' + str(message))
        self.taf_edit_dialog.hide()
        self.taf_send_dialog.receive_message(message)
        self.taf_send_dialog.show()

    def handle_sch_taf_edit(self, message):
        log.debug('receive from sch taf edit ' + str(message))
        self.sch_taf_send_dialog.receive_message(message)
        self.sch_taf_send_dialog.show()

    def handle_sch_taf_send(self):
        self.sch_taf_edit_dialog.hide()
        self.sch_taf_send_dialog.hide()
        self.sch_table_dialog.show()
        self.sch_table_dialog.update_gui()

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
                self.sch_taf_edit_dialog.show()
            if event.key() == QtCore.Qt.Key_T:
                self.sch_table_dialog.show()

    def closeEvent(self, event):
        if event.spontaneous():
            event.ignore()
            self.hide()
        else:
            self.taf_edit_dialog.setAttribute(QtCore.Qt.WA_DeleteOnClose)
            self.sch_taf_edit_dialog.setAttribute(QtCore.Qt.WA_DeleteOnClose)
            self.taf_send_dialog.setAttribute(QtCore.Qt.WA_DeleteOnClose)
            self.sch_taf_send_dialog.setAttribute(QtCore.Qt.WA_DeleteOnClose)
            self.sch_table_dialog.setAttribute(QtCore.Qt.WA_DeleteOnClose)
            self.setting_dialog.setAttribute(QtCore.Qt.WA_DeleteOnClose)

            self.taf_edit_dialog.close()
            self.sch_taf_edit_dialog.close()
            self.taf_send_dialog.close()
            self.sch_taf_send_dialog.close()
            self.sch_table_dialog.close()
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

    def update_gui(self):
        self.update_taf_table()
        self.update_recent()
        self.update_utc_time()
        self.update_current_taf()

        log.debug('Update GUI')

    def update_taf_table(self):
        items = db.query(Tafor).order_by(Tafor.send_time.desc()).all()
        if len(items) > 12:
            items = items[0:12]
        header = self.taf_table.horizontalHeader()
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        self.taf_table.setRowCount(len(items))
        self.taf_table.setColumnWidth(0, 50)
        self.taf_table.setColumnWidth(2, 140)
        self.taf_table.setColumnWidth(3, 50)
        self.taf_table.setColumnWidth(4, 50)

        for row, item in enumerate(items):
            self.taf_table.setItem(row, 0,  QtWidgets.QTableWidgetItem(item.tt))
            self.taf_table.setItem(row, 1,  QtWidgets.QTableWidgetItem(item.rpt))
            if item.send_time:
                send_time = item.send_time.strftime("%Y-%m-%d %H:%M:%S")
                self.taf_table.setItem(row, 2,  QtWidgets.QTableWidgetItem(send_time))

            if item.confirm_time:
                check_item = QtWidgets.QTableWidgetItem('√')
                # check_item.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
                # check_item.setIcon(QIcon(':/check.png'))
                self.taf_table.setItem(row, 3, check_item)
            else:
                check_item = QtWidgets.QTableWidgetItem('×')
                # check_item.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
                # check_item.setIcon(QIcon(':/warn.png'))
                self.taf_table.setItem(row, 3, check_item)

            if item.schedule:
                schedule_item = QtWidgets.QTableWidgetItem('√')
                # schedule_item.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
                # schedule_item.setIcon(QIcon(':/clock.png'))
                self.taf_table.setItem(row, 4, schedule_item)


        #self.taf_table.setStyleSheet("QTableWidget::item {padding: 5px 0;}")
        # self.taf_table.resizeRowsToContents()


    def update_metar_table(self):
        raise NotImplemented

    def update_recent(self):
        fc = db.query(Tafor).filter_by(tt='FC').order_by(Tafor.send_time.desc()).first()
        ft = db.query(Tafor).filter_by(tt='FT').order_by(Tafor.send_time.desc()).first()

        if fc:
            self.widget_fc.set_item(fc)
        else:
            self.widget_fc.hide()

        if ft:
            self.widget_ft.set_item(ft)
        else:
            self.widget_ft.hide()

    def update_utc_time(self):
        utc = datetime.datetime.utcnow()
        self.utc_time.setText('世界时  ' + utc.strftime("%Y-%m-%d %H:%M:%S"))

    def update_current_taf(self):
        self.current_fc.setText(self.next_taf('FC'))
        self.current_ft.setText(self.next_taf('FT'))

    def next_taf(self, tt):
        taf = TAFPeriod(tt)
        if taf.is_existed(taf.warn()):
            text = ''
        else:
            text = tt + taf.warn()[2:]
        return text


    def about(self):
        QtWidgets.QMessageBox.about(self, u"预报报文发布软件",
                u"""<b>预报报文发布软件</b> v %s
                <p>本软件用于智能发布预报报文、趋势报文、重要气象情报、低空气象情报，监控预报报文，以声音或电话的方式返回告警
                <p>本项目遵循 GPL-2.0 协议 
                <p>项目源码 <a href="http://git.oschina.net/piratecb/tafor">http://git.oschina.net/piratecb/tafor</a>
                <p>联系邮箱 <a href="mailto:piratecb@gmail.com">piratecb@gmail.com</a>
                """ % (__version__))


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
    finally:  
        local_server.close()


if __name__ == "__main__":
    main()