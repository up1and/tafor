from PyQt5.QtCore import QCoreApplication

from tafor.core.models import Sigmet
from tafor.core.repositories import SigmetFilter
from tafor.core.sigmet import SigmetDraft
from tafor.core.sigmet.compose import composeHeading
from tafor.core.utils.time import utcnow
from tafor.ui.qt import Ui_sigmet
from tafor.ui.widgets import AirmetGeneral, SigmetAsh, SigmetCancel, SigmetCustom, SigmetGeneral, SigmetTyphoon
from tafor.ui.widgets.editor import BaseEditor
from tafor.ui.widgets.graphic import SketchPanel


class SigmetPresenter:

    def __init__(self, view, context, conf):
        self.view = view
        self.context = context
        self.conf = conf

    def initialize(self):
        self.bindSignal()

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

        for c in self.view.contents.values():
            c.contentChanged.connect(self.enableNextButton)

        self.view.sender.succeeded.connect(self.view.updateState)

    def beforeNext(self):
        self.view.currentContent.validate()

        if self.hasAcceptableInput():
            self.previewMessage()

    def previewMessage(self):
        message = Sigmet(type=self.view.designator, heading=self.view.heading(), text=self.view.message())
        self.view.finished.emit(message)

    def hasAcceptableInput(self):
        items = [self.view.currentContent.hasAcceptableInput()]
        if self.view.hasGraphicWindow():
            items.append(self.view.graphic.hasAcceptableGraphic())

        return all(items)

    def enableNextButton(self):
        self.view.nextButton.setEnabled(self.hasAcceptableInput())

    def clear(self):
        self.view.clear()


class SigmetEditor(BaseEditor, Ui_sigmet.Ui_Editor):

    confGroup = 'sigmet'

    def __init__(self, parent=None, sender=None, conf=None, context=None, repository=None):
        super().__init__(parent, sender, conf, context)
        self.repository = repository
        self.setupUi(self)

        self.draft = SigmetDraft()

        self.presenter = SigmetPresenter(self, context, conf)
        self.initUI()
        self.presenter.initialize()

        self.setWindowTitle(QCoreApplication.translate('Editor', 'Encoding Significant Meteorological Information'))

    @property
    def designator(self):
        return self.draft.designator

    def initUI(self):
        self.graphic = SketchPanel(self, context=self.context)
        self.generalContent = SigmetGeneral(self, conf=self.conf, context=self.context, repository=self.repository)
        self.typhoonContent = SigmetTyphoon(self, conf=self.conf, context=self.context, repository=self.repository)
        self.ashContent = SigmetAsh(self, conf=self.conf, context=self.context, repository=self.repository)
        self.airmetContent = AirmetGeneral(self, conf=self.conf, context=self.context, repository=self.repository)
        self.cancelContent = SigmetCancel(self, conf=self.conf, context=self.context, repository=self.repository)
        self.customContent = SigmetCustom(self, conf=self.conf, context=self.context, repository=self.repository)

        self.contents = {
            'general': self.generalContent,
            'typhoon': self.typhoonContent,
            'ash': self.ashContent,
            'airmet': self.airmetContent,
            'cancel': self.cancelContent,
            'custom': self.customContent,
        }

        for c in self.contents.values():
            self.contentLayout.addWidget(c)

        self.contentLayout.addWidget(self.graphic)
        self.changeContent()

        self.addBottomBox(self.mainLayout)

    def updateGraphicCanvas(self):
        if self.draft.form == 'custom':
            return

        if self.draft.form == 'cancel':
            sigmets = self.context.current.filterSigmets(SigmetFilter(designator=self.draft.designator))
        else:
            sigmets = self.context.current.filterSigmets(SigmetFilter(category=self.category()))

        self.graphic.setSigmets(sigmets)

    def updateLayer(self):
        self.graphic.updateLayer()

    def updateState(self):
        self.currentContent.initState()

    def updateCustomText(self):
        self.customContent.updateText()

    def heading(self):
        area = self.conf.bulletinNumber or ''
        return composeHeading(self.draft.designator, area, self.conf.airport, utcnow())

    def message(self):
        state = self.currentContent.state
        if self.draft.hasSketch():
            return state.composeMessage(self.conf.firName, self.graphic.location())
        return state.composeMessage(self.conf.firName)

    def category(self):
        return self.draft.category()

    def hasGraphicWindow(self):
        return self.draft.hasSketch()

    def setOverlapMode(self, mode):
        if self.draft.hasSketch():
            self.currentContent.setOverlapMode(mode)

    def setLocationMode(self, mode):
        self.currentContent.setLocationMode(mode)

    def changeContent(self):
        form = self.current()
        changed = self.draft.select(form)
        self.currentContent = self.contents[form]

        if self.currentContent == self.customContent:
            self.graphic.hide()
        else:
            self.graphic.show()

        for c in self.contents.values():
            if c == self.currentContent:
                c.show()
            else:
                c.hide()

        if changed:
            self.currentContent.setSpan(self.draft.span())
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
        for c in self.contents.values():
            c.clear()

        self.graphic.clear()

    def onFirstShow(self):
        self.updateState()

    def onClose(self):
        self.context.notification.sigmet.clear()
        self.presenter.clear()
