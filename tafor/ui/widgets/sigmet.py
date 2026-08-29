import re
import logging
import datetime

from itertools import cycle

from PyQt5.QtGui import QRegExpValidator, QIntValidator, QTextCharFormat, QTextCursor, QFont, QPixmap, QIcon
from PyQt5.QtCore import Qt, QRegExp, QCoreApplication, pyqtSignal
from PyQt5.QtWidgets import QWidget, QLabel, QLineEdit, QToolButton

from tafor.core.parsers.base import Pattern
from tafor.core.parsers.sigmet import AshAdvisoryParser, TyphoonAdvisoryParser
from tafor.core.repositories import SigmetFilter, SigmetRepository
from tafor.core.sigmet import (SigmetAshState, SigmetCancelState, SigmetCustomState, SigmetGeneralState,
    SigmetTyphoonState, SigmetValidator)
from tafor.core.sigmet.issuance import adjustCancelBeginning, nextSequence, validPeriod
from tafor.core.geometry.coordinate import decimalToDegree
from tafor.core.utils.time import parseTime
from tafor.core.utils.common import iconPath
from tafor.ui.qt import Ui_sigmet_ash, Ui_sigmet_cancel, Ui_sigmet_custom, Ui_sigmet_general, Ui_sigmet_typhoon
from tafor.ui.widgets.taf import SegmentMixin

logger = logging.getLogger('tafor.sigmet.information')


def _translate(code, **kwargs):
    messages = {
        SigmetValidator.START_TOO_FAR: QCoreApplication.translate(
            'Editor', 'Start time cannot be less than the current time'),
        SigmetValidator.END_NOT_GREATER: QCoreApplication.translate(
            'Editor', 'Ending time must be greater than the beginning time'),
        SigmetValidator.PERIOD_TOO_LONG: QCoreApplication.translate(
            'Editor', 'Valid period more than {} hours').format(kwargs.get('hours', '')),
        SigmetValidator.FLIGHT_LEVEL_INVALID: QCoreApplication.translate(
            'Editor', 'The top flight level needs to be greater than the base flight level'),
    }
    return messages.get(code, code)


class BaseSigmet(SegmentMixin, QWidget):

    contentChanged = pyqtSignal()

    # Concrete classes declare their field-group parts here
    parts = ()

    def __init__(self, parent, conf=None, context=None, database=None):
        super().__init__()
        self.complete = False
        self.durations = None
        self.rules = Pattern()
        self.parent = parent
        self.conf = conf
        self.context = context
        self.database = database
        self.span = 4
        self.forecastMode = False
        self.mode = 'polygon'
        self.state = None

    def initialize(self):
        self.switchButton = QToolButton(self)
        self.switchButton.hide()
        self.headingGroup.setMinimumWidth(77 * 3 + 32)
        self.sigmetRepository = SigmetRepository(self.database)
        self.parts = [part(self) for part in self.parts]
        self.initState()
        self.setupFont()
        self.setupMainElementWidth()
        self.setupValidator()
        self.bindSignal()

    def part(self, cls):
        for part in self.parts:
            if isinstance(part, cls):
                return part

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
        self.updateSequence()
        self.updatePeriodTime()
        self.updateDurations()
        self.componentUpdate()

    def bindSignal(self):
        self.beginningTime.textChanged.connect(self.updateDurations)
        self.endingTime.textChanged.connect(self.updateDurations)
        self.beginningTime.editingFinished.connect(self.validatePeriod)
        self.endingTime.editingFinished.connect(self.validatePeriod)

        self.defaultSignal()

        for part in self.parts:
            part.bindSignal()

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
        return validPeriod(self.type(), self.span, self.time)

    def validatePeriod(self):
        error = SigmetValidator.validatePeriod(self.durations, self.span)
        if error:
            code = error[0] if isinstance(error, tuple) else error
            if code == SigmetValidator.START_TOO_FAR:
                self.beginningTime.clear()
            elif code in (SigmetValidator.END_NOT_GREATER, SigmetValidator.PERIOD_TOO_LONG):
                self.endingTime.clear()
            self.context.flash.editor('sigmet', _translate(error))

    def syncToState(self):
        self.state.header.area = self.conf.firName.split()[0] if self.conf.firName else ''
        self.state.header.sign = self.parent.reportType()
        self.state.header.sequence = self.sequence.text()
        self.state.header.beginningTime = self.beginningTime.text()
        self.state.header.endingTime = self.endingTime.text()
        self.state.header.icao = self.conf.airport

        for part in self.parts:
            part.syncToState()

    def validate(self):
        self.validatePeriod()

    def setSpan(self, span):
        self.span = span
        self.initState()

    def setOverlapMode(self, mode):
        if mode == 'final':
            observation = self.part(ObservationPart)
            if observation:
                observation.setSource('OBS')

        for part in self.parts:
            part.setOverlapMode(mode)

    def setLocationMode(self, mode):
        self.mode = mode
        self.state.mode = mode

        for part in self.parts:
            part.setLocationMode(mode)

    def setupValidator(self):
        date = QRegExpValidator(QRegExp(self.rules.date))
        self.beginningTime.setValidator(date)
        self.endingTime.setValidator(date)

        sequence = QRegExpValidator(QRegExp(self.rules.sequence, Qt.CaseInsensitive))
        self.sequence.setValidator(sequence)

        for part in self.parts:
            part.setupValidator()

    def updatePeriodTime(self):
        beginningTime, endingTime = self.periodTime()
        self.beginningTime.setText(beginningTime.strftime('%d%H%M'))
        self.endingTime.setText(endingTime.strftime('%d%H%M'))

    def updateSequence(self):
        sigmets = self.sigmetRepository.countToday(self.type())
        count = nextSequence([sig.heading for sig in sigmets], datetime.datetime.utcnow())
        self.sequence.setText(str(count))

    def hasAcceptableInput(self):
        return self.state.isAcceptable()

    def hasForecastMode(self):
        return self.forecastMode

    def type(self):
        return self.parent.type

    def firstLine(self):
        return self.state.header.compose()

    def clear(self):
        self.durations = None
        self.state.clear()
        self.beginningTime.clear()
        self.endingTime.clear()
        self.sequence.clear()

        for part in self.parts:
            part.clear()


class SigmetPart:
    """Field-group controller bound to a SIGMET editor widget.

    Required widget names fail fast at construction; optional widgets
    default to None and are only probed inside the part.
    """

    widgets = ()
    optional = ()

    def __init__(self, widget):
        missing = [name for name in self.widgets if not hasattr(widget, name)]
        if missing:
            raise TypeError('{} requires widgets missing on {}: {}'.format(
                type(self).__name__, type(widget).__name__, ', '.join(missing)))

        self.widget = widget
        for name in self.widgets:
            setattr(self, name, getattr(widget, name))
        for name in self.optional:
            setattr(self, name, getattr(widget, name, None))

    def bindSignal(self):
        pass

    def syncToState(self):
        pass

    def setupValidator(self):
        pass

    def clear(self):
        pass

    def setOverlapMode(self, mode):
        pass

    def setLocationMode(self, mode):
        pass


class FlightLevelPart(SigmetPart):

    widgets = ('format', 'base', 'top', 'baseLabel', 'topLabel')

    def bindSignal(self):
        self.format.currentTextChanged.connect(self.setFlightLevel)
        self.format.currentTextChanged.connect(self.widget.syncToState)
        self.base.textChanged.connect(self.widget.syncToState)
        self.top.textChanged.connect(self.widget.syncToState)
        self.base.editingFinished.connect(lambda: self.validateBaseTop(self.base))
        self.top.editingFinished.connect(lambda: self.validateBaseTop(self.top))

    def syncToState(self):
        self.widget.state.flightLevelFormat = self.format.currentText()
        self.widget.state.flightLevelBase = self.base.text()
        self.widget.state.flightLevelTop = self.top.text()

    def setupValidator(self):
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

        error = SigmetValidator.validateFlightLevel(self.base.text(), self.top.text())
        if error:
            line.clear()
            self.widget.context.flash.editor('sigmet', _translate(error))

    def clear(self):
        self.top.clear()
        self.base.clear()


class AirmetFlightLevelPart(FlightLevelPart):

    def setupValidator(self):
        self.base.setValidator(QIntValidator(1, 100, self.base))
        self.top.setValidator(QIntValidator(1, 150, self.top))
        self.base.setMaxLength(3)
        self.top.setMaxLength(3)


class MovementPart(SigmetPart):

    widgets = ('direction', 'speed', 'speedLabel')

    def bindSignal(self):
        self.direction.currentTextChanged.connect(self.setSpeed)
        self.direction.currentTextChanged.connect(self.widget.syncToState)
        self.speed.textChanged.connect(self.widget.syncToState)

    def syncToState(self):
        self.widget.state.direction = self.direction.currentText()
        self.widget.state.unit = self.widget.conf.units.sigmetSpeed
        self.widget.state.speed = self.speed.text() if self.speed.hasAcceptableInput() else ''

    def setupValidator(self):
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

    def clear(self):
        self.direction.setCurrentIndex(0)
        self.speed.clear()


class ObservationPart(SigmetPart):

    widgets = ('comeFrom', 'observedTime', 'observedTimeLabel', 'beginningTime')

    def bindSignal(self):
        self.comeFrom.currentTextChanged.connect(self.updateObservation)
        self.beginningTime.textChanged.connect(self.updateObservation)
        self.comeFrom.currentTextChanged.connect(self.widget.syncToState)
        self.observedTime.textChanged.connect(self.widget.syncToState)

    def syncToState(self):
        self.widget.state.comeFrom = self.comeFrom.currentText()
        self.widget.state.observedTime = self.observedTime.text() if self.observedTime.hasAcceptableInput() else ''

    def setupValidator(self):
        self.observedTime.setValidator(QRegExpValidator(QRegExp(self.widget.rules.time)))

    def setSource(self, source):
        """Switch the observation source ('OBS' / 'FCST')."""
        index = self.comeFrom.findText(source)
        if index >= 0:
            self.comeFrom.setCurrentIndex(index)

    def updateObservation(self):
        text = self.comeFrom.currentText()
        if text == 'OBS':
            self.observedTime.setText(self.beginningTime.text()[2:])
            self.observedTimeLabel.setText(QCoreApplication.translate('Editor', 'Observed Time'))
        else:
            self.observedTimeLabel.setText(QCoreApplication.translate('Editor', 'Forecast Time'))
            if self.beginningTime.text()[2:] == self.observedTime.text():
                self.observedTime.clear()

    def clear(self):
        self.observedTime.clear()
        self.comeFrom.setCurrentIndex(0)


class ForecastPart(SigmetPart):

    widgets = ('forecastTime', 'forecastTimeLabel')
    optional = ('finalPositionGroup',)

    def bindSignal(self):
        self.forecastTime.textChanged.connect(self.widget.syncToState)

    def syncToState(self):
        self.widget.state.forecastTime = self.forecastTime.text()

    def setupValidator(self):
        self.forecastTime.setValidator(QRegExpValidator(QRegExp(self.widget.rules.time)))

    def setForecastTime(self):
        if self.widget.durations is None or not self.widget.endingTime.text() or not self.forecastTime.isEnabled():
            return

        text = self.widget.endingTime.text()[2:]
        self.forecastTime.setText(text)

    def setOverlapMode(self, mode):
        if mode == 'final':
            self.forecastTime.setEnabled(True)
            self.forecastTimeLabel.setEnabled(True)
            self.setForecastTime()
            self.widget.forecastMode = True
            if self.finalPositionGroup is not None:
                self.finalPositionGroup.setEnabled(True)
        else:
            self.forecastTime.setEnabled(False)
            self.forecastTimeLabel.setEnabled(False)
            self.forecastTime.clear()
            self.widget.forecastMode = False
            if self.finalPositionGroup is not None:
                self.finalPositionGroup.setEnabled(False)
        self.widget.state.forecastMode = self.widget.forecastMode

    def clear(self):
        self.forecastTime.clear()


class AdvisoryImport(SigmetPart):
    """Import workflow for advisory messages: parse the text, fill the
    editor fields and publish sketch geometry via locationChanged."""

    widgets = ('switchButton', 'advisory', 'text', 'initial', 'final', 'name', 'main')

    def __init__(self, widget):
        super().__init__(widget)

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
        self.switchButton.clicked.connect(self.switchGroup)
        self.text.textChanged.connect(self.parseText)
        self.initial.currentTextChanged.connect(self.updateFinalOption)
        self.initial.currentTextChanged.connect(self.updateLocation)
        self.final.currentTextChanged.connect(self.updateLocation)

    def switchGroup(self):
        self.group = next(self.groupNames)
        if self.group == 'main':
            icon = iconPath('forward.png')
        else:
            icon = iconPath('back.png')

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
            self.parser = self.widget.advisoryParser(text)
            options = self.parser.availableLocations()
            self.initial.clear()
            self.initial.addItems(options)
            self.applyAdvisoryData()
            self.text.setStyleSheet('color: black')
        except Exception as e:
            self.widget.context.flash.editor('sigmet', QCoreApplication.translate('Editor', 'Advisory message can not be decoded'))
            self.text.setStyleSheet('color: grey')
            logger.error('Advisory message can not be decoded, {}, {}'.format(text, e))

    def applyAdvisoryData(self):
        name = self.parser.name()
        if name:
            self.name.setText(name)

        initial = self.initial.currentText()
        if 'OBS' in initial:
            self.widget.part(ObservationPart).setSource('OBS')

        if 'FCST' in initial:
            self.widget.part(ObservationPart).setSource('FCST')

        features = self.parser.location(initial)
        if features and 'time' in features['properties']:
            time = features['properties']['time']
            self.widget.observedTime.setText(time.strftime('%H%M'))

        features = self.parser.location(self.final.currentText())
        if features and 'time' in features['properties']:
            time = features['properties']['time']
            self.widget.forecastTime.setText(time.strftime('%H%M'))
            self.widget.forecastTime.setEnabled(True)
            self.widget.forecastTimeLabel.setEnabled(True)
        else:
            self.widget.forecastTime.setEnabled(False)
            self.widget.forecastTimeLabel.setEnabled(False)

        final = self.final.currentText()
        movement = self.parser.movement()
        if movement:
            self.widget.direction.setCurrentIndex(self.widget.direction.findText(movement))

            if not final and movement != 'STNR':
                speed = str(self.parser.speed())
                self.widget.speed.setText(speed)
            else:
                self.widget.speed.clear()

    def locationFeatures(self, initial, final=None):
        """Advisory locations tagged for the sketch canvas."""
        features = []
        if initial:
            feature = self.parser.location(initial)
            if 'geometry' in feature:
                feature['properties']['location'] = 'initial'
                feature['properties']['type'] = 'sketch'
                features.append(feature)

        if initial and final:
            feature = self.parser.location(final)
            if 'geometry' in feature:
                feature['properties']['location'] = 'final'
                feature['properties']['type'] = 'sketch'
                features.append(feature)

        return features

    def handleLocationChange(self):
        collections = {
            'type': 'FeatureCollection',
            'features': self.locationFeatures(self.initial.currentText(), self.final.currentText()),
        }
        self.widget.locationChanged.emit(collections)

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
            self.applyAdvisoryData()
        except Exception as e:
            logger.error('Auto fill location from advisory message failed, {}'.format(e))

    def setLocationMode(self, mode):
        if self.widget.mode in ['polygon', 'line', 'circle']:
            self.switchButton.show()
        else:
            self.switchButton.hide()
            if self.group == 'advisory':
                self.switchGroup()
                return

        self.updateVisibility()

    def clear(self):
        if self.group == 'advisory':
            self.group = next(self.groupNames)
            self.advisory.hide()
            self.main.show()

        self.text.clear()
        self.initial.clear()
        self.final.clear()
        self.parser = None


class TyphoonAdvisoryImport(AdvisoryImport):

    def applyAdvisoryData(self):
        super().applyAdvisoryData()

        height = self.parser.height()
        if height:
            self.widget.top.setText(height)

        intensity = self.parser.intensity()
        if intensity:
            self.widget.intensityChange.setCurrentIndex(self.widget.intensityChange.findText(intensity))

        radius = self.parser.radius()
        if radius:
            self.widget.radius.setText(str(radius))

        features = self.parser.location(self.initial.currentText())
        if features and 'geometry' in features:
            center = features['geometry']['coordinates']
            if center:
                lon, lat = center
                lon, lat = decimalToDegree(lon, fmt='longitude'), decimalToDegree(lat)
                self.widget.currentLongitude.setText(lon)
                self.widget.currentLatitude.setText(lat)

        features = self.parser.location(self.final.currentText())
        if features and 'geometry' in features:
            center = features['geometry']['coordinates']
            if center:
                lon, lat = center
                lon, lat = decimalToDegree(lon, fmt='longitude'), decimalToDegree(lat)
                self.widget.forecastLongitude.setText(lon)
                self.widget.forecastLatitude.setText(lat)
                self.widget.finalPositionGroup.setEnabled(True)
            else:
                self.widget.forecastLongitude.clear()
                self.widget.forecastLatitude.clear()
                self.widget.finalPositionGroup.setEnabled(False)

        self.handleLocationChange()

    def handleLocationChange(self):
        locations = []

        # when in polygon mode, there is no final position, and the initial geometry is a polygon
        if not self.widget.mode == 'polygon':
            locations += self.locationFeatures(self.initial.currentText(), self.final.currentText())

        for feature in locations:
            if self.widget.radius.hasAcceptableInput():
                radius = int(self.widget.radius.text())
            else:
                radius = 0
            feature['properties']['radius'] = radius

        properties = {
            'type': 'exterior',
            'location': 'initial'
        }

        route = self.parser.route()
        if route:
            locations.append({
                'geometry': route,
                'properties': properties
            })

        polygon = self.parser.polygon()
        if polygon:
            if self.widget.mode == 'polygon':
                properties = {
                    'type': 'sketch',
                    'location': 'initial'
                }

            locations.append({
                'geometry': polygon,
                'properties': properties
            })

        collections = {
            'type': 'FeatureCollection',
            'features': locations
        }
        self.widget.locationChanged.emit(collections)


class AshAdvisoryImport(AdvisoryImport):

    def applyAdvisoryData(self):
        super().applyAdvisoryData()

        position = self.parser.position()
        if position:
            lat, lon = position
            self.widget.currentLatitude.setText(lat)
            self.widget.currentLongitude.setText(lon)

        initial = self.initial.currentText()
        features = self.parser.location(initial)
        if features and 'flightLevel' in features['properties']:
            flightLevel = features['properties']['flightLevel']
            pattern = re.compile(r'\d+')
            if '/' in flightLevel:
                base, top = flightLevel.split('/')
                m = pattern.search(base)
                if m:
                    self.widget.base.setText(m.group())
                else:
                    self.widget.format.setCurrentIndex(self.widget.format.findText(base))
            else:
                top = flightLevel

            m = pattern.search(top)
            if m:
                self.widget.top.setText(m.group())

        self.handleLocationChange()


class SigmetGeneral(BaseSigmet, Ui_sigmet_general.Ui_Editor):

    parts = (ObservationPart, ForecastPart, FlightLevelPart, MovementPart)

    def __init__(self, parent=None, conf=None, context=None, database=None):
        super().__init__(parent, conf=conf, context=context, database=database)
        self.setupUi(self)
        self.state = SigmetGeneralState()
        self.initialize()
        self.setPhenomenaDescription()
        self.setPhenomena()
        self.setFcstOrObs()
        self.setFlightLevelFormat('TS')

    def bindSignal(self):
        super().bindSignal()
        self.description.currentTextChanged.connect(self.setPhenomena)
        self.phenomenon.currentTextChanged.connect(self.setFlightLevelFormat)
        self.description.currentTextChanged.connect(self.syncToState)
        self.phenomenon.currentTextChanged.connect(self.syncToState)
        self.intensityChange.currentTextChanged.connect(self.syncToState)

    def syncToState(self):
        super().syncToState()
        self.state.description = self.description.currentText()
        self.state.phenomenon = self.phenomenon.currentText()
        self.state.intensityChange = self.intensityChange.currentText()

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

    def message(self):
        return self.state.composeMessage(self.conf.firName)

    def clear(self):
        super().clear()
        self.description.setCurrentIndex(1)
        self.format.setCurrentIndex(1)
        self.intensityChange.setCurrentIndex(0)
        self.forecastTime.setEnabled(False)
        self.forecastTimeLabel.setEnabled(False)


class SigmetTyphoon(BaseSigmet, Ui_sigmet_typhoon.Ui_Editor):

    parts = (ObservationPart, ForecastPart, MovementPart, TyphoonAdvisoryImport)

    locationChanged = pyqtSignal(dict)
    circleChanged = pyqtSignal(dict)

    def __init__(self, parent, conf=None, context=None, database=None):
        super().__init__(parent, conf=conf, context=context, database=database)
        self.setupUi(self)
        self.state = SigmetTyphoonState()
        self.initialize()
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
        self.endingTime.textChanged.connect(self.part(ForecastPart).setForecastTime)

        self.phenomenon.currentTextChanged.connect(self.syncToState)
        self.name.textChanged.connect(self.syncToState)
        self.currentLatitude.textChanged.connect(self.syncToState)
        self.currentLongitude.textChanged.connect(self.syncToState)
        self.forecastLatitude.textChanged.connect(self.syncToState)
        self.forecastLongitude.textChanged.connect(self.syncToState)
        self.radius.textChanged.connect(self.syncToState)
        self.top.textChanged.connect(self.syncToState)
        self.intensityChange.currentTextChanged.connect(self.syncToState)

    def syncToState(self):
        super().syncToState()
        self.state.phenomenon = self.phenomenon.currentText()
        self.state.name = self.name.text()
        self.state.currentLatitude = self.currentLatitude.text() if self.currentLatitude.hasAcceptableInput() else ''
        self.state.currentLongitude = self.currentLongitude.text() if self.currentLongitude.hasAcceptableInput() else ''
        self.state.forecastLatitude = self.forecastLatitude.text() if self.forecastLatitude.hasAcceptableInput() else ''
        self.state.forecastLongitude = self.forecastLongitude.text() if self.forecastLongitude.hasAcceptableInput() else ''
        self.state.radius = self.radius.text() if self.radius.hasAcceptableInput() else ''
        self.state.top = self.top.text() if self.top.hasAcceptableInput() else ''
        self.state.intensityChange = self.intensityChange.currentText()
        self.state.mode = self.mode

    def setupValidator(self):
        super().setupValidator()
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
        positions = self.state.calcForecastPosition()
        if positions:
            forecastLatitude, forecastLongitude = positions
            self.forecastLatitude.setText(forecastLatitude)
            self.forecastLongitude.setText(forecastLongitude)
        else:
            self.forecastLatitude.clear()
            self.forecastLongitude.clear()
        self.handleCircleChange()

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

    def circle(self, location):
        return self.state.circleFeature(location)

    def message(self):
        self.state.forecastMode = self.hasForecastMode()
        return self.state.composeMessage(self.conf.firName)

    def clear(self):
        super().clear()
        self.name.clear()
        self.top.clear()
        self.forecastTime.clear()
        self.forecastLatitude.clear()
        self.forecastLongitude.clear()
        self.intensityChange.setCurrentIndex(0)


class SigmetAsh(BaseSigmet, Ui_sigmet_ash.Ui_Editor):

    parts = (ObservationPart, ForecastPart, FlightLevelPart, MovementPart, AshAdvisoryImport)

    locationChanged = pyqtSignal(dict)

    def __init__(self, parent=None, conf=None, context=None, database=None):
        super().__init__(parent, conf=conf, context=context, database=database)
        self.setupUi(self)
        self.state = SigmetAshState()
        self.initialize()
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
        self.phenomenon.currentTextChanged.connect(self.setEruptionOrCloud)
        self.phenomenon.currentTextChanged.connect(self.syncToState)
        self.name.textChanged.connect(self.syncToState)
        self.currentLatitude.textChanged.connect(self.syncToState)
        self.currentLongitude.textChanged.connect(self.syncToState)
        self.intensityChange.currentTextChanged.connect(self.syncToState)

    def syncToState(self):
        super().syncToState()
        self.state.phenomenon = self.phenomenon.currentText()
        self.state.name = self.name.text()
        self.state.currentLatitude = self.currentLatitude.text() if self.currentLatitude.hasAcceptableInput() else ''
        self.state.currentLongitude = self.currentLongitude.text() if self.currentLongitude.hasAcceptableInput() else ''
        self.state.intensityChange = self.intensityChange.currentText()
        self.state.isEruption = self.name.isEnabled()

    def setupValidator(self):
        super().setupValidator()
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
        enabled = text == 'ERUPTION'
        self.name.setEnabled(enabled)
        self.nameLabel.setEnabled(enabled)
        self.currentLatitude.setEnabled(enabled)
        self.currentLatitudeLabel.setEnabled(enabled)
        self.currentLongitude.setEnabled(enabled)
        self.currentLongitudeLabel.setEnabled(enabled)
        self.contentChanged.emit()

    def message(self):
        self.state.isEruption = self.name.isEnabled()
        self.state.forecastMode = self.hasForecastMode()
        return self.state.composeMessage(self.conf.firName)

    def clear(self):
        super().clear()
        self.name.clear()
        self.phenomenon.setCurrentIndex(0)
        self.format.setCurrentIndex(-1)
        self.intensityChange.setCurrentIndex(0)
        self.currentLatitude.clear()
        self.currentLongitude.clear()


class AirmetGeneral(SigmetGeneral):

    parts = (ObservationPart, ForecastPart, AirmetFlightLevelPart, MovementPart)

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


class SigmetCancel(BaseSigmet, Ui_sigmet_cancel.Ui_Editor):

    def __init__(self, parent, conf=None, context=None, database=None):
        super().__init__(parent, conf=conf, context=context, database=database)
        self.setupUi(self)
        self.state = SigmetCancelState()
        self.initialize()

    def bindSignal(self):
        super().bindSignal()
        self.cancelBeginningTime.textChanged.connect(self.syncValidsTime)
        self.cancelEndingTime.textChanged.connect(self.syncValidsTime)
        self.cancelSequence.currentTextChanged.connect(self.setValids)
        self.cancelSequence.currentIndexChanged.connect(self.setValids)
        self.cancelSequence.currentTextChanged.connect(self.syncToState)
        self.cancelBeginningTime.textChanged.connect(self.syncToState)
        self.cancelEndingTime.textChanged.connect(self.syncToState)

    def syncToState(self):
        super().syncToState()
        self.state.cancelSequence = self.cancelSequence.currentText().strip()
        self.state.cancelBeginningTime = self.cancelBeginningTime.text()
        self.state.cancelEndingTime = self.cancelEndingTime.text()

    def setupValidator(self):
        super().setupValidator()
        sequence = QRegExpValidator(QRegExp(self.rules.sequence, Qt.CaseInsensitive))
        self.cancelSequence.setValidator(sequence)

        date = QRegExpValidator(QRegExp(self.rules.date))
        self.cancelBeginningTime.setValidator(date)
        self.cancelEndingTime.setValidator(date)

    def message(self):
        return self.state.composeMessage(self.conf.firName)

    def syncValidsTime(self):
        if self.cancelEndingTime.hasAcceptableInput():
            endingText = self.cancelEndingTime.text()
            self.endingTime.setText(endingText)

        if self.cancelBeginningTime.hasAcceptableInput():
            start, _ = self.periodTime()
            beginning = adjustCancelBeginning(
                self.cancelBeginningTime.text(),
                start,
                self.endingTime.text(),
                datetime.datetime.utcnow(),
            )
            self.beginningTime.setText(beginning.strftime('%d%H%M'))

    def componentUpdate(self):
        self.prevs = []
        sigmets = self.context.current.filterSigmets(SigmetFilter(typeCode=self.type()))

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
            except (KeyError, IndexError):
                pass
        else:
            for seq, valid in self.prevs:
                if seq == sequence:
                    return valid


class SigmetCustom(BaseSigmet, Ui_sigmet_custom.Ui_Editor):

    def __init__(self, parent, conf=None, context=None, database=None):
        super().__init__(parent, conf=conf, context=context, database=database)
        self.setupUi(self)
        self.state = SigmetCustomState()
        self.initialize()
        self.setupApiSign()
        self.upperTextEdit()

    def bindSignal(self):
        super().bindSignal()
        self.text.textChanged.connect(self.filterText)
        self.text.textChanged.connect(lambda: self.contentChanged.emit())
        self.text.textChanged.connect(self.syncToState)

    def syncToState(self):
        super().syncToState()
        self.state.text = self.text.toPlainText().strip()

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

    def message(self):
        return self.state.composeMessage(self.conf.firName)

    def componentUpdate(self):
        self.setupPlaceholder()
        self.updateText()

    def setupApiSign(self):
        pixmap = QPixmap(iconPath('api.png'))
        self.apiSign = QLabel(self)
        self.apiSign.setPixmap(pixmap)
        self.apiSign.setMask(pixmap.mask())
        self.apiSign.adjustSize()
        self.apiSign.hide()

    def setupPlaceholder(self):
        tips = {
            'WS': 'EMBD TS FCST N OF N2000 TOP FL360 MOV N 25{} NC'.format(self.conf.units.sigmetSpeed),
            'WC': 'TC YAGI PSN N2706 W07306 CB OBS AT 1600Z WI 300{} OF TC CENTRE TOP FL420 NC\nFCST AT 2200Z TC CENTRE N2740 W07345'.format(self.conf.units.length),
            'WV': 'VA ERUPTION MT ASHVAL PSN S1500 E07348 VA CLD\nOBS AT 1100Z APRX 50{} WID LINE BTN S1500 E07348 - S1530 E07642 FL310/450 MOV ESE 65{}\nFCST AT 1700Z APRX 50{} WID LINE BTN S1506 E07500 - S1518 E08112 - S1712 E08330'.format(self.conf.units.length, self.conf.units.sigmetSpeed, self.conf.units.length),
            'WA': 'MOD MTW OBS AT 1205Z N4200 E11000 FL080 STNR NC'
        }
        tip = tips[self.type()]
        self.text.setPlaceholderText(tip)

    def loadLocalDatabase(self):
        last = self.sigmetRepository.latest(self.type())

        if last:
            parser = last.parser()
            return 'database', parser.content()

    def loadNotification(self):
        parser = self.context.notification.sigmet.parser()
        if parser and self.type() == parser.type():
            return 'notification', parser.content()

    def updateText(self):
        rv = self.loadNotification() or self.loadLocalDatabase()
        if rv:
            source, message = rv
            fir = self.conf.firName or ''
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
        super().resizeEvent(event)
