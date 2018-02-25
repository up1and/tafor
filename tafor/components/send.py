import datetime

from PyQt5.QtCore import QCoreApplication, QTimer, pyqtSignal
from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QMessageBox

from tafor import conf, logger
from tafor.components.ui import Ui_send
from tafor.models import db, Taf, Task, Trend
from tafor.utils import Parser, AFTNMessage
from tafor.utils.thread import SerialThread


class BaseSender(QDialog, Ui_send.Ui_Sender):

    sendSignal = pyqtSignal()
    closeSignal = pyqtSignal()
    backSignal = pyqtSignal()

    def __init__(self, parent=None):
        super(BaseSender, self).__init__(parent)
        self.setupUi(self)

        self.parent = parent
        self.aftn = None

        self.sendButton = self.buttonBox.button(QDialogButtonBox.Ok)
        self.resendButton = self.buttonBox.button(QDialogButtonBox.Retry)
        self.cancelButton = self.buttonBox.button(QDialogButtonBox.Cancel)

        self.sendButton.setText(QCoreApplication.translate('Sender', 'Send'))
        self.resendButton.setText(QCoreApplication.translate('Sender', 'Resend'))
        self.cancelButton.setText(QCoreApplication.translate('Sender', 'Cancel'))
        self.resendButton.setVisible(False)
        self.resendButton.setEnabled(False)
        # self.buttonBox.addButton("TEST", QDialogButtonBox.ActionRole)
        self.rejected.connect(self.cancel)
        self.closeSignal.connect(self.clear)
        self.backSignal.connect(self.clear)

        self.rawGroup.hide()

    def receive(self, message):
        self.message = message
        try:
            self.parser = Parser(self.message['rpt'])
            self.parser.validate()
            html = '<p>{}<br/>{}</p>'.format(self.message['head'], self.parser.renderer(style='html'))
            if self.parser.tips:
                html += '<p style="color: grey"># {}</p>'.format('<br/># '.join(self.parser.tips))
            self.rpt.setHtml(html)
            self.message['rpt'] = self.parser.renderer()

        except Exception as e:
            logger.error(e)

    def showRawGroup(self, error):
        self.raw.setText(self.aftn.toString())
        self.rawGroup.show()
        self.sendButton.setEnabled(False)
        self.parent.settingDialog.loadSerialNumber()

        if error:
            self.rawGroup.setTitle(QCoreApplication.translate('Sender', 'Send Failed'))
            self.sendButton.setVisible(False)
            self.resendButton.setVisible(True)
            self.resendButton.setEnabled(True)

            title = QCoreApplication.translate('Sender', 'Error')
            QMessageBox.critical(self, title, error)

    def send(self):
        if hasattr(self, 'parser') and not self.parser.isValid():
            title = QCoreApplication.translate('Sender', 'Validator Warning')
            text = QCoreApplication.translate('Sender', 'The message did not pass the validator, do you still want to send?')
            ret = QMessageBox.question(self, title, text)
            if ret != QMessageBox.Yes:
                return None

        if not isinstance(self.aftn, AFTNMessage):
            self.aftn = AFTNMessage(self.message['full'], self.reportType)

        message = self.aftn.toString()

        thread = SerialThread(message, self)
        thread.doneSignal.connect(self.showRawGroup)
        thread.doneSignal.connect(self.save)
        thread.start()

    def closeEvent(self, event):
        if event.spontaneous():
            self.cancel()

    def cancel(self):
        if self.sendButton.isEnabled() or self.resendButton.isEnabled():
            self.backSignal.emit()
        else:
            self.closeSignal.emit()

    def clear(self):
        self.rpt.setText('')
        self.rawGroup.hide()
        self.sendButton.setEnabled(True)
        self.sendButton.setVisible(True)
        self.resendButton.setEnabled(False)
        self.resendButton.setVisible(False)


class TAFSender(BaseSender):

    def __init__(self, parent=None):
        super(TAFSender, self).__init__(parent)

        self.reportType = 'TAF'

        self.buttonBox.accepted.connect(self.send)

    def save(self):
        item = Taf(tt=self.message['head'][0:2], head=self.message['head'], rpt=self.message['rpt'], raw=self.aftn.toJson())
        db.add(item)
        db.commit()
        logger.debug('Save ' + item.rpt)
        self.sendSignal.emit()


class TaskTAFSender(BaseSender):

    def __init__(self, parent=None):
        super(TaskTAFSender, self).__init__(parent)

        self.setWindowTitle(QCoreApplication.translate('Sender', 'Timing Tasks'))

        self.reportType = 'TAF'

        self.buttonBox.accepted.connect(self.save)
        self.buttonBox.accepted.connect(self.accept)

        # 自动发送报文的计时器
        self.autoSendTimer = QTimer()
        self.autoSendTimer.timeout.connect(self.autoSend)
        self.autoSendTimer.start(30 * 1000)

        # 测试数据
        # self.Task_time = datetime.datetime.utcnow() + datetime.timedelta(minutes=1)

    def save(self):
        item = Task(tt=self.message['head'][0:2], head=self.message['head'], rpt=self.message['rpt'], planning=self.message['planning'])
        db.add(item)
        db.commit()
        logger.debug('Save Task', item.planning.strftime("%b %d %Y %H:%M:%S"))
        self.sendSignal.emit()

    def autoSend(self):
        tasks = db.query(Task).filter_by(taf_id=None).order_by(Task.planning).all()
        now = datetime.datetime.utcnow()
        sendStatus = False

        for task in tasks:

            if task.planning <= now:

                message = '\n'.join([task.head, task.rpt])
                aftn = AFTNMessage(message, time=task.planning)
                item = Taf(tt=task.tt, head=task.head, rpt=task.rpt, raw=aftn.toJson())
                db.add(item)
                db.flush()
                task.taf_id = item.id
                db.merge(task)
                db.commit()

                sendStatus = True

        logger.debug('Tasks ' + ' '.join(task.rpt for task in tasks))
        
        if sendStatus:
            logger.debug('Task complete')


class TrendSender(BaseSender):

    def __init__(self, parent=None):
        super(TrendSender, self).__init__(parent)

        self.reportType = 'Trend'

        self.buttonBox.accepted.connect(self.send)

    def receive(self, message):
        self.message = message
        self.rpt.setText(self.message['rpt'])

    def save(self):
        item = Trend(sign=self.message['sign'], rpt=self.message['rpt'], raw=self.aftn.toJson())
        db.add(item)
        db.commit()
        logger.debug('Save ' + item.rpt)
        self.sendSignal.emit()


class SigmetSender(BaseSender):

    def __init__(self, parent=None):
        super(SigmetSender, self).__init__(parent)

        self.reportType = 'Sigmet'

        self.buttonBox.accepted.connect(self.send)

    def receive(self, message):
        self.message = message
        self.rpt.setText(self.message['full'])

    def save(self):
        pass
    