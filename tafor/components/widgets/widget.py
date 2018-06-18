import datetime

from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtCore import QCoreApplication, QTimer
from PyQt5.QtWidgets import QWidget, QMessageBox, QLabel, QHBoxLayout

from tafor import conf, boolean
from tafor.utils import CheckTaf
from tafor.components.ui import main_rc, Ui_main_recent


class RemindMessageBox(QMessageBox):
    """闹钟对话框"""
    def __init__(self, parent):
        super(RemindMessageBox, self).__init__(parent=parent)
        icon = QPixmap(':/time.png')
        title = QCoreApplication.translate('MainWindow', 'Alarm')
        self.setIconPixmap(icon)
        self.setWindowTitle(title)
        self.addButton(QCoreApplication.translate('MainWindow', 'Snooze'), QMessageBox.ApplyRole)
        self.addButton(QCoreApplication.translate('MainWindow', 'Dismiss'), QMessageBox.RejectRole)
        self.parent = parent

    def showEvent(self, event):
        self.parent.showNormal()


class RecentMessage(QWidget, Ui_main_recent.Ui_Recent):

    def __init__(self, parent, layout, item):
        super(RecentMessage, self).__init__(parent)
        self.setupUi(self)
        self.setFont()
        self.item = item
        self.setText()

        layout.addWidget(self)

    def setFont(self):
        font = QFont('Segoe UI')
        if boolean(conf.value('General/LargeFont')):
            font.setPointSize(15)
        else:
            font.setPixelSize(14)
        
        self.rpt.setFont(font)

    def setText(self):
        self.groupBox.setTitle(self.item.tt)
        self.sendTime.setText(self.item.sent.strftime('%Y-%m-%d %H:%M:%S'))
        self.rpt.setText(self.item.report)
        self.rpt.setWordWrap(True)
        self.showConfirm(self.item)

    def showConfirm(self, item):
        if item.tt not in ['FC', 'FT']:
            self.check.hide()
            return

        if item.confirmed:
            self.check.setText('<img src=":/checkmark.png" width="24" height="24"/>')
        else:
            self.check.setText('<img src=":/cross.png" width="24" height="24"/>')


class CurrentTaf(QWidget):

    def __init__(self, parent, container):
        super(CurrentTaf, self).__init__(parent)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self.fc = QLabel()
        self.ft = QLabel()

        layout.addWidget(self.fc)
        layout.addSpacing(10)
        layout.addWidget(self.ft)

        container.addWidget(self)

    def updateGui(self):
        self.fc.setText(self.current('FC'))
        self.ft.setText(self.current('FT'))

    def current(self, tt):
        taf = CheckTaf(tt)
        if taf.local():
            text = ''
        else:
            text = tt + taf.warningPeriod(withDay=False)
        return text


class Clock(QWidget):
    
    def __init__(self, parent, container):
        super(Clock, self).__init__(parent)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        # layout.addWidget(QLabel('世界时'))
        layout.addSpacing(5)
        self.label = QLabel()
        layout.addWidget(self.label)

        self.timer = QTimer()
        self.timer.timeout.connect(self.updateGui)
        self.timer.start(1 * 1000)

        self.updateGui()

        container.addWidget(self)

    def updateGui(self):
        utc = datetime.datetime.utcnow()
        self.label.setText(utc.strftime('%Y-%m-%d %H:%M:%S'))
