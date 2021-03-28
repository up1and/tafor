import re
import datetime

from itertools import cycle

from PyQt5.QtGui import QIcon, QRegExpValidator, QIntValidator, QTextCharFormat, QTextCursor, QFont, QPixmap
from PyQt5.QtCore import Qt, QRegExp, QCoreApplication, pyqtSignal
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLineEdit, QMenu, QActionGroup, QAction, QRadioButton, QLabel, QSpacerItem, QSizePolicy

from tafor import conf
from tafor.states import context
from tafor.utils import _purePattern, Pattern, SigmetGrammar
from tafor.utils.convert import parseTime, ceilTime, roundTime, calcPosition
from tafor.utils.service import currentSigmet
from tafor.models import db, Sigmet
from tafor.components.widgets.forecast import SegmentMixin
from tafor.components.widgets.graphic import GraphicsWindow
from tafor.components.ui import Ui_sigmet, Ui_sigmet_general, Ui_sigmet_typhoon, Ui_sigmet_ash, Ui_sigmet_cancel, Ui_sigmet_custom, main_rc



class BaseSigmet(SegmentMixin, QWidget):
    completeSignal = pyqtSignal(bool)

    def __init__(self, parent):
        super().__init__()
        self.complete = False
        self.durations = None
        self.rules = Pattern()
        self.parent = parent
        self.span = 4

        self.setupUi(self)
        self.initState()
        self.setValidator()
        self.bindSignal()

    def initState(self):
        self.setPeriodTime()
        self.setSquence()
        self.updateDurations()
        # self.setPrediction(self.forecast.currentText())

    def bindSignal(self):
        self.beginningTime.textChanged.connect(self.updateDurations)
        self.endingTime.textChanged.connect(self.updateDurations)
        self.beginningTime.editingFinished.connect(self.validatePeriod)
        self.endingTime.editingFinished.connect(self.validatePeriod)

        self.sequence.textEdited.connect(lambda: self.upperText(self.sequence))

        self.beginningTime.textEdited.connect(lambda: self.coloredText(self.beginningTime))
        self.endingTime.textEdited.connect(lambda: self.coloredText(self.endingTime))

        self.defaultSignal()

    def updateDurations(self):
        if self.beginningTime.hasAcceptableInput() and self.endingTime.hasAcceptableInput():
            beginText = self.beginningTime.text()
            endText = self.endingTime.text()
            start = parseTime(beginText)
            end = parseTime(endText)
            self.durations = (start, end)
        else:
            self.durations = None

    def periodTime(self):
        self.time = datetime.datetime.utcnow()
        if self.parent.tt == 'WC':
            start = roundTime(self.time)
        else:
            start = ceilTime(self.time, amount=10)
        end = start + datetime.timedelta(hours=self.span)
        return start, end

    def validatePeriod(self):
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

    def validate(self):
        self.validatePeriod()

    def setSpan(self, span):
        self.span = span
        self.initState()

    def setPeriodTime(self):
        beginningTime, endingTime = self.periodTime()
        self.beginningTime.setText(beginningTime.strftime('%d%H%M'))
        self.endingTime.setText(endingTime.strftime('%d%H%M'))

    def setValidator(self):
        date = QRegExpValidator(QRegExp(self.rules.date))
        self.beginningTime.setValidator(date)
        self.endingTime.setValidator(date)

        sequence = QRegExpValidator(QRegExp(self.rules.sequence, Qt.CaseInsensitive))
        self.sequence.setValidator(sequence)

    def setSquence(self):
        time = datetime.datetime.utcnow()
        begin = datetime.datetime(time.year, time.month, time.day)
        query = db.query(Sigmet).filter(Sigmet.sent > begin)
        if self.parent.tt == 'WA':
            query = query.filter(Sigmet.tt == 'WA')
        else:
            query = query.filter(Sigmet.tt != 'WA')

        def isYesterday(text):
            if text:
                pattern = re.compile(r'\d{6}')
                m = pattern.search(text)
                if m:
                    issueTime = m.group()
                    return int(issueTime[:2]) != time.day or issueTime[2:] == '0000'

            return False

        sigmets = [sig for sig in query.all() if not isYesterday(sig.sign)]
        count = len(sigmets) + 1
        self.sequence.setText(str(count))

    def checkComplete(self):
        raise NotImplementedError

    def firstLine(self):
        area = conf.value('Message/FIR').split()[0]
        sign = self.parent.sign()
        sequence = self.sequence.text()
        beginningTime = self.beginningTime.text()
        endingTime = self.endingTime.text()
        icao = conf.value('Message/ICAO')

        text = '{} {} {} VALID {}/{} {}-'.format(area, sign, sequence, beginningTime, endingTime, icao)
        return text

    def clear(self):
        self.durations = None
        self.beginningTime.clear()
        self.endingTime.clear()
        self.sequence.clear()


class FlightLevelMixin(object):

    def bindSignal(self):
        super().bindSignal()
        self.level.currentTextChanged.connect(self.setFightLevel)
        self.base.editingFinished.connect(lambda :self.validateBaseTop(self.base))
        self.top.editingFinished.connect(lambda :self.validateBaseTop(self.top))
        self.base.textEdited.connect(lambda: self.coloredText(self.base))
        self.top.textEdited.connect(lambda: self.coloredText(self.top))

    def setValidator(self):
        super().setValidator()
        fightLevel = QRegExpValidator(QRegExp(self.rules.fightLevel))
        self.base.setValidator(fightLevel)
        self.top.setValidator(fightLevel)

    def setFightLevel(self, text):
        if text in ['TOP', 'TOP ABV', 'SFC', 'BLW']:
            self.base.setEnabled(False)
            self.top.setEnabled(True)
            self.baseLabel.setEnabled(False)
            self.topLabel.setEnabled(True)
            self.base.clear()
        elif text in ['ABV']:
            self.base.setEnabled(True)
            self.top.setEnabled(False)
            self.baseLabel.setEnabled(True)
            self.topLabel.setEnabled(False)
            self.top.clear()
        else:
            self.base.setEnabled(True)
            self.top.setEnabled(True)
            self.baseLabel.setEnabled(True)
            self.topLabel.setEnabled(True)

    def validateBaseTop(self, line):
        if not (self.base.isEnabled() and self.top.isEnabled()):
            return

        base = self.base.text()
        top = self.top.text()
        if base and top:
            if int(top) <= int(base):
                line.clear()
                self.parent.showNotificationMessage(QCoreApplication.translate('Editor', 'The top flight level needs to be greater than the base flight level'))

    def fightLevel(self):
        level = self.level.currentText()
        base = self.base.text()
        top = self.top.text()

        if not level:
            if base and top:
                text = 'FL{}/{}'.format(base, top) if all([top, base]) else ''
            else:
                text = base if base else top
                text = 'FL{}'.format(text) if text else ''

        if level in ['TOP', 'TOP ABV', 'BLW']:
            text = '{} FL{}'.format(level, top) if top else ''

        if level == 'ABV':
            text = 'ABV FL{}'.format(base) if base else ''

        if level == 'SFC':
            text = 'SFC/FL{}'.format(top) if top else ''

        return text


class MovementMixin(object):

    def bindSignal(self):
        super().bindSignal()
        self.movement.currentTextChanged.connect(self.setSpeed)

    def setValidator(self):
        super().setValidator()
        self.speed.setValidator(QIntValidator(1, 99, self.speed))

    def setSpeed(self, text):
        if text == 'STNR':
            self.speed.setEnabled(False)
            self.speedLabel.setEnabled(False)
        else:
            self.speed.setEnabled(True)
            self.speedLabel.setEnabled(True)

    def moveState(self):
        movement = self.movement.currentText()
        if movement == 'STNR':
            return movement

        if not self.speed.hasAcceptableInput():
            return

        movement = self.movement.currentText()
        unit = 'KT' if context.environ.unit() == 'imperial' else 'KMH'
        speed = int(self.speed.text()) if self.speed.text() else ''

        text = 'MOV {movement} {speed}{unit}'.format(
                movement=movement,
                speed=speed,
                unit=unit
            )

        return text


class ObservationMixin(object):

    def bindSignal(self):
        super().bindSignal()
        self.observation.currentTextChanged.connect(self.setObservation)
        self.observationTime.textChanged.connect(lambda: self.coloredText(self.observationTime))

    def setValidator(self):
        super().setValidator()
        time = QRegExpValidator(QRegExp(self.rules.time))
        self.observationTime.setValidator(time)

    def setObservation(self, text):
        if text == 'OBS':
            self.observationTime.setText(self.beginningTime.text()[2:])
        else:
            if self.beginningTime.text()[2:] == self.observationTime.text():
                self.observationTime.clear()

    def isFcstMode(self):
        # return hasattr(self, 'area') and self.area.fcstButton.isChecked()
        pass

    def observation(self):
        if self.observation.currentText() == 'OBS':
            text = 'OBS AT {}Z'.format(self.observationTime.text()) if self.observationTime.hasAcceptableInput() else ''
        else:
            text = '{} AT {}Z'.format(self.observation.currentText(), 
                self.observationTime.text()) if self.observationTime.hasAcceptableInput() else self.observation.currentText()

        return text


class ForecastMixin(object):

    def setValidator(self):
        super().setValidator()
        time = QRegExpValidator(QRegExp(self.rules.time))
        self.forecastTime.setValidator(time)

    def setForecastTime(self):
        if self.durations is None or not self.endingTime.text():
            return

        text = self.endingTime.text()[2:]
        self.forecastTime.setText(text)

    def forecastTime(self):
        text = 'FCST AT {}Z'.format(self.forecastTime.text())
        return text


class SigmetGeneral(ObservationMixin, ForecastMixin, FlightLevelMixin, MovementMixin, BaseSigmet, Ui_sigmet_general.Ui_Editor):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPhenomenaDescription()
        self.setPhenomena()
        self.setFcstOrObs()
        self.setLevel('TS')

    def bindSignal(self):
        super().bindSignal()

        self.description.currentTextChanged.connect(self.setPhenomena)
        self.phenomena.currentTextChanged.connect(self.setLevel)

        # self.changeSignal.connect(self.head.initState)
        # self.content.area.areaModeChanged.connect(self.setAreaMode)

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
        observations = ['FCST', 'OBS']
        self.observation.addItems(observations)

    def setLevel(self, text):
        self.level.clear()

        if text in ['CB', 'TCU', 'TS', 'TSGR']:
            levels = ['', 'TOP', 'ABV', 'SFC', 'TOP ABV']
            self.level.addItems(levels)
            self.level.setCurrentIndex(self.level.findText('TOP'))
        else:
            levels = ['', 'ABV', 'BLW', 'SFC']
            self.level.addItems(levels)
            self.level.setCurrentIndex(-1)

    # def setAreaMode(self):
    #     if self.isFcstMode():
    #         self.forecast.setCurrentIndex(self.forecast.findText('OBS'))
    #         self.forecastTime.setEnabled(True)
    #         self.forecastTimeLabel.setEnabled(True)
    #         self.setForecastTime()
    #     else:
    #         self.forecastTime.setEnabled(False)
    #         self.forecastTimeLabel.setEnabled(False)
    #         self.forecastTime.clear()

    def checkComplete(self):
        mustRequired = [
            self.beginningTime.hasAcceptableInput(),
            self.endingTime.hasAcceptableInput(),
            self.sequence.hasAcceptableInput(),
        ]

        if self.observation.currentText() == 'OBS':
            mustRequired.append(self.observationTime.hasAcceptableInput())

        if self.base.isEnabled() and self.top.isEnabled():
            mustRequired.append(self.base.hasAcceptableInput() or self.top.hasAcceptableInput())
        else:
            if self.base.isEnabled():
                mustRequired.append(self.base.hasAcceptableInput())

            if self.top.isEnabled():
                mustRequired.append(self.top.hasAcceptableInput())

        # if hasattr(self, 'area'):
        #     mustRequired.append(self.area.text())

        if self.isFcstMode():
            mustRequired.append(self.forecastTime.hasAcceptableInput())
        else:
            mustRequired.append(self.moveState())

        self.complete = all(mustRequired)
        self.completeSignal.emit(self.complete)

    def phenomenon(self):
        items = [self.description.currentText(), self.phenomena.currentText()]
        text = ' '.join(items) if all(items) else ''
        return text

    def message(self):
        # areas = self.area.text()
        prediction = self.parent.prediction()
        fightLevel = self.fightLevel()
        moveState = self.moveState()
        intensityChange = self.intensityChange.currentText()
        if self.isFcstAreaMode():
            fcstTime = self.fcstTime()
            items = [prediction, '{location}', fightLevel, moveState, intensityChange, fcstTime, '{forecastLocation}']
        else:
            # area = areas[0] if isinstance(areas, list) else areas
            items = [prediction, '{location}', fightLevel, moveState, intensityChange]

        return ' '.join(filter(None, items))

    def clear(self):
        super().clear()
        self.description.setCurrentIndex(1)
        self.observation.setCurrentIndex(0)
        self.level.setCurrentIndex(1)
        self.forecastTime.setEnabled(False)
        self.forecastTimeLabel.setEnabled(False)


class SigmetTyphoon(ObservationMixin, ForecastMixin, MovementMixin, BaseSigmet, Ui_sigmet_typhoon.Ui_Editor):

    def __init__(self, parent):
        super().__init__(parent)
        self.setPhenomena()
        self.setFcstOrObs()

    def bindSignal(self):
        super().bindSignal()

        # self.currentLatitude.editingFinished.connect(self.setCircleOnCanvas)
        # self.currentLongitude.editingFinished.connect(self.setCircleOnCanvas)
        # self.range.editingFinished.connect(self.setCircleOnCanvas)
        # self.area.canvasWidget.canvas.pointsChanged.connect(self.setCircleOnContent)
        # self.area.canvasWidget.canvas.stateChanged.connect(self.setCircleOnContent)

        self.currentLatitude.textChanged.connect(self.setForecastPosition)
        self.currentLongitude.textChanged.connect(self.setForecastPosition)
        self.speed.textEdited.connect(self.setForecastPosition)
        self.movement.currentTextChanged.connect(self.setForecastPosition)
        self.forecastTime.textChanged.connect(self.setForecastPosition)

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

        self.endingTime.textChanged.connect(self.setForecastTime)
        self.beginningTime.textEdited.connect(self.setForecastPosition)
        self.observationTime.textEdited.connect(self.setForecastPosition)

        # self.changeSignal.connect(self.initState)

    def setValidator(self):
        super().setValidator()

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

    def setPhenomena(self, text='TC'):
        self.phenomena.addItems(['TC'])

    def setFcstOrObs(self):
        observations = ['OBS', 'FCST']
        self.observation.addItems(observations)

    def phenomenon(self):
        items = [self.phenomena.currentText(), self.name.text()]
        text = ' '.join(items) if all(items) else ''
        return text

    def setCircleOnCanvas(self):
        if not context.fir.layer.drawable:
            return

        if self.currentLatitude.hasAcceptableInput() and self.currentLongitude.hasAcceptableInput():
            lon = self.currentLongitude.text()
            lat = self.currentLatitude.text()
            # self.area.canvasWidget.setCircleCenter([lon, lat])

        if self.range.hasAcceptableInput():
            radius = self.range.text()
            # self.area.canvasWidget.setCircleRadius(radius)

    def setCircleOnContent(self):
        # layer = context.fir.layer
        # if not layer.drawable:
        #     return

        # canvas = self.area.canvasWidget.canvas
        # points = layer.pixelToDegree(canvas.points)
        # if points:
        #     lon, lat = points[0]
        #     self.currentLongitude.setText(lon)
        #     self.currentLatitude.setText(lat)
        # else:
        #     self.currentLongitude.clear()
        #     self.currentLatitude.clear()

        # unit = 'NM' if context.environ.unit() == 'imperial' else 'KM'
        # radius = round(layer.pixelToDistance(canvas.radius, unit=unit) / 10) * 10
        # if radius:
        #     self.range.setText(str(radius))
        # else:
        #     self.range.clear()
        pass

    def setForecastTime(self):
        if self.durations is None or not self.endingTime.text():
            return

        text = self.endingTime.text()
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
            self.observationTime.hasAcceptableInput(),
            self.beginningTime.hasAcceptableInput(),
        ]

        if not (all(mustRequired) and any(anyRequired)):
            return

        movement = self.movement.currentText()

        if movement == 'STNR':
            self.forecastLatitude.clear()
            self.forecastLongitude.clear()
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
        observationTime = self.observationTime.text() if self.observationTime.hasAcceptableInput() else ''
        beginningTime = self.beginningTime.text()[2:] if self.beginningTime.hasAcceptableInput() else ''
        fcstTime = self.forecastTime.text()

        time = self.moveTime(observationTime or beginningTime, fcstTime).seconds
        degree = direction[movement]
        speed = self.speed.text()
        latitude = self.currentLatitude.text()
        longitude = self.currentLongitude.text()

        forecastLatitude, forecastLongitude = calcPosition(latitude, longitude, speed, time, degree)
        self.forecastLatitude.setText(forecastLatitude)
        self.forecastLongitude.setText(forecastLongitude)

    def moveTime(self, start, end):
        return parseTime(end) - parseTime(start)

    def forecastPosition(self):
        required = self.forecastTime.hasAcceptableInput() and self.forecastLatitude.hasAcceptableInput() \
            and self.forecastLongitude.hasAcceptableInput()

        if not required:
            return

        text = 'FCST AT {forecastTime}Z TC CENTRE PSN {forecastLatitude} {forecastLongitude}'.format(
                forecastTime=self.forecastTime.text(),
                forecastLatitude=self.forecastLatitude.text(),
                forecastLongitude=self.forecastLongitude.text()
            )

        return text

    def message(self):
        unit = 'NM' if context.environ.unit() == 'imperial' else 'KM'
        area = 'PSN {latitude} {Longitude} CB {prediction} WI {range}{unit} OF TC CENTRE TOP FL{height}'.format(
                latitude=self.currentLatitude.text(),
                Longitude=self.currentLongitude.text(),
                prediction=self.parent.head.prediction(),
                range=int(self.range.text()),
                unit=unit,
                height=self.height.text(),
            )
        moveState = self.moveState()
        intensityChange = self.intensityChange.currentText()
        forecastPosition = self.forecastPosition()

        if forecastPosition:
            messages = [area, intensityChange, forecastPosition]
        else:
            messages = [area, moveState, intensityChange]

        text = ' '.join(messages)
        return text

    # def initState(self):
    #     if self.forecastTime.text():
    #         return

    #     self.setForecastTime()

    def checkComplete(self):
        mustRequired = [
            self.beginningTime.hasAcceptableInput(),
            self.endingTime.hasAcceptableInput(),
            self.sequence.hasAcceptableInput(),
            self.name.text(),
            self.currentLatitude.hasAcceptableInput(),
            self.currentLongitude.hasAcceptableInput(),
            self.height.hasAcceptableInput(),
            self.range.hasAcceptableInput()
        ]

        anyRequired = [
            self.forecastTime.hasAcceptableInput() and self.forecastLatitude.hasAcceptableInput() and self.forecastLongitude.hasAcceptableInput(),
            self.speed.hasAcceptableInput()
        ]

        if self.observation.currentText() == 'OBS':
            mustRequired.append(self.observationTime.hasAcceptableInput())

        self.complete = all(mustRequired) and any(anyRequired)
        self.completeSignal.emit(self.complete)

    def clear(self):
        super().clear()
        self.name.clear()


class SigmetAsh(ObservationMixin, ForecastMixin, FlightLevelMixin, MovementMixin, BaseSigmet, Ui_sigmet_ash.Ui_Editor):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPhenomena()
        self.setFcstOrObs()

    def bindSignal(self):
        super().bindSignal()
        self.currentLatitude.textEdited.connect(lambda: self.upperText(self.currentLatitude))
        self.currentLongitude.textEdited.connect(lambda: self.upperText(self.currentLongitude))

        self.currentLatitude.textEdited.connect(lambda: self.coloredText(self.currentLatitude))
        self.currentLongitude.textEdited.connect(lambda: self.coloredText(self.currentLongitude))

    def setValidator(self):
        super().setValidator()
        latitude = QRegExpValidator(QRegExp(self.rules.latitude, Qt.CaseInsensitive))
        self.currentLatitude.setValidator(latitude)

        longitude = QRegExpValidator(QRegExp(self.rules.longitude, Qt.CaseInsensitive))
        self.currentLongitude.setValidator(longitude)

    def setPhenomena(self, text='ERUPTION'):
        self.phenomena.addItems(['ERUPTION', 'CLD'])

    def setFcstOrObs(self):
        observations = ['FCST', 'OBS']
        self.observation.addItems(observations)

    def phenomenon(self):
        items = ['VA', self.phenomena.currentText()]
        if self.name.isEnabled() and self.name.text():
            items += ['MT', self.name.text()]
        text = ' '.join(items) if all(items) else ''
        return text

    def checkComplete(self):
        mustRequired = [
            self.beginningTime.hasAcceptableInput(),
            self.endingTime.hasAcceptableInput(),
            self.sequence.hasAcceptableInput(),
        ]

        if self.observationTime.isEnabled():
            mustRequired.append(self.observationTime.hasAcceptableInput())

        if self.base.isEnabled():
            mustRequired.append(self.base.hasAcceptableInput())

        if self.top.isEnabled():
            mustRequired.append(self.top.hasAcceptableInput())

        # if hasattr(self, 'area'):
        #     mustRequired.append(self.area.text())

        if self.isFcstMode():
            mustRequired.append(self.forecastTime.hasAcceptableInput())
        elif self.speed.isEnabled():
            mustRequired.append(self.speed.hasAcceptableInput())

        if self.currentLongitude.isEnabled() and self.currentLatitude.isEnabled():
            mustRequired.append(self.currentLongitude.hasAcceptableInput())
            mustRequired.append(self.currentLatitude.hasAcceptableInput())

        self.complete = all(mustRequired)
        self.completeSignal.emit(self.complete)

    def message(self):
        if self.currentLongitude.isEnabled() and self.currentLatitude.isEnabled():
            prefix = 'PSN {latitude} {Longitude} VA CLD {observation}'.format(
                    latitude=self.currentLatitude.text(),
                    Longitude=self.currentLongitude.text(),
                    observation=self.observation(),
                )
        else:
            prefix = self.observation()

        areas = self.area.text()
        fightLevel = self.fightLevel()
        moveState = self.moveState()
        intensityChange = self.intensityChange.currentText()
        if self.isFcstMode():
            area, forecastArea = areas
            fcstTime = self.fcstTime()
            items = [prefix, area, fightLevel, moveState, intensityChange, fcstTime, forecastArea]
        else:
            area = areas[0] if isinstance(areas, list) else areas
            items = [prefix, area, fightLevel, moveState, intensityChange]

        return ' '.join(filter(None, items))

    def clear(self):
        super().clear()
        self.name.clear()
        self.phenomena.setCurrentIndex(0)


class SigmetCancel(BaseSigmet, Ui_sigmet_cancel.Ui_Editor):

    def __init__(self, parent):
        super().__init__(parent)


class SigmetCustom(BaseSigmet, Ui_sigmet_custom.Ui_Editor):

    def __init__(self, parent):
        super().__init__(parent)


class AirmetGeneral(SigmetGeneral):

    def __init__(self, parent):
        super().__init__(parent)
        self.setAirmetMode()

    def setAirmetMode(self):
        self.forecastTime.hide()
        self.forecastTimeLabel.hide()

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

    def setValidator(self):
        super().setValidator()
        fightLevel = QRegExpValidator(QRegExp(self.rules.airmansFightLevel))
        self.base.setValidator(fightLevel)
        self.top.setValidator(fightLevel)


class SigmetSegment(QWidget, Ui_sigmet.Ui_Editor):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.parent = parent

        self.tt = 'WS'
        self.typeButtonTexts = [btn.text() for btn in self.typeGroup.findChildren(QRadioButton)]

        self.initUI()
        self.bindSignal()

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

    def bindSignal(self):
        self.significantWeather.clicked.connect(self.changeContent)
        self.tropicalCyclone.clicked.connect(self.changeContent)
        self.volcanicAsh.clicked.connect(self.changeContent)
        self.airmansWeather.clicked.connect(self.changeContent)
        self.template.clicked.connect(self.changeContent)
        self.custom.clicked.connect(self.changeContent)
        self.cancel.clicked.connect(self.changeContent)

    def wmoHeader(self):
        area = conf.value('Message/Area') or ''
        icao = conf.value('Message/ICAO')
        time = datetime.datetime.utcnow().strftime('%d%H%M')
        messages = [self.tt + area, icao, time]
        return ' '.join(filter(None, messages))

    # def message(self):
    #     content = ' '.join([self.head.message(), self.content.message()])
    #     text = '\n'.join([self.head.head(), content])
    #     text = text if text.endswith('=') else text + '='
    #     return text

    def sign(self):
        return 'AIRMET' if self.tt == 'WA' else 'SIGMET'

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
        self.content.clear()
