import datetime

from PyQt5.QtGui import QIcon, QRegExpValidator
from PyQt5.QtCore import Qt, QRegExp, QCoreApplication, QTimer, pyqtSignal
from PyQt5.QtWidgets import QWidget, QLabel, QLineEdit, QToolButton, QMessageBox, QHBoxLayout, QVBoxLayout

from tafor.core.parsers.base import Pattern
from tafor.core.taf import (GroupState, PrimaryState, SegmentState, TemperatureState, TrendState,
    TafFormValidator, TrendFormValidator, completeGroupPeriod, formatValidityEnd,
    isGroupStartAcceptable, normalizeTemperatureTime, parseWindSpeed)
from tafor.core.utils.time import parseDayHour, parsePeriod, parseTime, utcnow
from tafor.core.utils.common import iconPath
from tafor.ui.fonts import fixedFont
from tafor.ui.forms.base import TextFieldMixin
from tafor.ui.qt import Ui_taf_group, Ui_taf_primary, Ui_trend


def separatePeriod(text, previous):
    """Append the '/' separator after the four-digit day while typing.

    ``previous`` is the text from the last keystroke; the caller keeps that
    snapshot on its own instance.
    """
    if len(text) > len(previous) and len(text) == 4:
        return text + '/'
    return text


def normalizePeriod(text, previous, window):
    """Spell the typed period the one way the field accepts.

    Two respellings, both of the same instant: the separator after a
    four-digit day, and an end at midnight 00 written as 24 of the day
    before, the spelling that fits the validity window. Completion is not
    here: that adds what the operator has not typed, not how it is written.

    ``window`` is the (start, end) the text spells, as read from the state,
    or None when the field cannot read it yet.
    """
    text = separatePeriod(text, previous)

    if window is not None:
        start, end = window
        if end.hour == 0 and not text.endswith('24'):
            return '{:02d}{:02d}/{}'.format(start.day, start.hour, formatValidityEnd(end))

    return text


def _translate(code, **kwargs):
    # The table is built per call on purpose: installTranslations() runs in
    # main(), after this module is imported, so a module-level dict would freeze
    # the untranslated strings.
    messages = {
        TafFormValidator.WEATHER_CONFLICT: QCoreApplication.translate(
            'Editor', 'Weather phenomena conflict'),
        TafFormValidator.GUST_SPEED_INSUFFICIENT: QCoreApplication.translate(
            'Editor', 'Gust speed must be greater than wind speed by at least 5'),
        TafFormValidator.CLOUD_HEIGHT_CONFLICT: QCoreApplication.translate(
            'Editor', 'Cloud cover with different oktas should not at the same height'),
        TafFormValidator.CLOUD_OKTAS_EXCEED: QCoreApplication.translate(
            'Editor', 'Cloud cover cannot be more than 8 oktas at the same height'),
        TafFormValidator.CLOUD_ABOVE_OVC: QCoreApplication.translate(
            'Editor', 'No clouds should above overcast clouds'),
        TafFormValidator.GROUP_PERIOD_EXCEED: QCoreApplication.translate(
            'Editor', 'Change group time more than {span} hours').format(span=kwargs.get('span', '')),
        TafFormValidator.GROUP_START_INVALID: QCoreApplication.translate(
            'Editor', 'Start time of change group is not correct'),
        TafFormValidator.GROUP_END_INVALID: QCoreApplication.translate(
            'Editor', 'End time of change group is not correct'),
        TafFormValidator.GROUP_OVERLAP: QCoreApplication.translate(
            'Editor', 'Change group time is overlap'),
        TafFormValidator.FM_TIME_INVALID: QCoreApplication.translate(
            'Editor', 'Time of change group is not correct'),
        TafFormValidator.TEMP_TIME_INVALID: QCoreApplication.translate(
            'Editor', 'The time of temperature is not correct'),
        TafFormValidator.TEMP_MAX_LESS_MIN: QCoreApplication.translate(
            'Editor', 'The maximum temperature needs to be greater than the minimum temperature'),
        TafFormValidator.TEMP_MIN_GREATER_MAX: QCoreApplication.translate(
            'Editor', 'The minimum temperature needs to be less than the maximum temperature'),
        TrendFormValidator.TREND_TIME_INVALID: QCoreApplication.translate(
            'Editor', 'Trend valid time is not correct'),
    }
    return messages.get(code, code)


class BaseSegment(TextFieldMixin, QWidget):

    contentChanged = pyqtSignal()
    notified = pyqtSignal(str)

    def __init__(self, name=None, conf=None, context=None):
        super().__init__()
        self.rules = Pattern()
        self.conf = conf
        self.context = context
        self.indicator = name
        # Initialize specific state based on the type of widget
        unit = self.conf.units.tafSpeed
        if self.indicator == 'PRIMARY':
            self.state = PrimaryState(icao=self.conf.airport, unit=unit, spec=self.context.taf.spec)
        elif self.indicator in ['TEMPO', 'BECMG', 'FM']:
            self.state = GroupState(indicator=self.indicator, unit=unit)
        elif self.indicator == 'TREND':
            self.state = TrendState(unit=unit)
        else:
            self.state = SegmentState(unit=unit)

    def onUserEdited(self, *args):
        """The commit entry point: the operator changed a widget."""
        # textEdited is emitted before textChanged. The cross-field writers
        # below normally hang off textChanged, so run the same derivation here
        # before reading the fields they may clear.
        sender = self.sender()
        if sender is self.wind:
            self.setGust()
        elif sender is self.weather.lineEdit():
            self.setWeatherWithIntensity(sender.text())
        elif sender is self.cloud1:
            self.setVv()

        self.reload()

    def fields(self):
        """The line edits whose text feeds the state."""
        return [self.wind, self.gust, self.vis,
                self.weather.lineEdit(), self.weatherWithIntensity.lineEdit(),
                self.cloud1, self.cloud2, self.cloud3, self.cb]

    def toggles(self):
        """The check boxes and radio buttons whose value feeds the state."""
        return [self.cavok, self.nsc] if hasattr(self, 'cavok') else []

    def deferred(self):
        """Fields whose edit needs more than a read: they commit themselves.

        A deferred field writes before the state is read -- a completion, a
        separator -- so it goes through resolve() instead of onUserEdited(),
        and the state is read once, after that write.
        """
        return []

    def resolve(self, *args):
        """Finish a deferred field's edit, then read it: its own commit.

        Declared in deferred(); a field that needs one implements it in the
        same class that lists it.
        """
        raise NotImplementedError

    def bindSignal(self):
        if hasattr(self, 'cavok'):
            self.cavok.toggled.connect(self.setCavok)
            self.nsc.toggled.connect(self.setNsc)

        self.wind.textChanged.connect(self.setGust)
        self.gust.editingFinished.connect(self.validateGust)
        self.weather.lineEdit().textChanged.connect(self.setWeatherWithIntensity)
        self.weather.lineEdit().editingFinished.connect(lambda: self.validateWeather(self.weather))
        self.weatherWithIntensity.lineEdit().editingFinished.connect(lambda: self.validateWeather(self.weatherWithIntensity))
        self.cloud1.textChanged.connect(self.setVv)
        self.cloud1.editingFinished.connect(lambda: self.validateCloud(self.cloud1))
        self.cloud2.editingFinished.connect(lambda: self.validateCloud(self.cloud2))
        self.cloud3.editingFinished.connect(lambda: self.validateCloud(self.cloud3))
        self.cb.editingFinished.connect(lambda: self.validateCloud(self.cb))

        for line in self.fields():
            line.textChanged.connect(lambda _, current=line: self.coloredText(current))
            line.textEdited.connect(lambda _, current=line: self.upperText(current))
            slot = self.resolve if line in self.deferred() else self.onUserEdited
            line.textEdited.connect(slot)

        for toggle in self.toggles():
            toggle.clicked.connect(self.onUserEdited)

    def collect(self):
        """Read the widgets into the state."""
        self.state.wind = self.wind.text() if self.wind.hasAcceptableInput() else ""
        self.state.gust = self.gust.text() if self.gust.hasAcceptableInput() else ""
        self.state.visibility = self.vis.text() if self.vis.hasAcceptableInput() else ""
        self.state.weather = self.weather.currentText() if self.weather.lineEdit().hasAcceptableInput() else ""
        self.state.weatherWithIntensity = self.weatherWithIntensity.currentText() if self.weatherWithIntensity.lineEdit().hasAcceptableInput() else ""
        
        clouds = []
        if self.cloud1.hasAcceptableInput(): clouds.append(self.cloud1.text())
        if self.cloud2.hasAcceptableInput(): clouds.append(self.cloud2.text())
        if self.cloud3.hasAcceptableInput(): clouds.append(self.cloud3.text())
        if self.cb.hasAcceptableInput(): clouds.append(self.cb.text() + 'CB')
        self.state.clouds = clouds
        
        if hasattr(self, 'cavok'):
            self.state.isCavok = self.cavok.isChecked()
            self.state.isNsc = self.nsc.isChecked()

    def populate(self):
        """Write the state back into the widgets, the inverse of collect().

        `collect(); populate(); collect()` leaves the state unchanged, which
        is the property that keeps the two directions honest. Each subclass
        writes the fields it owns and leaves the rest alone.

        This is a programmatic write: textChanged still drives the derived
        widget behaviour, but textEdited does not fire, so it cannot collect
        the fields that have not been rendered yet.
        """
        # The CB layer is an entry with a 'CB' suffix; the widget holds the
        # bare six characters, so the suffix comes off again on the way back.
        layers = [cloud for cloud in self.state.clouds if not cloud.endswith('CB')]
        cb = next((cloud for cloud in self.state.clouds if cloud.endswith('CB')), '')

        self.wind.setText(self.state.wind)
        self.gust.setText(self.state.gust)
        self.vis.setText(self.state.visibility)
        self.weather.setCurrentText(self.state.weather)
        self.weatherWithIntensity.setCurrentText(self.state.weatherWithIntensity)
        self.cb.setText(cb[:-2])
        for index, line in enumerate((self.cloud1, self.cloud2, self.cloud3)):
            line.setText(layers[index] if index < len(layers) else '')

        if hasattr(self, 'cavok'):
            self.cavok.setChecked(self.state.isCavok)
            self.nsc.setChecked(self.state.isNsc)

    def setupPeriodPlaceholder(self):
        raise NotImplementedError

    def setClouds(self, enable):
        if enable:
            self.cloud1.setEnabled(True)
            self.cloud2.setEnabled(True)
            self.cloud3.setEnabled(True)
            self.cb.setEnabled(True)
        else:
            self.cloud1.clear()
            self.cloud1.setEnabled(False)
            self.cloud2.clear()
            self.cloud2.setEnabled(False)
            self.cloud3.clear()
            self.cloud3.setEnabled(False)
            self.cb.clear()
            self.cb.setEnabled(False)

    def setCavok(self, checked):
        if checked:
            self.nsc.setChecked(False)

            self.vis.clear()
            self.vis.setEnabled(False)
            self.weather.setEnabled(False)
            self.weather.setCurrentIndex(-1)
            self.weatherWithIntensity.setEnabled(False)
            self.weatherWithIntensity.setCurrentIndex(-1)
            self.setClouds(False)
        else:
            self.vis.setEnabled(True)
            self.weather.setEnabled(True)
            self.weatherWithIntensity.setEnabled(True)
            self.setClouds(True)

    def setNsc(self, checked):
        if checked:
            self.cavok.setChecked(False)
            self.setClouds(False)
        else:
            self.setClouds(True)

    def setVv(self):
        if self.cloud1.text().startswith('V'):
            self.cloud2.setEnabled(False)
            self.cloud3.setEnabled(False)
            self.cb.setEnabled(False)
            self.cloud2.clear()
            self.cloud3.clear()
            self.cb.clear()
            self.cloud1Label.setText(QCoreApplication.translate('Editor', 'Vertical Visibility'))
        else:
            self.cloud2.setEnabled(True)
            self.cloud3.setEnabled(True)
            self.cb.setEnabled(True)
            self.cloud1Label.setText(QCoreApplication.translate('Editor', 'Cloud'))

    def setGust(self):
        if self.wind.hasAcceptableInput() and parseWindSpeed(self.wind.text()) == 0:
            self.gust.setEnabled(False)
            self.gust.clear()
        else:
            self.gust.setEnabled(True)

    def setWeatherWithIntensity(self, text):
        if text.upper() == 'NSW':
            self.weatherWithIntensity.setCurrentIndex(-1)
            self.weatherWithIntensity.setEnabled(False)
        else:
            self.weatherWithIntensity.setEnabled(True)

    def setupValidator(self):
        wind = QRegExpValidator(QRegExp(self.rules.wind, Qt.CaseInsensitive))
        self.wind.setValidator(wind)

        gust = QRegExpValidator(QRegExp(self.rules.gust, Qt.CaseInsensitive))
        self.gust.setValidator(gust)

        vis = QRegExpValidator(QRegExp(self.rules.vis))
        self.vis.setValidator(vis)

        cloud = QRegExpValidator(QRegExp(self.rules.cloud, Qt.CaseInsensitive))
        vvCloud = QRegExpValidator(QRegExp(r'({})|({})'.format(self.rules.cloud, self.rules.vv), Qt.CaseInsensitive))
        self.cloud1.setValidator(vvCloud)
        self.cloud2.setValidator(cloud)
        self.cloud3.setValidator(cloud)
        self.cb.setValidator(cloud)

        weathers = self.conf.weatherList
        if self.indicator == 'PRIMARY':
            weathers = [w for w in weathers if w != 'NSW']
        self.weather.addItems([''] + weathers)
        weather = QRegExpValidator(QRegExp(r'{}'.format('|'.join(weathers)), Qt.CaseInsensitive))
        self.weather.setValidator(weather)

        weathers = self.conf.weatherWithIntensityList
        intensityWeathers = ['']
        if weathers:
            for w in weathers:
                intensityWeathers.append('-{}'.format(w))
            for w in weathers:
                intensityWeathers.append(w)
            for w in weathers:
                intensityWeathers.append('+{}'.format(w))
        self.weatherWithIntensity.addItems(intensityWeathers)
        intensityWeather = QRegExpValidator(QRegExp(r'[-+]?({})'.format('|'.join(weathers)), Qt.CaseInsensitive))
        self.weatherWithIntensity.setValidator(intensityWeather)

    def validateWeather(self, line):
        error = TafFormValidator.checkWeather(self.state)
        if error:
            line.setCurrentIndex(-1)
            self.notified.emit(_translate(error))

    def validateGust(self):
        error = TafFormValidator.checkGust(self.state)
        if error:
            self.gust.clear()
            self.notified.emit(_translate(error))

    def validateCloud(self, line):
        error = TafFormValidator.checkCloud(self.state, line.text())
        if error:
            self.notified.emit(_translate(error))
            line.clear()
            return

    def validate(self):
        self.validateGust()
        self.validateWeather(self.weather)
        self.validateCloud(self.cloud3)
        self.validateCloud(self.cloud2)
        self.validateCloud(self.cloud1)
        self.validateCloud(self.cb)

    def message(self):
        return self.state.composeMessage()

    def hasAcceptableInput(self):
        return self.state.isAcceptable()

    def clear(self):
        """Empty the state, then populate it again."""
        self.state.clear()
        self.populate()
        self.contentChanged.emit()


class TemperatureGroup(TextFieldMixin, QWidget):
    """One temperature group: a value, the time it happened at, and the rules
    that tie them to the rest of the report.

    `primary` is the primary report's *state*, not its widget -- this class knows
    neither the primary segment nor the editor. It registers its own state as it
    is built, which is how the message finds it, and it reports a rejected value
    through `notified` rather than reaching for the editor itself.
    """

    contentChanged = pyqtSignal()
    notified = pyqtSignal(str)

    def __init__(self, mode='max', canSwitch=False, primary=None, parent=None):
        super().__init__(parent)
        self.state = TemperatureState(mode)
        self.canSwitch = canSwitch
        self.rules = Pattern()
        self.primary = primary

        primary.addTemperature(self.state)

        self.setupUi()
        self.setupValidator()
        self.bindSignal()

    def setupUi(self):
        layout = QVBoxLayout()
        labelLayout = QHBoxLayout()
        lineLayout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.temp = QLineEdit()
        self.tempTime = QLineEdit()
        lineLayout.addWidget(self.temp)
        lineLayout.addWidget(self.tempTime)

        self.label = QLabel()
        self.switchButton = QToolButton()
        self.switchButton.setAutoRaise(True)
        labelLayout.addWidget(self.label)
        labelLayout.addWidget(self.switchButton)
        self.setLabel()

        if not self.canSwitch:
            self.switchButton.hide()

        layout.addLayout(labelLayout)
        layout.addLayout(lineLayout)
        self.setLayout(layout)
        self.setMaximumWidth(77)

    def bindSignal(self):
        if self.canSwitch:
            self.switchButton.clicked.connect(self.switchMode)

        # The temperature lines carry their own cosmetic policy: the primary
        # segment no longer sweeps them up.
        for line in (self.temp, self.tempTime):
            line.textChanged.connect(lambda _, current=line: self.coloredText(current))
            line.textEdited.connect(lambda _, current=line: self.upperText(current))
            line.textEdited.connect(self.onUserEdited)

        self.tempTime.editingFinished.connect(self.validateTemperatureTime)
        self.temp.editingFinished.connect(self.validateTemperature)

    def collect(self):
        self.state.value = self.temp.text() if self.temp.hasAcceptableInput() else ""
        self.state.time = self.tempTime.text() if self.tempTime.hasAcceptableInput() else ""

    def onUserEdited(self, *args):
        self.collect()
        self.contentChanged.emit()

    def setupValidator(self):
        temperature = QRegExpValidator(QRegExp(self.rules.temperature, Qt.CaseInsensitive))
        self.temp.setValidator(temperature)

        dayHour = QRegExpValidator(QRegExp(self.rules.dayHour))
        self.tempTime.setValidator(dayHour)

    def setLabel(self):
        if self.state.mode == 'max':
            text = QCoreApplication.translate('Editor', 'Max Temperature')
            icon = 'warm'
        else:
            text = QCoreApplication.translate('Editor', 'Min Temperature')
            icon = 'cold'

        self.label.setText(text)
        self.switchButton.setIcon(QIcon(iconPath('{}.png'.format(icon))))

    def validateTemperatureTime(self):
        if not self.primary.period or not self.tempTime.hasAcceptableInput():
            return

        error = TafFormValidator.checkTemperatureTime(
            self.state,
            self.primary.temperatures,
            self.primary.durations,
        )
        if error:
            self.state.time = ""
            self.tempTime.clear()
            self.notified.emit(_translate(error))
            return

        # Time normalization can stay in UI or move to state, keep here for now as it affects UI text
        time = parseDayHour(self.state.time[:2], self.state.time[2:], self.primary.durations[0], delta='month')
        normalized = normalizeTemperatureTime(time, self.primary.durations)
        if normalized:
            self.tempTime.setText(normalized)

    def validateTemperature(self):
        if not self.temp.hasAcceptableInput():
            return

        error = TafFormValidator.checkTemperature(
            self.state,
            self.primary.temperatures,
        )
        if error:
            self.state.value = ""
            self.temp.clear()
            self.notified.emit(_translate(error))
            return

    def switchMode(self):
        self.state.mode = 'min' if self.state.mode == 'max' else 'max'
        self.setLabel()
        self.validateTemperature()
        self.validateTemperatureTime()

    def widgets(self):
        if self.canSwitch:
            return [self.switchButton, self.temp, self.tempTime]

        return [self.temp, self.tempTime]

    def populate(self):
        """The inverse of collect().

        The mode is not rendered: switchMode() owns it, and
        TemperatureState.clear() deliberately leaves it alone.
        """
        self.temp.setText(self.state.value)
        self.tempTime.setText(self.state.time)

    def clear(self):
        """Empty the state, then populate it again."""
        self.state.clear()
        self.populate()


class TafPrimarySegment(BaseSegment, Ui_taf_primary.Ui_Editor):

    modifierChanged = pyqtSignal(object)
    periodShiftRequested = pyqtSignal(str)

    def __init__(self, name='PRIMARY', conf=None, context=None):
        super().__init__(name, conf, context)
        self.setupUi(self)

        self.setupValidator()
        self.period.setEnabled(False)
        self.sequence.setEnabled(False)

        self.groupCheckboxs = [
            self.fmCheckbox,
            self.becmg1Checkbox, self.becmg2Checkbox, self.becmg3Checkbox,
            self.tempo1Checkbox, self.tempo2Checkbox, self.tempo3Checkbox,
        ]

        # The groups register their own states with self.state as they are
        # built; this list is only for layout, tab order and clearing.
        self.tmax = TemperatureGroup(mode='max', primary=self.state, parent=self)
        self.tmin = TemperatureGroup(mode='min', primary=self.state, parent=self)
        self.temperatureLayout.addWidget(self.tmax)
        self.temperatureLayout.addWidget(self.tmin)
        self.temperatures = [self.tmax, self.tmin]

        if self.context.taf.spec.duration == datetime.timedelta(hours=30):
            self.temp = TemperatureGroup(canSwitch=True, primary=self.state, parent=self)
            self.temperatureLayout.addWidget(self.temp)
            self.temperatures.append(self.temp)
            self.becmg3Checkbox.setStyleSheet('QCheckBox {margin-top: 4px;}')
            self.tempo3Checkbox.setStyleSheet('QCheckBox {margin-top: 4px;}')

        self.prevButton.setIcon(QIcon(iconPath('back.png')))
        self.resetButton.setIcon(QIcon(iconPath('reset.png')))

        self.setupFont()
        self.bindSignal()
        self.initMessageSpec()
        self.setOrder()

    def collect(self):
        super().collect()
        self.state.date = self.date.text()
        self.state.period = self.period.text()
        self.state.sequence = self.sequence.text()
        self.state.modifier = self.modifier

    @property
    def modifier(self):
        """The modifier the radios are on: None, 'AMD', 'COR' or 'CNL'.

        The four radios share one exclusive group, so at most one is on. NORMAL is
        absent from the mapping on purpose -- it is not a marker but the lack of
        one, so it comes out as None, the same value the state spells it with.
        """
        for radio, modifier in ((self.cor, 'COR'), (self.amd, 'AMD'), (self.cnl, 'CNL')):
            if radio.isChecked():
                return modifier

    def populate(self):
        """Draw the whole header from the draft.

        Period, modifier and sequence are document facts now: draft.begin() fixes
        them before the draw, so populating can write them like any other field.
        They are programmatic writes, so they do not collect the header that has
        not been written yet.

        `date` is the one field left out: it belongs to the clock, and the timer
        in this widget owns it.
        """
        super().populate()
        self.period.setText(self.state.period)
        self.setModifier(self.state.modifier)
        self.sequence.setText(self.state.sequence)
        for t in self.temperatures:
            t.populate()

    def setModifier(self, modifier):
        """Show the modifier without going back through updateModifier().

        setChecked() emits toggled, not clicked, so it populates rather than
        a commit.
        """
        radios = {'AMD': self.amd, 'COR': self.cor, 'CNL': self.cnl}
        radios.get(modifier, self.normal).setChecked(True)

    def setOrder(self):
        orders = [self.nsc]
        for t in self.temperatures:
            orders += t.widgets()

        for p, n in zip(orders, orders[1:]):
            self.setTabOrder(p, n)

    def setupValidator(self):
        super().setupValidator()

        date = QRegExpValidator(QRegExp(self.rules.date))
        self.date.setValidator(date)

    def fields(self):
        return super().fields() + [self.date, self.period, self.sequence]

    def toggles(self):
        return super().toggles() + [self.normal, self.cor, self.amd, self.cnl]

    def bindSignal(self):
        super().bindSignal()

        self.normal.clicked.connect(lambda: self.modifierChanged.emit(self.modifier))
        self.cor.clicked.connect(lambda: self.modifierChanged.emit(self.modifier))
        self.amd.clicked.connect(lambda: self.modifierChanged.emit(self.modifier))
        self.cnl.clicked.connect(lambda: self.modifierChanged.emit(self.modifier))
        self.prevButton.clicked.connect(lambda: self.requestPeriodShift('prev'))
        self.resetButton.clicked.connect(lambda: self.requestPeriodShift('current'))

        for t in self.temperatures:
            t.contentChanged.connect(self.collect)
            t.contentChanged.connect(self.contentChanged.emit)
            t.notified.connect(self.notified.emit)

        # Parented to the widget: an unparented timer is not in the widget tree,
        # and only runs while the segment is visible.
        self.timer = QTimer(self)
        self.timer.setInterval(1 * 1000)
        self.timer.timeout.connect(self.setDate)

    def validate(self):
        super().validate()
        for t in self.temperatures:
            t.validateTemperatureTime()
            t.validateTemperature()

    def initMessageSpec(self):
        if self.context.taf.spec.designator == 'FT':
            self.tempo3Checkbox.show()
        else:
            self.tempo3Checkbox.hide()
            self.tempo3Checkbox.setChecked(False)

    def setSequenceValidator(self, modifier):
        """The sequence field's part of the change: enabled for a marked report,
        with the validator that matches the marker."""
        if modifier is None:
            self.sequence.setEnabled(False)
            return

        pattern = self.rules.ccc if modifier == 'COR' else self.rules.aaa
        self.sequence.setValidator(QRegExpValidator(QRegExp(pattern, Qt.CaseInsensitive)))
        self.sequence.setEnabled(True)

    def setGroupCheckboxes(self, enabled):
        """A cancellation carries no change groups; every other report may."""
        for checkbox in self.groupCheckboxs:
            checkbox.setEnabled(enabled)

    def requestPeriodShift(self, action):
        if action == 'prev':
            title = QCoreApplication.translate('Editor', 'Tips')
            text = QCoreApplication.translate('Editor', 'Do you want to change the message valid period to previous?')
            ret = QMessageBox.question(self, title, text)
            if ret != QMessageBox.Yes:
                return

        self.periodShiftRequested.emit(action)

    def setDate(self):
        time = utcnow()
        self.date.setText(time.strftime('%d%H%M'))

    def showEvent(self, event):
        super().showEvent(event)
        self.setDate()
        self.timer.start()

    def hideEvent(self, event):
        self.timer.stop()
        super().hideEvent(event)

    def closeEvent(self, event):
        self.timer.stop()
        super().closeEvent(event)

    def isCancelMode(self):
        return self.modifier == 'CNL'


class TafGroupSegment(BaseSegment, Ui_taf_group.Ui_Editor):
    """A change group: its own weather fields, and a period that only makes
    sense against the primary report's validity window.

    `primary` is the primary report's *state*, not its widget: the window and
    the period text are read from it live, because the operator may still be
    moving them while this group is being filled.
    """

    periodFinished = pyqtSignal()

    def __init__(self, name='TEMPO', conf=None, context=None, primary=None):
        super().__init__(name, conf, context)
        self.primary = primary
        self.setupUi(self)
        self.name.setText(name)
        self.setupFont()
        self.setupValidator()
        self.bindSignal()
        self.periodText = ''

    def clearPeriod(self):
        self.period.clear()
        self.reload()

    def fields(self):
        return super().fields() + [self.period]

    def collect(self):
        super().collect()
        self.state.period = self.period.text()
        self.state.durations = self.durations()

    def durations(self):
        """The window this period spells, against the primary's base time.

        Derived where it is read, not where the text changed: the same text
        always gives the same window, and collect() is the one place a field
        is read.
        """
        if not (self.period.hasAcceptableInput() and self.primary.period):
            return None

        return parsePeriod(self.period.text(), self.primary.durations[0])

    def populate(self):
        super().populate()
        self.period.setText(self.state.period)
        # periodText is the auto-completion bookkeeping, not state: it tracks the
        # text the operator can see, so populating sets it to what was just written.
        self.periodText = self.state.period

    def deferred(self):
        return [self.period]

    def bindSignal(self):
        super().bindSignal()
        self.period.editingFinished.connect(self.periodFinished.emit)

    def setupFont(self):
        super().setupFont()
        self.name.setFont(fixedFont())

    def setupValidator(self):
        super().setupValidator()
        period = QRegExpValidator(QRegExp(self.rules.period))
        self.period.setValidator(period)

    def setupPeriodPlaceholder(self):
        if self.primary.durations is None:
            self.period.setPlaceholderText('')
            return

        time = self.primary.durations[0]
        self.period.setPlaceholderText('{:02d}'.format(time.day))

    def resolve(self, *args):
        """The period's own commit: normalize its text, then read it once."""
        self.normalizePeriod()
        self.reload()

    def normalizePeriod(self):
        """Bring the typed period to the form the field accepts.

        Completion adds what the operator has not typed yet; normalisation
        only writes the same instant another way. Both write the line, so
        reload() still does the one read.
        """
        if self.conf.autoCompletionGroupTime and not self.autoCompletePeriod():
            return

        text = normalizePeriod(self.period.text(), self.periodText, self.durations())
        if text != self.period.text():
            self.period.setText(text)
        self.periodText = text

    def autoCompletePeriod(self):
        """Complete a freshly typed four-digit start into a full period.

        Returns False when the text must be left as typed: there is no window
        to complete against, or the start does not fit in it.
        """
        if self.primary.durations is None or not self.primary.period:
            return False

        text = self.period.text()
        if len(text) > len(self.periodText):
            if len(text) == 4:
                if not isGroupStartAcceptable(text, self.primary.durations):
                    return False

                if self.indicator in ('TEMPO', 'BECMG'):
                    completed = completeGroupPeriod(
                        text,
                        self.primary.durations,
                        self.indicator,
                        self.context.taf.spec,
                    )
                    if completed is None:
                        return False

                    text = completed

            self.period.setText(text)

        self.periodText = text
        return True

    def showEvent(self, event):
        super().showEvent(event)
        self.setupPeriodPlaceholder()



class TafFmSegment(TafGroupSegment):

    def __init__(self, name='FM', conf=None, context=None, primary=None):
        super().__init__(name, conf, context, primary)

    def resolve(self, *args):
        """FM's period is a single time: nothing to finish, just read it."""
        self.reload()

    def setupValidator(self):
        super().setupValidator()
        period = QRegExpValidator(QRegExp(self.rules.fmPeriod))
        self.period.setValidator(period)

    def durations(self):
        if not (self.period.hasAcceptableInput() and self.primary.period):
            return None

        time = parseTime(self.period.text(), self.primary.durations[0])
        return (time, time)


class TafBecmgSegment(TafGroupSegment):

    def __init__(self, name='BECMG', conf=None, context=None, primary=None):
        super().__init__(name, conf, context, primary)


class TafTempoSegment(TafGroupSegment):

    def __init__(self, name='TEMPO', conf=None, context=None, primary=None):
        super().__init__(name, conf, context, primary)
        self.cavok.hide()
        self.nsc.hide()


class TrendSegment(BaseSegment, Ui_trend.Ui_Editor):

    def __init__(self, name='TREND', conf=None, context=None):
        super().__init__(name, conf, context)
        self.setupUi(self)
        self.setupFont()
        self.setupValidator()
        self.bindSignal()
        self.periodText = ''

    def fields(self):
        return super().fields() + [self.period]

    def toggles(self):
        return super().toggles() + [self.nosig, self.at, self.fm, self.tl,
                                    self.becmg, self.tempo]

    def collect(self):
        super().collect()
        self.state.isNosig = self.nosig.isChecked()
        self.state.indicator = "BECMG" if self.becmg.isChecked() else "TEMPO"
        self.state.atChecked = self.at.isChecked()
        self.state.fmChecked = self.fm.isChecked()
        self.state.tlChecked = self.tl.isChecked()
        self.state.period = self.period.text()

    def populate(self):
        super().populate()
        self.nosig.setChecked(self.state.isNosig)
        self.becmg.setChecked(self.state.indicator == 'BECMG')
        self.tempo.setChecked(self.state.indicator != 'BECMG')
        self.at.setChecked(self.state.atChecked)
        self.fm.setChecked(self.state.fmChecked)
        self.tl.setChecked(self.state.tlChecked)
        # Last: unchecking at/fm/tl clears and disables the period through
        # setAt()/setFmTl(), and setNosig() re-derives what is enabled.
        self.period.setText(self.state.period)

    def deferred(self):
        return [self.period]

    def bindSignal(self):
        super().bindSignal()
        self.nosig.toggled.connect(self.setNosig)
        self.at.toggled.connect(self.setAt)
        self.fm.toggled.connect(self.setFmTl)
        self.tl.toggled.connect(self.setFmTl)

        self.becmg.clicked.connect(self.updateAtStatus)
        self.tempo.clicked.connect(self.updateAtStatus)

        self.period.editingFinished.connect(self.validatePeriod)

    def setupFont(self):
        super().setupFont()
        font = fixedFont()
        self.becmg.setFont(font)
        self.tempo.setFont(font)

    def resolve(self, *args):
        """The trend period's own commit: normalize it, then read it once."""
        self.normalizePeriod()
        self.reload()

    def normalizePeriod(self):
        """Separate the hours when the trend spells both ends.

        A trend with FM and TL spells DDHH/DDHH; with AT it is a single time
        and needs no separator.
        """
        if not (self.fm.isChecked() and self.tl.isChecked()):
            return

        text = separatePeriod(self.period.text(), self.periodText)
        if text != self.period.text():
            self.period.setText(text)
        self.periodText = text

    def setupValidator(self):
        super().setupValidator()
        self.setupPeriodValidator()

    def setupPeriodValidator(self):
        if self.fm.isChecked() and self.tl.isChecked():
            period = QRegExpValidator(QRegExp(self.rules.trendFmTlPeriod))
        else:
            period = QRegExpValidator(QRegExp(self.rules.trendPeriod))

        self.period.setValidator(period)

    def setupPeriodPlaceholder(self):
        time = utcnow() + datetime.timedelta(hours=1)
        self.period.setPlaceholderText('{:02d}'.format(time.hour))

    def setNosig(self, checked):
        status = not checked

        self.prefixGroup.setEnabled(status)
        self.typeGroup.setEnabled(status)

        self.wind.setEnabled(status)
        self.gust.setEnabled(status)
        self.vis.setEnabled(status)
        self.weather.setEnabled(status)
        self.weatherWithIntensity.setEnabled(status)
        self.cloud1.setEnabled(status)
        self.cloud2.setEnabled(status)
        self.cloud3.setEnabled(status)
        self.cb.setEnabled(status)

        self.cavok.setEnabled(status)
        self.nsc.setEnabled(status)

        if self.nsc.isChecked():
            self.setNsc(True)

        if self.cavok.isChecked():
            self.setCavok(True)

        if any([self.fm.isChecked(), self.tl.isChecked(), self.at.isChecked()]):
            self.period.setEnabled(status)
        else:
            self.period.setEnabled(False)

    def setAt(self, checked):
        if checked:
            self.fm.setChecked(False)
            self.tl.setChecked(False)
            self.period.setEnabled(True)
            self.setupPeriodPlaceholder()
        else:
            self.period.setEnabled(False)
            self.period.setPlaceholderText('')

        self.period.clear()
        self.setupPeriodValidator()

    def setFmTl(self):
        checked = [self.fm.isChecked(), self.tl.isChecked()]
        if any(checked):
            self.at.setChecked(False)
            self.period.setEnabled(True)
            self.setupPeriodPlaceholder()
        else:
            self.period.setEnabled(False)
            self.period.setPlaceholderText('')

        self.period.clear()
        self.setupPeriodValidator()

    def load(self, tokens):
        """Seed the form from a parsed trend group: state first, then render.

        The tokens become state and populate() renders it; nothing is read
        back, so collect() stays the reader for what the operator types. A
        load is not a user edit, but it is a content change, so it announces
        itself the way reload() does.
        """
        self.state = TrendState.fromTokens(tokens, self.conf.units.tafSpeed,
                                           self.conf.weatherWithIntensityList)
        self.populate()
        self.contentChanged.emit()

    def formatPeriod(self):
        if (self.at.isChecked() or self.fm.isChecked() and not self.tl.isChecked()) and self.period.text() == '2400':
            self.period.setText('0000')

        if self.tl.isChecked() and not self.fm.isChecked() and self.period.text() == '0000':
            self.period.setText('2400')

    def validatePeriod(self):
        self.formatPeriod()
        self.collect()
        error = TrendFormValidator.checkPeriod(self.period.text(), now=utcnow())
        if error:
            self.period.clear()
            self.notified.emit(_translate(error))

    def updateAtStatus(self):
        if self.tempo.isChecked():
            self.at.setEnabled(False)
            self.at.setChecked(False)
        else:
            self.at.setEnabled(True)

    def isPeriodActive(self):
        return self.period.isEnabled()
