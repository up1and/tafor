import json
import datetime

from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

from tafor import boolean, conf, logger
from tafor.utils import CheckTAF, Grammar, formatTimeInterval
from tafor.models import db, Tafor, Task
from tafor.components.widgets.editor import BaseEditor
from tafor.components.widgets.segments import TAFPrimarySegment, TAFBecmgSegment, TAFTempoSegment


class BaseTAFEditor(BaseEditor):

    def __init__(self, parent=None, sender=None):
        super(BaseTAFEditor, self).__init__(parent, sender)

        self.initUI()
        self.bindSignal()
        self.updateDate()
        self.updateMessageType()

    def initUI(self):
        window = QWidget(self)
        layout = QVBoxLayout(window)
        layout.setSizeConstraint(QLayout.SetFixedSize)
        self.primary = TAFPrimarySegment()
        self.becmg1, self.becmg2, self.becmg3 = TAFBecmgSegment('BECMG1'), TAFBecmgSegment('BECMG2'), TAFBecmgSegment('BECMG3')
        self.tempo1, self.tempo2 = TAFTempoSegment('TEMPO1'), TAFTempoSegment('TEMPO2')
        self.nextButton = QPushButton()
        self.nextButton.setEnabled(False)
        self.nextButton.setText(self.tr('Next'))
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

        self.primary.fc.clicked.connect(self.updateMessageType)
        self.primary.ft.clicked.connect(self.updateMessageType)

        self.primary.normal.clicked.connect(self.updateMessageType)
        self.primary.cor.clicked.connect(self.updateMessageType)
        self.primary.amd.clicked.connect(self.updateMessageType)
        self.primary.cnl.clicked.connect(self.updateMessageType)

        self.primary.period.textChanged.connect(self.clear)

        self.primary.tmaxTime.editingFinished.connect(lambda :self.verifyTemperatureHour(self.primary.tmaxTime))
        self.primary.tminTime.editingFinished.connect(lambda :self.verifyTemperatureHour(self.primary.tminTime))

        self.primary.tmax.editingFinished.connect(self.verifyTemperature)
        self.primary.tmin.editingFinished.connect(self.verifyTemperature)

        self.becmg1.interval.editingFinished.connect(lambda :self.verifyGroupInterval(self.becmg1.interval))
        self.becmg2.interval.editingFinished.connect(lambda :self.verifyGroupInterval(self.becmg2.interval))
        self.becmg3.interval.editingFinished.connect(lambda :self.verifyGroupInterval(self.becmg3.interval))

        self.tempo1.interval.editingFinished.connect(lambda :self.verifyGroupInterval(self.tempo1.interval, tempo=True))
        self.tempo2.interval.editingFinished.connect(lambda :self.verifyGroupInterval(self.tempo2.interval, tempo=True))

        self.primary.completeSignal.connect(self.enbaleNextButton)
        self.becmg1.completeSignal.connect(self.enbaleNextButton)
        self.becmg2.completeSignal.connect(self.enbaleNextButton)
        self.becmg3.completeSignal.connect(self.enbaleNextButton)
        self.tempo1.completeSignal.connect(self.enbaleNextButton)
        self.tempo2.completeSignal.connect(self.enbaleNextButton)

        # 下一步
        self.nextButton.clicked.connect(self.assembleMessage)
        self.nextButton.clicked.connect(self.previewMessage)

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

    def updateMessageType(self):
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
        taf = CheckTAF(self.tt, self.time)

        currentPeriod = taf.currentPeriod() if isTask else taf.warnPeriod()

        if currentPeriod and taf.existedInLocal(currentPeriod) or not self.primary.date.hasAcceptableInput():
            self.primary.period.clear()
        else:
            self.primary.period.setText(currentPeriod)

    def setAmendPeriod(self):
        taf = CheckTAF(self.tt, self.time)
        self.amdPeriod = taf.warnPeriod()
        self.primary.period.setText(self.amdPeriod)

    def amendNumber(self, sign):
        expired = datetime.datetime.utcnow() - datetime.timedelta(hours=24)
        query = db.query(Tafor).filter(Tafor.rpt.contains(self.amdPeriod), Tafor.sent > expired)
        if sign == 'COR':
            items = query.filter(Tafor.rpt.contains('COR')).all()
            order = chr(ord('A') + len(items))
            return 'CC' + order
        elif sign == 'AMD':
            items = query.filter(Tafor.rpt.contains('AMD')).all()
            order = chr(ord('A') + len(items))
            return 'AA' + order

    def periodDuration(self):
        period = self.primary.period.text()
        if len(period) == 6:
            return formatTimeInterval(period[2:])

    def groupInterval(self, interval):
        start, end = formatTimeInterval(interval)
        if start < self.periods[0]:
            start += datetime.timedelta(days=1)
            end += datetime.timedelta(days=1)
        return start, end

    def verifyTemperatureHour(self, line):
        if self.periods is not None:
            tempHour = formatTimeInterval(line.text())[0]

            if tempHour < self.periods[0]:
                tempHour += datetime.timedelta(days=1) 

            valid = self.periods[0] <= tempHour <= self.periods[1]

            if not valid:
                line.clear()
                self.parent.statusBar.showMessage(self.tr('Hour of temperature is not corret'), 5000)

    def verifyTemperature(self):
        tmax = self.primary.tmax.text()
        tmin = self.primary.tmin.text()
        if tmax and tmin:
            tmax = -int(tmax[1:]) if 'M' in tmax else int(tmax)
            tmin = -int(tmin[1:]) if 'M' in tmin else int(tmin)
            if tmax <= tmin:
                self.primary.tmin.clear()

    def verifyGroupInterval(self, line, tempo=False):
        if tempo and self.tt == 'FC':
            maxTime = 4
        elif tempo and self.tt == 'FT':
            maxTime = 6
        else:
            maxTime = 2

        start, end = self.groupInterval(line.text())
        if start < self.periods[0] or self.periods[1] < start:
            line.clear()
            self.parent.statusBar.showMessage(self.tr('Start time of change group is not corret %s') % start.strftime('%Y-%m-%d %H:%M:%S'), 5000)

        if end < self.periods[0] or self.periods[1] < end:
            line.clear()
            self.parent.statusBar.showMessage(self.tr('End time of change group is not corret %s') % end.strftime('%Y-%m-%d %H:%M:%S'), 5000)

        if end - start > datetime.timedelta(hours=maxTime):
            line.clear()
            self.parent.statusBar.showMessage(self.tr('Change group time more than %s hours') % str(maxTime), 5000)

    def assembleMessage(self):
        primaryMessage = self.primary.message()
        becmg1Message = self.becmg1.message() if self.primary.becmg1Checkbox.isChecked() else ''
        becmg2Message = self.becmg2.message() if self.primary.becmg2Checkbox.isChecked() else ''
        becmg3Message = self.becmg3.message() if self.primary.becmg3Checkbox.isChecked() else ''
        tempo1Message = self.tempo1.message() if self.primary.tempo1Checkbox.isChecked() else ''
        tempo2Message = self.tempo2.message() if self.primary.tempo2Checkbox.isChecked() else ''
        messages = [primaryMessage, becmg1Message, becmg2Message, becmg3Message, tempo1Message, tempo2Message]
        self.rpt = '\n'.join(filter(None, messages)) + '='
        self.head = self.primary.head()

    def updateDate(self):
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

        enbale = all(completes)

        self.nextButton.setEnabled(enbale)

    def clear(self):
        self.primary.clear()
        self.becmg1.clear()
        self.becmg2.clear()
        self.becmg3.clear()
        self.tempo1.clear()
        self.tempo2.clear()

    def closeEvent(self, event):
        self.clear()
        self.updateMessageType()


class TAFEditor(BaseTAFEditor):

    def __init__(self, parent=None, sender=None):
        super(TAFEditor, self).__init__(parent, sender)
        self.setWindowTitle(self.tr('Encoding Message'))
        self.primary.date.setEnabled(False)

        self.timer = QTimer()
        self.timer.timeout.connect(self.updateDate)
        self.timer.start(1 * 1000)

    def previewMessage(self):
        message = {'head': self.head, 'rpt':self.rpt, 'full': '\n'.join([self.head, self.rpt])}
        self.previewSignal.emit(message)
        logger.debug('TAF Edit ' + message['full'])


class TaskTAFEditor(BaseTAFEditor):

    def __init__(self, parent=None, sender=None):
        super(TaskTAFEditor, self).__init__(parent, sender)

        self.setWindowTitle(self.tr('Timing Tasks'))
        self.setWindowIcon(QIcon(':/time.png'))

        self.primary.sortGroup.hide()

        self.primary.date.editingFinished.connect(self.taskTime)
        self.primary.date.editingFinished.connect(lambda :self.setNormalPeriod(isTask=True))
        self.primary.date.editingFinished.connect(self.changeWindowTitle)
        self.primary.date.editingFinished.connect(self.periodDuration)

        self.sender.sendSignal.connect(self.hide)
        self.sender.sendSignal.connect(self.sender.hide)
        self.sender.sendSignal.connect(self.parent.taskBrowser.show)
        self.sender.sendSignal.connect(self.parent.taskBrowser.updateGUI)
        
    def previewMessage(self):
        message = {'head': self.head, 'rpt':self.rpt, 'full': '\n'.join([self.head, self.rpt]), 'plan': self.time}
        self.previewSignal.emit(message)
        log.debug('Emit', message)

    def taskTime(self):
        date = self.primary.date.text()
        now = datetime.datetime.utcnow()

        day = int(date[0:2])
        hour = int(date[2:4])
        minute = int(date[4:])

        try:
            self.time = datetime.datetime(now.year, now.month, day, hour, minute)
            if self.time < now:
                self.time = datetime.datetime(now.year, now.month+1, day, hour, minute)

        except ValueError as e:
            self.time = datetime.datetime(now.year, now.month+2, day, hour, minute)

        finally:
            logger.debug(' '.join(['Task time', self.time.strftime('%Y-%m-%d %H:%M:%S')]))
            return self.time

    def changeWindowTitle(self):
        self.setWindowTitle(self.tr('Timing Tasks %s') % self.time.strftime('%Y-%m-%d %H:%M'))

