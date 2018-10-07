import datetime

from PyQt5.QtCore import QCoreApplication, QTimer, Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLayout

from tafor import conf
from tafor.utils.convert import parseTime
from tafor.components.setting import isConfigured
from tafor.components.widgets.editor import BaseEditor
from tafor.components.widgets import TrendSegment


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
        self.trend = TrendSegment()
        layout.addWidget(self.trend)
        self.addBottomBox(layout)
        self.setLayout(layout)

        self.setStyleSheet('QLineEdit {width: 50px;} QComboBox {width: 50px;}')

    def bindSignal(self):
        self.trend.period.editingFinished.connect(self.validatePeriod)
        self.trend.completeSignal.connect(self.enbaleNextButton)

        # 下一步
        self.nextButton.clicked.connect(self.beforeNext)

    def enbaleNextButton(self):
        self.enbale = self.trend.complete
        self.nextButton.setEnabled(self.enbale)

    def beforeNext(self):
        self.trend.validate()

        if self.trend.period.isEnabled():
            self.validatePeriod()

        if self.enbale:
            self.assembleMessage()
            self.previewMessage()

    def validatePeriod(self):
        period = self.trend.period.text()
        utc = datetime.datetime.utcnow()
        time = parseTime(period)
        delta = datetime.timedelta(hours=2, minutes=30)

        if (self.trend.at.isChecked() or self.trend.fm.isChecked()) and period == '2400':
            self.trend.period.setText('0000')

        if self.trend.tl.isChecked() and period == '0000':
            self.trend.period.setText('2400')

        if time - delta > utc:
            self.trend.period.clear()
            self.showNotificationMessage(QCoreApplication.translate('Editor', 'Trend valid time is not corret'))

    def assembleMessage(self):
        message = self.trend.message()
        self.rpt = message + '='
        self.sign = conf.value('Message/TrendSign')

    def previewMessage(self):
        message = {'sign': self.sign, 'rpt': self.rpt, 'full': ' '.join([self.sign, self.rpt])}
        self.previewSignal.emit(message)

    def clear(self):
        self.trend.clear()

    def closeEvent(self, event):
        self.clear()

    def showEvent(self, event):
        if not isConfigured('Trend'):
            QTimer.singleShot(0, self.showConfigError)

