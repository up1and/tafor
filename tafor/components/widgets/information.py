import re
import datetime

from itertools import cycle

from PyQt5.QtGui import QIcon, QRegExpValidator, QIntValidator, QTextCharFormat, QTextCursor, QFont, QPixmap
from PyQt5.QtCore import Qt, QRegExp, QCoreApplication, pyqtSignal
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLineEdit, QMenu, QActionGroup, QAction, QLabel, QSpacerItem, QSizePolicy

from tafor import conf
from tafor.states import context
from tafor.utils import _purePattern, Pattern, SigmetGrammar
from tafor.utils.convert import parseTime, ceilTime, roundTime, calcPosition
from tafor.utils.service import currentSigmet
from tafor.models import db, Sigmet
from tafor.components.widgets.forecast import SegmentMixin
from tafor.components.ui import Ui_sigmet_general, Ui_sigmet_typhoon, Ui_sigmet_ash, Ui_sigmet_cancel, Ui_sigmet_custom, main_rc


class BaseSigmet(SegmentMixin, QWidget):

    contentChanged = pyqtSignal()

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
        self.sequence.textEdited.connect(lambda: self.coloredText(self.sequence))

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

    def hasAcceptableInput(self):
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
        self.base.editingFinished.connect(lambda: self.validateBaseTop(self.base))
        self.top.editingFinished.connect(lambda: self.validateBaseTop(self.top))
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
        self.observation.currentTextChanged.connect(self.setObservationTime)
        self.observationTime.textChanged.connect(lambda: self.coloredText(self.observationTime))

    def setValidator(self):
        super().setValidator()
        time = QRegExpValidator(QRegExp(self.rules.time))
        self.observationTime.setValidator(time)

    def setObservationTime(self, text):
        if text == 'OBS':
            self.observationTime.setText(self.beginningTime.text()[2:])
        else:
            if self.beginningTime.text()[2:] == self.observationTime.text():
                self.observationTime.clear()

    def isFcstMode(self):
        # return hasattr(self, 'area') and self.area.fcstButton.isChecked()
        pass

    def observationText(self):
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

    def forecastText(self):
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

    def hasAcceptableInput(self):
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

        if self.isFcstMode():
            mustRequired.append(self.forecastTime.hasAcceptableInput())
        else:
            mustRequired.append(self.moveState())

        return all(mustRequired)

    def phenomenon(self):
        items = [self.description.currentText(), self.phenomena.currentText()]
        text = ' '.join(items) if all(items) else ''
        return text

    def message(self):
        fir = conf.value('Message/FIR')
        phenomena = self.phenomenon()
        observation = self.observationText()
        fightLevel = self.fightLevel()
        moveState = self.moveState()
        intensityChange = self.intensityChange.currentText()

        items = [fir, phenomena, observation, '{location}', fightLevel, moveState, intensityChange]
        if self.forecastTime.isEnabled():
            forecast = self.forecastText()
            items += [forecast, '{forecastLocation}']

        content = ' '.join(filter(None, items))
        return '\n'.join([self.firstLine(), content])

    def clear(self):
        super().clear()
        self.description.setCurrentIndex(1)
        self.observation.setCurrentIndex(0)
        self.level.setCurrentIndex(1)
        self.forecastTime.setEnabled(False)
        self.forecastTimeLabel.setEnabled(False)


class SigmetTyphoon(ObservationMixin, ForecastMixin, MovementMixin, BaseSigmet, Ui_sigmet_typhoon.Ui_Editor):

    circleChanged = pyqtSignal()

    def __init__(self, parent):
        super().__init__(parent)
        self.setPhenomena()
        self.setFcstOrObs()

    def bindSignal(self):
        super().bindSignal()

        self.currentLatitude.editingFinished.connect(lambda: self.circleChanged.emit())
        self.currentLongitude.editingFinished.connect(lambda: self.circleChanged.emit())
        self.range.editingFinished.connect(lambda: self.circleChanged.emit())
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

    def circle(self):
        coords = {}
        if self.currentLatitude.hasAcceptableInput() and self.currentLongitude.hasAcceptableInput():
            coords['center'] = [self.currentLongitude.text(), self.currentLatitude.text()]

        if self.range.hasAcceptableInput():
            coords['radius'] = self.range.text()
        
        return coords

    def updateLocation(self, circle):
        if circle:
            lon, lat = circle['center']
            self.currentLongitude.setText(lon)
            self.currentLatitude.setText(lat)

            radius = circle['radius']
            self.range.setText(str(radius))
        else:
            self.currentLongitude.clear()
            self.currentLatitude.clear()
            self.range.clear()

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
        fir = conf.value('Message/FIR')
        phenomena = self.phenomenon()
        observation = self.observationText()
        intensityChange = self.intensityChange.currentText()
        moveState = self.moveState()
        forecastPosition = self.forecastPosition()

        unit = 'KM'
        main = 'PSN {latitude} {Longitude} CB {observation} WI {range}{unit} OF TC CENTRE TOP FL{height}'.format(
                latitude=self.currentLatitude.text(),
                Longitude=self.currentLongitude.text(),
                observation=observation,
                range=int(self.range.text()),
                unit=unit,
                height=self.height.text(),
            )

        items = [fir, phenomena, main]
        if forecastPosition:
            items += [intensityChange, forecastPosition]
        else:
            items += [moveState, intensityChange]

        content = ' '.join(filter(None, items))
        return '\n'.join([self.firstLine(), content])

    # def initState(self):
    #     if self.forecastTime.text():
    #         return

    #     self.setForecastTime()

    def hasAcceptableInput(self):
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

        return all(mustRequired) and any(anyRequired)

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
        self.name.textEdited.connect(lambda: self.upperText(self.name))

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

    def hasAcceptableInput(self):
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

        if self.isFcstMode():
            mustRequired.append(self.forecastTime.hasAcceptableInput())
        elif self.speed.isEnabled():
            mustRequired.append(self.speed.hasAcceptableInput())

        if self.currentLongitude.isEnabled() and self.currentLatitude.isEnabled():
            mustRequired.append(self.currentLongitude.hasAcceptableInput())
            mustRequired.append(self.currentLatitude.hasAcceptableInput())

        return all(mustRequired)

    def message(self):
        fir = conf.value('Message/FIR')
        phenomena = self.phenomenon()
        observation = self.observationText()
        fightLevel = self.fightLevel()
        moveState = self.moveState()
        intensityChange = self.intensityChange.currentText()

        if self.currentLongitude.isEnabled() and self.currentLatitude.isEnabled():
            position = 'PSN {latitude} {Longitude} VA CLD {observation}'.format(
                    latitude=self.currentLatitude.text(),
                    Longitude=self.currentLongitude.text(),
                    observation=observation,
                )
        else:
            position = self.observationText()

        items = [fir, phenomena, position, '{location}', fightLevel, moveState, intensityChange]
        if self.forecastTime.isEnabled():
            forecast = self.forecastText()
            items += [forecast, '{forecastLocation}']

        content = ' '.join(filter(None, items))
        return '\n'.join([self.firstLine(), content])

    def clear(self):
        super().clear()
        self.name.clear()
        self.phenomena.setCurrentIndex(0)


class SigmetCancel(BaseSigmet, Ui_sigmet_cancel.Ui_Editor):

    def bindSignal(self):
        super().bindSignal()
        self.cancelSequence.lineEdit().textEdited.connect(lambda: self.upperText(self.cancelSequence.lineEdit()))

        self.cancelSequence.lineEdit().textEdited.connect(lambda: self.coloredText(self.cancelSequence.lineEdit()))
        self.cancelBeginningTime.textEdited.connect(lambda: self.coloredText(self.cancelBeginningTime))
        self.cancelEndingTime.textEdited.connect(lambda: self.coloredText(self.cancelEndingTime))

    def setValidator(self):
        super().setValidator()
        sequence = QRegExpValidator(QRegExp(self.rules.sequence, Qt.CaseInsensitive))
        self.cancelSequence.setValidator(sequence)

        date = QRegExpValidator(QRegExp(self.rules.date))
        self.cancelBeginningTime.setValidator(date)
        self.cancelEndingTime.setValidator(date)

    def hasAcceptableInput(self):
        mustRequired = [
            self.beginningTime.hasAcceptableInput(),
            self.endingTime.hasAcceptableInput(),
            self.sequence.hasAcceptableInput(),
            self.cancelBeginningTime.hasAcceptableInput(),
            self.cancelEndingTime.hasAcceptableInput(),
            self.cancelSequence.lineEdit().hasAcceptableInput()
        ]

        return all(mustRequired)

    def message(self):
        fir = conf.value('Message/FIR')
        cancel = 'CNL {} {} {}/{}'.format(
            self.parent.sign(),
            self.cancelSequence.currentText().strip(),
            self.cancelBeginningTime.text(),
            self.cancelEndingTime.text()
        )
        items = [fir, cancel]
        content = ' '.join(filter(None, items))
        return '\n'.join([self.firstLine(), content])


class SigmetCustom(BaseSigmet, Ui_sigmet_custom.Ui_Editor):

    def __init__(self, parent):
        super().__init__(parent)
        self.setUpper()

    def bindSignal(self):
        super().bindSignal()
        self.text.textChanged.connect(self.filterText)
        self.text.textChanged.connect(lambda: self.contentChanged.emit())

    def filterText(self):
        origin = self.text.toPlainText()
        text = re.sub(r'[^A-Za-z0-9)(\/\.\s,-]+', '', origin)
        text = text.upper()
        if origin != text:
            cursor = self.text.textCursor()
            pos = cursor.position()
            self.text.setText(text)
            cursor.setPosition(pos)
            self.text.setTextCursor(cursor)

    def setUpper(self):
        upper = QTextCharFormat()
        upper.setFontCapitalization(QFont.AllUppercase)
        self.text.setCurrentCharFormat(upper)

    def hasAcceptableInput(self):
        mustRequired = [
            self.beginningTime.hasAcceptableInput(),
            self.endingTime.hasAcceptableInput(),
            self.sequence.hasAcceptableInput(),
            self.text.toPlainText().strip()
        ]

        return all(mustRequired)

    def message(self):
        fir = conf.value('Message/FIR')
        items = [fir, self.text.toPlainText().strip()]
        content = ' '.join(filter(None, items))
        return '\n'.join([self.firstLine(), content])


class AirmetGeneral(SigmetGeneral):

    def __init__(self, parent):
        super().__init__(parent)
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

