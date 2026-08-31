import datetime

from PyQt5.QtCore import QCoreApplication

from tafor.core.models import Sigmet
from tafor.core.repositories import SigmetFilter
from tafor.core.sigmet.issuance import composeHeading, validDuration
from tafor.ui.qt import Ui_sigmet
from tafor.ui.widgets import AirmetGeneral, SigmetAsh, SigmetCancel, SigmetCustom, SigmetGeneral, SigmetTyphoon
from tafor.ui.widgets.editor import BaseEditor
from tafor.ui.widgets.graphic import GraphicsWindow


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

        for c in self.view.contents:
            c.contentChanged.connect(self.enableNextButton)

        self.view.sender.succeeded.connect(self.view.updateState)

    def beforeNext(self):
        self.view.currentContent.validate()

        if self.hasAcceptableInput():
            self.previewMessage()

    def previewMessage(self):
        message = Sigmet(type=self.view.type, heading=self.view.heading(), text=self.view.message())
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

        self.type = 'WS'
        self.mode = 'template'

        self.presenter = SigmetPresenter(self, context, conf)
        self.initUI()
        self.presenter.initialize()

        self.setWindowTitle(QCoreApplication.translate('Editor', 'Encoding Significant Meteorological Information'))

    def initUI(self):
        self.graphic = GraphicsWindow(self, context=self.context)
        self.generalContent = SigmetGeneral(self, conf=self.conf, context=self.context, repository=self.repository)
        self.typhoonContent = SigmetTyphoon(self, conf=self.conf, context=self.context, repository=self.repository)
        self.ashContent = SigmetAsh(self, conf=self.conf, context=self.context, repository=self.repository)
        self.airmetContent = AirmetGeneral(self, conf=self.conf, context=self.context, repository=self.repository)
        self.cancelContent = SigmetCancel(self, conf=self.conf, context=self.context, repository=self.repository)
        self.customContent = SigmetCustom(self, conf=self.conf, context=self.context, repository=self.repository)

        self.contents = []
        self.contents.append(self.generalContent)
        self.contents.append(self.typhoonContent)
        self.contents.append(self.ashContent)
        self.contents.append(self.airmetContent)
        self.contents.append(self.cancelContent)
        self.contents.append(self.customContent)
        self.currentContent = self.contents[0]

        for c in self.contents:
            self.contentLayout.addWidget(c)

        self.contentLayout.addWidget(self.graphic)
        self.changeContent()

        self.addBottomBox(self.mainLayout)

    def updateGraphicCanvas(self):
        if self.mode == 'custom':
            return

        if self.mode == 'cancel':
            sigmets = self.context.current.filterSigmets(SigmetFilter(designator=self.type))
        else:
            sigmets = self.context.current.filterSigmets(SigmetFilter(category=self.category()))

        self.graphic.setCachedSigmet(sigmets)

    def updateLayer(self):
        self.graphic.updateLayer()

    def updateState(self):
        self.currentContent.initState()

    def updateCustomText(self):
        self.customContent.updateText()

    def heading(self):
        area = self.conf.bulletinNumber or ''
        return composeHeading(self.type, area, self.conf.airport, datetime.datetime.utcnow())

    def message(self):
        text = self.currentContent.message()

        if self.hasGraphicWindow():
            locations = self.graphic.location()
            text = text.format(**locations)

        text = text if text.endswith('=') else text + '='
        return text

    def category(self):
        return 'AIRMET' if self.type == 'WA' else 'SIGMET'

    def hasGraphicWindow(self):
        return self.currentContent not in [self.customContent, self.cancelContent]

    def setType(self, type, mode):
        self.type = type
        self.mode = mode
        self.currentContent.setSpan(validDuration(self.type))
        self.graphic.setButton(self.type, mode)
        self.updateGraphicCanvas()

    def setOverlapMode(self, mode):
        if self.currentContent not in [self.customContent, self.cancelContent]:
            self.currentContent.setOverlapMode(mode)

    def setLocationMode(self, mode):
        self.currentContent.setLocationMode(mode)

    def changeContent(self):
        if self.template.isChecked():
            mode = 'template'
            if self.significantWeather.isChecked():
                self.currentContent = self.generalContent

            elif self.tropicalCyclone.isChecked():
                self.currentContent = self.typhoonContent

            elif self.volcanicAsh.isChecked():
                self.currentContent = self.ashContent

            elif self.airmansWeather.isChecked():
                self.currentContent = self.airmetContent

        elif self.cancel.isChecked():
            mode = 'cancel'
            self.currentContent = self.cancelContent
        else:
            mode = 'custom'
            self.currentContent = self.customContent

        if self.currentContent == self.customContent:
            self.graphic.hide()
        else:
            self.graphic.show()

        for c in self.contents:
            if c == self.currentContent:
                c.show()
            else:
                c.hide()

        if self.significantWeather.isChecked():
            tt = 'WS'

        if self.tropicalCyclone.isChecked():
            tt = 'WC'

        if self.volcanicAsh.isChecked():
            tt = 'WV'

        if self.airmansWeather.isChecked():
            tt = 'WA'
        
        self.setType(tt, mode)

    def clear(self):
        for c in self.contents:
            c.clear()

        self.graphic.clear()

    def onFirstShow(self):
        self.updateState()

    def onClose(self):
        self.context.notification.sigmet.clear()
        self.presenter.clear()
