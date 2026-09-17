import datetime

from tafor.core.taf import TafDraft
from tafor.core.taf.spec import SpecFC, SpecFT24


FROZEN = datetime.datetime(2026, 6, 10, 8, 0)


def draft(spec=SpecFC):
    return TafDraft(spec, now=lambda: FROZEN)


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
        assert d.canPrev()

        d.prev()
        assert d.canPrev()

        d.prev()
        assert not d.canPrev()

    def test_reset_goes_back_to_the_current_report(self):
        d = draft()
        d.prev()
        assert d.canReset()

        d.reset()

        assert d.offset == 0
        assert not d.canReset()
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
        assert d.activeGroups() == (('BECMG', 1),)

        assert d.toggle('BECMG', 1) is None
        assert d.activeGroups() == ()

    def test_active_groups_are_ordered_by_family(self):
        d = draft()
        for group in (('TEMPO', 1), ('BECMG', 1), ('FM', 1)):
            assert d.toggle(*group) is None

        assert d.activeGroups() == (('FM', 1), ('BECMG', 1), ('TEMPO', 1))

    def test_a_family_must_be_contiguous_from_the_front(self):
        d = draft()

        assert d.toggle('BECMG', 2) == 'group_not_contiguous'
        assert d.activeGroups() == ()

        assert d.toggle('BECMG', 1) is None
        assert d.toggle('BECMG', 2) is None
        assert d.activeGroups() == (('BECMG', 1), ('BECMG', 2))

    def test_at_most_five_groups(self):
        d = draft()
        for group in (('FM', 1), ('BECMG', 1), ('BECMG', 2), ('BECMG', 3), ('TEMPO', 1)):
            assert d.toggle(*group) is None

        assert d.toggle('TEMPO', 2) == 'too_many_groups'
        assert d.activeGroups() == (('FM', 1), ('BECMG', 1), ('BECMG', 2), ('BECMG', 3),
                                    ('TEMPO', 1))

    def test_deselecting_cascades_to_the_later_groups_of_the_family(self):
        d = draft()
        for group in (('BECMG', 1), ('BECMG', 2), ('BECMG', 3), ('TEMPO', 1)):
            d.toggle(*group)

        d.toggle('BECMG', 2)

        assert d.activeGroups() == (('BECMG', 1), ('TEMPO', 1))

    def test_the_cascade_leaves_the_other_families_alone(self):
        d = draft()
        for group in (('FM', 1), ('TEMPO', 1), ('TEMPO', 2)):
            d.toggle(*group)

        d.toggle('FM', 1)

        assert d.activeGroups() == (('TEMPO', 1), ('TEMPO', 2))

    def test_clear_drops_the_selection(self):
        d = draft()
        for group in (('FM', 1), ('BECMG', 1)):
            d.toggle(*group)

        d.clear()

        assert d.activeGroups() == ()
