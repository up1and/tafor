import logging

from PyQt5.QtGui import QFontMetrics, QIcon, QPixmap
from PyQt5.QtCore import QCoreApplication, QSize, Qt, pyqtSignal
from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QMessageBox, QTextEdit, QLabel, QToolButton
from PyQt5.QtPrintSupport import QPrintDialog, QPrinter

from tafor.core.parsers.metar import MetarParser
from tafor.core.parsers.sigmet import SigmetParser
from tafor.core.parsers.taf import TafParser
from tafor.core.telegram.channels import canResend, createChannel
from tafor.core.telegram.generator import AFTNDecoder
from tafor.core.utils.common import iconPath
from tafor.core.utils.time import utcnow
from tafor.ui.fonts import fixedFont, uiFont
from tafor.ui.qt import Ui_send
from tafor.ui.widgets.graphic import PreviewPanel
from tafor.ui.workers import Job

logger = logging.getLogger('tafor.send')


class ComposedMessage:
    """Composer product for the current message: the validation result, the
    preview html and the optional SIGMET geographic shape."""

    def __init__(self, message, parser=None, html='', geo=None):
        self.message = message
        self.parser = parser
        self.html = html
        self.geo = geo


class MessageComposer:

    def __init__(self, conf, context, fontFamily='monospace'):
        self.conf = conf
        self.context = context
        self.fontFamily = fontFamily

    def compose(self, message):
        return ComposedMessage(message)


class TafMessageComposer(MessageComposer):

    def compose(self, message):
        visHas5000 = self.conf.visHas5000
        cloudHeightHas450 = self.conf.cloudHeightHas450
        weakPrecipitationVerification = self.conf.weakPrecipitationVerification
        uiFamily = self.fontFamily

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
        uiFamily = self.fontFamily
        notificationParser = self.context.notification.metar.parser()

        if notificationParser and notificationParser.hasTrend():
            metar = notificationParser.primary.part
            parser = MetarParser(
                ' '.join([metar, message.text]),
                trendOnly=True,
                visHas5000=self.conf.visHas5000,
                cloudHeightHas450=self.conf.cloudHeightHas450,
                weakPrecipitationVerification=self.conf.weakPrecipitationVerification,
            )
            parser.validate()

            if not parser.error:
                html = '<p>{}</p>'.format(parser.renderer(style='html'))
                if parser.tips:
                    html += '<p style="color: grey; font-family: \'{}\'; font-size: 10pt;"># {}</p>'.format(
                        uiFamily, '<br/># '.join(parser.tips)
                    )

        return ComposedMessage(message, parser=parser, html=html)


class SigmetMessageComposer(MessageComposer):

    def compose(self, message):
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

            return ComposedMessage(message, parser=parser, html=html, geo=geo)
        except Exception as e:
            logger.error('Sender parse SIGMET failed, {}, {}'.format(message.text, e))
            return ComposedMessage(message)


class CustomMessageComposer(MessageComposer):
    pass


def createComposer(category, conf, context, fontFamily='monospace'):
    mapping = {
        'TAF': TafMessageComposer,
        'TREND': TrendMessageComposer,
        'SIGMET': SigmetMessageComposer,
        'AIRMET': SigmetMessageComposer,
        'CUSTOM': CustomMessageComposer,
    }
    try:
        return mapping[category](conf, context, fontFamily)
    except KeyError:
        raise ValueError(f'Unsupported report type: {category}')


class Line:
    """The current communication line: protocol and telegraph generation.
    Transmission itself is the TransmissionQueue's job"""

    def __init__(self, conf, pinned=None):
        self.conf = conf
        self.pinned = pinned

    @property
    def protocol(self):
        if self.pinned:
            return self.pinned

        text = self.conf.communicationProtocol
        return text.lower() if text else 'aftn'

    @property
    def channel(self):
        return createChannel(self.protocol, self.conf)

    def generate(self, message):
        """Build the telegraph; custom messages carry their own transient
        addressing"""
        return self.channel.generate(
            message,
            priority=getattr(message, 'priority', None),
            address=getattr(message, 'address', None),
        )


class Session:
    """One message session, the only mutable business state. Loading a new
    message replaces the whole object (self-healing); object identity guards
    against stale transmission results."""

    def __init__(self, message, mode, line):
        self.message = message
        self.mode = mode            # 'send' | 'review' | 'custom', frozen at load
        self.line = line
        self.phase = 'ready'        # ready → sending → sent | failed
        self.composed = None        # ComposedMessage, set at load
        self.telegraph = None       # generator, set by custom load / settle display
        self.job = None             # the queued transmission, set by send()
        self.clicked = None         # 'send' | 'resend', which action is in flight
        self.pane = None            # 'canvas' | 'telegraph' | None, SIGMET display focus


class Situation:
    """Flat projection of what the dialog should display. Every stored field
    is a final render decision computed by the presenter; the view applies it
    blindly and derives nothing. A few decisions are plain restatements of a
    stored one (the visible pane, the badge following the action) and appear
    as properties. title = None means leave the current title untouched (the
    custom sender's fixed window title)."""

    def __init__(self, title=None, previewVisible=True, html='', geo=None,
                 pane=None, telegraphTitle='', telegraphText='',
                 action='send', busy=False, printVisible=False,
                 switchVisible=False, badgeProtocol='aftn'):
        self.title = title
        self.previewVisible = previewVisible
        self.html = html
        self.geo = geo
        self.pane = pane            # 'canvas' | 'telegraph' | None, the resolved visible pane
        self.telegraphTitle = telegraphTitle
        self.telegraphText = telegraphText
        self.action = action       # 'send' | 'resend' | None, which action button this frame offers
        self.busy = busy
        self.printVisible = printVisible
        self.switchVisible = switchVisible
        self.badgeProtocol = badgeProtocol

    @property
    def canvasVisible(self):
        return self.pane == 'canvas'

    @property
    def telegraphVisible(self):
        return self.pane == 'telegraph'

    @property
    def badgeVisible(self):
        return self.action is not None


class SenderPresenter:

    def __init__(self, view, context, conf, repository=None):
        self.view = view
        self.context = context
        self.conf = conf
        self.repository = repository
        self.session = None

    def receive(self, message):
        """Entry for editor-composed and historical messages"""
        mode = 'review' if (message and message.id) else 'send'
        session = Session(message, mode, self.createLine())
        session.composed = self.compose(message)

        if session.composed.geo is not None:
            session.pane = 'canvas'

        self.session = session
        self.view.render()

    def load(self, message):
        """Entry for custom messages arriving over RPC"""
        session = Session(message, 'custom', self.createLine())
        session.composed = self.compose(message)
        session.telegraph = session.line.generate(message)
        self.session = session
        self.view.render()

    def createLine(self):
        return Line(self.conf, pinned=self.view.pinnedProtocol)

    def compose(self, message):
        composer = createComposer(message.category, self.conf, self.context, uiFont().family())
        return composer.compose(message)

    def situation(self):
        """Map the session onto the flat render projection — the single
        place where state becomes pixels. Built by assigning deviations onto
        the cleared default Situation."""
        state = Situation()
        session = self.session
        if session is None:
            return state                        # the cleared display

        message = session.message
        sending = session.phase == 'sending'
        hasTelegram = bool(message.raw or (session.telegraph and not sending))

        state.previewVisible = session.mode != 'custom'
        state.html = session.composed.html
        state.geo = session.composed.geo

        if session.mode == 'review':
            state.title = QCoreApplication.translate('Sender', 'View Message')
        elif session.mode == 'custom':
            state.title = None                  # keep the fixed custom title
        else:
            state.title = QCoreApplication.translate('Sender', 'Send Message')

        # The transmission outcome outranks the session kind
        if session.phase == 'failed':
            state.telegraphTitle = QCoreApplication.translate('Sender', 'Send Failed')
        elif session.phase == 'sent':
            if session.line.protocol == 'ftp':
                state.telegraphTitle = QCoreApplication.translate('Sender', 'File has been uploaded to the host')
            else:
                state.telegraphTitle = QCoreApplication.translate('Sender', 'Data has been sent to the serial port')
        elif session.mode == 'custom':
            state.telegraphTitle = QCoreApplication.translate('Sender', 'Received Messages')
        else:
            state.telegraphTitle = QCoreApplication.translate('Sender', 'Raw Data')

        if self.view.graphic is not None and session.pane == 'canvas' and session.composed.geo is not None:
            state.pane = 'canvas'
        elif hasTelegram:
            state.pane = 'telegraph'

        state.telegraphText = session.telegraph.toString() if session.telegraph else message.rawText()
        state.action = self.action(session)
        state.busy = sending
        state.printVisible = bool(message.raw)
        state.switchVisible = self.view.graphic is not None and hasTelegram and not message.isCnl()
        state.badgeProtocol = session.line.protocol
        return state

    def action(self, session):
        """The currently visible action button: None | 'send' | 'resend'"""
        if session.phase == 'sent':
            return None

        if session.phase == 'sending':
            return session.clicked

        if session.phase == 'failed':
            licensed = self.context.license.hasPermission(session.message.category)
            return 'resend' if licensed else None

        if session.mode == 'review':
            eligible = canResend(session.message, utcnow())
            return 'resend' if eligible else None

        return 'send'

    def send(self):
        """The Send and Resend buttons share this entry"""
        session = self.session
        if session is None or session.phase in ('sending', 'sent'):
            return

        if not self.confirmations(session):
            return

        session.clicked = self.action(session)
        session.phase = 'sending'
        self.view.render()

        # License before submit: a refused message never enters the queue,
        # so it is never archived either
        if not self.context.license.hasPermission(session.message.category):
            session.phase = 'failed'
            self.view.showError(QCoreApplication.translate('Sender', 'Limited functionality, please check the license information'))
            self.view.render()
            return

        parser = session.composed.parser if session.composed else None
        job = Job(session.message, session.line, parser=parser, settle=self.settle)
        session.job = job
        self.context.transmission.submit(job)

    def confirmations(self, session):
        """Pre-send confirmations, checked in order; the first refusal aborts
        with the UI untouched"""
        if session.composed.parser and not session.composed.parser.isValid():
            logger.warning('Validator {}, valid status {}'.format(session.composed.parser, session.composed.parser.isValid()))
            title = QCoreApplication.translate('Sender', 'Validator Warning')
            text = QCoreApplication.translate('Sender', 'The message did not pass the validator, do you still want to send?')
            if not self.view.confirm(title, text):
                return False

        if session.mode == 'review':
            title = QCoreApplication.translate('Sender', 'Resend Reminder')
            if session.line.protocol == 'ftp':
                text = QCoreApplication.translate('Sender', 'The file will be resent, do you want to continue?')
            else:
                text = QCoreApplication.translate('Sender', 'Some part of the AFTN message may be updated, do you still want to resend?')
            if not self.view.confirm(title, text):
                return False

        if session.line.protocol != 'aftn':
            title = QCoreApplication.translate('Sender', 'Transmission Line Reminder')
            text = QCoreApplication.translate('Sender', 'Not a common transmission line, do you want to continue?')
            if not self.view.confirm(title, text):
                return False

        return True

    def settle(self, job, error=''):
        """Record the outcome of a queued transmission. Submitted is
        promised: saving and sequencing happen even after the session was
        replaced or the window closed; only the display is skipped then."""
        session = self.session
        self.save(job)

        if error:
            if session is not None and session.job is job:
                session.telegraph = job.telegraph
                session.phase = 'failed'
                self.view.showError(error)
                self.view.render()
            return

        self.advanceSequence(job)
        self.updateReminder(job.message)

        if session is not None and session.job is job:
            session.telegraph = job.telegraph
            session.phase = 'sent'
            session.pane = 'telegraph'
            self.view.render()

        # Consumers (table refresh, SIGMET reminders) do not depend on the
        # session surviving
        self.view.succeeded.emit(True)

    def save(self, job):
        if job.telegraph is None:
            return                      # generation failed: nothing was sent

        message = job.message
        resent = bool(message.raw)

        if resent or message.created is None:
            message.created = utcnow()

        message.raw = job.telegraph.toJson()
        message.protocol = job.line.protocol
        self.repository.add(message)

        logger.debug('{} {}'.format('Resend' if resent else 'Send', message.text))

    def advanceSequence(self, job):
        self.conf.set(job.line.channel.configName, str(job.telegraph.number))

    def updateReminder(self, message):
        if message.category in ('SIGMET', 'AIRMET'):
            self.context.sigmet.updateReminders(message)

    def toggle(self):
        if self.session is None or self.session.message.isCnl() or self.view.graphic is None:
            return

        self.session.pane = 'telegraph' if self.session.pane == 'canvas' else 'canvas'
        self.view.render()

    def reload(self):
        if self.session is not None and self.view.isVisible():
            self.session.composed = self.compose(self.session.message)
            self.view.render()

    def cancel(self):
        """What Cancel means right now: 'backed' returns to the editor,
        'closed' closes the dialog chain, None does neither (browsing a
        historical message)."""
        if self.session is not None:
            if self.session.phase == 'sent':
                self.view.closed.emit()
            elif self.session.mode != 'review':
                self.view.backed.emit()

        self.clear()
        self.view.close()

    def clear(self):
        self.session = None
        self.view.render()


class BaseSender(QDialog, Ui_send.Ui_Sender):

    graphic = None              # the SIGMET canvas; set only by subclasses that have one
    pinnedProtocol = None

    closed = pyqtSignal()
    backed = pyqtSignal()
    succeeded = pyqtSignal(bool)

    def __init__(self, parent=None, context=None, conf=None, repository=None):
        super().__init__(parent)
        self.context = context
        self.conf = conf
        self.setupUi(self)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

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

        self.presenter = SenderPresenter(self, self.context, self.conf, repository)

        self.buttonBox.accepted.connect(self.presenter.send)
        self.buttonBox.rejected.connect(self.cancel)
        self.printButton.clicked.connect(self.print)

        self.rawGroup.hide()
        self.canvasGroup.hide()
        self.printButton.hide()
        self.resendButton.hide()
        self.switchButton.hide()

        self.badge = QLabel(self)
        self.badge.hide()

        font = fixedFont()
        font.setPointSize(11)
        self.text.setFont(font)
        self.raw.setFont(font)

    def render(self):
        """Pull the current Situation from the presenter and apply it.
        Idempotent: the same session always renders the same display."""
        state = self.presenter.situation()

        if state.title is not None:
            self.setWindowTitle(state.title)

        self.textGroup.setVisible(state.previewVisible)
        self.text.setHtml(state.html)
        self.resizeText()

        self.canvasGroup.setVisible(state.canvasVisible)
        self.rawGroup.setVisible(state.telegraphVisible)
        self.rawGroup.setTitle(state.telegraphTitle)
        self.raw.setText(state.telegraphText)

        if self.graphic is not None:
            if state.geo is not None:
                self.graphic.setSigmet(state.geo)
            else:
                self.graphic.clear()

        self.sendButton.setVisible(state.action == 'send')
        self.sendButton.setEnabled(not state.busy)
        self.sendButton.setText(QCoreApplication.translate('Sender', 'Sending') if state.busy else QCoreApplication.translate('Sender', 'Send'))

        self.resendButton.setVisible(state.action == 'resend')
        self.resendButton.setEnabled(not state.busy)
        self.resendButton.setText(QCoreApplication.translate('Sender', 'Sending') if state.busy else QCoreApplication.translate('Sender', 'Resend'))

        self.switchButton.setVisible(state.switchVisible)
        if state.switchVisible:
            # The icon advertises the view it toggles to: the words icon
            # while the canvas is showing, the map icon while the telegram is.
            self.switchButton.setIcon(QIcon(iconPath('words.png' if state.canvasVisible else 'map.png')))

        self.printButton.setVisible(state.printVisible)
        self.updateBadge(state)

    def confirm(self, title, text):
        ret = QMessageBox.question(self, title, text)
        return ret == QMessageBox.Yes

    def showError(self, text):
        QMessageBox.critical(self, QCoreApplication.translate('Sender', 'Error'), text)

    def updateBadge(self, state):
        pixmap = QPixmap(iconPath('{}.png'.format(state.badgeProtocol)))
        self.badge.setPixmap(pixmap)
        self.badge.setMask(pixmap.mask())
        self.badge.adjustSize()
        self.badge.setVisible(state.badgeVisible)

    def resizeEvent(self, event):
        self.badge.move(self.width() - 53, 3)
        super().resizeEvent(event)

    def print(self):
        session = self.presenter.session
        if session is None or not session.message.raw:
            return

        printer = QPrinter()
        dialog = QPrintDialog(printer, self)
        if dialog.exec() != QDialog.Accepted:
            return

        message = session.message
        aftn = AFTNDecoder(message.raw)

        priority = QCoreApplication.translate('Sender', 'Priority Indicator')
        address = QCoreApplication.translate('Sender', 'Send Address')
        originator = QCoreApplication.translate('Sender', 'Originator Address')
        content = QCoreApplication.translate('Sender', 'Message Content')
        time = QCoreApplication.translate('Sender', 'Sent Time')
        raw = QCoreApplication.translate('Sender', 'Raw Data')

        items = [
            (priority, aftn.priority),
            (address, aftn.address),
            (originator, aftn.originator),
            (content, message.report),
            (raw, message.rawText()),
            (time, '{} UTC'.format(message.created)),
        ]

        blocks = ['<p><b>{}</b><br>{}</p>'.format(title, '<br>'.join(str(value).split('\n')))
                  for title, value in items if value]

        editor = QTextEdit()
        editor.document().setDefaultFont(fixedFont())
        editor.setHtml(''.join(blocks))
        editor.print(printer)

    def resizeText(self):
        text = self.text.toPlainText()
        font = self.text.document().defaultFont()
        fontMetrics = QFontMetrics(font)
        textSize = fontMetrics.size(0, text)
        textHeight = textSize.height() + 50
        self.text.setMaximumHeight(textHeight)

    def closeEvent(self, event):
        # A user click on the window × counts as Cancel; a programmatic close
        # only clears silently
        if event.spontaneous():
            self.cancel()
        else:
            self.clear()

    def receive(self, message):
        self.presenter.receive(message)

    def cancel(self):
        self.presenter.cancel()

    def clear(self):
        self.presenter.clear()


class TafSender(BaseSender):
    pass


class TrendSender(BaseSender):

    pinnedProtocol = 'aftn'

    def __init__(self, parent=None, context=None, conf=None, repository=None):
        super().__init__(parent, context, conf, repository)
        self.context.event.trendReloadRequested.connect(self.presenter.reload)


class SigmetSender(BaseSender):

    def __init__(self, parent=None, context=None, conf=None, repository=None):
        super().__init__(parent, context, conf, repository)
        self.graphic = PreviewPanel(self, context=self.context)
        self.canvasLayout.addWidget(self.graphic)
        self.switchButton.clicked.connect(self.presenter.toggle)

    def resizeEvent(self, event):
        self.switchButton.move(self.width() - 70, self.textGroup.height() + 50)
        super().resizeEvent(event)


class CustomSender(BaseSender):

    pinnedProtocol = 'aftn'

    def __init__(self, parent=None, context=None, conf=None, repository=None):
        super().__init__(parent, context, conf, repository)
        self.setModal(True)
        self.setWindowTitle(QCoreApplication.translate('Sender', 'Send Custom Message'))

    def receive(self, message):
        self.presenter.load(message)
