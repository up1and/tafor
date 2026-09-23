import datetime
import json

from types import SimpleNamespace

import pytest

from PyQt5.QtWidgets import QMessageBox

from tafor.core.models import Other, Sigmet, Taf, Trend
from tafor.core.repositories import MessageRepository
from tafor.ui.components.send import CustomSender, SigmetSender, TafSender, TrendSender
from tafor.ui.workers import TransmissionQueue


def makeTaf(read_fixture):
    return Taf(type='FT', heading='FTZJ41 ZJHK 211400', text=read_fixture('taf', 'pass1'))


def makeSigmet(read_fixture, name='va_pass'):
    return Sigmet(type='WS', heading='WSZJ31 ZJHK 300900', text=read_fixture('sigmet', name))


def spySignals(sender):
    received = []
    sender.backed.connect(lambda: received.append('backed'))
    sender.closed.connect(lambda: received.append('closed'))
    sender.succeeded.connect(lambda ok: received.append('succeeded'))
    return received


@pytest.fixture(autouse=True)
def resetSequence(conf):
    conf.set('channelSequenceNumber', '1')
    conf.set('fileSequenceNumber', '1')


@pytest.fixture
def transmission(context):
    """A real TransmissionQueue with the worker stubbed out: submissions are
    generated and dispatched synchronously, the test delivers results with
    queue.finish(error)"""
    calls = []
    worker = SimpleNamespace(prepare=lambda: None, stop=lambda: None, error='')
    queue = TransmissionQueue(worker)
    queue.dispatch.connect(lambda kind, text, params: calls.append(
        {'kind': kind, 'text': text, 'params': params}))
    queue.calls = calls
    context.transmission = queue
    return queue


@pytest.fixture
def answers(monkeypatch):
    """Auto-answer the popups and record their texts"""
    record = {'questions': [], 'errors': []}

    def question(parent, title, text, *args, **kwargs):
        record['questions'].append(text)
        return QMessageBox.Yes

    def critical(parent, title, text, *args, **kwargs):
        record['errors'].append(text)

    monkeypatch.setattr('tafor.ui.components.send.QMessageBox.question', question)
    monkeypatch.setattr('tafor.ui.components.send.QMessageBox.critical', critical)
    return record


@pytest.fixture
def sender(qtbot, context, conf, database, monkeypatch):
    monkeypatch.setattr(context.license, 'hasPermission', lambda category: True)
    sender = TafSender(None, context, conf, repository=MessageRepository(database))
    qtbot.addWidget(sender)
    return sender


@pytest.fixture
def sigmetSender(qtbot, context, conf, database, monkeypatch):
    monkeypatch.setattr(context.license, 'hasPermission', lambda category: True)
    sender = SigmetSender(None, context, conf, repository=MessageRepository(database))
    qtbot.addWidget(sender)
    return sender


@pytest.fixture
def customSender(qtbot, context, conf, database, monkeypatch):
    monkeypatch.setattr(context.license, 'hasPermission', lambda category: True)
    sender = CustomSender(None, context, conf, repository=MessageRepository(database))
    qtbot.addWidget(sender)
    return sender


class TestNewMessageSend:

    def test_badge_renders_protocol_icon(self, sender, read_fixture, qtbot):
        """Regression: the badge once loaded its pixmap through a path with a
        format placeholder resolved after the existence check, so the icon
        silently loaded empty and the label painted nothing"""
        message = makeTaf(read_fixture)
        sender.receive(message)
        sender.show()
        qtbot.waitExposed(sender)

        assert sender.badge.isVisible()
        assert not sender.badge.pixmap().isNull()
        assert sender.badge.geometry().right() < sender.width()

    def test_badge_reanchors_after_dialog_resize(self, sender, read_fixture, qtbot):
        """Regression: render pins the badge with the width of the moment, but
        the SetFixedSize dialog resizes later, so a reused dialog kept the
        badge at the previous session's width (review close shrinks it, the
        next receive grows it back)"""
        message = makeTaf(read_fixture)
        sender.receive(message)
        sender.show()
        qtbot.waitExposed(sender)

        sender.clear()
        qtbot.wait(10)              # let the cleared layout shrink land
        sender.receive(message)
        qtbot.wait(10)              # let the layout grow back and re-pin

        assert sender.badge.isVisible()

    def test_send_success(self, sender, transmission, answers, read_fixture, qtbot):
        message = makeTaf(read_fixture)
        sender.receive(message)

        assert sender.windowTitle() == 'Send Message'
        assert sender.sendButton.isVisibleTo(sender)
        assert not sender.resendButton.isVisibleTo(sender)
        assert not sender.rawGroup.isVisibleTo(sender)
        assert not sender.printButton.isVisibleTo(sender)
        assert sender.badge.isVisibleTo(sender)

        with qtbot.waitSignal(sender.succeeded):
            sender.presenter.send()
            transmission.finish('')

        assert sender.rawGroup.isVisibleTo(sender)
        assert sender.rawGroup.title() == 'Data has been sent to the serial port'
        assert not sender.sendButton.isVisibleTo(sender)
        assert not sender.resendButton.isVisibleTo(sender)
        assert sender.printButton.isVisibleTo(sender)
        assert not sender.badge.isVisibleTo(sender)
        assert 'ZCZC' in sender.raw.toPlainText()

        # Persisted message + sequence number advanced
        assert message.raw and message.protocol == 'aftn'
        assert message.id is not None
        assert sender.conf.get('channelSequenceNumber') == '2'

    def test_send_failure_then_resend(self, sender, transmission, answers, read_fixture):
        message = makeTaf(read_fixture)
        sender.receive(message)

        sender.presenter.send()
        transmission.finish('serial port offline')

        # One error popup, 'Send Failed' title, Resend appears
        assert answers['errors'] == ['serial port offline']
        assert sender.rawGroup.isVisibleTo(sender)
        assert sender.rawGroup.title() == 'Send Failed'
        assert not sender.sendButton.isVisibleTo(sender)
        assert sender.resendButton.isVisibleTo(sender)
        assert message.raw and message.id is not None
        assert sender.conf.get('channelSequenceNumber') == '1'

        # Resending is the same entry point; success returns to the sent display
        message.created = datetime.datetime.utcnow() - datetime.timedelta(minutes=5)
        sender.presenter.send()
        transmission.finish('')

        assert sender.rawGroup.title() == 'Data has been sent to the serial port'
        assert not sender.resendButton.isVisibleTo(sender)
        assert sender.conf.get('channelSequenceNumber') == '2'
        assert message.created > datetime.datetime.utcnow() - datetime.timedelta(seconds=10)

        received = spySignals(sender)
        sender.cancel()
        assert received == ['closed']

    def test_cancel_before_send_backs_to_editor(self, sender, read_fixture):
        sender.receive(makeTaf(read_fixture))

        received = spySignals(sender)
        sender.cancel()
        assert received == ['backed']

    def test_validator_confirmation(self, sender, transmission, answers, read_fixture):
        text = read_fixture('taf', 'vis_under_1000_weather_error')
        sender.receive(Taf(type='FT', heading='FTZJ41 ZJHK 211400', text=text))

        sender.presenter.send()

        assert answers['questions'] == ['The message did not pass the validator, do you still want to send?']
        assert len(transmission.calls) == 1

    def test_send_without_permission(self, sender, transmission, answers, read_fixture, monkeypatch):
        monkeypatch.setattr(sender.context.license, 'hasPermission', lambda category: False)
        message = makeTaf(read_fixture)
        sender.receive(message)

        sender.presenter.send()

        assert transmission.calls == []
        assert answers['errors'] == ['Limited functionality, please check the license information']
        assert sender.rawGroup.title() == 'Send Failed'
        assert not sender.sendButton.isVisibleTo(sender)
        assert not sender.resendButton.isVisibleTo(sender)
        # License before submit: a refused message is never archived
        assert message.id is None
        assert sender.conf.get('channelSequenceNumber') == '1'

    def test_receive_twice_without_clear(self, sender, transmission, answers, read_fixture):
        sender.receive(makeTaf(read_fixture))
        sender.presenter.send()
        transmission.finish('')
        assert sender.rawGroup.isVisibleTo(sender)

        second = makeTaf(read_fixture)
        second.heading = 'FTZJ41 ZJHK 220400'
        sender.receive(second)

        # The second load carries no residue of the first one
        assert sender.sendButton.isVisibleTo(sender)
        assert not sender.rawGroup.isVisibleTo(sender)
        assert not sender.printButton.isVisibleTo(sender)
        assert sender.windowTitle() == 'Send Message'

    def test_stale_result_discarded(self, sender, transmission, answers, read_fixture):
        first = makeTaf(read_fixture)
        sender.receive(first)
        sender.presenter.send()

        sender.receive(makeTaf(read_fixture))
        transmission.finish('boom')

        # The result belongs to the replaced session: the transmission is
        # still archived (it happened), but the display is not touched
        assert first.id is not None
        assert answers['errors'] == []
        assert sender.sendButton.isVisibleTo(sender)

    def test_submission_marks_session_sending(self, sender, transmission, answers, read_fixture):
        sender.receive(makeTaf(read_fixture))
        sender.presenter.send()

        assert sender.presenter.session.phase == 'sending'
        assert transmission.calls[0]['kind'] == 'aftn'

    def test_result_after_window_closed_is_still_archived(self, sender, transmission, answers, read_fixture, conf):
        message = makeTaf(read_fixture)
        sender.receive(message)
        sender.presenter.send()

        sender.clear()      # the window closed while the transmission runs
        transmission.finish('')

        assert message.id is not None
        assert conf.get('channelSequenceNumber') == '2'


class TestReviewMessage:

    def reviewMessage(self, read_fixture, minutes=30):
        message = makeTaf(read_fixture)
        message.id = 1
        message.created = datetime.datetime.utcnow() - datetime.timedelta(minutes=minutes)
        message.raw = json.dumps(['ZCZC YMC0001\r\nGG YUSOYMYX\r\n011200 YUSOYMYX\r\nTAF\r\nNNNN'])
        return message

    def test_view_mode_display(self, sender, read_fixture):
        sender.receive(self.reviewMessage(read_fixture))

        assert sender.windowTitle() == 'View Message'
        assert sender.rawGroup.isVisibleTo(sender)
        assert sender.rawGroup.title() == 'Raw Data'
        assert not sender.sendButton.isVisibleTo(sender)
        assert sender.resendButton.isVisibleTo(sender)
        assert sender.printButton.isVisibleTo(sender)

    def test_resend_refreshes_created_and_sequence(self, sender, transmission, answers, read_fixture):
        message = self.reviewMessage(read_fixture)
        sender.receive(message)

        sender.presenter.send()
        assert answers['questions'] == [
            'Some part of the AFTN message may be updated, do you still want to resend?']

        created = message.created
        transmission.finish('')

        assert message.created > created
        assert sender.conf.get('channelSequenceNumber') == '2'
        assert sender.rawGroup.title() == 'Data has been sent to the serial port'

    def test_cancel_without_resend_is_silent(self, sender, read_fixture):
        sender.receive(self.reviewMessage(read_fixture))

        received = spySignals(sender)
        sender.cancel()
        assert received == []

    def test_cancel_after_resend_closes(self, sender, transmission, answers, read_fixture):
        sender.receive(self.reviewMessage(read_fixture))
        sender.presenter.send()
        transmission.finish('')

        received = spySignals(sender)
        sender.cancel()
        assert received == ['closed']


class TestSigmet:

    def test_canvas_flow(self, sigmetSender, transmission, answers, read_fixture):
        message = makeSigmet(read_fixture)
        sigmetSender.receive(message)

        assert sigmetSender.canvasGroup.isVisibleTo(sigmetSender)
        assert not sigmetSender.rawGroup.isVisibleTo(sigmetSender)
        assert not sigmetSender.switchButton.isVisibleTo(sigmetSender)
        assert sigmetSender.sendButton.isVisibleTo(sigmetSender)

        sigmetSender.presenter.send()
        transmission.finish('')

        # Auto switch to the telegraph view, toggle button appears
        assert sigmetSender.rawGroup.isVisibleTo(sigmetSender)
        assert not sigmetSender.canvasGroup.isVisibleTo(sigmetSender)
        assert sigmetSender.switchButton.isVisibleTo(sigmetSender)
        assert sigmetSender.printButton.isVisibleTo(sigmetSender)

        # Print stays visible in the canvas view too
        sigmetSender.presenter.toggle()
        assert sigmetSender.canvasGroup.isVisibleTo(sigmetSender)
        assert not sigmetSender.rawGroup.isVisibleTo(sigmetSender)
        assert sigmetSender.printButton.isVisibleTo(sigmetSender)

        sigmetSender.presenter.toggle()
        assert sigmetSender.rawGroup.isVisibleTo(sigmetSender)

    def test_cnl_has_no_canvas(self, sigmetSender, transmission, answers, read_fixture):
        message = makeSigmet(read_fixture, name='cnl_pass')
        sigmetSender.receive(message)

        # A CNL never shows the canvas; with no telegraph both groups stay hidden
        assert not sigmetSender.canvasGroup.isVisibleTo(sigmetSender)
        assert not sigmetSender.rawGroup.isVisibleTo(sigmetSender)
        assert sigmetSender.sendButton.isVisibleTo(sigmetSender)

        sigmetSender.presenter.send()
        transmission.finish('')

        assert not sigmetSender.canvasGroup.isVisibleTo(sigmetSender)
        assert sigmetSender.rawGroup.isVisibleTo(sigmetSender)
        assert not sigmetSender.switchButton.isVisibleTo(sigmetSender)

    def test_graphic_receives_composed_shape(self, sigmetSender, read_fixture, monkeypatch):
        pushed = []
        cleared = []
        monkeypatch.setattr(sigmetSender.graphic, 'setSigmet', lambda geo: pushed.append(geo))
        monkeypatch.setattr(sigmetSender.graphic, 'clear', lambda: cleared.append(True))

        # A fresh session pushes the composed shape onto the canvas
        sigmetSender.receive(makeSigmet(read_fixture))
        assert pushed and pushed[-1] is not None

        # A review (historical message) pushes it as well
        review = makeSigmet(read_fixture)
        review.id = 1
        review.created = datetime.datetime.utcnow()
        sigmetSender.receive(review)
        assert len(pushed) == 2 and pushed[-1] is not None

        # A CNL has no shape: the canvas is cleared instead
        sigmetSender.receive(makeSigmet(read_fixture, name='cnl_pass'))
        assert cleared

    def test_broken_sigmet_degrades_gracefully(self, sigmetSender, transmission, answers, read_fixture, monkeypatch):
        def brokenParser(*args, **kwargs):
            raise ValueError('broken')

        monkeypatch.setattr('tafor.ui.components.send.SigmetParser', brokenParser)
        message = makeSigmet(read_fixture)
        sigmetSender.receive(message)

        # The preview degrades to empty instead of crashing the load
        assert not sigmetSender.canvasGroup.isVisibleTo(sigmetSender)
        assert not sigmetSender.rawGroup.isVisibleTo(sigmetSender)
        assert sigmetSender.sendButton.isVisibleTo(sigmetSender)

        sigmetSender.presenter.send()
        transmission.finish('')

        assert sigmetSender.rawGroup.isVisibleTo(sigmetSender)
        assert message.raw and message.id is not None


class TestCustomMessage:

    def test_load_and_send(self, customSender, transmission, answers):
        message = Other(text='TEST CUSTOM MESSAGE=', priority='FF', address='YUSO YUSI')

        customSender.presenter.load(message)

        # Fixed title, 'Received Messages' telegraph, Send visible, no Print
        assert customSender.windowTitle() == 'Send Custom Message'
        assert customSender.rawGroup.isVisibleTo(customSender)
        assert customSender.rawGroup.title() == 'Received Messages'
        assert not customSender.textGroup.isVisibleTo(customSender)
        assert customSender.sendButton.isVisibleTo(customSender)
        assert not customSender.printButton.isVisibleTo(customSender)
        assert 'ZCZC' in customSender.raw.toPlainText()
        assert 'FF YUSO YUSI' in customSender.raw.toPlainText()

        # No load or clear ever overwrites the window title
        customSender.clear()
        assert customSender.windowTitle() == 'Send Custom Message'

        customSender.receive(message)
        assert customSender.windowTitle() == 'Send Custom Message'
        assert customSender.rawGroup.title() == 'Received Messages'

        customSender.presenter.send()
        transmission.finish('')
        assert customSender.rawGroup.title() == 'Data has been sent to the serial port'


class TestTrendSender:

    def test_reload(self, qtbot, context, conf, database):
        sender = TrendSender(None, context, conf, repository=MessageRepository(database))
        qtbot.addWidget(sender)

        sender.receive(Trend(text='BECMG AT1200 CAVOK='))
        assert sender.sendButton.isVisibleTo(sender)

        sender.presenter.reload()
        assert sender.sendButton.isVisibleTo(sender)
