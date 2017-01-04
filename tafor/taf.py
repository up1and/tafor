# -*- coding: utf-8 -*-
import datetime

from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

from utils import current_taf_period
from validator import Parser
from models import Session, Tafor, Schedule
from ui import Ui_taf_send
from widgets import TAFWidgetsPrimary, TAFWidgetsBecmg, TAFWidgetsTempo

 

class TAFEditBase(QDialog):
    """docstring for TAF"""

    signal_send = pyqtSignal(dict)

    def __init__(self, parent=None):
        super(TAFEditBase, self).__init__(parent)
        #self.setAttribute(Qt.WA_DeleteOnClose)

        self.init_ui()
        self.bind_signal()

    def init_ui(self):
        window = QWidget(self)
        layout = QVBoxLayout(window)
        layout.setSizeConstraint(QLayout.SetFixedSize)
        self.widget_primary = TAFWidgetsPrimary()
        self.widget_becmg1, self.widget_becmg2, self.widget_becmg3 = TAFWidgetsBecmg('BECMG1'), TAFWidgetsBecmg('BECMG2'), TAFWidgetsBecmg('BECMG3')
        self.widget_tempo1, self.widget_tempo2 = TAFWidgetsTempo('TEMPO1'), TAFWidgetsTempo('TEMPO2')
        self.next_button = QPushButton()
        self.next_button.setText("下一步")
        layout.addWidget(self.widget_primary)
        layout.addWidget(self.widget_becmg1)
        layout.addWidget(self.widget_becmg2)
        layout.addWidget(self.widget_becmg3)
        layout.addWidget(self.widget_tempo1)
        layout.addWidget(self.widget_tempo2)
        layout.addWidget(self.next_button, 0, Qt.AlignRight|Qt.AlignBottom)
        self.setLayout(layout)

        self.setStyleSheet("QLineEdit {width: 50px;} QComboBox {width: 50px}")

        self.widget_becmg1.hide()
        self.widget_becmg2.hide()
        self.widget_becmg3.hide()
        self.widget_tempo1.hide()
        self.widget_tempo2.hide()

        self.primary = self.widget_primary.ui
        self.becmg1 = self.widget_becmg1.ui
        self.becmg2 = self.widget_becmg2.ui
        self.becmg3 = self.widget_becmg3.ui
        self.tempo1 = self.widget_tempo1.ui
        self.tempo2 = self.widget_tempo2.ui

    def bind_signal(self):

        self.primary.becmg1_checkbox.toggled.connect(self.add_becmg_and_tempo)
        self.primary.becmg2_checkbox.toggled.connect(self.add_becmg_and_tempo)
        self.primary.becmg3_checkbox.toggled.connect(self.add_becmg_and_tempo)
        self.primary.tempo1_checkbox.toggled.connect(self.add_becmg_and_tempo)
        self.primary.tempo2_checkbox.toggled.connect(self.add_becmg_and_tempo)

        self.next_button.clicked.connect(self.assemble_message)

    def add_becmg_and_tempo(self):
        # BECMG
        if self.primary.becmg1_checkbox.isChecked():
            self.widget_becmg1.setVisible(True)
        else:
            self.widget_becmg1.setVisible(False)
            self.widget_becmg2.setVisible(False)
            self.widget_becmg3.setVisible(False)
            self.primary.becmg2_checkbox.setChecked(False)
            self.primary.becmg3_checkbox.setChecked(False)

        if self.primary.becmg2_checkbox.isChecked():
            self.widget_becmg2.setVisible(True)
        else:
            self.widget_becmg2.setVisible(False)
            self.widget_becmg3.setVisible(False)
            self.primary.becmg3_checkbox.setChecked(False)

        if self.primary.becmg3_checkbox.isChecked():
            self.widget_becmg3.setVisible(True)
        else:
            self.widget_becmg3.setVisible(False)

        # TEMPO
        if self.primary.tempo1_checkbox.isChecked():
            self.widget_tempo1.setVisible(True)
        else:
            self.widget_tempo1.setVisible(False)
            self.widget_tempo2.setVisible(False)
            self.primary.tempo2_checkbox.setChecked(False)

        if self.primary.tempo2_checkbox.isChecked():
            self.widget_tempo2.setVisible(True)
        else:
            self.widget_tempo2.setVisible(False)

    def set_taf_period(self):
        if self.primary.date.text() and (self.primary.fc.isChecked() or self.primary.ft.isChecked()):
            if self.primary.fc.isChecked():
                self.tt = 'FC'
            elif self.primary.ft.isChecked():
                self.tt = 'FT'
            taf_period = current_taf_period(self.tt, self.time)
            self.primary.period.setText(self.time.strftime('%d') + taf_period)


    def assemble_message(self):
        primary_msg = self.widget_primary.message()
        becmg1_msg = self.widget_becmg1.message() if self.primary.becmg1_checkbox.isChecked() else ''
        becmg2_msg = self.widget_becmg2.message() if self.primary.becmg2_checkbox.isChecked() else ''
        becmg3_msg = self.widget_becmg3.message() if self.primary.becmg3_checkbox.isChecked() else ''
        tempo1_msg = self.widget_tempo1.message() if self.primary.tempo1_checkbox.isChecked() else ''
        tempo2_msg = self.widget_tempo2.message() if self.primary.tempo2_checkbox.isChecked() else ''
        self.rpt = '\n'.join([primary_msg, becmg1_msg, becmg2_msg, becmg3_msg, tempo1_msg, tempo2_msg])
        self.rpt = ' '.join(self.rpt.split())
        print(self.rpt)
        self.preview()



class TAFEdit(TAFEditBase):

    def __init__(self, parent=None):
        super(TAFEdit, self).__init__(parent)

        self.setWindowTitle("编发报文")
        self.setWindowIcon(QIcon(':/fine.png'))

        self.primary.fc.clicked.connect(self.set_taf_period)
        self.primary.ft.clicked.connect(self.set_taf_period)

        self.time = datetime.datetime.utcnow()
        self.primary.date.setText(self.time.strftime('%d%H%M'))
        self.primary.date.setEnabled(False)

    def preview(self):
        send = TAFSend(self)
        send.show()
        send_data = {'tt': self.tt, 'rpt':self.rpt}
        self.signal_send.connect(send.process)
        self.signal_send.emit(send_data)


class ScheduleTAFEdit(TAFEditBase):

    def __init__(self, parent=None):
        super(ScheduleTAFEdit, self).__init__(parent)

        self.setWindowTitle("定时任务")
        self.setWindowIcon(QIcon(':/schedule.png'))

        self.primary.fc.clicked.connect(self.set_taf_period)
        self.primary.ft.clicked.connect(self.set_taf_period)
        self.primary.date.editingFinished.connect(self.schedule_time)
        self.primary.date.editingFinished.connect(self.set_taf_period)
        self.primary.date.editingFinished.connect(self.change_window_title)
        
    def preview(self):
        send = ScheduleTAFSend(self)
        send.show()
        send_data = {'tt': self.tt, 'rpt':self.rpt, 'sch_time': self.time,}
        self.signal_send.connect(send.process)
        self.signal_send.emit(send_data)

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

        # self.message = 'TAF ZJHK 150726Z 150918 03003G10MPS 1600 BR OVC040 BECMG 1112 4000 BR='
        # self.message_container.setText(self.message)
        # self.tt = 'FC'

        self.db = Session()

    def process(self, message):
        self.message = message
        self.message_container.setText(self.message['rpt'])
        print(self.message)



class TAFSend(TAFSendBase):

    def __init__(self, parent=None):
        super(TAFSend, self).__init__(parent)

        self.setWindowIcon(QIcon(':/fine.png'))

    def accept(self):
        item = Tafor(tt=self.message['tt'], rpt=self.message['rpt'])
        self.db.add(item)
        self.db.commit()
        print(item.send_time)
        # self.close()


class ScheduleTAFSend(TAFSendBase):

    def __init__(self, parent=None):
        super(ScheduleTAFSend, self).__init__(parent)
        self.table = Schedule

        self.setWindowTitle("定时任务")
        self.setWindowIcon(QIcon(':/schedule.png'))

        # 测试数据
        self.schedule_time = datetime.datetime.utcnow() + datetime.timedelta(minutes=1)

    def accept(self):
        item = Schedule(tt=self.message['tt'], rpt=self.message['rpt'], schedule_time=self.message['sch_time'])
        self.db.add(item)
        self.db.commit()
        print(item.schedule_time)
        # self.close()





if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    ui = ScheduleTAFEdit()
    ui.show()
    sys.exit(app.exec_())
    
