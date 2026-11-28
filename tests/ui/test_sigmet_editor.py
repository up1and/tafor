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
from tafor.ui.forms import SigmetAsh, SigmetCancel, SigmetCustom, SigmetGeneral


MOMENT = datetime.datetime(2026, 6, 10, 8, 0)


@pytest.fixture
def draft():
    return SigmetDraft()


@pytest.fixture
def general(qtbot, conf, draft, frozen_time):
    widget = SigmetGeneral(header=draft.header, conf=conf)
    begin(widget, 1)
    qtbot.addWidget(widget)
    return widget


@pytest.fixture
def custom(qtbot, conf, draft, frozen_time):
    widget = SigmetCustom(header=draft.header, conf=conf)
    begin(widget, 1)
    qtbot.addWidget(widget)
    return widget


@pytest.fixture
def cancel(qtbot, conf, draft, frozen_time):
    widget = SigmetCancel(header=draft.header, conf=conf)
    begin(widget, 1)
    qtbot.addWidget(widget)
    return widget


def begin(widget, sequence):
    """The calls the editor makes when a draft begins in this form: the number,
    then the period."""
    widget.setSequence(sequence)
    widget.resetPeriod()


def choose(combo, text):
    """Pick a combo entry the way the operator does."""
    index = combo.findText(text)
    combo.setCurrentIndex(index)
    combo.activated.emit(index)


def user_edit(widget, text):
    """Type into the plain text edit, the way an operator does."""
    widget.setPlainText(text)


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
        general.beginningTime.textEdited.emit('100800')
        general.endingTime.setText('101400')
        general.endingTime.textEdited.emit('101400')

        assert general.state.durations == (MOMENT, MOMENT + datetime.timedelta(hours=6))

    def test_incomplete_times_clear_durations(self, general):
        general.beginningTime.setText('100800')
        general.beginningTime.textEdited.emit('100800')
        general.endingTime.setText('101400')
        general.endingTime.textEdited.emit('101400')
        general.endingTime.clear()
        general.endingTime.textEdited.emit('')

        assert general.state.durations is None

    def test_validate_period_accepts_the_suggested_period(self, general):
        general.collect()
        general.validate()

        assert general.beginningTime.text()
        assert general.endingTime.text()

    def test_validate_period_clears_end_before_start(self, general):
        general.beginningTime.setText('100800')
        general.endingTime.setText('100800')

        general.collect()
        general.validate()

        assert general.endingTime.text() == ''

    def test_validate_period_too_long_clears_the_ending_time(self, general):
        # four hours is the editor's span; '102300' overshoots it
        general.beginningTime.setText('100800')
        general.endingTime.setText('102300')

        general.collect()
        general.validate()

        assert general.endingTime.text() == ''
        assert general.beginningTime.text() == '100800'

    def test_validate_period_too_long_shows_a_message(self, general):
        seen = []
        general.notified.connect(seen.append)
        general.beginningTime.setText('100800')
        general.endingTime.setText('102300')

        general.collect()
        general.validate()

        assert seen == ['Valid period more than the permitted hours']

    def test_validate_period_clears_far_future_start(self, general):
        general.beginningTime.setText('200800')
        general.endingTime.setText('201400')

        general.collect()
        general.validate()

        assert general.beginningTime.text() == ''

    def test_the_period_follows_the_drafts_span(self, general, draft):
        draft.select('typhoon')

        begin(general, 1)

        assert general.span() == validDuration('WC')
        assert general.state.durations[1] - general.state.durations[0] == datetime.timedelta(hours=6)

    def test_the_header_renders_the_sequence_it_was_handed(self, general):
        begin(general, 7)

        assert general.sequence.text() == '7'
        assert general.state.header.sequence == '7'

    def test_a_header_change_does_not_revert_the_parts_being_rendered(self, general):
        # The header is written before the parts. A header write must not
        # collect the parts from their old widgets and undo what populate() wrote.
        general.state.header.sequence = '7'
        general.state.comeFrom = 'OBS'
        general.state.observedTime = '0750'
        general.state.flightLevelFormat = 'TOP'
        general.state.flightLevelTop = '360'
        general.state.direction = 'W'
        general.state.speed = '20'

        general.populate()

        assert general.sequence.text() == '7'
        assert general.comeFrom.currentText() == 'OBS'
        assert general.observedTime.text() == '0750'
        assert general.format.currentText() == 'TOP'
        assert general.top.text() == '360'
        assert general.direction.currentText() == 'W'
        assert general.speed.text() == '20'
        assert general.state.observedTime == '0750'
        assert general.state.flightLevelTop == '360'
        assert general.state.speed == '20'

    def test_a_programmatic_write_does_not_commit(self, general):
        general.observedTime.setText('0750')

        assert general.state.observedTime == ''

        general.observedTime.textEdited.emit('0750')
        assert general.state.observedTime == '0750'

    def test_sequence_counts_todays_sigmets(self, conf, context, database, frozen_time):
        seed_sigmet(database, 'ZJSA SIGMET 1 VALID 100730/101430 ZJHK-', 'ZJSA SANYA FIR OBSC TS=')

        presenter = SigmetPresenter(None, context, conf, SigmetRepository(database))

        assert presenter.nextSequence('WS') == 2

    def test_phenomenon_list_follows_description(self, general):
        choose(general.description, 'SEV')
        phenomena = [general.phenomenon.itemText(i) for i in range(general.phenomenon.count())]
        assert 'TURB' in phenomena
        assert general.state.description == 'SEV'

        choose(general.description, 'HVY')
        phenomena = [general.phenomenon.itemText(i) for i in range(general.phenomenon.count())]
        assert phenomena == ['DS', 'SS']

    def test_flight_level_format_follows_phenomenon(self, general):
        formats = [general.format.itemText(i) for i in range(general.format.count())]
        assert 'TOP' in formats

        choose(general.description, 'SEV')
        formats = [general.format.itemText(i) for i in range(general.format.count())]
        assert 'TOP' not in formats


class TestSigmetCustom:

    def test_sequence_starts_at_one_without_history(self, custom):
        assert custom.sequence.text() == '1'

    def test_filter_text_uppercases_and_keeps_allowed_characters(self, custom):
        user_edit(custom.text, 'embd ts (obs) 12,3 a-b.c/d')

        assert custom.text.toPlainText() == 'EMBD TS (OBS) 12,3 A-B.C/D'

    def test_filter_text_strips_unwanted_characters(self, custom):
        # '=' must not survive: the state closes the message with it
        user_edit(custom.text, 'AB#CD$12=')

        assert custom.text.toPlainText() == 'ABCD12'

    def test_sync_to_state_strips_whitespace(self, custom):
        user_edit(custom.text, ' TS OBS ')

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

    def test_choosing_a_row_fills_the_cancelled_period(self, cancel, context, conf):
        context.current.setState([cancelEditorSigmet()])
        cancel.setCandidates(candidates(context, conf))

        line = cancel.cancelSequence.lineEdit()
        line.setText('1')
        line.textEdited.emit('1')
        cancel.cancelSequence.activated[int].emit(0)

        assert cancel.cancelBeginningTime.text() == '100930'
        assert cancel.cancelEndingTime.text() == '101430'
        assert cancel.endingTime.text() == '101430'

    def test_typed_unknown_sequence_clears_the_cancelled_period(self, cancel, context, conf):
        context.current.setState([cancelEditorSigmet()])
        cancel.setCandidates(candidates(context, conf))

        line = cancel.cancelSequence.lineEdit()
        line.setText('9')
        line.textEdited.emit('9')

        assert cancel.cancelBeginningTime.text() == ''
        assert cancel.cancelEndingTime.text() == ''

    def test_same_numbered_rows_resolve_by_row(self, cancel, context, conf):
        context.current.setState(dayBoundaryRecords())
        cancel.setCandidates(candidates(context, conf))

        assert cancel.cancelSequence.itemText(0) == '2'
        assert cancel.cancelSequence.itemText(1) == '2'

        cancel.cancelSequence.activated[int].emit(1)
        assert cancel.cancelBeginningTime.text() == '100930'
        assert cancel.cancelEndingTime.text() == '101430'

        cancel.cancelSequence.activated[int].emit(0)
        assert cancel.cancelBeginningTime.text() == '092330'
        assert cancel.cancelEndingTime.text() == '100500'

    def test_switching_between_same_numbered_rows_fires(self, cancel, context, conf):
        context.current.setState(dayBoundaryRecords())
        cancel.setCandidates(candidates(context, conf))

        # Identical texts keep the text channel silent between the rows; the
        # pick carries the index, and the index names the record.
        cancel.cancelSequence.setCurrentIndex(1)
        cancel.cancelSequence.activated[int].emit(1)

        assert cancel.cancelBeginningTime.text() == '100930'
        assert cancel.cancelEndingTime.text() == '101430'

        cancel.cancelSequence.setCurrentIndex(0)
        cancel.cancelSequence.activated[int].emit(0)

        assert cancel.cancelBeginningTime.text() == '092330'
        assert cancel.cancelEndingTime.text() == '100500'

    def test_typing_a_cancel_sequence_commits_the_candidate_period(
            self, cancel, qtbot, context, conf):
        context.current.setState([cancelEditorSigmet()])
        cancel.setCandidates(candidates(context, conf))

        line = cancel.cancelSequence.lineEdit()
        line.clear()
        line.setFocus()
        qtbot.keyClicks(line, '2')

        assert cancel.state.cancelSequence == '2'
        assert cancel.state.cancelBeginningTime == '100930'
        assert cancel.state.cancelEndingTime == '101430'


class TestStage4SigmetPipeline:
    """Stage 4 regressions: period/flight-level validation, populate order, and clear defaults."""

    def test_validate_period_clears_both_widget_and_state_without_ghost_commit(self, general):
        general.beginningTime.setText('100800')
        general.beginningTime.textEdited.emit('100800')
        general.endingTime.setText('102300')
        general.endingTime.textEdited.emit('102300')

        general.endingTime.editingFinished.emit()

        assert general.endingTime.text() == ''
        assert general.state.header.endingTime == ''
        assert general.state.durations is None

    def test_flight_level_validation_clears_both_widget_and_state_and_notifies(self, general):
        seen = []
        general.notified.connect(seen.append)
        choose(general.format, '')
        general.base.setText('360')
        general.base.textEdited.emit('360')
        general.top.setText('200')
        general.top.textEdited.emit('200')

        general.top.editingFinished.emit()

        assert general.top.text() == ''
        assert general.state.flightLevelTop == ''
        assert seen == ['The top flight level needs to be greater than the base flight level']

    def test_general_populate_preserves_flight_level_across_description_change(self, general):
        general.state.description = 'SEV'
        general.state.phenomenon = 'TURB'
        general.state.flightLevelFormat = 'ABV'
        general.state.flightLevelBase = '120'
        general.state.flightLevelTop = ''

        general.populate()

        assert general.description.currentText() == 'SEV'
        assert general.phenomenon.currentText() == 'TURB'
        assert general.format.currentText() == 'ABV'
        assert general.base.text() == '120'
        assert general.state.flightLevelFormat == 'ABV'
        assert general.state.flightLevelBase == '120'

    def test_ash_populate_does_not_mutate_state_or_emit_content_changed(self, qtbot, conf, draft):
        ash = SigmetAsh(header=draft.header, conf=conf)
        qtbot.addWidget(ash)
        ash.state.phenomenon = 'CLD'
        ash.state.isEruption = False
        ash.state.flightLevelFormat = 'SFC'
        ash.state.flightLevelTop = '300'

        changed = []
        ash.contentChanged.connect(lambda: changed.append(True))

        ash.populate()

        assert changed == []
        assert ash.phenomenon.currentText() == 'CLD'
        assert not ash.name.isEnabled()
        assert ash.state.isEruption is False
        assert ash.state.flightLevelTop == '300'

    def test_clear_keeps_default_combos_and_state_in_agreement(self, general):
        choose(general.description, 'SEV')
        choose(general.direction, 'STNR')

        general.clear()

        assert general.description.currentText() == 'EMBD'
        assert general.state.description == 'EMBD'
        assert general.phenomenon.currentText() == 'TS'
        assert general.state.phenomenon == 'TS'
        assert general.format.currentText() == 'TOP'
        assert general.state.flightLevelFormat == 'TOP'
        assert general.direction.currentText() == 'N'
        assert general.state.direction == 'N'
        assert general.intensityChange.currentText() == 'NC'
        assert general.state.intensityChange == 'NC'


if __name__ == '__main__':
    pytest.main([__file__])
