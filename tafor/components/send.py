import datetime

from PyQt5.QtGui import QFontMetrics, QFont, QPixmap
from PyQt5.QtCore import QCoreApplication, QTimer, QSize, Qt, pyqtSignal
from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QMessageBox, QTextEdit, QLabel
from PyQt5.QtPrintSupport import QPrintDialog, QPrinter

from tafor import conf, logger
from tafor.states import context
from tafor.models import db
from tafor.utils import boolean, TafParser, MetarParser, SigmetParser, AFTNMessageGenerator, FileMessageGenerator, AFTNDecoder
from tafor.utils.thread import SerialThread, FtpThread
from tafor.components.ui import Ui_send, main_rc


class AFTNChannel(object):
    generator = AFTNMessageGenerator
    thread = SerialThread
    sequenceConfigPath = 'Communication/ChannelSequenceNumber'

    @staticmethod
    def successText():
        return QCoreApplication.translate('Sender', 'Data has been sent to the serial port')

    @staticmethod
    def resendText():
        return QCoreApplication.translate('Sender', 'Some part of the AFTN message may be updated, do you still want to resend?')


class FtpChannel(object):
    generator = FileMessageGenerator
    thread = FtpThread
    sequenceConfigPath = 'Communication/FileSequenceNumber'

    @staticmethod
    def successText():
        return QCoreApplication.translate('Sender', 'File has been uploaded to the host')

    @staticmethod
    def resendText():
        return QCoreApplication.translate('Sender', 'The file will be resent, do you want to continue?')


class BaseSender(QDialog, Ui_send.Ui_Sender):

    succeeded = pyqtSignal()

    def __init__(self, parent=None):
        super(BaseSender, self).__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self.parent = parent
        self.generator = None
        self.parser = None
        self.message = None
        self.error = None
        self.mode = 'send'

        self.sendButton = self.buttonBox.button(QDialogButtonBox.Ok)
        self.resendButton = self.buttonBox.button(QDialogButtonBox.Retry)
        self.cancelButton = self.buttonBox.button(QDialogButtonBox.Cancel)
        self.printButton = self.buttonBox.button(QDialogButtonBox.Reset)

        self.sendButton.setText(QCoreApplication.translate('Sender', 'Send'))
        self.resendButton.setText(QCoreApplication.translate('Sender', 'Resend'))
        self.cancelButton.setText(QCoreApplication.translate('Sender', 'Cancel'))
        self.printButton.setText(QCoreApplication.translate('Sender', 'Print'))

        self.buttonBox.accepted.connect(self.send)
        self.printButton.clicked.connect(self.print)
        self.cancelButton.clicked.connect(self.cancel)
        self.succeeded.connect(self.updateSequenceNumber)

        self.rawGroup.hide()
        self.printButton.hide()
        self.resendButton.hide()

        # self.text.setStyleSheet('font-size: 13px;')
        # self.raw.setStyleSheet('font-size: 13px; background-color: rgb(0, 0, 0); color: rgb(255, 255, 255);')

        self.updateProtocolIcon()

    def protocol(self):
        text = conf.value('General/CommunicationLine')
        return text.lower() if text else 'aftn'

    def channel(self):
        if self.protocol() == 'ftp':
            return FtpChannel
        else:
            return AFTNChannel

    def updateMode(self):
        """
        this method only update when receive message object
        """
        if self.message and self.message.id:
            self.mode = 'view'
        else:
            self.mode = 'send'

    def updateProtocolIcon(self):
        pixmap = QPixmap(':/{}.png'.format(self.protocol()))
        if hasattr(self, 'protocolSign'):
            self.protocolSign.setPixmap(pixmap)
        else:
            self.protocolSign = QLabel(self)
            self.protocolSign.setPixmap(pixmap)
            self.protocolSign.setMask(pixmap.mask())
            self.protocolSign.adjustSize()
            self.protocolSign.move(688, 2)

        visible = self.sendButton.isVisible() or self.resendButton.isVisible()
        self.protocolSign.setVisible(visible)

    def updateContent(self):
        if self.mode == 'view':
            self.sendButton.hide()
            self.setWindowTitle(QCoreApplication.translate('Sender', 'View Message'))
            self.rawGroup.setTitle(QCoreApplication.translate('Sender', 'Raw Data'))

            text = self.message.rawText()
            self.raw.setText(text)

            if not self.message.confirmed and datetime.datetime.utcnow() - self.message.sent < datetime.timedelta(hours=2):
                # enable resend button
                self.resendButton.show()

            if text:
                self.rawGroup.show()
                self.printButton.show()

        if self.mode == 'send':
            self.setWindowTitle(QCoreApplication.translate('Sender', 'Send Message'))
            self.rawGroup.setTitle(self.channel().successText())

    def receive(self, message):
        self.message = message
        self.parse()
        self.updateMode()
        self.updateContent()

    def parse(self):
        visHas5000 = boolean(conf.value('Validator/VisHas5000'))
        cloudHeightHas450 = boolean(conf.value('Validator/CloudHeightHas450'))
        weakPrecipitationVerification = boolean(conf.value('Validator/WeakPrecipitationVerification'))

        self.parser = TafParser(self.message.text,
            visHas5000=visHas5000, cloudHeightHas450=cloudHeightHas450, weakPrecipitationVerification=weakPrecipitationVerification)
        self.parser.validate()

        if self.parser.hasMessageChanged():
            self.message.text = self.parser.renderer()

        html = self.parser.renderer(style='html')
        if self.message.heading is None:
            html = '<p>{}</p>'.format(html)
        else:
            html = '<p>{}<br/>{}</p>'.format(self.message.heading, html)
        if self.parser.tips:
            html += '<p style="color: grey"># {}</p>'.format('<br/># '.join(self.parser.tips))

        self.text.setHtml(html)
        self.resizeText()

    def setRawGroup(self, rawText, error=''):
        if rawText is None:
            return None

        self.raw.setText(rawText)
        self.rawGroup.show()
        self.printButton.show()
        self.sendButton.hide()
        self.resendButton.hide()

        if error:
            self.error = error
            self.rawGroup.setTitle(QCoreApplication.translate('Sender', 'Send Failed'))

            if context.environ.hasPermission(self.reportType):
                self.resendButton.setEnabled(True)
                self.resendButton.setText(QCoreApplication.translate('Sender', 'Resend'))
                self.resendButton.show()

            title = QCoreApplication.translate('Sender', 'Error')
            QMessageBox.critical(self, title, error)

    def parameters(self):
        spacer = ' ' if self.reportType == 'Trend' else '\n'
        message = spacer.join([self.message.heading, self.message.text])
        channel = conf.value('Communication/Channel') or ''
        number = conf.value(self.channel().sequenceConfigPath) or 1
        priority = 'FF' if self.reportType in ['SIGMET', 'AIRMET'] or \
            self.message.text.startswith('TAF AMD') else 'GG'
        address = conf.value('Communication/{}Address'.format(self.reportType)) or ''
        originator = conf.value('Communication/OriginatorAddress') or ''
        sequenceLength = conf.value('Communication/ChannelSequenceLength') or 4
        maxSendAddress = conf.value('Communication/MaxSendAddress') or 21

        return message, channel, number, priority, address, originator, sequenceLength, maxSendAddress

    def generateRawText(self):
        message, channel, number, priority, address, originator, sequenceLength, maxSendAddress = self.parameters()
        generator = self.channel().generator
        self.generator = generator(message, channel=channel, number=number, priority=priority, address=address,
            originator=originator, sequenceLength=sequenceLength, maxSendAddress=maxSendAddress)

        rawText = self.generator.toString()
        return rawText

    def send(self):
        if self.parser and not self.parser.isValid():
            logger.warning('Validator {}, valid status {}'.format(self.parser, self.parser.isValid()))
            title = QCoreApplication.translate('Sender', 'Validator Warning')
            text = QCoreApplication.translate('Sender', 'The message did not pass the validator, do you still want to send?')
            ret = QMessageBox.question(self, title, text)
            if ret != QMessageBox.Yes:
                return None

        if self.mode == 'view':
            title = QCoreApplication.translate('Sender', 'Resend Reminder')
            ret = QMessageBox.question(self, title, self.channel().resendText())
            if ret != QMessageBox.Yes:
                return None

        if self.protocol() != 'aftn':
            title = QCoreApplication.translate('Sender', 'Transmission Line Reminder')
            text = QCoreApplication.translate('Sender', 'Not a common transmission line, do you want to continue?')
            ret = QMessageBox.question(self, title, text)
            if ret != QMessageBox.Yes:
                return None

        self.sendButton.setEnabled(False)
        self.sendButton.setText(QCoreApplication.translate('Sender', 'Sending'))
        self.resendButton.setEnabled(False)
        self.resendButton.setText(QCoreApplication.translate('Sender', 'Sending'))

        rawText = self.generateRawText()

        if context.environ.hasPermission(self.reportType):
            thread = self.channel().thread
            self.thread = thread(rawText)
            self.thread.done.connect(lambda error: self.setRawGroup(rawText, error))
            self.thread.finished.connect(self.save)
            self.thread.start()
        else:
            error = QCoreApplication.translate('Sender', 'Limited functionality, please check the license information')
            self.setRawGroup(rawText, error=error)
            self.save()

    def save(self):
        if self.message and self.message.id:
            # resend the message
            self.message.raw = self.generator.toJson()
            self.message.protocol = self.protocol()
            self.message.sent = datetime.datetime.utcnow()
            logger.debug('Resend ' + self.message.text)
        else:
            # create the message
            self.message.raw = self.generator.toJson()
            self.message.protocol = self.protocol()
            logger.debug('Send ' + self.message.text)

        db.add(self.message)
        db.commit()
        self.succeeded.emit()

    def updateSequenceNumber(self):
        if not self.error:
            conf.setValue(self.channel().sequenceConfigPath, str(self.generator.number))

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

    def resizeText(self):
        text = self.text.toPlainText()
        font = self.text.document().defaultFont()
        fontMetrics = QFontMetrics(font)
        textSize = fontMetrics.size(0, text)
        textHeight = textSize.height() + 50
        self.text.setMaximumHeight(textHeight)

    def cancel(self):
        if self.mode == 'send':
            if (self.error or not self.sendButton.isHidden() or not self.resendButton.isHidden()):
                self.rejected.emit()
            else:
                self.accepted.emit()

        self.clear()

    def showEvent(self, event):
        self.updateProtocolIcon()

    def closeEvent(self, event):
        if event.spontaneous():
            self.cancel()

        self.clear()

    def clear(self):
        self.message = None
        self.error = None
        self.parser = None
        self.text.setText('')
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


class TrendSender(BaseSender):

    def __init__(self, parent=None):
        super(TrendSender, self).__init__(parent)
        self.reportType = 'Trend'

    def protocol(self):
        return 'aftn'

    def parse(self):
        html = self.message.text
        parser = context.notification.metar.parser()
        if parser and parser.hasMetar():
            metar = parser.primary.part
            visHas5000 = boolean(conf.value('Validator/VisHas5000'))
            cloudHeightHas450 = boolean(conf.value('Validator/CloudHeightHas450'))
            weakPrecipitationVerification = boolean(conf.value('Validator/WeakPrecipitationVerification'))

            self.parser = MetarParser(' '.join([metar, self.message.text]), ignoreMetar=True,
                visHas5000=visHas5000, cloudHeightHas450=cloudHeightHas450, weakPrecipitationVerification=weakPrecipitationVerification)
            self.parser.validate()

            if not self.parser.failed:
                html = '<p>{}</p>'.format(self.parser.renderer(style='html', emphasizeNosig=True))
                if self.parser.tips:
                    html += '<p style="color: grey"># {}</p>'.format('<br/># '.join(self.parser.tips))

        self.text.setHtml(html)
        self.resizeText()


class SigmetSender(BaseSender):

    def __init__(self, parent=None):
        super(SigmetSender, self).__init__(parent)
        self.reportType = 'SIGMET'

    def parse(self):
        if self.message.heading and self.message.heading[0:2] == 'WA' or 'AIRMET' in self.message.text.split():
            self.reportType = 'AIRMET'
        else:
            self.reportType = 'SIGMET'

        try:
            self.parser = SigmetParser(self.message.text)
            html = self.parser.renderer(style='html')
            if self.message.heading is None:
                html = '<p>{}</p>'.format(html)
            else:
                html = '<p>{}<br/>{}</p>'.format(self.message.heading, html)

            self.text.setHtml(html)
            self.resizeText()

        except Exception as e:
            logger.error(e)

    def save(self):
        super(SigmetSender, self).save()
        if not self.message.isCnl():
            delta = self.message.expired() - datetime.datetime.utcnow() - datetime.timedelta(minutes=20)
            sig = self.message.parser()
            QTimer.singleShot(delta.total_seconds() * 1000, lambda: self.parent.remindSigmet(sig))


class CustomSender(BaseSender):

    def __init__(self, parent=None):
        super(CustomSender, self).__init__(parent)
        self.textGroup.hide()
        self.reportType = 'Custom'
        self.setModal(True)
        self.setWindowTitle(QCoreApplication.translate('Sender', 'Send Custom Message'))

    def protocol(self):
        return 'aftn'

    def load(self):
        self.message = context.other.state()
        rawText = self.generateRawText()
        self.setRawGroup(rawText)
        self.protocolSign.show()
        self.sendButton.show()
        self.printButton.hide()
        self.rawGroup.setTitle(QCoreApplication.translate('Sender', 'Received Messages'))

    def parameters(self):
        message = self.message['message']
        priority = self.message['priority']
        address = self.message['address']
        channel = conf.value('Communication/Channel') or ''
        originator = conf.value('Communication/OriginatorAddress') or ''
        number = conf.value(self.channel().sequenceConfigPath) or 1
        sequenceLength = conf.value('Communication/ChannelSequenceLength') or 4
        maxSendAddress = conf.value('Communication/MaxSendAddress') or 21

        return message, channel, number, priority, address, originator, sequenceLength, maxSendAddress
