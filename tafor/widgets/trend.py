# -*- coding: utf-8 -*-
import json
import datetime

from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

from tafor.widgets.edit import TrendWidget
from tafor.utils import CheckTAF, Element, Grammar
from tafor import setting, log


class TrendEdit(QDialog):
    """docstring for TrendEdit"""

    signal_preview = pyqtSignal(dict)

    def __init__(self, parent=None):
        super(TrendEdit, self).__init__(parent)
        self.init_ui()
        self.bind_signal()
        
        self.setWindowTitle("编发趋势")

    def init_ui(self):
        window = QWidget(self)
        layout = QVBoxLayout(window)
        layout.setSizeConstraint(QLayout.SetFixedSize)
        self.trend = TrendWidget()
        self.next_button = QPushButton()
        self.next_button.setEnabled(False)
        self.next_button.setText("下一步")
        layout.addWidget(self.trend)
        layout.addWidget(self.next_button, 0, Qt.AlignRight|Qt.AlignBottom)
        self.setLayout(layout)

        self.setStyleSheet("QLineEdit {width: 50px;} QComboBox {width: 50px}")

    def bind_signal(self):

        self.trend.signal_required.connect(self.enbale_next_button)

        # 下一步
        self.next_button.clicked.connect(self.assemble_message)
        self.next_button.clicked.connect(self.preview_message)

    def enbale_next_button(self):
        enbale = self.trend.required
        log.debug('Trend required ' + str(enbale))
        self.next_button.setEnabled(enbale)

    def assemble_message(self):
        message = self.trend.message()
        self.rpt = message + '='
        self.sign = setting.value('message/trend_sign')

    def preview_message(self):
        message = {'sign': self.sign, 'rpt': self.rpt, 'full': ' '.join([self.sign, self.rpt])}
        self.signal_preview.emit(message)
        log.debug('Emit', message)

    def clear(self):
        self.trend.clear()


    def closeEvent(self, event):
        self.clear()

