import datetime

from PyQt5.QtCore import QCoreApplication, Qt
from PyQt5.QtWidgets import QVBoxLayout, QPushButton, QLayout

from tafor import logger
from tafor.components.widgets.editor import BaseEditor
from tafor.components.widgets.segments import SigmetTypeSegment, SigmetGeneralSegment, SigmetTyphoonSegment, SigmetCustomSegment


class SigmetEditor(BaseEditor):

    def __init__(self, parent=None, sender=None):
        super(SigmetEditor, self).__init__(parent, sender)
        self.initUI()
        self.bindSignal()
        
        self.setWindowTitle(QCoreApplication.translate('Editor', 'Encoding Significant Meteorological Information'))
        self.setStyleSheet('QLineEdit {width: 50px;} QComboBox {width: 50px}')

        self.currentSegment = self.general

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setSizeConstraint(QLayout.SetFixedSize)
        self.type = SigmetTypeSegment()
        self.general = SigmetGeneralSegment()
        self.typhoon = SigmetTyphoonSegment()
        self.custom = SigmetCustomSegment()
        self.nextButton = QPushButton()
        # self.nextButton.setEnabled(False)
        self.nextButton.setText(QCoreApplication.translate('Editor', 'Next'))
        layout.addWidget(self.type)
        layout.addWidget(self.general)
        layout.addWidget(self.typhoon)
        layout.addWidget(self.custom)
        layout.addWidget(self.nextButton, 0, Qt.AlignRight|Qt.AlignBottom)
        self.setLayout(layout)

        self.typhoon.hide()
        self.custom.hide()

    def bindSignal(self):
        self.nextButton.clicked.connect(self.message)

        self.type.general.clicked.connect(self.changeSegment)
        self.type.tropicalCyclone.clicked.connect(self.changeSegment)
        self.type.volcanicAsh.clicked.connect(self.changeSegment)
        self.type.custom.clicked.connect(self.changeSegment)
        self.type.cancel.clicked.connect(self.changeSegment)

    def changeSegment(self):
        if self.type.general.isChecked():
            self.general.show()
            self.typhoon.hide()
            self.custom.hide()

            self.currentSegment = self.general

        if self.type.tropicalCyclone.isChecked():
            self.general.hide()
            self.typhoon.show()
            self.custom.hide()

            self.currentSegment = self.typhoon

        if self.type.custom.isChecked() or self.type.cancel.isChecked() or self.type.volcanicAsh.isChecked():
            self.general.hide()
            self.typhoon.hide()
            self.custom.show()

            self.currentSegment = self.custom



    def message(self):
        headMessage = self.type.head()
        typeMessage = self.type.message()
        generalMessage = self.general.message() if self.type.general.isChecked() else ''
        messages = [headMessage, typeMessage, generalMessage]
        print(messages)