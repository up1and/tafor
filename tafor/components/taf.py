# -*- coding: utf-8 -*-
import json
import datetime

from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

from tafor import logger
from tafor.utils import CheckTAF, Grammar
from tafor.models import db, Tafor, Task
from tafor.components.widgets.segments import TAFPrimarySegment, TAFBecmgSegment, TAFTempoSegment


class BaseEditor(QDialog):
    previewSignal = pyqtSignal(dict)

    def __init__(self, parent=None):
        super(BaseEditor, self).__init__(parent)
        self.parent = parent

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
        self.nextButton.setText("下一步")
        layout.addWidget(self.primary)
        layout.addWidget(self.becmg1)
        layout.addWidget(self.becmg2)
        layout.addWidget(self.becmg3)
        layout.addWidget(self.tempo1)
        layout.addWidget(self.tempo2)
        layout.addWidget(self.nextButton, 0, Qt.AlignRight|Qt.AlignBottom)
        self.setLayout(layout)

        self.setStyleSheet("QLineEdit {width: 50px;} QComboBox {width: 50px}")

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

        self.becmg1.interval.editingFinished.connect(lambda :self.verifyAmendInterval(self.becmg1.interval))
        self.becmg2.interval.editingFinished.connect(lambda :self.verifyAmendInterval(self.becmg2.interval))
        self.becmg3.interval.editingFinished.connect(lambda :self.verifyAmendInterval(self.becmg3.interval))

        self.tempo1.interval.editingFinished.connect(lambda :self.verifyAmendInterval(self.tempo1.interval, tempo=True))
        self.tempo2.interval.editingFinished.connect(lambda :self.verifyAmendInterval(self.tempo2.interval, tempo=True))

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
            duration = self._duration(period[2:4], period[4:6])
            return duration

    def _duration(self, start, end):
        duration = {}
        start = int(start)
        end = 0 if end == '24' else int(end)
        base_time = datetime.datetime(self.time.year, self.time.month, self.time.day)

        duration['start'] = base_time + datetime.timedelta(hours=start)

        if start < end:
            duration['end'] = base_time + datetime.timedelta(hours=end)
        else:
            duration['end'] = base_time + datetime.timedelta(days=1, hours=end)

        logger.debug(' '.join([
            'Duration',
            duration['start'].strftime('%Y-%m-%d %H:%M:%S'),
            duration['end'].strftime('%Y-%m-%d %H:%M:%S')
        ]))

        return duration

    def amendInterval(self, start, end):
        duration = self._duration(start, end)
        if duration['start'] < self.periods['start']:
            duration['start'] += datetime.timedelta(days=1)
            duration['end'] += datetime.timedelta(days=1)
        return duration

    def verifyTemperatureHour(self, line):
        if self.periods is not None:
            temp_hour = self._duration(line.text(), 0)['start']

            if temp_hour < self.periods['start']:
                temp_hour += datetime.timedelta(days=1) 

            valid = self.periods['start'] <= temp_hour <= self.periods['end']
            logger.debug('Verify temperature hour ' + str(valid))

            if not valid:
                line.clear()

    def verifyTemperature(self):
        tmax = self.primary.tmax.text()
        tmin = self.primary.tmin.text()
        if tmax and tmin:
            if int(tmax) <= int(tmin):
                self.primary.tmin.clear()

    def verifyAmendInterval(self, line, tempo=False):
        if tempo and self.tt == 'FC':
            interval = 4
        elif tempo and self.tt == 'FT':
            interval = 6
        else:
            interval = 2

        duration = self.amendInterval(line.text()[0:2], line.text()[2:4])
        if duration['start'] < self.periods['start'] or self.periods['end'] < duration['start']:
            line.clear()
            logger.info('Start interval time is not corret ' + duration['start'].strftime('%Y-%m-%d %H:%M:%S'))

        if duration['end'] < self.periods['start'] or self.periods['end'] < duration['end']:
            line.clear()
            logger.info('End interval time is not corret' + duration['end'].strftime('%Y-%m-%d %H:%M:%S'))

        if duration['end'] - duration['start'] > datetime.timedelta(hours=interval):
            line.clear()
            logger.info('More than ' + str(interval) + ' hours')

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

        # logger.debug('TAF required ' + ' '.join(map(str, completes)))

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



class TAFEditor(BaseEditor):

    def __init__(self, parent=None):
        super(TAFEditor, self).__init__(parent)
        self.setWindowTitle("编发报文")
        self.primary.date.setEnabled(False)

        self.timer = QTimer()
        self.timer.timeout.connect(self.updateDate)
        self.timer.start(1 * 1000)

    def previewMessage(self):
        message = {'head': self.head, 'rpt':self.rpt, 'full': '\n'.join([self.head, self.rpt])}
        self.previewSignal.emit(message)
        logger.debug('TAF Edit ' + message['full'])


class TaskTAFEditor(BaseEditor):

    def __init__(self, parent=None):
        super(TaskTAFEditor, self).__init__(parent)

        self.setWindowTitle("定时任务")
        self.setWindowIcon(QIcon(':/time.png'))

        self.primary.sortGroup.hide()

        self.primary.date.editingFinished.connect(self.taskTime)
        self.primary.date.editingFinished.connect(lambda :self.setNormalPeriod(is_task=True))
        self.primary.date.editingFinished.connect(self.changeWindowTitle)
        self.primary.date.editingFinished.connect(self.periodDuration)
        
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
        self.setWindowTitle("定时任务   " + self.time.strftime('%Y-%m-%d %H:%M'))

