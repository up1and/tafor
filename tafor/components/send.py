import json
import datetime

from PyQt5 import QtCore, QtGui, QtWidgets

from tafor.components.ui import Ui_send
from tafor.models import db, Tafor, Task, Trend
from tafor.utils import Parser, serialComm
from tafor import conf, logger


class AFTNMessage(object):
    """docstring for AFTNMessage"""
    def __init__(self, message, sort='TAF', time=None):
        super(AFTNMessage, self).__init__()
        self.message = message
        self.sort = sort
        self.time = datetime.datetime.utcnow() if time is None else time

        self.toAFTN()

    def raw(self):
        return self.aftnMessages

    def toAFTN(self):
        channel = conf.value('Communication/Channel')
        number = conf.value('Communication/Number')
        number = int(number) if number else 0
        sendAddress = conf.value('Communication/{}Address'.format(self.sort)) or ''
        userAddress = conf.value('Communication/UserAddress') or ''

        addresses = self.divideAddress(sendAddress)
        time = self.time.strftime('%d%H%M')

        # 定值
        self.aftnTime = ' '.join([time, userAddress])
        self.aftnNnnn = 'NNNN'

        self.aftnMessages = []
        for address in addresses:
            self.aftnZczc = ' '.join(['ZCZC', channel + str(number).zfill(4)])
            self.aftnAddress = ' '.join(['GG'] + address)
            items = [self.aftnZczc, self.aftnAddress, self.aftnTime, self.message, self.aftnNnnn]
            self.aftnMessages.append('\n'.join(items))
            number += 1

        conf.setValue('Communication/Number', str(number))
        
        return self.aftnMessages

    def divideAddress(self, address):
        def chunks(lists, n):
            """Yield successive n-sized chunks from lists."""
            for i in range(0, len(lists), n):
                yield lists[i:i + n]

        items = address.split()
        return chunks(items, 7)


class BaseSender(QtWidgets.QDialog, Ui_send.Ui_Send):

    sendSignal = QtCore.pyqtSignal()
    closeSignal = QtCore.pyqtSignal()
    backSignal = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        """
        初始化主窗口
        """
        super(BaseSender, self).__init__(parent)
        self.setupUi(self)

        self.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText("Send")
        # self.buttonBox.addButton("TEST", QDialogButtonBox.ActionRole)
        self.rejected.connect(self.cancel)
        self.closeSignal.connect(self.clear)

        self.rawGroup.hide()

    def receive(self, message):
        self.message = message
        try:
            m = Parser(self.message['rpt'])
            m.validate()
            html = '<p>{}<br/>{}</p>'.format(self.message['head'], m.renderer(style='html'))
            if m.tips:
                html += '<p style="color: grey"># {}</p>'.format('<br/># '.join(m.tips))
            self.rpt.setHtml(html)
            self.message['rpt'] = m.renderer()

        except Exception as e:
            logger.error(e)

    def toSerial(self, message):
        port = conf.value('Communication/SerialPort')
        baudrate = int(conf.value('Communication/SerialBaudrate'))
        bytesize = conf.value('Communication/SerialBytesize')
        parity = conf.value('Communication/SerialParity')
        stopbits = conf.value('Communication/SerialStopbits')

        try:
            error = not serialComm(message, port, baudrate=baudrate, bytesize=bytesize, parity=parity, stopbits=stopbits)
        except Exception as e:
            error = str(e)
            logger.error(e)
        
        return error

    def closeEvent(self, event):
        if event.spontaneous():
            self.cancel()

    def cancel(self):
        if self.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).isEnabled():
            self.backSignal.emit()
            logger.debug('Back to edit')
        else:
            self.closeSignal.emit()
            logger.debug('Close send dialog')

    def clear(self):
        self.rpt.setText('')
        self.rawGroup.hide()
        self.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(True)


class TAFSender(BaseSender):

    def __init__(self, parent=None):
        super(TAFSender, self).__init__(parent)

        self.buttonBox.accepted.connect(self.send)
        self.buttonBox.accepted.connect(self.save)

    def save(self):
        item = Tafor(tt=self.message['head'][0:2], head=self.message['head'], rpt=self.message['rpt'], raw=json.dumps(self.aftn.raw()))
        db.add(item)
        db.commit()
        logger.debug('Save ' + item.rpt)
        self.sendSignal.emit()

    def send(self):
        self.aftn = AFTNMessage(self.message['full'])
        messages = self.aftn.raw()
        error = self.toSerial('\n\n\n\n'.join(messages))

        if error:
            self.rawGroup.setTitle('发送失败')
        else:
            self.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)

        self.raw.setText('\n\n\n\n'.join(messages))
        self.rawGroup.show()


class TaskTAFSender(BaseSender):

    def __init__(self, parent=None):
        super(TaskTAFSender, self).__init__(parent)

        self.setWindowTitle('定时任务')

        self.buttonBox.accepted.connect(self.save)
        self.buttonBox.accepted.connect(self.accept)

        # 自动发送报文的计时器
        self.autoSendTimer = QtCore.QTimer()
        self.autoSendTimer.timeout.connect(self.autoSend)
        self.autoSendTimer.start(30 * 1000)

        # 测试数据
        # self.Task_time = datetime.datetime.utcnow() + datetime.timedelta(minutes=1)

    def save(self):
        item = Task(tt=self.message['head'][0:2], head=self.message['head'], rpt=self.message['rpt'], plan=self.message['plan'])
        db.add(item)
        db.commit()
        logger.debug('Save Task', item.plan.strftime("%b %d %Y %H:%M:%S"))
        self.sendSignal.emit()

    def autoSend(self):
        tasks = db.query(Task).filter_by(tafor_id=None).order_by(Task.plan).all()
        now = datetime.datetime.utcnow()
        sendStatus = False

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

                sendStatus = True

        logger.debug('Tasks ' + ' '.join(task.rpt for task in tasks))
        
        if sendStatus:
            logger.debug('Task complete')


class TrendSender(BaseSender):

    def __init__(self, parent=None):
        super(TrendSender, self).__init__(parent)

        self.buttonBox.accepted.connect(self.send)
        self.buttonBox.accepted.connect(self.save)

    def receive(self, message):
        self.message = message
        self.rpt.setText(self.message['rpt'])

    def save(self):
        item = Trend(sign=self.message['sign'], rpt=self.message['rpt'], raw=json.dumps(self.aftn.raw()))
        db.add(item)
        db.commit()
        logger.debug('Save ' + item.rpt)
        self.sendSignal.emit()

    def send(self):
        self.aftn = AFTNMessage(self.message['full'], 'Trend')
        messages = self.aftn.raw()
        error = self.toSerial('\n\n\n\n'.join(messages))

        if error:
            self.rawGroup.setTitle('发送失败')
        else:
            self.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)

        self.raw.setText('\n\n\n\n'.join(messages))
        self.rawGroup.show()


    