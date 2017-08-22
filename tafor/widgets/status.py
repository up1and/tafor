from PyQt5 import QtCore, QtGui, QtWidgets


class StatusBarWidget(QtWidgets.QWidget):
    def __init__(self, parent, statusbar):
        QtWidgets.QWidget.__init__(self, parent)

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        statusbar.addPermanentWidget(self)


class BaseTimerStatus(StatusBarWidget):
    title = None

    def __init__(self, parent, statusbar):
        StatusBarWidget.__init__(self, parent, statusbar)
        layout = self.layout()
        layout.addSpacing(10)
        layout.addWidget(QtWidgets.QLabel(self.title))
        self.label = QtWidgets.QLabel()
        font = QtGui.QFont()
        font.setBold(True)
        self.label.setFont(font)
        layout.addWidget(self.label)
        layout.addSpacing(10)
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_label)
        self.timer.start(2000)
    
    def get_value(self):
        raise NotImplementedError
        
    def update_label(self):
        if self.isVisible():
            # self.label.setText('<img src=":/checkmark.png" width="16" height="16"/>')
            self.label.setText(self.get_value())

class WebAPIStatus(BaseTimerStatus):
    title = '数据源:'

    def get_value(self):
        return '正常'


class CallServiceStatus(BaseTimerStatus):
    title = '电话服务:'

    def get_value(self):
        return '超时'