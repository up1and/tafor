from tafor.core.taf.spec import CurrentTaf
from tafor.core.utils.time import utcnow


class TafDraft:
    """What the editor is drafting: which report, and which change groups.

    Qt-free. Two pieces of knowledge that used to live in the widgets are here:
    the period offset behind the prev/reset buttons, and the change-group
    selection.
    """

    # The three change-group families, in the order they are reported. A group
    # is a family plus a position in it (BECMG, 2); the position is the UI's
    # knowledge, so it arrives as an argument rather than being read back out of
    # a name.
    families = ('FM', 'BECMG', 'TEMPO')

    def __init__(self, spec, now=utcnow):
        self.spec = spec
        self.now = now
        self.offset = 0
        self.selected = set()

    def taf(self):
        """The report the current offset points at."""
        return CurrentTaf(self.spec, time=self.now(), offset=self.offset)

    def prev(self):
        """Step one report back, no further than -2."""
        self.offset = max(self.offset - 1, -2)

    def canPrev(self):
        return self.offset > -2

    def reset(self):
        self.offset = 0

    def canReset(self):
        return self.offset != 0

    def toggle(self, family, number):
        """Select or deselect one change group, returning an error code or None.

        Three rules, in this order: at most 5 groups active; a family selected
        from the front and contiguously; deselecting a group also drops the
        later groups of its family. The caller turns the code into wording.

        """
        if (family, number) in self.selected:
            # The cascade: dropping BECMG2 drops BECMG3 with it.
            self.selected = {group for group in self.selected
                             if group[0] != family or group[1] < number}
            return

        if len(self.selected) >= 5:
            return 'too_many_groups'

        if number > 1 and (family, number - 1) not in self.selected:
            return 'group_not_contiguous'

        self.selected.add((family, number))

    def activeGroups(self):
        """The active (family, number) pairs, ordered FM / BECMG / TEMPO."""
        return tuple(sorted(self.selected,
                            key=lambda group: (self.families.index(group[0]), group[1])))

    def clear(self):
        self.selected.clear()
