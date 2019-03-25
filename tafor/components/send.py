import datetime

from PyQt5.QtGui import QFontMetrics, QFont
from PyQt5.QtCore import QCoreApplication, QTimer, QSize, pyqtSignal
from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QMessageBox, QTextEdit
from PyQt5.QtPrintSupport import QPrintDialog, QPrinter

from tafor import conf, logger
from tafor.models import db, Taf, Task, Trend, Sigmet
from tafor.utils import boolean, TafParser, SigmetParser, AFTNMessage, AFTNDecoder
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
        self.error = None
        self.rawText = None
        self.mode = 'send'

        self.sendButton = self.buttonBox.button(QDialogButtonBox.Ok)
        self.resendButton = self.buttonBox.button(QDialogButtonBox.Retry)
        self.cancelButton = self.buttonBox.button(QDialogButtonBox.Cancel)
        self.printButton = self.buttonBox.button(QDialogButtonBox.Reset)

        self.sendButton.setText(QCoreApplication.translate('Sender', 'Send'))
        self.resendButton.setText(QCoreApplication.translate('Sender', 'Resend'))
        self.cancelButton.setText(QCoreApplication.translate('Sender', 'Cancel'))
        self.printButton.setText(QCoreApplication.translate('Sender', 'Print'))

        self.rejected.connect(self.cancel)
        self.closeSignal.connect(self.clear)
        self.backSignal.connect(self.clear)
        self.printButton.clicked.connect(self.print)

        self.rawGroup.hide()
        self.printButton.hide()
        self.resendButton.hide()

    def setMode(self, mode):
        if mode == 'view':
            self.sendButton.hide()
            self.setWindowTitle(QCoreApplication.translate('Sender', 'View Message'))
            self.rawGroup.setTitle(QCoreApplication.translate('Sender', 'Raw Data'))

            if not self.item.confirmed and datetime.datetime.utcnow() - self.item.sent < datetime.timedelta(hours=2):
                self.resendButton.show()

            if self.item.raw:
                self.rawGroup.show()
                self.printButton.show()

        if mode == 'send':
            self.setWindowTitle(QCoreApplication.translate('Sender', 'Send Message'))
            self.rawGroup.setTitle(QCoreApplication.translate('Sender', 'Data has been sent to the serial port'))

    def receive(self, message, mode='send'):
        self.mode = mode
        if mode == 'view':
            self.item = message['item']
            self.parse(message)
            self.mode = 'view'
            self.raw.setText(self.item.rawText())

        if mode == 'send':
            self.parse(message)

        self.setMode(mode)

    def parse(self, message):
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

            if self.message['sign'] is None:
                html = '<p>{}</p>'.format(self.parser.renderer(style='html'))
            else:
                html = '<p>{}<br/>{}</p>'.format(self.message['sign'], self.parser.renderer(style='html'))
            if self.parser.tips:
                html += '<p style="color: grey"># {}</p>'.format('<br/># '.join(self.parser.tips))
            self.rpt.setHtml(html)

        except Exception as e:
            logger.exception(e)

        self.resizeRpt()

    def showRawGroup(self, error):
        if self.rawText is None:
            return None

        self.raw.setText(self.rawText)
        self.rawGroup.show()
        self.printButton.show()
        self.sendButton.hide()
        self.resendButton.hide()

        if error:
            self.error = error
            self.rawGroup.setTitle(QCoreApplication.translate('Sender', 'Send Failed'))
            self.resendButton.setEnabled(True)
            self.resendButton.setText(QCoreApplication.translate('Sender', 'Resend'))
            self.resendButton.show()

            title = QCoreApplication.translate('Sender', 'Error')
            QMessageBox.critical(self, title, error)

    def send(self):
        if hasattr(self, 'parser') and not self.parser.isValid():
            title = QCoreApplication.translate('Sender', 'Validator Warning')
            text = QCoreApplication.translate('Sender', 'The message did not pass the validator, do you still want to send?')
            ret = QMessageBox.question(self, title, text)
            if ret != QMessageBox.Yes:
                return None

        if self.mode == 'view':
            title = QCoreApplication.translate('Sender', 'Resend Reminder')
            text = QCoreApplication.translate('Sender', 'Some part of the AFTN message may be updated, do you still want to resend?')
            ret = QMessageBox.question(self, title, text)
            if ret != QMessageBox.Yes:
                return None

        self.sendButton.setEnabled(False)
        self.sendButton.setText(QCoreApplication.translate('Sender', 'Sending'))
        self.resendButton.setEnabled(False)
        self.resendButton.setText(QCoreApplication.translate('Sender', 'Sending'))

        if self.item and self.error:
            self.rawText = self.aftn.toString() if self.aftn else self.item.rawText()
        else:
            if self.state is None:
                fullMessage = '\n'.join([self.message['sign'], self.message['rpt']])
                self.aftn = AFTNMessage(fullMessage, self.reportType)
                self.parent.settingDialog.loadSerialNumber()

            self.state = self.aftn
            self.rawText = self.aftn.toString()

        self.thread = SerialThread(self.rawText, self)
        self.thread.doneSignal.connect(self.showRawGroup)
        self.thread.doneSignal.connect(self.save)
        self.thread.start()

    def save(self):
        if self.item:
            if self.error and self.aftn or not self.error:
                self.item.raw = self.aftn.toJson()
            self.item.sent = datetime.datetime.utcnow()
            logger.debug('Resend ' + self.item.rpt)
        else:
            self.item = self.model(tt=self.message['sign'][0:2], sign=self.message['sign'], rpt=self.message['rpt'], raw=self.aftn.toJson())
            logger.debug('Send ' + self.item.rpt)

        db.add(self.item)
        db.commit()
        self.sendSignal.emit()

    def print(self):
        printer = QPrinter()
        dialog = QPrintDialog(printer)
        if dialog.exec() != QDialog.Accepted:
            return

        editor = QTextEdit()
        priority = QCoreApplication.translate('Sender', 'Priority Indicator')
        address = QCoreApplication.translate('Sender', 'Send Address')
        originator = QCoreApplication.translate('Sender', 'Originator Address')
        content = QCoreApplication.translate('Sender', 'Message Content')
        time = QCoreApplication.translate('Sender', 'Sent Time')
        raw = QCoreApplication.translate('Sender', 'Raw Data')
        aftn = AFTNDecoder(self.item.raw)
        texts = [priority, aftn.priority, address, aftn.address, originator, aftn.originator,
            content, self.item.report, raw, self.item.rawText(), time, '{} UTC'.format(self.item.sent)]

        elements = []
        for title, content in zip(texts[::2], texts[1::2]):
            content = '<br>'.join(content.split('\n'))
            text = '<p><b>{}</b><br>{}</p>'.format(title, content)
            elements.append(text)

        font = QFont('Courier', 10)
        editor.setFont(font)
        editor.setHtml(''.join(elements))
        editor.print(printer)

    def cancel(self):
        if (self.error or not self.sendButton.isHidden()) and self.mode == 'send':
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

    def closeEvent(self, event):
        if event.spontaneous():
            self.cancel()

    def clear(self):
        self.state = None
        self.item = None
        self.error = None
        self.rawText = None
        self.rpt.setText('')
        self.rawGroup.hide()
        self.printButton.hide()
        self.resendButton.setEnabled(True)
        self.resendButton.setText(QCoreApplication.translate('Sender', 'Resend'))
        self.resendButton.hide()
        self.sendButton.setEnabled(True)
        self.sendButton.setText(QCoreApplication.translate('Sender', 'Send'))
        self.sendButton.show()


class TafSender(BaseSender):

    def __init__(self, parent=None):
        super(TafSender, self).__init__(parent)
        self.reportType = 'TAF'
        self.model = Taf
        self.buttonBox.accepted.connect(self.send)


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

    def parse(self, message):
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
        self.model = Sigmet
        self.reportType = 'SIGMET'
        self.buttonBox.accepted.connect(self.send)

    def parse(self, message):
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
        super(SigmetSender, self).save()
        if not self.item.isCnl():
            delta = self.item.expired() - datetime.datetime.utcnow() - datetime.timedelta(minutes=15)
            text = 'SIGMET {}'.format(self.item.parser().sequence())
            QTimer.singleShot(delta.total_seconds() * 1000, lambda: self.parent.remindSigmet(text))
    