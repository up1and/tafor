import json
import datetime

from PyQt5.QtCore import QCoreApplication, QTimer
from PyQt5.QtWidgets import QWidget, QMessageBox, QLabel, QHBoxLayout

from tafor.models import db, Taf
from tafor.utils import CheckTAF
from tafor.components.ui import Ui_main_recent


def alarmMessageBox(parent):
    title = QCoreApplication.translate('MainWindow', 'Alarm')
    messageBox = QMessageBox(QMessageBox.Question, title, 'Display Text', parent=parent)
    snooze = messageBox.addButton(QCoreApplication.translate('MainWindow', 'Snooze'), QMessageBox.ApplyRole)
    dismiss = messageBox.addButton(QCoreApplication.translate('MainWindow', 'Dismiss'), QMessageBox.RejectRole)
    return messageBox


class RecentTAF(QWidget, Ui_main_recent.Ui_Recent):

    def __init__(self, parent, container, tt):
        super(RecentTAF, self).__init__(parent)
        self.setupUi(self)
        self.tt = tt

        container.addWidget(self)

    def updateGUI(self):
        item = db.query(Taf).filter_by(tt=self.tt).order_by(Taf.sent.desc()).first()

        if not item:
            self.hide()
            return 

        self.groupBox.setTitle(item.tt)
        self.sendTime.setText(item.sent.strftime('%Y-%m-%d %H:%M:%S'))
        self.rpt.setText(item.report)
        if item.confirmed:
            self.check.setText('<img src=":/checkmark.png" width="24" height="24"/>')
        else:
            self.check.setText('<img src=":/cross.png" width="24" height="24"/>')


class CurrentTAF(QWidget):

    def __init__(self, parent, container):
        super(CurrentTAF, self).__init__(parent)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self.fc = QLabel()
        self.ft = QLabel()

        layout.addWidget(self.fc)
        layout.addSpacing(10)
        layout.addWidget(self.ft)

        container.addWidget(self)

    def updateGUI(self):
        self.fc.setText(self.current('FC'))
        self.ft.setText(self.current('FT'))

    def current(self, tt):
        taf = CheckTAF(tt)
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
        self.timer.timeout.connect(self.updateGUI)
        self.timer.start(1 * 1000)

        self.updateGUI()

        container.addWidget(self)

    def updateGUI(self):
        utc = datetime.datetime.utcnow()
        self.label.setText(utc.strftime('%Y-%m-%d %H:%M:%S'))
