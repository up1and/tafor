from PyQt5.QtCore import QCoreApplication, QTimer
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLayout

from tafor.states import context
from tafor.models import Taf
from tafor.components.setting import isConfigured
from tafor.components.widgets.editor import BaseEditor
from tafor.components.widgets import TafPrimarySegment, TafFmSegment, TafBecmgSegment, TafTempoSegment


class TafEditor(BaseEditor):

    def __init__(self, parent=None, sender=None):
        super(TafEditor, self).__init__(parent, sender)
        self.initUI()
        self.bindSignal()
        self.setWindowTitle(QCoreApplication.translate('Editor', 'Encoding Terminal Aerodrome Forecast'))
        self.primary.date.setEnabled(False)

    def initUI(self):
        window = QWidget(self)
        layout = QVBoxLayout(window)
        layout.setSizeConstraint(QLayout.SetFixedSize)
        layout.setSpacing(18)
        self.primary = TafPrimarySegment(parent=self)
        self.fm = TafFmSegment('FM', self)
        self.becmg1, self.becmg2, self.becmg3 = TafBecmgSegment('BECMG1', self), TafBecmgSegment('BECMG2', self), TafBecmgSegment('BECMG3', self)
        self.tempo1, self.tempo2, self.tempo3 = TafTempoSegment('TEMPO1', self), TafTempoSegment('TEMPO2', self), TafTempoSegment('TEMPO3', self)
        self.becmgs = [self.fm, self.becmg1, self.becmg2, self.becmg3]
        self.tempos = [self.tempo1, self.tempo2, self.tempo3]
        layout.addWidget(self.primary)
        layout.addWidget(self.fm)
        layout.addWidget(self.becmg1)
        layout.addWidget(self.becmg2)
        layout.addWidget(self.becmg3)
        layout.addWidget(self.tempo1)
        layout.addWidget(self.tempo2)
        layout.addWidget(self.tempo3)
        self.addBottomBox(layout)
        self.setLayout(layout)

        self.setStyleSheet('QLineEdit {width: 50px;} QComboBox {width: 50px;}')

        self.fm.hide()
        self.becmg1.hide()
        self.becmg2.hide()
        self.becmg3.hide()
        self.tempo1.hide()
        self.tempo2.hide()
        self.tempo3.hide()

    def bindSignal(self):
        for c in self.primary.groupCheckboxs:
            c.stateChanged.connect(self.enbaleNextButton)

        # This is a weird bug, when I loop and connect the slot, the lambda function always pass the last value to the slot.
        self.primary.fmCheckbox.toggled.connect(lambda: self.addGroup(self.primary.fmCheckbox))
        self.primary.becmg1Checkbox.toggled.connect(lambda: self.addGroup(self.primary.becmg1Checkbox))
        self.primary.becmg2Checkbox.toggled.connect(lambda: self.addGroup(self.primary.becmg2Checkbox))
        self.primary.becmg3Checkbox.toggled.connect(lambda: self.addGroup(self.primary.becmg3Checkbox))
        self.primary.tempo1Checkbox.toggled.connect(lambda: self.addGroup(self.primary.tempo1Checkbox))
        self.primary.tempo2Checkbox.toggled.connect(lambda: self.addGroup(self.primary.tempo2Checkbox))
        self.primary.tempo3Checkbox.toggled.connect(lambda: self.addGroup(self.primary.tempo3Checkbox))

        self.primary.contentChanged.connect(self.enbaleNextButton)
        for segment in self.becmgs + self.tempos:
            segment.contentChanged.connect(self.enbaleNextButton)

        self.primary.period.textChanged.connect(self.clear)

        # 下一步
        self.nextButton.clicked.connect(self.beforeNext)

    def addGroup(self, clickedbox):
        fmCheckboxs = [self.primary.fmCheckbox]
        becmgCheckboxs = [self.primary.becmg1Checkbox, self.primary.becmg2Checkbox, self.primary.becmg3Checkbox]
        tempoCheckboxs = [self.primary.tempo1Checkbox, self.primary.tempo2Checkbox, self.primary.tempo3Checkbox]
        fmGroups = [self.fm]
        becmgGroups = [self.becmg1, self.becmg2, self.becmg3]
        tempoGroups = [self.tempo1, self.tempo2, self.tempo3]

        checks = [c for c in fmCheckboxs + becmgCheckboxs + tempoCheckboxs if c.isChecked()]
        if len(checks) > 5:
            clickedbox.setChecked(False)
            context.flash.editor('taf', QCoreApplication.translate('Editor', 'Change groups cannot be more than 5'))
            return

        def manipulate(checkboxs, groups):
            if clickedbox not in checkboxs:
                return

            index = checkboxs.index(clickedbox)
            checked = clickedbox.isChecked()

            if checked:
                if index != 0 and not checkboxs[index-1].isChecked():
                    clickedbox.setChecked(False)
            else:
                for i, checkbox in enumerate(checkboxs):
                    if i > index:
                        checkbox.setChecked(False)

            for i, group in enumerate(groups):
                isVisible = checkboxs[i].isChecked()
                group.setVisible(isVisible)

        # FM
        manipulate(fmCheckboxs, fmGroups)
        # BECMG
        manipulate(becmgCheckboxs, becmgGroups)
        # TEMPO
        manipulate(tempoCheckboxs, tempoGroups)

    def previewMessage(self):

        def sortedGroup(groups):
            groups = [e for e in groups if e.isVisible() and e.durations is not None]
            orders = ['FM', 'BECMG', 'TEMPO']
            priority = lambda x: orders.index(x) if x in orders else -1
            return sorted(groups, key=lambda x: (x.durations[0], priority(x.identifier)))

        groupsMessage = [e.message() for e in sortedGroup(self.becmgs + self.tempos)]
        messages = [self.primary.message()] + groupsMessage
        self.text = '\n'.join(filter(None, messages)) + '='
        self.heading = self.primary.heading()
        message = Taf(type=self.heading[0:2], heading=self.heading, text=self.text)
        self.finished.emit(message)

    def beforeNext(self):
        if not self.primary.cnl.isChecked():
            self.primary.validate()

        if self.primary.fmCheckbox.isChecked():
            self.fm.validate()

        if self.primary.becmg1Checkbox.isChecked():
            self.becmg1.validate()

        if self.primary.becmg2Checkbox.isChecked():
            self.becmg2.validate()

        if self.primary.becmg3Checkbox.isChecked():
            self.becmg3.validate()

        if self.primary.tempo1Checkbox.isChecked():
            self.tempo1.validate()

        if self.primary.tempo2Checkbox.isChecked():
            self.tempo2.validate()

        if self.primary.tempo3Checkbox.isChecked():
            self.tempo3.validate()

        if self.hasAcceptableInput():
            self.previewMessage()

    def hasAcceptableInput(self):
        acceptables = [self.primary.hasAcceptableInput()]

        if self.primary.fmCheckbox.isChecked():
            acceptables.append(self.fm.hasAcceptableInput())

        if self.primary.becmg1Checkbox.isChecked():
            acceptables.append(self.becmg1.hasAcceptableInput())

        if self.primary.becmg2Checkbox.isChecked():
            acceptables.append(self.becmg2.hasAcceptableInput())

        if self.primary.becmg3Checkbox.isChecked():
            acceptables.append(self.becmg3.hasAcceptableInput())

        if self.primary.tempo1Checkbox.isChecked():
            acceptables.append(self.tempo1.hasAcceptableInput())

        if self.primary.tempo2Checkbox.isChecked():
            acceptables.append(self.tempo2.hasAcceptableInput())

        if self.primary.tempo3Checkbox.isChecked():
            acceptables.append(self.tempo3.hasAcceptableInput())

        return all(acceptables)

    def enbaleNextButton(self):
        self.nextButton.setEnabled(self.hasAcceptableInput())

    def clear(self):
        self.primary.clear()
        self.fm.clear()
        self.becmg1.clear()
        self.becmg2.clear()
        self.becmg3.clear()
        self.tempo1.clear()
        self.tempo2.clear()
        self.tempo3.clear()

    def closeEvent(self, event):
        super(TafEditor, self).closeEvent(event)
        self.clear()
        self.primary.clearType()

    def showEvent(self, event):
        # 检查必要配置是否完成
        if isConfigured('TAF'):
            if not self.isStaged:
                self.primary.updateMessageType()
        else:
            QTimer.singleShot(0, self.showConfigError)
