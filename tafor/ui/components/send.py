import logging
import datetime

from itertools import cycle

from PyQt5.QtGui import QFontMetrics, QPixmap, QIcon
from PyQt5.QtCore import QCoreApplication, QSize, Qt, pyqtSignal
from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QMessageBox, QTextEdit, QLabel, QToolButton
from PyQt5.QtPrintSupport import QPrintDialog, QPrinter

from tafor.core.models import Other, db
from tafor.core.parsers.metar import MetarParser
from tafor.core.parsers.sigmet import SigmetParser
from tafor.core.parsers.taf import TafParser
from tafor.core.telegram.generator import AFTNDecoder, AFTNMessageGenerator, FileMessageGenerator
from tafor.core.utils.thread import FtpWorker, SerialWorker, threadManager
from tafor.ui.qt import Ui_send, main_rc
from tafor.ui.widgets.graphic import GraphicsViewer

logger = logging.getLogger('tafor.send')


class BaseChannel(object):
    generator = None
    worker = None
    configName = None

    def __init__(self, conf, context):
        self.conf = conf
        self.context = context

    def buildText(self, message, reportType):
        if reportType == 'Custom':
            return self.context.other.message

        spacer = ' ' if reportType == 'Trend' else '\n'
        return spacer.join([message.heading, message.text])

    def buildParams(self, message, reportType):
        raise NotImplementedError

    def workerParams(self, parser=None):
        return {}

    def generateRawText(self, message, reportType):
        generator = self.generator(**self.buildParams(message, reportType))
        return generator, generator.toString()

    def successText(self):
        raise NotImplementedError

    def resendText(self):
        raise NotImplementedError


class AFTNChannel(BaseChannel):
    generator = AFTNMessageGenerator
    worker = SerialWorker
    configName = 'channelSequenceNumber'

    def successText(self):
        return QCoreApplication.translate('Sender', 'Data has been sent to the serial port')

    def resendText(self):
        return QCoreApplication.translate('Sender', 'Some part of the AFTN message may be updated, do you still want to resend?')

    def buildParams(self, message, reportType):
        if reportType == 'Custom':
            return {
                'text': self.context.other.message,
                'channel': self.conf.channel,
                'number': self.conf.get(self.configName),
                'priority': self.context.other.priority,
                'address': self.context.other.address,
                'originator': self.conf.originatorAddress,
                'sequenceLength': self.conf.channelSequenceLength,
                'maxSendAddress': self.conf.maxSendAddress,
            }

        priority = 'FF' if reportType in ['SIGMET', 'AIRMET'] or message.text.startswith('TAF AMD') else 'GG'
        address = self.conf.get(f'{reportType.lower()}Address')

        return {
            'text': self.buildText(message, reportType),
            'channel': self.conf.channel,
            'number': self.conf.get(self.configName),
            'priority': priority,
            'address': address,
            'originator': self.conf.originatorAddress,
            'sequenceLength': self.conf.channelSequenceLength or 4,
            'maxSendAddress': self.conf.maxSendAddress or 21,
        }


class FileChannel(BaseChannel):
    generator = FileMessageGenerator
    worker = FtpWorker
    configName = 'fileSequenceNumber'

    def successText(self):
        return QCoreApplication.translate('Sender', 'File has been uploaded to the host')

    def resendText(self):
        return QCoreApplication.translate('Sender', 'The file will be resent, do you want to continue?')

    def buildParams(self, message, reportType):
        return {
            'text': self.buildText(message, reportType),
            'number': self.conf.get(self.configName),
        }

    def workerParams(self, parser=None):
        return {
            'valids': getattr(parser, 'valids', None),
        }


class ComposedMessage:
    def __init__(self, message, parser=None, html='', reportType=None, geo=None):
        self.message = message
        self.parser = parser
        self.html = html
        self.reportType = reportType
        self.geo = geo


class SenderViewState:
    def __init__(self, mode, windowTitle, rawGroupTitle, rawText='', resendVisible=False):
        self.mode = mode
        self.windowTitle = windowTitle
        self.rawGroupTitle = rawGroupTitle
        self.rawText = rawText
        self.resendVisible = resendVisible


class MessageComposer:
    def __init__(self, conf, context):
        self.conf = conf
        self.context = context

    def compose(self, message):
        return ComposedMessage(message)


class TafMessageComposer(MessageComposer):
    def compose(self, message):
        visHas5000 = self.conf.visHas5000
        cloudHeightHas450 = self.conf.cloudHeightHas450
        weakPrecipitationVerification = self.conf.weakPrecipitationVerification
        uiFamily = self.context.resource.uiFont().family()

        parser = TafParser(
            message.text,
            created=message.created,
            visHas5000=visHas5000,
            cloudHeightHas450=cloudHeightHas450,
            weakPrecipitationVerification=weakPrecipitationVerification,
        )
        parser.validate()

        if parser.hasMessageChanged():
            message.text = parser.renderer()

        html = parser.renderer(style='html')
        if message.heading is None:
            html = '<p>{}</p>'.format(html)
        else:
            html = '<p>{}<br/>{}</p>'.format(message.heading, html)

        if parser.tips:
            html += '<p style="color: grey; font-family: \'{}\'; font-size: 10pt;"># {}</p>'.format(
                uiFamily, '<br/># '.join(parser.tips)
            )

        return ComposedMessage(message, parser=parser, html=html)


class TrendMessageComposer(MessageComposer):
    def compose(self, message):
        html = message.text
        parser = None
        uiFamily = self.context.resource.uiFont().family()
        notificationParser = self.context.notification.metar.parser()

        if notificationParser and notificationParser.hasMetar():
            metar = notificationParser.primary.part
            visHas5000 = self.conf.visHas5000
            cloudHeightHas450 = self.conf.cloudHeightHas450
            weakPrecipitationVerification = self.conf.weakPrecipitationVerification

            parser = MetarParser(
                ' '.join([metar, message.text]),
                ignoreMetar=True,
                visHas5000=visHas5000,
                cloudHeightHas450=cloudHeightHas450,
                weakPrecipitationVerification=weakPrecipitationVerification,
            )
            parser.validate()

            if not parser.failed:
                html = '<p>{}</p>'.format(parser.renderer(style='html', emphasizeNosig=True))
                if parser.tips:
                    html += '<p style="color: grey; font-family: \'{}\'; font-size: 10pt;"># {}</p>'.format(
                        uiFamily, '<br/># '.join(parser.tips)
                    )

        return ComposedMessage(message, parser=parser, html=html)


class SigmetMessageComposer(MessageComposer):
    def compose(self, message):
        reportType = 'AIRMET' if (message.heading and message.heading[0:2] == 'WA') or 'AIRMET' in message.text.split() else 'SIGMET'

        try:
            parser = SigmetParser(message.text, created=message.created)
            html = parser.renderer(style='html')
            if message.heading is None:
                html = '<p>{}</p>'.format(html)
            else:
                html = '<p>{}<br/>{}</p>'.format(message.heading, html)

            geo = None
            if not message.isCnl():
                geo = parser.geo(self.context.layer.boundaries(), trim=True)

            return ComposedMessage(message, parser=parser, html=html, reportType=reportType, geo=geo)
        except Exception as e:
            logger.error('Sender parse SIGMET failed, {}, {}'.format(message.text, e))
            return ComposedMessage(message, reportType=reportType)


class CustomMessageComposer(MessageComposer):
    pass


def createComposer(reportType, conf, context):
    mapping = {
        'TAF': TafMessageComposer,
        'Trend': TrendMessageComposer,
        'SIGMET': SigmetMessageComposer,
        'AIRMET': SigmetMessageComposer,
        'Custom': CustomMessageComposer,
    }
    try:
        return mapping[reportType](conf, context)
    except KeyError:
        raise ValueError(f'Unsupported report type: {reportType}')


class TransportService:
    def __init__(self, conf, context):
        self.conf = conf
        self.context = context

    def channel(self, protocol):
        if protocol == 'ftp':
            return FileChannel(self.conf, self.context)
        return AFTNChannel(self.conf, self.context)

    def generateRawText(self, message, reportType, protocol):
        return self.channel(protocol).generateRawText(message, reportType)

    def transmit(self, protocol, parser, rawText, done, finished):
        channel = self.channel(protocol)
        worker, thread = threadManager.createWorker(channel.worker, rawText, **channel.workerParams(parser))
        worker.done.connect(done)
        worker.finished.connect(finished)
        thread.start()


class SenderPresenter:
    def __init__(self, view, context, conf):
        self.view = view
        self.context = context
        self.conf = conf
        self.composer = createComposer(view.reportType, conf, context)
        self.transportService = TransportService(conf, context)
        self.resetGroupCycle()

    def protocol(self):
        return self.view.protocol()

    def channel(self):
        return self.transportService.channel(self.protocol())

    def resetGroupCycle(self):
        groups = ['canvas', 'raw'] if self.view.hasCanvasGroup else ['raw']
        self.groupNames = cycle(groups)

    def nextGroupName(self):
        return next(self.groupNames)

    def receive(self, message):
        self.view.message = message
        self.compose()
        self.view.renderContent(self.buildViewState())
        self.updateVisibility()

    def buildViewState(self):
        isViewMode = bool(self.view.message and self.view.message.id)
        mode = 'view' if isViewMode else 'send'
        resendVisible = False
        rawText = ''

        if isViewMode:
            windowTitle = QCoreApplication.translate('Sender', 'View Message')
            rawGroupTitle = QCoreApplication.translate('Sender', 'Raw Data')
            rawText = self.view.message.rawText()
            resendVisible = (
                not self.view.message.confirmed and
                datetime.datetime.utcnow() - self.view.message.created < datetime.timedelta(hours=2)
            )
        else:
            windowTitle = QCoreApplication.translate('Sender', 'Send Message')
            rawGroupTitle = self.channel().successText()

        return SenderViewState(
            mode=mode,
            windowTitle=windowTitle,
            rawGroupTitle=rawGroupTitle,
            rawText=rawText,
            resendVisible=resendVisible,
        )

    def compose(self):
        result = self.composer.compose(self.view.message)
        self.view.message = result.message
        self.view.parser = result.parser

        if result.reportType:
            self.view.reportType = result.reportType

        if result.html:
            self.view.text.setHtml(result.html)
            self.view.resizeText()

        if hasattr(self.view, 'graphic'):
            if result.geo:
                self.view.graphic.setSigmet(result.geo)
            else:
                self.view.graphic.clear()

    def generateRawText(self):
        generator, rawText = self.transportService.generateRawText(
            self.view.message, self.view.reportType, self.protocol()
        )
        self.view.generator = generator
        return rawText

    def send(self):
        if self.view.parser and not self.view.parser.isValid():
            logger.warning('Validator {}, valid status {}'.format(self.view.parser, self.view.parser.isValid()))
            title = QCoreApplication.translate('Sender', 'Validator Warning')
            text = QCoreApplication.translate('Sender', 'The message did not pass the validator, do you still want to send?')
            ret = QMessageBox.question(self.view, title, text)
            if ret != QMessageBox.Yes:
                return None

        if self.view.mode == 'view':
            title = QCoreApplication.translate('Sender', 'Resend Reminder')
            ret = QMessageBox.question(self.view, title, self.channel().resendText())
            if ret != QMessageBox.Yes:
                return None

        if self.protocol() != 'aftn':
            title = QCoreApplication.translate('Sender', 'Transmission Line Reminder')
            text = QCoreApplication.translate('Sender', 'Not a common transmission line, do you want to continue?')
            ret = QMessageBox.question(self.view, title, text)
            if ret != QMessageBox.Yes:
                return None

        self.view.sendButton.setEnabled(False)
        self.view.sendButton.setText(QCoreApplication.translate('Sender', 'Sending'))
        self.view.resendButton.setEnabled(False)
        self.view.resendButton.setText(QCoreApplication.translate('Sender', 'Sending'))

        rawText = self.generateRawText()

        if self.context.license.hasPermission(self.view.reportType):
            self.transportService.transmit(
                self.protocol(),
                self.view.parser,
                rawText,
                done=lambda error: self.view.setRawGroup(rawText, error),
                finished=self.save,
            )
        else:
            error = QCoreApplication.translate('Sender', 'Limited functionality, please check the license information')
            self.view.setRawGroup(rawText, error=error)
            self.save()

    def save(self):
        if self.view.message and self.view.message.id:
            self.view.message.raw = self.view.generator.toJson()
            self.view.message.protocol = self.protocol()
            self.view.message.created = datetime.datetime.utcnow()
            logger.debug('Resend {}'.format(self.view.message.text))
        else:
            self.view.message.raw = self.view.generator.toJson()
            self.view.message.protocol = self.protocol()
            logger.debug('Send {}'.format(self.view.message.text))

        with db.session() as session:
            session.add(self.view.message)

        self.view.succeeded.emit(True)

    def updateSequenceNumber(self, succeeded=True):
        if succeeded and not self.view.error:
            self.conf.set(self.channel().configName, str(self.view.generator.number))

    def handleSucceeded(self, succeeded=True):
        self.updateSequenceNumber(succeeded)
        if succeeded and isinstance(self.view, SigmetSender):
            self.updateReminder()
        self.updateVisibility(succeeded)

    def updateReminder(self):
        sig = self.view.message.parser()
        if self.view.message.isCnl():
            cancelSequence = sig.cancelSequence()
            states = self.context.sigmet.entries
            for uuid, value in states.items():
                parser = value['text']
                sequence = parser.sequence(), parser.validTime()
                if cancelSequence == sequence:
                    self.context.sigmet.remove(uuid=uuid)
        else:
            time = self.view.message.expired()
            self.context.sigmet.add(uuid=self.view.message.uuid, text=sig, time=time)

    def reload(self):
        if self.view.isVisible() and self.view.message:
            self.compose()

    def load(self):
        self.view.clear()
        self.view.message = Other(uuid=self.context.other.uuid, text=self.context.other.message, source='api')
        rawText = self.generateRawText()
        self.view.setRawGroup(rawText)
        self.view.rawGroup.show()
        self.view.protocolSign.show()
        self.view.sendButton.show()
        self.view.printButton.hide()
        self.view.rawGroup.setTitle(QCoreApplication.translate('Sender', 'Received Messages'))

    def groupState(self, succeeded=False):
        if not self.view.message:
            return None

        if self.view.hasCanvasGroup:
            group = self.nextGroupName()

            if (self.view.message.isCnl() or succeeded) and group == 'canvas':
                group = self.nextGroupName()

            if not self.view.message.raw and group == 'raw':
                group = self.nextGroupName()

            if not self.view.message.raw and self.view.message.isCnl():
                return None

            return group

        if self.view.message.rawText():
            return 'raw'

        return None

    def updateVisibility(self, succeeded=False):
        group = self.groupState(succeeded)
        self.view.group = group

        if self.view.hasCanvasGroup:
            self.view.renderCanvasRawGroup(group)
            return

        self.view.renderRawGroup(group)


class BaseSender(QDialog, Ui_send.Ui_Sender):
    reportType = ''
    fixedProtocol = None
    hasCanvasGroup = False

    closed = pyqtSignal()
    backed = pyqtSignal()
    succeeded = pyqtSignal(bool)

    def __init__(self, parent=None, context=None, conf=None):
        super(BaseSender, self).__init__(parent)
        self.context = context
        self.conf = conf
        self.setupUi(self)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self.generator = None
        self.parser = None
        self.message = None
        self.error = None
        self.mode = 'send'
        self.group = None

        self.sendButton = self.buttonBox.button(QDialogButtonBox.Ok)
        self.resendButton = self.buttonBox.button(QDialogButtonBox.Retry)
        self.cancelButton = self.buttonBox.button(QDialogButtonBox.Cancel)
        self.printButton = self.buttonBox.button(QDialogButtonBox.Reset)

        self.switchButton = QToolButton(self)
        self.switchButton.setText('Switch')
        self.switchButton.setFixedSize(26, 26)
        self.switchButton.setIconSize(QSize(20, 20))
        self.switchButton.setAutoRaise(True)

        self.sendButton.setText(QCoreApplication.translate('Sender', 'Send'))
        self.resendButton.setText(QCoreApplication.translate('Sender', 'Resend'))
        self.cancelButton.setText(QCoreApplication.translate('Sender', 'Cancel'))
        self.printButton.setText(QCoreApplication.translate('Sender', 'Print'))

        self.presenter = SenderPresenter(self, self.context, self.conf)

        self.buttonBox.accepted.connect(self.presenter.send)
        self.printButton.clicked.connect(self.print)
        self.cancelButton.clicked.connect(self.cancel)
        self.succeeded.connect(self.presenter.handleSucceeded)

        self.rawGroup.hide()
        self.canvasGroup.hide()
        self.printButton.hide()
        self.resendButton.hide()
        self.switchButton.hide()

        font = self.context.resource.fixedFont()
        font.setPointSize(11)
        self.text.setFont(font)
        self.raw.setFont(font)

        self.updateProtocolIcon()

    def protocol(self):
        text = self.fixedProtocol or self.conf.communicationProtocol
        return text.lower() if text else 'aftn'

    def channel(self):
        return self.presenter.channel()

    def updateProtocolIcon(self):
        pixmap = QPixmap(':/{}.png'.format(self.protocol()))
        if hasattr(self, 'protocolSign'):
            self.protocolSign.setPixmap(pixmap)
        else:
            self.protocolSign = QLabel(self)
            self.protocolSign.setPixmap(pixmap)
            self.protocolSign.setMask(pixmap.mask())
            self.protocolSign.adjustSize()
            self.protocolSign.move(self.width() - 100, 3)

        visible = self.sendButton.isVisible() or self.resendButton.isVisible()
        self.protocolSign.setVisible(visible)

    def renderContent(self, state):
        self.mode = state.mode
        self.setWindowTitle(state.windowTitle)
        self.rawGroup.setTitle(state.rawGroupTitle)
        self.raw.setText(state.rawText)

        if state.mode == 'view':
            self.sendButton.hide()
        else:
            self.sendButton.show()

        self.resendButton.setVisible(state.resendVisible)

    def renderRawGroup(self, group):
        if group == 'raw':
            self.rawGroup.show()
            self.printButton.show()

        if group is None:
            self.rawGroup.hide()
            self.printButton.hide()

    def receive(self, message):
        self.presenter.receive(message)

    def setRawGroup(self, rawText, error=''):
        if rawText is None:
            return None

        self.raw.setText(rawText)
        self.group = self.presenter.nextGroupName()
        self.printButton.show()
        self.sendButton.hide()
        self.resendButton.hide()

        if error:
            self.error = error
            self.rawGroup.setTitle(QCoreApplication.translate('Sender', 'Send Failed'))

            if self.context.license.hasPermission(self.reportType):
                self.resendButton.setEnabled(True)
                self.resendButton.setText(QCoreApplication.translate('Sender', 'Resend'))
                self.resendButton.show()

            title = QCoreApplication.translate('Sender', 'Error')
            QMessageBox.critical(self, title, error)

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
        aftn = AFTNDecoder(self.message.raw)
        texts = [priority, aftn.priority, address, aftn.address, originator, aftn.originator,
            content, self.message.report, raw, self.message.rawText(), time, '{} UTC'.format(self.message.created)]

        elements = []
        for title, content in zip(texts[::2], texts[1::2]):
            content = '<br>'.join(content.split('\n'))
            text = '<p><b>{}</b><br>{}</p>'.format(title, content)
            elements.append(text)

        font = self.context.resource.fixedFont()
        font.setPointSize(10)
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
                self.backed.emit()
            else:
                self.closed.emit()

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
        self.group = None
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
    reportType = 'TAF'


class TrendSender(BaseSender):
    reportType = 'Trend'
    fixedProtocol = 'aftn'

    def __init__(self, parent=None, context=None, conf=None):
        super(TrendSender, self).__init__(parent, context, conf)
        self.context.event.trendReloadRequested.connect(self.presenter.reload)


class SigmetSender(BaseSender):
    reportType = 'SIGMET'
    hasCanvasGroup = True

    def __init__(self, parent=None, context=None, conf=None):
        super(SigmetSender, self).__init__(parent, context, conf)
        self.graphic = GraphicsViewer(self)
        self.canvasLayout.addWidget(self.graphic)
        self.switchButton.clicked.connect(self.presenter.updateVisibility)

    def renderCanvasRawGroup(self, group):
        if group is None:
            self.rawGroup.hide()
            self.canvasGroup.hide()

        if group == 'canvas':
            self.rawGroup.hide()
            self.canvasGroup.show()

        if group == 'raw':
            self.rawGroup.show()
            self.canvasGroup.hide()

        if not self.message.raw or self.message.isCnl():
            self.switchButton.hide()
        else:
            if group == 'canvas':
                icon = ':/words.png'
            else:
                icon = ':/map.png'

            self.switchButton.setIcon(QIcon(icon))
            self.switchButton.show()

        if self.message.raw:
            self.printButton.show()
        else:
            self.printButton.hide()

    def resizeEvent(self, event):
        self.switchButton.move(self.width() - 70, self.textGroup.height() + 50)
        super(SigmetSender, self).resizeEvent(event)

    def clear(self):
        super().clear()
        self.presenter.resetGroupCycle()


class CustomSender(BaseSender):
    reportType = 'Custom'
    fixedProtocol = 'aftn'

    def __init__(self, parent=None, context=None, conf=None):
        super(CustomSender, self).__init__(parent, context, conf)
        self.textGroup.hide()
        self.setModal(True)
        self.setWindowTitle(QCoreApplication.translate('Sender', 'Send Custom Message'))
