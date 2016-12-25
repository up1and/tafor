# -*- coding: utf-8 -*-

from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

from ui import Ui_main, main_rc
from taf import TAFEdit, ScheduleTAFEdit
# from models import session, Tafor, Schedule

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


    @pyqtSlot("bool")
    def on_warn_action_triggered(self, checked):
        """
        预报报文告警开启开关
        
        @param checked
        @type bool
        """
        print(checked)

    def keyPressEvent(self, event):
        # if event.key() == Qt.Key_Escape:
        if event.modifiers() == (Qt.ShiftModifier | Qt.ControlModifier) and event.key() == Qt.Key_P:
            ScheduleTAFEdit(self).show()
        
 
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
    