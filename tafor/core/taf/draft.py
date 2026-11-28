from tafor.core.models import Taf
from tafor.core.taf.compose import composeBody, composeHeading
from tafor.core.taf.spec import CurrentTaf
from tafor.core.utils.time import utcnow


class TafDraft:
    """What the editor is drafting: which report, which change groups, and the
    states behind them.

    Qt-free. The pieces of knowledge that used to live in the widgets are here:
    the period offset behind the prev/reset buttons, the change-group selection,
    and -- since the groups read each other's windows -- the groups themselves,
    keyed by which box they are. A group needs the primary's window and its
    siblings' windows to make sense of its own period; asking the draft is what
    keeps that a lookup rather than a walk up through the widgets.

    The vocabulary is the one the reports use: `primary` and `groups` are the
    states, `selected`/`selectedKeys()` are which of them are in this report.
    """

    # The three change-group families, in the order they are reported. A group
    # is a family plus a position in it (BECMG, 2); the position is the UI's
    # knowledge, so it arrives as an argument rather than being read back out of
    # a name.
    families = ('FM', 'BECMG', 'TEMPO')

    def __init__(self, spec, bulletinNumber='', now=utcnow):
        self.spec = spec
        self.now = now
        self.bulletinNumber = bulletinNumber
        self.offset = 0
        self.selected = set()
        self.primary = None   # PrimaryState, attached once the primary exists
        self.groups = {}      # (family, number) -> GroupState

    def taf(self):
        """The report the current offset points at."""
        return CurrentTaf(self.spec, time=self.now(), offset=self.offset)

    def prev(self):
        """Step one report back, no further than -2."""
        self.offset = max(self.offset - 1, -2)

    def hasPrevious(self):
        return self.offset > -2

    def toCurrent(self):
        """Back to the window the clock is in now."""
        self.offset = 0

    def isBackdated(self):
        return self.offset != 0

    def toggle(self, family, number):
        """Select or deselect one change group, returning an error code or None.

        Three rules, in this order: at most 5 groups selected; a family selected
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

    def selectedKeys(self):
        """The (family, number) pairs in this report, ordered FM / BECMG / TEMPO.

        Keys, not groups: `groups` is the map from a key to the state behind it,
        so this is the "which ones" half and `selectedStates()` is the other.
        """
        return tuple(sorted(self.selected,
                            key=lambda group: (self.families.index(group[0]), group[1])))

    def attach(self, primary):
        """Take the primary report's state: the window every group reads."""
        self.primary = primary

    def register(self, key, state):
        """Register the state behind one change group.

        The editor calls this as it builds its segments: the key is the UI's
        knowledge (which family, which box), the state is what everyone else
        wants to reach.
        """
        self.groups[key] = state

    def selectedStates(self, family=None):
        """The states of the selected groups, in reporting order."""
        return [self.groups[key] for key in self.selectedKeys()
                if family is None or key[0] == family]

    def compose(self):
        """The message this draft is: its own heading and body, no widgets.

        This is the draft answering the third criterion -- delete every control
        and the report is still here. What the draft cannot know stays with the
        caller: the model wrapper and where the message goes.
        """
        primary = self.primary
        heading = composeHeading(self.spec, self.bulletinNumber,
                                 primary.icao, primary.date, primary.sequence)

        return Taf(type=heading[0:2], heading=heading,
                   text=composeBody(primary, self.selectedStates()))

    def isAcceptable(self):
        """Whether this report could be sent as it stands."""
        return (self.primary.isAcceptable()
                and all(state.isAcceptable() for state in self.selectedStates()))

    def clear(self):
        """Empty the whole draft: back to the current window, nothing kept.

        The data is cleared here rather than in the widgets so that drawing can
        be a plain render -- there is no half-cleared state left for a widget
        write to collect back over.
        """
        self.offset = 0
        self.discard()
        self.begin()

    def begin(self, period='', modifier=None, sequence=''):
        """Start the report this header belongs to.

        One header, written as one fact: a report at this period has one answer
        for period, durations, modifier and sequence. What has been typed
        survives unless the window moved -- switching the marker on the same
        window re-labels the report, it does not start another one. The caller
        does not pick between the two: the period decides.

        `offset` is left alone on purpose: stepping back one window and then
        beginning a report must not also step the window forward again.
        """
        discarded = period != self.primary.period
        if discarded:
            self.discard()

        self.primary.period = period
        self.primary.durations = self.taf().durations() if period else None
        self.primary.modifier = modifier
        self.primary.sequence = sequence

        if modifier == 'CNL':
            # A cancellation carries no change groups.
            self.selected.clear()

        return discarded

    def discard(self):
        """Throw away the report's body -- the primary and every group -- and
        which groups were selected, leaving the clock date and header for the caller."""
        date = self.primary.date
        self.selected.clear()
        self.primary.clear()
        self.primary.date = date
        for state in self.groups.values():
            state.clear()
