import datetime

from PyQt5.QtCore import QCoreApplication, Qt
from PyQt5.QtWidgets import QVBoxLayout, QPushButton, QLayout

from tafor import logger
from tafor.components.widgets.editor import BaseEditor
from tafor.components.widgets import SigmetTypeSegment, SigmetGeneralSegment, SigmetTyphoonSegment, SigmetCancelSegment, SigmetCustomSegment


class SigmetEditor(BaseEditor):

    def __init__(self, parent=None, sender=None):
        super(SigmetEditor, self).__init__(parent, sender)
        self.initUI()
        self.bindSignal()
        
        self.setWindowTitle(QCoreApplication.translate('Editor', 'Encoding Significant Meteorological Information'))
        self.setStyleSheet('QLineEdit {width: 50px;} QComboBox {width: 50px}')

        self.currentSegment = self.sigmetGeneral

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setSizeConstraint(QLayout.SetFixedSize)
        self.type = SigmetTypeSegment()
        self.sigmetGeneral = SigmetGeneralSegment(self.type)
        self.sigmetTyphoon = SigmetTyphoonSegment(self.type)
        self.sigmetCancel = SigmetCancelSegment(self.type)
        self.sigmetCustom = SigmetCustomSegment(self.type)
        self.nextButton = QPushButton()
        self.nextButton.setEnabled(False)
        self.nextButton.setText(QCoreApplication.translate('Editor', 'Next'))
        layout.addWidget(self.type)
        layout.addWidget(self.sigmetGeneral)
        layout.addWidget(self.sigmetTyphoon)
        layout.addWidget(self.sigmetCancel)
        layout.addWidget(self.sigmetCustom)
        layout.addWidget(self.nextButton, 0, Qt.AlignRight|Qt.AlignBottom)
        self.setLayout(layout)

        self.sigmetTyphoon.hide()
        self.sigmetCancel.hide()
        self.sigmetCustom.hide()

    def bindSignal(self):
        self.nextButton.clicked.connect(self.beforeNext)

        self.type.significantWeather.clicked.connect(self.changeSegment)
        self.type.tropicalCyclone.clicked.connect(self.changeSegment)
        self.type.volcanicAsh.clicked.connect(self.changeSegment)
        self.type.template.clicked.connect(self.changeSegment)
        self.type.custom.clicked.connect(self.changeSegment)
        self.type.cancel.clicked.connect(self.changeSegment)

        self.sigmetGeneral.head.completeSignal.connect(self.enbaleNextButton)
        self.sigmetGeneral.content.completeSignal.connect(self.enbaleNextButton)
        self.sigmetTyphoon.head.completeSignal.connect(self.enbaleNextButton)
        self.sigmetTyphoon.content.completeSignal.connect(self.enbaleNextButton)
        self.sigmetCancel.head.completeSignal.connect(self.enbaleNextButton)
        self.sigmetCancel.content.completeSignal.connect(self.enbaleNextButton)
        self.sigmetCustom.head.completeSignal.connect(self.enbaleNextButton)
        self.sigmetCustom.content.completeSignal.connect(self.enbaleNextButton)

    def changeSegment(self, a):
        if self.type.template.isChecked():
            if self.type.significantWeather.isChecked():
                self.sigmetGeneral.show()
                self.sigmetTyphoon.hide()
                self.sigmetCancel.hide()
                self.sigmetCustom.hide()
                self.currentSegment = self.sigmetGeneral

            elif self.type.tropicalCyclone.isChecked():
                self.sigmetGeneral.hide()
                self.sigmetTyphoon.show()
                self.sigmetCancel.hide()
                self.sigmetCustom.hide()
                self.currentSegment = self.sigmetTyphoon

            elif self.type.volcanicAsh.isChecked():
                self.type.custom.setChecked(True)
                self.sigmetGeneral.hide()
                self.sigmetTyphoon.hide()
                self.sigmetCancel.hide()
                self.sigmetCustom.show()
                self.currentSegment = self.sigmetCustom

        elif self.type.cancel.isChecked():
            self.sigmetGeneral.hide()
            self.sigmetTyphoon.hide()
            self.sigmetCancel.show()
            self.sigmetCustom.hide()
            self.currentSegment = self.sigmetCancel
            self.currentSegment.clear()
        else:
            self.sigmetGeneral.hide()
            self.sigmetTyphoon.hide()
            self.sigmetCancel.hide()
            self.sigmetCustom.show()
            self.currentSegment = self.sigmetCustom
            self.currentSegment.clear()

        self.type.template.setEnabled(True)

        if self.type.significantWeather.isChecked():
            self.currentSegment.setType('WS')

        if self.type.tropicalCyclone.isChecked():
            self.currentSegment.setType('WC')

        if self.type.volcanicAsh.isChecked():
            self.currentSegment.setType('WV')
            self.type.template.setEnabled(False)

    def beforeNext(self):
        self.currentSegment.head.validate()

        if self.enbale:
            self.previewMessage()

    def previewMessage(self):
        self.rpt = self.currentSegment.message()
        self.sign = self.type.message()
        message = {'sign': self.sign, 'rpt': self.rpt, 'full': '\n'.join([self.sign, self.rpt])}
        self.previewSignal.emit(message)

    def enbaleNextButton(self):
        completes = [self.currentSegment.head.complete, self.currentSegment.content.complete]
        self.enbale = all(completes)
        self.nextButton.setEnabled(self.enbale)

    def clear(self):
        self.sigmetGeneral.clear()
        self.sigmetTyphoon.clear()
        self.sigmetCustom.clear()
        self.sigmetCancel.clear()

    def closeEvent(self, event):
        self.clear()

    def showEvent(self, event):
        self.currentSegment.head.updateState()

