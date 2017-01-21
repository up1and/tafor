# -*- coding: utf-8 -*-
import datetime

from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

from utils import AFTNMessage, TAFPeriod
from models import Session, Tafor, Schedule
from ui import Ui_taf_send
from widgets import TAFWidgetsPrimary, TAFWidgetsBecmg, TAFWidgetsTempo
from validator import Parser

 

class TAFEditBase(QDialog):
    """docstring for TAF"""

    signal_send = pyqtSignal(dict)

    def __init__(self, parent=None):
        super(TAFEditBase, self).__init__(parent)
        #self.setAttribute(Qt.WA_DeleteOnClose)

        self.init_ui()
        self.bind_signal()
        self.db = Session()

    def init_ui(self):
        window = QWidget(self)
        layout = QVBoxLayout(window)
        layout.setSizeConstraint(QLayout.SetFixedSize)
        self.primary = TAFWidgetsPrimary()
        self.becmg1, self.becmg2, self.becmg3 = TAFWidgetsBecmg('BECMG1'), TAFWidgetsBecmg('BECMG2'), TAFWidgetsBecmg('BECMG3')
        self.tempo1, self.tempo2 = TAFWidgetsTempo('TEMPO1'), TAFWidgetsTempo('TEMPO2')
        self.next_button = QPushButton()
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

        self.primary.fc.clicked.connect(self.dispatch)
        self.primary.ft.clicked.connect(self.dispatch)

        self.primary.cor.toggled.connect(self.set_ccc)
        self.primary.amd.toggled.connect(self.set_aaa)
        self.primary.cnl.toggled.connect(self.set_aaa_cnl)

        self.next_button.clicked.connect(self.update_date)
        self.next_button.clicked.connect(self.assemble_message)
        self.next_button.clicked.connect(self.send_message)

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

    def dispatch(self):
        if self.primary.fc.isChecked():
            self.tt = 'FC'

        if self.primary.ft.isChecked():
            self.tt = 'FT'

        if self.primary.date.text():
            if self.primary.normal.isChecked():
                self._set_current_period()
            else:
                self._set_amd_period()


    def _set_current_period(self):
        self.current_period = TAFPeriod(self.tt, self.time).current()
        self.primary.period.setText(self.current_period)

    def _set_amd_period(self):
        self.amd_period = TAFPeriod(self.tt, self.time).warn()
        self.primary.period.setText(self.amd_period)

    def set_ccc(self, checked):
        self.dispatch()
        self.primary.ccc.setEnabled(checked)
        if checked:
            order = self._calc_revision_number('COR')
            self.primary.ccc.setText(order)
        else:
            self.primary.ccc.clear()

    def set_aaa(self, checked):
        self.dispatch()
        self.primary.aaa.setEnabled(checked)
        if checked:
            order = self._calc_revision_number('AMD')
            self.primary.aaa.setText(order)
        else:
            self.primary.aaa.clear()

    def set_aaa_cnl(self, checked):
        self.dispatch()
        self.primary.aaa_cnl.setEnabled(checked)
        if checked:
            order = self._calc_revision_number('AMD')
            self.primary.aaa_cnl.setText(order)
        else:
            self.primary.aaa_cnl.clear()

    def _calc_revision_number(self, sign):
        time_limit = datetime.datetime.utcnow() - datetime.timedelta(hours=24)
        query = self.db.query(Tafor).filter(Tafor.rpt.contains(self.amd_period), Tafor.send_time > time_limit)
        if sign == 'COR':
            items = query.filter(Tafor.rpt.contains('COR')).all()
            print(items)
            order = chr(ord('A') + len(items))
            return 'CC' + order
        elif sign == 'AMD':
            items = query.filter(Tafor.rpt.contains('AMD')).all()
            print(items)
            order = chr(ord('A') + len(items))
            return 'AA' + order


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


class TAFEdit(TAFEditBase):

    def __init__(self, parent=None):
        super(TAFEdit, self).__init__(parent)

        self.setWindowTitle("编发报文")
        self.setWindowIcon(QIcon(':/fine.png'))

        self.primary.date.setEnabled(False)
        self.update_date()

    def send_message(self):
        send = TAFSend(self)
        send.show()
        message = {'rpt': self.rpt, 'head': self.head}
        self.signal_send.connect(send.receive_from_edit)
        self.signal_send.emit(message)


class ScheduleTAFEdit(TAFEditBase):

    def __init__(self, parent=None):
        super(ScheduleTAFEdit, self).__init__(parent)

        self.setWindowTitle("定时任务")
        self.setWindowIcon(QIcon(':/schedule.png'))

        self.primary.date.editingFinished.connect(self.schedule_time)
        self.primary.date.editingFinished.connect(self.set_period)
        self.primary.date.editingFinished.connect(self.change_window_title)

        self.next_button.clicked.disconnect(self.update_date)
        
    def send_message(self):
        send = ScheduleTAFSend(self)
        send.show()
        message = {'head': self.head, 'rpt':self.rpt, 'sch_time': self.time}
        self.signal_send.connect(send.receive_from_edit)
        self.signal_send.emit(message)

    def schedule_time(self):
        date = self.primary.date.text()
        now = datetime.datetime.utcnow()

        day = int(date[0:2])
        hour = int(date[2:4])
        minute = int(date[4:])

        def _sch_time(time):
            year = time.year
            month = time.month
            return datetime.datetime(year, month, day, hour, minute)

        tmp_time = now
        while _sch_time(tmp_time) < now:
            tmp_time = tmp_time + datetime.timedelta(days=1)

        sch_time = _sch_time(tmp_time)
        self.time = sch_time
        return sch_time

    def change_window_title(self):
        self.setWindowTitle("定时任务   " + self.time.strftime('%Y-%m-%d %H:%M'))


class TAFSendBase(QDialog, Ui_taf_send.Ui_TAFSend):

    def __init__(self, parent=None):
        """
        初始化主窗口
        """
        super(TAFSendBase, self).__init__(parent)
        self.setupUi(self)
        self.setAttribute(Qt.WA_DeleteOnClose)

        self.button_box.button(QDialogButtonBox.Ok).setText("Send")
        # self.button_box.addButton("TEST", QDialogButtonBox.ActionRole)

        self.raw_group.hide()

        self.db = Session()
        self.setting = QSettings('Up1and', 'Tafor')

        # 测试数据
        # message = dict()
        # message['rpt'] = 'TAF ZJHK 150726Z 150918 03003G10MPS 1600 BR OVC040 BECMG 1112 4000 BR='
        # message['tt'] = 'FC'
        # self.aftn = AFTNMessage(message)
        # self.rpt.setText(self.aftn.rpt_with_head())

    def receive_from_edit(self, message):
        self.message = message
        rpt_with_head = '\n'.join([self.message['head'], self.message['rpt']])
        self.rpt.setText(rpt_with_head)
        print(self.message)



class TAFSend(TAFSendBase):

    def __init__(self, parent=None):
        super(TAFSend, self).__init__(parent)

        self.setWindowIcon(QIcon(':/fine.png'))
        self.button_box.accepted.connect(self.send)
        self.button_box.accepted.connect(self.save)

    def save(self):
        item = Tafor(tt=self.message['head'][0:2], head=self.message['head'], rpt=self.message['rpt'])
        self.db.add(item)
        self.db.commit()
        print(item, 'save')

    def send(self):
        self.aftn = AFTNMessage(self.message)
        self.raw.setText('\n\n\n\n'.join(self.aftn.raw()))
        self.raw_group.show()
        self.button_box.button(QDialogButtonBox.Ok).setEnabled(False)


class ScheduleTAFSend(TAFSendBase):

    def __init__(self, parent=None):
        super(ScheduleTAFSend, self).__init__(parent)
        self.table = Schedule

        self.setWindowTitle('定时任务')
        self.setWindowIcon(QIcon(':/schedule.png'))

        # self.button_box.accepted.connect(self.save)
        self.button_box.accepted.connect(self.accept)

        # 测试数据
        # self.schedule_time = datetime.datetime.utcnow() + datetime.timedelta(minutes=1)

    def save(self):
        item = Schedule(tt=self.message['head'][0:2], head=self.message['head'], rpt=self.message['rpt'], schedule_time=self.message['sch_time'])
        self.db.add(item)
        self.db.commit()
        print(item.schedule_time)

    def auto_send(self):
        db = Session()
        sch_queue = db.query(Schedule).filter_by(tafor_id=None).order_by(Schedule.schedule_time).all()
        now = datetime.datetime.utcnow()
        send_status = False

        for sch in sch_queue:
            #print(sch)

            if sch.schedule_time <= now:
                # print(sch)
                item = Tafor(tt=sch.tt, head=sch.head, rpt=sch.rpt)
                self.db.add(item)
                self.db.flush()
                sch.tafor_id = item.id
                self.db.merge(sch)
                self.db.commit()

                send_status = True

        print(sch_queue)
        
        if send_status:
            self.update_taf_table()
            print('auto_send')
        else:
            print('nothing to do')





if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    ui = TAFEdit()
    ui.show()
    sys.exit(app.exec_())
    
