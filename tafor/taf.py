# -*- coding: utf-8 -*-
import json
import datetime

from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

from widgets import TAFWidgetsPrimary, TAFWidgetsBecmg, TAFWidgetsTempo
from utils import AFTNMessage, TAFPeriod, Parser, REGEX_TAF
from models import Tafor, Schedule
from config import db, log


class TAFEditBase(QDialog):
    """docstring for TAF"""

    signal_preview = pyqtSignal(dict)

    def __init__(self, parent=None):
        super(TAFEditBase, self).__init__(parent)
        self.init_ui()
        self.bind_signal()
        self.update_date()
        self.update_message_type()

    def init_ui(self):
        window = QWidget(self)
        layout = QVBoxLayout(window)
        layout.setSizeConstraint(QLayout.SetFixedSize)
        self.primary = TAFWidgetsPrimary()
        self.becmg1, self.becmg2, self.becmg3 = TAFWidgetsBecmg('BECMG1'), TAFWidgetsBecmg('BECMG2'), TAFWidgetsBecmg('BECMG3')
        self.tempo1, self.tempo2 = TAFWidgetsTempo('TEMPO1'), TAFWidgetsTempo('TEMPO2')
        self.next_button = QPushButton()
        self.next_button.setEnabled(False)
        self.next_button.setText("下一步")
        layout.addWidget(self.primary)
        layout.addWidget(self.becmg1)
        layout.addWidget(self.becmg2)
        layout.addWidget(self.becmg3)
        layout.addWidget(self.tempo1)
        layout.addWidget(self.tempo2)
        layout.addWidget(self.next_button, 0, Qt.AlignRight|Qt.AlignBottom)
        self.setLayout(layout)

        self.setStyleSheet("QLineEdit {width: 50px;} QComboBox {width: 50px}")

        self.becmg1.hide()
        self.becmg2.hide()
        self.becmg3.hide()
        self.tempo1.hide()
        self.tempo2.hide()

    def bind_signal(self):

        self.primary.becmg1_checkbox.toggled.connect(self.add_becmg_and_tempo)
        self.primary.becmg2_checkbox.toggled.connect(self.add_becmg_and_tempo)
        self.primary.becmg3_checkbox.toggled.connect(self.add_becmg_and_tempo)
        self.primary.tempo1_checkbox.toggled.connect(self.add_becmg_and_tempo)
        self.primary.tempo2_checkbox.toggled.connect(self.add_becmg_and_tempo)

        self.primary.becmg1_checkbox.toggled.connect(self.becmg1._check_required)
        self.primary.becmg2_checkbox.toggled.connect(self.becmg2._check_required)
        self.primary.becmg3_checkbox.toggled.connect(self.becmg3._check_required)
        self.primary.tempo1_checkbox.toggled.connect(self.tempo1._check_required)
        self.primary.tempo2_checkbox.toggled.connect(self.tempo2._check_required)

        self.primary.fc.clicked.connect(self.update_message_type)
        self.primary.ft.clicked.connect(self.update_message_type)

        self.primary.normal.clicked.connect(self.update_message_type)
        self.primary.cor.clicked.connect(self.update_message_type)
        self.primary.amd.clicked.connect(self.update_message_type)
        self.primary.cnl.clicked.connect(self.update_message_type)

        self.primary.period.textChanged.connect(self.clear)

        self.primary.tmax_time.editingFinished.connect(lambda :self._check_temp_time_in_duration(self.primary.tmax_time))
        self.primary.tmin_time.editingFinished.connect(lambda :self._check_temp_time_in_duration(self.primary.tmin_time))

        self.primary.tmax.editingFinished.connect(self._check_temp_correct)
        self.primary.tmin.editingFinished.connect(self._check_temp_correct)

        self.becmg1.interval.editingFinished.connect(lambda :self._check_interval(self.becmg1.interval))
        self.becmg2.interval.editingFinished.connect(lambda :self._check_interval(self.becmg2.interval))
        self.becmg3.interval.editingFinished.connect(lambda :self._check_interval(self.becmg3.interval))

        self.tempo1.interval.editingFinished.connect(lambda :self._check_interval(self.tempo1.interval, tempo=True))
        self.tempo2.interval.editingFinished.connect(lambda :self._check_interval(self.tempo2.interval, tempo=True))

        self.primary.signal_required.connect(self._enbale_next_button)
        self.becmg1.signal_required.connect(self._enbale_next_button)
        self.becmg2.signal_required.connect(self._enbale_next_button)
        self.becmg3.signal_required.connect(self._enbale_next_button)
        self.tempo1.signal_required.connect(self._enbale_next_button)
        self.tempo2.signal_required.connect(self._enbale_next_button)

        # 下一步
        self.next_button.clicked.connect(self.assemble_message)
        self.next_button.clicked.connect(self.preview_message)

    def add_becmg_and_tempo(self):
        # BECMG
        if self.primary.becmg1_checkbox.isChecked():
            self.becmg1.setVisible(True)
        else:
            self.becmg1.setVisible(False)
            self.becmg2.setVisible(False)
            self.becmg3.setVisible(False)
            self.primary.becmg2_checkbox.setChecked(False)
            self.primary.becmg3_checkbox.setChecked(False)

        if self.primary.becmg2_checkbox.isChecked():
            self.becmg2.setVisible(True)
        else:
            self.becmg2.setVisible(False)
            self.becmg3.setVisible(False)
            self.primary.becmg3_checkbox.setChecked(False)

        if self.primary.becmg3_checkbox.isChecked():
            self.becmg3.setVisible(True)
        else:
            self.becmg3.setVisible(False)

        # TEMPO
        if self.primary.tempo1_checkbox.isChecked():
            self.tempo1.setVisible(True)
        else:
            self.tempo1.setVisible(False)
            self.tempo2.setVisible(False)
            self.primary.tempo2_checkbox.setChecked(False)

        if self.primary.tempo2_checkbox.isChecked():
            self.tempo2.setVisible(True)
        else:
            self.tempo2.setVisible(False)

    def update_message_type(self):
        if self.primary.fc.isChecked():
            self.tt = 'FC'

        if self.primary.ft.isChecked():
            self.tt = 'FT'

        if self.primary.date.text():
            if self.primary.normal.isChecked():
                self._set_period()

                self.primary.ccc.clear()
                self.primary.ccc.setEnabled(False)
                self.primary.aaa.clear()
                self.primary.aaa.setEnabled(False)
                self.primary.aaa_cnl.clear()
                self.primary.aaa_cnl.setEnabled(False)
            else:
                self._set_amd_period()

                if self.primary.cor.isChecked():
                    self.primary.ccc.setEnabled(True)
                    order = self._calc_revision_number('COR')
                    self.primary.ccc.setText(order)
                else:
                    self.primary.ccc.clear()
                    self.primary.ccc.setEnabled(False)

                if self.primary.amd.isChecked():
                    self.primary.aaa.setEnabled(True)
                    order = self._calc_revision_number('AMD')
                    self.primary.aaa.setText(order)
                else:
                    self.primary.aaa.clear()
                    self.primary.aaa.setEnabled(False)

                if self.primary.cnl.isChecked():
                    self.primary.aaa_cnl.setEnabled(True)
                    order = self._calc_revision_number('AMD')
                    self.primary.aaa_cnl.setText(order)
                else:
                    self.primary.aaa_cnl.clear()
                    self.primary.aaa_cnl.setEnabled(False)

            self._period_duration()

    def _set_period(self, sch=False):
        period = TAFPeriod(self.tt, self.time)

        self._period = period.current() if sch else period.warn()

        if self._period and period.is_existed(self._period):
            self.primary.period.setText('')
        else:
            self.primary.period.setText(self._period)

    def _set_amd_period(self):
        period = TAFPeriod(self.tt, self.time)
        self.amd_period = period.warn()
        self.primary.period.setText(self.amd_period)

    def _calc_revision_number(self, sign):
        time_limit = datetime.datetime.utcnow() - datetime.timedelta(hours=24)
        query = db.query(Tafor).filter(Tafor.rpt.contains(self.amd_period), Tafor.send_time > time_limit)
        if sign == 'COR':
            items = query.filter(Tafor.rpt.contains('COR')).all()
            log.debug(items)
            order = chr(ord('A') + len(items))
            return 'CC' + order
        elif sign == 'AMD':
            items = query.filter(Tafor.rpt.contains('AMD')).all()
            log.debug(items)
            order = chr(ord('A') + len(items))
            return 'AA' + order

    def _period_duration(self):
        period = self.primary.period.text()
        if len(period) == 6:
            self.period_duration = self._calc_duration(period[2:4], period[4:6])
            log.debug('period_duration ', self.period_duration)
            return self.period_duration

    def _check_temp_time_in_duration(self, line):
        temp_time = self._calc_duration(line.text(), 0)['start']

        if temp_time < self.period_duration['start']:
            temp_time += datetime.timedelta(days=1) 

        condition = self.period_duration['start'] <= temp_time <= self.period_duration['end']
        log.debug('Check temp', self.period_duration, temp_time)
        if not condition:
            line.clear()

    def _check_temp_correct(self):
        tmax = self.primary.tmax.text()
        tmin = self.primary.tmin.text()
        if tmax and tmin:
            if int(tmax) <= int(tmin):
                self.primary.tmin.clear()

    def _calc_duration(self, start, end):
        duration = dict()
        start = int(start)
        end = 0 if end == '24' else int(end)
        base_time = datetime.datetime(self.time.year, self.time.month, self.time.day)

        duration['start'] = base_time + datetime.timedelta(hours=start)

        if start < end:
            duration['end'] = base_time + datetime.timedelta(hours=end)
        else:
            duration['end'] = base_time + datetime.timedelta(days=1, hours=end)

        return duration

    def _calc_interval(self, start, end):
        duration = self._calc_duration(start, end)
        if duration['start'] < self.period_duration['start']:
            duration['start'] += datetime.timedelta(days=1)
            duration['end'] += datetime.timedelta(days=1)
        return duration

    def _check_interval(self, line, tempo=False):
        if tempo and self.tt == 'FC':
            interval = 4
        elif tempo and self.tt == 'FT':
            interval = 6
        else:
            interval = 2

        duration = self._calc_interval(line.text()[0:2], line.text()[2:4])
        if duration['start'] < self.period_duration['start'] or self.period_duration['end'] < duration['start']:
            line.clear()
            log.info('start interval time is not corret')

        if duration['end'] < self.period_duration['start'] or self.period_duration['end'] < duration['end']:
            line.clear()
            log.info('end interval time is not corret')

        if duration['end'] - duration['start'] > datetime.timedelta(hours=interval):
            line.clear()
            log.info('more than ', interval, ' hours')

        log.debug('interval ', duration)

    def assemble_message(self):
        primary_msg = self.primary.message()
        becmg1_msg = self.becmg1.message() if self.primary.becmg1_checkbox.isChecked() else ''
        becmg2_msg = self.becmg2.message() if self.primary.becmg2_checkbox.isChecked() else ''
        becmg3_msg = self.becmg3.message() if self.primary.becmg3_checkbox.isChecked() else ''
        tempo1_msg = self.tempo1.message() if self.primary.tempo1_checkbox.isChecked() else ''
        tempo2_msg = self.tempo2.message() if self.primary.tempo2_checkbox.isChecked() else ''
        msg_list = [primary_msg, becmg1_msg, becmg2_msg, becmg3_msg, tempo1_msg, tempo2_msg]
        self.rpt = '\n'.join(filter(None, msg_list)) + '='
        self.head = self.primary.head()

    def update_date(self):
        self.time = datetime.datetime.utcnow()
        self.primary.date.setText(self.time.strftime('%d%H%M'))

    def _enbale_next_button(self):
        # 允许下一步
        required_widgets = [self.primary.required]

        if self.primary.becmg1_checkbox.isChecked():
            required_widgets.append(self.becmg1.required)

        if self.primary.becmg2_checkbox.isChecked():
            required_widgets.append(self.becmg2.required)

        if self.primary.becmg3_checkbox.isChecked():
            required_widgets.append(self.becmg3.required)

        if self.primary.tempo1_checkbox.isChecked():
            required_widgets.append(self.tempo1.required)

        if self.primary.tempo2_checkbox.isChecked():
            required_widgets.append(self.tempo2.required)

        enbale = all(required_widgets)

        # log.debug('required', ' '.join(required_widgets))

        self.next_button.setEnabled(enbale)

    def clear(self):
        self.primary.clear()
        self.becmg1.clear()
        self.becmg2.clear()
        self.becmg3.clear()
        self.tempo1.clear()
        self.tempo2.clear()

    def closeEvent(self, event):
        self.clear()
        self.update_message_type()



class TAFEdit(TAFEditBase):

    def __init__(self, parent=None):
        super(TAFEdit, self).__init__(parent)

        self.setWindowTitle("编发报文")
        self.setWindowIcon(QIcon(':/fine.png'))

        self.primary.date.setEnabled(False)

    def preview_message(self):
        message = {'rpt': self.rpt, 'head': self.head}
        self.signal_preview.emit(message)
        log.debug('Emit', message)


class ScheduleTAFEdit(TAFEditBase):

    def __init__(self, parent=None):
        super(ScheduleTAFEdit, self).__init__(parent)

        self.setWindowTitle("定时任务")
        self.setWindowIcon(QIcon(':/schedule.png'))

        self.primary.group_cls.hide()

        self.primary.date.editingFinished.connect(self.schedule_time)
        self.primary.date.editingFinished.connect(lambda :self._set_period(sch=True))
        self.primary.date.editingFinished.connect(self.change_window_title)
        self.primary.date.editingFinished.connect(self._period_duration)
        
    def preview_message(self):
        message = {'head': self.head, 'rpt':self.rpt, 'sch_time': self.time}
        self.signal_preview.emit(message)
        log.debug('Emit', message)

    def schedule_time(self):
        date = self.primary.date.text()
        now = datetime.datetime.utcnow()

        day = int(date[0:2])
        hour = int(date[2:4])
        minute = int(date[4:])

        try:
            self.time = datetime.datetime(now.year, now.month, day, hour, minute)
            if self.time < now:
                self.time = datetime.datetime(now.year, now.month+1, day, hour, minute)
            return self.time
        except ValueError as e:
            self.time = datetime.datetime(now.year, now.month+2, day, hour, minute)
            return self.time

    def change_window_title(self):
        self.setWindowTitle("定时任务   " + self.time.strftime('%Y-%m-%d %H:%M'))



if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    ui = TAFEdit()
    ui.show()
    sys.exit(app.exec_())
    
