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
from utils import TAFPeriod
from config import db, setting, __version__


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

        self.taf_send_dialog.button_box.rejected.connect(self.taf_edit_dialog.show)
        self.taf_send_dialog.button_box.accepted.connect(self.taf_edit_dialog.close)

        # 连接菜单信号
        self.taf_action.triggered.connect(self.taf_edit_dialog.show)

        # 添加定时任务菜单
        # self.sch_taf_action = QAction(self)
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

        # 连接系统托盘的槽
        self.tray.activated.connect(self.restore_window)

        self.tray_menu = QtWidgets.QMenu(self)

        self.alarm_status = QtWidgets.QAction(self)
        self.alarm_status.setEnabled(False)
        status_text = '告警开启' if setting.value('monitor/phone/phone_warn_taf') else '告警关闭'
        self.alarm_status.setText(status_text)
        
        self.tray_menu.addAction(self.alarm_status)
        self.tray_menu.addSeparator()
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
            self.alarm_status.setText('告警关闭')
        else:
            name = target.text()
            person = db.query(User).filter_by(name=name).first()
            phone_number = person.phone_number if person else ''

            setting.setValue('monitor/phone/phone_warn_taf', True)
            setting.setValue('monitor/phone/select_phone_number', phone_number)
            self.alarm_status.setText('告警开启')

    def handle_taf_edit(self, message):
        print('Receive', message)
        self.taf_edit_dialog.hide()
        self.taf_send_dialog.receive_message(message)
        self.taf_send_dialog.show()

    def handle_sch_taf_edit(self, message):
        print('Receive', message)
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
            # self.taf_edit_dialog.setAttribute(QtCore.Qt.WA_DeleteOnClose)
            # self.sch_taf_edit_dialog.setAttribute(QtCore.Qt.WA_DeleteOnClose)
            # self.taf_send_dialog.setAttribute(QtCore.Qt.WA_DeleteOnClose)
            # self.sch_taf_send_dialog.setAttribute(QtCore.Qt.WA_DeleteOnClose)
            # self.sch_table_dialog.setAttribute(QtCore.Qt.WA_DeleteOnClose)

            self.setting_dialog.setAttribute(QtCore.Qt.WA_DeleteOnClose)
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

        print('Update GUI')

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
        # print(fc)
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
        fc_period = TAFPeriod('FC')
        if fc_period.is_existed(fc_period.warn()):
            fc_text = ''
        else:
            fc_text = 'FC' + fc_period.warn()[2:]
        self.current_fc.setText(fc_text)

        ft_period = TAFPeriod('FT')
        if ft_period.is_existed(ft_period.warn()):
            ft_text = ''
        else:
            ft_text = 'FT' + ft_period.warn()[2:]
        self.current_ft.setText(ft_text)


    def about(self):
        QtWidgets.QMessageBox.about(self, u"预报报文发布软件",
                u"""<b>预报报文发布软件</b> v %s
                <p>暂无
                <p>本项目遵循 GPL-2.0 协议 
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