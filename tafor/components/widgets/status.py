import requests

from PyQt5.QtCore import QCoreApplication, QTimer
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel

from tafor.states import context


class StatusBarWidget(QWidget):

    def __init__(self, parent, statusBar, last=False):
        super(StatusBarWidget, self).__init__(parent)
        self.initUI()

        self.parent = parent

        statusBar.addPermanentWidget(self)

    def initUI(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addSpacing(10)
        self.head = QLabel()
        self.label = QLabel()
        layout.addWidget(self.head)
        layout.addWidget(self.label)
        layout.addSpacing(10)
        self.setHead()
        self.setLayout(layout)


class BaseTimerStatus(StatusBarWidget):

    def __init__(self, parent, statusBar, last=False):
        super(BaseTimerStatus, self).__init__(parent, statusBar, last)

        self.timer = QTimer()
        self.timer.timeout.connect(self.setValue)
        self.timer.start(2000)
    
    def setValue(self):
        raise NotImplementedError

    def setHead(self):
        raise NotImplementedError

class WebAPIStatus(BaseTimerStatus):

    def setHead(self):
        title = QCoreApplication.translate('MainWindow', 'Data Source')
        self.head.setText(title)

    def setValue(self):
        online = context.webApi.isOnline()
        text = QCoreApplication.translate('MainWindow', 'Online') if online else QCoreApplication.translate('MainWindow', 'Offline')
        self.label.setText(text)


class CallServiceStatus(BaseTimerStatus):

    def setHead(self):
        title = QCoreApplication.translate('MainWindow', 'Phone Service')
        self.head.setText(title)

    def setValue(self):
        online = context.callService.isOnline()
        text = QCoreApplication.translate('MainWindow', 'Online') if online else QCoreApplication.translate('MainWindow', 'Offline')
        self.label.setText(text)