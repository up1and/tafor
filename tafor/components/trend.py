import json
import datetime

from PyQt5.QtCore import QCoreApplication, Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLayout

from tafor import boolean, conf, logger
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
        self.nextButton = QPushButton()
        self.nextButton.setEnabled(False)
        self.nextButton.setText(QCoreApplication.translate('Editor', 'Next'))
        layout.addWidget(self.trend)
        layout.addWidget(self.nextButton, 0, Qt.AlignRight|Qt.AlignBottom)
        self.setLayout(layout)

        self.setStyleSheet('QLineEdit {width: 50px;} QComboBox {width: 50px}')

    def bindSignal(self):
        self.trend.completeSignal.connect(self.enbaleNextButton)

        # 下一步
        self.nextButton.clicked.connect(self.assembleMessage)
        self.nextButton.clicked.connect(self.previewMessage)

    def enbaleNextButton(self):
        enbale = self.trend.complete
        self.nextButton.setEnabled(enbale)

    def assembleMessage(self):
        message = self.trend.message()
        self.rpt = message + '='
        self.sign = conf.value('Message/TrendSign')

    def previewMessage(self):
        message = {'sign': self.sign, 'rpt': self.rpt, 'full': ' '.join([self.sign, self.rpt])}
        self.previewSignal.emit(message)
        logger.debug('Emit', message)

    def clear(self):
        self.trend.clear()

    def closeEvent(self, event):
        self.clear()

    def showEvent(self, event):
        # Check Settings
        pass

