import re
import logging

from itertools import cycle

from PyQt5.QtGui import QRegExpValidator, QIntValidator, QTextCharFormat, QTextCursor, QFont, QPixmap, QIcon
from PyQt5.QtCore import Qt, QRegExp, QCoreApplication, QSignalBlocker, pyqtSignal
from PyQt5.QtWidgets import QComboBox, QWidget, QLabel, QLineEdit, QToolButton

from tafor.core.parsers.base import Pattern
from tafor.core.parsers.advisory import AshAdvisoryParser, TyphoonAdvisoryParser
from tafor.core.sigmet import (SigmetAshState, SigmetCancelState, SigmetCustomState, SigmetGeneralState,
    SigmetTyphoonState, SigmetFormValidator)
from tafor.core.sigmet.compose import adjustCancelBeginning, typhoonCircleFeature, validPeriod
from tafor.core.geometry import geojson
from tafor.core.geometry.coordinate import decimalToDegree
from tafor.core.utils.time import parseTime, utcnow
from tafor.core.utils.common import iconPath
from tafor.ui.qt import Ui_sigmet_ash, Ui_sigmet_cancel, Ui_sigmet_custom, Ui_sigmet_general, Ui_sigmet_typhoon
from tafor.ui.forms.base import TextFieldMixin
from tafor.ui.styles import invalidTextStyle, validTextStyle

logger = logging.getLogger('tafor.sigmet.information')


def _translate(code):
    messages = {
        SigmetFormValidator.START_TOO_FAR: QCoreApplication.translate(
            'Editor', 'Start time cannot be less than the current time'),
        SigmetFormValidator.END_NOT_GREATER: QCoreApplication.translate(
            'Editor', 'Ending time must be greater than the beginning time'),
        SigmetFormValidator.PERIOD_TOO_LONG: QCoreApplication.translate(
            'Editor', 'Valid period more than the permitted hours'),
        SigmetFormValidator.FLIGHT_LEVEL_INVALID: QCoreApplication.translate(
            'Editor', 'The top flight level needs to be greater than the base flight level'),
    }
    return messages.get(code, code)


class BaseSigmet(TextFieldMixin, QWidget):

    contentChanged = pyqtSignal()

    # Concrete classes declare their field-group members here. Kept apart
    # from self.parts, which holds one live instance per member.
    members = ()

    def __init__(self, editor=None, conf=None):
        super().__init__()
        self.rules = Pattern()
        self.editor = editor
        self.conf = conf
        self.state = None

    def initialize(self):
        self.switchButton = QToolButton(self)
        self.switchButton.hide()
        self.headingGroup.setMinimumWidth(77 * 3 + 32)
        self.parts = [member(self) for member in self.members]
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

    def setSequence(self, sequence):
        """The number the presenter handed this draft, rendered as the
        operator sees it."""
        self.sequence.setText(str(sequence))

    def resetPeriod(self):
        """Anchor the validity period to the draft's span, then re-derive the
        durations from what was just written.

        Re-anchoring is the point: periodTime() reads the clock, so a draft
        rendered ten minutes after the last one must not keep the old hours.
        """
        beginningTime, endingTime = self.periodTime()
        self.beginningTime.setText(beginningTime.strftime('%d%H%M'))
        self.endingTime.setText(endingTime.strftime('%d%H%M'))
        self.updateDurations()

    def bindSignal(self):
        self.beginningTime.textChanged.connect(self.updateDurations)
        self.endingTime.textChanged.connect(self.updateDurations)
        self.beginningTime.editingFinished.connect(self.validatePeriod)
        self.endingTime.editingFinished.connect(self.validatePeriod)

        for widget in self.fields():
            if isinstance(widget, QLineEdit):
                widget.textChanged.connect(lambda _, current=widget: self.coloredText(current))
                widget.textEdited.connect(lambda _, current=widget: self.upperText(current))
                widget.textEdited.connect(self.onUserEdited)
            elif isinstance(widget, QComboBox):
                # The templates only expose non-editable combos; a user pick
                # fires activated. The one editable combo, cancelSequence,
                # contributes its line edit to fields() itself and takes the
                # branch above.
                widget.activated.connect(self.onUserEdited)
            else:
                raise TypeError('Unsupported input widget: {}'.format(type(widget).__name__))

        for part in self.parts:
            part.bindSignal()

    def onUserEdited(self, *args):
        sender = self.sender()
        if sender in (self.beginningTime, self.endingTime):
            self.updateDurations()

        self.reload()

    def fields(self):
        """Every input widget whose value feeds the state, the parts' included."""
        return [self.sequence, self.beginningTime, self.endingTime] + \
               [widget for part in self.parts for widget in part.fields()]

    def updateDurations(self):
        if self.beginningTime.hasAcceptableInput() and self.endingTime.hasAcceptableInput():
            beginText = self.beginningTime.text()
            endText = self.endingTime.text()
            start = parseTime(beginText)
            end = parseTime(endText)
            self.state.durations = (start, end)
        else:
            self.state.durations = None

    def periodTime(self):
        self.time = utcnow()
        return validPeriod(self.designator(), self.span(), self.time)

    def validatePeriod(self):
        error = SigmetFormValidator.validatePeriod(self.state, self.span())
        if error:
            if error == SigmetFormValidator.START_TOO_FAR:
                self.beginningTime.clear()
            elif error in (SigmetFormValidator.END_NOT_GREATER, SigmetFormValidator.PERIOD_TOO_LONG):
                self.endingTime.clear()
            self.editor.showNotification('sigmet', _translate(error))

    def collect(self):
        self.state.header.area = self.conf.firName.split()[0] if self.conf.firName else ''
        self.state.header.sign = self.editor.category()
        self.state.header.sequence = self.sequence.text()
        self.state.header.beginningTime = self.beginningTime.text()
        self.state.header.endingTime = self.endingTime.text()
        self.state.header.icao = self.conf.airport

        for part in self.parts:
            part.collect()

    def validate(self):
        self.validatePeriod()

    def setOverlapMode(self, mode):
        if mode == 'final':
            observation = self.part(ObservationPart)
            if observation:
                observation.setSource('OBS')

        for part in self.parts:
            part.setOverlapMode(mode)

    def setLocationMode(self, mode):
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

    def hasAcceptableInput(self):
        return self.state.isAcceptable()

    def designator(self):
        return self.editor.designator

    def span(self):
        return self.editor.span

    def populate(self):
        """Write the header fields back from the state, the inverse of collect().

        These are programmatic writes: derived textChanged handlers still run,
        but textEdited/activated do not, so the header cannot collect the parts
        before they get their turn.
        """
        self.sequence.setText(self.state.header.sequence)
        self.beginningTime.setText(self.state.header.beginningTime)
        self.endingTime.setText(self.state.header.endingTime)

        for part in self.parts:
            part.populate()

    def clear(self):
        self.state.clear()
        self.populate()
        self.contentChanged.emit()

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

    def fields(self):
        return []

    def collect(self):
        pass

    def populate(self):
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
        self.base.editingFinished.connect(lambda: self.validateBaseTop(self.base))
        self.top.editingFinished.connect(lambda: self.validateBaseTop(self.top))

    def fields(self):
        return [self.base, self.top, self.format]

    def collect(self):
        self.widget.state.flightLevelFormat = self.format.currentText()
        self.widget.state.flightLevelBase = self.base.text()
        self.widget.state.flightLevelTop = self.top.text()

    def populate(self):
        self.format.setCurrentIndex(self.format.findText(self.widget.state.flightLevelFormat))
        self.base.setText(self.widget.state.flightLevelBase)
        self.top.setText(self.widget.state.flightLevelTop)

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

        error = SigmetFormValidator.validateFlightLevel(self.base.text(), self.top.text())
        if error:
            line.clear()
            self.widget.editor.showNotification('sigmet', _translate(error))

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

    def fields(self):
        return [self.speed, self.direction]

    def collect(self):
        self.widget.state.direction = self.direction.currentText()
        self.widget.state.speed = self.speed.text() if self.speed.hasAcceptableInput() else ''

    def populate(self):
        self.direction.setCurrentIndex(self.direction.findText(self.widget.state.direction))
        self.speed.setText(self.widget.state.speed)

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

    def fields(self):
        return [self.observedTime, self.comeFrom]

    def collect(self):
        self.widget.state.comeFrom = self.comeFrom.currentText()
        self.widget.state.observedTime = self.observedTime.text() if self.observedTime.hasAcceptableInput() else ''

    def populate(self):
        self.comeFrom.setCurrentIndex(self.comeFrom.findText(self.widget.state.comeFrom))
        self.observedTime.setText(self.widget.state.observedTime)

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

    def fields(self):
        return [self.forecastTime]

    def collect(self):
        self.widget.state.forecastTime = self.forecastTime.text()

    def populate(self):
        hasForecast = self.widget.state.hasForecast

        self.forecastTime.setEnabled(hasForecast)
        self.forecastTimeLabel.setEnabled(hasForecast)
        self.forecastTime.setText(self.widget.state.forecastTime)

    def setupValidator(self):
        self.forecastTime.setValidator(QRegExpValidator(QRegExp(self.widget.rules.time)))

    def setForecastTime(self):
        if self.widget.state.durations is None or not self.widget.endingTime.text() or not self.forecastTime.isEnabled():
            return

        text = self.widget.endingTime.text()[2:]
        self.forecastTime.setText(text)

    def setOverlapMode(self, mode):
        if mode == 'final':
            self.forecastTime.setEnabled(True)
            self.forecastTimeLabel.setEnabled(True)
            self.setForecastTime()
            if self.finalPositionGroup is not None:
                self.finalPositionGroup.setEnabled(True)
        else:
            self.forecastTime.setEnabled(False)
            self.forecastTimeLabel.setEnabled(False)
            self.forecastTime.clear()
            if self.finalPositionGroup is not None:
                self.finalPositionGroup.setEnabled(False)

        self.widget.state.hasForecast = mode == 'final'

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
            self.text.setStyleSheet(validTextStyle)
        except Exception as e:
            self.widget.editor.showNotification('sigmet', QCoreApplication.translate('Editor', 'Advisory message can not be decoded'))
            self.text.setStyleSheet(invalidTextStyle)
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
                speed = str(self.parser.speed() or '')
                self.widget.speed.setText(speed)
            else:
                self.widget.speed.clear()

    def locationFeatures(self, initial, final=None):
        """Advisory locations tagged for the sketch canvas."""
        features = []
        if initial:
            feature = self.parser.location(initial)
            if geojson.hasGeometry(feature):
                feature['properties']['location'] = 'initial'
                feature['properties']['type'] = 'sketch'
                features.append(feature)

        if initial and final:
            feature = self.parser.location(final)
            if geojson.hasGeometry(feature):
                feature['properties']['location'] = 'final'
                feature['properties']['type'] = 'sketch'
                features.append(feature)

        return features

    def handleLocationChange(self):
        features = self.locationFeatures(self.initial.currentText(), self.final.currentText())
        self.widget.locationChanged.emit(geojson.featureCollection(features))

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
        if self.widget.state.mode in ['polygon', 'line', 'circle']:
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

        position = self.parser.formattedPosition(self.initial.currentText())
        if position:
            lat, lon = position
            self.widget.currentLatitude.setText(lat)
            self.widget.currentLongitude.setText(lon)

        position = self.parser.formattedPosition(self.final.currentText())
        if position:
            lat, lon = position
            self.widget.forecastLatitude.setText(lat)
            self.widget.forecastLongitude.setText(lon)
            self.widget.finalPositionGroup.setEnabled(True)
        else:
            self.widget.forecastLongitude.clear()
            self.widget.forecastLatitude.clear()
            self.widget.finalPositionGroup.setEnabled(False)

        self.handleLocationChange()

    def handleLocationChange(self):
        locations = []

        # when in polygon mode, there is no final position, and the initial geometry is a polygon
        if not self.widget.state.mode == 'polygon':
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
            locations.append(geojson.feature(route, **properties))

        polygon = self.parser.polygon()
        if polygon:
            if self.widget.state.mode == 'polygon':
                properties = {
                    'type': 'sketch',
                    'location': 'initial'
                }

            locations.append(geojson.feature(polygon, **properties))

        self.widget.locationChanged.emit(geojson.featureCollection(locations))


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
            base, top = self.parser.splitFlightLevel(features['properties']['flightLevel'])

            pattern = re.compile(r'\d+')
            if base:
                m = pattern.search(base)
                if m:
                    self.widget.base.setText(m.group())
                else:
                    self.widget.format.setCurrentIndex(self.widget.format.findText(base))

            if top:
                m = pattern.search(top)
                if m:
                    self.widget.top.setText(m.group())

        self.handleLocationChange()


class SigmetGeneral(BaseSigmet, Ui_sigmet_general.Ui_Editor):

    members = (ObservationPart, ForecastPart, FlightLevelPart, MovementPart)

    # WMO intensity codes and the phenomena each one admits. OBSC, EMBD,
    # FRQ and SQL all describe convective weather, so they share a list.
    phenomena = {
        'OBSC': ['TS', 'TSGR'],
        'EMBD': ['TS', 'TSGR'],
        'FRQ': ['TS', 'TSGR'],
        'SQL': ['TS', 'TSGR'],
        'SEV': ['TURB', 'ICE', 'ICE (FZRA)', 'MTW'],
        'HVY': ['DS', 'SS'],
        'RDOACT': ['CLD'],
    }

    descriptions = ['OBSC', 'EMBD', 'FRQ', 'SQL', 'SEV', 'HVY', 'RDOACT']

    # Convective phenomena that take the TOP/ABV/SFC flight-level formats.
    convective = ['CB', 'TCU', 'TS', 'TSGR']

    def __init__(self, header, editor=None, conf=None):
        super().__init__(editor, conf=conf)
        self.setupUi(self)
        self.state = SigmetGeneralState(unit=self.conf.units.sigmetSpeed, header=header)
        self.initialize()
        self.setPhenomenaDescription()
        self.setPhenomena()
        self.setFcstOrObs()
        self.setFlightLevelFormat('TS')
        self.collect()

    def bindSignal(self):
        super().bindSignal()
        self.description.currentTextChanged.connect(self.setPhenomena)
        self.phenomenon.currentTextChanged.connect(self.setFlightLevelFormat)

    def fields(self):
        return super().fields() + [self.description, self.phenomenon, self.intensityChange]

    def collect(self):
        super().collect()
        self.state.description = self.description.currentText()
        self.state.phenomenon = self.phenomenon.currentText()
        self.state.intensityChange = self.intensityChange.currentText()

    def populate(self):
        super().populate()
        self.description.setCurrentIndex(self.description.findText(self.state.description))
        self.phenomenon.setCurrentIndex(self.phenomenon.findText(self.state.phenomenon))
        self.intensityChange.setCurrentIndex(self.intensityChange.findText(self.state.intensityChange))

    def setPhenomenaDescription(self):
        self.description.addItems(self.descriptions)
        # Was setCurrentIndex(1), i.e. the second entry. Named rather than
        # indexed so reordering `descriptions` cannot silently change it.
        self.description.setCurrentText('EMBD')

    def setPhenomena(self, text='OBSC'):
        self.phenomenon.clear()
        # Unknown codes fall back to the convective list rather than
        # silently landing in an else branch.
        self.phenomenon.addItems(self.phenomena.get(text, ['TS', 'TSGR']))

    def setFcstOrObs(self):
        observations = ['FCST', 'OBS']
        self.comeFrom.addItems(observations)

    def setFlightLevelFormat(self, text):
        self.format.clear()

        if text in self.convective:
            formats = ['', 'TOP', 'ABV', 'SFC', 'TOP ABV']
            self.format.addItems(formats)
            self.format.setCurrentIndex(self.format.findText('TOP'))
        else:
            formats = ['', 'ABV', 'BLW', 'SFC']
            self.format.addItems(formats)
            self.format.setCurrentIndex(-1)


class SigmetTyphoon(BaseSigmet, Ui_sigmet_typhoon.Ui_Editor):

    members = (ObservationPart, ForecastPart, MovementPart, TyphoonAdvisoryImport)

    locationChanged = pyqtSignal(dict)
    circleChanged = pyqtSignal(dict)

    def __init__(self, header, editor=None, conf=None):
        super().__init__(editor, conf=conf)
        self.setupUi(self)
        self.state = SigmetTyphoonState(unit=self.conf.units.sigmetSpeed, header=header)
        self.initialize()
        self.setPhenomena()
        self.setFcstOrObs()
        self.advisoryParser = TyphoonAdvisoryParser
        self.collect()

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

    def fields(self):
        return super().fields() + [self.name, self.currentLatitude, self.currentLongitude,
                                   self.forecastLatitude, self.forecastLongitude,
                                   self.radius, self.top, self.intensityChange]

    def collect(self):
        super().collect()
        self.state.phenomenon = self.phenomenon.currentText()
        self.state.name = self.name.text()
        self.state.currentLatitude = self.currentLatitude.text() if self.currentLatitude.hasAcceptableInput() else ''
        self.state.currentLongitude = self.currentLongitude.text() if self.currentLongitude.hasAcceptableInput() else ''
        self.state.forecastLatitude = self.forecastLatitude.text() if self.forecastLatitude.hasAcceptableInput() else ''
        self.state.forecastLongitude = self.forecastLongitude.text() if self.forecastLongitude.hasAcceptableInput() else ''
        self.state.radius = self.radius.text() if self.radius.hasAcceptableInput() else ''
        self.state.top = self.top.text() if self.top.hasAcceptableInput() else ''
        self.state.intensityChange = self.intensityChange.currentText()

    def populate(self):
        super().populate()
        self.name.setText(self.state.name)
        self.top.setText(self.state.top)
        self.intensityChange.setCurrentIndex(self.intensityChange.findText(self.state.intensityChange))
        # Radius before the centre: moving the centre re-derives the forecast
        # position, and that derivation reads the radius from the state.
        self.radius.setText(self.state.radius)
        self.currentLatitude.setText(self.state.currentLatitude)
        self.currentLongitude.setText(self.state.currentLongitude)
        self.forecastLatitude.setText(self.state.forecastLatitude)
        self.forecastLongitude.setText(self.state.forecastLongitude)

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
        if self.state.mode == 'circle':
            features = []
            initial = self.circle('initial')
            if initial:
                features.append(initial)
                final = self.circle('final')
                if final:
                    features.append(final)
            self.circleChanged.emit(geojson.featureCollection(features))

    def circle(self, location):
        state = self.state
        latitude = state.currentLatitude if location == 'initial' else state.forecastLatitude
        longitude = state.currentLongitude if location == 'initial' else state.forecastLongitude
        return typhoonCircleFeature(latitude, longitude, state.radius, location)


class SigmetAsh(BaseSigmet, Ui_sigmet_ash.Ui_Editor):

    members = (ObservationPart, ForecastPart, FlightLevelPart, MovementPart, AshAdvisoryImport)

    locationChanged = pyqtSignal(dict)

    def __init__(self, header, editor=None, conf=None):
        super().__init__(editor, conf=conf)
        self.setupUi(self)
        self.state = SigmetAshState(unit=self.conf.units.sigmetSpeed, header=header)
        self.initialize()
        self.setPhenomena()
        self.setFcstOrObs()
        self.advisoryParser = AshAdvisoryParser
        self.collect()

    def bindSignal(self):
        super().bindSignal()
        self.phenomenon.currentTextChanged.connect(self.setEruptionOrCloud)

    def fields(self):
        return super().fields() + [self.name, self.currentLatitude, self.currentLongitude,
                                   self.phenomenon, self.intensityChange]

    def collect(self):
        super().collect()
        self.state.phenomenon = self.phenomenon.currentText()
        self.state.name = self.name.text()
        self.state.currentLatitude = self.currentLatitude.text() if self.currentLatitude.hasAcceptableInput() else ''
        self.state.currentLongitude = self.currentLongitude.text() if self.currentLongitude.hasAcceptableInput() else ''
        self.state.intensityChange = self.intensityChange.currentText()
        self.state.isEruption = self.phenomenon.currentText() == 'ERUPTION'

    def populate(self):
        isEruption = self.state.isEruption
        super().populate()
        self.name.setText(self.state.name)
        self.name.setEnabled(isEruption)
        self.nameLabel.setEnabled(isEruption)
        self.currentLatitude.setEnabled(isEruption)
        self.currentLatitudeLabel.setEnabled(isEruption)
        self.currentLongitude.setEnabled(isEruption)
        self.currentLongitudeLabel.setEnabled(isEruption)
        self.currentLatitude.setText(self.state.currentLatitude)
        self.currentLongitude.setText(self.state.currentLongitude)
        self.intensityChange.setCurrentIndex(self.intensityChange.findText(self.state.intensityChange))

        index = self.phenomenon.findText(self.state.phenomenon)
        self.phenomenon.setCurrentIndex(index if index >= 0 else 0)

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
        self.state.phenomenon = text
        self.state.isEruption = enabled
        self.contentChanged.emit()


class AirmetGeneral(SigmetGeneral):

    members = (ObservationPart, ForecastPart, AirmetFlightLevelPart, MovementPart)

    # AIRMET coverage codes and the phenomena each one admits. A different
    # vocabulary from the SIGMET intensities above, not a subset of them.
    phenomena = {
        'ISOL': ['CB', 'TCU', 'TS', 'TSGR'],
        'OCNL': ['CB', 'TCU', 'TS', 'TSGR'],
        'FRQ': ['CB', 'TCU'],
        'MOD': ['TURB', 'ICE', 'MTW'],
    }

    descriptions = ['ISOL', 'OCNL', 'FRQ', 'MOD']

    def setPhenomenaDescription(self):
        self.description.addItems(self.descriptions)
        # ISOL is the default below; name it rather than lean on index 0.
        self.description.setCurrentText('ISOL')

    def setPhenomena(self, text='ISOL'):
        self.phenomenon.clear()
        self.phenomenon.addItems(
            self.phenomena.get(text, ['CB', 'TCU', 'TS', 'TSGR'])
        )


class SigmetCancel(BaseSigmet, Ui_sigmet_cancel.Ui_Editor):

    def __init__(self, header, editor=None, conf=None):
        super().__init__(editor, conf=conf)
        self.setupUi(self)
        self.state = SigmetCancelState(header=header)
        self.initialize()
        self.collect()

    def bindSignal(self):
        super().bindSignal()
        self.cancelBeginningTime.textChanged.connect(self.syncValidsTime)
        self.cancelEndingTime.textChanged.connect(self.syncValidsTime)
        self.cancelSequence.currentTextChanged.connect(self.setValids)
        # two rows can carry the same sequence number
        self.cancelSequence.currentIndexChanged.connect(self.setValids)

    def fields(self):
        return super().fields() + [self.cancelBeginningTime, self.cancelEndingTime,
                                   self.cancelSequence.lineEdit()]

    def collect(self):
        super().collect()
        self.state.cancelSequence = self.cancelSequence.currentText().strip()
        self.state.cancelBeginningTime = self.cancelBeginningTime.text()
        self.state.cancelEndingTime = self.cancelEndingTime.text()

    def onUserEdited(self, *args):
        # Typing in the editable sequence fires textEdited before the combo's
        # currentTextChanged, so fill the cancelled period before collecting it.
        sender = self.sender()
        if sender is self.cancelSequence.lineEdit():
            self.setValids(self.cancelSequence.currentText())
        elif sender in (self.cancelBeginningTime, self.cancelEndingTime):
            self.syncValidsTime()

        super().onUserEdited(*args)

    def populate(self):
        super().populate()
        self.cancelSequence.setCurrentIndex(self.cancelSequence.findText(self.state.cancelSequence))
        self.cancelBeginningTime.setText(self.state.cancelBeginningTime)
        self.cancelEndingTime.setText(self.state.cancelEndingTime)

    def setupValidator(self):
        super().setupValidator()
        sequence = QRegExpValidator(QRegExp(self.rules.sequence, Qt.CaseInsensitive))
        self.cancelSequence.setValidator(sequence)

        date = QRegExpValidator(QRegExp(self.rules.date))
        self.cancelBeginningTime.setValidator(date)
        self.cancelEndingTime.setValidator(date)

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
                utcnow(),
            )
            self.beginningTime.setText(beginning.strftime('%d%H%M'))

    def setCandidates(self, sigmets):
        """Refill the dropdown with the cancellable reports the presenter
        handed over, each row carrying its valid period as item data:
        same-numbered rows differ in their data, not in their text."""
        self.cancelSequence.clear()

        for sig in sigmets:
            parser = sig.parser()
            self.cancelSequence.addItem(parser.sequence(), parser.validTime())

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
        """The valid period of the addressed record, by combo row index or by
        typed sequence text. The row tells same-numbered records apart; the
        text can only ever reach the first match."""
        combo = self.cancelSequence
        if isinstance(sequence, int):
            if 0 <= sequence < combo.count():
                return combo.itemData(sequence)
        else:
            for row in range(combo.count()):
                if combo.itemText(row) == sequence:
                    return combo.itemData(row)


class SigmetCustom(BaseSigmet, Ui_sigmet_custom.Ui_Editor):

    def __init__(self, header, editor=None, conf=None):
        super().__init__(editor, conf=conf)
        self.setupUi(self)
        self.state = SigmetCustomState(header=header)
        self.setupApiSign()
        self.initialize()
        self.upperTextEdit()
        self.collect()

    def bindSignal(self):
        super().bindSignal()
        self.text.textChanged.connect(self.onUserEdited)

    def onUserEdited(self, *args):
        # The filter is part of the commit: let the text edited by the operator
        # settle into its allowed form, then read that form into the state.
        self.filterText()
        super().onUserEdited()

    def collect(self):
        super().collect()
        self.state.text = self.text.toPlainText().strip()

    def populate(self):
        super().populate()
        with QSignalBlocker(self.text):
            self.text.setPlainText(self.state.text)

    def filterText(self):
        origin = self.text.toPlainText()
        text = re.sub(r'[^A-Za-z0-9)(\/\.\s,-]+', '', origin)
        text = text.upper()
        if origin != text:
            cursor = self.text.textCursor()
            pos = cursor.position()
            with QSignalBlocker(self.text):
                self.text.setText(text)
            cursor.movePosition(QTextCursor.Left, QTextCursor.MoveAnchor, len(text) - pos)
            self.text.setTextCursor(cursor)

    def upperTextEdit(self):
        upper = QTextCharFormat()
        upper.setFontCapitalization(QFont.AllUppercase)
        self.text.setCurrentCharFormat(upper)

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
        tip = tips[self.designator()]
        self.text.setPlaceholderText(tip)

    def setLatestText(self, rv):
        """Render the message the presenter resolved: (source, content) or
        None. The api sign follows the source, so no message at all hides it
        rather than leaving a stale mark from the designator before."""
        self.setupPlaceholder()
        self.apiSign.setVisible(bool(rv) and rv[0] == 'notification')

        if not rv:
            self.setText('')
            return

        _, message = rv
        fir = self.conf.firName or ''
        self.setText(message.replace(fir, '').replace('=', '').strip())

    def setText(self, message):
        with QSignalBlocker(self.text):
            self.text.setText(message)
        self.text.moveCursor(QTextCursor.End)

    def resizeEvent(self, event):
        self.apiSign.move(self.width() - 43, 80)
        super().resizeEvent(event)
