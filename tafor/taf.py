# -*- coding: utf-8 -*-
import datetime

from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

from utils import TAF
from validator import Parser
from models import Session, Tafor, Schedule
from ui import Ui_taf_edit, Ui_taf_send
from widgets import TAFWidgetsPrimary


class TAFEditBase(QDialog, Ui_taf_edit.Ui_TAFEdit):
    """
    主窗口
    """

    message = pyqtSignal(dict)

    def __init__(self, parent=None):
        """
        初始化主窗口
        """
        super(TAFEditBase, self).__init__(parent)
        self.setupUi(self)
        self.setAttribute(Qt.WA_DeleteOnClose)
        # self.validate()
        self.setStyleSheet("QLineEdit {width: 50px;} QGroupBox {border:none;}")

        self.primary = TAFWidgetsPrimary()
        self.main.addWidget(self.primary)
        
        # self.becmg1_frame.hide()
        # self.becmg2_frame.hide()
        # self.becmg3_frame.hide()
        # self.tempo1_frame.hide()
        # self.tempo2_frame.hide()

        # self.becmg1_checkbox.toggled.connect(self.becmg1_frame.setVisible)
        # self.becmg2_checkbox.toggled.connect(self.becmg2_frame.setVisible)
        # self.becmg3_checkbox.toggled.connect(self.becmg3_frame.setVisible)

        # self.tempo1_checkbox.toggled.connect(self.tempo1_frame.setVisible)
        # self.tempo2_checkbox.toggled.connect(self.tempo2_frame.setVisible)

        # self.taf_cavok.clicked.connect(self.set_cavok)

        # self.taf_next.setEnabled(False)
        # self.taf_next.clicked.connect(self.assemble)
        # self.taf_period.setEnabled(False)

        self.time = datetime.datetime.utcnow()

        # self.one_second_timer = QTimer()
        # self.one_second_timer.timeout.connect(self.enbale_next_button)
        # self.one_second_timer.start(1 * 1000)

        # self.test()

    def set_taf_period(self):
        if self.taf_date.text() and (self.type_fc.isChecked() or self.type_ft.isChecked()):
            if self.type_fc.isChecked():
                self.tt = 'FC'
            elif self.type_ft.isChecked():
                self.tt = 'FT'
            taf = TAF(self.tt, self.time)
            self.taf_period.setText(self.time.strftime('%d') + taf.get_period())

    def set_cavok(self, checked):
        if checked:
            self.taf_vis.clear()
            self.taf_vis.setEnabled(False)
            self.taf_cloud1.clear()
            self.taf_cloud1.setEnabled(False)
            self.taf_cloud2.clear()
            self.taf_cloud2.setEnabled(False)
            self.taf_cloud3.clear()
            self.taf_cloud3.setEnabled(False)
            self.taf_cb.clear()
            self.taf_cb.setEnabled(False)
        else:
            self.taf_vis.setEnabled(True)
            self.taf_cloud1.setEnabled(True)
            self.taf_cloud2.setEnabled(True)
            self.taf_cloud3.setEnabled(True)
            self.taf_cb.setEnabled(True)


    def validate(self):
        regex = Parser.regex_taf['edit']
        # print(regex)

        valid_date = QRegExpValidator(QRegExp(regex['time']))
        self.taf_date.setValidator(valid_date)

        valid_wind = QRegExpValidator(QRegExp(regex['wind']))
        self.taf_wind.setValidator(valid_wind)

        valid_gust = QRegExpValidator(QRegExp(regex['gust']))
        self.taf_gust.setValidator(valid_gust)

        valid_vis = QRegExpValidator(QRegExp(regex['vis']))
        self.taf_vis.setValidator(valid_vis)

        valid_cloud = QRegExpValidator(QRegExp(regex['cloud']))
        self.taf_cloud1.setValidator(valid_cloud)
        self.taf_cloud2.setValidator(valid_cloud)
        self.taf_cloud3.setValidator(valid_cloud)
        self.taf_cb.setValidator(valid_cloud)

        valid_temp = QRegExpValidator(QRegExp(regex['temp']))
        self.taf_temp_max.setValidator(valid_temp)
        self.taf_temp_min.setValidator(valid_temp)

        wx1 = ['', 'BR', 'FG', 'SA', 'DU', 'HZ', 'FU', 'VA', 'SQ', 'PO', 'FC', 'TS', 'FZFG', 'BLSN', 'BLSA', 'BLDU', 'DRSN', 'DRSA', 'DRDU', 'MIFG', 'BCFG', 'PRFG', 'NSW']
        self.taf_weather1_combobox.addItems(wx1)

        wx2 = ['', 'DZ', 'RA', 'SN', 'SG', 'PL', 'DS', 'SS', 'TSRA', 'TSSN', 'TSPL', 'TSGR', 'TSGS', 'SHRA', 'SHSN', 'SHGR', 'SHGS', 'FZRA', 'FZDZ']
        self.taf_weather2_combobox.addItems(wx2)

    def enbale_next_button(self):
        if self.taf_date.text() and self.taf_period.text() and self.taf_wind.text():
            if self.taf_cavok.isChecked():
                self.taf_next.setEnabled(True)
            elif self.taf_vis.text():
                if self.taf_cloud1.text() or self.taf_cloud2.text() or self.taf_cloud3.text() or self.taf_cb.text() or self.taf_nsc.isChecked():
                    self.taf_next.setEnabled(True)

    def assemble(self):
        taf = 'TAF'
        icao = 'ZJHK'
        timez = self.taf_date.text() + 'Z'
        period = self.taf_period.text()
        wind = ''.join([self.taf_wind.text(), 'G', self.taf_gust.text(), 'MPS']) if self.taf_gust.text() else ''.join([self.taf_wind.text(), 'MPS'])
        vis = self.taf_vis.text()
        wx1 = self.taf_weather1_combobox.currentText()
        wx2 = self.taf_weather2_combobox.currentText()
        cloud1 = self.taf_cloud1.text()
        cloud2 = self.taf_cloud2.text()
        cloud3 = self.taf_cloud3.text()
        cb = self.taf_cb.text()
        tmax = ''.join(['TX', self.taf_temp_max.text()[0:-2], '/', self.taf_temp_max.text()[-2:], 'Z'])
        tmin = ''.join(['TN', self.taf_temp_min.text()[0:-2], '/', self.taf_temp_min.text()[-2:], 'Z'])

        prefix_group = [taf, icao, timez, period, wind]
        temp_group = [tmax, tmin]
        if self.taf_cavok.isChecked():
            rpt_group = prefix_group + ['CAVOK'] + temp_group
            self.rpt = ' '.join(rpt_group)
        else:
            rpt_group = prefix_group + [vis, wx1, wx2, cloud1, cloud2, cloud3, cb] + temp_group
            self.rpt = ' '.join(rpt_group)
        self.rpt = ' '.join(self.rpt.split()) + '='
        
        


class TAFEdit(TAFEditBase):

    def __init__(self, parent=None):
        super(TAFEdit, self).__init__(parent)
        # self.type_fc.clicked.connect(self.set_taf_period)
        # self.type_ft.clicked.connect(self.set_taf_period)

        # self.taf_date.setText(self.time.strftime('%d%H%M'))
        # self.taf_date.setEnabled(False)

    def assemble(self):
        super(TAFEdit, self).assemble()
        send = TAFSend(self)
        send.show()
        send_data = {'tt': self.tt, 'rpt':self.rpt}
        self.message.connect(send.process)
        self.message.emit(send_data)


class ScheduleTAFEdit(TAFEditBase):

    def __init__(self, parent=None):
        super(ScheduleTAFEdit, self).__init__(parent)
        self.setWindowTitle("定时任务")

        self.type_fc.clicked.connect(self.set_taf_period)
        self.type_ft.clicked.connect(self.set_taf_period)
        self.taf_date.editingFinished.connect(self.schedule_time)
        self.taf_date.editingFinished.connect(self.set_taf_period)
        
    def assemble(self):
        super(ScheduleTAFEdit, self).assemble()
        send = ScheduleTAFSend(self)
        send.show()
        send_data = {'tt': self.tt, 'rpt':self.rpt, 'sch_time': self.time,}
        self.message.connect(send.process)
        self.message.emit(send_data)

    def schedule_time(self):
        date = self.taf_date.text()
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
    ui = TAFEdit()
    ui.show()
    sys.exit(app.exec_())
    
