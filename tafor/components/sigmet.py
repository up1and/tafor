import datetime

from PyQt5.QtCore import QCoreApplication, Qt
from PyQt5.QtWidgets import QVBoxLayout, QPushButton, QLayout

from tafor import logger
from tafor.components.widgets.editor import BaseEditor
from tafor.components.widgets import SigmetTypeSegment, SigmetGeneralSegment, SigmetTyphoonSegment, SigmetCustomSegment


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
        self.sigmetGeneral = SigmetGeneralSegment()
        self.sigmetTyphoon = SigmetTyphoonSegment()
        self.custom = SigmetCustomSegment()
        self.nextButton = QPushButton()
        self.nextButton.setEnabled(False)
        self.nextButton.setText(QCoreApplication.translate('Editor', 'Next'))
        layout.addWidget(self.type)
        layout.addWidget(self.sigmetGeneral)
        layout.addWidget(self.sigmetTyphoon)
        layout.addWidget(self.custom)
        layout.addWidget(self.nextButton, 0, Qt.AlignRight|Qt.AlignBottom)
        self.setLayout(layout)

        self.sigmetTyphoon.hide()
        self.custom.hide()

    def bindSignal(self):
        self.nextButton.clicked.connect(self.previewMessage)

        self.type.significantWeather.clicked.connect(self.changeSegment)
        self.type.tropicalCyclone.clicked.connect(self.changeSegment)
        self.type.volcanicAsh.clicked.connect(self.changeSegment)
        self.type.custom.clicked.connect(self.changeSegment)
        self.type.cancel.clicked.connect(self.changeSegment)

        self.sigmetGeneral.phenomena.completeSignal.connect(self.enbaleNextButton)
        self.sigmetGeneral.content.completeSignal.connect(self.enbaleNextButton)
        self.sigmetTyphoon.phenomena.completeSignal.connect(self.enbaleNextButton)
        self.sigmetTyphoon.content.completeSignal.connect(self.enbaleNextButton)
        self.custom.phenomena.completeSignal.connect(self.enbaleNextButton)
        self.custom.content.completeSignal.connect(self.enbaleNextButton)

    def changeSegment(self):
        if self.type.template.isChecked():
            if self.type.significantWeather.isChecked():
                self.sigmetGeneral.show()
                self.sigmetTyphoon.hide()
                self.custom.hide()
                self.currentSegment = self.sigmetGeneral

            elif self.type.tropicalCyclone.isChecked():
                self.sigmetGeneral.hide()
                self.sigmetTyphoon.show()
                self.custom.hide()
                self.currentSegment = self.sigmetTyphoon

            elif self.type.volcanicAsh.isChecked():
                # 火山灰模板
                pass

        else:
            self.sigmetGeneral.hide()
            self.sigmetTyphoon.hide()
            self.custom.show()
            self.currentSegment = self.custom


        if self.type.significantWeather.isChecked():
            self.currentSegment.setDuration(4)
            self.type.setType('WS')

        if self.type.tropicalCyclone.isChecked():
            self.currentSegment.setDuration(6)
            self.type.setType('WC')

        if self.type.volcanicAsh.isChecked():
            self.currentSegment.setDuration(6)
            self.type.setType('WV')

    def previewMessage(self):
        self.rpt = self.currentSegment.message()
        self.sign = self.type.message()
        message = {'sign': self.sign, 'rpt': self.rpt, 'full': '\n'.join([self.sign, self.rpt])}
        self.previewSignal.emit(message)
        print(message)

    def enbaleNextButton(self):
        completes = [self.currentSegment.phenomena.complete, self.currentSegment.content.complete]
        enbale = all(completes)
        self.nextButton.setEnabled(enbale)
        logger.debug('phenomena status {}, content status {}'.format(*completes))

    def clear(self):
        self.sigmetGeneral.clear()
        self.sigmetTyphoon.clear()
        self.custom.clear()

    def closeEvent(self, event):
        self.clear()

