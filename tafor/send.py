import json
import datetime

from PyQt5 import QtCore, QtGui, QtWidgets

from ui import Ui_send
from models import Tafor, Schedule
from config import db, setting
from utils import AFTNMessage


class SendBase(QtWidgets.QDialog, Ui_send.Ui_Send):

    signal_send = QtCore.pyqtSignal()
    signal_close = QtCore.pyqtSignal()
    signal_back = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        """
        初始化主窗口
        """
        super(SendBase, self).__init__(parent)
        self.setupUi(self)

        self.button_box.button(QtWidgets.QDialogButtonBox.Ok).setText("Send")
        # self.button_box.addButton("TEST", QDialogButtonBox.ActionRole)
        self.rejected.connect(self.cancel_signal)
        self.signal_close.connect(self.clear)

        self.raw_group.hide()

    def receive_message(self, message):
        self.message = message
        rpt_with_head = '\n'.join([self.message['head'], self.message['rpt']])
        self.rpt.setText(rpt_with_head)

    def closeEvent(self, event):
        if event.spontaneous():
            self.cancel_signal()

    def cancel_signal(self):
        if self.button_box.button(QtWidgets.QDialogButtonBox.Ok).isEnabled():
            self.signal_back.emit()
            print('emit back')
        else:
            self.signal_close.emit()
            print('emit close')

    def clear(self):
        self.rpt.setText('')
        self.raw_group.hide()
        self.button_box.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(True)


class TAFSend(SendBase):

    def __init__(self, parent=None):
        super(TAFSend, self).__init__(parent)

        self.setWindowIcon(QtGui.QIcon(':/fine.png'))
        self.button_box.accepted.connect(self.send)
        self.button_box.accepted.connect(self.save)

    def save(self):
        item = Tafor(tt=self.message['head'][0:2], head=self.message['head'], rpt=self.message['rpt'], raw=json.dumps(self.aftn.raw()))
        db.add(item)
        db.commit()
        print('Save', item)
        self.signal_send.emit()

    def send(self):
        self.aftn = AFTNMessage(self.message)
        self.raw.setText('\n\n\n\n'.join(self.aftn.raw()))
        self.raw_group.show()
        self.button_box.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)


class ScheduleTAFSend(SendBase):

    def __init__(self, parent=None):
        super(ScheduleTAFSend, self).__init__(parent)
        self.table = Schedule

        self.setWindowTitle('定时任务')
        self.setWindowIcon(QtGui.QIcon(':/schedule.png'))

        self.button_box.accepted.connect(self.save)
        self.button_box.accepted.connect(self.accept)

        # 测试数据
        # self.schedule_time = datetime.datetime.utcnow() + datetime.timedelta(minutes=1)

    def save(self):
        item = Schedule(tt=self.message['head'][0:2], head=self.message['head'], rpt=self.message['rpt'], schedule_time=self.message['sch_time'])
        db.add(item)
        db.commit()
        print('Save Schedule', item.schedule_time)
        self.signal_send.emit()

    def auto_send(self):
        sch_queue = db.query(Schedule).filter_by(tafor_id=None).order_by(Schedule.schedule_time).all()
        now = datetime.datetime.utcnow()
        send_status = False

        for sch in sch_queue:
            #print(sch)

            if sch.schedule_time <= now:
                # print(sch)
                message = {'head': sch.head, 'rpt': sch.rpt}
                aftn = AFTNMessage(message)
                item = Tafor(tt=sch.tt, head=sch.head, rpt=sch.rpt, raw=json.dumps(aftn.raw()))
                db.add(item)
                db.flush()
                sch.tafor_id = item.id
                db.merge(sch)
                db.commit()

                send_status = True

        print('Queue to send', sch_queue)
        
        if send_status:
            # self.update_taf_table()
            print('Auto Send')


if __name__ == "__main__":
    import sys
    import datetime
    app = QtWidgets.QApplication(sys.argv)

    message = dict()
    message['rpt'] = 'TAF ZJHK 150726Z 150918 03003G10MPS 1600 BR OVC040 BECMG 1112 4000 BR='
    message['head'] = 'FCCI35 ZJHK 150726'

    # TAF Send
    ui = TAFSend()
    ui.receive_message(message)

    # Schedule TAF Send
    # message['sch_time'] = datetime.datetime.utcnow() + datetime.timedelta(minutes=1)

    # ui = ScheduleTAFSend()
    # ui.receive_message(message)

    ui.show()
    sys.exit(app.exec_())
    