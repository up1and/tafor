import requests

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QCoreApplication


class StatusBarWidget(QtWidgets.QWidget):

    def __init__(self, parent, statusBar, last=False):
        super(StatusBarWidget, self).__init__(parent)

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self.parent = parent

        statusBar.addPermanentWidget(self)


class BaseTimerStatus(StatusBarWidget):

    def __init__(self, parent, statusBar, last=False):
        super(BaseTimerStatus, self).__init__(parent, statusBar, last)
        layout = self.layout()
        layout.addSpacing(10)
        self.head = QtWidgets.QLabel()
        self.label = QtWidgets.QLabel()
        # font = QtGui.QFont()
        # font.setBold(True)
        # self.label.setFont(font)
        layout.addWidget(self.head)
        layout.addWidget(self.label)
        layout.addSpacing(10)
        self.setHead()

        self.timer = QtCore.QTimer()
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
        if self.isVisible():
            status = self.parent.context.webApi
            text = QCoreApplication.translate('MainWindow', 'Online') if status else QCoreApplication.translate('MainWindow', 'Offline')
            self.label.setText(text)


class CallServiceStatus(BaseTimerStatus):

    def setHead(self):
        title = QCoreApplication.translate('MainWindow', 'Phone Service')
        self.head.setText(title)

    def setValue(self):
        status = self.parent.context.callService
        text = QCoreApplication.translate('MainWindow', 'Online') if status else QCoreApplication.translate('MainWindow', 'Offline')
        self.label.setText(text)