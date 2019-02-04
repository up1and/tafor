import datetime

from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QCoreApplication, QTimer
from PyQt5.QtWidgets import QWidget, QMessageBox, QVBoxLayout, QLayout

from tafor.utils import CheckTaf
from tafor.utils.convert import parseTimeInterval, parseDateTime, isOverlap
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
        self.primary = TafPrimarySegment()
        self.becmgs = self.becmg1, self.becmg2, self.becmg3 = TafBecmgSegment('BECMG1'), TafBecmgSegment('BECMG2'), TafBecmgSegment('BECMG3')
        self.tempos = self.tempo1, self.tempo2, self.tempo3= TafTempoSegment('TEMPO1'), TafTempoSegment('TEMPO2'), TafTempoSegment('TEMPO3')
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

        self.becmg1.interval.editingFinished.connect(lambda :self.validateChangeGroupInterval(self.becmg1))
        self.becmg2.interval.editingFinished.connect(lambda :self.validateChangeGroupInterval(self.becmg2))
        self.becmg3.interval.editingFinished.connect(lambda :self.validateChangeGroupInterval(self.becmg3))

        self.tempo1.interval.editingFinished.connect(lambda :self.validateChangeGroupInterval(self.tempo1))
        self.tempo2.interval.editingFinished.connect(lambda :self.validateChangeGroupInterval(self.tempo2))
        self.tempo3.interval.editingFinished.connect(lambda :self.validateChangeGroupInterval(self.tempo3))

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

    def changeMessageType(self):
        if self.primary.fc.isChecked():
            self.tt = 'FC'
            self.primary.tempo3Checkbox.hide()
            self.primary.tempo3Checkbox.setChecked(False)

        if self.primary.ft.isChecked():
            self.tt = 'FT'
            self.primary.tempo3Checkbox.show()

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
                self.showNotificationMessage(QCoreApplication.translate('Editor', 'The time of temperature is not corret'))

    def validateTemperature(self):
        tmax = self.primary.tmax.text()
        tmin = self.primary.tmin.text()
        if tmax and tmin:
            tmax = -int(tmax[1:]) if 'M' in tmax else int(tmax)
            tmin = -int(tmin[1:]) if 'M' in tmin else int(tmin)
            if tmax <= tmin:
                self.primary.tmin.clear()

    def validateChangeGroupInterval(self, group):
        line = group.interval
        isTempo = group.id.startswith('TEMPO')
        if not self.periods:
            line.clear()
            return

        if isTempo and self.tt == 'FC':
            maxTime = 4
        elif isTempo and self.tt == 'FT':
            maxTime = 6
        else:
            maxTime = 2

        interval = start, end = self.groupInterval(line.text())
        if start < self.periods[0] or self.periods[1] < start:
            line.clear()
            self.showNotificationMessage(QCoreApplication.translate('Editor', 'Start time of change group is not corret'))
            return

        if end < self.periods[0] or self.periods[1] < end:
            line.clear()
            self.showNotificationMessage(QCoreApplication.translate('Editor', 'End time of change group is not corret'))
            return

        if end - start > datetime.timedelta(hours=maxTime):
            line.clear()
            self.showNotificationMessage(QCoreApplication.translate('Editor', 'Change group time more than {} hours').format(maxTime))
            return

        def isIntervalOverlay(interval, periods):
            for p in periods:
                if isOverlap(interval, p):
                    return True

        groups = self.tempos if isTempo else self.becmgs
        periods = [g.periods for g in groups if g.periods and group != g]
        if isIntervalOverlay(interval, periods):
            line.clear()
            self.showNotificationMessage(QCoreApplication.translate('Editor', 'Change group time is overlap'))
        else:
            group.periods = interval

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
            self.setDate()
            self.changeMessageType()
        else:
            QTimer.singleShot(0, self.showConfigError)


class TafEditor(BaseTafEditor):

    def __init__(self, parent=None, sender=None):
        super(TafEditor, self).__init__(parent, sender)
        self.setWindowTitle(QCoreApplication.translate('Editor', 'Encoding Terminal Aerodrome Forecast'))
        self.primary.date.setEnabled(False)

        self.timer = QTimer()
        self.timer.timeout.connect(self.setDate)
        self.timer.start(1 * 1000)

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
        self.periods = self.periodDuration()

    def afterSend(self):
        self.parent.taskBrowser.show()
        self.parent.taskBrowser.updateGui()

