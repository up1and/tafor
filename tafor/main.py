# -*- coding: utf-8 -*-

from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

from ui import Ui_main, main_rc
from taf import TAFEdit, ScheduleTAFEdit
from models import Tafor, Schedule, Session
from task import AutoSendTAF

__version__ = "1.0.0"


class MainWindow(QMainWindow, Ui_main.Ui_MainWindow):
    """
    主窗口
    """
    def __init__(self, parent=None):
        """
        初始化主窗口
        """
        QMainWindow.__init__(self, parent)
        self.setupUi(self)

        # 连接TAF对话框
        self.taf_action.triggered.connect(TAFEdit(self).show)

        # 连接设置对话框的槽
        # self.setting_action.triggered.connect(SettingDialog(self).show)
        self.setting_action.setIcon(QIcon(':/setting.png'))

        # 连接关于信息的槽
        self.about_action.triggered.connect(self.about)

        # 设置主窗口文字图标
        self.setWindowTitle(u'预报发报软件')
        self.setWindowIcon(QIcon(':/sunny.png'))

        # 设置系统托盘
        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(QIcon(':/sunny.png'))
        self.tray.show()

        # 链接系统托盘的槽
        # self.tray.activated.connect(self.restore_window)

        # 自动发送报文的计时器
        self.auto_send_timer = QTimer()
        self.auto_send_timer.timeout.connect(self.auto_send)
        self.auto_send_timer.start(15 * 1000) # 15 秒

        self.db = Session()

        self.update_taf_table()


    @pyqtSlot("bool")
    def on_warn_action_triggered(self, checked):
        """
        预报报文告警开启开关
        
        @param checked
        @type bool
        """
        print(checked)

    def keyPressEvent(self, event):
        if event.modifiers() == (Qt.ShiftModifier | Qt.ControlModifier) and event.key() == Qt.Key_P:
            ScheduleTAFEdit(self).show()

    def auto_send(self):
        self.auto_send_taf = AutoSendTAF()
        self.auto_send_taf.send.connect(self.update_taf_table)
        self.auto_send_taf.run()


    def update_taf_table(self):
        items = self.db.query(Tafor).order_by(Tafor.send_time.desc()).all()
        if len(items) > 12:
            items = items[0:12]
        header = self.taf_table.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        self.taf_table.setRowCount(len(items))
        self.taf_table.setColumnWidth(0, 50)
        self.taf_table.setColumnWidth(2, 140)

        for row, item in enumerate(items):
            self.taf_table.setItem(row, 0,  QTableWidgetItem(item.tt))
            self.taf_table.setItem(row, 1,  QTableWidgetItem(item.rpt))
            if item.confirm_time:
                cell_time = item.confirm_time.strftime("%Y-%m-%d %H:%M:%S")
                self.taf_table.setItem(row, 2,  QTableWidgetItem(cell_time))
            if item.schedule:
                self.taf_table.setItem(row, 3,  QTableWidgetItem('Schedule'))

        #self.taf_table.setStyleSheet("QTableWidget::item {padding: 5px 0;}")
        self.taf_table.resizeRowsToContents()


    def update_metar_table(self):
        raise NotImplemented

    def update_recent(self):
        raise NotImplemented
    
 
    def about(self):
        QMessageBox.about(self, u"预报报文发布软件",
                u"""<b>预报报文发布软件</b> v %s
                <p>暂无
                <p>本项目遵循 GPL-2.0 协议 
                <p>联系邮箱 <a href="mailto:piratecb@gmail.com">piratecb@gmail.com</a>
                """ % (__version__))



class SettingDialog(object):
    pass


if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    ui = MainWindow()
    ui.show()
    sys.exit(app.exec_())
    