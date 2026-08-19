from PyQt5.QtCore import QCoreApplication, QTimer
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLayout

from tafor.core.models import Taf
from tafor.ui.widgets import TafBecmgSegment, TafFmSegment, TafPrimarySegment, TafTempoSegment
from tafor.ui.widgets.editor import BaseEditor
    

def composeHeading(spec, area, icao, date, sequence):
    tt = spec[:2].upper() if spec else "FC"
    messages = [tt + area, icao, date, sequence]
    return " ".join(filter(None, messages))


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
            c.toggled.connect(lambda _, c=c: self.view.updateGroupsVisibility(c))

        for s in self.view.segments():
            s.contentChanged.connect(self.enableNextButton)

        self.view.primary.period.textChanged.connect(self.clear)
        self.view.nextButton.clicked.connect(self.beforeNext)

    def previewMessage(self):        
        def sortKey(s):
            if s.identifier == 'PRIMARY':
                return (0, 0, 0)

            # Sort by segment identifier priority
            orders = ['FM', 'BECMG', 'TEMPO']
            priority = orders.index(s.identifier) if s.identifier in orders else 99
            # Use start duration for groups to maintain chronological order
            return (1, s.state.durations[0], priority)

        # Retrieve and sort active segments
        activeSegments = sorted(self.view.segments(activeOnly=True), key=sortKey)
        
        messages = [s.state.composeMessage() for s in activeSegments]
        text = '\n'.join(filter(None, messages)) + '='

        # Composing Heading from primary state
        primary = self.view.primary
        state = primary.state
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

    def __init__(self, parent=None, sender=None, conf=None, context=None, database=None):
        super(TafEditor, self).__init__(parent, sender, conf, context, database)
        self.presenter = TafPresenter(self, context, conf)
        self.initUI()
        self.presenter.initialize()
        self.setWindowTitle(QCoreApplication.translate('Editor', 'Encoding Terminal Aerodrome Forecast'))

    def initUI(self):
        window = QWidget(self)
        layout = QVBoxLayout(window)
        layout.setSizeConstraint(QLayout.SetFixedSize)
        layout.setSpacing(18)
        
        self.primary = TafPrimarySegment(parent=self, conf=self.conf, context=self.context, database=self.database)
        self.fm = TafFmSegment('FM', self, conf=self.conf, context=self.context)
        self.becmg1 = TafBecmgSegment('BECMG1', self, conf=self.conf, context=self.context)
        self.becmg2 = TafBecmgSegment('BECMG2', self, conf=self.conf, context=self.context)
        self.becmg3 = TafBecmgSegment('BECMG3', self, conf=self.conf, context=self.context)
        self.tempo1 = TafTempoSegment('TEMPO1', self, conf=self.conf, context=self.context)
        self.tempo2 = TafTempoSegment('TEMPO2', self, conf=self.conf, context=self.context)
        self.tempo3 = TafTempoSegment('TEMPO3', self, conf=self.conf, context=self.context)
        
        self.becmgs = [self.fm, self.becmg1, self.becmg2, self.becmg3]
        self.tempos = [self.tempo1, self.tempo2, self.tempo3]
        
        layout.addWidget(self.primary)
        for segment in self.becmgs + self.tempos:
            layout.addWidget(segment)
            segment.hide()
            
        self.addBottomBox(layout)
        self.setLayout(layout)
        self.setStyleSheet('QLineEdit {width: 50px;} QComboBox {width: 50px;}')

    def segments(self, activeOnly=False):
        """Return segments, optionally filtering for active ones."""
        allSegments = [self.primary] + self.becmgs + self.tempos
        if activeOnly:
            return [s for s in allSegments if s == self.primary or s.isVisible()]
        return allSegments

    def getGroupCheckboxes(self):
        return self.primary.groupCheckboxs

    def isCancelMode(self):
        return self.primary.isCancelMode()

    def setNextEnabled(self, enabled):
        self.nextButton.setEnabled(enabled)

    def clear(self):
        """Clear all segment data."""
        for s in self.segments():
            s.clear()

    def updateGroupsVisibility(self, clickedbox):
        """Handle visibility logic for change groups."""
        fmCheckboxs = [self.primary.fmCheckbox]
        becmgCheckboxs = [self.primary.becmg1Checkbox, self.primary.becmg2Checkbox, self.primary.becmg3Checkbox]
        tempoCheckboxs = [self.primary.tempo1Checkbox, self.primary.tempo2Checkbox, self.primary.tempo3Checkbox]
        fmGroups = [self.fm]
        becmgGroups = [self.becmg1, self.becmg2, self.becmg3]
        tempoGroups = [self.tempo1, self.tempo2, self.tempo3]

        checks = [c for c in fmCheckboxs + becmgCheckboxs + tempoCheckboxs if c.isChecked()]
        if len(checks) > 5:
            clickedbox.setChecked(False)
            self.context.flash.editor('taf', QCoreApplication.translate('Editor', 'Change groups cannot be more than 5'))
            return

        def manipulate(checkboxs, groups):
            if clickedbox not in checkboxs:
                return

            index = checkboxs.index(clickedbox)
            if clickedbox.isChecked():
                if index != 0 and not checkboxs[index-1].isChecked():
                    clickedbox.setChecked(False)
            else:
                for i, checkbox in enumerate(checkboxs):
                    if i > index:
                        checkbox.setChecked(False)

            for i, group in enumerate(groups):
                group.setVisible(checkboxs[i].isChecked())

        manipulate(fmCheckboxs, fmGroups)
        manipulate(becmgCheckboxs, becmgGroups)
        manipulate(tempoCheckboxs, tempoGroups)

    def closeEvent(self, event):
        super(TafEditor, self).closeEvent(event)
        self.presenter.clear()
        self.primary.clearType()

    def showEvent(self, event):
        if not self.conf.checkCompleteness('taf'):
            QTimer.singleShot(0, self.showConfigError)
            return
        
        if not self.isStaged:
            self.primary.updateMessageType()
