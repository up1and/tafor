import datetime

from PyQt5.QtCore import QCoreApplication, QTimer, Qt
from PyQt5.QtWidgets import QRadioButton

from tafor import conf
from tafor.states import context
from tafor.models import Sigmet
from tafor.components.setting import isConfigured
from tafor.components.widgets import SigmetGeneral, SigmetTyphoon, SigmetAsh, AirmetGeneral, SigmetCancel, SigmetCustom
from tafor.components.widgets.graphic import GraphicsWindow
from tafor.components.widgets.editor import BaseEditor
from tafor.components.ui import Ui_sigmet


class SigmetEditor(BaseEditor, Ui_sigmet.Ui_Editor):

    def __init__(self, parent=None, sender=None):
        super(SigmetEditor, self).__init__(parent, sender)
        self.setupUi(self)
        self.parent = parent

        self.type = 'WS'
        self.category = 'template'
        self.typeButtonTexts = [btn.text() for btn in self.typeGroup.findChildren(QRadioButton)]

        self.initUI()
        self.bindSignal()

        self.setWindowTitle(QCoreApplication.translate('Editor', 'Encoding Significant Meteorological Information'))
        self.setStyleSheet('QLineEdit {width: 50px;} QComboBox {width: 50px;}')

    def initUI(self):
        self.graphic = GraphicsWindow(self)
        self.generalContent = SigmetGeneral(self)
        self.typhoonContent = SigmetTyphoon(self)
        self.ashContent = SigmetAsh(self)
        self.airmetContent = AirmetGeneral(self)
        self.cancelContent = SigmetCancel(self)
        self.customContent = SigmetCustom(self)

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

    def bindSignal(self):
        self.significantWeather.clicked.connect(self.changeContent)
        self.tropicalCyclone.clicked.connect(self.changeContent)
        self.volcanicAsh.clicked.connect(self.changeContent)
        self.airmansWeather.clicked.connect(self.changeContent)
        self.template.clicked.connect(self.changeContent)
        self.custom.clicked.connect(self.changeContent)
        self.cancel.clicked.connect(self.changeContent)

        self.graphic.sketchChanged.connect(self.enbaleNextButton)
        self.graphic.modeChanged.connect(self.setForecastMode)
        self.graphic.modeChanged.connect(self.enbaleNextButton)

        self.graphic.circleChanged.connect(self.typhoonContent.setTyphoonLocation)
        self.typhoonContent.circleChanged.connect(self.graphic.setTyphoonGraphic)

        for c in self.contents:
            c.contentChanged.connect(self.enbaleNextButton)

        self.nextButton.clicked.connect(self.beforeNext)

        # change content self.enbaleNextButton()
        self.sender.succeeded.connect(self.updateState)

    def updateGraphicCanvas(self):
        if self.category == 'custom':
            return

        if self.category == 'cancel':
            sigmets = context.message.sigmets(type=self.type)
        else:
            airsigmet = self.reportType()
            sigmets = context.message.sigmets(airsigmet=airsigmet)

        self.graphic.setCachedSigmet(sigmets)

    def updateLayer(self):
        self.graphic.updateLayer()

    def beforeNext(self):
        self.currentContent.validate()

        if self.hasAcceptableInput():
            self.previewMessage()

    def previewMessage(self):
        message = Sigmet(type=self.type, heading=self.heading(), text=self.message())
        self.finished.emit(message)

    def enbaleNextButton(self):
        self.nextButton.setEnabled(self.hasAcceptableInput())

    def updateState(self):
        self.currentContent.initState()

    def loadNotification(self):
        self.customContent.loadNotification()

    def heading(self):
        area = conf.value('Message/Area') or ''
        icao = conf.value('Message/ICAO')
        time = datetime.datetime.utcnow().strftime('%d%H%M')
        messages = [self.type + area, icao, time]
        return ' '.join(filter(None, messages))

    def message(self):
        text = self.currentContent.message()

        if self.hasGraphicWindow():
            locations = self.graphic.location()
            text = text.format(**locations)

        text = text if text.endswith('=') else text + '='
        return text

    def reportType(self):
        return 'AIRMET' if self.type == 'WA' else 'SIGMET'

    def hasGraphicWindow(self):
        return self.currentContent not in [self.customContent, self.cancelContent]

    def hasAcceptableInput(self):
        items = [self.currentContent.hasAcceptableInput()]
        if self.hasGraphicWindow():
            items.append(self.graphic.hasAcceptableGraphic())

        return all(items)

    def hideTypeGroupOverflow(self):
        """
        hide extra text when radio button has more than 8 characters
        """
        for i, btn in enumerate(self.typeGroup.findChildren(QRadioButton)):
            text = self.typeButtonTexts[i]
            if not btn.isChecked() and len(text) > 8:
                text = text[:8]

            btn.setText(text)

    def setType(self, type, category):
        self.type = type
        self.category = category
        durations = {
            'WS': 4,
            'WC': 6,
            'WV': 6,
            'WA': 4,
        }
        self.currentContent.setSpan(durations[self.type])
        self.hideTypeGroupOverflow()

        self.graphic.setButton(self.type, category)
        self.updateGraphicCanvas()

    def setForecastMode(self, mode):
        if self.currentContent in [self.generalContent, self.ashContent]:
            self.currentContent.setForecastMode(mode)

    def changeContent(self):
        if self.template.isChecked():
            category = 'template'
            if self.significantWeather.isChecked():
                self.currentContent = self.generalContent

            elif self.tropicalCyclone.isChecked():
                self.currentContent = self.typhoonContent

            elif self.volcanicAsh.isChecked():
                self.currentContent = self.ashContent

            elif self.airmansWeather.isChecked():
                self.currentContent = self.airmetContent

        elif self.cancel.isChecked():
            category = 'cancel'
            self.currentContent = self.cancelContent
        else:
            category = 'custom'
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
        
        self.setType(tt, category)

    def showEvent(self, event):
        self.setTypeButtonText()

    def clear(self):
        for c in self.contents:
            c.clear()

        self.graphic.clear()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F5:
            context.layer.refresh()

    def closeEvent(self, event):
        super(SigmetEditor, self).closeEvent(event)
        context.notification.sigmet.clear()
        self.clear()

    def showEvent(self, event):
        # 检查必要配置是否完成
        if isConfigured('SIGMET'):
            if not self.isStaged:
                self.updateState()
        else:
            QTimer.singleShot(0, self.showConfigError)
