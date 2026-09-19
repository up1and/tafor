import datetime

import pytest

from tafor.core.config import createConfig
from tafor.core.repositories import MessageRepository, TafRepository
from tafor.core.states import createContext
from tafor.ui.components.send import TafSender
from tafor.ui.components.taf import TafEditor
from tests.mocks import MockConfig


CONTENT = {
    'wind': '24008MPS',
    'gust': '24015MPS',
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


def open_header(editor):
    """Build the header the way the first show does.

    `TafPrimarySegment.showEvent` sets the date and `TafEditor.showEvent` calls
    `onFirstShow()`, which runs `updateModifier()`. Clicking a radio instead would
    reach the same slot through a signal the real path never fires.
    """
    editor.primary.setDate()
    editor.onFirstShow()
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
        # the radios emit toggled before clicked, and toggles() is wired to
        # onContentChanged, so the state follows them without waiting for a
        # hand-written collect()
        primary = editor.primary
        primary.setDate()
        primary.amd.click()

        assert primary.state.modifier == 'AMD'

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
        assert editor.draft.activeGroups() == (('BECMG', 1),)

        checkbox.setChecked(False)
        assert not editor.becmg1.isVisibleTo(editor)
        assert editor.draft.activeGroups() == ()

    def test_the_change_group_cap_is_enforced(self, editor):
        primary = editor.primary
        for name in ('fmCheckbox', 'becmg1Checkbox', 'becmg2Checkbox', 'becmg3Checkbox', 'tempo1Checkbox'):
            getattr(primary, name).setChecked(True)
        assert len(editor.draft.activeGroups()) == 5

        primary.tempo2Checkbox.setChecked(True)

        # the sixth is refused, and the render puts the checkbox back
        assert editor.draft.activeGroups() == (('FM', 1), ('BECMG', 1), ('BECMG', 2), ('BECMG', 3),
                                               ('TEMPO', 1))
        assert not primary.tempo2Checkbox.isChecked()

    def test_the_ordinal_comes_from_the_position_not_the_name(self, editor):
        # three segments are all named 'BECMG'; the editor numbers them by their
        # position among their own family, and heads each box with the result
        assert editor.becmg2.indicator == 'BECMG'
        assert editor.groupKey(editor.fm) == ('FM', 1)
        assert editor.groupKey(editor.becmg1) == ('BECMG', 1)
        assert editor.groupKey(editor.becmg2) == ('BECMG', 2)
        assert editor.groupKey(editor.becmg3) == ('BECMG', 3)
        assert editor.groupKey(editor.tempo2) == ('TEMPO', 2)
        assert editor.becmg2.name.text() == 'BECMG'

    def test_cloud_and_cb_at_the_same_height_are_accepted(self, editor):
        # a CB layer may share the height of an ordinary cloud layer, and it
        # joins `clouds` as a whole entry marked by its 'CB' suffix
        primary = editor.primary
        primary.cloud1.setText('SCT020')
        primary.cb.setText('SCT020')

        primary.validateCloud(primary.cloud1)
        primary.validateCloud(primary.cb)

        assert primary.cloud1.text() == 'SCT020'
        assert primary.cb.text() == 'SCT020'
        assert primary.state.clouds == ['SCT020', 'SCT020CB']


class TestTafGroupOverlap:
    """The overlap checks take their siblings from the draft's selection, not
    from `isVisible()` (design 5.4).

    Visibility is the render's business, and it is false for every group while
    the editor is off screen — which is every run of this file. Reading it there
    made both checks unreachable rather than merely untested.
    """

    def messages(self, context):
        seen = []
        context.event.editorMessage.connect(lambda title, text: seen.append((title, text)))
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

        seen = self.messages(context)
        editor.becmg2.validateGroupsPeriod()

        assert seen == [('taf', 'Change group time is overlap')]

    def test_touching_siblings_pass(self, editor, context):
        primary = self.openPeriod(editor)
        editor.primary.becmg1Checkbox.setChecked(True)
        editor.primary.becmg2Checkbox.setChecked(True)

        start = primary.state.durations[0]
        editor.becmg1.state.durations = (start + datetime.timedelta(hours=2),
                                         start + datetime.timedelta(hours=5))
        editor.becmg2.state.durations = (start + datetime.timedelta(hours=5),
                                         start + datetime.timedelta(hours=8))

        seen = self.messages(context)
        editor.becmg2.validateGroupsPeriod()

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

        seen = self.messages(context)
        editor.becmg1.validateGroupsPeriod()

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

        seen = self.messages(context)
        editor.becmg1.validateGroupsPeriod()

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

        seen = self.messages(context)
        editor.fm.validateGroupsPeriod()

        assert seen == [('taf', 'Change group time is overlap')]


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

        assert [t.state.isAcceptable() for t in primary.temperatures] == [True, True, True]
        assert editor30.presenter.hasAcceptableInput() is True
        assert editor30.nextButton.isEnabled()


class TestTafApplyState:
    """collect() is widget -> state and applyState() is state -> widget; they
    are one contract. `collect(); applyState(); collect()` must leave the state
    alone, and clear() is nothing more than `state.clear(); applyState()`."""

    def test_apply_state_is_the_inverse_of_collect(self, editor):
        for segment in editor.segments():
            fill(segment)
            segment.collect()
            before = read_state(segment)

            segment.applyState()
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
        # applyState() writes widgets, and those writes re-enter collect();
        # a second clear must not find anything to resurrect
        for segment in editor.segments():
            fill(segment)

        editor.clear()
        editor.clear()

        for segment in editor.segments():
            assert read_widgets(segment) == ('',) * 9

    def test_clear_keeps_the_primary_header(self, editor):
        primary = editor.primary
        primary.date.setText('101200')
        editor.onFirstShow()
        period = primary.period.text()
        assert period and primary.state.durations is not None

        editor.clear()

        # The date belongs to the clock and the period to updateModifier();
        # clear() must not put a period on screen that updateModifier() did not
        # choose, and it is updateModifier() that decides to clear the form.
        assert primary.date.text() == '101200'
        assert primary.period.text() == period

    def test_clear_leaves_the_message_type_radio_alone(self, editor):
        primary = editor.primary
        primary.date.setText('101200')
        primary.amd.click()

        editor.clear()

        # PrimaryState.clear() drops the modifier back to None, but rendering that
        # would reset the radios in the middle of updateModifier()'s own
        # re-derivation of the period.
        assert primary.amd.isChecked()

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
        # the render direction must re-derive the enablement too, or a state
        # loaded from elsewhere would not be able to show a VV at all
        primary = editor.primary
        primary.state.clouds = ['VV005']

        primary.applyState()

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
        assert editor.draft.activeGroups() == (('BECMG', 1),)

        primary.amd.click()

        assert editor.draft.activeGroups() == (('BECMG', 1),)
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

        editor.draft.prev()
        primary.updateModifier()

        assert read_widgets(primary) == ('',) * 9
        assert primary.period.text() and primary.period.text() != period

    def test_stepping_to_another_period_keeps_the_modifier_in_the_state(self, editor):
        # the clear() inside updateModifier() wipes the state, and no collect
        # runs after it on this path -- the re-assertion in updateModifier() is
        # what keeps `state.modifier` on the radios' value
        primary = open_header(editor)
        primary.amd.click()
        assert primary.state.modifier == 'AMD'

        editor.draft.prev()
        primary.updateModifier()

        assert primary.state.modifier == 'AMD'
        assert primary.state.sequence == 'AAA'

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

    def test_clear_type_forgets_the_applied_modifier(self, editor):
        """A fresh message leaves nothing pending in the state.

        clearType() puts the radios back to NORMAL; the toggles() wiring collects
        them into the state on the way, so `state.modifier` follows without a
        hand-written reset.
        """
        primary = self.start_filled(editor)

        primary.amd.click()
        assert primary.state.modifier == 'AMD'

        primary.clearType()

        assert primary.state.modifier is None


if __name__ == '__main__':
    pytest.main()
