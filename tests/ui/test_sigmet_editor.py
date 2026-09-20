"""Tests for the SIGMET editor widgets in tafor/ui/widgets/sigmet.py.

The field-group parts are covered by test_sigmet_parts.py; here we exercise
the BaseSigmet header behavior (period/durations/sequence) and the concrete
editors. Advisory import panels and typhoon geometry are out of scope.

parseTime resolves day/hour texts against the wall clock and rolls a past
time into the next month, which would make every assertion date-dependent.
The tests freeze the process-wide clock (shared frozen_time fixture) at
2026-06-10 08:00 UTC so that '100800' means June 10 08:00 deterministically.
"""

import datetime

import pytest

from tafor.core.models import Sigmet
from tafor.core.repositories import SigmetRepository
from tafor.core.sigmet import SigmetDraft
from tafor.core.sigmet.compose import validDuration
from tafor.ui.widgets.sigmet import SigmetCancel, SigmetCustom, SigmetGeneral


MOMENT = datetime.datetime(2026, 6, 10, 8, 0)


class EditorStub:
    """The slice of SigmetEditor the widgets read: the draft-derived facts.

    Qt-free, and derived from a real draft so that switching the form here
    moves the designator and the span exactly as the editor does.
    """

    def __init__(self, draft=None):
        self.draft = draft or SigmetDraft()

    @property
    def designator(self):
        return self.draft.designator

    @property
    def span(self):
        return self.draft.span()

    def category(self):
        return self.draft.category()


def editor_stub(designator='WS'):
    return EditorStub(SigmetDraft(designator=designator))


@pytest.fixture
def editor():
    return editor_stub()


@pytest.fixture
def general(qtbot, conf, context, database, editor, frozen_time):
    widget = SigmetGeneral(editor=editor, conf=conf, context=context,
                           repository=SigmetRepository(database))
    widget.initState()
    qtbot.addWidget(widget)
    return widget


@pytest.fixture
def custom(qtbot, conf, context, database, editor, frozen_time):
    widget = SigmetCustom(editor=editor, conf=conf, context=context,
                          repository=SigmetRepository(database))
    widget.initState()
    qtbot.addWidget(widget)
    return widget


@pytest.fixture
def cancel(qtbot, conf, context, database, editor, frozen_time):
    widget = SigmetCancel(editor=editor, conf=conf, context=context,
                          repository=SigmetRepository(database))
    widget.initState()
    qtbot.addWidget(widget)
    return widget


def seed_sigmet(database, heading, text, created=None):
    sigmet = Sigmet(type='WS', heading=heading, text=text,
                    created=created or datetime.datetime.utcnow())
    with database.session() as session:
        session.add(sigmet)
    return sigmet


def cancelEditorSigmet():
    return Sigmet(type='WS', heading='ZJSA SIGMET 2 VALID 100930/101430 ZJHK-',
                  text='ZJSA SANYA FIR OBSC TS=')


class TestSigmetGeneral:

    def test_initial_durations_follow_the_period(self, general):
        assert general.state.durations == (MOMENT + datetime.timedelta(minutes=10),
                                     MOMENT + datetime.timedelta(hours=4, minutes=10))

    def test_update_durations_parses_both_times(self, general):
        general.beginningTime.setText('100800')
        general.endingTime.setText('101400')

        assert general.state.durations == (MOMENT, MOMENT + datetime.timedelta(hours=6))

    def test_incomplete_times_clear_durations(self, general):
        general.beginningTime.setText('100800')
        general.endingTime.setText('101400')
        general.endingTime.clear()

        assert general.state.durations is None

    def test_validate_period_accepts_the_suggested_period(self, general):
        general.validatePeriod()

        assert general.beginningTime.text()
        assert general.endingTime.text()

    def test_validate_period_clears_end_before_start(self, general):
        general.beginningTime.setText('100800')
        general.endingTime.setText('100800')

        general.validatePeriod()

        assert general.endingTime.text() == ''

    def test_validate_period_too_long_clears_the_ending_time(self, general):
        # four hours is the editor's span; '102300' overshoots it
        general.beginningTime.setText('100800')
        general.endingTime.setText('102300')

        general.validatePeriod()

        assert general.endingTime.text() == ''
        assert general.beginningTime.text() == '100800'

    def test_validate_period_too_long_shows_a_message(self, general, context):
        general.beginningTime.setText('100800')
        general.endingTime.setText('102300')

        texts = []
        context.event.editorMessage.connect(lambda title, text: texts.append(text))

        general.validatePeriod()

        assert texts == ['Valid period more than the permitted hours']

    def test_validate_period_clears_far_future_start(self, general):
        general.beginningTime.setText('200800')
        general.endingTime.setText('201400')

        general.validatePeriod()

        assert general.beginningTime.text() == ''

    def test_the_period_follows_the_drafts_span(self, general, editor):
        editor.draft.select('typhoon')

        general.initState()

        assert general.span() == validDuration('WC')
        assert general.state.durations[1] - general.state.durations[0] == datetime.timedelta(hours=6)

    def test_sequence_counts_todays_sigmets(self, qtbot, conf, context, database, frozen_time):
        seed_sigmet(database, 'ZJSA SIGMET 1 VALID 100730/101430 ZJHK-', 'ZJSA SANYA FIR OBSC TS=')

        widget = SigmetGeneral(editor=editor_stub(), conf=conf, context=context,
                               repository=SigmetRepository(database))
        widget.initState()
        qtbot.addWidget(widget)

        assert widget.sequence.text() == '2'

    def test_phenomenon_list_follows_description(self, general):
        general.description.setCurrentText('SEV')
        phenomena = [general.phenomenon.itemText(i) for i in range(general.phenomenon.count())]
        assert 'TURB' in phenomena
        assert general.state.description == 'SEV'

        general.description.setCurrentText('HVY')
        phenomena = [general.phenomenon.itemText(i) for i in range(general.phenomenon.count())]
        assert phenomena == ['DS', 'SS']

    def test_flight_level_format_follows_phenomenon(self, general):
        general.setFlightLevelFormat('TS')
        formats = [general.format.itemText(i) for i in range(general.format.count())]
        assert 'TOP' in formats

        general.setFlightLevelFormat('TURB')
        formats = [general.format.itemText(i) for i in range(general.format.count())]
        assert 'TOP' not in formats


class TestSigmetCustom:

    def test_sequence_starts_at_one_without_history(self, custom):
        assert custom.sequence.text() == '1'

    def test_filter_text_uppercases_and_keeps_allowed_characters(self, custom):
        custom.text.setPlainText('embd ts (obs) 12,3 a-b.c/d')

        assert custom.text.toPlainText() == 'EMBD TS (OBS) 12,3 A-B.C/D'

    def test_filter_text_strips_unwanted_characters(self, custom):
        # '=' must not survive: the state closes the message with it
        custom.text.setPlainText('AB#CD$12=')

        assert custom.text.toPlainText() == 'ABCD12'

    def test_sync_to_state_strips_whitespace(self, custom):
        custom.text.setPlainText(' TS OBS ')

        assert custom.state.text == 'TS OBS'


class TestSigmetCancel:

    def test_designator_follows_the_editor(self, cancel):
        assert cancel.designator() == 'WS'

    def test_component_update_lists_active_sequences(self, cancel, context):
        context.current.setState([cancelEditorSigmet()])

        cancel.componentUpdate()

        assert cancel.prevs == [('2', '100930/101430')]
        assert cancel.cancelSequence.currentText() == '2'

    def test_component_update_skips_cnl(self, cancel, context):
        cnl = Sigmet(type='WS', heading='ZJSA SIGMET 2 VALID 100930/101430 ZJHK-',
                     text='ZJSA SANYA FIR CNL SIGMET 1 100930/101430=')
        context.current.setState([cnl])

        cancel.componentUpdate()

        assert cancel.prevs == []
        assert cancel.cancelSequence.count() == 0

    def test_find_valid_matches_by_sequence(self, cancel, context):
        context.current.setState([cancelEditorSigmet()])
        cancel.componentUpdate()

        assert cancel.findValid('2') == '100930/101430'
        assert cancel.findValid(0) == '100930/101430'
        assert cancel.findValid('9') is None
        assert cancel.findValid(9) is None

    def test_set_valids_fills_the_cancelled_period(self, cancel, context):
        context.current.setState([cancelEditorSigmet()])
        cancel.componentUpdate()

        cancel.setValids('2')

        assert cancel.cancelBeginningTime.text() == '100930'
        assert cancel.cancelEndingTime.text() == '101430'
        assert cancel.endingTime.text() == '101430'

    def test_set_valids_unknown_sequence_clears_fields(self, cancel, context):
        context.current.setState([cancelEditorSigmet()])
        cancel.componentUpdate()

        cancel.setValids('9')

        assert cancel.cancelBeginningTime.text() == ''
        assert cancel.cancelEndingTime.text() == ''


if __name__ == '__main__':
    pytest.main([__file__])
