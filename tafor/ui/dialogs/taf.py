from PyQt5.QtCore import QCoreApplication, pyqtSignal
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLayout

from tafor.core.taf import TafDraft, TafFormValidator, amendSequence, groupSpan
from tafor.ui.dialogs.base import BaseEditor
from tafor.ui.forms import TafBecmgSegment, TafFmSegment, TafPrimarySegment, TafTempoSegment
from tafor.ui.forms.taf import _translate


class TafPresenter:
    """What a TAF commit consists of, in order: validate, compose, emit.

    It reads the draft, not the widget tree: which report is being written and
    which groups are in it are the draft's business, and the states it composes
    from live there too.
    """

    def __init__(self, view, draft, conf, repository=None):
        self.view = view
        self.draft = draft
        self.conf = conf
        self.repository = repository

    def initialize(self):
        self.bindSignal()

    def bindSignal(self):
        self.view.groupToggled.connect(self.toggleGroup)

        for s in self.view.segments():
            s.contentChanged.connect(self.updateNextButton)
            s.notified.connect(lambda message: self.view.showNotification(message))

        for g in self.view.groups:
            g.periodFinished.connect(lambda segment=g: self.validateGroupPeriod(segment))

        self.view.primary.modifierChanged.connect(lambda _: self.updateHeader())
        self.view.primary.periodShiftRequested.connect(self.shiftPeriod)

    def toggleGroup(self, family, number):
        """A change-group checkbox was toggled: move the selection, then draw it."""
        error = self.draft.toggle(family, number)
        if error == 'too_many_groups':
            self.view.showNotification(QCoreApplication.translate('Editor', 'Change groups cannot be more than 5'))
        self.view.applySelection()
        self.updateNextButton()

    def impliedPeriod(self, taf, modifier):
        """The validity period the modifier implies."""
        period = taf.period()

        if modifier is None:
            # The normal report for this period is already out: leave the field
            # empty rather than offering the same report twice.
            return '' if self.repository.hasRecent(period) is not None else period

        return period

    def amendNumber(self, period, modifier):
        """The sequence to offer based on stored reports for this period."""
        count = self.repository.amendCount(period, modifier)
        return amendSequence(count, modifier)

    def updateHeader(self):
        """Re-derive the header the radios imply and redraw the draft."""
        modifier = self.view.primary.modifier
        period = self.impliedPeriod(self.draft.taf(), modifier)
        # A cancellation is numbered like an amendment; only a correction has
        # its own notation.
        notation = 'COR' if modifier == 'COR' else 'AMD'
        sequence = self.amendNumber(period, notation) if modifier else ''

        # The validator goes in before the draw: populating writes the sequence,
        # and the state the draw leaves behind is judged by it.
        self.view.primary.setSequenceValidator(modifier)
        self.draft.begin(period=period, modifier=modifier, sequence=sequence)
        self.view.populate()
        self.view.primary.setGroupCheckboxes(modifier != 'CNL')
        self.updateNextButton()

    def shiftPeriod(self, action):
        if action == 'current':
            self.draft.toCurrent()
        elif action == 'prev':
            self.draft.prev()
        else:
            return

        self.updateHeader()

    def validateGroupPeriod(self, segment):
        if segment.indicator == 'FM':
            span = ''
            error = TafFormValidator.checkFmPeriod(segment.state, self.draft.primary)
        else:
            span = groupSpan(segment.indicator, self.draft.spec)
            error = TafFormValidator.checkGroupPeriod(segment.state, self.draft.primary, span)

        if error:
            segment.clearPeriod()
            self.view.showNotification(_translate(error, span=span))
            return

        self.validateGroupOverlap(segment)

    def validateGroupOverlap(self, segment):
        if segment.indicator == 'FM':
            siblings = self.draft.selectedStates('BECMG')
            error = TafFormValidator.checkFmOverlap(segment.state, siblings)
        else:
            siblings = [state for state in self.draft.selectedStates(segment.indicator)
                        if state is not segment.state]
            error = TafFormValidator.checkGroupOverlap(segment.state, siblings)

        if error:
            segment.clearPeriod()
            self.view.showNotification(_translate(error))

    def commit(self):
        """Read what is on screen, judge it, and hand the message on.

        The collect comes first: a control whose signal never fired must not be
        validated, nor composed, from the value it did not carry. compose() is
        then a pure read of the state.
        """
        self.view.collect()

        # Validate all active segments before proceeding
        if not self.view.isCancelMode():
            for s in self.view.segments(selectedOnly=True):
                s.validate()
            for g in self.view.selectedGroups():
                self.validateGroupPeriod(g)

        if self.hasAcceptableInput():
            self.view.finished.emit(self.compose())

    def compose(self):
        """The draft composes itself; the presenter only hands the model on."""
        return self.view.compose()

    def hasAcceptableInput(self):
        """Whether the draft could be sent: the primary and every selected group."""
        return self.draft.isAcceptable()

    def updateNextButton(self):
        self.view.setNextEnabled(self.hasAcceptableInput())

    def clear(self):
        self.draft.clear()
        self.view.populate()
        self.updateNextButton()


class TafEditor(BaseEditor):

    editorName = 'taf'
    groupToggled = pyqtSignal(str, int)

    def __init__(self, parent=None, sender=None, conf=None, context=None, repository=None):
        super().__init__(parent, sender, conf, context)
        self.initUI()
        self.presenter = TafPresenter(self, self.draft, conf, repository)
        self.presenter.initialize()
        self.setWindowTitle(QCoreApplication.translate('Editor', 'Encoding Terminal Aerodrome Forecast'))

    def initUI(self):
        window = QWidget(self)
        layout = QVBoxLayout(window)
        layout.setSizeConstraint(QLayout.SetFixedSize)
        layout.setSpacing(18)

        self.draft = TafDraft(self.context.taf.spec, bulletinNumber=self.conf.bulletinNumber)

        self.primary = TafPrimarySegment(conf=self.conf, context=self.context)
        # Every group reads the primary report's window and period straight from
        # its state, live: the primary has to exist before they are built.
        kwargs = dict(conf=self.conf, context=self.context, primary=self.primary.state)
        self.fm = TafFmSegment('FM', **kwargs)
        self.becmg1 = TafBecmgSegment('BECMG', **kwargs)
        self.becmg2 = TafBecmgSegment('BECMG', **kwargs)
        self.becmg3 = TafBecmgSegment('BECMG', **kwargs)
        self.tempo1 = TafTempoSegment('TEMPO', **kwargs)
        self.tempo2 = TafTempoSegment('TEMPO', **kwargs)
        self.tempo3 = TafTempoSegment('TEMPO', **kwargs)
        
        self.becmgs = [self.fm, self.becmg1, self.becmg2, self.becmg3]
        self.tempos = [self.tempo1, self.tempo2, self.tempo3]
        self.groups = self.becmgs + self.tempos

        # Which box each group is, written onto the segment itself. The number
        # is not part of the segment name -- all three BECMG segments are named
        # 'BECMG' -- so it is read off the segment's position among its own
        # family here, in the only layer that knows how many boxes there are.
        for family in TafDraft.families:
            sameFamily = [g for g in self.groups if g.indicator == family]
            for number, segment in enumerate(sameFamily, start=1):
                segment.key = (family, number)

        # The same groups, addressed by key instead of by position. A lookup,
        # not an ordering: the order a report is written in is the draft's.
        self.segmentsByKey = {segment.key: segment for segment in self.groups}

        self.draft.attach(self.primary.state)
        for segment in self.groups:
            self.draft.register(segment.key, segment.state)
        
        layout.addWidget(self.primary)
        for segment in self.groups:
            layout.addWidget(segment)
            segment.hide()

        for checkbox, group in zip(self.primary.groupCheckboxs, self.groups):
            key = group.key
            checkbox.toggled.connect(lambda _, key=key: self.groupToggled.emit(*key))
            
        self.addBottomBox(layout)
        self.setLayout(layout)

    def segments(self, selectedOnly=False):
        """Return segments, optionally filtering for the selected groups."""
        if selectedOnly:
            return [self.primary] + self.selectedGroups()
        return [self.primary] + self.groups

    def collect(self):
        """Read every active segment's widgets into its state.

        The commit prelude: called by the presenter's commit() so that the
        message is composed from what is on screen, not from the last value a
        signal happened to collect. Unselected groups are left alone -- their
        state is not part of this report.
        """
        for segment in self.segments(selectedOnly=True):
            segment.collect()

    def selectedGroups(self):
        """The selected change-group segments, in the order they are reported.

        The draft holds both halves of that, so the order is read off it rather
        than off `self.groups`.
        """
        return [self.segmentsByKey[key] for key in self.draft.selectedKeys()]

    def isCancelMode(self):
        return self.primary.isCancelMode()

    def setNextEnabled(self, enabled):
        self.nextButton.setEnabled(enabled)

    def clear(self):
        """Start a new draft: empty the data, then draw that emptiness."""
        self.presenter.clear()

    def populate(self):
        """Draw the draft: each segment from its state, then what follows from it.

        One pass, in this order: the fields, the selection the draft holds, and
        the navigation the window implies. Nothing here re-reads a widget.
        """
        for segment in self.segments():
            segment.populate()

        self.applySelection()
        self.updatePeriodButtons()

    def updatePeriodButtons(self):
        """Prev/Reset follow the window the draft is on, not the click that moved it."""
        self.primary.resetButton.setEnabled(self.draft.isBackdated())
        self.primary.prevButton.setEnabled(self.draft.hasPrevious())

    def applySelection(self):
        """Draw `draft.selected` into the checkboxes and the group widgets."""
        for checkbox, group in zip(self.primary.groupCheckboxs, self.groups):
            selected = group.key in self.draft.selected
            # This is populating, not a click: without blocking, the writes below
            # would come straight back through toggleGroup and fight the
            # selection they are drawing.
            checkbox.blockSignals(True)
            checkbox.setChecked(selected)
            checkbox.blockSignals(False)
            group.setVisible(selected)

    def compose(self):
        """The draft composes itself against the settings as they are now.

        The bulletin prefix is a setting, not a document fact: syncing it here
        is what keeps a heading composed after a settings change current.
        """
        self.draft.bulletinNumber = self.conf.bulletinNumber
        return self.draft.compose()

    def onOpen(self):
        self.presenter.updateHeader()

    def onClose(self):
        # clear() is the whole reset now: it empties the draft and draws it,
        # radios and period buttons included.
        self.presenter.clear()
