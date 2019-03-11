import datetime

from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QCoreApplication, QTimer
from PyQt5.QtWidgets import QWidget, QMessageBox, QVBoxLayout, QLayout

from tafor import conf
from tafor.utils.convert import parseDateTime, isOverlap
from tafor.states import context
from tafor.models import db, Taf
from tafor.components.setting import isConfigured
from tafor.components.widgets.editor import BaseEditor
from tafor.components.widgets import TafPrimarySegment, TafBecmgSegment, TafTempoSegment


class BaseTafEditor(BaseEditor):

    def __init__(self, parent=None, sender=None):
        super(BaseTafEditor, self).__init__(parent, sender)
        self.initUI()
        self.bindSignal()

    def initUI(self):
        window = QWidget(self)
        layout = QVBoxLayout(window)
        layout.setSizeConstraint(QLayout.SetFixedSize)
        self.primary = TafPrimarySegment(parent=self)
        self.becmgs = self.becmg1, self.becmg2, self.becmg3 = TafBecmgSegment('BECMG1', self), TafBecmgSegment('BECMG2', self), TafBecmgSegment('BECMG3', self)
        self.tempos = self.tempo1, self.tempo2, self.tempo3= TafTempoSegment('TEMPO1', self), TafTempoSegment('TEMPO2', self), TafTempoSegment('TEMPO3', self)
        layout.addWidget(self.primary)
        layout.addWidget(self.becmg1)
        layout.addWidget(self.becmg2)
        layout.addWidget(self.becmg3)
        layout.addWidget(self.tempo1)
        layout.addWidget(self.tempo2)
        layout.addWidget(self.tempo3)
        self.addBottomBox(layout)
        self.setLayout(layout)

        self.setStyleSheet('QLineEdit {width: 50px;} QComboBox {width: 50px;}')

        self.becmg1.hide()
        self.becmg2.hide()
        self.becmg3.hide()
        self.tempo1.hide()
        self.tempo2.hide()
        self.tempo3.hide()

    def bindSignal(self):
        self.primary.becmg1Checkbox.toggled.connect(self.addGroup)
        self.primary.becmg2Checkbox.toggled.connect(self.addGroup)
        self.primary.becmg3Checkbox.toggled.connect(self.addGroup)
        self.primary.tempo1Checkbox.toggled.connect(self.addGroup)
        self.primary.tempo2Checkbox.toggled.connect(self.addGroup)
        self.primary.tempo3Checkbox.toggled.connect(self.addGroup)

        self.primary.becmg1Checkbox.toggled.connect(self.becmg1.checkComplete)
        self.primary.becmg2Checkbox.toggled.connect(self.becmg2.checkComplete)
        self.primary.becmg3Checkbox.toggled.connect(self.becmg3.checkComplete)
        self.primary.tempo1Checkbox.toggled.connect(self.tempo1.checkComplete)
        self.primary.tempo2Checkbox.toggled.connect(self.tempo2.checkComplete)
        self.primary.tempo3Checkbox.toggled.connect(self.tempo3.checkComplete)

        self.primary.period.textChanged.connect(self.clear)

        self.becmg1.period.editingFinished.connect(lambda :self.validateChangeGroupPeriod(self.becmg1))
        self.becmg2.period.editingFinished.connect(lambda :self.validateChangeGroupPeriod(self.becmg2))
        self.becmg3.period.editingFinished.connect(lambda :self.validateChangeGroupPeriod(self.becmg3))

        self.tempo1.period.editingFinished.connect(lambda :self.validateChangeGroupPeriod(self.tempo1))
        self.tempo2.period.editingFinished.connect(lambda :self.validateChangeGroupPeriod(self.tempo2))
        self.tempo3.period.editingFinished.connect(lambda :self.validateChangeGroupPeriod(self.tempo3))

        self.primary.completeSignal.connect(self.enbaleNextButton)
        self.becmg1.completeSignal.connect(self.enbaleNextButton)
        self.becmg2.completeSignal.connect(self.enbaleNextButton)
        self.becmg3.completeSignal.connect(self.enbaleNextButton)
        self.tempo1.completeSignal.connect(self.enbaleNextButton)
        self.tempo2.completeSignal.connect(self.enbaleNextButton)
        self.tempo3.completeSignal.connect(self.enbaleNextButton)

        # 下一步
        self.nextButton.clicked.connect(self.beforeNext)

    def addGroup(self):

        def manipulate(group1, group2, group3):
            if getattr(self.primary, group1 + 'Checkbox').isChecked():
                getattr(self, group1).setVisible(True)
            else:
                getattr(self, group1).setVisible(False)
                getattr(self, group2).setVisible(False)
                getattr(self, group3).setVisible(False)
                getattr(self.primary, group2 + 'Checkbox').setChecked(False)
                getattr(self.primary, group3 + 'Checkbox').setChecked(False)

            if getattr(self.primary, group2 + 'Checkbox').isChecked():
                getattr(self, group2).setVisible(True)
            else:
                getattr(self, group2).setVisible(False)
                getattr(self, group3).setVisible(False)
                getattr(self.primary, group3 + 'Checkbox').setChecked(False)

            if getattr(self.primary, group3 + 'Checkbox').isChecked():
                getattr(self, group3).setVisible(True)
            else:
                getattr(self, group3).setVisible(False)

        # BECMG
        manipulate('becmg1', 'becmg2', 'becmg3')
        # TEMPO
        manipulate('tempo1', 'tempo2', 'tempo3')

    def validateChangeGroupPeriod(self, group):
        line = group.period
        isTempo = group.id.startswith('TEMPO')
        if not self.durations:
            line.clear()
            return

        if isTempo and self.tt == 'FC':
            maxTime = 4
        elif isTempo and self.tt == 'FT':
            maxTime = 6
        else:
            maxTime = 2

        period = start, end = self.groupPeriod(line.text())
        if start < self.durations[0] or self.durations[1] < start:
            line.clear()
            self.showNotificationMessage(QCoreApplication.translate('Editor', 'Start time of change group is not corret'))
            return

        if end < self.durations[0] or self.durations[1] < end:
            line.clear()
            self.showNotificationMessage(QCoreApplication.translate('Editor', 'End time of change group is not corret'))
            return

        if end - start > datetime.timedelta(hours=maxTime):
            line.clear()
            self.showNotificationMessage(QCoreApplication.translate('Editor', 'Change group time more than {} hours').format(maxTime))
            return

        def isIntervalOverlay(period, periods):
            for p in periods:
                if isOverlap(period, p):
                    return True

        groups = self.tempos if isTempo else self.becmgs
        periods = [g.periods for g in groups if g.periods and group != g]
        if isIntervalOverlay(period, periods):
            line.clear()
            self.showNotificationMessage(QCoreApplication.translate('Editor', 'Change group time is overlap'))
        else:
            group.periods = period

    def assembleMessage(self):
        primaryMessage = self.primary.message()
        becmgsMessage = [e.message() for e in self.becmgs if e.isVisible()]
        temposMessage = [e.message() for e in self.tempos if e.isVisible()]
        messages = [primaryMessage] + becmgsMessage + temposMessage
        self.rpt = '\n'.join(filter(None, messages)) + '='
        self.sign = self.primary.sign()

    def beforeNext(self):
        if not self.primary.cnl.isChecked():
            self.validateTemperature()
            self.validateTemperatureHour(self.primary.tmaxTime)
            self.validateTemperatureHour(self.primary.tminTime)
            self.primary.validate()

        if self.primary.becmg1Checkbox.isChecked():
            self.validateChangeGroupInterval(self.becmg1)
            self.becmg1.validate()

        if self.primary.becmg2Checkbox.isChecked():
            self.validateChangeGroupInterval(self.becmg2)
            self.becmg2.validate()

        if self.primary.becmg3Checkbox.isChecked():
            self.validateChangeGroupInterval(self.becmg3)
            self.becmg3.validate()

        if self.primary.tempo1Checkbox.isChecked():
            self.validateChangeGroupInterval(self.tempo1)
            self.tempo1.validate()

        if self.primary.tempo2Checkbox.isChecked():
            self.validateChangeGroupInterval(self.tempo2)
            self.tempo2.validate()

        if self.primary.tempo3Checkbox.isChecked():
            self.validateChangeGroupInterval(self.tempo3)
            self.tempo3.validate()

        if self.enbale:
            self.assembleMessage()
            self.previewMessage()

    def setDate(self):
        self.time = datetime.datetime.utcnow()
        self.primary.date.setText(self.time.strftime('%d%H%M'))

    def enbaleNextButton(self):
        # 允许下一步
        completes = [self.primary.complete]

        if self.primary.becmg1Checkbox.isChecked():
            completes.append(self.becmg1.complete)

        if self.primary.becmg2Checkbox.isChecked():
            completes.append(self.becmg2.complete)

        if self.primary.becmg3Checkbox.isChecked():
            completes.append(self.becmg3.complete)

        if self.primary.tempo1Checkbox.isChecked():
            completes.append(self.tempo1.complete)

        if self.primary.tempo2Checkbox.isChecked():
            completes.append(self.tempo2.complete)

        if self.primary.tempo3Checkbox.isChecked():
            completes.append(self.tempo3.complete)

        self.enbale = all(completes)

        self.nextButton.setEnabled(self.enbale)

    def clear(self):
        self.primary.clear()
        self.becmg1.clear()
        self.becmg2.clear()
        self.becmg3.clear()
        self.tempo1.clear()
        self.tempo2.clear()
        self.tempo3.clear()

    def closeEvent(self, event):
        self.clear()

    def showEvent(self, event):
        # 检查必要配置是否完成
        if isConfigured('TAF'):
            self.primary.setMessageType()
        else:
            QTimer.singleShot(0, self.showConfigError)


class TafEditor(BaseTafEditor):

    def __init__(self, parent=None, sender=None):
        super(TafEditor, self).__init__(parent, sender)
        self.setWindowTitle(QCoreApplication.translate('Editor', 'Encoding Terminal Aerodrome Forecast'))
        self.primary.date.setEnabled(False)

    def previewMessage(self):
        message = {'sign': self.sign, 'rpt': self.rpt}
        self.previewSignal.emit(message)


class TaskTafEditor(BaseTafEditor):

    def __init__(self, parent=None, sender=None):
        super(TaskTafEditor, self).__init__(parent, sender)
        self.title = QCoreApplication.translate('Editor', 'Encoding Terminal Aerodrome Forecast - Delay Send')
        self.setWindowTitle(self.title)
        self.setWindowIcon(QIcon(':/time.png'))

        self.primary.sortGroup.hide()
        self.primary.date.editingFinished.connect(self.updateState)
        self.sender.sendSignal.connect(self.afterSend)

    def previewMessage(self):
        message = {'sign': self.sign, 'rpt':self.rpt, 'planning': self.time}
        self.previewSignal.emit(message)

    def updateState(self):
        date = self.primary.date.text()
        self.time = parseDateTime(date)
        self.setWindowTitle(self.title + ' - {}'.format(self.time.strftime('%Y-%m-%d %H:%M')))
        self.setNormalPeriod(isTask=True)
        self.durations = self.periodDuration()

    def afterSend(self):
        self.parent.taskBrowser.show()
        self.parent.taskBrowser.updateGui()

