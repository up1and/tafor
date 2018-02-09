import datetime

from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

from tafor import logger
from tafor.components.widgets.editor import BaseEditor
from tafor.components.widgets.segments import SigmetTypeSegment, SigmetGeneralSegment


class SigmetEditor(BaseEditor):

    def __init__(self, parent=None, sender=None):
        super(SigmetEditor, self).__init__(parent, sender)
        
        self.initUI()
        self.bindSignal()
        
        self.setWindowTitle(QCoreApplication.translate('Editor', 'Encoding Significant Meteorological Information'))

    def initUI(self):
        window = QWidget(self)
        layout = QVBoxLayout(window)
        layout.setSizeConstraint(QLayout.SetFixedSize)
        self.type = SigmetTypeSegment()
        self.general = SigmetGeneralSegment()
        self.nextButton = QPushButton()
        # self.nextButton.setEnabled(False)
        self.nextButton.setText(QCoreApplication.translate('Editor', 'Next'))
        layout.addWidget(self.type)
        layout.addWidget(self.general)
        layout.addWidget(self.nextButton, 0, Qt.AlignRight|Qt.AlignBottom)
        self.setLayout(layout)

        self.setStyleSheet('QLineEdit {width: 50px;} QComboBox {width: 50px}')

    def bindSignal(self):
    	self.nextButton.clicked.connect(self.message)

    def message(self):
        headMessage = self.type.head()
        typeMessage = self.type.message()
        generalMessage = self.general.message() if self.type.general.isChecked() else ''
        messages = [headMessage, typeMessage, generalMessage]
        print(messages)