import datetime

from PyQt5.QtGui import QFontMetrics, QFont, QPixmap
from PyQt5.QtCore import QCoreApplication, QTimer, QSize, Qt, pyqtSignal
from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QMessageBox, QTextEdit, QLabel
from PyQt5.QtPrintSupport import QPrintDialog, QPrinter

from tafor import conf, logger
from tafor.states import context
from tafor.models import db, Taf, Trend, Sigmet, Other
from tafor.utils import boolean, TafParser, MetarParser, SigmetParser, AFTNMessageGenerator, FileMessageGenerator, AFTNDecoder
from tafor.utils.thread import SerialThread, FtpThread
from tafor.components.ui import Ui_send, main_rc


class AFTNChannel(object):
    generator = AFTNMessageGenerator
    thread = SerialThread
    field = 'raw'
    sequenceConfigPath = 'Communication/ChannelSequenceNumber'

    def successText():
        return QCoreApplication.translate('Sender', 'Data has been sent to the serial port')

    def resendText():
        return QCoreApplication.translate('Sender', 'Some part of the AFTN message may be updated, do you still want to resend?')


class FtpChannel(object):
    generator = FileMessageGenerator
    thread = FtpThread
    field = 'file'
    sequenceConfigPath = 'Communication/FileSequenceNumber'

    def successText():
        return QCoreApplication.translate('Sender', 'File has been uploaded to the host')

    def resendText():
        return QCoreApplication.translate('Sender', 'The file will be resent, do you want to continue?')


class BaseSender(QDialog, Ui_send.Ui_Sender):

    sendSignal = pyqtSignal()
    closeSignal = pyqtSignal()
    backSignal = pyqtSignal()

    def __init__(self, parent=None):
        super(BaseSender, self).__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self.parent = parent
        self.generator = None
        self.currentGenerator = None
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
        self.buttonBox.accepted.connect(self.send)
        self.printButton.clicked.connect(self.print)

        self.rawGroup.hide()
        self.printButton.hide()
        self.resendButton.hide()

        # self.rpt.setStyleSheet('font-size: 13px;')
        # self.raw.setStyleSheet('font-size: 13px; background-color: rgb(0, 0, 0); color: rgb(255, 255, 255);')

        self.setLineIcon()
        self.setChannel()

    def line(self):
        text = conf.value('General/CommunicationLine')
        return text.lower() if text else 'aftn'

    def setChannel(self):
        if self.line() == 'ftp':
            self.channel = FtpChannel
        else:
            self.channel = AFTNChannel

    def setLineIcon(self):
        pixmap = QPixmap(':/{}.png'.format(self.line()))
        if hasattr(self, 'lineSign'):
            self.lineSign.setPixmap(pixmap)
        else:
            self.lineSign = QLabel(self)
            self.lineSign.setPixmap(pixmap)
            self.lineSign.setMask(pixmap.mask())
            self.lineSign.adjustSize()
            self.lineSign.move(688, 2)

        visible = self.sendButton.isVisible() or self.resendButton.isVisible()
        self.lineSign.setVisible(visible)

    def setMode(self, mode):
        if mode == 'view':
            self.sendButton.hide()
            self.setWindowTitle(QCoreApplication.translate('Sender', 'View Message'))
            self.rawGroup.setTitle(QCoreApplication.translate('Sender', 'Raw Data'))

            if self.line() == 'ftp':
                text = self.item.file
            else:
                text = self.item.rawText() or self.item.file

            self.raw.setText(text)

            if not self.item.confirmed and datetime.datetime.utcnow() - self.item.sent < datetime.timedelta(hours=2):
                self.resendButton.show()

            if self.item.raw:
                self.rawGroup.show()
                self.printButton.show()

            if self.item.file:
                self.rawGroup.show()

        if mode == 'send':
            self.setWindowTitle(QCoreApplication.translate('Sender', 'Send Message'))
            self.rawGroup.setTitle(self.channel.successText())

    def receive(self, message, mode='send'):
        self.mode = mode
        if mode == 'view':
            self.item = message['item']

        self.parse(message)
        self.setMode(mode)

    def parse(self, message):
        self.message = message
        visHas5000 = boolean(conf.value('Validator/VisHas5000'))
        cloudHeightHas450 = boolean(conf.value('Validator/CloudHeightHas450'))
        weakPrecipitationVerification = boolean(conf.value('Validator/WeakPrecipitationVerification'))

        self.parser = TafParser(self.message['rpt'],
            visHas5000=visHas5000, cloudHeightHas450=cloudHeightHas450, weakPrecipitationVerification=weakPrecipitationVerification)
        self.parser.validate()

        if self.parser.hasMessageChanged():
            self.message['rpt'] = self.parser.renderer()

        html = self.parser.renderer(style='html')
        if self.message['sign'] is None:
            html = '<p>{}</p>'.format(html)
        else:
            html = '<p>{}<br/>{}</p>'.format(self.message['sign'], html)
        if self.parser.tips:
            html += '<p style="color: grey"># {}</p>'.format('<br/># '.join(self.parser.tips))

        self.rpt.setHtml(html)
        self.resizeRpt()

    def showRawGroup(self, error=''):
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

            if context.environ.canEnable(self.reportType):
                self.resendButton.setEnabled(True)
                self.resendButton.setText(QCoreApplication.translate('Sender', 'Resend'))
                self.resendButton.show()

            title = QCoreApplication.translate('Sender', 'Error')
            QMessageBox.critical(self, title, error)

    def parameters(self):
        spacer = ' ' if self.reportType == 'Trend' else '\n'
        message = spacer.join([self.message['sign'], self.message['rpt']])
        channel = conf.value('Communication/Channel') or ''
        number = conf.value(self.channel.sequenceConfigPath) or 1
        priority = 'FF' if self.reportType in ['SIGMET', 'AIRMET'] or \
            self.message['rpt'].startswith('TAF AMD') else 'GG'
        address = conf.value('Communication/{}Address'.format(self.reportType)) or ''
        originator = conf.value('Communication/OriginatorAddress') or ''
        sequenceLength = conf.value('Communication/ChannelSequenceLength') or 4
        maxSendAddress = conf.value('Communication/MaxSendAddress') or 21

        return message, channel, number, priority, address, originator, sequenceLength, maxSendAddress

    def generateRawText(self):
        if self.item and self.error:
            self.rawText = self.generator.toString() if self.generator else self.item.rawText()
        else:
            if self.currentGenerator is None:
                message, channel, number, priority, address, originator, sequenceLength, maxSendAddress = self.parameters()
                generator = self.channel.generator
                self.generator = generator(message, channel=channel, number=number, priority=priority, address=address,
                    originator=originator, sequenceLength=sequenceLength, maxSendAddress=maxSendAddress)

            self.currentGenerator = self.generator
            self.rawText = self.generator.toString()

    def send(self):
        if hasattr(self, 'parser') and not self.parser.isValid() and not (self.reportType == 'Trend' and self.parser.failed):
            title = QCoreApplication.translate('Sender', 'Validator Warning')
            text = QCoreApplication.translate('Sender', 'The message did not pass the validator, do you still want to send?')
            ret = QMessageBox.question(self, title, text)
            if ret != QMessageBox.Yes:
                return None

        if self.mode == 'view':
            title = QCoreApplication.translate('Sender', 'Resend Reminder')
            ret = QMessageBox.question(self, title, self.channel.resendText())
            if ret != QMessageBox.Yes:
                return None

        if self.line() != 'aftn':
            title = QCoreApplication.translate('Sender', 'Transmission Line Reminder')
            text = QCoreApplication.translate('Sender', 'Not a common transmission line, do you want to continue?')
            ret = QMessageBox.question(self, title, text)
            if ret != QMessageBox.Yes:
                return None

        self.sendButton.setEnabled(False)
        self.sendButton.setText(QCoreApplication.translate('Sender', 'Sending'))
        self.resendButton.setEnabled(False)
        self.resendButton.setText(QCoreApplication.translate('Sender', 'Sending'))

        self.generateRawText()

        if context.environ.canEnable(self.reportType):
            thread = self.channel.thread
            self.thread = thread(self.rawText, self)
            self.thread.doneSignal.connect(self.showRawGroup)
            self.thread.doneSignal.connect(self.save)
            self.thread.doneSignal.connect(self.updateSequenceNumber)
            self.thread.start()
        else:
            error = QCoreApplication.translate('Sender', 'Limited functionality, please check the license information')
            self.showRawGroup(error=error)
            self.save()

    def save(self):
        if self.item and self.item.uuid == self.message['uuid']:
            if self.error and self.generator or not self.error:
                setattr(self.item, self.channel.field, self.generator.toJson())
            self.item.sent = datetime.datetime.utcnow()
            logger.debug('Resend ' + self.item.rpt)
        else:
            self.item = self.model(uuid=self.message['uuid'],
                tt=self.message['sign'][0:2], sign=self.message['sign'], rpt=self.message['rpt'])
            setattr(self.item, self.channel.field, self.generator.toJson())
            logger.debug('Send ' + self.item.rpt)

        db.add(self.item)
        db.commit()
        self.sendSignal.emit()

    def updateSequenceNumber(self):
        if not self.error:
            conf.setValue(self.channel.sequenceConfigPath, str(self.generator.number))

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

    def resizeRpt(self):
        text = self.rpt.toPlainText()
        font = self.rpt.document().defaultFont()
        fontMetrics = QFontMetrics(font)
        textSize = fontMetrics.size(0, text)
        textHeight = textSize.height() + 50
        self.rpt.setMaximumHeight(textHeight)

    def cancel(self):
        if self.mode == 'send':
            if (self.error or not self.sendButton.isHidden() or not self.resendButton.isHidden()):
                self.backSignal.emit()
            else:
                self.closeSignal.emit()

        self.clear()

    def showEvent(self, event):
        self.setLineIcon()
        self.setChannel()

    def closeEvent(self, event):
        if event.spontaneous():
            self.cancel()

        self.clear()

    def clear(self):
        self.item = None
        self.error = None
        self.rawText = None
        self.currentGenerator = None
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


class TrendSender(BaseSender):

    def __init__(self, parent=None):
        super(TrendSender, self).__init__(parent)
        self.reportType = 'Trend'

    def line(self):
        return 'aftn'

    def parse(self, message):
        self.message = message
        html = self.message['rpt']
        parser = context.notification.metar.parser()
        if parser:
            metar = parser.primary.part
            visHas5000 = boolean(conf.value('Validator/VisHas5000'))
            cloudHeightHas450 = boolean(conf.value('Validator/CloudHeightHas450'))
            weakPrecipitationVerification = boolean(conf.value('Validator/WeakPrecipitationVerification'))

            self.parser = MetarParser(' '.join([metar, self.message['rpt']]), ignoreMetar=True,
                visHas5000=visHas5000, cloudHeightHas450=cloudHeightHas450, weakPrecipitationVerification=weakPrecipitationVerification)
            self.parser.validate()

            if not self.parser.failed:
                html = '<p>{}</p>'.format(self.parser.renderer(style='html'))
                if self.parser.tips:
                    html += '<p style="color: grey"># {}</p>'.format('<br/># '.join(self.parser.tips))

        self.rpt.setHtml(html)
        self.resizeRpt()

    def save(self):
        if self.item and self.item.uuid == self.message['uuid']:
            self.item.sent = datetime.datetime.utcnow()
            logger.debug('Resend ' + self.item.rpt)
        else:
            self.item = Trend(uuid=self.message['uuid'], sign=self.message['sign'], rpt=self.message['rpt'], raw=self.generator.toJson())
            logger.debug('Send ' + self.item.rpt)

        db.add(self.item)
        db.commit()
        self.sendSignal.emit()


class SigmetSender(BaseSender):

    def __init__(self, parent=None):
        super(SigmetSender, self).__init__(parent)
        self.model = Sigmet
        self.reportType = 'SIGMET'

    def parse(self, message):
        self.message = message

        if self.message['sign'] and self.message['sign'][0:2] == 'WA' or 'AIRMET' in self.message['rpt'].split():
            self.reportType = 'AIRMET'
        else:
            self.reportType = 'SIGMET'

        try:
            self.parser = SigmetParser(self.message['rpt'])
            html = self.parser.renderer(style='html')
            if self.message['sign'] is None:
                html = '<p>{}</p>'.format(html)
            else:
                html = '<p>{}<br/>{}</p>'.format(self.message['sign'], html)

            self.rpt.setHtml(html)
            self.resizeRpt()

        except Exception as e:
            logger.error(e)

    def save(self):
        super(SigmetSender, self).save()
        if not self.item.isCnl():
            delta = self.item.expired() - datetime.datetime.utcnow() - datetime.timedelta(minutes=20)
            sig = self.item.parser()
            QTimer.singleShot(delta.total_seconds() * 1000, lambda: self.parent.remindSigmet(sig))


class CustomSender(BaseSender):

    def __init__(self, parent=None):
        super(CustomSender, self).__init__(parent)
        self.rptGroup.hide()
        self.reportType = 'Custom'
        self.setModal(True)
        self.setWindowTitle(QCoreApplication.translate('Sender', 'Send Custom Message'))

    def line(self):
        return 'aftn'

    def load(self):
        self.currentGenerator = None
        self.message = context.other.state()
        self.generateRawText()
        self.showRawGroup()
        self.lineSign.show()
        self.sendButton.show()
        self.printButton.hide()
        self.rawGroup.setTitle(QCoreApplication.translate('Sender', 'Received Messages'))

    def parameters(self):
        message = self.message['message']
        priority = self.message['priority']
        address = self.message['address']
        channel = conf.value('Communication/Channel') or ''
        originator = conf.value('Communication/OriginatorAddress') or ''
        number = conf.value(self.channel.sequenceConfigPath) or 1
        sequenceLength = conf.value('Communication/ChannelSequenceLength') or 4
        maxSendAddress = conf.value('Communication/MaxSendAddress') or 21

        return message, channel, number, priority, address, originator, sequenceLength, maxSendAddress

    def save(self):
        if self.item and self.item.uuid == self.message['uuid']:
            self.item.sent = datetime.datetime.utcnow()
            logger.debug('Custom Resend ' + self.item.raw)
        else:
            self.item = Other(uuid=self.message['uuid'], rpt=self.message['message'] ,raw=self.generator.toJson())
            logger.debug('Custom Send ' + self.item.raw)

        db.add(self.item)
        db.commit()
        self.sendSignal.emit()
