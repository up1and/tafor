import logging

from PyQt5.QtCore import QCoreApplication, Qt, pyqtSignal

from tafor.core.repositories import SigmetFilter
from tafor.core.sigmet import SigmetDraft
from tafor.core.sigmet.compose import nextSequence
from tafor.core.utils.time import utcnow
from tafor.ui.qt import Ui_sigmet
from tafor.ui.dialogs.base import BaseEditor
from tafor.ui.forms import AirmetGeneral, SigmetAsh, SigmetCancel, SigmetCustom, SigmetGeneral, SigmetTyphoon
from tafor.ui.map import SketchPanel

logger = logging.getLogger(__name__)


class SigmetPresenter:

    def __init__(self, view, context, conf, repository=None):
        self.view = view
        self.context = context
        self.conf = conf
        self.repository = repository
        self.draft = SigmetDraft(
            fir=conf.firName if conf else '',
            airport=conf.airport if conf else '',
            bulletinNumber=(conf.bulletinNumber or '') if conf else '',
        )

    def initialize(self):
        self.bindSignal()
        self.draft.attach(self.view.formState(self.draft.form))
        self.view.showForm(self.draft.form)

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
        self.view.formSelected.connect(self.selectForm)
        self.view.contentChanged.connect(self.updateNextButton)
        self.view.opened.connect(self.renderForm)
        self.view.closed.connect(self.clear)
        self.view.submitted.connect(self.commit)
        self.context.event.currentSigmetChanged.connect(self.updateSigmetGraphic)
        self.context.event.notificationChanged.connect(self.onNotificationChanged)
        self.bindGraphic()

    def onNotificationChanged(self, category):
        if category in ('SIGMET', 'AIRMET') and self.draft.form == 'custom':
            self.updateCustomText()

    def bindGraphic(self):
        """The sketch panel holds no context; every layer write and geometry
        parse comes through these signals and lands here."""
        self.view.graphic.refreshClicked.connect(self.refreshLayers)
        self.view.graphic.layerSelectionChanged.connect(self.selectLayers)
        self.view.graphic.trimChanged.connect(self.updateSigmetGraphic)
        # The Show Latest toggle is view state on SceneLayer, so the panel
        # handles it locally; layer fetches, selections and trim changes push
        # fresh data down from here.
        self.context.event.layersChanged.connect(self.updateLayers)
        if self.context.layer.getLayers():
            self.updateLayers()

    def selectForm(self, form):
        changed = self.draft.select(form)
        self.draft.attach(self.view.formState(form))
        self.view.showForm(form)

        if changed:
            self.renderForm()
            self.view.graphic.configureMode(
                self.draft.designator,
                'cancel' if form == 'cancel' else 'template',
            )
            self.updateSigmetGraphic()

    def renderForm(self):
        sequence = self.nextSequence(self.draft.designator)
        candidates = self.sigmets(designator=self.draft.designator) if self.draft.form == 'cancel' else None
        latestText = self.latestText(self.draft.designator) if self.draft.form == 'custom' else None
        self.view.seedForm(sequence, candidates=candidates, latestText=latestText)
        self.updateNextButton()

    def updateCustomText(self):
        self.view.setCustomText(self.latestText(self.draft.designator))

    def sigmetGeometries(self, *, designator=None, category=None, trim=True):
        boundaries = self.context.layer.boundaries()
        if not boundaries:
            return []

        geometries = []
        for sig in self.sigmets(designator=designator, category=category):
            parser = sig.parser()
            try:
                geometries.append(parser.geo(boundaries, trim))
            except Exception as e:
                logger.error('Decode SIGMET graphic area error, {}, {}'.format(sig.text, e))
        return geometries

    def updateSigmetGraphic(self, trim=None):
        if trim is None:
            trim = self.view.graphic.trimShapes

        if self.draft.form == 'custom':
            return

        if self.draft.form == 'cancel':
            geometries = self.sigmetGeometries(designator=self.draft.designator, trim=trim)
        else:
            geometries = self.sigmetGeometries(category=self.draft.category(), trim=trim)

        self.view.graphic.setSigmets(geometries)

    def updateLayers(self):
        groups = self.context.layer.groupLayers()
        selected = list(self.context.layer.selected)
        active = self.context.layer.currentLayers()
        stackable = {
            layer.name
            for layer in groups.get('mixed', [])
            if self.context.layer.canStack(layer.name)
        }
        maxExtent = self.context.layer.maxExtent()
        self.view.graphic.setLayers(
            groups=groups,
            selected=selected,
            active=active,
            stackable=stackable,
            maxExtent=maxExtent,
        )

    def refreshLayers(self):
        self.context.layer.refreshLayers()

    def selectLayers(self, selected):
        filtered = self.context.layer.filterSelected(selected)
        if filtered == self.context.layer.selected:
            if filtered != list(selected):
                self.updateLayers()
            return

        self.context.layer.setState({'selected': filtered})

    def commit(self):
        # Read the form before judging it: see TafPresenter.commit().
        self.view.collect()
        self.view.validate()

        if self.hasAcceptableInput():
            self.view.finished.emit(self.compose())

    def compose(self):
        """The draft composes itself against the settings and the sketch as
        they are now: the bulletin prefix, the airport and the FIR are settings,
        not facts frozen when the presenter was built.
        """
        self.draft.fir = self.conf.firName
        self.draft.airport = self.conf.airport
        self.draft.bulletinNumber = self.conf.bulletinNumber or ''

        locations = self.view.graphic.location() if self.draft.hasSketch() else None
        return self.draft.compose(locations)

    def hasAcceptableInput(self):
        """Whether this draft could go: the document's verdict, then the canvas's."""
        return self.draft.isAcceptable() and (
            not self.draft.hasSketch() or self.view.graphic.hasAcceptableGraphic()
        )

    def updateNextButton(self):
        self.view.setNextEnabled(self.hasAcceptableInput())

    def clear(self):
        self.context.notification.sigmet.clear()
        self.draft.header.clear()
        self.view.clear()
        # re-render the canvas tool from the draft: modeChanged carries the
        # designator default back into state.mode, so the cleared state and
        # the canvas agree instead of drifting until the next form switch
        self.view.graphic.configureMode(
            self.draft.designator,
            'cancel' if self.draft.form == 'cancel' else 'template',
        )
        self.updateNextButton()


class SigmetEditor(BaseEditor, Ui_sigmet.Ui_Editor):

    editorName = 'sigmet'
    formSelected = pyqtSignal(str)
    contentChanged = pyqtSignal()

    def __init__(self, parent=None, sender=None, conf=None, context=None, repository=None):
        super().__init__(parent, sender, conf, context)
        self.setupUi(self)
        self.presenter = SigmetPresenter(self, context, conf, repository)
        self.initUI(self.presenter.draft.header)
        self.bindSignal()
        self.presenter.initialize()
        self.setWindowTitle(QCoreApplication.translate('Editor', 'Encoding Significant Meteorological Information'))

    def initUI(self, header):
        self.graphic = SketchPanel(
            self,
            projection=self.context.layer.projection(),
            boundaries=self.context.layer.boundaries(),
        )
        self.generalContent = SigmetGeneral(header=header, conf=self.conf)
        self.typhoonContent = SigmetTyphoon(header=header, conf=self.conf)
        self.ashContent = SigmetAsh(header=header, conf=self.conf)
        self.airmetContent = AirmetGeneral(header=header, conf=self.conf)
        self.cancelContent = SigmetCancel(header=header, conf=self.conf)
        self.customForm = SigmetCustom(header=header, conf=self.conf)

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

        self.showForm('general')
        self.addBottomBox(self.mainLayout)

    def bindSignal(self):
        for radio in (
            self.significantWeather,
            self.tropicalCyclone,
            self.volcanicAsh,
            self.airmansWeather,
            self.template,
            self.custom,
            self.cancel,
        ):
            radio.clicked.connect(lambda: self.formSelected.emit(self.current()))

        self.graphic.sketchChanged.connect(lambda _: self.contentChanged.emit())
        self.graphic.overlapChanged.connect(self.setOverlapMode)
        self.graphic.overlapChanged.connect(lambda _: self.contentChanged.emit())
        self.graphic.modeChanged.connect(self.setLocationMode)

        self.graphic.circleChanged.connect(self.typhoonContent.setTyphoonLocation)
        self.typhoonContent.circleChanged.connect(self.graphic.setTyphoonGraphic)

        self.ashContent.locationChanged.connect(self.graphic.setAdvisoryGraphic)
        self.typhoonContent.locationChanged.connect(self.graphic.setAdvisoryGraphic)

        for form in self.forms.values():
            form.contentChanged.connect(self.contentChanged.emit)
            form.notified.connect(self.showNotification)

    def formState(self, name):
        return self.forms[name].state

    def showForm(self, name):
        self.currentForm = self.forms[name]

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

    def seedForm(self, sequence, candidates=None, latestText=None):
        """Start a draft in the current form: sequence, span-derived period,
        and any form-specific seed before one read-back via reload()."""
        form = self.currentForm
        form.setSequence(sequence)
        form.resetPeriod()

        if form is self.cancelContent:
            form.setCandidates(candidates)
        elif form is self.customForm:
            form.setLatestText(latestText)

        form.reload()

    def setCustomText(self, latest):
        self.customForm.setLatestText(latest)
        self.customForm.reload()

    def collect(self):
        """Read the current form's widgets into its state -- the commit prelude.

        Only the form on screen: the other five keep their own drafts but they
        are not part of the report being composed.
        """
        self.currentForm.collect()

    def validate(self):
        self.currentForm.validate()

    def setOverlapMode(self, mode):
        if self.currentForm not in (self.cancelContent, self.customForm):
            self.currentForm.setOverlapMode(mode)

    def setLocationMode(self, mode):
        self.currentForm.setLocationMode(mode)

    def clear(self):
        for form in self.forms.values():
            form.clear()

        self.graphic.clear()

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
