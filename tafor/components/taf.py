import json
import datetime

from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QCoreApplication, Qt, QTimer
from PyQt5.QtWidgets import QWidget, QMessageBox, QVBoxLayout, QPushButton, QLayout

from tafor import boolean, conf, logger
from tafor.utils import CheckTaf, Grammar
from tafor.utils.convert import parseTimeInterval, parseDateTime
from tafor.models import db, Taf, Task
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
        self.primary = TafPrimarySegment()
        self.becmg1, self.becmg2, self.becmg3 = TafBecmgSegment('BECMG1'), TafBecmgSegment('BECMG2'), TafBecmgSegment('BECMG3')
        self.tempo1, self.tempo2 = TafTempoSegment('TEMPO1'), TafTempoSegment('TEMPO2')
        self.nextButton = QPushButton()
        self.nextButton.setEnabled(False)
        self.nextButton.setText(QCoreApplication.translate('Editor', 'Next'))
        layout.addWidget(self.primary)
        layout.addWidget(self.becmg1)
        layout.addWidget(self.becmg2)
        layout.addWidget(self.becmg3)
        layout.addWidget(self.tempo1)
        layout.addWidget(self.tempo2)
        layout.addWidget(self.nextButton, 0, Qt.AlignRight|Qt.AlignBottom)
        self.setLayout(layout)

        self.setStyleSheet('QLineEdit {width: 50px;} QComboBox {width: 50px}')

        self.becmg1.hide()
        self.becmg2.hide()
        self.becmg3.hide()
        self.tempo1.hide()
        self.tempo2.hide()

    def bindSignal(self):
        self.primary.becmg1Checkbox.toggled.connect(self.addGroup)
        self.primary.becmg2Checkbox.toggled.connect(self.addGroup)
        self.primary.becmg3Checkbox.toggled.connect(self.addGroup)
        self.primary.tempo1Checkbox.toggled.connect(self.addGroup)
        self.primary.tempo2Checkbox.toggled.connect(self.addGroup)

        self.primary.becmg1Checkbox.toggled.connect(self.becmg1.checkComplete)
        self.primary.becmg2Checkbox.toggled.connect(self.becmg2.checkComplete)
        self.primary.becmg3Checkbox.toggled.connect(self.becmg3.checkComplete)
        self.primary.tempo1Checkbox.toggled.connect(self.tempo1.checkComplete)
        self.primary.tempo2Checkbox.toggled.connect(self.tempo2.checkComplete)

        self.primary.fc.clicked.connect(self.changeMessageType)
        self.primary.ft.clicked.connect(self.changeMessageType)

        self.primary.normal.clicked.connect(self.changeMessageType)
        self.primary.cor.clicked.connect(self.changeMessageType)
        self.primary.amd.clicked.connect(self.changeMessageType)
        self.primary.cnl.clicked.connect(self.changeMessageType)
        self.primary.prev.clicked.connect(self.setPreviousPeriod)

        self.primary.period.textChanged.connect(self.clear)

        self.primary.tmaxTime.editingFinished.connect(lambda :self.validateTemperatureHour(self.primary.tmaxTime))
        self.primary.tminTime.editingFinished.connect(lambda :self.validateTemperatureHour(self.primary.tminTime))

        self.primary.tmax.editingFinished.connect(self.validateTemperature)
        self.primary.tmin.editingFinished.connect(self.validateTemperature)

        self.becmg1.interval.editingFinished.connect(lambda :self.validateChangeGroupInterval(self.becmg1.interval))
        self.becmg2.interval.editingFinished.connect(lambda :self.validateChangeGroupInterval(self.becmg2.interval))
        self.becmg3.interval.editingFinished.connect(lambda :self.validateChangeGroupInterval(self.becmg3.interval))

        self.tempo1.interval.editingFinished.connect(lambda :self.validateChangeGroupInterval(self.tempo1.interval, tempo=True))
        self.tempo2.interval.editingFinished.connect(lambda :self.validateChangeGroupInterval(self.tempo2.interval, tempo=True))

        self.primary.completeSignal.connect(self.enbaleNextButton)
        self.becmg1.completeSignal.connect(self.enbaleNextButton)
        self.becmg2.completeSignal.connect(self.enbaleNextButton)
        self.becmg3.completeSignal.connect(self.enbaleNextButton)
        self.tempo1.completeSignal.connect(self.enbaleNextButton)
        self.tempo2.completeSignal.connect(self.enbaleNextButton)

        # 下一步
        self.nextButton.clicked.connect(self.beforeNext)

    def addGroup(self):
        # BECMG
        if self.primary.becmg1Checkbox.isChecked():
            self.becmg1.setVisible(True)
        else:
            self.becmg1.setVisible(False)
            self.becmg2.setVisible(False)
            self.becmg3.setVisible(False)
            self.primary.becmg2Checkbox.setChecked(False)
            self.primary.becmg3Checkbox.setChecked(False)

        if self.primary.becmg2Checkbox.isChecked():
            self.becmg2.setVisible(True)
        else:
            self.becmg2.setVisible(False)
            self.becmg3.setVisible(False)
            self.primary.becmg3Checkbox.setChecked(False)

        if self.primary.becmg3Checkbox.isChecked():
            self.becmg3.setVisible(True)
        else:
            self.becmg3.setVisible(False)

        # TEMPO
        if self.primary.tempo1Checkbox.isChecked():
            self.tempo1.setVisible(True)
        else:
            self.tempo1.setVisible(False)
            self.tempo2.setVisible(False)
            self.primary.tempo2Checkbox.setChecked(False)

        if self.primary.tempo2Checkbox.isChecked():
            self.tempo2.setVisible(True)
        else:
            self.tempo2.setVisible(False)

    def changeMessageType(self):
        if self.primary.fc.isChecked():
            self.tt = 'FC'

        if self.primary.ft.isChecked():
            self.tt = 'FT'

        if self.primary.date.text():
            if self.primary.normal.isChecked():
                self.setNormalPeriod()

                self.primary.ccc.clear()
                self.primary.ccc.setEnabled(False)
                self.primary.aaa.clear()
                self.primary.aaa.setEnabled(False)
                self.primary.aaaCnl.clear()
                self.primary.aaaCnl.setEnabled(False)
            else:
                self.setAmendPeriod()

                if self.primary.cor.isChecked():
                    self.primary.ccc.setEnabled(True)
                    order = self.amendNumber('COR')
                    self.primary.ccc.setText(order)
                else:
                    self.primary.ccc.clear()
                    self.primary.ccc.setEnabled(False)

                if self.primary.amd.isChecked():
                    self.primary.aaa.setEnabled(True)
                    order = self.amendNumber('AMD')
                    self.primary.aaa.setText(order)
                else:
                    self.primary.aaa.clear()
                    self.primary.aaa.setEnabled(False)

                if self.primary.cnl.isChecked():
                    self.primary.aaaCnl.setEnabled(True)
                    order = self.amendNumber('AMD')
                    self.primary.aaaCnl.setText(order)
                else:
                    self.primary.aaaCnl.clear()
                    self.primary.aaaCnl.setEnabled(False)

            self.periods = self.periodDuration()

    def setNormalPeriod(self, isTask=False):
        prev = 1 if self.primary.prev.isChecked() else 0
        taf = CheckTaf(self.tt, time=self.time, prev=prev)
        period = taf.normalPeriod() if isTask else taf.warningPeriod()

        if period and taf.local(period) or not self.primary.date.hasAcceptableInput():
            self.primary.period.clear()
        else:
            self.primary.period.setText(period)

    def setAmendPeriod(self):
        prev = 1 if self.primary.prev.isChecked() else 0
        taf = CheckTaf(self.tt, self.time, prev=prev)
        self.amdPeriod = taf.warningPeriod()
        self.primary.period.setText(self.amdPeriod)

    def setPreviousPeriod(self, checked):
        if checked:
            title = QCoreApplication.translate('Editor', 'Tips')
            text = QCoreApplication.translate('Editor', 'Do you want to change the message valid period to previous?')
            ret = QMessageBox.question(self, title, text)
            if ret == QMessageBox.Yes:
                self.changeMessageType()
            else:
                self.primary.prev.setChecked(False)
        else:
            self.changeMessageType()

    def amendNumber(self, sort):
        expired = datetime.datetime.utcnow() - datetime.timedelta(hours=24)
        query = db.query(Taf).filter(Taf.rpt.contains(self.amdPeriod), Taf.sent > expired)
        if sort == 'COR':
            items = query.filter(Taf.rpt.contains('COR')).all()
            order = chr(ord('A') + len(items))
            return 'CC' + order
        elif sort == 'AMD':
            items = query.filter(Taf.rpt.contains('AMD')).all()
            order = chr(ord('A') + len(items))
            return 'AA' + order

    def periodDuration(self):
        period = self.primary.period.text()
        if len(period) == 6:
            return parseTimeInterval(period[2:], self.time)

    def groupInterval(self, interval):
        start, end = parseTimeInterval(interval)
        if start < self.periods[0]:
            start += datetime.timedelta(days=1)
            end += datetime.timedelta(days=1)
        return start, end

    def validateTemperatureHour(self, line):
        if self.periods is not None:
            tempHour = parseTimeInterval(line.text(), self.time)[0]

            if tempHour < self.periods[0]:
                tempHour += datetime.timedelta(days=1)

            valid = self.periods[0] <= tempHour <= self.periods[1] and self.primary.tmaxTime.text() != self.primary.tminTime.text()

            if not valid:
                line.clear()
                self.parent.statusBar.showMessage(QCoreApplication.translate('Editor', 'Hour of temperature is not corret'), 5000)

    def validateTemperature(self):
        tmax = self.primary.tmax.text()
        tmin = self.primary.tmin.text()
        if tmax and tmin:
            tmax = -int(tmax[1:]) if 'M' in tmax else int(tmax)
            tmin = -int(tmin[1:]) if 'M' in tmin else int(tmin)
            if tmax <= tmin:
                self.primary.tmin.clear()

    def validateChangeGroupInterval(self, line, tempo=False):
        if not self.periods:
            line.clear()
            return

        if tempo and self.tt == 'FC':
            maxTime = 4
        elif tempo and self.tt == 'FT':
            maxTime = 6
        else:
            maxTime = 2

        start, end = self.groupInterval(line.text())
        if start < self.periods[0] or self.periods[1] < start:
            line.clear()
            self.parent.statusBar.showMessage(QCoreApplication.translate('Editor', 'Start time of change group is not corret %s') % start.strftime('%Y-%m-%d %H:%M:%S'), 5000)

        if end < self.periods[0] or self.periods[1] < end:
            line.clear()
            self.parent.statusBar.showMessage(QCoreApplication.translate('Editor', 'End time of change group is not corret %s') % end.strftime('%Y-%m-%d %H:%M:%S'), 5000)

        if end - start > datetime.timedelta(hours=maxTime):
            line.clear()
            self.parent.statusBar.showMessage(QCoreApplication.translate('Editor', 'Change group time more than %s hours') % str(maxTime), 5000)

    def assembleMessage(self):
        primaryMessage = self.primary.message()
        becmg1Message = self.becmg1.message() if self.primary.becmg1Checkbox.isChecked() else ''
        becmg2Message = self.becmg2.message() if self.primary.becmg2Checkbox.isChecked() else ''
        becmg3Message = self.becmg3.message() if self.primary.becmg3Checkbox.isChecked() else ''
        tempo1Message = self.tempo1.message() if self.primary.tempo1Checkbox.isChecked() else ''
        tempo2Message = self.tempo2.message() if self.primary.tempo2Checkbox.isChecked() else ''
        messages = [primaryMessage, becmg1Message, becmg2Message, becmg3Message, tempo1Message, tempo2Message]
        self.rpt = '\n'.join(filter(None, messages)) + '='
        self.sign = self.primary.sign()

    def beforeNext(self):
        self.validateTemperature()
        self.validateTemperatureHour(self.primary.tmaxTime)
        self.validateTemperatureHour(self.primary.tminTime)
        self.primary.validate()

        if self.primary.becmg1Checkbox.isChecked():
            self.validateChangeGroupInterval(self.becmg1.interval)
            self.becmg1.validate()

        if self.primary.becmg2Checkbox.isChecked():
            self.validateChangeGroupInterval(self.becmg2.interval)
            self.becmg2.validate()

        if self.primary.becmg3Checkbox.isChecked():
            self.validateChangeGroupInterval(self.becmg3.interval)
            self.becmg3.validate()

        if self.primary.tempo1Checkbox.isChecked():
            self.validateChangeGroupInterval(self.tempo1.interval, tempo=True)
            self.tempo1.validate()

        if self.primary.tempo2Checkbox.isChecked():
            self.validateChangeGroupInterval(self.tempo2.interval, tempo=True)
            self.tempo2.validate()
        
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

        self.enbale = all(completes)

        self.nextButton.setEnabled(self.enbale)

    def clear(self):
        self.primary.clear()
        self.becmg1.clear()
        self.becmg2.clear()
        self.becmg3.clear()
        self.tempo1.clear()
        self.tempo2.clear()

    def closeEvent(self, event):
        self.clear()

    def showEvent(self, event):
        self.setDate()
        self.changeMessageType()

        # Check Settings


class TafEditor(BaseTafEditor):

    def __init__(self, parent=None, sender=None):
        super(TafEditor, self).__init__(parent, sender)
        self.setWindowTitle(QCoreApplication.translate('Editor', 'Encoding Terminal Aerodrome Forecast'))
        self.primary.date.setEnabled(False)

        self.timer = QTimer()
        self.timer.timeout.connect(self.setDate)
        self.timer.start(1 * 1000)

    def previewMessage(self):
        message = {'sign': self.sign, 'rpt': self.rpt, 'full': '\n'.join([self.sign, self.rpt])}
        self.previewSignal.emit(message)


class TaskTafEditor(BaseTafEditor):

    def __init__(self, parent=None, sender=None):
        super(TaskTafEditor, self).__init__(parent, sender)
        self.setWindowTitle(QCoreApplication.translate('Editor', 'Timing Tasks'))
        self.setWindowIcon(QIcon(':/time.png'))

        self.primary.sortGroup.hide()
        self.primary.date.editingFinished.connect(self.updateState)
        self.sender.sendSignal.connect(self.afterSend)
        
    def previewMessage(self):
        message = {'sign': self.sign, 'rpt':self.rpt, 'full': '\n'.join([self.sign, self.rpt]), 'planning': self.time}
        self.previewSignal.emit(message)

    def updateState(self):
        date = self.primary.date.text()
        self.time = parseDateTime(date)
        self.setWindowTitle(self.time.strftime('%Y-%m-%d %H:%M'))
        self.setNormalPeriod(isTask=True)
        self.periods = self.periodDuration()

    def afterSend(self):
        self.parent.taskBrowser.show()
        self.parent.taskBrowser.updateGui()

