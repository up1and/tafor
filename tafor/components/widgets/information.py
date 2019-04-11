import datetime

from itertools import cycle

from PyQt5.QtGui import QIcon, QRegExpValidator, QIntValidator, QTextCharFormat, QFont
from PyQt5.QtCore import Qt, QRegExp, QCoreApplication, pyqtSignal
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLineEdit

from tafor import conf
from tafor.states import context
from tafor.utils import _purePattern, Pattern, SigmetGrammar
from tafor.utils.convert import parseTime, ceilTime, roundTime, calcPosition
from tafor.utils.service import currentSigmet
from tafor.models import db, Sigmet
from tafor.components.widgets.forecast import SegmentMixin
from tafor.components.widgets.area import AreaBoard
from tafor.components.ui import (Ui_sigmet_type, Ui_sigmet_general, Ui_sigmet_head,
    Ui_sigmet_typhoon, Ui_sigmet_cancel, Ui_sigmet_custom, Ui_sigmet_area, main_rc)


class SigmetTypeSegment(QWidget, Ui_sigmet_type.Ui_Editor):

    def __init__(self):
        super(SigmetTypeSegment, self).__init__()
        self.setupUi(self)
        self.tt = 'WS'

    def setType(self, tt):
        self.tt = tt

    def message(self):
        area = conf.value('Message/Area') or ''
        icao = conf.value('Message/ICAO')
        time = datetime.datetime.utcnow().strftime('%d%H%M')
        messages = [self.tt + area, icao, time]
        return ' '.join(filter(None, messages))

    def sign(self):
        return 'AIRMET' if self.tt == 'WA' else 'SIGMET'


class BaseSigmetHead(QWidget, SegmentMixin, Ui_sigmet_head.Ui_Editor):
    completeSignal = pyqtSignal(bool)

    def __init__(self, parent=None):
        super(BaseSigmetHead, self).__init__()
        self.span = 4
        self.durations = None
        self.complete = True
        self.rules = Pattern()
        self.parent = parent

        self.setupUi(self)
        self.initState()
        self.setValidator()
        self.bindSignal()

    def initState(self):
        self.setPeriodTime()
        self.setSquence()
        self.setPrediction(self.forecast.currentText())
        self.updateDurations()

    def bindSignal(self):
        self.forecast.currentTextChanged.connect(self.setPrediction)
        self.beginningTime.textChanged.connect(self.updateDurations)
        self.endingTime.textChanged.connect(self.updateDurations)
        self.beginningTime.editingFinished.connect(self.validateValidTime)
        self.endingTime.editingFinished.connect(self.validateValidTime)

        self.name.textEdited.connect(lambda: self.upperText(self.name))

        self.beginningTime.textEdited.connect(lambda: self.coloredText(self.beginningTime))
        self.endingTime.textEdited.connect(lambda: self.coloredText(self.endingTime))
        self.obsTime.textChanged.connect(lambda: self.coloredText(self.obsTime))

        self.defaultSignal()

    def setPrediction(self, text):
        if text == 'OBS':
            self.obsTime.setEnabled(True)
            self.obsTimeLabel.setEnabled(True)
            self.obsTime.setText(self.beginningTime.text()[2:])
        else:
            self.obsTime.setEnabled(False)
            self.obsTimeLabel.setEnabled(False)
            self.obsTime.clear()

    def updateDurations(self):
        if self.beginningTime.hasAcceptableInput() and self.endingTime.hasAcceptableInput():
            beginText = self.beginningTime.text()
            endText = self.endingTime.text()
            start = parseTime(beginText)
            end = parseTime(endText)
            self.durations = (start, end)
        else:
            self.durations = None

    def validPeriodTime(self):
        self.time = datetime.datetime.utcnow()
        if self.parent.type.tt == 'WC':
            start = roundTime(self.time)
        else:
            start = ceilTime(self.time, amount=10)
        end = start + datetime.timedelta(hours=self.span)
        return start, end

    def validateValidTime(self):
        if self.durations is None:
            return

        start, end = self.durations
        time = datetime.datetime.utcnow()

        if start - time > datetime.timedelta(hours=24):
            self.beginningTime.clear()
            self.parent.showNotificationMessage(QCoreApplication.translate('Editor', 'Start time cannot be less than the current time'))
            return

        if end <= start:
            self.endingTime.clear()
            self.parent.showNotificationMessage(QCoreApplication.translate('Editor', 'Ending time must be greater than the beginning time'))
            return

        if end - start > datetime.timedelta(hours=self.span):
            self.endingTime.clear()
            self.parent.showNotificationMessage(QCoreApplication.translate('Editor', 'Valid period more than {} hours').format(self.span))
            return

    def validateObsTime(self):
        # 未启用
        if self.durations is None:
            return

        start, _ = self.durations
        obs = parseTime(self.obsTime.text())
        if obs > start:
            self.obsTime.clear()
            self.parent.showNotificationMessage(QCoreApplication.translate('Editor', 'Observation time should before the beginning time'))

    def validate(self):
        self.validateValidTime()

    def setSpan(self, span):
        self.span = span

    def setPeriodTime(self):
        beginningTime, endingTime = self.validPeriodTime()
        self.beginningTime.setText(beginningTime.strftime('%d%H%M'))
        self.endingTime.setText(endingTime.strftime('%d%H%M'))

    def setValidator(self):
        date = QRegExpValidator(QRegExp(self.rules.date))
        self.beginningTime.setValidator(date)
        self.endingTime.setValidator(date)

        time = QRegExpValidator(QRegExp(self.rules.time))
        self.obsTime.setValidator(time)

        sequence = QRegExpValidator(QRegExp(self.rules.sequence))
        self.sequence.setValidator(sequence)

    def setSquence(self):
        time = datetime.datetime.utcnow()
        begin = datetime.datetime(time.year, time.month, time.day)
        query = db.query(Sigmet).filter(Sigmet.sent > begin)
        if self.parent.type.tt == 'WA':
            query = query.filter(Sigmet.tt == 'WA')
        else:
            query = query.filter(Sigmet.tt != 'WA')
        count = query.count() + 1
        self.sequence.setText(str(count))

    def setPhenomenaDescription(self):
        raise NotImplementedError

    def setPhenomena(self, text):
        raise NotImplementedError

    def checkComplete(self):
        raise NotImplementedError

    def message(self):
        fir = conf.value('Message/FIR')
        phenomena = self.weatherPhenomena()

        text = ' '.join([fir, phenomena])
        return text

    def head(self):
        area = conf.value('Message/FIR').split()[0]
        sign = self.parent.type.sign()
        sequence = self.sequence.text()
        beginningTime = self.beginningTime.text()
        endingTime = self.endingTime.text()
        icao = conf.value('Message/ICAO')

        text = '{} {} {} VALID {}/{} {}-'.format(area, sign, sequence, beginningTime, endingTime, icao)
        return text

    def prediction(self):
        if self.forecast.currentText() == 'OBS':
            text = 'OBS AT {}Z'.format(self.obsTime.text()) if self.obsTime.text() else ''
        else:
            text = self.forecast.currentText()

        return text

    def weatherPhenomena(self):
        items = [self.description.currentText(), self.phenomena.currentText()]
        text = ' '.join(items) if all(items) else ''
        return text

    def clear(self):
        self.durations = None


class BaseSigmetContent(QWidget, SegmentMixin):
    completeSignal = pyqtSignal(bool)

    def __init__(self, parent):
        super(BaseSigmetContent, self).__init__()
        self.complete = False
        self.rules = Pattern()
        self.parent = parent


class BaseSegment(QWidget):
    changeSignal = pyqtSignal()

    def __init__(self, typeSegment, parent=None):
        super(BaseSegment, self).__init__()
        self.type = typeSegment
        self.parent = parent

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.head)
        layout.addWidget(self.content)
        self.setLayout(layout)

    def head(self):
        area = conf.value('Message/Area') or ''
        icao = conf.value('Message/ICAO')
        time = self.time.strftime('%d%H%M')
        tt = self.type.tt

        messages = [tt + area, icao, time]
        return ' '.join(filter(None, messages))

    def message(self):
        content = ' '.join([self.head.message(), self.content.message()])
        text = '\n'.join([self.head.head(), content])
        text = text if text.endswith('=') else text + '='
        return text

    def setType(self, tt):
        durations = {
            'WS': 4,
            'WC': 6,
            'WV': 6,
            'WA': 4,
        }
        self.head.setSpan(durations[tt])
        self.type.setType(tt)

        self.changeSignal.emit()

    def showNotificationMessage(text):
        self.parent.showNotificationMessage(text)

    def clear(self):
        self.head.clear()
        self.content.clear()


class SigmetArea(QWidget, SegmentMixin, Ui_sigmet_area.Ui_Editor):
    areaModeChanged = pyqtSignal()

    def __init__(self, tt='WS', parent=None):
        super(SigmetArea, self).__init__()
        self.setupUi(self)
        self.tt = tt
        self.parent = parent
        self.rules = Pattern()
        self.canvasWidget = AreaBoard(self)
        self.areaLayout.addWidget(self.canvasWidget)
        self.areaGroup.setLayout(self.areaLayout)
        self.fcstButton.setIcon(QIcon(':/f.png'))

        self.initState()
        self.bindSignal()
        self.setValidator()
        self.setArea()
        self.setCanvasMode()

    def initState(self):
        if self.tt == 'WC':
            self.icons = [{'icon': ':/circle.png', 'mode': 'circle'}]
            self.entire.hide()
        else:
            self.icons = [
                {'icon': ':/polygon.png', 'mode': 'polygon'},
                {'icon': ':/line.png', 'mode': 'line'},
                {'icon': ':/rectangular.png', 'mode': 'rectangular'},
                {'icon': ':/corridor.png', 'mode': 'corridor'}
            ]

    def bindSignal(self):
        self.manual.clicked.connect(self.setArea)
        self.canvas.clicked.connect(self.setArea)
        self.entire.clicked.connect(self.setArea)

        self.fcstButton.clicked.connect(self.setAreaMode)
        self.modeButton.clicked.connect(self.switchCanvasMode)

        self.textArea.textEdited.connect(lambda: self.upperText(self.textArea))
        self.textArea.textEdited.connect(lambda: self.coloredText(self.textArea))

        self.canvasWidget.canvas.stateChanged.connect(self.setAreaMode)
        self.canvasWidget.canvas.stateChanged.connect(self.checkComplete)

        self.defaultSignal()

    def checkComplete(self):
        self.parent.checkComplete()

    def setValidator(self):
        grammar = SigmetGrammar()
        patterns = [grammar.lines, grammar.rectangulars, grammar.polygon, grammar.corridor]
        pattern = r'{}'.format('|'.join([_purePattern(p) for p in patterns]))
        area = QRegExpValidator(QRegExp(pattern, Qt.CaseInsensitive))
        self.textArea.setValidator(area)

    def setArea(self):
        if self.manual.isChecked():
            self.textAreaWidget.setVisible(True)
            self.canvasWidget.setVisible(False)
            self.fcstButton.setVisible(False)
            self.modeButton.setVisible(False)
            self.setTextAreaPlaceholder()

        if self.canvas.isChecked():
            self.textAreaWidget.setVisible(False)
            self.canvasWidget.setVisible(True)
            self.fcstButton.setVisible(True)
            self.modeButton.setVisible(True)

        if self.entire.isChecked():
            self.textAreaWidget.setVisible(False)
            self.canvasWidget.setVisible(False)
            self.fcstButton.setVisible(False)
            self.modeButton.setVisible(False)

    def setAreaMode(self):
        enbale = self.canvasWidget.canEnbaleFcstMode()
        self.fcstButton.setEnabled(enbale)

        if self.fcstButton.isChecked():
            self.canvasWidget.setAreaType('forecast')
            self.modeButton.setEnabled(False)
        else:
            self.canvasWidget.setAreaType('default')
            self.modeButton.setEnabled(True)

        self.areaModeChanged.emit()

    def setTextAreaPlaceholder(self):
        import random
        areas = [
            'WI N1950 E10917 - N1918 E11000 - N1814 E10903 - N1915 E10809 - N1950 E10917',
            'APRX 25KM WID LINE BTN N1941 E10842 - N1817 E10847 - N1743 E11002',
            'N OF N1830 AND W OF E10917',
            'NW OF LINE N2030 E11017 - N1751 E10813'
        ]
        self.textArea.setPlaceholderText(random.choice(areas))

    def setCanvasMode(self):
        self.canvasMode = cycle(self.icons)
        self.switchCanvasMode()

    def switchCanvasMode(self):
        canvasMode = next(self.canvasMode)
        self.canvasWidget.setMode(canvasMode['mode'])
        self.modeButton.setIcon(QIcon(canvasMode['icon']))

        if canvasMode['mode'] == 'circle':
            self.fcstButton.setChecked(False)
            self.fcstButton.hide()

    def text(self):
        text = ''

        if self.manual.isChecked():
            if self.textArea.hasAcceptableInput() and not self.textArea.text().endswith('AND '):
                text = self.textArea.text()
            else:
                text = ''

        if self.canvas.isChecked():
            text = self.canvasWidget.texts()

        if self.entire.isChecked():
            suffix = conf.value('Message/FIR').split()[-1]
            text = 'ENTIRE {}'.format(suffix)

        return text

    def showEvent(self, event):
        if conf.value('Monitor/FirApiURL') or self.tt == 'WC':
            self.manual.hide()
            self.textAreaWidget.hide()

    def clear(self):
        self.canvasWidget.clear()
        self.modeButton.setEnabled(True)
        self.fcstButton.setChecked(False)
        self.canvasWidget.setAreaType('default')


class SigmetGeneralHead(BaseSigmetHead):

    def __init__(self, parent=None):
        super(SigmetGeneralHead, self).__init__(parent)
        self.hideName()
        self.setPhenomenaDescription()
        self.setPhenomena()
        self.setFcstOrObs()

    def setPhenomenaDescription(self):
        descriptions = ['OBSC', 'EMBD', 'FRQ', 'SQL', 'SEV', 'HVY', 'RDOACT']
        self.description.addItems(descriptions)
        self.description.setCurrentIndex(1)

    def setPhenomena(self, text='OBSC'):
        self.phenomena.clear()

        if text == 'SEV':
            phenomenas = ['TURB', 'ICE', 'ICE (FZRA)', 'MTW']
        elif text == 'HVY':
            phenomenas = ['DS', 'SS']
        elif text == 'RDOACT':
            phenomenas = ['CLD']
        else:
            phenomenas = ['TS', 'TSGR']

        self.phenomena.addItems(phenomenas)

    def setFcstOrObs(self):
        forecasts = ['FCST', 'OBS']
        self.forecast.addItems(forecasts)

    def hideName(self):
        self.name.setVisible(False)
        self.nameLabel.setVisible(False)

    def checkComplete(self):
        mustRequired = [
            self.beginningTime.hasAcceptableInput(),
            self.endingTime.hasAcceptableInput(),
            self.sequence.hasAcceptableInput(),
        ]
        if self.obsTime.isEnabled():
            mustRequired.append(self.obsTime.hasAcceptableInput())

        self.complete = all(mustRequired)
        self.completeSignal.emit(self.complete)


class SigmetGeneralContent(BaseSigmetContent, Ui_sigmet_general.Ui_Editor):

    def __init__(self, parent):
        super(SigmetGeneralContent, self).__init__(parent)
        self.setupUi(self)
        self.area = SigmetArea(tt=self.parent.type.tt, parent=self)
        self.verticalLayout.addWidget(self.area)

        self.bindSignal()
        self.setValidator()
        self.setLevel('TS')
        self.hideForecast()

    def bindSignal(self):
        self.level.currentTextChanged.connect(self.setFightLevel)
        self.movement.currentTextChanged.connect(self.setSpeed)
        self.base.editingFinished.connect(lambda :self.validateBaseTop(self.base))
        self.top.editingFinished.connect(lambda :self.validateBaseTop(self.top))

        self.base.textEdited.connect(lambda: self.coloredText(self.base))
        self.top.textEdited.connect(lambda: self.coloredText(self.top))

        self.defaultSignal()

    def setValidator(self):
        fightLevel = QRegExpValidator(QRegExp(self.rules.fightLevel))
        self.base.setValidator(fightLevel)
        self.top.setValidator(fightLevel)

        self.speed.setValidator(QIntValidator(1, 99, self.speed))

        time = QRegExpValidator(QRegExp(self.rules.time))
        self.forecastTime.setValidator(time)

    def setFightLevel(self, text):
        if text in ['TOP', 'ABV']:
            self.base.setEnabled(False)
            self.top.setEnabled(True)
            self.baseLabel.setEnabled(False)
            self.topLabel.setEnabled(True)
        elif text in ['BLW', 'SFC']:
            self.base.setEnabled(True)
            self.top.setEnabled(False)
            self.baseLabel.setEnabled(True)
            self.topLabel.setEnabled(False)
        else:
            self.base.setEnabled(True)
            self.top.setEnabled(True)
            self.baseLabel.setEnabled(True)
            self.topLabel.setEnabled(True)

    def setSpeed(self, text):
        if text == 'STNR':
            self.speed.setEnabled(False)
            self.speedLabel.setEnabled(False)
        else:
            self.speed.setEnabled(True)
            self.speedLabel.setEnabled(True)

    def setLevel(self, text):
        if text in ['CB', 'TCU', 'TS', 'TSGR']:
            self.level.setCurrentIndex(self.level.findText('TOP'))
        else:
            self.level.setCurrentIndex(-1)

    def setForecastTime(self):
        if self.parent.head.durations is None or not self.parent.head.endingTime.text():
            return

        text = self.parent.head.endingTime.text()[2:]
        self.forecastTime.setText(text)

    def hideForecast(self):
        pass

    def validateBaseTop(self, line):
        if not (self.base.isEnabled() and self.top.isEnabled()):
            return

        base = self.base.text()
        top = self.top.text()
        if base and top:
            if int(top) <= int(base):
                line.clear()
                self.parent.showNotificationMessage(QCoreApplication.translate('Editor', 'The top flight level needs to be greater than the base flight level'))

    def isFcstAreaMode(self):
        return hasattr(self, 'area') and self.area.fcstButton.isChecked()

    def checkComplete(self):
        mustRequired = []

        if self.base.isEnabled():
            mustRequired.append(self.base.hasAcceptableInput())

        if self.top.isEnabled():
            mustRequired.append(self.top.hasAcceptableInput())

        if hasattr(self, 'area'):
            mustRequired.append(self.area.text())

        if self.isFcstAreaMode():
            mustRequired.append(self.forecastTime.hasAcceptableInput())
        elif self.speed.isEnabled():
            mustRequired.append(self.speed.hasAcceptableInput())

        self.complete = all(mustRequired)
        self.completeSignal.emit(self.complete)

    def message(self):
        areas = self.area.text()
        prediction = self.parent.head.prediction()
        fightLevel = self.fightLevel()
        moveState = self.moveState()
        intensityChange = self.intensityChange.currentText()
        if self.isFcstAreaMode():
            area, forecastArea = areas
            fcstTime = self.fcstTime()
            items = [prediction, area, fightLevel, moveState, intensityChange, fcstTime, forecastArea]
        else:
            area = areas[0] if isinstance(areas, list) else areas
            items = [prediction, area, fightLevel, moveState, intensityChange]

        return ' '.join(filter(None, items))

    def moveState(self):
        if not self.speed.hasAcceptableInput():
            return

        movement = self.movement.currentText()

        if movement == 'STNR':
            text = 'STNR'
        else:
            text = 'MOV {movement} {speed}KMH'.format(
                    movement=movement,
                    speed=int(self.speed.text())
                )

        return text

    def fightLevel(self):
        level = self.level.currentText()
        base = self.base.text()
        top = self.top.text()

        if not level:
            text = 'FL{}/{}'.format(base, top) if all([top, base]) else ''

        if level in ['TOP', 'ABV']:
            text = '{} FL{}'.format(level, top) if top else ''

        if level == 'BLW':
            text = 'BLW FL{}'.format(base) if base else ''

        if level == 'SFC':
            text = 'SFC/FL{}'.format(base) if base else ''

        return text

    def fcstTime(self):
        text = 'FCST AT {}Z'.format(self.forecastTime.text())
        return text

    def clear(self):
        super(SigmetGeneralContent, self).clear()
        self.area.clear()


class SigmetTyphoonHead(BaseSigmetHead):

    def __init__(self, parent=None):
        super(SigmetTyphoonHead, self).__init__(parent)
        self.hideDescription()
        self.setPhenomena()
        self.setFcstOrObs()
        self.span = 6
        self.nameLabel.setText(QCoreApplication.translate('Editor', 'Typhoon Name'))

    def setPhenomena(self, text='TC'):
        self.phenomena.addItems(['TC'])

    def setFcstOrObs(self):
        forecasts = ['OBS']
        self.forecast.addItems(forecasts)

    def hideDescription(self):
        self.description.setVisible(False)
        self.descriptionLabel.setVisible(False)

    def weatherPhenomena(self):
        items = [self.phenomena.currentText(), self.name.text()]
        text = ' '.join(items) if all(items) else ''
        return text

    def checkComplete(self):
        mustRequired = [
            self.beginningTime.hasAcceptableInput(),
            self.endingTime.hasAcceptableInput(),
            self.sequence.hasAcceptableInput(),
            self.name.text(),
            self.obsTime.hasAcceptableInput()
        ]

        self.complete = all(mustRequired)
        self.completeSignal.emit(self.complete)

    def clear(self):
        super(SigmetTyphoonHead, self).clear()
        self.name.clear()


class SigmetTyphoonContent(BaseSigmetContent, Ui_sigmet_typhoon.Ui_Editor):

    def __init__(self, parent):
        super(SigmetTyphoonContent, self).__init__(parent)
        self.setupUi(self)
        self.area = SigmetArea(tt='WC', parent=self)
        self.verticalLayout.addWidget(self.area)
        self.bindSignal()
        self.setValidator()

    def bindSignal(self):
        self.movement.currentTextChanged.connect(self.setSpeed)

        self.currentLatitude.editingFinished.connect(self.setCircleOnCanvas)
        self.currentLongitude.editingFinished.connect(self.setCircleOnCanvas)
        self.range.editingFinished.connect(self.setCircleOnCanvas)
        self.area.canvasWidget.canvas.pointsChanged.connect(self.setCircleOnContent)
        self.area.canvasWidget.canvas.stateChanged.connect(self.setCircleOnContent)

        self.currentLatitude.textChanged.connect(self.setForecastPosition)
        self.currentLongitude.textChanged.connect(self.setForecastPosition)
        self.speed.textEdited.connect(self.setForecastPosition)
        self.movement.currentTextChanged.connect(self.setForecastPosition)

        self.currentLatitude.textEdited.connect(lambda: self.upperText(self.currentLatitude))
        self.currentLongitude.textEdited.connect(lambda: self.upperText(self.currentLongitude))
        self.forecastLatitude.textEdited.connect(lambda: self.upperText(self.forecastLatitude))
        self.forecastLongitude.textEdited.connect(lambda: self.upperText(self.forecastLongitude))

        self.currentLatitude.textEdited.connect(lambda: self.coloredText(self.currentLatitude))
        self.currentLongitude.textEdited.connect(lambda: self.coloredText(self.currentLongitude))
        self.height.textEdited.connect(lambda: self.coloredText(self.height))
        self.forecastTime.textEdited.connect(lambda: self.coloredText(self.forecastTime))
        self.forecastLatitude.textEdited.connect(lambda: self.coloredText(self.forecastLatitude))
        self.forecastLongitude.textEdited.connect(lambda: self.coloredText(self.forecastLongitude))

        self.defaultSignal()

    def setValidator(self):
        latitude = QRegExpValidator(QRegExp(self.rules.latitude, Qt.CaseInsensitive))
        self.currentLatitude.setValidator(latitude)
        self.forecastLatitude.setValidator(latitude)

        longitude = QRegExpValidator(QRegExp(self.rules.longitude, Qt.CaseInsensitive))
        self.currentLongitude.setValidator(longitude)
        self.forecastLongitude.setValidator(longitude)

        fightLevel = QRegExpValidator(QRegExp(self.rules.fightLevel))
        self.height.setValidator(fightLevel)

        time = QRegExpValidator(QRegExp(self.rules.time))
        self.forecastTime.setValidator(time)

        self.speed.setValidator(QIntValidator(1, 99, self.speed))
        self.range.setValidator(QIntValidator(1, 999, self.range))

    def setCircleOnCanvas(self):
        if not context.fir.drawable:
            return

        if self.currentLatitude.hasAcceptableInput() and self.currentLongitude.hasAcceptableInput():
            lon = self.currentLongitude.text()
            lat = self.currentLatitude.text()
            self.area.canvasWidget.setCircleCenter([lon, lat])

        if self.range.hasAcceptableInput():
            radius = self.range.text()
            self.area.canvasWidget.setCircleRadius(radius)

    def setCircleOnContent(self):
        if not context.fir.drawable:
            return

        canvas = self.area.canvasWidget.canvas
        points = context.fir.pixelToDegree(canvas.points)
        if points:
            lon, lat = points[0]
            self.currentLongitude.setText(lon)
            self.currentLatitude.setText(lat)
        else:
            self.currentLongitude.clear()
            self.currentLatitude.clear()

        radius = round(context.fir.pixelToDistance(canvas.radius) / 10) * 10
        if radius:
            self.range.setText(str(radius))
        else:
            self.range.clear()

    def setSpeed(self, text):
        if text == 'STNR':
            self.speed.setEnabled(False)
            self.speedLabel.setEnabled(False)
        else:
            self.speed.setEnabled(True)
            self.speedLabel.setEnabled(True)

    def setForecastTime(self):
        if self.parent.head.durations is None or not self.parent.head.endingTime.text():
            return

        text = self.parent.head.endingTime.text()
        time = parseTime(text)
        time = time - datetime.timedelta(minutes=time.minute)
        fcstTime = time.strftime('%H%M')

        self.forecastTime.setText(fcstTime)

    def setForecastPosition(self):
        mustRequired = [
            self.currentLatitude.hasAcceptableInput(),
            self.currentLongitude.hasAcceptableInput(),
            self.speed.hasAcceptableInput(),
            self.forecastTime.hasAcceptableInput(),
        ]

        anyRequired = [
            self.parent.head.obsTime.hasAcceptableInput(),
            self.parent.head.beginningTime.hasAcceptableInput(),
        ]

        if not (all(mustRequired) and any(anyRequired)):
            return

        movement = self.movement.currentText()

        if movement == 'STNR':
            return

        direction = {
            'N': 0,
            'NNE': 22.5,
            'NE': 45,
            'ENE': 67.5,
            'E': 90,
            'ESE': 112.5,
            'SE': 135,
            'SSE': 157.5,
            'S': 180,
            'SSW': 202.5,
            'SW': 225,
            'WSW': 247.5,
            'W': 270,
            'WNW': 292.5,
            'NW': 315,
            'NNW': 337.5
        }
        obsTime = self.parent.head.obsTime.text() if self.parent.head.obsTime.hasAcceptableInput() else ''
        beginningTime = self.parent.head.beginningTime.text()[2:] if self.parent.head.beginningTime.hasAcceptableInput() else ''
        fcstTime = self.forecastTime.text()

        time = self.moveTime(obsTime or beginningTime, fcstTime).seconds
        degree = direction[movement]
        speed = self.speed.text()
        latitude = self.currentLatitude.text()
        longitude = self.currentLongitude.text()

        forecastLatitude, forecastLongitude = calcPosition(latitude, longitude, speed, time, degree)
        self.forecastLatitude.setText(forecastLatitude)
        self.forecastLongitude.setText(forecastLongitude)

    def moveTime(self, start, end):
        return parseTime(end) - parseTime(start)

    def message(self):
        area = 'PSN {latitude} {Longitude} CB {prediction} WI {range}KM OF CENTRE TOP FL{height}'.format(
                latitude=self.currentLatitude.text(),
                Longitude=self.currentLongitude.text(),
                prediction=self.parent.head.prediction(),
                height=self.height.text(),
                range=int(self.range.text())
            )
        intensityChange = self.intensityChange.currentText()
        forecast = 'FCST {forecastTime}Z TC CENTRE {forecastLatitude} {forecastLongitude}'.format(
                forecastTime=self.forecastTime.text(),
                forecastLatitude=self.forecastLatitude.text(),
                forecastLongitude=self.forecastLongitude.text()
            )
        text = ' '.join([area, intensityChange, forecast])
        return text

    def checkComplete(self):
        mustRequired = [
            self.currentLatitude.hasAcceptableInput(),
            self.currentLongitude.hasAcceptableInput(),
            self.height.hasAcceptableInput(),
            self.range.hasAcceptableInput(),
            self.forecastTime.hasAcceptableInput(),
            self.forecastLatitude.hasAcceptableInput(),
            self.forecastLongitude.hasAcceptableInput(),
        ]

        self.complete = all(mustRequired)
        self.completeSignal.emit(self.complete)

    def clear(self):
        super(SigmetTyphoonContent, self).clear()
        self.area.clear()


class SigmetSimpleHead(BaseSigmetHead):

    def __init__(self, parent=None):
        super(SigmetSimpleHead, self).__init__(parent)
        self.hidePhenomena()

    def hidePhenomena(self):
        self.description.setVisible(False)
        self.descriptionLabel.setVisible(False)
        self.phenomena.setVisible(False)
        self.phenomenaLabel.setVisible(False)
        self.name.setVisible(False)
        self.nameLabel.setVisible(False)
        self.forecast.setVisible(False)
        self.forecastLabel.setVisible(False)
        self.obsTime.setVisible(False)
        self.obsTimeLabel.setVisible(False)

    def message(self):
        fir = conf.value('Message/FIR')
        return fir

    def checkComplete(self):
        mustRequired = [
            self.beginningTime.hasAcceptableInput(),
            self.endingTime.hasAcceptableInput(),
            self.sequence.hasAcceptableInput(),
        ]

        self.complete = all(mustRequired)
        self.completeSignal.emit(self.complete)


class SigmetCancelContent(BaseSigmetContent, Ui_sigmet_cancel.Ui_Editor):

    def __init__(self, parent):
        super(SigmetCancelContent, self).__init__(parent)
        self.setupUi(self)
        self.setValidator()
        self.bindSignal()

    def bindSignal(self):
        self.beginningTime.textEdited.connect(lambda: self.coloredText(self.beginningTime))
        self.endingTime.textEdited.connect(lambda: self.coloredText(self.endingTime))

        self.defaultSignal()

    def setValidator(self):
        date = QRegExpValidator(QRegExp(self.rules.date))
        self.beginningTime.setValidator(date)
        self.endingTime.setValidator(date)

        self.sequence.setValidator(QIntValidator(1, 99, self.sequence))

    def message(self):
        sign = self.parent.type.sign()
        text = 'CNL {} {} {}/{}'.format(sign, int(self.sequence.currentText()), self.beginningTime.text(), self.endingTime.text())
        return text

    def checkComplete(self):
        mustRequired = [
            self.beginningTime.hasAcceptableInput(),
            self.endingTime.hasAcceptableInput(),
            self.sequence.currentText() and int(self.sequence.currentText()),
        ]

        self.complete = all(mustRequired)
        self.completeSignal.emit(self.complete)


class SigmetCustomContent(BaseSigmetContent, Ui_sigmet_custom.Ui_Editor):

    def __init__(self, parent):
        super(SigmetCustomContent, self).__init__(parent)
        self.setupUi(self)
        self.bindSignal()
        self.setUpper()

    def message(self):
        text = self.text.toPlainText().upper()
        return text

    def setUpper(self):
        upper = QTextCharFormat()
        upper.setFontCapitalization(QFont.AllUppercase)
        self.text.setCurrentCharFormat(upper)

    def bindSignal(self):
        self.text.textChanged.connect(self.checkComplete)

    def checkComplete(self):
        self.complete = True if self.text.toPlainText() else False
        self.completeSignal.emit(self.complete)


class AirmetGeneralHead(SigmetGeneralHead):

    def setPhenomenaDescription(self):
        descriptions = ['ISOL', 'OCNL', 'FRQ', 'MOD']
        self.description.addItems(descriptions)

    def setPhenomena(self, text='ISOL'):
        self.phenomena.clear()

        if text == 'MOD':
            phenomenas = ['TURB', 'ICE', 'MTW']
        elif text == 'FRQ':
            phenomenas = ['CB', 'TCU']
        else:
            phenomenas = ['CB', 'TCU', 'TS', 'TSGR']

        self.phenomena.addItems(phenomenas)


class AirmetGeneralContent(SigmetGeneralContent):

    def hideForecast(self):
        self.forecastTime.hide()
        self.forecastTimeLabel.hide()
        self.area.fcstButton.hide()

    def setValidator(self):
        fightLevel = QRegExpValidator(QRegExp(self.rules.airmansFightLevel))
        self.base.setValidator(fightLevel)
        self.top.setValidator(fightLevel)

        self.speed.setValidator(QIntValidator(1, 99, self.speed))


class SigmetGeneralSegment(BaseSegment):

    def __init__(self, typeSegment, parent=None):
        super(SigmetGeneralSegment, self).__init__(typeSegment, parent)
        self.head = SigmetGeneralHead(self)
        self.content = SigmetGeneralContent(self)

        self.initUI()
        self.bindSignal()

    def bindSignal(self):
        self.changeSignal.connect(self.head.initState)

        self.head.description.currentTextChanged.connect(self.head.setPhenomena)
        self.head.phenomena.currentTextChanged.connect(self.content.setLevel)

        self.content.area.areaModeChanged.connect(self.setAreaMode)

    def setAreaMode(self):
        fcstAreaMode = self.content.isFcstAreaMode()
        if fcstAreaMode:
            self.head.forecast.setCurrentIndex(self.head.forecast.findText('OBS'))
            self.content.forecastTime.setEnabled(True)
            self.content.forecastTimeLabel.setEnabled(True)
            self.content.setForecastTime()
        else:
            self.content.forecastTime.setEnabled(False)
            self.content.forecastTimeLabel.setEnabled(False)
            self.content.forecastTime.clear()

    def clear(self):
        super(SigmetGeneralSegment, self).clear()
        self.head.description.setCurrentIndex(1)
        self.head.forecast.setCurrentIndex(0)
        self.content.level.setCurrentIndex(1)
        self.content.forecastTime.setEnabled(False)
        self.content.forecastTimeLabel.setEnabled(False)


class SigmetTyphoonSegment(BaseSegment):

    def __init__(self, typeSegment, parent=None):
        super(SigmetTyphoonSegment, self).__init__(typeSegment, parent)
        self.head = SigmetTyphoonHead(self)
        self.content = SigmetTyphoonContent(self)

        self.initUI()
        self.bindSignal()

    def bindSignal(self):
        self.changeSignal.connect(self.head.initState)
        self.changeSignal.connect(self.initState)
        self.head.endingTime.textChanged.connect(self.content.setForecastTime)
        self.head.beginningTime.textEdited.connect(self.content.setForecastPosition)
        self.head.obsTime.textEdited.connect(self.content.setForecastPosition)

    def initState(self):
        if self.content.forecastTime.text():
            return

        self.content.setForecastTime()


class AirmetGeneralSegment(BaseSegment):

    def __init__(self, typeSegment, parent=None):
        super(AirmetGeneralSegment, self).__init__(typeSegment, parent)
        self.head = AirmetGeneralHead(self)
        self.content = AirmetGeneralContent(self)

        self.initUI()
        self.bindSignal()

    def bindSignal(self):
        self.changeSignal.connect(self.head.initState)

        self.head.description.currentTextChanged.connect(self.head.setPhenomena)
        self.head.phenomena.currentTextChanged.connect(self.content.setLevel)


class SigmetCancelSegment(BaseSegment):

    def __init__(self, typeSegment, parent=None):
        super(SigmetCancelSegment, self).__init__(typeSegment, parent)
        self.head = SigmetSimpleHead(self)
        self.content = SigmetCancelContent(self)

        self.initUI()
        self.bindSignal()

    def bindSignal(self):
        self.changeSignal.connect(self.head.initState)
        self.changeSignal.connect(self.initState)

        self.content.endingTime.textChanged.connect(self.setEndingTime)
        self.content.sequence.currentTextChanged.connect(self.setValids)

    def setEndingTime(self):
        ending = self.content.endingTime.text()
        self.head.endingTime.setText(ending)

    def initState(self):
        self.prevs = {}
        sigmets = currentSigmet(tt=self.type.tt)

        for sig in sigmets:
            parser = sig.parser()
            self.prevs[parser.sequence()] = parser.valids()

        sequences = [s for s in self.prevs]
        self.content.sequence.clear()
        self.content.sequence.addItems(sequences)

    def setValids(self, sequence):
        self.content.beginningTime.clear()
        self.content.endingTime.clear()

        valids = self.prevs.get(sequence)
        if valids:
            self.content.beginningTime.setText(valids[0])
            self.content.endingTime.setText(valids[1])


class SigmetCustomSegment(BaseSegment):

    def __init__(self, typeSegment, parent=None):
        super(SigmetCustomSegment, self).__init__(typeSegment, parent)
        self.head = SigmetSimpleHead(self)
        self.content = SigmetCustomContent(self)

        self.initUI()
        self.bindSignal()

    def bindSignal(self):
        self.changeSignal.connect(self.head.initState)
        self.changeSignal.connect(self.updateText)
        self.changeSignal.connect(self.setText)

    def updateText(self):
        self.setText()
        self.setPlaceholder()

    def setPlaceholder(self):
        tips = {
            'WS': 'EMBD TS FCST N OF N2000 TOP FL360 MOV N 25KMH NC',
            'WC': 'TC YAGI PSN N2706 W07306 CB OBS AT 1600Z WI 300KM OF CENTRE TOP FL420 NC\nFCST 2200Z TC CENTRE N2740 W07345',
            'WV': 'VA ERUPTION MT ASHVAL PSN S1500 E07348 VA CLD\nOBS AT 1100Z APRX 50KM WID LINE BTN S1500 E07348 - S1530 E07642 FL310/450 MOV ESE 65KMH\nFCST 1700Z VA CLD APRX 50KM WID LINE BTN S1506 E07500 - S1518 E08112 - S1712 E08330',
            'WA': 'MOD MTW OBS AT 1205Z N4200 E11000 FL080 STNR NC'
        }
        tip = tips[self.type.tt]
        self.content.text.setPlaceholderText(tip)

    def setText(self):
        last = db.query(Sigmet).filter(Sigmet.tt == self.type.tt, ~Sigmet.rpt.contains('CNL')).order_by(Sigmet.sent.desc()).first()
        if last:
            fir = conf.value('Message/FIR')
            _, text = last.rpt.split('\n')
            text = text.replace(fir, '')
            text = text.replace('=', '').strip()

            self.content.text.setText(text)
        else:
            self.content.text.clear()
