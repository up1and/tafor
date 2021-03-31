import datetime

from uuid import uuid4

from PyQt5.QtCore import QCoreApplication, QTimer
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLayout

from tafor import conf
from tafor.states import context
from tafor.components.setting import isConfigured
from tafor.components.widgets.editor import BaseEditor
from tafor.components.widgets import TrendSegment
from tafor.utils import message


class TrendEditor(BaseEditor):

    def __init__(self, parent=None, sender=None):
        super(TrendEditor, self).__init__(parent, sender)

        self.initUI()
        self.bindSignal()

        self.setWindowTitle(QCoreApplication.translate('Editor', 'Encoding Trend Forecast'))

    def initUI(self):
        window = QWidget(self)
        layout = QVBoxLayout(window)
        layout.setSizeConstraint(QLayout.SetFixedSize)
        self.trend = TrendSegment(parent=self)
        layout.addWidget(self.trend)
        self.addBottomBox(layout)
        self.setLayout(layout)

        self.setStyleSheet('QLineEdit {width: 50px;} QComboBox {width: 50px;}')
        self.trend.metar.setStyleSheet('QLabel {color: grey;}')

    def bindSignal(self):
        self.trend.contentChanged.connect(self.enbaleNextButton)

        # 下一步
        self.nextButton.clicked.connect(self.beforeNext)

    def enbaleNextButton(self):
        self.enbale = self.trend.complete
        self.nextButton.setEnabled(self.enbale)

    def beforeNext(self):
        self.trend.validate()

        if self.trend.period.isEnabled():
            self.trend.validatePeriod()

        if self.enbale:
            self.assembleMessage()
            self.previewMessage()

    def assembleMessage(self):
        message = self.trend.message()
        self.rpt = message + '='
        self.sign = conf.value('Message/TrendSign')

    def previewMessage(self):
        uuid = str(uuid4())
        message = {'sign': self.sign, 'rpt': self.rpt, 'uuid': uuid}
        self.previewSignal.emit(message)

    def clear(self):
        self.trend.clear()
        self.nextButton.setEnabled(False)

    def closeEvent(self, event):
        super(TrendEditor, self).closeEvent(event)
        self.clear()

    def showEvent(self, event):
        if not isConfigured('Trend'):
            QTimer.singleShot(0, self.showConfigError)

