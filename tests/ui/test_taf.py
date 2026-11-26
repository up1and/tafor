import datetime

import pytest

from PyQt5.QtCore import QSignalBlocker

from tafor.core.config import createConfig
from tafor.core.repositories import MessageRepository, TafRepository
from tafor.core.states import createContext
from tafor.ui.dialogs import TafEditor, TafSender
from tafor.ui.forms.taf import normalizePeriod, separatePeriod
from tests.mocks import MockConfig


# Field values, not message groups: the wind box holds five digits (the unit
# comes from the settings) and the gust box holds two. '24008MPS' looks right in
# a message but is not acceptable input, and a collect() drops it from the state.
CONTENT = {
    'wind': '24008',
    'gust': '15',
    'vis': '9999',
    'weather': 'TS',
    'weatherWithIntensity': '-RA',
    'cloud1': 'SCT020',
    'cloud2': 'BKN040',
    'cb': 'BKN030',
}

EMPTY = ('', '', '', '', '', [], False, False)


def fill(segment):
    """Put a full set of valid content into every content widget."""
    segment.wind.setText(CONTENT['wind'])
    segment.gust.setText(CONTENT['gust'])
    segment.vis.setText(CONTENT['vis'])
    segment.weather.setCurrentText(CONTENT['weather'])
    segment.weatherWithIntensity.setCurrentText(CONTENT['weatherWithIntensity'])
    segment.cloud1.setText(CONTENT['cloud1'])
    segment.cloud2.setText(CONTENT['cloud2'])
    segment.cb.setText(CONTENT['cb'])
    segment.collect()


def open_header(editor):
    """Build the header the way the first show does.

    `TafPrimarySegment.showEvent` sets the date and `TafEditor.showEvent` calls
    `onOpen()`, which asks `TafPresenter` to update the header. Clicking a
    radio instead would reach the same slot through a signal the real path
    never fires.
    """
    editor.primary.setDate()
    editor.onOpen()
    return editor.primary


def fill_without_temperature(editor):
    """Everything the primary segment needs, the temperature groups left alone."""
    primary = open_header(editor)
    primary.wind.setText('24008')
    primary.gust.setText('15')
    primary.vis.setText('9999')
    primary.weather.setCurrentText('RA')
    primary.cloud1.setText('SCT020')
    primary.cloud2.setText('BKN040')
    primary.cb.setText('BKN030')
    primary.collect()
    return primary


def read_state(segment):
    """The scalar content of a segment's state, as a comparable tuple."""
    return (segment.state.wind, segment.state.gust, segment.state.visibility,
            segment.state.weather, segment.state.weatherWithIntensity,
            list(segment.state.clouds), segment.state.isCavok, segment.state.isNsc)


def read_widgets(segment):
    return (segment.wind.text(), segment.gust.text(), segment.vis.text(),
            segment.weather.currentText(), segment.weatherWithIntensity.currentText(),
            segment.cloud1.text(), segment.cloud2.text(), segment.cloud3.text(),
            segment.cb.text())


@pytest.fixture
def sender(qtbot, context, conf, database):
    sender = TafSender(None, context, conf, repository=MessageRepository(database))
    qtbot.addWidget(sender)
    return sender


@pytest.fixture
def editor(qtbot, sender, conf, context, database):
    editor = TafEditor(None, sender=sender, conf=conf, context=context, repository=TafRepository(database))
    qtbot.addWidget(editor)
    return editor


@pytest.fixture
def editor30(qtbot, database):
    """An editor on the 30 hour spec, which offers three temperature groups.

    A stack of its own: the spec is read from `General/TAFSpec`, and the shared
    `conf` fixture sits on the 24 hour default, which offers only two -- it could
    not show that a third group is built, nor that it is required.
    """
    settings = MockConfig()
    settings.setValue('General/TAFSpec', 2)
    conf = createConfig(settings=settings)
    context = createContext(conf)

    sender = TafSender(None, context, conf, repository=MessageRepository(database))
    qtbot.addWidget(sender)

    editor = TafEditor(None, sender=sender, conf=conf, context=context,
                       repository=TafRepository(database))
    qtbot.addWidget(editor)
    return editor


class TestTafEditor:

    def test_construct(self, editor, conf, context):
        assert editor.primary.state.icao == conf.airport
        assert editor.primary.state.spec == context.taf.spec
        assert len(editor.segments()) == 8
        assert editor.windowTitle()

    def test_normal_period(self, editor):
        primary = open_header(editor)

        assert primary.period.text()
        assert primary.state.durations is not None
        assert not primary.sequence.isEnabled()

    def test_amend_sequence(self, editor):
        primary = editor.primary
        primary.setDate()
        primary.amd.click()
        primary.collect()

        # Empty database: no amendment this period, so the first one is AAA
        assert primary.sequence.text() == 'AAA'
        assert primary.sequence.isEnabled()
        assert primary.state.modifier == 'AMD'
        assert primary.state.sequence == 'AAA'

    def test_the_modifier_radio_collects_on_its_own(self, editor):
        # the radios are wired through clicked, the user-intent signal, so the
        # state follows them without waiting for a hand-written collect()
        primary = editor.primary
        primary.setDate()
        primary.amd.click()

        assert primary.state.modifier == 'AMD'

    def test_a_field_that_never_collected_is_read_before_the_commit(self, editor):
        """A widget whose signal never fired (blocked here, missing wiring in
        the field) must not vanish from the message.

        The commit entry collects before it judges, so the text the report is
        built from is what is on screen. Whether the whole form is then
        acceptable is a separate question, proved by the temperature tests.
        """
        primary = fill_without_temperature(editor)

        with QSignalBlocker(primary.wind):
            primary.wind.setText('09010')

        editor.commit()

        assert primary.state.wind == '09010'
        assert '09010' in primary.message()

    def test_normal_is_the_absence_of_a_marker(self, editor):
        # NORMAL is not a fifth value next to AMD/COR/CNL: it is the lack of a
        # marker, so both the radios and the state spell it None.
        primary = open_header(editor)

        assert primary.modifier is None
        assert primary.state.modifier is None

    def test_cancel_mode(self, editor):
        primary = editor.primary
        primary.setDate()
        primary.cnl.click()
        primary.collect()

        assert editor.isCancelMode()
        assert all(not c.isEnabled() for c in primary.groupCheckboxs)

        message = primary.message()
        assert message.startswith('TAF AMD ')
        assert message.endswith(' CNL')

    def test_group_visibility(self, editor):
        primary = editor.primary
        checkbox = primary.becmg1Checkbox

        checkbox.setChecked(True)
        assert editor.becmg1.isVisibleTo(editor)
        assert editor.draft.selectedKeys() == (('BECMG', 1),)

        checkbox.setChecked(False)
        assert not editor.becmg1.isVisibleTo(editor)
        assert editor.draft.selectedKeys() == ()

    def test_the_change_group_cap_is_enforced(self, editor):
        primary = editor.primary
        for name in ('fmCheckbox', 'becmg1Checkbox', 'becmg2Checkbox', 'becmg3Checkbox', 'tempo1Checkbox'):
            getattr(primary, name).setChecked(True)
        assert len(editor.draft.selectedKeys()) == 5

        primary.tempo2Checkbox.setChecked(True)

        # the sixth is refused, and populating puts the checkbox back
        assert editor.draft.selectedKeys() == (('FM', 1), ('BECMG', 1), ('BECMG', 2), ('BECMG', 3),
                                               ('TEMPO', 1))
        assert not primary.tempo2Checkbox.isChecked()

    def test_the_ordinal_comes_from_the_position_not_the_name(self, editor):
        # three segments are all named 'BECMG'; the editor numbers them by their
        # position among their own family, and heads each box with the result
        assert editor.becmg2.indicator == 'BECMG'
        assert editor.fm.key == ('FM', 1)
        assert editor.becmg1.key == ('BECMG', 1)
        assert editor.becmg2.key == ('BECMG', 2)
        assert editor.becmg3.key == ('BECMG', 3)
        assert editor.tempo2.key == ('TEMPO', 2)
        assert editor.becmg2.name.text() == 'BECMG'

    def test_cloud_and_cb_at_the_same_height_are_accepted(self, editor):
        # a CB layer may share the height of an ordinary cloud layer, and it
        # joins `clouds` as a whole entry marked by its 'CB' suffix
        primary = editor.primary
        primary.cloud1.setText('SCT020')
        primary.cb.setText('SCT020')
        primary.collect()

        primary.validateCloud(primary.cloud1)
        primary.validateCloud(primary.cb)

        assert primary.cloud1.text() == 'SCT020'
        assert primary.cb.text() == 'SCT020'
        assert primary.state.clouds == ['SCT020', 'SCT020CB']

    def test_a_user_edit_runs_its_cross_field_derivation_before_committing(self, editor):
        # textEdited fires before textChanged. A zero wind clears the gust
        # through textChanged, so the commit must run that derivation first.
        primary = open_header(editor)
        primary.gust.setText('15')
        primary.collect()

        with QSignalBlocker(primary.wind):
            primary.wind.setText('00000')
        primary.wind.textEdited.emit('00000')

        assert primary.gust.text() == ''
        assert primary.state.gust == ''


class TestTafGroupOverlap:
    """The overlap checks take their siblings from the draft's selection, not
    from `isVisible()` (design 5.4).

    Visibility belongs to populate(), and it is false for every group while
    the editor is off screen — which is every run of this file. Reading it there
    made both checks unreachable rather than merely untested.
    """

    def messages(self, editor):
        """The editor addresses its notifications via showNotification();
        groups emit periodFinished and the presenter reports overlap there."""
        seen = []
        editor.showNotification = lambda message: seen.append(message)
        return seen

    def openPeriod(self, editor):
        """A primary with a real period, so the groups have something to sit in."""
        primary = open_header(editor)
        assert primary.state.durations is not None
        return primary

    def test_overlapping_siblings_are_rejected_off_screen(self, editor, context):
        primary = self.openPeriod(editor)
        editor.primary.becmg1Checkbox.setChecked(True)
        editor.primary.becmg2Checkbox.setChecked(True)

        # Nothing is visible: the old isVisible() filter saw no siblings at all
        assert not editor.isVisible()
        assert not editor.becmg1.isVisible()

        start = primary.state.durations[0]
        editor.becmg1.state.durations = (start + datetime.timedelta(hours=2),
                                         start + datetime.timedelta(hours=5))
        editor.becmg2.state.durations = (start + datetime.timedelta(hours=3),
                                         start + datetime.timedelta(hours=6))

        seen = self.messages(editor)
        editor.becmg2.periodFinished.emit()

        assert seen == ['Change group time is overlap']

    def test_touching_siblings_pass(self, editor, context):
        primary = self.openPeriod(editor)
        editor.primary.becmg1Checkbox.setChecked(True)
        editor.primary.becmg2Checkbox.setChecked(True)

        start = primary.state.durations[0]
        editor.becmg1.state.durations = (start + datetime.timedelta(hours=2),
                                         start + datetime.timedelta(hours=5))
        editor.becmg2.state.durations = (start + datetime.timedelta(hours=5),
                                         start + datetime.timedelta(hours=8))

        seen = self.messages(editor)
        editor.becmg2.periodFinished.emit()

        assert seen == []

    def test_unselected_groups_are_not_siblings(self, editor, context):
        primary = self.openPeriod(editor)
        editor.primary.becmg1Checkbox.setChecked(True)

        start = primary.state.durations[0]
        editor.becmg1.state.durations = (start + datetime.timedelta(hours=2),
                                         start + datetime.timedelta(hours=5))
        # becmg2 overlaps, but the draft does not have it selected
        editor.becmg2.state.durations = (start + datetime.timedelta(hours=3),
                                         start + datetime.timedelta(hours=6))

        seen = self.messages(editor)
        editor.becmg1.periodFinished.emit()

        assert seen == []

    def test_another_family_is_not_a_sibling(self, editor, context):
        primary = self.openPeriod(editor)
        editor.primary.becmg1Checkbox.setChecked(True)
        editor.primary.tempo1Checkbox.setChecked(True)

        start = primary.state.durations[0]
        editor.becmg1.state.durations = (start + datetime.timedelta(hours=2),
                                         start + datetime.timedelta(hours=5))
        editor.tempo1.state.durations = (start + datetime.timedelta(hours=3),
                                         start + datetime.timedelta(hours=6))

        seen = self.messages(editor)
        editor.becmg1.periodFinished.emit()

        assert seen == []

    def test_fm_compares_against_the_selected_becmg_groups(self, editor, context):
        primary = self.openPeriod(editor)
        editor.primary.fmCheckbox.setChecked(True)
        editor.primary.becmg1Checkbox.setChecked(True)

        start = primary.state.durations[0]
        inside = start + datetime.timedelta(hours=3)
        editor.fm.state.durations = (inside, inside)
        editor.becmg1.state.durations = (start + datetime.timedelta(hours=2),
                                         start + datetime.timedelta(hours=5))

        seen = self.messages(editor)
        editor.fm.periodFinished.emit()

        assert seen == ['Change group time is overlap']


class TestTafTemperatureIsRequired:
    """A TAF needs its temperature groups: Next stays off until every one of them
    is filled.

    The rule was in the widget before the extraction and required all of them.
    The extracted version filtered to the groups that had been started, which is
    vacuously true when none has — so the form could be sent with no temperature
    at all. Restored 2026-09-18; the sweep is in `.workbuddy/probe-6/`.
    """

    def test_the_next_button_stays_off_without_a_temperature(self, editor):
        primary = fill_without_temperature(editor)
        assert [t.state.isAcceptable() for t in primary.temperatures] == [False, False]

        assert editor.presenter.hasAcceptableInput() is False
        assert not editor.nextButton.isEnabled()

    def test_one_temperature_group_is_not_enough(self, editor):
        primary = fill_without_temperature(editor)
        primary.temperatures[0].temp.setText('12')
        primary.temperatures[0].tempTime.setText('1012')

        assert editor.presenter.hasAcceptableInput() is False

    def test_a_half_filled_group_is_not_enough(self, editor):
        primary = fill_without_temperature(editor)
        primary.temperatures[0].temp.setText('12')

        assert editor.presenter.hasAcceptableInput() is False

    def test_filling_every_group_enables_the_next_button(self, editor):
        primary = fill_without_temperature(editor)
        for temperature, value, time in zip(primary.temperatures, ('12', 'M03'), ('1012', '1015')):
            temperature.temp.setText(value)
            temperature.tempTime.setText(time)
            temperature.onUserEdited()

        assert editor.presenter.hasAcceptableInput() is True
        assert editor.nextButton.isEnabled()


class TestTafTemperatureGroupsPerSpec:
    """The spec decides how many temperature groups the form offers, and every
    one of them is required.

    `TestPrimaryStateIsAcceptable` proves the rule over a list handed to it; this
    proves the editor *builds* that list from the spec. The 30 hour form's third
    group exists only because `__init__` appended it, which a hand-built state
    cannot show.
    """

    def test_the_24_hour_form_offers_two_groups(self, editor):
        primary = editor.primary
        assert [t.state.mode for t in primary.temperatures] == ['max', 'min']
        assert len(primary.state.temperatures) == 2
        assert all(s is t.state for s, t in zip(primary.state.temperatures, primary.temperatures))

    def test_the_30_hour_form_offers_three_groups(self, editor30):
        primary = editor30.primary
        assert [t.state.mode for t in primary.temperatures] == ['max', 'min', 'max']
        assert len(primary.state.temperatures) == 3
        assert all(s is t.state for s, t in zip(primary.state.temperatures, primary.temperatures))

    def test_the_third_group_is_the_switchable_one(self, editor30):
        third = editor30.primary.temperatures[2]
        assert third.canSwitch is True
        assert [t.canSwitch for t in editor30.primary.temperatures] == [False, False, True]

        third.switchMode()
        assert third.state.mode == 'min'

    def test_two_groups_are_not_enough_on_the_30_hour_form(self, editor30):
        primary = fill_without_temperature(editor30)
        for temperature, value, time in zip(primary.temperatures, ('12', 'M03'), ('1012', '1015')):
            temperature.temp.setText(value)
            temperature.tempTime.setText(time)
            temperature.onUserEdited()

        assert [t.state.isAcceptable() for t in primary.temperatures] == [True, True, False]
        assert editor30.presenter.hasAcceptableInput() is False
        assert not editor30.nextButton.isEnabled()

    def test_all_three_groups_enable_the_next_button(self, editor30):
        primary = fill_without_temperature(editor30)
        for temperature, value, time in zip(primary.temperatures,
                                            ('12', 'M03', 'M01'),
                                            ('1012', '1015', '1018')):
            temperature.temp.setText(value)
            temperature.tempTime.setText(time)
            temperature.onUserEdited()

        assert [t.state.isAcceptable() for t in primary.temperatures] == [True, True, True]
        assert editor30.presenter.hasAcceptableInput() is True
        assert editor30.nextButton.isEnabled()


class TestTafPeriodReanchor:
    """Moving the primary's window clears the form, and that is what keeps a
    group's derived window from outliving the period it was computed against.

    `PrimaryState.period` is written by `TafDraft.begin()`,
    reached only from `updateModifier()`, which clears everything when the
    window moves. No event carries the news to the groups; the clear is the
    news. This pins the whole chain -- the reset of `GroupState.durations`
    itself is pinned in `tests/core/test_taf_states.py::TestStateClear`,
    because populating would cover for it here.
    """

    def test_moving_the_period_drops_the_group_windows(self, editor):
        primary = open_header(editor)
        editor.primary.becmg1Checkbox.setChecked(True)
        group = editor.becmg1

        start, end = primary.state.durations
        period = '{:02d}{:02d}/{:02d}{:02d}'.format(start.day, start.hour, end.day, end.hour)
        group.period.setText(period)
        group.collect()          # a programmatic fill is read by collect()
        assert group.state.durations is not None

        # The slot asks the operator first, then steps the draft and refills the
        # header; this is everything after the confirmation.
        editor.presenter.shiftPeriod('prev')

        assert editor.selectedGroups() == []
        assert group.state.period == ''
        assert group.state.durations is None


class TestTafGroupPeriodCommit:
    """One keystroke in a group period commits once, after the completion.

    The period used to be wired twice: the generic textEdited -> onUserEdited
    read the half-typed text, then the completion wrote the full period and
    read again. Both fired, so the state was briefly the thing the operator
    had not finished typing.
    """

    @pytest.fixture
    def editorNoCompletion(self, qtbot, database):
        """An editor that only separates the period, never completes it.

        A stack of its own: `conf` is session-scoped, and this test needs the
        other branch of normalizePeriod().
        """
        settings = MockConfig()
        settings.setValue('General/AutoCompletionGroupTime', 'false')
        conf = createConfig(settings=settings)
        context = createContext(conf)

        sender = TafSender(None, context, conf, repository=MessageRepository(database))
        qtbot.addWidget(sender)

        editor = TafEditor(None, sender=sender, conf=conf, context=context,
                           repository=TafRepository(database))
        qtbot.addWidget(editor)
        return editor

    def test_typing_in_the_period_announces_once(self, editor):
        primary = open_header(editor)
        primary.becmg1Checkbox.setChecked(True)
        group = editor.becmg1

        changed = []
        group.contentChanged.connect(lambda: changed.append(group.state.period))

        group.period.setText('1009/10')
        group.period.textEdited.emit('1009/10')

        assert len(changed) == 1
        assert changed[0] == group.period.text()
        assert group.state.period == group.period.text()

    def test_the_separator_is_written_before_the_read(self, editorNoCompletion):
        editor = editorNoCompletion
        primary = open_header(editor)
        primary.becmg1Checkbox.setChecked(True)
        group = editor.becmg1

        group.period.setText('1012')
        group.period.textEdited.emit('1012')

        assert group.period.text() == '1012/'
        assert group.state.period == '1012/'

    def test_a_refused_start_does_not_stop_the_next_attempt(self, editor):
        primary = open_header(editor)
        primary.becmg1Checkbox.setChecked(True)
        group = editor.becmg1

        group.period.setText('9999')
        group.period.textEdited.emit('9999')
        assert group.period.text() == '9999'

        # Replacing a digit is not growth, so completion only retries if the
        # refused start left the bookkeeping it compares against alone.
        start = primary.state.durations[0]
        group.period.setText('{:02d}{:02d}'.format(start.day, start.hour))
        group.period.textEdited.emit(group.period.text())

        assert group.period.text().startswith('{:02d}{:02d}/'.format(start.day, start.hour))


class TestPeriodSpelling:
    """The rules that turn typed text into the accepted spelling.

    Pure text in, text out, so they are pinned without a widget: the group
    and the trend both build on them.
    """

    def test_the_day_gets_its_separator_while_typing(self):
        assert separatePeriod('1012', '101') == '1012/'

    def test_a_deleted_character_does_not_add_the_separator(self):
        assert separatePeriod('1012', '1012/') == '1012'

    def test_a_midnight_end_is_spelled_as_24_of_the_day_before(self):
        window = (datetime.datetime(2026, 8, 10, 12), datetime.datetime(2026, 8, 12, 0))
        assert normalizePeriod('1012/1200', '1012/120', window) == '1012/1124'

    def test_a_period_already_spelled_as_24_is_left_alone(self):
        window = (datetime.datetime(2026, 8, 10, 12), datetime.datetime(2026, 8, 12, 0))
        assert normalizePeriod('1012/1124', '1012/112', window) == '1012/1124'

    def test_a_window_the_field_cannot_read_leaves_the_text_alone(self):
        assert normalizePeriod('1012/1200', '1012/120', None) == '1012/1200'


class TestTafTemperatureNotifications:
    """A rejected temperature still reaches the operator.

    The groups used to climb two hops -- `primary.editor.showNotification` --
    to report it. They now emit `notified`, which propagates through the
    primary segment to the editor.
    """

    def test_a_rejected_temperature_time_still_reaches_the_editor(self, editor):
        seen = []
        editor.showNotification = lambda message: seen.append(message)

        primary = open_header(editor)
        start, _ = primary.state.durations
        instant = (start + datetime.timedelta(hours=1)).strftime('%d%H')

        first, second = primary.temperatures[:2]
        first.tempTime.setText(instant)
        first.collect()
        first.validateTemperatureTime()
        assert seen == []

        # The same instant as the first group: a TX and a TN never coincide.
        second.tempTime.setText(instant)
        second.collect()
        second.validateTemperatureTime()

        assert seen == ['The time of temperature is not correct']
        assert second.state.time == ''
        assert second.tempTime.text() == ''


class TestTafApplyState:
    """collect() is widget -> state and populate() is state -> widget; they
    are one contract. `collect(); populate(); collect()` must leave the state
    alone, and `editor.clear()` is `draft.clear()` -- empty the data -- followed
    by `populate()`, which draws it."""

    def test_a_render_draws_the_header_from_the_state(self, editor):
        """The header is part of the document: populating writes it like any other
        field, instead of leaving it to whoever called clear()."""
        primary = fill_without_temperature(editor)

        primary.state.period = '0918'
        primary.state.sequence = 'AAB'
        primary.state.modifier = 'AMD'

        primary.populate()

        assert primary.period.text() == '0918'
        assert primary.sequence.text() == 'AAB'
        assert primary.amd.isChecked()

    def test_a_render_of_a_changed_state_converges(self, editor):
        """The D invariant: every field populate() writes ends up in both places.

        Several fields are changed behind the widgets at once, so the writes
        interleave with the collects they trigger; populating is finished only
        when the last write leaves the state agreeing with the screen.
        """
        primary = fill_without_temperature(editor)

        primary.state.wind = '09010'
        primary.state.visibility = '4000'
        primary.state.clouds = ['FEW010']

        primary.populate()

        assert (primary.wind.text(), primary.vis.text(), primary.cloud1.text()) == ('09010', '4000', 'FEW010')
        assert primary.state.wind == '09010'
        assert primary.state.visibility == '4000'
        assert primary.state.clouds == ['FEW010']

    def test_apply_state_is_the_inverse_of_collect(self, editor):
        for segment in editor.segments():
            fill(segment)
            segment.collect()
            before = read_state(segment)

            segment.populate()
            segment.collect()

            assert read_state(segment) == before

    def test_clear_empties_every_content_widget_and_the_state(self, editor):
        for segment in editor.segments():
            fill(segment)

        editor.clear()

        for segment in editor.segments():
            assert read_widgets(segment) == ('',) * 9
            assert not segment.cavok.isChecked()
            assert not segment.nsc.isChecked()

            segment.collect()
            assert read_state(segment) == EMPTY

    def test_clear_twice_changes_nothing(self, editor):
        # populate() writes widgets without collecting them back; a second
        # clear must not find anything to resurrect
        for segment in editor.segments():
            fill(segment)

        editor.clear()
        editor.clear()

        for segment in editor.segments():
            assert read_widgets(segment) == ('',) * 9

    def test_clear_empties_the_header_and_the_next_begin_fills_it(self, editor, frozen_time):
        primary = editor.primary
        primary.date.setText('101200')
        editor.onOpen()
        period = primary.period.text()
        assert period and primary.state.durations is not None

        editor.clear()

        # The header is part of the document now: clear() empties it like any
        # other field, and updateHeader() re-derives it on the next show.
        assert primary.period.text() == ''
        assert primary.state.period == ''
        assert primary.date.text() == '101200'   # the clock owns the date

        editor.presenter.updateHeader()

        assert primary.period.text() == period
        assert primary.state.durations is not None

    def test_clear_returns_the_radios_to_normal(self, editor):
        primary = editor.primary
        primary.date.setText('101200')
        primary.amd.click()
        assert primary.amd.isChecked()

        editor.clear()

        # The radios are part of the rendered header: clearing it draws NORMAL.
        assert primary.normal.isChecked()
        assert primary.state.modifier is None

    def test_clear_leaves_vertical_visibility_mode(self, editor):
        # setVv used to hang off cloud1.textEdited, which a programmatic write
        # never fires, so clear() left the label on "Vertical Visibility" and
        # cloud2/3/cb disabled — with no way back except typing in cloud1.
        primary = editor.primary
        primary.cloud1.setText('VV005')
        assert not primary.cloud2.isEnabled()

        editor.clear()

        assert primary.cloud1Label.text() == 'Cloud'
        assert primary.cloud2.isEnabled()
        assert primary.cloud3.isEnabled()
        assert primary.cb.isEnabled()

    def test_apply_state_enters_vertical_visibility_mode(self, editor):
        # the write direction must re-derive the enablement too, or a state
        # loaded from elsewhere would not be able to show a VV at all
        primary = editor.primary
        primary.state.clouds = ['VV005']

        primary.populate()

        assert primary.cloud1.text() == 'VV005'
        assert not primary.cloud2.isEnabled()
        assert not primary.cb.isEnabled()


class TestTafPeriodClearsTheForm:
    """Changing the period empties the form; changing the modifier does not.

    The period owns the validity window: when it moves, the change-group times
    typed against the old window go stale, so everything is emptied. A modifier
    does not move the window, so switching the marker keeps what has been typed
    and only rebuilds the header -- the sequence included. Within either half the
    trigger is "the value really changed", not "the handler ran": a click on the
    radio that is already on must keep what has been typed. Emptying the form is
    updateModifier()'s own explicit decision — it used to be a side effect of the
    period line's textChanged signal, which made every write to the period clear
    the form, and the modifier used to empty the form too.
    """

    def start_filled(self, editor):
        """A period on screen and every content widget filled."""
        primary = open_header(editor)
        fill(primary)
        primary.collect()
        return primary

    def test_a_click_on_the_radio_already_on_keeps_the_form(self, editor):
        primary = self.start_filled(editor)
        widgets = read_widgets(primary)
        state = read_state(primary)

        primary.normal.click()

        assert read_widgets(primary) == widgets
        assert read_state(primary) == state

    def test_changing_the_modifier_keeps_the_form(self, editor):
        primary = self.start_filled(editor)
        widgets = read_widgets(primary)
        state = read_state(primary)

        primary.amd.click()

        assert read_widgets(primary) == widgets
        assert read_state(primary) == state
        assert primary.state.modifier == 'AMD'
        assert primary.sequence.text() == 'AAA'

    def test_changing_the_modifier_refills_the_header(self, editor, frozen_time):
        # frozen_time: the period is read off the clock, and this test compares it
        # before and after the switch
        primary = self.start_filled(editor)
        period = primary.period.text()

        primary.amd.click()

        assert primary.period.text() == period
        assert primary.state.period == period
        assert primary.state.durations is not None
        assert primary.sequence.text() == 'AAA'
        assert primary.state.sequence == 'AAA'
        assert primary.state.modifier == 'AMD'

    def test_changing_the_modifier_keeps_the_change_groups(self, editor):
        primary = self.start_filled(editor)
        primary.becmg1Checkbox.setChecked(True)
        fill(editor.becmg1)
        widgets = read_widgets(editor.becmg1)
        assert editor.draft.selectedKeys() == (('BECMG', 1),)

        primary.amd.click()

        assert editor.draft.selectedKeys() == (('BECMG', 1),)
        assert read_widgets(editor.becmg1) == widgets

    def test_the_cancel_modifier_keeps_the_form_and_still_composes_cnl(self, editor):
        primary = self.start_filled(editor)
        widgets = read_widgets(primary)

        primary.cnl.click()

        assert read_widgets(primary) == widgets
        assert primary.state.modifier == 'CNL'
        assert all(not c.isEnabled() for c in primary.groupCheckboxs)
        assert primary.message().endswith(' CNL')

    def test_a_second_click_on_the_new_radio_keeps_the_form(self, editor):
        primary = self.start_filled(editor)
        primary.amd.click()
        fill(primary)
        primary.collect()
        widgets = read_widgets(primary)

        primary.amd.click()

        assert read_widgets(primary) == widgets

    def test_a_programmatic_period_write_does_not_clear_the_form(self, editor):
        primary = self.start_filled(editor)
        widgets = read_widgets(primary)

        primary.period.setText('1012/1024')

        assert read_widgets(primary) == widgets

    def test_stepping_to_another_period_empties_the_form(self, editor):
        primary = self.start_filled(editor)
        period = primary.period.text()

        editor.presenter.shiftPeriod('prev')

        assert read_widgets(primary) == ('',) * 9
        assert primary.period.text() and primary.period.text() != period

    def test_stepping_to_another_period_keeps_the_modifier_in_the_state(self, editor):
        # draft.begin() clears the body while keeping the modifier from the
        # radios; populate() draws that back to screen.
        primary = open_header(editor)
        primary.amd.click()
        assert primary.state.modifier == 'AMD'

        editor.presenter.shiftPeriod('prev')

        assert primary.state.modifier == 'AMD'
        assert primary.state.sequence == 'AAA'

    def test_beginning_a_report_keeps_the_window_the_draft_is_on(self, editor, frozen_time):
        """begin() must not step the window back to the current one.

        The prev button exists to write about another window; a begin() that
        also reset the offset would silently turn the backdated report into
        today's.
        """
        editor.draft.prev()
        primary = editor.primary

        editor.presenter.updateHeader()

        assert editor.draft.isBackdated()
        assert primary.period.text()
        assert primary.state.period == primary.period.text()

    def test_switching_between_two_amend_modifiers_keeps_the_form(self, editor):
        """AMD -> COR implies the same period, so nothing is cleared.

        The period COR implies is the one already on screen, so the period half
        of the trigger is false and the typed content stays; what flips is the
        header the marker owns -- the sequence is rebuilt for the COR notation.
        """
        primary = self.start_filled(editor)
        primary.amd.click()
        fill(primary)
        primary.collect()
        period = primary.period.text()
        widgets = read_widgets(primary)
        assert primary.sequence.text() == 'AAA'

        primary.cor.click()

        assert primary.period.text() == period  # the period did not move
        assert read_widgets(primary) == widgets
        assert primary.state.modifier == 'COR'
        assert primary.sequence.text() == 'CCA'

    def test_clear_forgets_the_applied_modifier(self, editor):
        """A fresh message leaves nothing pending in the state.

        The header is drawn from the draft now, so clearing it is what puts the
        radios back to NORMAL -- there is no separate clearType() step.
        """
        primary = self.start_filled(editor)

        primary.amd.click()
        assert primary.state.modifier == 'AMD'

        editor.clear()

        assert primary.state.modifier is None
        assert primary.normal.isChecked()


class TestTafFormDecoupling:

    def test_segments_do_not_hold_editor_repository_or_draft(self, editor):
        primary = editor.primary
        assert not hasattr(primary, 'repository')
        assert not hasattr(primary, 'draft')
        assert not hasattr(primary, 'editor')
        assert not hasattr(primary, 'notify')

        for group in editor.groups:
            assert not hasattr(group, 'draft')
            assert not hasattr(group, 'editor')
            assert not hasattr(group, 'notify')

    def test_primary_timer_starts_when_shown_and_stops_when_hidden_or_closed(self, editor):
        assert not editor.primary.timer.isActive()

        editor.show()
        assert editor.primary.timer.isActive()

        editor.hide()
        assert not editor.primary.timer.isActive()

        editor.show()
        assert editor.primary.timer.isActive()

        editor.close()
        assert not editor.primary.timer.isActive()

    def test_notifications_flow_through_notified_signal_to_editor_area(self, editor, frozen_time):
        primary = open_header(editor)
        primary.wind.setText('24008')
        primary.gust.setText('10')
        primary.collect()
        primary.validateGust()
        assert editor.notificationArea.text() == 'Gust speed must be greater than wind speed by at least 5'

        primary.becmg1Checkbox.setChecked(True)
        editor.becmg1.wind.setText('24008')
        editor.becmg1.gust.setText('10')
        editor.becmg1.collect()
        editor.becmg1.validateGust()
        assert editor.notificationArea.text() == 'Gust speed must be greater than wind speed by at least 5'

        end = primary.state.durations[1]
        start = end - datetime.timedelta(hours=2)
        editor.becmg1.period.setText('{:02d}{:02d}/{:02d}{:02d}'.format(
            start.day, start.hour, end.day, end.hour))
        editor.becmg1.collect()
        editor.becmg1.period.editingFinished.emit()
        assert editor.becmg1.period.text() == ''
        assert editor.notificationArea.text() == 'End time of change group is not correct'

    def test_toggle_group_by_semantic_key_updates_selection(self, editor):
        editor.presenter.toggleGroup('BECMG', 1)

        assert editor.presenter.draft.selectedKeys() == (('BECMG', 1),)
        assert editor.primary.becmg1Checkbox.isChecked()
        assert editor.becmg1.isVisibleTo(editor)

        editor.presenter.toggleGroup('BECMG', 1)

        assert editor.presenter.draft.selectedKeys() == ()
        assert not editor.primary.becmg1Checkbox.isChecked()
        assert not editor.becmg1.isVisibleTo(editor)

    def test_shift_period_toggles_buttons_and_updates_period(self, editor):
        primary = open_header(editor)
        initial_period = primary.period.text()
        assert primary.prevButton.isEnabled()
        assert not primary.resetButton.isEnabled()

        editor.presenter.shiftPeriod('prev')
        assert primary.period.text() != initial_period
        assert primary.resetButton.isEnabled()

        editor.presenter.shiftPeriod('current')
        assert primary.period.text() == initial_period
        assert not primary.resetButton.isEnabled()

    def test_commit_catches_overlapping_groups(self, editor, frozen_time):
        primary = fill_without_temperature(editor)
        for temperature, value, time in zip(primary.temperatures, ('12', 'M03'), ('1012', '1015')):
            temperature.temp.setText(value)
            temperature.tempTime.setText(time)
            temperature.onUserEdited()

        primary.becmg1Checkbox.setChecked(True)
        primary.becmg2Checkbox.setChecked(True)
        fill(editor.becmg1)
        fill(editor.becmg2)

        start = primary.state.durations[0]
        p1_start = start + datetime.timedelta(hours=1)
        p1_end = start + datetime.timedelta(hours=3)
        editor.becmg1.period.setText('{:02d}{:02d}/{:02d}{:02d}'.format(
            p1_start.day, p1_start.hour, p1_end.day, p1_end.hour))

        p2_start = start + datetime.timedelta(hours=2)
        p2_end = start + datetime.timedelta(hours=4)
        editor.becmg2.period.setText('{:02d}{:02d}/{:02d}{:02d}'.format(
            p2_start.day, p2_start.hour, p2_end.day, p2_end.hour))

        editor.commit()
        assert editor.notificationArea.text() == 'Change group time is overlap'


if __name__ == '__main__':
    pytest.main()
