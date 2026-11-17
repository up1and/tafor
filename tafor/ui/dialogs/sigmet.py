from PyQt5.QtCore import QCoreApplication, Qt

from tafor.core.repositories import SigmetFilter
from tafor.core.sigmet import SigmetDraft
from tafor.core.sigmet.compose import nextSequence
from tafor.core.utils.time import utcnow
from tafor.ui.qt import Ui_sigmet
from tafor.ui.dialogs.base import BaseEditor
from tafor.ui.forms import AirmetGeneral, SigmetAsh, SigmetCancel, SigmetCustom, SigmetGeneral, SigmetTyphoon
from tafor.ui.map import SketchPanel


class SigmetPresenter:

    def __init__(self, view, context, conf, repository=None):
        self.view = view
        self.context = context
        self.conf = conf
        self.repository = repository

    def initialize(self):
        self.bindSignal()

    def nextSequence(self, designator):
        """The number this draft gets: today's stored reports of the same
        designator decide where the count restarts."""
        sigmets = self.repository.countToday(designator)
        return nextSequence([sig.heading for sig in sigmets], utcnow())

    def sigmets(self, *, designator=None, category=None):
        """The reports in force, narrowed by how they are addressed.

        A designator is one code (WS), a category is every code filed under
        that bulletin sign (SIGMET covers WS, WC and WV). Pass exactly one of
        the two: SigmetFilter resolves a designator before a category, so both
        at once would silently ignore the category, and neither returns every
        report in force.
        """
        return self.context.current.filterSigmets(
            SigmetFilter(designator=designator, category=category))

    def latestText(self, designator):
        """The text the custom form starts from -- (source, content) or None.

        A notification still waiting to be handled comes first: it is the
        message the operator was just handed. The stored report is what the
        form falls back to, and the source travels with the content because
        the api sign shows where the text came from.
        """
        return self.notificationText(designator) or self.databaseText(designator)

    def notificationText(self, designator):
        parser = self.context.notification.sigmet.parser()
        if parser and designator == parser.type():
            return 'notification', parser.content()

    def databaseText(self, designator):
        last = self.repository.latest(designator)
        if last:
            return 'database', last.parser().content()

    def bindSignal(self):
        self.view.significantWeather.clicked.connect(self.view.changeContent)
        self.view.tropicalCyclone.clicked.connect(self.view.changeContent)
        self.view.volcanicAsh.clicked.connect(self.view.changeContent)
        self.view.airmansWeather.clicked.connect(self.view.changeContent)
        self.view.template.clicked.connect(self.view.changeContent)
        self.view.custom.clicked.connect(self.view.changeContent)
        self.view.cancel.clicked.connect(self.view.changeContent)

        self.view.graphic.sketchChanged.connect(self.enableNextButton)
        self.view.graphic.overlapChanged.connect(self.enableNextButton)
        self.view.graphic.overlapChanged.connect(self.view.setOverlapMode)
        self.view.graphic.modeChanged.connect(self.view.setLocationMode)

        self.view.graphic.circleChanged.connect(self.view.typhoonContent.setTyphoonLocation)
        self.view.typhoonContent.circleChanged.connect(self.view.graphic.setTyphoonGraphic)

        self.view.ashContent.locationChanged.connect(self.view.graphic.setAdvisoryGraphic)
        self.view.typhoonContent.locationChanged.connect(self.view.graphic.setAdvisoryGraphic)

        for c in self.view.forms.values():
            c.contentChanged.connect(self.enableNextButton)

        self.connectGraphic()

    def connectGraphic(self):
        """The sketch panel only reads context; every layer write it asks for
        comes back through these signals and lands here."""
        self.view.graphic.refreshClicked.connect(self.refreshLayers)
        self.view.graphic.layerSelectionChanged.connect(self.selectLayers)
        # The display switches are view state, so the panel repaints them on
        # its own; a fetch or a selection change arrives from the service.
        self.context.event.layersChanged.connect(self.view.graphic.handleLayersChanged)

    def refreshLayers(self):
        self.context.layer.refreshLayers()

    def selectLayers(self, selected):
        self.context.layer.setState({'selected': selected})

    def commit(self):
        # Read the form before judging it: see TafPresenter.commit().
        self.view.collect()
        self.view.currentForm.validate()

        if self.hasAcceptableInput():
            self.view.finished.emit(self.compose())

    def compose(self):
        """The draft composes itself; the presenter only hands the model on."""
        return self.view.compose()

    def hasAcceptableInput(self):
        """The view answers: the draft's verdict plus the canvas's."""
        return self.view.isAcceptable()

    def enableNextButton(self):
        self.view.nextButton.setEnabled(self.hasAcceptableInput())

    def clear(self):
        self.context.notification.sigmet.clear()
        self.view.clear()


class SigmetEditor(BaseEditor, Ui_sigmet.Ui_Editor):

    editorName = 'sigmet'

    def __init__(self, parent=None, sender=None, conf=None, context=None, repository=None):
        super().__init__(parent, sender, conf, context)
        self.setupUi(self)

        # The heading's facts are the document's, so the draft is built with
        # them: compose() should not have to be handed what never changes.
        self.draft = SigmetDraft(
            fir=self.conf.firName,
            airport=self.conf.airport,
            bulletinNumber=self.conf.bulletinNumber or '',
        )

        # The forms hold no queries: the presenter owns the repository and
        # hands them the rows and text they render.
        self.presenter = SigmetPresenter(self, context, conf, repository)
        self.initUI()
        self.presenter.initialize()

        self.setWindowTitle(QCoreApplication.translate('Editor', 'Encoding Significant Meteorological Information'))

    @property
    def designator(self):
        return self.draft.designator

    @property
    def span(self):
        return self.draft.span()

    def initUI(self):
        self.graphic = SketchPanel(self, context=self.context)
        self.generalContent = SigmetGeneral(header=self.draft.header, editor=self, conf=self.conf)
        self.typhoonContent = SigmetTyphoon(header=self.draft.header, editor=self, conf=self.conf)
        self.ashContent = SigmetAsh(header=self.draft.header, editor=self, conf=self.conf)
        self.airmetContent = AirmetGeneral(header=self.draft.header, editor=self, conf=self.conf)
        self.cancelContent = SigmetCancel(header=self.draft.header, editor=self, conf=self.conf)
        self.customForm = SigmetCustom(header=self.draft.header, editor=self, conf=self.conf)

        self.forms = {
            'general': self.generalContent,
            'typhoon': self.typhoonContent,
            'ash': self.ashContent,
            'airmet': self.airmetContent,
            'cancel': self.cancelContent,
            'custom': self.customForm,
        }

        # The template forms are pages of one stack.
        for name in ('general', 'typhoon', 'ash', 'airmet', 'cancel'):
            self.formStack.addWidget(self.forms[name])

        self.contentLayout.addWidget(self.customForm)
        self.customForm.hide()
        self.contentLayout.addWidget(self.graphic)
        # Pin the canvas to the top of the row.
        self.contentLayout.setAlignment(self.graphic, Qt.AlignTop)
        self.contentLayout.addStretch()

        self.changeContent()
        self.addBottomBox(self.mainLayout)

    def updateGraphicCanvas(self):
        if self.draft.form == 'custom':
            return

        # A cancellation is shown the reports it may address, one code at a
        # time; a template the whole category, so the three codes that share
        # a bulletin sign stay together.
        if self.draft.form == 'cancel':
            sigmets = self.presenter.sigmets(designator=self.draft.designator)
        else:
            sigmets = self.presenter.sigmets(category=self.category())

        self.graphic.setSigmets(sigmets)

    def renderForm(self):
        """Start a draft in the current form: the number the presenter
        computed, the period the draft's span implies, then the rows only
        that form consumes.

        The order is the render order, not a preference. The candidates carry
        the cancelled report's own validity, and filling them rewrites the
        period, so they have to land after the period was reset -- that is how
        entering Cancel lands on the first candidate's period.

        This is the one place a new draft begins: the form cannot discover it
        on its own, because the switch and the successful send are the
        editor's events, not the form's.
        """
        form = self.currentForm
        form.setSequence(self.sequenceNumber())
        form.resetPeriod()

        if form is self.cancelContent:
            form.setCandidates(self.presenter.sigmets(designator=self.designator))
        elif form is self.customForm:
            form.setLatestText(self.presenter.latestText(self.designator))

        # Everything above only wrote widgets. Read it back once, here, so the
        # draft's header is filled by the same collect() a user edit uses.
        form.reload()
        self.presenter.enableNextButton()

    def sequenceNumber(self):
        """What number today's reports give this draft."""
        return self.presenter.nextSequence(self.designator)

    def updateCustomText(self):
        self.customForm.setLatestText(self.presenter.latestText(self.designator))
        self.customForm.reload()

    def collect(self):
        """Read the current form's widgets into its state -- the commit prelude.

        Only the form on screen: the other five keep their own drafts but they
        are not part of the report being composed.
        """
        self.currentForm.collect()

    def compose(self):
        """The draft composes itself, against the settings and the sketch as
        they are now: the bulletin prefix, the airport and the FIR are settings,
        not facts frozen when the editor was built.
        """
        self.draft.fir = self.conf.firName
        self.draft.airport = self.conf.airport
        self.draft.bulletinNumber = self.conf.bulletinNumber or ''

        locations = self.graphic.location() if self.draft.hasSketch() else None
        return self.draft.compose(locations)

    def category(self):
        return self.draft.category()

    def isGraphicAcceptable(self):
        """Whether the canvas is finished -- the one input the draft cannot own.

        True when this report needs no drawing: nothing to answer for.
        """
        return not self.draft.hasSketch() or self.graphic.hasAcceptableGraphic()

    def isAcceptable(self):
        """Whether this draft could go: the document's verdict, then the canvas's."""
        return self.draft.isAcceptable() and self.isGraphicAcceptable()

    def setOverlapMode(self, mode):
        if self.draft.hasSketch():
            self.currentForm.setOverlapMode(mode)

    def setLocationMode(self, mode):
        self.currentForm.setLocationMode(mode)

    def changeContent(self):
        form = self.current()
        changed = self.draft.select(form)
        self.currentForm = self.forms[form]
        self.draft.attach(self.currentForm.state)

        # Custom takes the canvas's place, so it is shown instead of the pair.
        if self.currentForm is self.customForm:
            self.customForm.show()
            self.formStack.hide()
            self.graphic.hide()
        else:
            self.customForm.hide()
            self.formStack.show()
            self.formStack.setCurrentWidget(self.currentForm)
            self.graphic.show()

        if changed:
            self.renderForm()
            self.graphic.configureMode(self.draft.designator, 'cancel' if form == 'cancel' else 'template')
            self.updateGraphicCanvas()

    def current(self):
        if self.cancel.isChecked():
            return 'cancel'

        if self.custom.isChecked():
            return 'custom'

        if self.tropicalCyclone.isChecked():
            return 'typhoon'

        if self.volcanicAsh.isChecked():
            return 'ash'

        if self.airmansWeather.isChecked():
            return 'airmet'

        return 'general'

    def clear(self):
        # The header belongs to the draft, so the draft empties it here; each
        # form then clears its own body and renders the empty header.
        self.draft.header.clear()

        for c in self.forms.values():
            c.clear()

        self.graphic.clear()
        # re-render the canvas tool from the draft: modeChanged carries the
        # designator default back into state.mode, so the cleared state and
        # the canvas agree instead of drifting until the next form switch
        self.graphic.configureMode(self.draft.designator,
                                   'cancel' if self.draft.form == 'cancel' else 'template')
        self.presenter.enableNextButton()

    def onOpen(self):
        self.renderForm()

    def onClose(self):
        self.presenter.clear()
