from uuid import uuid4

from PyQt5.QtCore import QCoreApplication, QTimer, Qt
from PyQt5.QtWidgets import QVBoxLayout, QLayout

from tafor.states import context
from tafor.components.setting import isConfigured
# from tafor.components.widgets import (SigmetTypeSegment, SigmetGeneralSegment, SigmetTyphoonSegment, SigmetAshSegment,
#     AirmetGeneralSegment, SigmetCancelSegment, SigmetCustomSegment)
from tafor.components.widgets import SigmetSegment
from tafor.components.widgets.editor import BaseEditor


class SigmetEditor(BaseEditor):

    def __init__(self, parent=None, sender=None):
        super(SigmetEditor, self).__init__(parent, sender)
        self.initUI()
        self.bindSignal()

        self.setWindowTitle(QCoreApplication.translate('Editor', 'Encoding Significant Meteorological Information'))
        self.setStyleSheet('QLineEdit {width: 50px;} QComboBox {width: 50px;}')

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setSizeConstraint(QLayout.SetFixedSize)
        self.sigmet = SigmetSegment(parent=self)
        layout.addWidget(self.sigmet)
        self.addBottomBox(layout)
        self.setLayout(layout)

    def bindSignal(self):
        self.nextButton.clicked.connect(self.beforeNext)

        # self.sigmetGeneral.head.completeSignal.connect(self.enbaleNextButton)
        # self.sigmetGeneral.content.completeSignal.connect(self.enbaleNextButton)
        # self.sigmetTyphoon.head.completeSignal.connect(self.enbaleNextButton)
        # self.sigmetTyphoon.content.completeSignal.connect(self.enbaleNextButton)
        # self.sigmetAsh.head.completeSignal.connect(self.enbaleNextButton)
        # self.sigmetAsh.content.completeSignal.connect(self.enbaleNextButton)
        # self.sigmetCancel.head.completeSignal.connect(self.enbaleNextButton)
        # self.sigmetCancel.content.completeSignal.connect(self.enbaleNextButton)
        # self.sigmetCustom.head.completeSignal.connect(self.enbaleNextButton)
        # self.sigmetCustom.content.completeSignal.connect(self.enbaleNextButton)
        # self.airmetGeneral.head.completeSignal.connect(self.enbaleNextButton)
        # self.airmetGeneral.content.completeSignal.connect(self.enbaleNextButton)

        # change content self.enbaleNextButton()

        self.sender.sendSignal.connect(self.initState)

    def beforeNext(self):
        self.currentSegment.head.validate()

        if self.enbale:
            self.previewMessage()

    def previewMessage(self):
        self.rpt = self.currentSegment.message()
        self.sign = self.type.message()
        uuid = str(uuid4())
        message = {'sign': self.sign, 'rpt': self.rpt, 'uuid': uuid}
        self.previewSignal.emit(message)

    def enbaleNextButton(self):
        completes = [self.currentSegment.head.complete, self.currentSegment.content.complete]
        self.enbale = all(completes)
        self.nextButton.setEnabled(self.enbale)

    def initState(self):
        # self.sigmet.initState()
        pass

    def loadSigmet(self):
        # self.sigmetCustom.setText()
        pass

    def clear(self):
        # self.sigmetGeneral.clear()
        # self.sigmetTyphoon.clear()
        # self.sigmetAsh.clear()
        # self.sigmetCustom.clear()
        # self.sigmetCancel.clear()
        # self.airmetGeneral.clear()
        pass

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F5:
            context.fir.refresh()

    def closeEvent(self, event):
        super(SigmetEditor, self).closeEvent(event)
        context.notification.sigmet.clear()
        # self.sigmetCustom.setText()
        self.clear()

    def showEvent(self, event):
        # 检查必要配置是否完成
        if isConfigured('SIGMET'):
            if not self.isStaged:
                self.initState()
        else:
            QTimer.singleShot(0, self.showConfigError)
