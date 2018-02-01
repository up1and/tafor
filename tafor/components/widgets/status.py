import requests

from PyQt5 import QtCore, QtGui, QtWidgets


class StatusBarWidget(QtWidgets.QWidget):
    def __init__(self, parent, statusbar):
        super(StatusBarWidget, self).__init__(parent)

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self.parent = parent

        statusbar.addPermanentWidget(self)


class BaseTimerStatus(StatusBarWidget):
    title = None

    def __init__(self, parent, statusbar):
        super(BaseTimerStatus, self).__init__(parent, statusbar)
        layout = self.layout()
        layout.addSpacing(10)
        layout.addWidget(QtWidgets.QLabel(self.tr(self.title)))
        self.label = QtWidgets.QLabel()
        # font = QtGui.QFont()
        # font.setBold(True)
        # self.label.setFont(font)
        layout.addWidget(self.label)
        layout.addSpacing(10)
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.updateLabel)
        self.timer.start(2000)
    
    def value(self):
        raise NotImplementedError

    def updateLabel(self):
        if self.isVisible():
            self.label.setText(str(self.value()))

class WebAPIStatus(BaseTimerStatus):
    title = 'Data Source'

    def value(self):
        status = self.parent.store.webApi
        text = 'Normal' if status else 'Timeout'
        return self.tr(text)


class CallServiceStatus(BaseTimerStatus):
    title = 'Telephone Service'

    def value(self):
        status = self.parent.store.callService
        text = 'Normal' if status else 'Timeout'
        return self.tr(text)