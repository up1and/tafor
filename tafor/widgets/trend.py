# -*- coding: utf-8 -*-
import json
import datetime

from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

from tafor.widgets.common import TrendWidget
from tafor.utils import TAFPeriod, Parser, REGEX_TAF
from tafor.models import Tafor, Task
from tafor import db, log


class TrendEdit(QDialog):
    """docstring for TrendEdit"""

    signal_preview = pyqtSignal(dict)

    def __init__(self, parent=None):
        super(TrendEdit, self).__init__(parent)
        self.init_ui()
        self.bind_signal()

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

        # 下一步
        # self.next_button.clicked.connect(self.assemble_message)
        # self.next_button.clicked.connect(self.preview_message)
        pass

    def _enbale_next_button(self):
        pass

    def clear(self):
        pass


    def closeEvent(self, event):
        self.clear()

