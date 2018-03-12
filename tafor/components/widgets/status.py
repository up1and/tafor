import requests

from PyQt5.QtCore import QCoreApplication, QTimer
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel


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


class PageStatus(StatusBarWidget):

    def __init__(self, parent, statusBar, last=False):
        super(PageStatus, self).__init__(parent, statusBar, last)
        self.table = None
        self.updateGUI()

    def setHead(self):
        title = QCoreApplication.translate('MainWindow', 'Page')
        self.head.setText(title)

    def setValue(self):
        page = str(self.table.page)
        self.label.setText(page)

    def setTable(self, table):
        self.table = table
        self.updateGUI()

    def updateGUI(self):
        if self.table is None:
            self.hide()
        else:
            self.show()
            self.setValue()


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