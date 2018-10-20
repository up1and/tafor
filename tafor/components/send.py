import datetime

from PyQt5.QtGui import QFontMetrics
from PyQt5.QtCore import QCoreApplication, QTimer, QSize, pyqtSignal
from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QMessageBox

from tafor import conf, logger
from tafor.models import db, Taf, Task, Trend, Sigmet
from tafor.utils import boolean, TafParser, SigmetParser, AFTNMessage
from tafor.utils.thread import SerialThread
from tafor.components.ui import Ui_send


class BaseSender(QDialog, Ui_send.Ui_Sender):

    sendSignal = pyqtSignal()
    closeSignal = pyqtSignal()
    backSignal = pyqtSignal()

    def __init__(self, parent=None):
        super(BaseSender, self).__init__(parent)
        self.setupUi(self)

        self.parent = parent
        self.aftn = None
        self.state = None
        self.item = None

        self.sendButton = self.buttonBox.button(QDialogButtonBox.Ok)
        self.resendButton = self.buttonBox.button(QDialogButtonBox.Retry)
        self.cancelButton = self.buttonBox.button(QDialogButtonBox.Cancel)

        self.sendButton.setText(QCoreApplication.translate('Sender', 'Send'))
        self.resendButton.setText(QCoreApplication.translate('Sender', 'Resend'))
        self.cancelButton.setText(QCoreApplication.translate('Sender', 'Cancel'))
        self.resendButton.setVisible(False)
        self.resendButton.setEnabled(False)
        self.rejected.connect(self.cancel)
        self.closeSignal.connect(self.clear)
        self.backSignal.connect(self.clear)

        self.rawGroup.hide()

    def receive(self, message):
        self.message = message
        visHas5000 = boolean(conf.value('Validator/VisHas5000'))
        cloudHeightHas450 = boolean(conf.value('Validator/CloudHeightHas450'))
        try:
            self.parser = TafParser(self.message['rpt'], visHas5000=visHas5000, cloudHeightHas450=cloudHeightHas450)
            self.parser.validate()

            if self.parser.hasMessageChanged():
                text = QCoreApplication.translate('Sender', 'The message is different from the original after validation')
                self.parser.tips.insert(0, text)
                self.message['rpt'] = self.parser.renderer()

            html = '<p>{}<br/>{}</p>'.format(self.message['sign'], self.parser.renderer(style='html'))
            if self.parser.tips:
                html += '<p style="color: grey"># {}</p>'.format('<br/># '.join(self.parser.tips))
            self.rpt.setHtml(html)

        except Exception as e:
            logger.exception(e)

        self.resizeRpt()

    def showRawGroup(self, error):
        self.sendButton.setText(QCoreApplication.translate('Sender', 'Send'))

        if self.state is None:
            return None

        self.raw.setText(self.aftn.toString())
        self.rawGroup.show()

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

        if self.state is None:
            fullMessage = '\n'.join([self.message['sign'], self.message['rpt']])
            self.aftn = AFTNMessage(fullMessage, self.reportType)

        self.state = self.aftn

        self.sendButton.setEnabled(False)
        self.sendButton.setText(QCoreApplication.translate('Sender', 'Sending'))
        self.parent.settingDialog.loadSerialNumber()

        message = self.aftn.toString()

        self.thread = SerialThread(message, self)
        self.thread.doneSignal.connect(self.showRawGroup)
        self.thread.doneSignal.connect(self.save)
        self.thread.start()

    def closeEvent(self, event):
        if event.spontaneous():
            self.cancel()

    def cancel(self):
        if self.sendButton.isEnabled() or self.resendButton.isEnabled():
            self.backSignal.emit()
        else:
            self.closeSignal.emit()

    def resizeRpt(self):
        text = self.rpt.toPlainText()
        font = self.rpt.document().defaultFont()
        fontMetrics = QFontMetrics(font)
        textSize = fontMetrics.size(0, text)
        height = 60 if boolean(conf.value('General/LargeFont')) else 30
        textHeight = textSize.height() + height
        self.rpt.setMaximumSize(QSize(16777215, textHeight))

    def clear(self):
        self.state = None
        self.item = None
        self.rpt.setText('')
        self.rawGroup.hide()
        self.sendButton.setEnabled(True)
        self.sendButton.setVisible(True)
        self.resendButton.setEnabled(False)
        self.resendButton.setVisible(False)


class TafSender(BaseSender):

    def __init__(self, parent=None):
        super(TafSender, self).__init__(parent)
        self.reportType = 'TAF'
        self.buttonBox.accepted.connect(self.send)

    def save(self):
        if self.item:
            self.item.sent = datetime.datetime.utcnow()
            logger.debug('Resend ' + self.item.rpt)
        else:
            self.item = Taf(tt=self.message['sign'][0:2], sign=self.message['sign'], rpt=self.message['rpt'], raw=self.aftn.toJson())
            logger.debug('Send ' + self.item.rpt)

        db.add(self.item)
        db.commit()
        self.sendSignal.emit()


class TaskTafSender(BaseSender):

    def __init__(self, parent=None):
        super(TaskTafSender, self).__init__(parent)
        self.setWindowTitle(QCoreApplication.translate('Sender', 'Delay Send Message'))
        self.reportType = 'TAF'
        self.buttonBox.accepted.connect(self.save)
        self.buttonBox.accepted.connect(self.accept)

    def save(self):
        self.item = Task(tt=self.message['sign'][0:2], sign=self.message['sign'], rpt=self.message['rpt'], planning=self.message['planning'])
        db.add(self.item)
        db.commit()
        logger.debug('Task {} will be sent on {}'.format(self.item.rpt, self.item.planning.strftime('%Y-%m-%d %H:%M:%S')))
        self.sendSignal.emit()


class TrendSender(BaseSender):

    def __init__(self, parent=None):
        super(TrendSender, self).__init__(parent)
        self.reportType = 'Trend'
        self.buttonBox.accepted.connect(self.send)

    def receive(self, message):
        self.message = message
        self.rpt.setText(self.message['rpt'])

    def save(self):
        if self.item:
            self.item.sent = datetime.datetime.utcnow()
            logger.debug('Resend ' + self.item.rpt)
        else:
            self.item = Trend(sign=self.message['sign'], rpt=self.message['rpt'], raw=self.aftn.toJson())
            logger.debug('Send ' + self.item.rpt)

        db.add(self.item)
        db.commit()
        self.sendSignal.emit()


class SigmetSender(BaseSender):

    def __init__(self, parent=None):
        super(SigmetSender, self).__init__(parent)
        self.reportType = 'SIGMET'
        self.buttonBox.accepted.connect(self.send)

    def receive(self, message):
        self.message = message
        firCode = conf.value('Message/FIR')
        airportCode = conf.value('Message/ICAO')
        try:
            self.parser = SigmetParser(self.message['rpt'], firCode=firCode, airportCode=airportCode)
            html = '<p>{}<br/>{}</p>'.format(self.message['sign'], self.parser.renderer(style='html'))
            self.rpt.setHtml(html)

        except Exception as e:
            logger.error(e)

    def save(self):
        if self.item:
            self.item.sent = datetime.datetime.utcnow()
            logger.debug('Resend ' + self.item.rpt)
        else:
            self.item = Sigmet(tt=self.message['sign'][0:2], sign=self.message['sign'], rpt=self.message['rpt'], raw=self.aftn.toJson())
            logger.debug('Send ' + self.item.rpt)

        db.add(self.item)
        db.commit()
        self.remind(self.item)
        self.sendSignal.emit()

    def remind(self, item):
        if not item.isCnl():
            delta = item.expired() - datetime.datetime.utcnow() - datetime.timedelta(minutes=15)
            text = 'SIGMET {}'.format(item.sequence)
            QTimer.singleShot(delta.total_seconds() * 1000, lambda: self.parent.remindSigmet(text))


class ReSender(BaseSender):

    def __init__(self, parent=None):
        super(ReSender, self).__init__(parent)
        self.reportType = 'TAF'
        self.buttonBox.accepted.connect(self.send)
        title = QCoreApplication.translate('Sender', 'Resend Message')
        self.setWindowTitle(title)

    def save(self):
        item = self.message['item']
        item.raw = self.aftn.toJson()
        db.add(item)
        db.commit()

    def closeEvent(self, event):
        self.aftn = None
        self.clear()
    