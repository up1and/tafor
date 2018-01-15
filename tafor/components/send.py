import json
import datetime

from PyQt5 import QtCore, QtGui, QtWidgets

from tafor.components.ui import Ui_send
from tafor.models import db, Tafor, Task, Trend
from tafor import conf, logger


def chunks(lists, n):
    """Yield successive n-sized chunks from lists."""
    for i in range(0, len(lists), n):
        yield lists[i:i + n]


class AFTNMessage(object):
    """docstring for AFTNMessage"""
    def __init__(self, message, cls='taf', time=None):
        super(AFTNMessage, self).__init__()
        self.message = message
        self.cls = cls
        self.time = datetime.datetime.utcnow() if time is None else time

    def raw(self):
        channel = conf.value('communication/other/channel')
        number = int(conf.value('communication/other/number'))
        send_address = conf.value('communication/address/' + self.cls)
        user_address = conf.value('communication/other/user_addr')

        addresses = self.divide_address(send_address)
        time = self.time.strftime('%d%H%M')

        # 定值
        self.aftn_time = ' '.join([time, user_address])
        self.aftn_nnnn = 'NNNN'

        aftn_message = []
        for address in addresses:
            self.aftn_zczc = ' '.join(['ZCZC', channel + str(number).zfill(4)])
            self.aftn_adress = ' '.join(['GG'] + address)
            items = [self.aftn_zczc, self.aftn_adress, self.aftn_time, self.message, self.aftn_nnnn]
            aftn_message.append('\n'.join(items))
            number += 1

        conf.setValue('communication/other/number', str(number))
        
        return aftn_message


    def divide_address(self, address):
        items = address.split()
        return chunks(items, 7)


class BaseSender(QtWidgets.QDialog, Ui_send.Ui_Send):

    signal_send = QtCore.pyqtSignal()
    signal_close = QtCore.pyqtSignal()
    signal_back = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        """
        初始化主窗口
        """
        super(BaseSender, self).__init__(parent)
        self.setupUi(self)

        self.button_box.button(QtWidgets.QDialogButtonBox.Ok).setText("Send")
        # self.button_box.addButton("TEST", QDialogButtonBox.ActionRole)
        self.rejected.connect(self.cancel_signal)
        self.signal_close.connect(self.clear)

        self.raw_group.hide()

    def receive(self, message):
        self.message = message
        self.rpt.setText(self.message['full'])

    def closeEvent(self, event):
        if event.spontaneous():
            self.cancel_signal()

    def cancel_signal(self):
        if self.button_box.button(QtWidgets.QDialogButtonBox.Ok).isEnabled():
            self.signal_back.emit()
            logger.debug('Back to edit')
        else:
            self.signal_close.emit()
            logger.debug('Close send dialog')

    def clear(self):
        self.rpt.setText('')
        self.raw_group.hide()
        self.button_box.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(True)


class TAFSender(BaseSender):

    def __init__(self, parent=None):
        super(TAFSender, self).__init__(parent)

        self.button_box.accepted.connect(self.send)
        self.button_box.accepted.connect(self.save)

    def save(self):
        item = Tafor(tt=self.message['head'][0:2], head=self.message['head'], rpt=self.message['rpt'], raw=json.dumps(self.aftn.raw()))
        db.add(item)
        db.commit()
        logger.debug('Save ' + item.rpt)
        self.signal_send.emit()

    def send(self):
        self.aftn = AFTNMessage(self.message['full'])
        self.raw.setText('\n\n\n\n'.join(self.aftn.raw()))
        self.raw_group.show()
        self.button_box.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)


class TaskTAFSender(BaseSender):

    def __init__(self, parent=None):
        super(TaskTAFSender, self).__init__(parent)

        self.setWindowTitle('定时任务')

        self.button_box.accepted.connect(self.save)
        self.button_box.accepted.connect(self.accept)

        # 自动发送报文的计时器
        self.auto_sent = QtCore.QTimer()
        self.auto_sent.timeout.connect(self.auto_send)
        self.auto_sent.start(30 * 1000)

        # 测试数据
        # self.Task_time = datetime.datetime.utcnow() + datetime.timedelta(minutes=1)

    def save(self):
        item = Task(tt=self.message['head'][0:2], head=self.message['head'], rpt=self.message['rpt'], plan=self.message['plan'])
        db.add(item)
        db.commit()
        logger.debug('Save Task', item.plan.strftime("%b %d %Y %H:%M:%S"))
        self.signal_send.emit()

    def auto_send(self):
        tasks = db.query(Task).filter_by(tafor_id=None).order_by(Task.plan).all()
        now = datetime.datetime.utcnow()
        send_status = False

        for task in tasks:

            if task.plan <= now:

                message = '\n'.join([task.head, task.rpt])
                aftn = AFTNMessage(message, time=task.plan)
                item = Tafor(tt=task.tt, head=task.head, rpt=task.rpt, raw=json.dumps(aftn.raw()))
                db.add(item)
                db.flush()
                task.tafor_id = item.id
                db.merge(task)
                db.commit()

                send_status = True

        logger.debug('Tasks ' + ' '.join(task.rpt for task in tasks))
        
        if send_status:
            logger.debug('Task complete')


class TrendSender(BaseSender):

    def __init__(self, parent=None):
        super(TrendSender, self).__init__(parent)

        self.button_box.accepted.connect(self.send)
        self.button_box.accepted.connect(self.save)

    def receive(self, message):
        self.message = message
        self.rpt.setText(self.message['rpt'])

    def save(self):
        item = Trend(sign=self.message['sign'], rpt=self.message['rpt'], raw=json.dumps(self.aftn.raw()))
        db.add(item)
        db.commit()
        logger.debug('Save ' + item.rpt)
        self.signal_send.emit()

    def send(self):
        self.aftn = AFTNMessage(self.message['full'], 'trend')
        self.raw.setText('\n\n\n\n'.join(self.aftn.raw()))
        self.raw_group.show()
        self.button_box.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)


    