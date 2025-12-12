import re
import logging
import datetime

from itertools import cycle

from PyQt5.QtGui import QRegExpValidator, QIntValidator, QTextCharFormat, QTextCursor, QFont, QPixmap, QIcon
from PyQt5.QtCore import Qt, QRegExp, QCoreApplication, pyqtSignal
from PyQt5.QtWidgets import QWidget, QLabel, QLineEdit, QToolButton

from tafor import conf
from tafor.states import context

from tafor.utils import Pattern
from tafor.utils.convert import parseTime, ceilTime, roundTime, calcPosition, decimalToDegree, degreeToDecimal
from tafor.utils.validator import AshAdvisoryParser, TyphoonAdvisoryParser
from tafor.models import db, Sigmet
from tafor.components.widgets.forecast import SegmentMixin
from tafor.components.ui import Ui_sigmet_general, Ui_sigmet_typhoon, Ui_sigmet_ash, Ui_sigmet_cancel, Ui_sigmet_custom, main_rc

logger = logging.getLogger('tafor.sigmet.information')


class BaseSigmet(SegmentMixin, QWidget):

    contentChanged = pyqtSignal()

    def __init__(self, parent):
        super().__init__()
        self.complete = False
        self.durations = None
        self.rules = Pattern()
        self.parent = parent
        self.span = 4
        self.forecastMode = False
        self.mode = 'polygon'

        self.setupUi(self)
        self.switchButton = QToolButton(self)
        self.switchButton.hide()
        self.headingGroup.setMinimumWidth(77 * 3 + 32)
        self.initState()
        self.setupFont()
        self.setupMainElementWidth()
        self.setupValidator()
        self.bindSignal()

    def setupMainElementWidth(self):
        if hasattr(self, 'main'):
            parent = self.main
        else:
            parent = self

        for label in parent.findChildren(QLabel):
            label.setMaximumWidth(77)

        for line in parent.findChildren(QLineEdit):
            line.setMaximumWidth(77)

    def initState(self):
        self.updateSquence()
        self.updatePeriodTime()
        self.updateDurations()
        self.componentUpdate()

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

    def componentUpdate(self):
        """
        This method is used to add some custom updates
        """
        pass

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
        if self.type() == 'WC':
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
            context.flash.editor('sigmet', QCoreApplication.translate('Editor', 'Start time cannot be less than the current time'))
            return

        if end <= start:
            self.endingTime.clear()
            context.flash.editor('sigmet', QCoreApplication.translate('Editor', 'Ending time must be greater than the beginning time'))
            return

        if end - start > datetime.timedelta(hours=self.span):
            self.endingTime.clear()
            context.flash.editor('sigmet', QCoreApplication.translate('Editor', 'Valid period more than {} hours').format(self.span))
            return

    def validate(self):
        self.validatePeriod()

    def setSpan(self, span):
        self.span = span
        self.initState()

    def setLocationMode(self, mode):
        self.mode = mode

    def setupValidator(self):
        date = QRegExpValidator(QRegExp(self.rules.date))
        self.beginningTime.setValidator(date)
        self.endingTime.setValidator(date)

        sequence = QRegExpValidator(QRegExp(self.rules.sequence, Qt.CaseInsensitive))
        self.sequence.setValidator(sequence)

    def updatePeriodTime(self):
        beginningTime, endingTime = self.periodTime()
        self.beginningTime.setText(beginningTime.strftime('%d%H%M'))
        self.endingTime.setText(endingTime.strftime('%d%H%M'))

    def updateSquence(self):
        time = datetime.datetime.utcnow()
        begin = datetime.datetime(time.year, time.month, time.day)

        with db.session() as session:
            query = session.query(Sigmet).filter(Sigmet.created > begin)

            if self.type() == 'WA':
                query = query.filter(Sigmet.type == 'WA')
            else:
                query = query.filter(Sigmet.type != 'WA')

            sigmets = query.all()

        def isYesterday(text):
            if text:
                pattern = re.compile(r'\d{6}')
                m = pattern.search(text)
                if m:
                    issueTime = m.group()
                    return int(issueTime[:2]) != time.day or issueTime[2:] == '0000'

            return False

        sigmets = [sig for sig in sigmets if not isYesterday(sig.heading)]
        count = len(sigmets) + 1
        self.sequence.setText(str(count))

    def hasAcceptableInput(self):
        raise NotImplementedError

    def hasForecastMode(self):
        return self.forecastMode

    def type(self):
        return self.parent.type

    def firstLine(self):
        fir = conf.firName
        area = fir.split()[0] if fir else ''
        sign = self.parent.reportType()
        sequence = self.sequence.text()
        beginningTime = self.beginningTime.text()
        endingTime = self.endingTime.text()
        icao = conf.airport

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
        self.format.currentTextChanged.connect(self.setFlightLevel)
        self.base.editingFinished.connect(lambda: self.validateBaseTop(self.base))
        self.top.editingFinished.connect(lambda: self.validateBaseTop(self.top))
        self.base.textEdited.connect(lambda: self.coloredText(self.base))
        self.top.textEdited.connect(lambda: self.coloredText(self.top))

    def setupValidator(self):
        super(FlightLevelMixin, self).setupValidator()
        self.base.setValidator(QIntValidator(1, 999, self.base))
        self.top.setValidator(QIntValidator(100, 999, self.top))
        self.base.setMaxLength(3)
        self.top.setMaxLength(3)

    def setFlightLevel(self, text):
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
                context.flash.editor('sigmet', QCoreApplication.translate('Editor', 'The top flight level needs to be greater than the base flight level'))

    def flightLevel(self):
        format = self.format.currentText()
        base = self.base.text()
        top = self.top.text()

        if base:
            base = str(int(base)).zfill(3)

        if top:
            top = str(int(top)).zfill(3)

        if not format:
            if base and top:
                text = 'FL{}/{}'.format(base, top) if all([top, base]) else ''
            else:
                text = base if base else top
                text = 'FL{}'.format(text) if text else ''

        if format in ['TOP', 'TOP ABV', 'BLW']:
            text = '{} FL{}'.format(format, top) if top else ''

        if format == 'ABV':
            text = 'ABV FL{}'.format(base) if base else ''

        if format == 'SFC':
            text = 'SFC/FL{}'.format(top) if top else ''

        return text

    def clear(self):
        super().clear()
        self.top.clear()
        self.base.clear()


class MovementMixin(object):

    def bindSignal(self):
        super().bindSignal()
        self.direction.currentTextChanged.connect(self.setSpeed)
        self.speed.textChanged.connect(lambda: self.coloredText(self.speed))

    def setupValidator(self):
        super(MovementMixin, self).setupValidator()
        self.speed.setValidator(QIntValidator(1, 99, self.speed))
        self.speed.setMaxLength(2)

    def setSpeed(self, text):
        if text == 'STNR':
            self.speed.setEnabled(False)
            self.speedLabel.setEnabled(False)
            self.speed.clear()
        else:
            self.speed.setEnabled(True)
            self.speedLabel.setEnabled(True)

    def moveState(self):
        movement = self.direction.currentText()
        if movement == 'STNR':
            return movement

        if not self.speed.hasAcceptableInput():
            return

        movement = self.direction.currentText()
        unit = 'KT' if context.environ.unit() == 'imperial' else 'KMH'
        speed = int(self.speed.text()) if self.speed.text() else ''

        text = 'MOV {movement} {speed}{unit}'.format(
                movement=movement,
                speed=speed,
                unit=unit
            )

        return text

    def clear(self):
        super().clear()
        self.direction.setCurrentIndex(0)
        self.speed.clear()


class ObservationMixin(object):

    def bindSignal(self):
        super().bindSignal()
        self.comeFrom.currentTextChanged.connect(self.updateObservation)
        self.beginningTime.textChanged.connect(self.updateObservation)
        self.observedTime.textChanged.connect(lambda: self.coloredText(self.observedTime))

    def setupValidator(self):
        super(ObservationMixin, self).setupValidator()
        time = QRegExpValidator(QRegExp(self.rules.time))
        self.observedTime.setValidator(time)

    def updateObservation(self):
        text = self.comeFrom.currentText()
        if text == 'OBS':
            self.observedTime.setText(self.beginningTime.text()[2:])
            self.observedTimeLabel.setText(QCoreApplication.translate('Editor', 'Observed Time'))
        else:
            self.observedTimeLabel.setText(QCoreApplication.translate('Editor', 'Forecast Time'))
            if self.beginningTime.text()[2:] == self.observedTime.text():
                self.observedTime.clear()

    def observationText(self):
        if self.comeFrom.currentText() == 'OBS':
            text = 'OBS AT {}Z'.format(self.observedTime.text()) if self.observedTime.hasAcceptableInput() else ''
        else:
            text = '{} AT {}Z'.format(self.comeFrom.currentText(), 
                self.observedTime.text()) if self.observedTime.hasAcceptableInput() else self.comeFrom.currentText()

        return text

    def clear(self):
        super().clear()
        self.observedTime.clear()
        self.comeFrom.setCurrentIndex(0)


class ForecastMixin(object):

    def bindSignal(self):
        super().bindSignal()
        self.forecastTime.textChanged.connect(lambda: self.coloredText(self.forecastTime))

    def setupValidator(self):
        super(ForecastMixin, self).setupValidator()
        time = QRegExpValidator(QRegExp(self.rules.time))
        self.forecastTime.setValidator(time)

    def setForecastTime(self):
        if self.durations is None or not self.endingTime.text() or not self.forecastTime.isEnabled():
            return

        text = self.endingTime.text()[2:]
        self.forecastTime.setText(text)

    def setOverlapMode(self, mode):
        if mode == 'final':
            self.comeFrom.setCurrentIndex(self.comeFrom.findText('OBS'))
            self.forecastTime.setEnabled(True)
            self.forecastTimeLabel.setEnabled(True)
            self.setForecastTime()
            self.forecastMode = True
            if hasattr(self, 'finalPositionGroup'):
                self.finalPositionGroup.setEnabled(True)
        else:
            self.forecastTime.setEnabled(False)
            self.forecastTimeLabel.setEnabled(False)
            self.forecastTime.clear()
            self.forecastMode = False
            if hasattr(self, 'finalPositionGroup'):
                self.finalPositionGroup.setEnabled(False)

    def forecastText(self):
        text = 'FCST AT {}Z'.format(self.forecastTime.text())
        return text

    def clear(self):
        super().clear()
        self.forecastTime.clear()


class AdvisoryMixin(object):

    locationChanged = pyqtSignal(dict)

    def __init__(self, parent):
        super().__init__(parent)
        self.switchButton.setText('Switch')
        self.switchButton.setFixedSize(26, 26)
        self.switchButton.setAutoRaise(True)
        self.switchButton.move(233, 12)
        self.switchButton.show()
        self.advisory.hide()
        self.text.setAcceptRichText(False)

        self.groupNames = cycle(['main', 'advisory'])
        self.switchGroup()
        self.upperTextEdit()

    def bindSignal(self):
        super().bindSignal()
        self.switchButton.clicked.connect(self.switchGroup)
        self.text.textChanged.connect(self.parseText)
        self.initial.currentTextChanged.connect(self.updateFinalOption)
        self.initial.currentTextChanged.connect(self.updateLocation)
        self.final.currentTextChanged.connect(self.updateLocation)

    def switchGroup(self):
        self.group = next(self.groupNames)
        if self.group == 'main':
            icon = ':/forward.png'
        else:
            icon = ':/back.png'

        self.switchButton.setIcon(QIcon(icon))
        self.updateVisibility()

    def upperTextEdit(self):
        upper = QTextCharFormat()
        upper.setFontCapitalization(QFont.AllUppercase)
        self.text.setCurrentCharFormat(upper)

    def parseText(self):
        text = self.text.toPlainText()
        if not text:
            return

        try:
            self.parser = self.advisoryParser(text)
            options = self.parser.availableLocations()
            self.initial.clear()
            self.initial.addItems(options)
            self.autoFill()
            self.text.setStyleSheet('color: black')
        except Exception as e:
            context.flash.editor('sigmet', QCoreApplication.translate('Editor', 'Advisory message can not be decoded'))
            self.text.setStyleSheet('color: grey')
            logger.error('Advisory message can not be decoded, {}, {}'.format(text, e))

    def autoFill(self):
        name = self.parser.name()
        if name:
            self.name.setText(name)

        initial = self.initial.currentText()
        if 'OBS' in initial:
            self.comeFrom.setCurrentIndex(self.comeFrom.findText('OBS'))

        if 'FCST' in initial:
            self.comeFrom.setCurrentIndex(self.comeFrom.findText('FCST'))

        features = self.parser.location(initial)
        if features and 'time' in features['properties']:
            time = features['properties']['time']
            self.observedTime.setText(time.strftime('%H%M'))

        features = self.parser.location(self.final.currentText())
        if features and 'time' in features['properties']:
            time = features['properties']['time']
            self.forecastTime.setText(time.strftime('%H%M'))
            self.forecastTime.setEnabled(True)
            self.forecastTimeLabel.setEnabled(True)
        else:
            self.forecastTime.setEnabled(False)
            self.forecastTimeLabel.setEnabled(False)

        final = self.final.currentText()
        movement = self.parser.movement()
        if movement:
            self.direction.setCurrentIndex(self.direction.findText(movement))

            if not final and movement != 'STNR':
                speed = str(self.parser.speed())
                self.speed.setText(speed)
            else:
                self.speed.clear()

    def updateFinalOption(self):
        index = self.initial.currentIndex()
        rests = ['']
        if index + 1 < self.initial.count():
            rests.append(self.initial.itemText(index + 1))

        self.final.clear()
        self.final.addItems(rests)

    def updateVisibility(self):
        if self.group == 'main':
            self.advisory.hide()
            self.main.show()
        else:
            self.advisory.show()
            self.main.hide()

    def updateLocation(self):
        try:
            self.autoFill()
        except Exception as e:
            logger.error('Auto fill location from advisory message failed, {}'.format(e))

    def setLocationMode(self, mode):
        super().setLocationMode(mode)

        if self.mode in ['polygon', 'line', 'circle']:
            self.switchButton.show()
        else:
            self.switchButton.hide()
            if self.group == 'advisory':
                self.switchGroup()
                return

        self.updateVisibility()

    def clear(self):
        super().clear()
        if self.group == 'advisory':
            self.group = next(self.groupNames)
            self.advisory.hide()
            self.main.show()

        self.text.clear()
        self.initial.clear()
        self.final.clear()
        self.parser = None


class SigmetGeneral(ObservationMixin, ForecastMixin, FlightLevelMixin, MovementMixin, BaseSigmet, Ui_sigmet_general.Ui_Editor):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPhenomenaDescription()
        self.setPhenomena()
        self.setFcstOrObs()
        self.setFlightLevelFormat('TS')

    def bindSignal(self):
        super().bindSignal()
        self.description.currentTextChanged.connect(self.setPhenomena)
        self.phenomenon.currentTextChanged.connect(self.setFlightLevelFormat)

    def setPhenomenaDescription(self):
        descriptions = ['OBSC', 'EMBD', 'FRQ', 'SQL', 'SEV', 'HVY', 'RDOACT']
        self.description.addItems(descriptions)
        self.description.setCurrentIndex(1)

    def setPhenomena(self, text='OBSC'):
        self.phenomenon.clear()

        if text == 'SEV':
            phenomena = ['TURB', 'ICE', 'ICE (FZRA)', 'MTW']
        elif text == 'HVY':
            phenomena = ['DS', 'SS']
        elif text == 'RDOACT':
            phenomena = ['CLD']
        else:
            phenomena = ['TS', 'TSGR']

        self.phenomenon.addItems(phenomena)

    def setFcstOrObs(self):
        observations = ['FCST', 'OBS']
        self.comeFrom.addItems(observations)

    def setFlightLevelFormat(self, text):
        self.format.clear()

        if text in ['CB', 'TCU', 'TS', 'TSGR']:
            formats = ['', 'TOP', 'ABV', 'SFC', 'TOP ABV']
            self.format.addItems(formats)
            self.format.setCurrentIndex(self.format.findText('TOP'))
        else:
            formats = ['', 'ABV', 'BLW', 'SFC']
            self.format.addItems(formats)
            self.format.setCurrentIndex(-1)

    def hasAcceptableInput(self):
        mustRequired = [
            self.beginningTime.hasAcceptableInput(),
            self.endingTime.hasAcceptableInput(),
            self.sequence.hasAcceptableInput(),
        ]

        if self.comeFrom.currentText() == 'OBS':
            mustRequired.append(self.observedTime.hasAcceptableInput())

        if self.base.isEnabled():
            mustRequired.append(self.base.hasAcceptableInput())

        if self.top.isEnabled():
            mustRequired.append(self.top.hasAcceptableInput())

        if self.hasForecastMode():
            mustRequired.append(self.forecastTime.hasAcceptableInput())
        else:
            mustRequired.append(self.moveState())

        return all(mustRequired)

    def hazard(self):
        items = [self.description.currentText(), self.phenomenon.currentText()]
        text = ' '.join(items) if all(items) else ''
        return text

    def message(self):
        fir = conf.firName
        hazard = self.hazard()
        observation = self.observationText()
        flightLevel = self.flightLevel()
        moveState = self.moveState()
        intensityChange = self.intensityChange.currentText()

        items = [fir, hazard, observation, '{location}', flightLevel]

        if self.hasForecastMode():
            forecast = self.forecastText()
            items += [intensityChange, forecast, '{forecastLocation}']
        else:
            items += [moveState, intensityChange]

        content = ' '.join(filter(None, items))
        return '\n'.join([self.firstLine(), content])

    def clear(self):
        super().clear()
        self.description.setCurrentIndex(1)
        self.format.setCurrentIndex(1)
        self.intensityChange.setCurrentIndex(0)
        self.forecastTime.setEnabled(False)
        self.forecastTimeLabel.setEnabled(False)


class SigmetTyphoon(ObservationMixin, ForecastMixin, MovementMixin, AdvisoryMixin, BaseSigmet, Ui_sigmet_typhoon.Ui_Editor):

    circleChanged = pyqtSignal(dict)

    def __init__(self, parent):
        super().__init__(parent)
        self.setPhenomena()
        self.setFcstOrObs()
        self.advisoryParser = TyphoonAdvisoryParser

        # testStr = (
        #     "TC ADVISORY\n"
        #     "DTG: 20220702/0600Z\n"
        #     "TCAC: TOKYO\n"
        #     "TC: CHABA\n"
        #     "ADVISORY NR: 2022/14 \n"
        #     "PSN: 02/0600Z N2110 E11120 \n"
        #     "CB: WI N1755 E11105 - N1955 E10840 - N2220 E11205 - N2110 E11330 - N1905 E11230 - N1755 E11105 TOP FL530\n"
        #     "MOV: NNW 07KT\n"
        #     "INTST CHANGE: WKN\n"
        #     "C: 965HPA\n"
        #     "MAX WIND: 70KT\n"
        #     "FCST PSN +6 HR: 02/1200Z N2155 E11050\n"
        #     "FCST MAX WIND +6 HR: 60KT\n"
        #     "FCST PSN +12 HR: 02/1800Z N2235 E11010\n"
        #     "FCST MAX WIND +12 HR: 45KT\n"
        #     "FCST PSN +18 HR: 03/0000Z N2310 E11000\n"
        #     "FCST MAX WIND +18 HR: NIL\n"
        #     "FCST PSN +24 HR: 03/0600Z N2340 E10955\n"
        #     "FCST MAX WIND +24 HR: NIL \n"
        #     "RMK: NIL\n"
        #     "NXT MSG: 20220702/1200Z="
        # )
        # self.text.setText(testStr)

    def bindSignal(self):
        super().bindSignal()
        self.currentLatitude.editingFinished.connect(self.handleCircleChange)
        self.currentLongitude.editingFinished.connect(self.handleCircleChange)
        self.forecastLatitude.editingFinished.connect(self.handleCircleChange)
        self.forecastLongitude.editingFinished.connect(self.handleCircleChange)
        self.radius.textEdited.connect(self.handleCircleChange)

        self.currentLatitude.textChanged.connect(self.updateForecastPosition)
        self.currentLongitude.textChanged.connect(self.updateForecastPosition)
        self.speed.textEdited.connect(self.updateForecastPosition)
        self.direction.currentTextChanged.connect(self.updateForecastPosition)
        self.forecastTime.textChanged.connect(self.updateForecastPosition)
        self.beginningTime.textEdited.connect(self.updateForecastPosition)
        self.observedTime.textEdited.connect(self.updateForecastPosition)
        self.endingTime.textChanged.connect(self.setForecastTime)

        self.currentLatitude.textEdited.connect(lambda: self.upperText(self.currentLatitude))
        self.currentLongitude.textEdited.connect(lambda: self.upperText(self.currentLongitude))
        self.forecastLatitude.textEdited.connect(lambda: self.upperText(self.forecastLatitude))
        self.forecastLongitude.textEdited.connect(lambda: self.upperText(self.forecastLongitude))
        self.name.textEdited.connect(lambda: self.upperText(self.name))

        self.currentLatitude.textChanged.connect(lambda: self.coloredText(self.currentLatitude))
        self.currentLongitude.textChanged.connect(lambda: self.coloredText(self.currentLongitude))
        self.radius.textEdited.connect(lambda: self.coloredText(self.radius))
        self.top.textEdited.connect(lambda: self.coloredText(self.top))
        self.forecastLatitude.textChanged.connect(lambda: self.coloredText(self.forecastLatitude))
        self.forecastLongitude.textChanged.connect(lambda: self.coloredText(self.forecastLongitude))

    def setupValidator(self):
        super(SigmetTyphoon, self).setupValidator()
        latitude = QRegExpValidator(QRegExp(self.rules.latitude, Qt.CaseInsensitive))
        self.currentLatitude.setValidator(latitude)
        self.forecastLatitude.setValidator(latitude)

        longitude = QRegExpValidator(QRegExp(self.rules.longitude, Qt.CaseInsensitive))
        self.currentLongitude.setValidator(longitude)
        self.forecastLongitude.setValidator(longitude)

        self.top.setValidator(QIntValidator(100, 999, self.top))
        self.radius.setMaxLength(3)

        time = QRegExpValidator(QRegExp(self.rules.time))
        self.forecastTime.setValidator(time)

        self.radius.setValidator(QIntValidator(1, 999, self.radius))
        self.radius.setMaxLength(3)

        name = QRegExpValidator(QRegExp(r'[A-Za-z0-9-]+'))
        self.name.setValidator(name)
        self.name.setMaxLength(20)

    def setPhenomena(self, text='TC'):
        self.phenomenon.addItems(['TC'])

    def setFcstOrObs(self):
        observations = ['OBS', 'FCST']
        self.comeFrom.addItems(observations)

    def setTyphoonLocation(self, collections):
        if not collections['features']:
            return

        for feature in collections['features']:
            location = feature['properties']['location']
            if location == 'initial':
                longitude, latitude = self.currentLongitude, self.currentLatitude
                radius = feature['properties']['radius']
            else:
                longitude, latitude = self.forecastLongitude, self.forecastLatitude

            center = feature['geometry']['coordinates']
            if center:
                lon, lat = center
                lon, lat = decimalToDegree(lon, fmt='longitude'), decimalToDegree(lat)
                longitude.setText(lon)
                latitude.setText(lat)
            else:
                if longitude.hasAcceptableInput() and latitude.hasAcceptableInput():
                    longitude.clear()
                    latitude.clear()

        if radius:
            self.radius.setText(str(radius))
        else:
            self.radius.clear()

    def updateForecastPosition(self):
        mustRequired = [
            self.currentLatitude.hasAcceptableInput(),
            self.currentLongitude.hasAcceptableInput(),
            self.speed.hasAcceptableInput(),
            self.forecastTime.hasAcceptableInput(),
        ]

        anyRequired = [
            self.observedTime.hasAcceptableInput(),
            self.beginningTime.hasAcceptableInput(),
        ]

        if not (all(mustRequired) and any(anyRequired)):
            return

        movement = self.direction.currentText()

        if movement == 'STNR':
            self.forecastLatitude.clear()
            self.forecastLongitude.clear()
            return

        directions = {
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
        observedTime = self.observedTime.text() if self.observedTime.hasAcceptableInput() else ''
        beginningTime = self.beginningTime.text()[2:] if self.beginningTime.hasAcceptableInput() else ''
        fcstTime = self.forecastTime.text()

        time = self.moveTime(observedTime or beginningTime, fcstTime).seconds
        degree = directions[movement]
        speed = self.speed.text()
        latitude = self.currentLatitude.text()
        longitude = self.currentLongitude.text()

        forecastLatitude, forecastLongitude = calcPosition(latitude, longitude, speed, time, degree)
        self.forecastLatitude.setText(forecastLatitude)
        self.forecastLongitude.setText(forecastLongitude)

        self.handleCircleChange()

    def autoFill(self):
        super().autoFill()
        height = self.parser.height()
        if height:
            self.top.setText(height)

        intensity = self.parser.intensity()
        if intensity:
            self.intensityChange.setCurrentIndex(self.intensityChange.findText(intensity))

        radius = self.parser.radius()
        if radius:
            self.radius.setText(str(radius))

        features = self.parser.location(self.initial.currentText())
        if features and 'geometry' in features:
            center = features['geometry']['coordinates']
            if center:
                lon, lat = center
                lon, lat = decimalToDegree(lon, fmt='longitude'), decimalToDegree(lat)
                self.currentLongitude.setText(lon)
                self.currentLatitude.setText(lat)

        features = self.parser.location(self.final.currentText())
        if features and 'geometry' in features:
            center = features['geometry']['coordinates']
            if center:
                lon, lat = center
                lon, lat = decimalToDegree(lon, fmt='longitude'), decimalToDegree(lat)
                self.forecastLongitude.setText(lon)
                self.forecastLatitude.setText(lat)
                self.finalPositionGroup.setEnabled(True)
            else:
                self.forecastLongitude.clear()
                self.forecastLatitude.clear()
                self.finalPositionGroup.setEnabled(False)

        self.handleLocationChange()

    def handleLocationChange(self):
        collections = {
            'type': 'FeatureCollection',
            'features': []
        }
        locations = []

        # when in polygon mode, there is no final position, and the initial geometry is a polygon
        if not self.mode == 'polygon':
            initial = self.initial.currentText()
            if initial:
                feature = self.parser.location(initial)
                if 'geometry' in feature:
                    feature['properties']['location'] = 'initial'
                    feature['properties']['type'] = 'sketch'
                    locations.append(feature)

            final = self.final.currentText()
            if initial and final:
                feature = self.parser.location(final)
                if 'geometry' in feature:
                    feature['properties']['location'] = 'final'
                    feature['properties']['type'] = 'sketch'
                    locations.append(feature)

        for feature in locations:
            if self.radius.hasAcceptableInput():
                radius = int(self.radius.text())
            else:
                radius = 0
            feature['properties']['radius'] = radius

        properties = {
            'type': 'exterior',
            'location': 'initial'
        }

        route = self.parser.route()
        if route:
            features = {
                'geometry': route,
                'properties': properties
            }
            locations.append(features)

        polygon = self.parser.polygon()
        if polygon:
            if self.mode == 'polygon':
                properties = {
                    'type': 'sketch',
                    'location': 'initial'
                }

            features = {
                'geometry': polygon,
                'properties': properties
            }
            locations.append(features)

        collections['features'] = locations
        self.locationChanged.emit(collections)

    def handleCircleChange(self):
        if self.mode == 'circle':
            collections = {
                'type': 'FeatureCollection',
                'features': []
            }
            initial = self.circle('initial')
            if initial:
                collections['features'].append(initial)
                final = self.circle('final')
                if final:
                    collections['features'].append(final)
            self.circleChanged.emit(collections)

    def hazard(self):
        items = [self.phenomenon.currentText(), self.name.text()]
        text = ' '.join(items) if all(items) else ''
        return text

    def circle(self, location):
        feature = {
            'type': 'Feature',
            'properties': {
                'location': location
            }
        }
        geometry = {}
        if location == 'initial':
            if self.currentLatitude.hasAcceptableInput() and self.currentLongitude.hasAcceptableInput():
                geometry = {
                    'type': 'Point',
                    'coordinates': (degreeToDecimal(self.currentLongitude.text()), degreeToDecimal(self.currentLatitude.text()))
                }
        else:
            if self.forecastLatitude.hasAcceptableInput() and self.forecastLongitude.hasAcceptableInput():
                geometry = {
                    'type': 'Point',
                    'coordinates': (degreeToDecimal(self.forecastLongitude.text()), degreeToDecimal(self.forecastLatitude.text()))
                }

        if geometry and self.radius.hasAcceptableInput():
            feature['geometry'] = geometry
            feature['properties']['radius'] = int(self.radius.text())
        else:
            feature = {}
        
        return feature

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

    def flightLevel(self):
        return 'TOP FL{}'.format(self.top.text())

    def message(self):
        fir = conf.firName
        hazard = self.hazard()
        position = 'PSN {latitude} {Longitude} CB {observation}'.format(
            latitude=self.currentLatitude.text(),
            Longitude=self.currentLongitude.text(),
            observation=self.observationText()
        )
        flightLevel = self.flightLevel()
        moveState = self.moveState()
        intensityChange = self.intensityChange.currentText()
        forecastPosition = self.forecastPosition()

        if self.mode == 'circle':
            location = 'WI {radius}{unit} OF TC CENTRE'.format(
                radius=int(self.radius.text()),
                unit='KM'
            )
        else:
            location = '{location}'

        items = [fir, hazard, position, location, flightLevel]

        if forecastPosition:
            items += [intensityChange, forecastPosition]
        else:
            items += [moveState, intensityChange]

        content = ' '.join(filter(None, items))
        return '\n'.join([self.firstLine(), content])

    def hasAcceptableInput(self):
        mustRequired = [
            self.beginningTime.hasAcceptableInput(),
            self.endingTime.hasAcceptableInput(),
            self.sequence.hasAcceptableInput(),
            self.name.text(),
            self.currentLatitude.hasAcceptableInput(),
            self.currentLongitude.hasAcceptableInput(),
            self.top.hasAcceptableInput()
        ]

        if self.mode == 'circle':
            mustRequired.append(self.radius.hasAcceptableInput())

        if self.hasForecastMode():
            mustRequired.append(self.forecastTime.hasAcceptableInput() and self.forecastLatitude.hasAcceptableInput() and self.forecastLongitude.hasAcceptableInput())
        else:
            mustRequired.append(self.moveState())

        if self.comeFrom.currentText() == 'OBS':
            mustRequired.append(self.observedTime.hasAcceptableInput())

        return all(mustRequired)

    def clear(self):
        super().clear()
        self.name.clear()
        self.top.clear()
        self.forecastTime.clear()
        self.forecastLatitude.clear()
        self.forecastLongitude.clear()
        self.intensityChange.setCurrentIndex(0)


class SigmetAsh(ObservationMixin, ForecastMixin, FlightLevelMixin, MovementMixin, AdvisoryMixin, BaseSigmet, Ui_sigmet_ash.Ui_Editor):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPhenomena()
        self.setFcstOrObs()
        self.advisoryParser = AshAdvisoryParser

        # testStr = (
        #     "FVFE01 RJTD 142100\n"
        #     "VA ADVISORY\n"
        #     "DTG: 20210814/2100Z\n"
        #     "VAAC: TOKYO\n"
        #     "VOLCANO: FUKUTOKU-OKA-NO-BA 284130\n"
        #     "PSN: N2417 E14129\n"
        #     "AREA: JAPAN\n"
        #     "SUMMIT ELEV: -29M\n"
        #     "ADVISORY NR: 2021/16\n"
        #     "INFO SOURCE: HIMAWARI-8\n"
        #     "AVIATION COLOUR CODE: NIL\n"
        #     "ERUPTION DETAILS: VA EMISSIONS CONTINUING\n"
        #     "OBS VA DTG: 14/2020Z\n"
        #     "OBS VA CLD: SFC/FL480 N2433 E14132 - N2411 E14137 - N2106 E13408 -\n"
        #     "N2030 E12501 - N1829 E11931 - N2032 E11751 - N2342 E12603 - N2314\n"
        #     "E13222 MOV W 55KT\n"
        #     "FCST VA CLD +6 HR: 15/0220Z SFC/FL510 N2533 E14014 - N2412 E14141 -\n"
        #     "N2214 E13836 - N2050 E13001 - N2008 E12142 - N1633 E11431 - N1832\n"
        #     "E11203 - N2402 E12019 - N2355 E13843\n"
        #     "FCST VA CLD +12 HR: 15/0820Z SFC/FL520 N2608 E13902 - N2409 E14145 -\n"
        #     "N2054 E13813 - N2019 E11914 - N1426 E10847 - N1633 E10627 - N2334\n"
        #     "E11717 - N2504 E12425 - N2314 E13600\n"
        #     "FCST VA CLD +18 HR: 15/1420Z SFC/FL530 N2659 E13836 - N2416 E14148 -\n"
        #     "N1936 E13735 - N2050 E12525 - N1846 E11503 - N1134 E10322 - N1259\n"
        #     "E10041 - N2042 E11014 - N2524 E12436 - N2352 E13446\n"
        #     "RMK: NIL\n"
        #     "NXT ADVISORY: 20210815/0000Z="
        # )
        # self.text.setText(testStr)

    def bindSignal(self):
        super().bindSignal()
        self.currentLatitude.textEdited.connect(lambda: self.upperText(self.currentLatitude))
        self.currentLongitude.textEdited.connect(lambda: self.upperText(self.currentLongitude))
        self.name.textEdited.connect(lambda: self.upperText(self.name))

        self.currentLatitude.textEdited.connect(lambda: self.coloredText(self.currentLatitude))
        self.currentLongitude.textEdited.connect(lambda: self.coloredText(self.currentLongitude))

        self.phenomenon.currentTextChanged.connect(self.setEruptionOrCloud)

    def setupValidator(self):
        super(SigmetAsh, self).setupValidator()
        latitude = QRegExpValidator(QRegExp(self.rules.latitude, Qt.CaseInsensitive))
        self.currentLatitude.setValidator(latitude)

        longitude = QRegExpValidator(QRegExp(self.rules.longitude, Qt.CaseInsensitive))
        self.currentLongitude.setValidator(longitude)

        self.speed.setValidator(QIntValidator(1, 200, self.speed))
        self.speed.setMaxLength(3)

        name = QRegExpValidator(QRegExp(r'[A-Za-z0-9-]+'))
        self.name.setValidator(name)
        self.name.setMaxLength(20)

    def setPhenomena(self, text='ERUPTION'):
        self.phenomenon.addItems(['ERUPTION', 'CLD'])

    def setFcstOrObs(self):
        observations = ['FCST', 'OBS']
        self.comeFrom.addItems(observations)

    def setEruptionOrCloud(self, text='ERUPTION'):
        enbaled = text == 'ERUPTION'
        self.name.setEnabled(enbaled)
        self.nameLabel.setEnabled(enbaled)
        self.currentLatitude.setEnabled(enbaled)
        self.currentLatitudeLabel.setEnabled(enbaled)
        self.currentLongitude.setEnabled(enbaled)
        self.currentLongitudeLabel.setEnabled(enbaled)
        self.contentChanged.emit()

    def autoFill(self):
        super().autoFill()
        position = self.parser.position()
        if position:
            lat, lon = position
            self.currentLatitude.setText(lat)
            self.currentLongitude.setText(lon)

        initial = self.initial.currentText()
        features = self.parser.location(initial)
        if features and 'flightLevel' in features['properties']:
            flightLevel = features['properties']['flightLevel']
            pattern = re.compile(r'\d+')
            if '/' in flightLevel:
                base, top = flightLevel.split('/')
                m = pattern.search(base)
                if m:
                    self.base.setText(m.group())
                else:
                    self.format.setCurrentIndex(self.format.findText(base))
            else:
                top = flightLevel

            m = pattern.search(top)
            if m:
                self.top.setText(m.group())

        self.handleLocationChange()

    def handleLocationChange(self):
        collections = {
            'type': 'FeatureCollection',
            'features': []
        }
        locations = []

        initial = self.initial.currentText()
        if initial:
            feature = self.parser.location(initial)
            if 'geometry' in feature:
                feature['properties']['location'] = 'initial'
                feature['properties']['type'] = 'sketch'
                locations.append(feature)

        final = self.final.currentText()
        if initial and final:
            feature = self.parser.location(final)
            if 'geometry' in feature:
                feature['properties']['location'] = 'final'
                feature['properties']['type'] = 'sketch'
                locations.append(feature)

        collections['features'] = locations
        self.locationChanged.emit(collections)

    def hazard(self):
        items = ['VA', self.phenomenon.currentText()]
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

        if self.comeFrom.currentText() == 'OBS':
            mustRequired.append(self.observedTime.hasAcceptableInput())

        if self.base.isEnabled():
            mustRequired.append(self.base.hasAcceptableInput())

        if self.top.isEnabled():
            mustRequired.append(self.top.hasAcceptableInput())

        if self.hasForecastMode():
            mustRequired.append(self.forecastTime.hasAcceptableInput())
        else:
            mustRequired.append(self.moveState())

        if self.currentLongitude.isEnabled() and self.currentLatitude.isEnabled():
            mustRequired.append(self.currentLongitude.hasAcceptableInput())
            mustRequired.append(self.currentLatitude.hasAcceptableInput())

        return all(mustRequired)

    def message(self):
        fir = conf.firName
        hazard = self.hazard()
        observation = self.observationText()
        flightLevel = self.flightLevel()
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

        items = [fir, hazard, position, '{location}', flightLevel]
        if self.hasForecastMode():
            forecast = self.forecastText()
            items += [forecast, '{forecastLocation}']

        if self.hasForecastMode():
            forecast = self.forecastText()
            items += [intensityChange, forecast, '{forecastLocation}']
        else:
            items += [moveState, intensityChange]

        content = ' '.join(filter(None, items))
        return '\n'.join([self.firstLine(), content])

    def clear(self):
        super().clear()
        self.name.clear()
        self.phenomenon.setCurrentIndex(0)
        self.format.setCurrentIndex(-1)
        self.intensityChange.setCurrentIndex(0)
        self.currentLatitude.clear()
        self.currentLongitude.clear()


class AirmetGeneral(SigmetGeneral):

    def setPhenomenaDescription(self):
        descriptions = ['ISOL', 'OCNL', 'FRQ', 'MOD']
        self.description.addItems(descriptions)

    def setPhenomena(self, text='ISOL'):
        self.phenomenon.clear()

        if text == 'MOD':
            phenomena = ['TURB', 'ICE', 'MTW']
        elif text == 'FRQ':
            phenomena = ['CB', 'TCU']
        else:
            phenomena = ['CB', 'TCU', 'TS', 'TSGR']

        self.phenomenon.addItems(phenomena)

    def setupValidator(self):
        super(AirmetGeneral, self).setupValidator()
        self.base.setValidator(QIntValidator(1, 100, self.base))
        self.top.setValidator(QIntValidator(1, 150, self.top))
        self.base.setMaxLength(3)
        self.top.setMaxLength(3)


class SigmetCancel(BaseSigmet, Ui_sigmet_cancel.Ui_Editor):

    def bindSignal(self):
        super().bindSignal()
        self.cancelSequence.lineEdit().textEdited.connect(lambda: self.upperText(self.cancelSequence.lineEdit()))

        self.cancelSequence.lineEdit().textChanged.connect(lambda: self.coloredText(self.cancelSequence.lineEdit()))
        self.cancelBeginningTime.textChanged.connect(lambda: self.coloredText(self.cancelBeginningTime))
        self.cancelEndingTime.textChanged.connect(lambda: self.coloredText(self.cancelEndingTime))

        self.cancelBeginningTime.textChanged.connect(self.syncValidsTime)
        self.cancelEndingTime.textChanged.connect(self.syncValidsTime)
        self.cancelSequence.currentTextChanged.connect(self.setValids)
        self.cancelSequence.currentIndexChanged.connect(self.setValids)

    def setupValidator(self):
        super(SigmetCancel, self).setupValidator()
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
        fir = conf.firName
        cancel = 'CNL {} {} {}/{}'.format(
            self.parent.reportType(),
            self.cancelSequence.currentText().strip(),
            self.cancelBeginningTime.text(),
            self.cancelEndingTime.text()
        )
        items = [fir, cancel]
        content = ' '.join(filter(None, items))
        return '\n'.join([self.firstLine(), content])

    def syncValidsTime(self):
        if self.cancelEndingTime.hasAcceptableInput():
            endingText = self.cancelEndingTime.text()
            self.endingTime.setText(endingText)

        if self.cancelBeginningTime.hasAcceptableInput():
            beginningText = self.cancelBeginningTime.text()
            start = parseTime(beginningText)
            beginning, _ = self.periodTime()

            if beginning < start and start - datetime.datetime.utcnow() < datetime.timedelta(hours=12):
                beginning = start

            if beginning.strftime('%d%H%M') == self.endingTime.text():
                beginning = beginning - datetime.timedelta(minutes=10)

            self.beginningTime.setText(beginning.strftime('%d%H%M'))

    def componentUpdate(self):
        self.prevs = []
        sigmets = context.message.sigmets(type=self.type())

        for sig in sigmets:
            parser = sig.parser()
            sequence = parser.sequence(), parser.validTime()
            self.prevs.append(sequence)

        sequences = [s[0] for s in self.prevs]
        self.cancelSequence.clear()
        self.cancelSequence.addItems(sequences)

    def setValids(self, sequence):
        valid = self.findValid(sequence)
        if valid:
            begin, end = valid.split('/')
            self.cancelBeginningTime.setText(begin)
            self.cancelEndingTime.setText(end)
            self.syncValidsTime()
        else:
            self.cancelBeginningTime.clear()
            self.cancelEndingTime.clear()

    def findValid(self, sequence):
        if isinstance(sequence, int):
            try:
                return self.prevs[sequence][1]
            except:
                pass
        else:
            for seq, valid in self.prevs:
                if seq == sequence:
                    return valid


class SigmetCustom(BaseSigmet, Ui_sigmet_custom.Ui_Editor):

    def __init__(self, parent):
        super().__init__(parent)
        self.setupApiSign()
        self.upperTextEdit()

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
            cursor.movePosition(QTextCursor.Left, QTextCursor.MoveAnchor, len(text) - pos)
            self.text.setTextCursor(cursor)

    def upperTextEdit(self):
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
        fir = conf.firName
        items = [fir, self.text.toPlainText().strip()]
        content = ' '.join(filter(None, items))
        return '\n'.join([self.firstLine(), content])

    def componentUpdate(self):
        self.setupPlaceholder()
        self.updateText()

    def setupApiSign(self):
        pixmap = QPixmap(':/api.png')
        self.apiSign = QLabel(self)
        self.apiSign.setPixmap(pixmap)
        self.apiSign.setMask(pixmap.mask())
        self.apiSign.adjustSize()
        self.apiSign.hide()

    def setupPlaceholder(self):
        speedUnit = 'KT' if context.environ.unit() == 'imperial' else 'KMH'
        lengthUnit = 'NM' if context.environ.unit() == 'imperial' else 'KM'
        tips = {
            'WS': 'EMBD TS FCST N OF N2000 TOP FL360 MOV N 25{} NC'.format(speedUnit),
            'WC': 'TC YAGI PSN N2706 W07306 CB OBS AT 1600Z WI 300{} OF TC CENTRE TOP FL420 NC\nFCST AT 2200Z TC CENTRE N2740 W07345'.format(lengthUnit),
            'WV': 'VA ERUPTION MT ASHVAL PSN S1500 E07348 VA CLD\nOBS AT 1100Z APRX 50{} WID LINE BTN S1500 E07348 - S1530 E07642 FL310/450 MOV ESE 65{}\nFCST AT 1700Z APRX 50{} WID LINE BTN S1506 E07500 - S1518 E08112 - S1712 E08330'.format(lengthUnit, speedUnit, lengthUnit),
            'WA': 'MOD MTW OBS AT 1205Z N4200 E11000 FL080 STNR NC'
        }
        tip = tips[self.type()]
        self.text.setPlaceholderText(tip)

    def loadLocalDatabase(self):
        with db.session() as session:
            last = session.query(Sigmet).filter(Sigmet.type == self.type(), ~Sigmet.text.contains('CNL')).order_by(Sigmet.created.desc()).first()

        if last:
            parser = last.parser()
            return 'database', parser.content()

    def loadNotification(self):
        parser = context.notification.sigmet.parser()
        if parser and self.type() == parser.type():
            return 'notification', parser.content()

    def updateText(self):
        rv = self.loadNotification() or self.loadLocalDatabase()
        if rv:
            source, message = rv
            fir = conf.firName or ''
            text = message.replace(fir, '').replace('=', '').strip()
            self.setText(text)

            if hasattr(self, 'apiSign'):
                if source == 'notification':
                    self.apiSign.show()
                else:
                    self.apiSign.hide()
        else:
            self.text.clear()
    
    def setText(self, message):
        self.text.setText(message)
        self.text.moveCursor(QTextCursor.End)

    def resizeEvent(self, event):
        self.apiSign.move(self.width() - 43, 80)
        super(SigmetCustom, self).resizeEvent(event)
