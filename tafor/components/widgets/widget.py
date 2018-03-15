import json
import datetime

from PyQt5.QtCore import QCoreApplication, QTimer
from PyQt5.QtWidgets import QWidget, QMessageBox, QLabel, QHBoxLayout

from tafor.models import db, Taf, Sigmet, Trend
from tafor.utils import CheckTaf
from tafor.components.ui import Ui_main_recent


def alarmMessageBox(parent):
    title = QCoreApplication.translate('MainWindow', 'Alarm')
    messageBox = QMessageBox(QMessageBox.Question, title, 'Display Text', parent=parent)
    snooze = messageBox.addButton(QCoreApplication.translate('MainWindow', 'Snooze'), QMessageBox.ApplyRole)
    dismiss = messageBox.addButton(QCoreApplication.translate('MainWindow', 'Dismiss'), QMessageBox.RejectRole)
    return messageBox


class RecentMessage(QWidget, Ui_main_recent.Ui_Recent):

    def __init__(self, parent, layout, tt):
        super(RecentMessage, self).__init__(parent)
        self.setupUi(self)
        self.tt = tt

        layout.addWidget(self)

    def updateGui(self):
        item = self.item()

        if item:
            self.groupBox.setTitle(item.tt)
            self.sendTime.setText(item.sent.strftime('%Y-%m-%d %H:%M:%S'))
            self.rpt.setText(item.report)
            self.showConfirm(item)
            
        self.showOrHide(item)

    def item(self):
        item = None
        recent = datetime.datetime.utcnow() - datetime.timedelta(hours=24)

        if self.tt in ['FC', 'FT']:
            item = db.query(Taf).filter(Taf.sent > recent, Taf.tt == self.tt).order_by(Taf.sent.desc()).first()

        if self.tt in ['WS', 'WC', 'WV']:
            item = db.query(Sigmet).filter(Sigmet.sent > recent).order_by(Sigmet.sent.desc()).first()

        if self.tt == 'TREND':
            item = db.query(Trend).filter(Trend.sent > recent).order_by(Trend.sent.desc()).first()
            if item and item.isNosig():
                item = None

        return item

    def showOrHide(self, item):
        if item:
            if not self.isVisible():
                self.show()
        else:
            self.hide()

    def showConfirm(self, item):
        if self.tt not in ['FC', 'FT']:
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
