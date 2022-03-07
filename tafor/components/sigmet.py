import datetime

from uuid import uuid4

from PyQt5.QtCore import QCoreApplication, QTimer, Qt
from PyQt5.QtWidgets import QVBoxLayout, QLayout, QRadioButton

from tafor import conf
from tafor.states import context
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

        self.tt = 'WS'
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

        self.mainLayout.addWidget(self.graphic)
        self.changeContent()
        self.location.clear()

        self.addBottomBox(self.layout)

    def bindSignal(self):
        self.significantWeather.clicked.connect(self.changeContent)
        self.tropicalCyclone.clicked.connect(self.changeContent)
        self.volcanicAsh.clicked.connect(self.changeContent)
        self.airmansWeather.clicked.connect(self.changeContent)
        self.template.clicked.connect(self.changeContent)
        self.custom.clicked.connect(self.changeContent)
        self.cancel.clicked.connect(self.changeContent)

        self.graphic.sketchChanged.connect(self.setLocationLabel)
        self.graphic.sketchChanged.connect(self.enbaleNextButton)
        # self.graphic.sketchChanged.connect(self.updateContentLine)

        self.typhoonContent.circleChanged.connect(lambda: self.graphic.updateTyphoonGraphic(self.typhoonContent.circle()))

        for c in self.contents:
            c.contentChanged.connect(self.enbaleNextButton)

        self.nextButton.clicked.connect(self.beforeNext)

        # change content self.enbaleNextButton()
        self.sender.sendSignal.connect(self.initState)

    # def updateContentLine(self):
    #     if self.currentContent == self.typhoonContent:
    #         drawing = self.graphic.canvas.drawings['default']
    #         self.typhoonContent.updateLocation(drawing.geographicalCircle())

    def updateGraphicCanvas(self):
        isAirmet = True if self.tt == 'WA' else False

        if isAirmet:
            sigmets = [s for s in context.layer.sigmets() if s.tt == 'WA']
        else:
            sigmets = [s for s in context.layer.sigmets() if s.tt != 'WA']

        self.graphic.setCachedSigmet(sigmets)

    def updateLayer(self):
        self.graphic.updateLayer()

    def beforeNext(self):
        self.currentContent.validate()

        if self.hasAcceptableInput():
            self.previewMessage()

    def previewMessage(self):
        sign = self.wmoHeader()
        rpt = self.message()
        uuid = str(uuid4())
        message = {'sign': sign, 'rpt': rpt, 'uuid': uuid}
        self.previewSignal.emit(message)

    def enbaleNextButton(self):
        self.nextButton.setEnabled(self.hasAcceptableInput())

    def initState(self):
        # self.sigmet.initState()
        pass

    def loadSigmet(self):
        # self.sigmetCustom.setText()
        pass

    def wmoHeader(self):
        area = conf.value('Message/Area') or ''
        icao = conf.value('Message/ICAO')
        time = datetime.datetime.utcnow().strftime('%d%H%M')
        messages = [self.tt + area, icao, time]
        return ' '.join(filter(None, messages))

    def message(self):
        text = self.currentContent.message()

        if self.hasGraphicWindow():
            locations = self.graphic.location()
            text = text.format(**locations)

        text = text if text.endswith('=') else text + '='
        return text

    def sign(self):
        return 'AIRMET' if self.tt == 'WA' else 'SIGMET'

    def hasGraphicWindow(self):
        return self.currentContent not in [self.customContent, self.cancelContent]

    def hasAcceptableInput(self):
        items = [self.currentContent.hasAcceptableInput()]
        if self.hasGraphicWindow():
            items.append(self.graphic.hasAcceptableGraphic)

        return all(items)

    def setTypeButtonText(self):
        for i, btn in enumerate(self.typeGroup.findChildren(QRadioButton)):
            text = self.typeButtonTexts[i]
            if not btn.isChecked() and len(text) > 8:
                text = text[:8]

            btn.setText(text)

    def setType(self, tt):
        typeChanged = False if self.tt == tt else True
        self.tt = tt
        durations = {
            'WS': 4,
            'WC': 6,
            'WV': 6,
            'WA': 4,
        }
        self.currentContent.setSpan(durations[tt])
        self.setTypeButtonText()

        if typeChanged:
            self.graphic.setModeButton(tt)

        # self.changeSignal.emit()

    def setLocationLabel(self, messages):
        titles = ['DEFAULT', 'FORECAST']
        words = []
        for i, text in enumerate(messages):
            label = '<span style="color: grey">{}</span>'.format(titles[i])
            if text:
                text = label + '  ' + text
                words.append(text)

        html = '<br><br>'.join(words)
        self.location.setText(html)

    def changeContent(self):
        if self.template.isChecked():
            if self.significantWeather.isChecked():
                self.currentContent = self.generalContent

            elif self.tropicalCyclone.isChecked():
                self.currentContent = self.typhoonContent

            elif self.volcanicAsh.isChecked():
                self.currentContent = self.ashContent

            elif self.airmansWeather.isChecked():
                self.currentContent = self.airmetContent

        elif self.cancel.isChecked():
            self.currentContent = self.cancelContent
            # self.currentContent.clear()
        else:
            self.currentContent = self.customContent
            # self.currentContent.clear()

        if self.currentContent == self.customContent:
            self.graphic.hide()
        else:
            self.graphic.show()

        if self.currentContent in [self.currentContent, self.cancelContent]:
            self.location.show()
        else:
            self.location.hide()

        for c in self.contents:
            if c == self.currentContent:
                c.show()
            else:
                c.hide()

        if self.significantWeather.isChecked():
            self.setType('WS')

        if self.tropicalCyclone.isChecked():
            self.setType('WC')

        if self.volcanicAsh.isChecked():
            self.setType('WV')

        if self.airmansWeather.isChecked():
            self.setType('WA')

    def showNotificationMessage(self, text):
        self.parent.showNotificationMessage(text)

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
        # self.sigmetCustom.setText()
        self.clear()

    def showEvent(self, event):
        # 检查必要配置是否完成
        if isConfigured('SIGMET'):
            if not self.isStaged:
                self.initState()
        else:
            QTimer.singleShot(0, self.showConfigError)
