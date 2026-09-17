from PyQt5.QtCore import QCoreApplication
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLayout

from tafor.core.models import Taf
from tafor.core.taf import TafDraft, composeHeading, composeBody
from tafor.ui.widgets import TafBecmgSegment, TafFmSegment, TafPrimarySegment, TafTempoSegment
from tafor.ui.widgets.editor import BaseEditor


class TafPresenter:
    def __init__(self, view, context, conf):
        self.view = view
        self.context = context
        self.conf = conf

    def initialize(self):
        self.bindSignal()

    def bindSignal(self):
        for c in self.view.getGroupCheckboxes():
            c.stateChanged.connect(self.enableNextButton)
            c.toggled.connect(lambda _, c=c: self.view.toggleGroup(c))

        for s in self.view.segments():
            s.contentChanged.connect(self.enableNextButton)

    def previewMessage(self):
        """Take the active segments, let core compose them, then build the model."""
        state = self.view.primary.state
        groups = [s.state for s in self.view.segments(activeOnly=True) if s is not self.view.primary]

        text = composeBody(state, groups)
        heading = composeHeading(state.spec, self.conf.bulletinNumber, state.icao, state.date, state.sequence)

        message = Taf(type=heading[0:2], heading=heading, text=text)
        self.view.finished.emit(message)

    def beforeNext(self):
        # Validate all active segments before proceeding
        if not self.view.isCancelMode():
            for s in self.view.segments(activeOnly=True):
                s.validate()

        if self.hasAcceptableInput():
            self.previewMessage()

    def hasAcceptableInput(self):
        # Check if input is acceptable for all active segments
        return all(s.hasAcceptableInput() for s in self.view.segments(activeOnly=True))

    def enableNextButton(self):
        self.view.setNextEnabled(self.hasAcceptableInput())

    def clear(self):
        self.view.clear()


class TafEditor(BaseEditor):

    confGroup = 'taf'

    def __init__(self, parent=None, sender=None, conf=None, context=None, repository=None):
        super().__init__(parent, sender, conf, context)
        self.repository = repository
        self.presenter = TafPresenter(self, context, conf)
        self.initUI()
        self.presenter.initialize()
        self.setWindowTitle(QCoreApplication.translate('Editor', 'Encoding Terminal Aerodrome Forecast'))

    def initUI(self):
        window = QWidget(self)
        layout = QVBoxLayout(window)
        layout.setSizeConstraint(QLayout.SetFixedSize)
        layout.setSpacing(18)

        self.draft = TafDraft(self.context.taf.spec)

        self.primary = TafPrimarySegment(editor=self, conf=self.conf, context=self.context,
                                         repository=self.repository, draft=self.draft)
        self.fm = TafFmSegment('FM', self, conf=self.conf, context=self.context)
        self.becmg1 = TafBecmgSegment('BECMG', self, conf=self.conf, context=self.context)
        self.becmg2 = TafBecmgSegment('BECMG', self, conf=self.conf, context=self.context)
        self.becmg3 = TafBecmgSegment('BECMG', self, conf=self.conf, context=self.context)
        self.tempo1 = TafTempoSegment('TEMPO', self, conf=self.conf, context=self.context)
        self.tempo2 = TafTempoSegment('TEMPO', self, conf=self.conf, context=self.context)
        self.tempo3 = TafTempoSegment('TEMPO', self, conf=self.conf, context=self.context)
        
        self.becmgs = [self.fm, self.becmg1, self.becmg2, self.becmg3]
        self.tempos = [self.tempo1, self.tempo2, self.tempo3]
        self.groups = self.becmgs + self.tempos
        
        layout.addWidget(self.primary)
        for segment in self.groups:
            layout.addWidget(segment)
            segment.hide()
            
        self.addBottomBox(layout)
        self.setLayout(layout)

    def segments(self, activeOnly=False):
        """Return segments, optionally filtering for active ones."""
        if activeOnly:
            return [self.primary] + self.activeGroups()
        return [self.primary] + self.groups

    def activeGroups(self):
        """The selected change-group segments, in the order they are reported.

        The draft holds both halves of that, so the order is read off it rather
        than off `self.groups`.
        """
        byKey = {self.groupKey(g): g for g in self.groups}
        return [byKey[key] for key in self.draft.activeGroups()]

    def groupKey(self, segment):
        """The (family, number) a group segment stands for.

        The number is not part of the segment name any more — all three BECMG
        segments are named 'BECMG' — so it is read off the segment's position
        among its own family here, in the UI, which is the only layer that knows
        how many boxes there are. 'FM' is alone in its family, so it comes out as
        ('FM', 1).

        """
        family = segment.indicator
        sameFamily = [g for g in self.groups if g.indicator == family]
        return family, sameFamily.index(segment) + 1

    def getGroupCheckboxes(self):
        return self.primary.groupCheckboxs

    def isCancelMode(self):
        return self.primary.isCancelMode()

    def setNextEnabled(self, enabled):
        self.nextButton.setEnabled(enabled)

    def clear(self):
        """Clear all segment data, and the change-group selection."""
        self.draft.clear()
        for s in self.segments():
            s.clear()

        self.applySelection()

    def toggleGroup(self, checkbox):
        """A change-group checkbox was clicked: move the selection, then draw it."""
        segment = self.groups[self.primary.groupCheckboxs.index(checkbox)]
        error = self.draft.toggle(*self.groupKey(segment))
        if error == 'too_many_groups':
            self.context.flash.editor('taf', QCoreApplication.translate('Editor', 'Change groups cannot be more than 5'))
        self.applySelection()

    def applySelection(self):
        """Draw `draft.selected` into the checkboxes and the group widgets."""
        for checkbox, group in zip(self.primary.groupCheckboxs, self.groups):
            selected = self.groupKey(group) in self.draft.selected
            # This is a render, not a click: without blocking, the writes below
            # would come straight back through toggleGroup and fight the
            # selection they are drawing.
            checkbox.blockSignals(True)
            checkbox.setChecked(selected)
            checkbox.blockSignals(False)
            group.setVisible(selected)

        self.presenter.enableNextButton()

    def onFirstShow(self):
        self.primary.updateModifier()

    def onClose(self):
        self.presenter.clear()
        self.primary.clearType()
