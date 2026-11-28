"""Tests for tafor/ui/dialogs/sigmet.py.

SigmetEditor is constructed against a real SigmetSender like the TAF editor
tests do; the graphic canvas loads the local FIR resources, which works
offscreen.
"""

import pytest

from PyQt5.QtCore import QObject, QSignalBlocker, pyqtSignal
from PyQt5.QtWidgets import QComboBox, QStackedWidget

from tafor.core.models import Sigmet
from tafor.core.repositories import MessageRepository, SigmetRepository
from tafor.core.sigmet import SigmetHeaderState
from tafor.core.sigmet.compose import validDuration
from tafor.core.sigmet.states import (
    SigmetCancelState,
    SigmetCustomState,
    SigmetGeneralState,
    SigmetTyphoonState,
)
from tafor.ui.dialogs import SigmetEditor, SigmetPresenter, SigmetSender


class StubGraphic(QObject):

    refreshClicked = pyqtSignal()
    layerSelectionChanged = pyqtSignal(list)
    trimChanged = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.trimShapes = True
        self.acceptable = True
        self.locations = {'location': 'N2000 E11000'}
        self.modes = []
        self.sigmets = []
        self.layers = []

    def configureMode(self, designator, mode):
        self.modes.append((designator, mode))

    def location(self):
        return self.locations

    def hasAcceptableGraphic(self):
        return self.acceptable

    def setSigmets(self, geometries):
        self.sigmets.append(geometries)

    def setLayers(self, **kwargs):
        self.layers.append(kwargs)


class StubView(QObject):
    """Pure passive view surface for headless SigmetPresenter tests."""

    formSelected = pyqtSignal(str)
    contentChanged = pyqtSignal()
    opened = pyqtSignal()
    closed = pyqtSignal()
    submitted = pyqtSignal()
    finished = pyqtSignal(object)

    def __init__(self, unit='KMH'):
        super().__init__()
        self.unit = unit
        self.graphic = StubGraphic()
        self.setHeader(SigmetHeaderState())
        self.shownForm = None
        self.seeded = None
        self.customText = None
        self.collected = False
        self.validated = False
        self.cleared = False
        self.enabled = None

    def setHeader(self, header):
        self.header = header
        self.states = {
            'general': self._make_general_state(self.unit),
            'typhoon': SigmetTyphoonState(self.unit, self.header),
            'ash': SigmetGeneralState(self.unit, self.header),
            'airmet': self._make_general_state(self.unit),
            'cancel': self._make_cancel_state(),
            'custom': self._make_custom_state(),
        }

    def _make_general_state(self, unit):
        state = SigmetGeneralState(unit, self.header)
        state.description = 'OBSC'
        state.phenomenon = 'TS'
        state.comeFrom = 'OBS'
        state.observedTime = '100800'
        state.flightLevelTop = '120'
        state.direction = 'NE'
        state.speed = '25'
        return state

    def _make_cancel_state(self):
        state = SigmetCancelState(self.header)
        state.cancelSequence = '1'
        state.cancelBeginningTime = '100930'
        state.cancelEndingTime = '101430'
        return state

    def _make_custom_state(self):
        state = SigmetCustomState(self.header)
        state.text = 'ZJSA SANYA FIR OBSC TS'
        return state

    def fillHeader(self, sign='SIGMET'):
        self.header.area = 'ZJSA'
        self.header.sign = sign
        self.header.sequence = '1'
        self.header.beginningTime = '100930'
        self.header.endingTime = '101430'
        self.header.icao = 'ZJHK'

    def formState(self, name):
        return self.states[name]

    def showForm(self, name):
        self.shownForm = name

    def seedForm(self, sequence, candidates=None, latestText=None):
        self.seeded = (sequence, candidates, latestText)

    def setCustomText(self, latest):
        self.customText = latest

    def collect(self):
        self.collected = True

    def validate(self):
        self.validated = True

    def setNextEnabled(self, enabled):
        self.enabled = enabled

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


@pytest.fixture
def presenter(editor):
    return editor.presenter


SIGMET_TEXT = 'YUDD SIGMET 1 VALID 100730/101430 YUSO- YUDD SHANLON FIR OBSC TS='


def store_sigmet(database, text, type='WS'):
    sigmet = Sigmet(type=type, heading=text, text=text)
    with database.session() as session:
        session.add(sigmet)
    return sigmet


def choose(combo, text):
    index = combo.findText(text)
    combo.setCurrentIndex(index)
    combo.activated.emit(index)


def user_edit(widget, text):
    widget.setPlainText(text)


class TestSigmetPresenter:

    @pytest.fixture
    def view(self):
        return StubView()

    @pytest.fixture
    def presenter(self, view, context, conf, database):
        presenter = SigmetPresenter(view, context, conf, SigmetRepository(database))
        view.setHeader(presenter.draft.header)
        return presenter

    def test_next_sequence_continues_todays_count(self, context, conf, database, frozen_time):
        store_sigmet(database, 'YUDD SIGMET 1 VALID 100730/101430 YUSO- YUDD SHANLON FIR OBSC TS=')
        presenter = SigmetPresenter(None, context, conf, SigmetRepository(database))

        # one series per FIR, not per designator: the stored WS takes number 1
        # for the WV draft too; AIRMET carries its own count
        assert presenter.nextSequence('WS') == 2
        assert presenter.nextSequence('WV') == 2
        assert presenter.nextSequence('WA') == 1

    def test_latest_text_prefers_the_waiting_notification(self, context, conf, database):
        store_sigmet(database, 'YUDD SIGMET 1 VALID 100730/101430 YUSO- YUDD SHANLON FIR OBSC TS=')
        context.notification.sigmet.setState({'message': SIGMET_TEXT})
        presenter = SigmetPresenter(None, context, conf, SigmetRepository(database))

        assert presenter.latestText('WS') == ('notification', 'YUDD SHANLON FIR OBSC TS=')

    def test_latest_text_falls_back_to_the_stored_report(self, context, conf, database):
        store_sigmet(database, 'YUDD SIGMET 1 VALID 100730/101430 YUSO- YUDD SHANLON FIR OBSC TS=')
        presenter = SigmetPresenter(None, context, conf, SigmetRepository(database))

        assert presenter.latestText('WS') == ('database', 'YUDD SHANLON FIR OBSC TS=')

    def test_latest_text_ignores_a_notification_for_another_designator(self, context, conf, database):
        context.notification.sigmet.setState({'message': SIGMET_TEXT})
        presenter = SigmetPresenter(None, context, conf, SigmetRepository(database))

        assert presenter.latestText('WV') is None

    def test_sigmets_are_the_ones_in_force(self, context, conf, database):
        store_sigmet(database, SIGMET_TEXT)
        context.current.setState(SigmetRepository(database).current())
        presenter = SigmetPresenter(None, context, conf, SigmetRepository(database))

        assert [sig.heading for sig in presenter.sigmets(designator='WS')] == [SIGMET_TEXT]
        assert presenter.sigmets(designator='WV') == []

    def test_sigmets_narrow_by_the_address_the_caller_names(self, context, conf):
        # One code or the whole bulletin sign: WS is a designator, SIGMET is
        # the category that also covers WC and WV. The dropdown needs the
        # first, the canvas beside a template the second.
        context.current.setState([
            Sigmet(type='WS', heading='', text='A'),
            Sigmet(type='WC', heading='', text='B'),
            Sigmet(type='WV', heading='', text='C'),
            Sigmet(type='WA', heading='', text='D'),
        ])
        presenter = SigmetPresenter(None, context, conf)

        def types(sigmets):
            return [sig.type for sig in sigmets]

        assert types(presenter.sigmets(designator='WS')) == ['WS']
        assert types(presenter.sigmets(category='SIGMET')) == ['WS', 'WC', 'WV']
        assert types(presenter.sigmets(category='AIRMET')) == ['WA']

    def test_initialize_attaches_initial_body_and_shows_general_without_seeding(self, presenter, view):
        presenter.initialize()

        assert presenter.draft.body is view.states['general']
        assert view.shownForm == 'general'
        assert view.seeded is None

    def test_select_form_updates_draft_renders_form_and_reconfigures_graphic(self, presenter, view, context):
        sig = Sigmet(type='WC', heading='YUDD SIGMET 1 VALID 100730/101430 YUSO-', text='YUDD SHANLON FIR TC=')
        context.current.setState([sig])
        presenter.initialize()

        view.formSelected.emit('typhoon')

        assert presenter.draft.form == 'typhoon'
        assert presenter.draft.designator == 'WC'
        assert presenter.draft.header.designator == 'WC'
        assert presenter.draft.body is view.states['typhoon']
        assert view.shownForm == 'typhoon'
        assert view.seeded == (1, None, None)
        assert view.graphic.modes == [('WC', 'template')]
        assert len(view.graphic.sigmets) == 1

    def test_reselecting_current_form_is_a_noop(self, presenter, view):
        presenter.initialize()

        view.formSelected.emit('general')

        assert view.seeded is None
        assert view.graphic.modes == []
        assert view.graphic.sigmets == []

    def test_select_cancel_loads_candidates_and_custom_loads_latest_text(self, presenter, view, context, database):
        store_sigmet(database, SIGMET_TEXT)
        sig = Sigmet(type='WS', heading='YUDD SIGMET 1 VALID 100730/101430 YUSO-', text='YUDD SHANLON FIR OBSC TS=')
        context.current.setState([sig])
        presenter.initialize()

        view.formSelected.emit('cancel')
        assert view.seeded == (1, [sig], None)
        assert view.graphic.modes == [('WS', 'cancel')]

        view.formSelected.emit('custom')
        assert view.seeded == (1, None, ('database', 'YUDD SHANLON FIR OBSC TS='))

        presenter.updateCustomText()
        assert view.customText == ('database', 'YUDD SHANLON FIR OBSC TS=')

    def test_before_next_validates_and_previews(self, presenter, view):
        presenter.initialize()
        view.fillHeader()
        messages = []
        view.finished.connect(messages.append)

        view.submitted.emit()

        assert view.collected is True
        assert view.validated is True
        assert len(messages) == 1
        assert messages[0].type == 'WS'
        assert 'N2000 E11000' in messages[0].text

    def test_before_next_skips_preview_when_draft_or_graphic_rejected(self, presenter, view):
        presenter.initialize()
        view.fillHeader()
        messages = []
        view.finished.connect(messages.append)

        view.graphic.acceptable = False
        view.submitted.emit()
        assert messages == []

        view.graphic.acceptable = True
        view.header.sequence = ''
        view.submitted.emit()
        assert view.validated is True
        assert messages == []

    def test_has_acceptable_input_requires_graphic_only_for_sketch_forms(self, presenter, view):
        presenter.initialize()
        view.fillHeader()
        assert presenter.hasAcceptableInput() is True

        view.graphic.acceptable = False
        assert presenter.hasAcceptableInput() is False

        view.formSelected.emit('custom')
        assert presenter.hasAcceptableInput() is True

    def test_enable_next_button_mirrors_input(self, presenter, view):
        presenter.initialize()
        view.fillHeader()

        view.contentChanged.emit()
        assert view.enabled is True

        view.graphic.acceptable = False
        view.contentChanged.emit()
        assert view.enabled is False

    def test_clear_empties_notification_header_view_and_resets_graphic(self, presenter, view, context):
        context.notification.sigmet.setState({'message': SIGMET_TEXT})
        presenter.initialize()
        view.fillHeader()

        view.closed.emit()

        assert context.notification.sigmet.message() is None
        assert presenter.draft.header.sequence == ''
        assert view.cleared is True
        assert view.graphic.modes == [('WS', 'template')]
        assert view.enabled is False

    def test_current_sigmet_changed_event_redraws_graphic(self, presenter, view, context):
        sig = Sigmet(type='WS', heading='YUDD SIGMET 1 VALID 100730/101430 YUSO-', text='YUDD SHANLON FIR OBSC TS=')
        presenter.initialize()
        view.graphic.sigmets.clear()

        context.current.setState([sig])

        assert len(view.graphic.sigmets) == 1

    def test_notification_changed_updates_custom_text_only_when_on_custom_form(
            self, presenter, view, context, database):
        presenter.initialize()

        context.notification.sigmet.setState({'message': SIGMET_TEXT})
        assert view.customText is None

        view.formSelected.emit('custom')
        view.customText = None
        other = 'YUDD SIGMET 2 VALID 100730/101430 YUSO- YUDD SHANLON FIR SEV TS='
        context.notification.sigmet.setState({'message': other})

        assert view.customText == ('notification', 'YUDD SHANLON FIR SEV TS=')


class TestSigmetEditor:

    def test_view_and_forms_hold_no_back_references(self, editor):
        assert not hasattr(editor, 'draft')
        assert not hasattr(editor, 'header')
        assert all(not hasattr(form, 'editor') for form in editor.forms.values())
        assert all(form.state.header is editor.presenter.draft.header for form in editor.forms.values())

    def test_category_follows_designator(self, editor, presenter):
        assert presenter.draft.category() == 'SIGMET'

        editor.airmansWeather.click()
        assert presenter.draft.category() == 'AIRMET'

    def test_template_mode_starts_with_general_content(self, editor):
        assert editor.template.isChecked() is True
        assert editor.currentForm is editor.generalContent
        assert editor.graphic.isVisibleTo(editor)

    def test_the_forms_share_the_documents_header(self, editor, presenter):
        # one sequence, one validity, one area: the header describes the report
        # being written, not the form that happens to be on screen
        for form in editor.forms.values():
            assert form.state.header is presenter.draft.header

    def test_opening_the_editor_seeds_the_draft(self, editor, presenter, frozen_time):
        """The open path is the only thing that starts a draft.

        It is what makes a success handler unnecessary: a sent report ends by
        closing the editor, and the next open seeds number and period again.
        """
        editor.opened.emit()

        assert editor.generalContent.sequence.text() == '1'
        assert presenter.draft.header.sequence == '1'
        # the window is anchored to the clock, so pin that it was written and
        # that it is the draft's span, not the exact minute
        assert len(editor.generalContent.beginningTime.text()) == 6
        assert len(editor.generalContent.endingTime.text()) == 6
        assert presenter.draft.header.beginningTime == editor.generalContent.beginningTime.text()

    def test_view_clear_leaves_header_to_presenter(self, editor, presenter):
        # A view clear empties only forms/graphic; presenter.clear() is the one
        # place that empties the shared document header and notification.
        presenter.draft.header.sequence = '7'

        editor.clear()
        assert presenter.draft.header.sequence == '7'

        presenter.clear()
        assert presenter.draft.header.sequence == ''
        assert editor.generalContent.sequence.text() == ''

    def test_cancel_mode_keeps_the_graphic_visible(self, editor, presenter):
        # unlike the message composition, the canvas stays visible in
        # cancel mode; only custom content hides it
        editor.cancel.click()

        assert editor.currentForm is editor.cancelContent
        assert editor.graphic.isVisibleTo(editor)
        assert presenter.draft.designator == 'WS'

    def test_leaving_cancel_mode_needs_the_template_radio(self, editor, presenter):
        # the template/custom/cancel radios form one exclusive group while
        # the hazard radios live in another, so clicking a hazard radio
        # cannot leave cancel mode
        editor.cancel.click()
        editor.significantWeather.click()

        assert editor.currentForm is editor.cancelContent

        editor.template.click()
        assert editor.currentForm is editor.generalContent
        assert editor.graphic.isVisibleTo(editor)

    def test_custom_mode_hides_graphic(self, editor, presenter):
        editor.custom.click()

        assert editor.currentForm is editor.customForm
        assert not editor.graphic.isVisibleTo(editor)

    def test_selecting_a_form_updates_span_of_current_content(self, editor, presenter):
        editor.tropicalCyclone.click()

        assert presenter.draft.designator == 'WC'
        assert editor.currentForm.span() == validDuration('WC')

    def test_reclicking_the_checked_radio_does_not_reset_the_canvas(self, editor, presenter, monkeypatch):
        # radio clicked fires even on the already-checked radio; the path
        # gated on draft.select() must not re-run configureMode, which
        # clears the drawn sketch
        calls = []
        monkeypatch.setattr(editor.graphic, 'configureMode', lambda *args: calls.append(args))

        editor.significantWeather.click()

        assert calls == []

    def test_message_from_custom_content_appends_equals(self, editor, presenter):
        editor.custom.click()
        user_edit(editor.customForm.text, 'ZJSA SANYA FIR OBSC TS')

        message = presenter.compose()

        assert message.text.endswith('ZJSA SANYA FIR OBSC TS=')

    def test_message_composes_from_the_current_state(self, editor, presenter, conf):
        state = editor.generalContent.state
        state.header.area = 'ZJSA'
        state.header.sign = 'SIGMET'
        state.header.sequence = '2'
        state.header.beginningTime = '100930'
        state.header.endingTime = '101430'
        state.header.icao = 'ZJHK'
        state.description = 'SEV'
        state.phenomenon = 'TS'
        state.comeFrom = 'OBS'
        state.observedTime = '100800'
        state.flightLevelFormat = ''
        state.flightLevelBase = '80'
        state.flightLevelTop = '120'
        state.direction = 'NE'
        state.speed = '25'
        state.intensityChange = 'NC'

        message = presenter.compose()

        assert message.text == '\n'.join([
            'ZJSA SIGMET 2 VALID 100930/101430 ZJHK-',
            '{} SEV TS OBS AT 100800Z FL080/120 MOV NE 25KMH NC='.format(conf.firName),
        ])

    def test_a_field_that_never_collected_is_read_before_the_commit(self, editor, presenter):
        """The same guard as the TAF editor: a control whose signal never fired
        must still reach the message, because the commit entry reads it."""
        general = editor.generalContent
        general.direction.setCurrentIndex(general.direction.findText('N'))
        general.speed.setText('20')

        with QSignalBlocker(general.speed):
            general.speed.setText('45')

        editor.submitted.emit()

        assert general.state.speed == '45'
        assert 'MOV N 45' in presenter.compose().text

    def test_the_overlap_mode_writes_the_state_forecast_flag(self, editor):
        editor.generalContent.setOverlapMode('final')
        assert editor.generalContent.state.hasForecast is True

        editor.generalContent.setOverlapMode('initial')
        assert editor.generalContent.state.hasForecast is False

    def test_the_phenomenon_switch_writes_the_state_eruption_flag(self, editor):
        choose(editor.ashContent.phenomenon, 'CLD')
        assert editor.ashContent.state.isEruption is False
        assert editor.ashContent.state.phenomenon == 'CLD'

        choose(editor.ashContent.phenomenon, 'ERUPTION')
        assert editor.ashContent.state.isEruption is True
        assert editor.ashContent.state.phenomenon == 'ERUPTION'

    def test_changing_the_typhoon_intensity_reaches_the_message(self, editor, presenter):
        editor.tropicalCyclone.click()
        content = editor.typhoonContent

        choose(content.intensityChange, 'INTSF')

        assert content.state.intensityChange == 'INTSF'
        assert 'INTSF' in presenter.compose().text

    def test_changing_the_ash_intensity_reaches_the_state(self, editor, presenter):
        editor.volcanicAsh.click()
        content = editor.ashContent

        choose(content.intensityChange, 'WKN')

        assert content.state.intensityChange == 'WKN'

    def test_the_typhoon_apply_state_renders_every_state_field(self, editor, presenter):
        editor.tropicalCyclone.click()
        content = editor.typhoonContent
        state = content.state
        state.name = 'YAGI'
        state.top = '420'
        state.intensityChange = 'WKN'
        state.currentLatitude = 'N2110'
        state.currentLongitude = 'E11120'
        state.forecastLatitude = 'N2155'
        state.forecastLongitude = 'E11050'
        state.radius = '300'

        content.populate()

        assert content.name.text() == 'YAGI'
        assert content.top.text() == '420'
        assert content.intensityChange.currentText() == 'WKN'
        assert content.currentLatitude.text() == 'N2110'
        assert content.currentLongitude.text() == 'E11120'
        assert content.forecastLatitude.text() == 'N2155'
        assert content.forecastLongitude.text() == 'E11050'
        assert content.radius.text() == '300'
        assert content.state.currentLatitude == 'N2110'

    def test_the_general_apply_state_renders_the_intensity(self, editor):
        content = editor.generalContent
        content.state.intensityChange = 'INTSF'

        content.populate()

        assert content.intensityChange.currentText() == 'INTSF'
        assert content.state.intensityChange == 'INTSF'

    def test_the_typhoon_circles_use_each_locations_own_coordinates(self, editor, presenter):
        # A.6: initial and final circles must not borrow each other's longitude
        editor.tropicalCyclone.click()
        content = editor.typhoonContent
        state = content.state
        state.currentLatitude = 'N1010'
        state.currentLongitude = 'E11010'
        state.forecastLatitude = 'N2020'
        state.forecastLongitude = 'E12020'
        state.radius = '300'

        initial = content.circle('initial')
        final = content.circle('final')

        assert initial['geometry']['coordinates'] == pytest.approx([110 + 10 / 60, 10 + 10 / 60])
        assert final['geometry']['coordinates'] == pytest.approx([120 + 20 / 60, 20 + 20 / 60])

    def test_clear_resets_the_state_and_the_text_widget(self, editor, presenter):
        # was pinned as a bug (state cleared, text widget kept stale content)
        # until populate() gave clear() its write direction
        editor.customForm.text.setPlainText('SOME TEXT')
        presenter.clear()

        assert editor.customForm.state.text == ''
        assert editor.customForm.text.toPlainText() == ''

    def test_clear_empties_the_cancel_fields(self, editor, presenter):
        editor.cancel.click()
        editor.cancelContent.cancelBeginningTime.setText('100930')

        presenter.clear()

        assert editor.cancelContent.cancelBeginningTime.text() == ''
        assert editor.cancelContent.cancelSequence.currentText() == ''

    def test_clear_disables_the_forecast_time(self, editor, presenter):
        editor.generalContent.setOverlapMode('final')
        presenter.clear()

        assert not editor.generalContent.forecastTime.isEnabled()
        assert editor.generalContent.forecastTime.text() == ''

    def test_clear_resets_the_typhoon_canvas_tool(self, editor, presenter):
        editor.tropicalCyclone.click()
        editor.graphic.modeButton.click()

        presenter.clear()

        assert editor.graphic.canvas.mode == 'circle'
        assert editor.typhoonContent.state.mode == 'circle'

    def _assert_every_input_announces(self, qtbot, content):
        # the anti-miss guard for the fields() wiring: a declared input that
        # fails to fire contentChanged means a missed connect
        changed = []
        content.contentChanged.connect(lambda: changed.append(1))

        for widget in content.fields():
            del changed[:]
            if isinstance(widget, QComboBox):
                if widget.count() < 2:
                    continue
                index = 1 if widget.currentIndex() == 0 else 0
                widget.setCurrentIndex(index)
                widget.activated.emit(index)
            else:
                text = widget.text() + 'X'
                widget.setText(text)
                widget.textEdited.emit(text)
            assert changed, '{} did not announce'.format(widget.objectName())

    def test_general_inputs_announce_content_changed(self, editor, qtbot):
        self._assert_every_input_announces(qtbot, editor.generalContent)

    def test_typhoon_inputs_announce_content_changed(self, editor, qtbot):
        self._assert_every_input_announces(qtbot, editor.typhoonContent)

    def test_ash_inputs_announce_content_changed(self, editor, qtbot):
        self._assert_every_input_announces(qtbot, editor.ashContent)

    def test_cancel_inputs_announce_content_changed(self, editor, presenter, qtbot):
        editor.cancel.click()
        self._assert_every_input_announces(qtbot, editor.cancelContent)

    def test_custom_inputs_announce_content_changed(self, editor, qtbot):
        self._assert_every_input_announces(qtbot, editor.customForm)

        changed = []
        editor.customForm.contentChanged.connect(lambda: changed.append(1))
        user_edit(editor.customForm.text, 'X')
        assert changed

    def test_close_clears_sigmet_notification(self, editor, presenter, context):
        context.notification.sigmet.setState({'message': 'ZJSA SIGMET 1 VALID 100930/101430 ZJHK-'})

        editor.closed.emit()

        assert context.notification.sigmet.message() is None


class TestSigmetEditorPageSwitching:
    """The forms live in a stack, so switching cannot show two at once.

    They used to share one horizontal layout, and ``changeContent`` showed the
    new form before hiding the old one. With ``SetFixedSize`` on the main
    layout that stretched the window to the two forms' combined width for a
    frame, which showed up as a flash of extra window on the right when the
    form radios were clicked quickly.

    The stack is pinned to the size of the page it shows (``pageResize``):
    a QStackedWidget otherwise reports the largest page it holds, so the
    window kept the tall Cyclone form's height on every other form.
    """

    @pytest.fixture
    def shown(self, qtbot, editor, presenter):
        editor.show()
        qtbot.waitExposed(editor)
        return editor

    def visiblePages(self, editor):
        return [name for name, page in editor.forms.items() if page.isVisibleTo(editor)]

    def test_the_forms_are_switched_by_a_stack(self, editor):
        assert isinstance(editor.formStack, QStackedWidget)

    def test_the_canvas_is_not_one_of_the_pages(self, editor):
        # the canvas is shown alongside every form but Custom, so it is a
        # sibling of the stack, not one of the pages switched inside it
        assert editor.graphic.parent() is not editor.formStack
        assert editor.formStack.indexOf(editor.graphic) == -1
        assert editor.graphic.isVisibleTo(editor) is True

    def test_only_one_form_is_ever_visible(self, shown):
        for radio in ('tropicalCyclone', 'volcanicAsh', 'airmansWeather',
                      'significantWeather', 'cancel', 'custom'):
            getattr(shown, radio).click()

            assert len(self.visiblePages(shown)) == 1, radio

    def test_the_stack_tracks_the_current_content(self, shown):
        shown.tropicalCyclone.click()

        assert shown.formStack.currentWidget() is shown.typhoonContent
        assert self.visiblePages(shown) == ['typhoon']

    def test_the_window_keeps_one_size_across_the_forms(self, shown, qtbot):
        # the stack holds every form, so the window is the size of the largest
        # one throughout: no resize while the radios are being clicked
        sizes = []
        for radio in ('tropicalCyclone', 'volcanicAsh', 'airmansWeather',
                      'significantWeather', 'cancel'):
            getattr(shown, radio).click()
            qtbot.wait(30)
            sizes.append((shown.width(), shown.height()))

        assert len(set(sizes)) == 1, sizes

    def test_the_tallest_form_sets_the_window_height(self, shown, qtbot):
        # each form is laid out inside the stack, not squeezed to fit a
        # smaller one, so the tallest page is what the window has to be
        shown.tropicalCyclone.click()
        qtbot.wait(30)

        tallest = max(page.sizeHint().height() for page in shown.forms.values()
                      if shown.formStack.indexOf(page) != -1)

        assert shown.currentForm.height() >= tallest

    def test_every_form_fits_the_stack(self, shown, qtbot):
        # a form must never be laid out smaller than it asks for
        for radio in ('tropicalCyclone', 'volcanicAsh', 'airmansWeather',
                      'significantWeather', 'cancel'):
            getattr(shown, radio).click()
            qtbot.wait(30)

            page = shown.currentForm
            assert page.height() >= page.sizeHint().height(), radio
            assert page.width() >= page.sizeHint().width(), radio

    def test_rapid_switching_leaves_one_form_visible(self, shown, qtbot):
        for _ in range(6):
            shown.tropicalCyclone.click()
            shown.significantWeather.click()

        qtbot.wait(50)

        assert len(self.visiblePages(shown)) == 1
        assert shown.formStack.currentWidget() is shown.generalContent


class TestSigmetEditorCustomPage:
    """Custom is not a stack page.

    It is the widest form (599 against 366) and the only one that replaces the
    canvas rather than sitting beside it, so keeping it in the stack made every
    other form as wide as it. It sits in the row beside the stack instead and
    is shown or hidden; a hidden widget is skipped by the layout, so it
    reserves no width while the other forms are up.
    """

    @pytest.fixture
    def shown(self, qtbot, editor, presenter):
        editor.show()
        qtbot.waitExposed(editor)
        return editor

    def test_custom_is_not_a_page_of_the_stack(self, editor):
        assert editor.formStack.indexOf(editor.customForm) == -1

    def test_custom_hides_the_stack_and_the_canvas(self, shown):
        shown.custom.click()

        assert shown.currentForm is shown.customForm
        assert not shown.formStack.isVisibleTo(shown)
        assert not shown.graphic.isVisibleTo(shown)

    def test_custom_takes_the_whole_row(self, shown):
        shown.significantWeather.click()
        stackedWidth = shown.formStack.width()

        shown.custom.click()

        # custom is the only thing in the row when it shows
        assert shown.customForm.isVisibleTo(shown)
        assert shown.customForm.width() > stackedWidth

    def test_a_hidden_custom_reserves_no_width(self, shown):
        # this is why it can stay in the row the whole time: the layout skips
        # hidden items, so nothing of custom's width is held back
        assert not shown.customForm.isVisibleTo(shown)

        hidden_width = shown.customForm.sizeHint().width()
        row = shown.contentLayout.geometry()
        stack = shown.formStack.geometry()
        canvas = shown.graphic.geometry()

        # the two visible columns fit without custom's width
        assert stack.left() == row.left()
        assert canvas.right() < row.left() + hidden_width + canvas.width()

    def test_custom_yields_the_row_again(self, shown):
        shown.custom.click()
        shown.template.click()

        assert not shown.customForm.isVisibleTo(shown)
        assert shown.formStack.isVisibleTo(shown)
        assert shown.graphic.isVisibleTo(shown)
        assert shown.currentForm is shown.generalContent

    def test_custom_can_be_entered_twice(self, shown):
        shown.custom.click()
        shown.template.click()
        shown.custom.click()

        assert shown.currentForm is shown.customForm
        assert shown.customForm.isVisibleTo(shown)
        assert not shown.formStack.isVisibleTo(shown)

    def test_the_template_forms_are_all_the_same_width(self, editor):
        # this is what lets a plain width come out right now that the stack
        # no longer holds the wide custom form: the pages agree on a width
        widths = {editor.forms[name].sizeHint().width()
                  for name in ('general', 'typhoon', 'ash', 'airmet')}

        assert len(widths) == 1, widths

    def test_custom_is_wider_than_every_page_in_the_stack(self, editor):
        # the reason custom cannot share the stack
        pages = [editor.forms[name] for name in ('general', 'typhoon', 'ash', 'airmet')]

        assert editor.customForm.sizeHint().width() > max(p.sizeHint().width() for p in pages)


class TestSigmetCustomText:
    """The custom form renders the text the presenter resolved.

    The source policy -- notification first, the stored report after it -- is
    the presenter's, so these tests set up the two sources and check what the
    form does with the answer: strip the FIR and the terminator, follow the
    source with the api sign, and clear both when there is nothing to show.
    """

    def test_a_waiting_notification_becomes_the_text(self, editor, presenter, context):
        context.notification.sigmet.setState({'message': SIGMET_TEXT})

        editor.custom.click()

        assert editor.customForm.text.toPlainText() == 'OBSC TS'
        assert editor.customForm.state.text == 'OBSC TS'

    def test_the_api_sign_follows_the_source(self, editor, presenter, context, database):
        context.notification.sigmet.setState({'message': SIGMET_TEXT})
        editor.custom.click()

        assert not editor.customForm.apiSign.isHidden()

        store_sigmet(database, SIGMET_TEXT)
        context.notification.sigmet.clear()
        presenter.updateCustomText()

        assert editor.customForm.text.toPlainText() == 'OBSC TS'
        assert editor.customForm.apiSign.isHidden()

    def test_the_stored_report_fills_the_text(self, editor, presenter, database):
        store_sigmet(database, SIGMET_TEXT)

        editor.custom.click()

        assert editor.customForm.text.toPlainText() == 'OBSC TS'

    def test_a_designator_with_neither_source_clears_both(self, editor, presenter, context, database):
        context.notification.sigmet.setState({'message': SIGMET_TEXT})
        editor.custom.click()
        assert editor.customForm.text.toPlainText() == 'OBSC TS'

        # WV has no notification and nothing stored: the icon from WS must go
        # with the text, not outlive it. Custom keeps whichever product the
        # hazard radios are on, so the product moves through the stack first.
        editor.template.click()
        editor.volcanicAsh.click()
        editor.custom.click()

        assert editor.customForm.text.toPlainText() == ''
        assert editor.customForm.state.text == ''
        assert editor.customForm.apiSign.isHidden()

    def test_a_message_arriving_while_the_form_is_open_shows_up(self, editor, presenter, context):
        editor.custom.click()
        assert editor.customForm.text.toPlainText() == ''

        # the monitor hands the received message over through the notification event
        context.notification.sigmet.setState({'message': SIGMET_TEXT})

        assert editor.customForm.text.toPlainText() == 'OBSC TS'

    def test_form_notified_updates_editor_notification_area(self, editor, frozen_time):
        editor.generalContent.beginningTime.setText('100800')
        editor.generalContent.endingTime.setText('102300')
        editor.generalContent.collect()
        editor.generalContent.validate()

        assert editor.notificationArea.text() == 'Valid period more than the permitted hours'

    def test_trim_toggle_recomputes_sigmet_geometries_through_presenter(self, editor, presenter, context, monkeypatch):
        sig = Sigmet(
            type='WS',
            heading='YUDD SIGMET 1 VALID 100730/101430 YUSO-',
            text='YUDD SHANLON FIR OBSC TS=',
        )
        context.current.setState([sig])
        seen_trims = []
        monkeypatch.setattr(
            presenter,
            'sigmetGeometries',
            lambda **kwargs: (seen_trims.append(kwargs['trim']) or []),
        )

        editor.graphic.trimShapesAction.setChecked(False)

        assert seen_trims == [False]

    def test_presenter_sigmet_geometries_respects_trim_flag(self, context, conf):
        text = 'YUDD SHANLON FIR OBSC TS WI N1400 E10800 - N1400 E11000 - N1600 E11000 - N1600 E10800 - N1400 E10800='
        sig = Sigmet(
            type='WS',
            heading='YUDD SIGMET 1 VALID 100730/101430 YUSO-',
            text=text,
        )
        context.current.setState([sig])
        presenter = SigmetPresenter(None, context, conf)

        trimmed = presenter.sigmetGeometries(category='SIGMET', trim=True)
        untrimmed = presenter.sigmetGeometries(category='SIGMET', trim=False)

        assert len(trimmed) == 1
        assert len(untrimmed) == 1
        assert trimmed[0] != untrimmed[0]


class TestSigmetTyphoon:

    def test_top_and_radius_limit_length_to_three(self, editor):
        typhoon = editor.typhoonContent
        assert typhoon.top.maxLength() == 3
        assert typhoon.radius.maxLength() == 3

    def test_set_typhoon_location_with_only_final_feature_clears_radius(self, editor):
        typhoon = editor.typhoonContent
        typhoon.radius.setText('150')

        collections = {
            'type': 'FeatureCollection',
            'features': [
                {
                    'type': 'Feature',
                    'properties': {'location': 'final'},
                    'geometry': {'type': 'Point', 'coordinates': [120.0, 20.0]},
                }
            ],
        }
        typhoon.setTyphoonLocation(collections)

        assert typhoon.forecastLongitude.text() != ''
        assert typhoon.forecastLatitude.text() != ''
        assert typhoon.radius.text() == ''


class TestSigmetPipeline:
    """Stage 4 regressions: unidirectional pipeline behaviour in SIGMET forms."""

    def test_typhoon_map_update_syncs_state_without_circle_echo_or_forecast_overwrite(self, editor, frozen_time):
        editor.tropicalCyclone.click()
        typhoon = editor.typhoonContent
        typhoon.setLocationMode('circle')
        typhoon.speed.setText('20')
        typhoon.speed.textEdited.emit('20')
        typhoon.observedTime.setText('0800')
        typhoon.observedTime.textEdited.emit('0800')
        typhoon.forecastTime.setText('1400')
        typhoon.forecastTime.textEdited.emit('1400')

        emitted = []
        typhoon.circleChanged.connect(emitted.append)

        collections = {
            'type': 'FeatureCollection',
            'features': [
                {
                    'type': 'Feature',
                    'properties': {'location': 'initial', 'radius': 200},
                    'geometry': {'type': 'Point', 'coordinates': [115.0, 20.0]},
                },
                {
                    'type': 'Feature',
                    'properties': {'location': 'final'},
                    'geometry': {'type': 'Point', 'coordinates': [120.0, 22.0]},
                },
            ],
        }
        typhoon.setTyphoonLocation(collections)

        assert emitted == []
        assert typhoon.state.currentLongitude == 'E11500'
        assert typhoon.state.currentLatitude == 'N2000'
        assert typhoon.state.forecastLongitude == 'E12000'
        assert typhoon.state.forecastLatitude == 'N2200'
        assert typhoon.state.radius == '200'

    def test_typhoon_user_speed_edit_updates_forecast_state_and_emits_circle_changed(self, editor, frozen_time):
        editor.tropicalCyclone.click()
        typhoon = editor.typhoonContent
        typhoon.setLocationMode('circle')
        typhoon.setOverlapMode('final')
        typhoon.currentLatitude.setText('N2000')
        typhoon.currentLatitude.textEdited.emit('N2000')
        typhoon.currentLongitude.setText('E11500')
        typhoon.currentLongitude.textEdited.emit('E11500')
        typhoon.radius.setText('150')
        typhoon.radius.textEdited.emit('150')
        typhoon.observedTime.setText('0800')
        typhoon.observedTime.textEdited.emit('0800')
        typhoon.forecastTime.setText('1400')
        typhoon.forecastTime.textEdited.emit('1400')

        emitted = []
        typhoon.circleChanged.connect(emitted.append)

        typhoon.speed.setText('20')
        typhoon.speed.textEdited.emit('20')

        assert typhoon.forecastLatitude.text() != ''
        assert typhoon.state.forecastLatitude == typhoon.forecastLatitude.text()
        assert typhoon.state.forecastLongitude == typhoon.forecastLongitude.text()
        assert len(emitted) == 1

    def test_overlap_mode_final_syncs_observation_and_forecast_state(self, editor, frozen_time):
        editor.opened.emit()
        general = editor.generalContent

        editor.setOverlapMode('final')

        assert general.state.comeFrom == 'OBS'
        assert general.state.observedTime == general.beginningTime.text()[2:]
        assert general.state.hasForecast is True
        assert general.state.forecastTime == general.endingTime.text()[2:]
        assert general.forecastTime.isEnabled()

    def test_advisory_import_commits_state_immediately(self, editor):
        editor.tropicalCyclone.click()
        typhoon = editor.typhoonContent
        typhoon.text.setPlainText(
            'TC ADVISORY\n'
            'DTG: 20260610/0600Z\n'
            'TC: YAGI\n'
            'OBS PSN: 20260610/0600Z N2000 E11500\n'
            'MOV: W 15KT\n'
            'FCST PSN +06HR: 20260610/1200Z N2100 E11400\n'
        )
        assert typhoon.state.name == 'YAGI'
        assert typhoon.name.text() == 'YAGI'
        assert typhoon.state.comeFrom == 'OBS'
        assert typhoon.state.observedTime == '0600'
        assert typhoon.state.currentLatitude == 'N2000'
        assert typhoon.state.currentLongitude == 'E11500'


if __name__ == '__main__':
    pytest.main([__file__])
