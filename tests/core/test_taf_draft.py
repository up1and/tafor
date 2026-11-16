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
