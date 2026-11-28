import re
import logging

from itertools import cycle

from PyQt5.QtGui import QRegExpValidator, QIntValidator, QTextCharFormat, QTextCursor, QFont, QPixmap, QIcon
from PyQt5.QtCore import Qt, QRegExp, QCoreApplication, QSignalBlocker, pyqtSignal
from PyQt5.QtWidgets import QComboBox, QWidget, QLabel, QLineEdit, QToolButton

from tafor.core.parsers.base import Pattern
from tafor.core.parsers.advisory import AshAdvisoryParser, TyphoonAdvisoryParser
from tafor.core.sigmet import (
    SigmetAshState, SigmetCancelState, SigmetCustomState, SigmetGeneralState,
    SigmetTyphoonState, SigmetFormValidator, ashRules, cancelRules, customRules,
    filterCustomText, flightLevelFormats, generalRules, typhoonRules,
)
from tafor.core.sigmet.compose import (
    adjustCancelBeginning,
    category,
    typhoonCircleFeature,
    validDuration,
    validPeriod,
)
from tafor.core.geometry import geojson
from tafor.core.geometry.coordinate import decimalToDegree
from tafor.core.utils.time import parseTime, utcnow
from tafor.core.utils.common import iconPath
from tafor.ui.qt import Ui_sigmet_ash, Ui_sigmet_cancel, Ui_sigmet_custom, Ui_sigmet_general, Ui_sigmet_typhoon
from tafor.ui.forms.base import (
    coloredText, isAcceptable, setComboOptions, setComboText, setLineText, setPlainText, setupFont,
)
from tafor.ui.forms.pipeline import FormPipeline
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


class BaseSigmet(QWidget):

    contentChanged = pyqtSignal()
    notified = pyqtSignal(str)

    # Concrete classes declare their field-group members here. Kept apart
    # from self.parts, which holds one live instance per member.
    members = ()

    defaults = {}

    def __init__(self, conf=None):
        super().__init__()
        self.patterns = Pattern()
        self.conf = conf
        self.state = None

    def initialize(self):
        self.switchButton = QToolButton(self)
        self.switchButton.hide()
        self.headingGroup.setMinimumWidth(77 * 3 + 32)
        self.parts = [member(self) for member in self.members]
        setupFont(self)
        self.setupMainElementWidth()
        self.setupValidator()
        self.pipeline = FormPipeline(
            initial=self.fromState(),
            apply=self.apply,
            rules=self.rules,
            validator=self.check,
            render=lambda: self.populate(self.pipeline.raw),
            notify=self.notified.emit,
            changed=self.contentChanged.emit,
            effect=self.effect,
        )
        self.bindSignal()

    def rules(self, raw, previous, changed, source):
        pass

    def effect(self, changed, source):
        pass

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
        self.pipeline.edit({'sequence': str(sequence)}, source='seed', force=True)

    def resetPeriod(self):
        """Anchor the validity period to the draft's span, then re-derive the
        durations from what was just written.

        Re-anchoring is the point: periodTime() reads the clock, so a draft
        rendered ten minutes after the last one must not keep the old hours.
        """
        beginningTime, endingTime = self.periodTime()
        self.pipeline.edit({
            'beginningTime': beginningTime.strftime('%d%H%M'),
            'endingTime': endingTime.strftime('%d%H%M'),
        }, source='seed', force=True)

    def bindings(self):
        """Pairs of ``(widget, fieldName)`` managed by the pipeline."""
        return [
            (self.sequence, 'sequence'),
            (self.beginningTime, 'beginningTime'),
            (self.endingTime, 'endingTime'),
        ] + [binding for part in self.parts for binding in part.bindings()]

    def fields(self):
        """Every input widget whose value feeds the state, the parts' included."""
        return [widget for widget, _ in self.bindings()]

    def fromState(self):
        raw = {
            'sequence': self.state.header.sequence,
            'beginningTime': self.state.header.beginningTime,
            'endingTime': self.state.header.endingTime,
        }
        for part in self.parts:
            raw.update(part.fromState())
        return raw

    def fromWidgets(self):
        raw = {
            'sequence': self.sequence.text(),
            'beginningTime': self.beginningTime.text(),
            'endingTime': self.endingTime.text(),
        }
        for part in self.parts:
            raw.update(part.fromWidgets())
        return raw

    def apply(self, raw):
        self.state.header.area = self.conf.firName.split()[0] if self.conf.firName else ''
        self.state.header.sign = category(self.designator())
        self.state.header.icao = self.conf.airport
        self.state.header.sequence = raw.get('sequence', '')
        beginText = raw.get('beginningTime', '')
        endText = raw.get('endingTime', '')
        self.state.header.beginningTime = beginText
        self.state.header.endingTime = endText

        if isAcceptable(self.beginningTime, beginText) and isAcceptable(self.endingTime, endText):
            self.state.durations = (parseTime(beginText), parseTime(endText))
        else:
            self.state.durations = None

        for part in self.parts:
            part.apply(raw)

    def editText(self, field, line, text):
        upper = text.upper()
        if upper != text:
            setLineText(line, upper)
        self.pipeline.edit({field: upper})

    def editCombo(self, field, combo, index):
        text = combo.itemText(index) if 0 <= index < combo.count() else combo.currentText()
        self.pipeline.edit({field: text})

    def finishText(self, field, line, scope=None):
        if not line.isEnabled():
            return
        self.editText(field, line, line.text())
        self.pipeline.validate(scope or field)

    def bindSignal(self):
        self.beginningTime.editingFinished.connect(
            lambda: self.finishText('beginningTime', self.beginningTime, scope='period')
        )
        self.endingTime.editingFinished.connect(
            lambda: self.finishText('endingTime', self.endingTime, scope='period')
        )

        for widget, field in self.bindings():
            if isinstance(widget, QLineEdit):
                widget.textEdited.connect(lambda text, f=field, w=widget: self.editText(f, w, text))
            elif isinstance(widget, QComboBox):
                widget.activated[int].connect(lambda index, f=field, w=widget: self.editCombo(f, w, index))
            else:
                raise TypeError('Unsupported input widget: {}'.format(type(widget).__name__))

        for part in self.parts:
            part.bindSignal()

    def periodTime(self):
        self.time = utcnow()
        return validPeriod(self.designator(), self.span(), self.time)

    def check(self, scope):
        if scope == 'period':
            error = SigmetFormValidator.validatePeriod(self.state, self.span())
            if error == SigmetFormValidator.START_TOO_FAR:
                return ({'beginningTime': ''}, [_translate(error)])
            if error in (SigmetFormValidator.END_NOT_GREATER, SigmetFormValidator.PERIOD_TOO_LONG):
                return ({'endingTime': ''}, [_translate(error)])
            return ({}, [])

        for part in self.parts:
            patch, errors = part.check(scope)
            if patch or errors:
                return (patch, errors)

        return ({}, [])

    def collect(self):
        self.pipeline.sync(self.fromWidgets(), source='collect', derive=True, changed=False)

    def validate(self):
        self.pipeline.validate('period')
        for part in self.parts:
            for scope in part.scopes:
                self.pipeline.validate(scope)

    def setOverlapMode(self, mode):
        patch = {'hasForecast': mode == 'final'}
        if mode == 'final' and self.part(ObservationPart):
            patch['comeFrom'] = 'OBS'
        self.pipeline.edit(patch, source='overlap')

    def setLocationMode(self, mode):
        # Only the typhoon body composes from its mode, so only it carries the
        # field in raw; the other bodies keep this canvas fact on the state.
        if 'mode' in self.pipeline.raw:
            self.pipeline.edit({'mode': mode}, source='map')
        else:
            self.state.mode = mode

        for part in self.parts:
            part.setLocationMode(mode)

    def setupValidator(self):
        date = QRegExpValidator(QRegExp(self.patterns.date))
        self.beginningTime.setValidator(date)
        self.endingTime.setValidator(date)

        sequence = QRegExpValidator(QRegExp(self.patterns.sequence, Qt.CaseInsensitive))
        self.sequence.setValidator(sequence)

        for part in self.parts:
            part.setupValidator()

    def hasAcceptableInput(self):
        return self.state.isAcceptable()

    def designator(self):
        return self.state.header.designator

    def span(self):
        return validDuration(self.designator())

    def populate(self, raw=None):
        """Write the header fields back from the state, the inverse of collect()."""
        if raw is None:
            self.pipeline.sync(self.fromState())
            return

        setLineText(self.sequence, raw.get('sequence', ''))
        setLineText(self.beginningTime, raw.get('beginningTime', ''))
        setLineText(self.endingTime, raw.get('endingTime', ''))
        coloredText(self.sequence)
        coloredText(self.beginningTime)
        coloredText(self.endingTime)

        for part in self.parts:
            part.populate(raw)

    def clear(self):
        self.state.clear()
        self.pipeline.sync({**self.fromState(), **self.defaults}, source='clear', derive=True, changed=True)

        for part in self.parts:
            part.clear()


class SigmetPart:
    """Field-group controller bound to a SIGMET editor widget.

    Required widget names fail fast at construction; optional widgets
    default to None and are only probed inside the part.
    """

    widgets = ()
    optional = ()
    scopes = ()

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

    def bindings(self):
        return []

    def fromState(self):
        return {}

    def fromWidgets(self):
        return {}

    def apply(self, raw):
        pass

    def populate(self, raw=None):
        pass

    def check(self, scope):
        return ({}, [])

    def setupValidator(self):
        pass

    def clear(self):
        pass

    def setLocationMode(self, mode):
        pass


class FlightLevelPart(SigmetPart):

    widgets = ('format', 'base', 'top', 'baseLabel', 'topLabel')
    scopes = ('flightLevelTop',)

    def bindSignal(self):
        self.base.editingFinished.connect(lambda: self.widget.finishText('flightLevelBase', self.base))
        self.top.editingFinished.connect(lambda: self.widget.finishText('flightLevelTop', self.top))

    def bindings(self):
        return [
            (self.base, 'flightLevelBase'),
            (self.top, 'flightLevelTop'),
            (self.format, 'flightLevelFormat'),
        ]

    def fromState(self):
        return {
            'flightLevelFormat': self.widget.state.flightLevelFormat,
            'flightLevelBase': self.widget.state.flightLevelBase,
            'flightLevelTop': self.widget.state.flightLevelTop,
        }

    def fromWidgets(self):
        return {
            'flightLevelFormat': self.format.currentText(),
            'flightLevelBase': self.base.text(),
            'flightLevelTop': self.top.text(),
        }

    def apply(self, raw):
        self.widget.state.flightLevelFormat = raw.get('flightLevelFormat', '')
        self.widget.state.flightLevelBase = raw.get('flightLevelBase', '')
        self.widget.state.flightLevelTop = raw.get('flightLevelTop', '')

    def populate(self, raw=None):
        if raw is None:
            raw = self.fromState()

        fmt = raw.get('flightLevelFormat', '')
        setComboText(self.format, fmt)
        setLineText(self.base, raw.get('flightLevelBase', ''))
        setLineText(self.top, raw.get('flightLevelTop', ''))

        baseEnabled = fmt not in ('TOP', 'TOP ABV', 'SFC', 'BLW')
        topEnabled = fmt != 'ABV'
        self.base.setEnabled(baseEnabled)
        self.baseLabel.setEnabled(baseEnabled)
        self.top.setEnabled(topEnabled)
        self.topLabel.setEnabled(topEnabled)

        coloredText(self.base)
        coloredText(self.top)

    def setupValidator(self):
        self.base.setValidator(QIntValidator(1, 999, self.base))
        self.top.setValidator(QIntValidator(100, 999, self.top))
        self.base.setMaxLength(3)
        self.top.setMaxLength(3)

    def check(self, scope):
        if scope not in ('flightLevelBase', 'flightLevelTop'):
            return ({}, [])

        if not (self.base.isEnabled() and self.top.isEnabled()):
            return ({}, [])

        base = self.widget.pipeline.value('flightLevelBase')
        top = self.widget.pipeline.value('flightLevelTop')
        error = SigmetFormValidator.validateFlightLevel(base, top)
        if error:
            return ({scope: ''}, [_translate(error)])
        return ({}, [])

class AirmetFlightLevelPart(FlightLevelPart):

    def setupValidator(self):
        self.base.setValidator(QIntValidator(1, 100, self.base))
        self.top.setValidator(QIntValidator(1, 150, self.top))
        self.base.setMaxLength(3)
        self.top.setMaxLength(3)


class MovementPart(SigmetPart):

    widgets = ('direction', 'speed', 'speedLabel')

    def bindings(self):
        return [(self.speed, 'speed'), (self.direction, 'direction')]

    def fromState(self):
        return {
            'direction': self.widget.state.direction,
            'speed': self.widget.state.speed,
        }

    def fromWidgets(self):
        return {
            'direction': self.direction.currentText(),
            'speed': self.speed.text(),
        }

    def apply(self, raw):
        self.widget.state.direction = raw.get('direction', '')
        speed = raw.get('speed', '')
        self.widget.state.speed = speed if isAcceptable(self.speed, speed) else ''

    def populate(self, raw=None):
        if raw is None:
            raw = self.fromState()

        direction = raw.get('direction', '')
        setComboText(self.direction, direction)
        setLineText(self.speed, raw.get('speed', ''))

        moving = direction != 'STNR'
        self.speed.setEnabled(moving)
        self.speedLabel.setEnabled(moving)
        coloredText(self.speed)

    def setupValidator(self):
        self.speed.setValidator(QIntValidator(1, 99, self.speed))
        self.speed.setMaxLength(2)


class ObservationPart(SigmetPart):

    widgets = ('comeFrom', 'observedTime', 'observedTimeLabel', 'beginningTime')

    def bindings(self):
        return [(self.observedTime, 'observedTime'), (self.comeFrom, 'comeFrom')]

    def fromState(self):
        return {
            'comeFrom': self.widget.state.comeFrom,
            'observedTime': self.widget.state.observedTime,
        }

    def fromWidgets(self):
        return {
            'comeFrom': self.comeFrom.currentText(),
            'observedTime': self.observedTime.text(),
        }

    def apply(self, raw):
        self.widget.state.comeFrom = raw.get('comeFrom', '')
        observedTime = raw.get('observedTime', '')
        self.widget.state.observedTime = observedTime if isAcceptable(self.observedTime, observedTime) else ''

    def populate(self, raw=None):
        if raw is None:
            raw = self.fromState()

        comeFrom = raw.get('comeFrom', '')
        setComboText(self.comeFrom, comeFrom)
        setLineText(self.observedTime, raw.get('observedTime', ''))

        label = (
            QCoreApplication.translate('Editor', 'Observed Time')
            if comeFrom == 'OBS'
            else QCoreApplication.translate('Editor', 'Forecast Time')
        )
        if self.observedTimeLabel.text() != label:
            self.observedTimeLabel.setText(label)
        coloredText(self.observedTime)

    def setupValidator(self):
        self.observedTime.setValidator(QRegExpValidator(QRegExp(self.widget.patterns.time)))


class ForecastPart(SigmetPart):

    widgets = ('forecastTime', 'forecastTimeLabel')
    optional = ('finalPositionGroup',)

    def bindings(self):
        return [(self.forecastTime, 'forecastTime')]

    def fromState(self):
        return {
            'forecastTime': self.widget.state.forecastTime,
            'hasForecast': self.widget.state.hasForecast,
        }

    def fromWidgets(self):
        return {
            'forecastTime': self.forecastTime.text(),
            'hasForecast': self.widget.state.hasForecast,
        }

    def apply(self, raw):
        self.widget.state.hasForecast = bool(raw.get('hasForecast'))
        self.widget.state.forecastTime = raw.get('forecastTime', '')

    def populate(self, raw=None):
        if raw is None:
            raw = self.fromState()

        hasForecast = bool(raw.get('hasForecast'))
        self.forecastTime.setEnabled(hasForecast)
        self.forecastTimeLabel.setEnabled(hasForecast)
        if self.finalPositionGroup is not None:
            self.finalPositionGroup.setEnabled(hasForecast)

        setLineText(self.forecastTime, raw.get('forecastTime', ''))
        coloredText(self.forecastTime)

    def setupValidator(self):
        self.forecastTime.setValidator(QRegExpValidator(QRegExp(self.widget.patterns.time)))


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
        self.initial.activated[int].connect(self.onInitialChanged)
        self.final.activated[int].connect(self.updateLocation)

    def onInitialChanged(self):
        self.updateFinalOption()
        self.updateLocation()

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
            setComboOptions(self.initial, options)
            self.updateFinalOption()
            self.fill()
            self.text.setStyleSheet(validTextStyle)
        except Exception as e:
            self.widget.notified.emit(QCoreApplication.translate('Editor', 'Advisory message can not be decoded'))
            self.text.setStyleSheet(invalidTextStyle)
            logger.error('Advisory message can not be decoded, {}, {}'.format(text, e))

    def extract(self):
        patch = {}
        name = self.parser.name()
        if name:
            patch['name'] = name

        initial = self.initial.currentText()
        if 'OBS' in initial:
            patch['comeFrom'] = 'OBS'
        if 'FCST' in initial:
            patch['comeFrom'] = 'FCST'

        features = self.parser.location(initial)
        if features and 'time' in features['properties']:
            time = features['properties']['time']
            patch['observedTime'] = time.strftime('%H%M')

        final = self.final.currentText()
        features = self.parser.location(final)
        if features and 'time' in features['properties']:
            time = features['properties']['time']
            patch['forecastTime'] = time.strftime('%H%M')
            patch['hasForecast'] = True
        else:
            patch['forecastTime'] = ''
            patch['hasForecast'] = False

        movement = self.parser.movement()
        if movement:
            patch['direction'] = movement
            if not final and movement != 'STNR':
                patch['speed'] = str(self.parser.speed() or '')
            else:
                patch['speed'] = ''

        return patch

    def fill(self):
        patch = self.extract()
        if patch:
            self.widget.pipeline.edit(patch, source='advisory')
        self.handleLocationChange()

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

        setComboOptions(self.final, rests)

    def updateVisibility(self):
        if self.group == 'main':
            self.advisory.hide()
            self.main.show()
        else:
            self.advisory.show()
            self.main.hide()

    def updateLocation(self):
        try:
            self.fill()
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

        setPlainText(self.text, '')
        setComboOptions(self.initial, [])
        setComboOptions(self.final, [])
        self.parser = None


class TyphoonAdvisoryImport(AdvisoryImport):

    def extract(self):
        patch = super().extract()

        height = self.parser.height()
        if height:
            patch['top'] = height

        intensity = self.parser.intensity()
        if intensity:
            patch['intensityChange'] = intensity

        radius = self.parser.radius()
        if radius:
            patch['radius'] = str(radius)

        position = self.parser.formattedPosition(self.initial.currentText())
        if position:
            lat, lon = position
            patch['currentLatitude'] = lat
            patch['currentLongitude'] = lon

        position = self.parser.formattedPosition(self.final.currentText())
        if position:
            lat, lon = position
            patch['forecastLatitude'] = lat
            patch['forecastLongitude'] = lon
            patch['hasForecast'] = True
        else:
            patch['forecastLatitude'] = ''
            patch['forecastLongitude'] = ''

        return patch

    def handleLocationChange(self):
        locations = []

        # when in polygon mode, there is no final position, and the initial geometry is a polygon
        if not self.widget.state.mode == 'polygon':
            locations += self.locationFeatures(self.initial.currentText(), self.final.currentText())

        radius = int(self.widget.state.radius) if self.widget.state.radius else 0
        for feature in locations:
            feature['properties']['radius'] = radius

        route = self.parser.route()
        if route:
            locations.append(geojson.feature(route, type='exterior', location='initial'))

        polygon = self.parser.polygon()
        if polygon:
            type = 'sketch' if self.widget.state.mode == 'polygon' else 'exterior'
            locations.append(geojson.feature(polygon, type=type, location='initial'))

        self.widget.locationChanged.emit(geojson.featureCollection(locations))


class AshAdvisoryImport(AdvisoryImport):

    def extract(self):
        patch = super().extract()

        position = self.parser.position()
        if position:
            lat, lon = position
            patch['currentLatitude'] = lat
            patch['currentLongitude'] = lon

        initial = self.initial.currentText()
        features = self.parser.location(initial)
        if features and 'flightLevel' in features['properties']:
            base, top = self.parser.splitFlightLevel(features['properties']['flightLevel'])

            pattern = re.compile(r'\d+')
            if base:
                m = pattern.search(base)
                if m:
                    patch['flightLevelBase'] = m.group()
                else:
                    patch['flightLevelFormat'] = base

            if top:
                m = pattern.search(top)
                if m:
                    patch['flightLevelTop'] = m.group()

        return patch


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
    defaultPhenomena = ['TS', 'TSGR']

    defaults = {
        'description': 'EMBD',
        'phenomenon': 'TS',
        'comeFrom': 'FCST',
        'flightLevelFormat': 'TOP',
        'direction': 'N',
        'intensityChange': 'NC',
    }

    def __init__(self, header, conf=None):
        super().__init__(conf=conf)
        self.setupUi(self)
        self.state = SigmetGeneralState(unit=self.conf.units.sigmetSpeed, header=header)
        self.initialize()
        setComboOptions(self.description, self.descriptions)
        setComboOptions(self.comeFrom, ['FCST', 'OBS'])
        self.pipeline.sync({**self.fromState(), **self.defaults}, source='init', derive=True)

    def rules(self, raw, previous, changed, source):
        generalRules(
            raw,
            previous,
            changed,
            source,
            phenomenaMap=self.phenomena,
            defaultPhenomena=self.defaultPhenomena,
            hasDurations=self.state.durations is not None,
        )

    def bindings(self):
        return super().bindings() + [
            (self.description, 'description'),
            (self.phenomenon, 'phenomenon'),
            (self.intensityChange, 'intensityChange'),
        ]

    def fromState(self):
        raw = super().fromState()
        raw.update({
            'description': self.state.description,
            'phenomenon': self.state.phenomenon,
            'intensityChange': self.state.intensityChange,
        })
        return raw

    def fromWidgets(self):
        raw = super().fromWidgets()
        raw.update({
            'description': self.description.currentText(),
            'phenomenon': self.phenomenon.currentText(),
            'intensityChange': self.intensityChange.currentText(),
        })
        return raw

    def apply(self, raw):
        super().apply(raw)
        self.state.description = raw.get('description', '')
        self.state.phenomenon = raw.get('phenomenon', '')
        self.state.intensityChange = raw.get('intensityChange', '')

    def populate(self, raw=None):
        if raw is None:
            self.pipeline.sync(self.fromState())
            return

        description = raw.get('description', '')
        phenomenon = raw.get('phenomenon', '')
        setComboOptions(self.phenomenon, self.phenomena.get(description, self.defaultPhenomena))
        setComboOptions(self.format, flightLevelFormats(phenomenon))

        super().populate(raw)

        setComboText(self.description, description)
        setComboText(self.phenomenon, phenomenon)
        setComboText(self.intensityChange, raw.get('intensityChange', ''))


class SigmetTyphoon(BaseSigmet, Ui_sigmet_typhoon.Ui_Editor):

    members = (ObservationPart, ForecastPart, MovementPart, TyphoonAdvisoryImport)

    locationChanged = pyqtSignal(dict)
    circleChanged = pyqtSignal(dict)

    defaults = {
        'phenomenon': 'TC',
        'comeFrom': 'OBS',
        'direction': 'N',
        'intensityChange': 'NC',
        'mode': 'polygon',
    }

    def __init__(self, header, conf=None):
        super().__init__(conf=conf)
        self.setupUi(self)
        self.state = SigmetTyphoonState(unit=self.conf.units.sigmetSpeed, length=self.conf.units.length, header=header)
        self.initialize()
        setComboOptions(self.phenomenon, ['TC'])
        setComboOptions(self.comeFrom, ['OBS', 'FCST'])
        self.advisoryParser = TyphoonAdvisoryParser
        self.pipeline.sync({**self.fromState(), **self.defaults}, source='init', derive=True)

    def rules(self, raw, previous, changed, source):
        typhoonRules(
            raw,
            previous,
            changed,
            source,
            hasDurations=self.state.durations is not None,
            calcForecast=self.state.calcForecastPosition,
        )

    def effect(self, changed, source):
        circleKeys = (
            'currentLatitude',
            'currentLongitude',
            'forecastLatitude',
            'forecastLongitude',
            'radius',
        )
        circleChanged = any(
            self.pipeline.raw.get(key) != self.pipeline.previous.get(key)
            for key in circleKeys
        )
        if source not in ('map', 'clear', 'system') and circleChanged:
            self.handleCircleChange()

    def bindings(self):
        return super().bindings() + [
            (self.name, 'name'),
            (self.currentLatitude, 'currentLatitude'),
            (self.currentLongitude, 'currentLongitude'),
            (self.forecastLatitude, 'forecastLatitude'),
            (self.forecastLongitude, 'forecastLongitude'),
            (self.radius, 'radius'),
            (self.top, 'top'),
            (self.intensityChange, 'intensityChange'),
        ]

    def fromState(self):
        raw = super().fromState()
        raw.update({
            'phenomenon': self.state.phenomenon,
            'name': self.state.name,
            'currentLatitude': self.state.currentLatitude,
            'currentLongitude': self.state.currentLongitude,
            'forecastLatitude': self.state.forecastLatitude,
            'forecastLongitude': self.state.forecastLongitude,
            'radius': self.state.radius,
            'top': self.state.top,
            'intensityChange': self.state.intensityChange,
            'mode': self.state.mode,
        })
        return raw

    def fromWidgets(self):
        raw = super().fromWidgets()
        raw.update({
            'phenomenon': self.phenomenon.currentText(),
            'name': self.name.text(),
            'currentLatitude': self.currentLatitude.text(),
            'currentLongitude': self.currentLongitude.text(),
            'forecastLatitude': self.forecastLatitude.text(),
            'forecastLongitude': self.forecastLongitude.text(),
            'radius': self.radius.text(),
            'top': self.top.text(),
            'intensityChange': self.intensityChange.currentText(),
            'mode': self.state.mode,
        })
        return raw

    def apply(self, raw):
        super().apply(raw)
        self.state.phenomenon = raw.get('phenomenon', '') or self.phenomenon.currentText()
        self.state.name = raw.get('name', '')
        self.state.currentLatitude = (
            raw.get('currentLatitude', '')
            if isAcceptable(self.currentLatitude, raw.get('currentLatitude', ''))
            else ''
        )
        self.state.currentLongitude = (
            raw.get('currentLongitude', '')
            if isAcceptable(self.currentLongitude, raw.get('currentLongitude', ''))
            else ''
        )
        self.state.forecastLatitude = (
            raw.get('forecastLatitude', '')
            if isAcceptable(self.forecastLatitude, raw.get('forecastLatitude', ''))
            else ''
        )
        self.state.forecastLongitude = (
            raw.get('forecastLongitude', '')
            if isAcceptable(self.forecastLongitude, raw.get('forecastLongitude', ''))
            else ''
        )
        self.state.radius = raw.get('radius', '') if isAcceptable(self.radius, raw.get('radius', '')) else ''
        self.state.top = raw.get('top', '') if isAcceptable(self.top, raw.get('top', '')) else ''
        self.state.intensityChange = raw.get('intensityChange', '')
        self.state.mode = raw.get('mode', self.state.mode)

    def populate(self, raw=None):
        if raw is None:
            self.pipeline.sync(self.fromState())
            return

        super().populate(raw)
        setLineText(self.name, raw.get('name', ''))
        setLineText(self.top, raw.get('top', ''))
        setComboText(self.intensityChange, raw.get('intensityChange', ''))
        setLineText(self.radius, raw.get('radius', ''))
        setLineText(self.currentLatitude, raw.get('currentLatitude', ''))
        setLineText(self.currentLongitude, raw.get('currentLongitude', ''))
        setLineText(self.forecastLatitude, raw.get('forecastLatitude', ''))
        setLineText(self.forecastLongitude, raw.get('forecastLongitude', ''))

        for line in (
            self.name,
            self.top,
            self.radius,
            self.currentLatitude,
            self.currentLongitude,
            self.forecastLatitude,
            self.forecastLongitude,
        ):
            coloredText(line)

    def setupValidator(self):
        super().setupValidator()
        latitude = QRegExpValidator(QRegExp(self.patterns.latitude, Qt.CaseInsensitive))
        self.currentLatitude.setValidator(latitude)
        self.forecastLatitude.setValidator(latitude)

        longitude = QRegExpValidator(QRegExp(self.patterns.longitude, Qt.CaseInsensitive))
        self.currentLongitude.setValidator(longitude)
        self.forecastLongitude.setValidator(longitude)

        self.top.setValidator(QIntValidator(100, 999, self.top))
        self.top.setMaxLength(3)

        time = QRegExpValidator(QRegExp(self.patterns.time))
        self.forecastTime.setValidator(time)

        self.radius.setValidator(QIntValidator(1, 999, self.radius))
        self.radius.setMaxLength(3)

        name = QRegExpValidator(QRegExp(r'[A-Za-z0-9-]+'))
        self.name.setValidator(name)
        self.name.setMaxLength(20)

    def setTyphoonLocation(self, collections):
        if not collections['features']:
            return

        patch = {}
        radius = None
        for feature in collections['features']:
            location = feature['properties']['location']
            if location == 'initial':
                lonKey, latKey = 'currentLongitude', 'currentLatitude'
                radius = feature['properties']['radius']
            else:
                lonKey, latKey = 'forecastLongitude', 'forecastLatitude'

            center = geojson.position(feature['geometry'])
            if center:
                lon, lat = center
                patch[lonKey] = decimalToDegree(lon, fmt='longitude')
                patch[latKey] = decimalToDegree(lat)
            elif self.pipeline.value(lonKey) and self.pipeline.value(latKey):
                patch[lonKey] = ''
                patch[latKey] = ''

        patch['radius'] = str(radius) if radius else ''
        self.pipeline.edit(patch, source='map', force=True)

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

    defaults = {
        'phenomenon': 'ERUPTION',
        'isEruption': True,
        'comeFrom': 'FCST',
        'flightLevelFormat': '',
        'direction': 'N',
        'intensityChange': 'NC',
    }

    def __init__(self, header, conf=None):
        super().__init__(conf=conf)
        self.setupUi(self)
        self.state = SigmetAshState(unit=self.conf.units.sigmetSpeed, header=header)
        self.initialize()
        setComboOptions(self.phenomenon, ['ERUPTION', 'CLD'])
        setComboOptions(self.comeFrom, ['FCST', 'OBS'])
        self.advisoryParser = AshAdvisoryParser
        self.pipeline.sync({**self.fromState(), **self.defaults}, source='init', derive=True)

    def rules(self, raw, previous, changed, source):
        ashRules(
            raw,
            previous,
            changed,
            source,
            hasDurations=self.state.durations is not None,
        )

    def bindings(self):
        return super().bindings() + [
            (self.name, 'name'),
            (self.currentLatitude, 'currentLatitude'),
            (self.currentLongitude, 'currentLongitude'),
            (self.phenomenon, 'phenomenon'),
            (self.intensityChange, 'intensityChange'),
        ]

    def fromState(self):
        raw = super().fromState()
        raw.update({
            'phenomenon': self.state.phenomenon,
            'name': self.state.name,
            'currentLatitude': self.state.currentLatitude,
            'currentLongitude': self.state.currentLongitude,
            'intensityChange': self.state.intensityChange,
            'isEruption': self.state.isEruption,
        })
        return raw

    def fromWidgets(self):
        raw = super().fromWidgets()
        phenomenon = self.phenomenon.currentText()
        raw.update({
            'phenomenon': phenomenon,
            'name': self.name.text(),
            'currentLatitude': self.currentLatitude.text(),
            'currentLongitude': self.currentLongitude.text(),
            'intensityChange': self.intensityChange.currentText(),
            'isEruption': phenomenon == 'ERUPTION',
        })
        return raw

    def apply(self, raw):
        super().apply(raw)
        phenomenon = raw.get('phenomenon', 'ERUPTION')
        self.state.phenomenon = phenomenon
        self.state.name = raw.get('name', '')
        self.state.currentLatitude = (
            raw.get('currentLatitude', '')
            if isAcceptable(self.currentLatitude, raw.get('currentLatitude', ''))
            else ''
        )
        self.state.currentLongitude = (
            raw.get('currentLongitude', '')
            if isAcceptable(self.currentLongitude, raw.get('currentLongitude', ''))
            else ''
        )
        self.state.intensityChange = raw.get('intensityChange', '')
        self.state.isEruption = bool(raw.get('isEruption', phenomenon == 'ERUPTION'))

    def populate(self, raw=None):
        if raw is None:
            self.pipeline.sync(self.fromState())
            return

        super().populate(raw)
        isEruption = bool(raw.get('isEruption', True))
        self.name.setEnabled(isEruption)
        self.nameLabel.setEnabled(isEruption)
        self.currentLatitude.setEnabled(isEruption)
        self.currentLatitudeLabel.setEnabled(isEruption)
        self.currentLongitude.setEnabled(isEruption)
        self.currentLongitudeLabel.setEnabled(isEruption)

        setLineText(self.name, raw.get('name', ''))
        setLineText(self.currentLatitude, raw.get('currentLatitude', ''))
        setLineText(self.currentLongitude, raw.get('currentLongitude', ''))
        setComboText(self.intensityChange, raw.get('intensityChange', ''))

        phenomenon = raw.get('phenomenon', 'ERUPTION')
        setComboText(self.phenomenon, phenomenon if self.phenomenon.findText(phenomenon) >= 0 else 'ERUPTION')

        coloredText(self.name)
        coloredText(self.currentLatitude)
        coloredText(self.currentLongitude)

    def setupValidator(self):
        super().setupValidator()
        latitude = QRegExpValidator(QRegExp(self.patterns.latitude, Qt.CaseInsensitive))
        self.currentLatitude.setValidator(latitude)

        longitude = QRegExpValidator(QRegExp(self.patterns.longitude, Qt.CaseInsensitive))
        self.currentLongitude.setValidator(longitude)

        self.speed.setValidator(QIntValidator(1, 200, self.speed))
        self.speed.setMaxLength(3)

        name = QRegExpValidator(QRegExp(r'[A-Za-z0-9-]+'))
        self.name.setValidator(name)
        self.name.setMaxLength(20)


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
    defaultPhenomena = ['CB', 'TCU', 'TS', 'TSGR']

    defaults = {
        'description': 'ISOL',
        'phenomenon': 'CB',
        'comeFrom': 'FCST',
        'flightLevelFormat': 'TOP',
        'direction': 'N',
        'intensityChange': 'NC',
    }


class SigmetCancel(BaseSigmet, Ui_sigmet_cancel.Ui_Editor):

    def __init__(self, header, conf=None):
        super().__init__(conf=conf)
        self.setupUi(self)
        self.cancelSequenceLine = self.cancelSequence.lineEdit()
        self.state = SigmetCancelState(header=header)
        self.initialize()
        self.pipeline.sync({**self.fromState(), **self.defaults}, source='init', derive=True)

    def bindSignal(self):
        super().bindSignal()
        self.cancelSequence.activated[int].connect(self.selectCancelIndex)

    def selectCancelIndex(self, index):
        if index < 0 or index == self.pipeline.value('cancelIndex', None):
            return
        text = self.cancelSequence.itemText(index)
        self.pipeline.edit({'cancelIndex': index, 'cancelSequence': text}, source='user', force=True)

    def editText(self, field, line, text):
        if field == 'cancelSequence':
            upper = text.upper()
            if upper != text:
                setLineText(line, upper)
            self.pipeline.edit({'cancelSequence': upper, 'cancelIndex': None})
            return

        super().editText(field, line, text)

    def rules(self, raw, previous, changed, source):
        cancelRules(
            raw,
            previous,
            changed,
            source,
            resolveValid=self.findValid,
            adjustBeginning=self.adjustCancelTimes,
        )

    def adjustCancelTimes(self, raw, cancelBegin, cancelEnd):
        if isAcceptable(self.cancelEndingTime, cancelEnd):
            raw['endingTime'] = cancelEnd

        if isAcceptable(self.cancelBeginningTime, cancelBegin):
            start, _ = self.periodTime()
            beginning = adjustCancelBeginning(
                cancelBegin,
                start,
                raw.get('endingTime', ''),
                utcnow(),
            )
            raw['beginningTime'] = beginning.strftime('%d%H%M')

    def bindings(self):
        return super().bindings() + [
            (self.cancelBeginningTime, 'cancelBeginningTime'),
            (self.cancelEndingTime, 'cancelEndingTime'),
            (self.cancelSequence.lineEdit(), 'cancelSequence'),
        ]

    def fromState(self):
        raw = super().fromState()
        raw.update({
            'cancelIndex': None,
            'cancelSequence': self.state.cancelSequence,
            'cancelBeginningTime': self.state.cancelBeginningTime,
            'cancelEndingTime': self.state.cancelEndingTime,
        })
        return raw

    def fromWidgets(self):
        raw = super().fromWidgets()
        index = self.cancelSequence.currentIndex()
        text = self.cancelSequence.currentText()
        matchedIndex = index if 0 <= index < self.cancelSequence.count() and self.cancelSequence.itemText(index) == text else None
        raw.update({
            'cancelIndex': matchedIndex,
            'cancelSequence': text,
            'cancelBeginningTime': self.cancelBeginningTime.text(),
            'cancelEndingTime': self.cancelEndingTime.text(),
        })
        return raw

    def apply(self, raw):
        super().apply(raw)
        self.state.cancelSequence = raw.get('cancelSequence', '').strip()
        self.state.cancelBeginningTime = raw.get('cancelBeginningTime', '')
        self.state.cancelEndingTime = raw.get('cancelEndingTime', '')

    def populate(self, raw=None):
        if raw is None:
            self.pipeline.sync(self.fromState())
            return

        super().populate(raw)
        cancelIndex = raw.get('cancelIndex')
        cancelSequence = raw.get('cancelSequence', '')
        with QSignalBlocker(self.cancelSequence):
            if cancelIndex is not None and 0 <= cancelIndex < self.cancelSequence.count():
                if self.cancelSequence.currentIndex() != cancelIndex:
                    self.cancelSequence.setCurrentIndex(cancelIndex)
            elif cancelSequence == '' and self.cancelSequence.currentIndex() != -1:
                self.cancelSequence.setCurrentIndex(-1)
        setLineText(self.cancelSequence.lineEdit(), cancelSequence)
        setLineText(self.cancelBeginningTime, raw.get('cancelBeginningTime', ''))
        setLineText(self.cancelEndingTime, raw.get('cancelEndingTime', ''))
        coloredText(self.cancelSequence.lineEdit())
        coloredText(self.cancelBeginningTime)
        coloredText(self.cancelEndingTime)

    def setupValidator(self):
        super().setupValidator()
        sequence = QRegExpValidator(QRegExp(self.patterns.sequence, Qt.CaseInsensitive))
        self.cancelSequence.setValidator(sequence)

        date = QRegExpValidator(QRegExp(self.patterns.date))
        self.cancelBeginningTime.setValidator(date)
        self.cancelEndingTime.setValidator(date)

    def setCandidates(self, sigmets):
        """Refill the dropdown with the cancellable reports the presenter
        handed over, each row carrying its valid period as item data:
        same-numbered rows differ in their data, not in their text."""
        options = []
        for sig in sigmets:
            parser = sig.parser()
            options.append((parser.sequence(), parser.validTime()))

        with QSignalBlocker(self.cancelSequence):
            setComboOptions(self.cancelSequence, options)

        if options:
            self.pipeline.edit({'cancelIndex': 0, 'cancelSequence': options[0][0]}, source='seed', force=True)
        else:
            self.pipeline.edit({
                'cancelIndex': None,
                'cancelSequence': '',
                'cancelBeginningTime': '',
                'cancelEndingTime': '',
            }, source='seed', force=True)

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

    rules = staticmethod(customRules)

    def __init__(self, header, conf=None):
        super().__init__(conf=conf)
        self.setupUi(self)
        self.state = SigmetCustomState(header=header)
        self.setupApiSign()
        self.initialize()
        self.upperTextEdit()
        self.pipeline.sync({**self.fromState(), **self.defaults}, source='init', derive=True)

    def bindSignal(self):
        super().bindSignal()
        self.text.textChanged.connect(lambda: self.pipeline.edit({'text': self.text.toPlainText()}))

    def fromState(self):
        raw = super().fromState()
        raw['text'] = self.state.text
        return raw

    def fromWidgets(self):
        raw = super().fromWidgets()
        raw['text'] = self.text.toPlainText()
        return raw

    def apply(self, raw):
        super().apply(raw)
        self.state.text = raw.get('text', '').strip()

    def populate(self, raw=None):
        if raw is None:
            self.pipeline.sync(self.fromState())
            return

        super().populate(raw)
        setPlainText(self.text, raw.get('text', ''))

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

        if rv:
            _, message = rv
            fir = self.conf.firName or ''
            text = filterCustomText(message.replace(fir, '').replace('=', '').strip())
        else:
            text = ''

        self.pipeline.edit({'text': text}, source='seed', force=True)
        if text:
            self.text.moveCursor(QTextCursor.End)

    def resizeEvent(self, event):
        self.apiSign.move(self.width() - 43, 80)
        super().resizeEvent(event)
