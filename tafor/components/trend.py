# -*- coding: utf-8 -*-
import json
import datetime

from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

from tafor import conf, logger
from tafor.components.widgets.segments import TrendSegment


class TrendEditor(QDialog):
    previewSignal = pyqtSignal(dict)

    def __init__(self, parent=None):
        super(TrendEditor, self).__init__(parent)
        self.initUI()
        self.bindSignal()
        
        self.setWindowTitle("编发趋势")

    def initUI(self):
        window = QWidget(self)
        layout = QVBoxLayout(window)
        layout.setSizeConstraint(QLayout.SetFixedSize)
        self.trend = TrendSegment()
        self.nextButton = QPushButton()
        self.nextButton.setEnabled(False)
        self.nextButton.setText("下一步")
        layout.addWidget(self.trend)
        layout.addWidget(self.nextButton, 0, Qt.AlignRight|Qt.AlignBottom)
        self.setLayout(layout)

        self.setStyleSheet("QLineEdit {width: 50px;} QComboBox {width: 50px}")

    def bindSignal(self):

        self.trend.completeSignal.connect(self.enbaleNextButton)

        # 下一步
        self.nextButton.clicked.connect(self.assembleMessage)
        self.nextButton.clicked.connect(self.previewMessage)

    def enbaleNextButton(self):
        enbale = self.trend.required
        logger.debug('Trend required ' + str(enbale))
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

