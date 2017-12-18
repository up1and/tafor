# -*- coding: utf-8 -*-
import json
import datetime

from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

from tafor import logger
from tafor.utils import CheckTAF, Grammar
from tafor.models import db, Tafor, Task
from tafor.widgets.edit import TAFWidgetPrimary, TAFWidgetBecmg, TAFWidgetTempo


class TAFEditBase(QDialog):
    """docstring for TAF"""

    signal_preview = pyqtSignal(dict)

    def __init__(self, parent=None):
        super(TAFEditBase, self).__init__(parent)
        self.parent = parent

        self.init_ui()
        self.bind_signal()
        self.update_date()
        self.update_message_type()

    def init_ui(self):
        window = QWidget(self)
        layout = QVBoxLayout(window)
        layout.setSizeConstraint(QLayout.SetFixedSize)
        self.primary = TAFWidgetPrimary()
        self.becmg1, self.becmg2, self.becmg3 = TAFWidgetBecmg('BECMG1'), TAFWidgetBecmg('BECMG2'), TAFWidgetBecmg('BECMG3')
        self.tempo1, self.tempo2 = TAFWidgetTempo('TEMPO1'), TAFWidgetTempo('TEMPO2')
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

        self.primary.becmg1_checkbox.toggled.connect(self.becmg1.check_required)
        self.primary.becmg2_checkbox.toggled.connect(self.becmg2.check_required)
        self.primary.becmg3_checkbox.toggled.connect(self.becmg3.check_required)
        self.primary.tempo1_checkbox.toggled.connect(self.tempo1.check_required)
        self.primary.tempo2_checkbox.toggled.connect(self.tempo2.check_required)

        self.primary.fc.clicked.connect(self.update_message_type)
        self.primary.ft.clicked.connect(self.update_message_type)

        self.primary.normal.clicked.connect(self.update_message_type)
        self.primary.cor.clicked.connect(self.update_message_type)
        self.primary.amd.clicked.connect(self.update_message_type)
        self.primary.cnl.clicked.connect(self.update_message_type)

        self.primary.period.textChanged.connect(self.clear)

        self.primary.tmax_time.editingFinished.connect(lambda :self.verify_temperature_hour(self.primary.tmax_time))
        self.primary.tmin_time.editingFinished.connect(lambda :self.verify_temperature_hour(self.primary.tmin_time))

        self.primary.tmax.editingFinished.connect(self.verify_temperature)
        self.primary.tmin.editingFinished.connect(self.verify_temperature)

        self.becmg1.interval.editingFinished.connect(lambda :self.verify_amend_interval(self.becmg1.interval))
        self.becmg2.interval.editingFinished.connect(lambda :self.verify_amend_interval(self.becmg2.interval))
        self.becmg3.interval.editingFinished.connect(lambda :self.verify_amend_interval(self.becmg3.interval))

        self.tempo1.interval.editingFinished.connect(lambda :self.verify_amend_interval(self.tempo1.interval, tempo=True))
        self.tempo2.interval.editingFinished.connect(lambda :self.verify_amend_interval(self.tempo2.interval, tempo=True))

        self.primary.signal_required.connect(self.enbale_next_button)
        self.becmg1.signal_required.connect(self.enbale_next_button)
        self.becmg2.signal_required.connect(self.enbale_next_button)
        self.becmg3.signal_required.connect(self.enbale_next_button)
        self.tempo1.signal_required.connect(self.enbale_next_button)
        self.tempo2.signal_required.connect(self.enbale_next_button)

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
                self.set_normal_period()

                self.primary.ccc.clear()
                self.primary.ccc.setEnabled(False)
                self.primary.aaa.clear()
                self.primary.aaa.setEnabled(False)
                self.primary.aaa_cnl.clear()
                self.primary.aaa_cnl.setEnabled(False)
            else:
                self.set_amend_period()

                if self.primary.cor.isChecked():
                    self.primary.ccc.setEnabled(True)
                    order = self.get_amend_number('COR')
                    self.primary.ccc.setText(order)
                else:
                    self.primary.ccc.clear()
                    self.primary.ccc.setEnabled(False)

                if self.primary.amd.isChecked():
                    self.primary.aaa.setEnabled(True)
                    order = self.get_amend_number('AMD')
                    self.primary.aaa.setText(order)
                else:
                    self.primary.aaa.clear()
                    self.primary.aaa.setEnabled(False)

                if self.primary.cnl.isChecked():
                    self.primary.aaa_cnl.setEnabled(True)
                    order = self.get_amend_number('AMD')
                    self.primary.aaa_cnl.setText(order)
                else:
                    self.primary.aaa_cnl.clear()
                    self.primary.aaa_cnl.setEnabled(False)

            self.period_duration = self.get_period_duration()

    def set_normal_period(self, is_task=False):
        taf = CheckTAF(self.tt, self.time)

        current_period = taf.current_period() if is_task else taf.warn_period()

        if current_period and taf.existed_in_local(current_period) or not self.primary.date.hasAcceptableInput():
            self.primary.period.clear()
        else:
            self.primary.period.setText(current_period)

    def set_amend_period(self):
        taf = CheckTAF(self.tt, self.time)
        self.amd_period = taf.warn_period()
        self.primary.period.setText(self.amd_period)

    def get_amend_number(self, sign):
        expired = datetime.datetime.utcnow() - datetime.timedelta(hours=24)
        query = db.query(Tafor).filter(Tafor.rpt.contains(self.amd_period), Tafor.sent > expired)
        if sign == 'COR':
            items = query.filter(Tafor.rpt.contains('COR')).all()
            order = chr(ord('A') + len(items))
            return 'CC' + order
        elif sign == 'AMD':
            items = query.filter(Tafor.rpt.contains('AMD')).all()
            order = chr(ord('A') + len(items))
            return 'AA' + order

    def get_period_duration(self):
        period = self.primary.period.text()
        if len(period) == 6:
            duration = self._get_duration(period[2:4], period[4:6])
            return duration

    def _get_duration(self, start, end):
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

    def _get_amend_interval(self, start, end):
        duration = self._get_duration(start, end)
        if duration['start'] < self.period_duration['start']:
            duration['start'] += datetime.timedelta(days=1)
            duration['end'] += datetime.timedelta(days=1)
        return duration

    def verify_temperature_hour(self, line):
        if self.period_duration is not None:
            temp_hour = self._get_duration(line.text(), 0)['start']

            if temp_hour < self.period_duration['start']:
                temp_hour += datetime.timedelta(days=1) 

            valid = self.period_duration['start'] <= temp_hour <= self.period_duration['end']
            logger.debug('Verify temperature hour ' + str(valid))

            if not valid:
                line.clear()

    def verify_temperature(self):
        tmax = self.primary.tmax.text()
        tmin = self.primary.tmin.text()
        if tmax and tmin:
            if int(tmax) <= int(tmin):
                self.primary.tmin.clear()

    def verify_amend_interval(self, line, tempo=False):
        if tempo and self.tt == 'FC':
            interval = 4
        elif tempo and self.tt == 'FT':
            interval = 6
        else:
            interval = 2

        duration = self._get_amend_interval(line.text()[0:2], line.text()[2:4])
        if duration['start'] < self.period_duration['start'] or self.period_duration['end'] < duration['start']:
            line.clear()
            logger.info('Start interval time is not corret ' + duration['start'].strftime('%Y-%m-%d %H:%M:%S'))

        if duration['end'] < self.period_duration['start'] or self.period_duration['end'] < duration['end']:
            line.clear()
            logger.info('End interval time is not corret' + duration['end'].strftime('%Y-%m-%d %H:%M:%S'))

        if duration['end'] - duration['start'] > datetime.timedelta(hours=interval):
            line.clear()
            logger.info('More than ' + str(interval) + ' hours')

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

    def enbale_next_button(self):
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

        # logger.debug('TAF required ' + ' '.join(map(str, required_widgets)))

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
        self.primary.date.setEnabled(False)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_date)
        self.timer.start(1 * 1000)

    def preview_message(self):
        message = {'head': self.head, 'rpt':self.rpt, 'full': '\n'.join([self.head, self.rpt])}
        self.signal_preview.emit(message)
        logger.debug('TAF Edit ' + message['full'])


class TaskTAFEdit(TAFEditBase):

    def __init__(self, parent=None):
        super(TaskTAFEdit, self).__init__(parent)

        self.setWindowTitle("定时任务")
        self.setWindowIcon(QIcon(':/time.png'))

        self.primary.group_cls.hide()

        self.primary.date.editingFinished.connect(self.task_time)
        self.primary.date.editingFinished.connect(lambda :self.set_normal_period(is_task=True))
        self.primary.date.editingFinished.connect(self.change_window_title)
        self.primary.date.editingFinished.connect(self.get_period_duration)
        
    def preview_message(self):
        message = {'head': self.head, 'rpt':self.rpt, 'full': '\n'.join([self.head, self.rpt]), 'plan': self.time}
        self.signal_preview.emit(message)
        log.debug('Emit', message)

    def task_time(self):
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

    def change_window_title(self):
        self.setWindowTitle("定时任务   " + self.time.strftime('%Y-%m-%d %H:%M'))

