import datetime

from tafor.core.taf import TafDraft
from tafor.core.taf.spec import SpecFC, SpecFT24
from tafor.core.taf.states import GroupState, PrimaryState


FROZEN = datetime.datetime(2026, 6, 10, 8, 0)


def draft(spec=SpecFC):
    return TafDraft(spec, now=lambda: FROZEN)


def ready(spec=SpecFC):
    """A draft with a primary report and one registered group: the shape the
    editor builds, without the editor."""
    d = draft(spec)
    d.attach(PrimaryState(unit='KT', icao='ZUUU'))
    d.register(('BECMG', 1), GroupState('KT', indicator='BECMG'))
    return d


class TestPeriodNavigation:

    def test_taf_is_the_report_at_the_current_offset(self):
        assert draft().taf().period() == '1009/1018'

    def test_prev_steps_one_report_back(self):
        d = draft()
        d.prev()

        assert d.offset == -1
        assert d.taf().period() == '1006/1015'

    def test_prev_stops_at_minus_two(self):
        d = draft()
        for _ in range(5):
            d.prev()

        assert d.offset == -2
        assert d.taf().period() == '1003/1012'

    def test_can_prev_until_minus_two(self):
        d = draft()
        assert d.hasPrevious()

        d.prev()
        assert d.hasPrevious()

        d.prev()
        assert not d.hasPrevious()

    def test_reset_goes_back_to_the_current_report(self):
        d = draft()
        d.prev()
        assert d.isBackdated()

        d.toCurrent()

        assert d.offset == 0
        assert not d.isBackdated()
        assert d.taf().period() == '1009/1018'

    def test_the_spec_decides_the_step(self):
        d = draft(SpecFT24)
        assert d.taf().period() == '1006/1106'

        d.prev()
        assert d.taf().period() == '1000/1024'


class TestGroupSelection:

    def test_toggle_selects_and_deselects(self):
        d = draft()

        assert d.toggle('BECMG', 1) is None
        assert d.selectedKeys() == (('BECMG', 1),)

        assert d.toggle('BECMG', 1) is None
        assert d.selectedKeys() == ()

    def test_active_groups_are_ordered_by_family(self):
        d = draft()
        for group in (('TEMPO', 1), ('BECMG', 1), ('FM', 1)):
            assert d.toggle(*group) is None

        assert d.selectedKeys() == (('FM', 1), ('BECMG', 1), ('TEMPO', 1))

    def test_a_family_must_be_contiguous_from_the_front(self):
        d = draft()

        assert d.toggle('BECMG', 2) == 'group_not_contiguous'
        assert d.selectedKeys() == ()

        assert d.toggle('BECMG', 1) is None
        assert d.toggle('BECMG', 2) is None
        assert d.selectedKeys() == (('BECMG', 1), ('BECMG', 2))

    def test_at_most_five_groups(self):
        d = draft()
        for group in (('FM', 1), ('BECMG', 1), ('BECMG', 2), ('BECMG', 3), ('TEMPO', 1)):
            assert d.toggle(*group) is None

        assert d.toggle('TEMPO', 2) == 'too_many_groups'
        assert d.selectedKeys() == (('FM', 1), ('BECMG', 1), ('BECMG', 2), ('BECMG', 3),
                                    ('TEMPO', 1))

    def test_deselecting_cascades_to_the_later_groups_of_the_family(self):
        d = draft()
        for group in (('BECMG', 1), ('BECMG', 2), ('BECMG', 3), ('TEMPO', 1)):
            d.toggle(*group)

        d.toggle('BECMG', 2)

        assert d.selectedKeys() == (('BECMG', 1), ('TEMPO', 1))

    def test_the_cascade_leaves_the_other_families_alone(self):
        d = draft()
        for group in (('FM', 1), ('TEMPO', 1), ('TEMPO', 2)):
            d.toggle(*group)

        d.toggle('FM', 1)

        assert d.selectedKeys() == (('TEMPO', 1), ('TEMPO', 2))

    def test_begin_empties_what_the_draft_holds(self):
        d = ready()
        d.prev()
        d.toggle('BECMG', 1)
        d.primary.period = '1006/1015'
        d.primary.durations = (FROZEN, FROZEN)
        d.groups[('BECMG', 1)].period = '1006/1015'

        d.clear()

        assert d.offset == 0
        assert d.selectedKeys() == ()
        assert d.primary.period == ''
        assert d.primary.durations is None
        assert d.groups[('BECMG', 1)].period == ''
        assert d.selectedStates() == []


class TestSelectedStates:
    """The draft answers "what is in this report" with states, not keys: the
    groups read each other's windows to make sense of their own periods."""

    def test_active_states_follow_the_selection_order(self):
        d = ready()
        d.register(('BECMG', 2), GroupState('KT', indicator='BECMG'))
        d.register(('TEMPO', 1), GroupState('KT', indicator='TEMPO'))
        for group in (('TEMPO', 1), ('BECMG', 1), ('BECMG', 2)):
            d.toggle(*group)

        assert [state.indicator for state in d.selectedStates()] == ['BECMG', 'BECMG', 'TEMPO']

    def test_a_family_narrows_the_lookup(self):
        d = ready()
        d.register(('TEMPO', 1), GroupState('KT', indicator='TEMPO'))
        for group in (('BECMG', 1), ('TEMPO', 1)):
            d.toggle(*group)

        assert [state.indicator for state in d.selectedStates('BECMG')] == ['BECMG']
        assert d.selectedStates('FM') == []


class TestCompose:
    """The draft answers two questions on its own: what it is, and whether it
    could go. Both used to be the presenter's, assembled from the states there.
    """

    def filled(self):
        d = ready()
        p = d.primary
        p.icao = 'ZUUU'
        p.date = '100800'
        p.period = '1009/1018'
        p.durations = d.taf().durations()
        p.wind = '24008'
        p.visibility = '9999'
        p.clouds = ['SCT020']
        return d

    def test_the_draft_composes_its_own_heading_and_body(self):
        message = self.filled().compose()

        assert message.type == 'FC'
        assert message.heading == 'FC ZUUU 100800'
        assert message.text == 'TAF ZUUU 100800Z 1009/1018 24008KT 9999 SCT020='
        assert message.text.endswith('=')

    def test_an_unselected_group_stays_out_of_the_body(self):
        d = self.filled()

        assert 'BECMG' not in d.compose().text

    def test_a_selected_group_joins_the_body(self):
        d = self.filled()
        d.toggle('BECMG', 1)
        group = d.groups[('BECMG', 1)]
        group.period = '1012/1014'
        group.durations = (d.taf().durations()[0], d.taf().durations()[1])
        group.wind = '30010'

        assert 'BECMG 1012/1014' in d.compose().text

    def test_a_report_with_a_header_and_weather_is_acceptable(self):
        assert self.filled().isAcceptable() is True

    def test_an_empty_draft_is_not_acceptable(self):
        assert ready().isAcceptable() is False

    def test_a_selected_group_has_to_be_acceptable_too(self):
        d = self.filled()
        d.toggle('BECMG', 1)

        # the group has no period and no weather yet
        assert d.isAcceptable() is False
