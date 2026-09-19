"""Tests for tafor/ui/components/sigmet.py.

SigmetEditor is constructed against a real SigmetSender like the TAF editor
tests do; the graphic canvas loads the local FIR resources, which works
offscreen.
"""

import re
from types import SimpleNamespace

import pytest

from PyQt5.QtCore import QObject, pyqtSignal

from tafor.core.models import Sigmet
from tafor.core.repositories import MessageRepository, SigmetRepository
from tafor.core.sigmet.compose import validDuration
from tafor.ui.components.send import SigmetSender
from tafor.ui.components.sigmet import SigmetEditor, SigmetPresenter


class StubContent:

    def __init__(self, acceptable=True):
        self.acceptable = acceptable
        self.validated = False
        self.cleared = False

    def validate(self):
        self.validated = True

    def hasAcceptableInput(self):
        return self.acceptable

    def clear(self):
        self.cleared = True


class StubView(QObject):
    """Just the surface SigmetPresenter touches."""

    finished = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.designator = 'WS'
        self.heading = lambda: 'WSNT36 ZJHK 100800'
        self.message = lambda: 'ZJSA SANYA FIR OBSC TS='
        self.currentContent = StubContent()
        self.graphic = SimpleNamespace(hasAcceptableGraphic=lambda: True)
        self.graphicWindow = False
        self.enabled = None
        self.cleared = False
        self.nextButton = SimpleNamespace(setEnabled=self.setEnabled)

    def setEnabled(self, enabled):
        self.enabled = enabled

    def hasGraphicWindow(self):
        return self.graphicWindow

    def clear(self):
        self.cleared = True


@pytest.fixture
def sender(qtbot, context, conf, database):
    sender = SigmetSender(None, context, conf, repository=MessageRepository(database))
    qtbot.addWidget(sender)
    return sender


@pytest.fixture
def editor(qtbot, sender, conf, context, database):
    editor = SigmetEditor(None, sender=sender, conf=conf, context=context,
                          repository=SigmetRepository(database))
    qtbot.addWidget(editor)
    return editor


class TestSigmetPresenter:

    @pytest.fixture
    def view(self):
        return StubView()

    @pytest.fixture
    def presenter(self, view, context, conf):
        presenter = SigmetPresenter(view, context, conf)
        return presenter

    def test_before_next_validates_and_previews(self, presenter, view, qtbot):
        messages = []
        view.finished.connect(messages.append)

        presenter.beforeNext()

        assert view.currentContent.validated is True
        assert len(messages) == 1
        message = messages[0]
        assert isinstance(message, Sigmet)
        assert message.type == 'WS'
        assert message.heading == 'WSNT36 ZJHK 100800'
        assert message.text == 'ZJSA SANYA FIR OBSC TS='

    def test_before_next_skips_preview_when_input_rejected(self, presenter, view, qtbot):
        messages = []
        view.finished.connect(messages.append)
        view.currentContent.acceptable = False

        presenter.beforeNext()

        assert view.currentContent.validated is True
        assert messages == []

    def test_has_acceptable_input_aggregates_graphic(self, presenter, view):
        assert presenter.hasAcceptableInput() is True

        view.graphicWindow = True
        assert presenter.hasAcceptableInput() is True

        view.graphic.hasAcceptableGraphic = lambda: False
        assert presenter.hasAcceptableInput() is False

    def test_enable_next_button_mirrors_input(self, presenter, view):
        presenter.enableNextButton()
        assert view.enabled is True

        view.currentContent.acceptable = False
        presenter.enableNextButton()
        assert view.enabled is False

    def test_clear_delegates_to_view(self, presenter, view):
        presenter.clear()
        assert view.cleared is True


class TestSigmetEditor:

    def test_category_follows_designator(self, editor):
        assert editor.category() == 'SIGMET'

        editor.airmansWeather.click()
        assert editor.category() == 'AIRMET'

    def test_template_mode_starts_with_general_content(self, editor):
        assert editor.template.isChecked() is True
        assert editor.currentContent is editor.generalContent
        assert editor.graphic.isVisibleTo(editor)

    def test_cancel_mode_keeps_the_graphic_visible(self, editor):
        # unlike the message composition, the canvas stays visible in
        # cancel mode; only custom content hides it
        editor.cancel.click()

        assert editor.currentContent is editor.cancelContent
        assert editor.graphic.isVisibleTo(editor)
        assert editor.designator == 'WS'

    def test_leaving_cancel_mode_needs_the_template_radio(self, editor):
        # the template/custom/cancel radios form one exclusive group while
        # the hazard radios live in another, so clicking a hazard radio
        # cannot leave cancel mode
        editor.cancel.click()
        editor.significantWeather.click()

        assert editor.currentContent is editor.cancelContent

        editor.template.click()
        assert editor.currentContent is editor.generalContent
        assert editor.graphic.isVisibleTo(editor)

    def test_custom_mode_hides_graphic(self, editor):
        editor.custom.click()

        assert editor.currentContent is editor.customContent
        assert not editor.graphic.isVisibleTo(editor)

    def test_selecting_a_form_updates_span_of_current_content(self, editor):
        editor.tropicalCyclone.click()

        assert editor.draft.designator == 'WC'
        assert editor.currentContent.span == validDuration('WC')

    def test_reclicking_the_checked_radio_does_not_reset_the_canvas(self, editor, monkeypatch):
        # radio clicked fires even on the already-checked radio; the render
        # gated on draft.select() must not re-run configureMode, which
        # clears the drawn sketch
        calls = []
        monkeypatch.setattr(editor.graphic, 'configureMode', lambda *args: calls.append(args))

        editor.significantWeather.click()

        assert calls == []

    def test_heading_composes_designator_area_and_time(self, editor, conf):
        heading = editor.heading()

        pattern = r'^WS{} {} \d{{6}}$'.format(conf.bulletinNumber or '', conf.airport)
        assert re.match(pattern, heading)

    def test_message_from_custom_content_appends_equals(self, editor):
        editor.custom.click()
        editor.customContent.text.setPlainText('ZJSA SANYA FIR OBSC TS')

        message = editor.message()

        assert message.endswith('ZJSA SANYA FIR OBSC TS=')

    def test_clear_resets_state_but_keeps_the_text_widget(self, editor):
        # BUG: SigmetCustom.clear resets the state but not the text widget,
        # so the editor keeps showing stale content after a clear
        editor.customContent.text.setPlainText('SOME TEXT')
        editor.clear()

        assert editor.customContent.state.text == ''
        assert editor.customContent.text.toPlainText() == 'SOME TEXT'

    def test_close_clears_sigmet_notification(self, editor, context):
        context.notification.sigmet.setState({'message': 'ZJSA SIGMET 1 VALID 100930/101430 ZJHK-'})

        editor.onClose()

        assert context.notification.sigmet.message() is None


if __name__ == '__main__':
    pytest.main([__file__])
