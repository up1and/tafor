"""Tests for the SIGMET editor widgets in tafor/ui/forms/sigmet.py.

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
from tafor.ui.dialogs import SigmetPresenter
from tafor.ui.forms import SigmetCancel, SigmetCustom, SigmetGeneral


MOMENT = datetime.datetime(2026, 6, 10, 8, 0)


class EditorStub:
    """The slice of SigmetEditor the widgets read: the draft-derived facts.

    Qt-free, and derived from a real draft so that switching the form here
    moves the designator and the span exactly as the editor does.
    """

    def __init__(self, draft=None):
        self.draft = draft or SigmetDraft()
        self.notifications = []

    @property
    def designator(self):
        return self.draft.designator

    @property
    def span(self):
        return self.draft.span()

    def category(self):
        return self.draft.category()

    def showNotification(self, editorName, message):
        self.notifications.append((editorName, message))


def editor_stub(designator='WS'):
    return EditorStub(SigmetDraft(designator=designator))


@pytest.fixture
def editor():
    return editor_stub()


@pytest.fixture
def general(qtbot, conf, editor, frozen_time):
    widget = SigmetGeneral(header=editor.draft.header, editor=editor, conf=conf)
    render(widget, 1)
    qtbot.addWidget(widget)
    return widget


@pytest.fixture
def custom(qtbot, conf, editor, frozen_time):
    widget = SigmetCustom(header=editor.draft.header, editor=editor, conf=conf)
    render(widget, 1)
    qtbot.addWidget(widget)
    return widget


@pytest.fixture
def cancel(qtbot, conf, editor, frozen_time):
    widget = SigmetCancel(header=editor.draft.header, editor=editor, conf=conf)
    render(widget, 1)
    qtbot.addWidget(widget)
    return widget


def render(widget, sequence):
    """The two calls the editor makes when a draft begins in this form: the
    number, then the period. The form's own data (candidates, custom text) is
    fed separately, by the tests that care about it."""
    widget.setSequence(sequence)
    widget.resetPeriod()


def candidates(context, conf, designator='WS'):
    """The candidate list the editor hands the dropdown, from the one source
    the canvas reads too."""
    return SigmetPresenter(None, context, conf).sigmets(designator=designator)


def seed_sigmet(database, heading, text, created=None):
    sigmet = Sigmet(type='WS', heading=heading, text=text,
                    created=created or datetime.datetime.utcnow())
    with database.session() as session:
        session.add(sigmet)
    return sigmet


def cancelEditorSigmet():
    return Sigmet(type='WS', heading='ZJSA SIGMET 2 VALID 100930/101430 ZJHK-',
                  text='ZJSA SANYA FIR OBSC TS=')


def dayBoundaryRecords():
    """A report issued before midnight still in force, and today's fresh one
    reusing its sequence number: one '2' on two dropdown rows."""
    older = Sigmet(type='WS', heading='ZJSA SIGMET 2 VALID 092330/100500 ZJHK-',
                   text='ZJSA SANYA FIR OBSC TS=')
    return [older, cancelEditorSigmet()]


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

    def test_validate_period_too_long_shows_a_message(self, general):
        general.beginningTime.setText('100800')
        general.endingTime.setText('102300')

        general.validatePeriod()

        assert general.editor.notifications == [
            ('sigmet', 'Valid period more than the permitted hours')
        ]

    def test_validate_period_clears_far_future_start(self, general):
        general.beginningTime.setText('200800')
        general.endingTime.setText('201400')

        general.validatePeriod()

        assert general.beginningTime.text() == ''

    def test_the_period_follows_the_drafts_span(self, general, editor):
        editor.draft.select('typhoon')

        render(general, 1)

        assert general.span() == validDuration('WC')
        assert general.state.durations[1] - general.state.durations[0] == datetime.timedelta(hours=6)

    def test_the_header_renders_the_sequence_it_was_handed(self, general):
        render(general, 7)

        assert general.sequence.text() == '7'
        assert general.state.header.sequence == '7'

    def test_sequence_counts_todays_sigmets(self, conf, context, database, frozen_time):
        seed_sigmet(database, 'ZJSA SIGMET 1 VALID 100730/101430 ZJHK-', 'ZJSA SANYA FIR OBSC TS=')

        presenter = SigmetPresenter(None, context, conf, SigmetRepository(database))

        assert presenter.nextSequence('WS') == 2

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

    def test_set_candidates_lists_active_sequences(self, cancel, context, conf):
        context.current.setState([cancelEditorSigmet()])

        cancel.setCandidates(candidates(context, conf))

        assert cancel.cancelSequence.count() == 1
        assert cancel.cancelSequence.itemText(0) == '2'
        assert cancel.cancelSequence.itemData(0) == '100930/101430'
        assert cancel.cancelSequence.currentText() == '2'

    def test_find_valid_matches_by_sequence(self, cancel, context, conf):
        context.current.setState([cancelEditorSigmet()])
        cancel.setCandidates(candidates(context, conf))

        assert cancel.findValid('2') == '100930/101430'
        assert cancel.findValid(0) == '100930/101430'
        assert cancel.findValid('9') is None
        assert cancel.findValid(9) is None
        assert cancel.findValid(-1) is None

    def test_set_valids_fills_the_cancelled_period(self, cancel, context, conf):
        context.current.setState([cancelEditorSigmet()])
        cancel.setCandidates(candidates(context, conf))

        cancel.setValids('2')

        assert cancel.cancelBeginningTime.text() == '100930'
        assert cancel.cancelEndingTime.text() == '101430'
        assert cancel.endingTime.text() == '101430'

    def test_set_valids_unknown_sequence_clears_fields(self, cancel, context, conf):
        context.current.setState([cancelEditorSigmet()])
        cancel.setCandidates(candidates(context, conf))

        cancel.setValids('9')

        assert cancel.cancelBeginningTime.text() == ''
        assert cancel.cancelEndingTime.text() == ''

    def test_same_numbered_rows_resolve_by_row(self, cancel, context, conf):
        context.current.setState(dayBoundaryRecords())
        cancel.setCandidates(candidates(context, conf))

        assert cancel.cancelSequence.itemText(0) == '2'
        assert cancel.cancelSequence.itemText(1) == '2'

        cancel.setValids(0)
        assert cancel.cancelBeginningTime.text() == '092330'
        assert cancel.cancelEndingTime.text() == '100500'

        cancel.setValids(1)
        assert cancel.cancelBeginningTime.text() == '100930'
        assert cancel.cancelEndingTime.text() == '101430'

    def test_switching_between_same_numbered_rows_fires(self, cancel, context, conf):
        context.current.setState(dayBoundaryRecords())
        cancel.setCandidates(candidates(context, conf))

        # Identical texts keep currentTextChanged silent between the rows;
        # only the index change carries the pick to the second record.
        cancel.cancelSequence.setCurrentIndex(1)

        assert cancel.cancelBeginningTime.text() == '100930'
        assert cancel.cancelEndingTime.text() == '101430'

        cancel.cancelSequence.setCurrentIndex(0)

        assert cancel.cancelBeginningTime.text() == '092330'
        assert cancel.cancelEndingTime.text() == '100500'


if __name__ == '__main__':
    pytest.main([__file__])
