import datetime

from PyQt5.QtGui import QIcon, QRegExpValidator
from PyQt5.QtCore import Qt, QRegExp, QCoreApplication, QTimer, pyqtSignal
from PyQt5.QtWidgets import QWidget, QLabel, QLineEdit, QComboBox, QToolButton, QCheckBox, QTextEdit, QMessageBox, QHBoxLayout, QVBoxLayout

from tafor.core.parsers.base import Pattern
from tafor.core.taf import (GroupState, PrimaryState, SegmentState, TemperatureState, TrendState,
    TafFormValidator, TrendFormValidator, amendSequence, completeGroupPeriod, formatValidityEnd,
    groupSpan, isGroupStartAcceptable, normalizeTemperatureTime)
from tafor.core.utils.time import parseDayHour, parsePeriod, parseTime, utcnow
from tafor.core.utils.common import iconPath
from tafor.ui.fonts import fixedFont
from tafor.ui.qt import Ui_taf_group, Ui_taf_primary, Ui_trend


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


class SegmentMixin:

    def formatPeriodSeparator(self, line):
        """Append the '/' separator after the 4-digit day while typing."""
        text = line.text()
        if len(text) > len(self.periodText):
            if len(text) == 4:
                text += '/'
            line.setText(text)
        self.periodText = text

    @classmethod
    def upperText(cls, line):
        line.setText(line.text().upper())

    @classmethod
    def coloredText(cls, line):
        if line.hasAcceptableInput():
            line.setStyleSheet('color: black')
        else:
            line.setStyleSheet('color: grey')

    def setupFont(self):
        font = fixedFont()
        for line in self.findChildren(QLineEdit):
            line.setFont(font)

        for combox in self.findChildren(QComboBox):
            combox.setFont(font)

        for checkbox in self.findChildren(QCheckBox):
            checkbox.setFont(font)

        for text in self.findChildren(QTextEdit):
            text.setFont(font)


class BaseSegment(SegmentMixin, QWidget):

    contentChanged = pyqtSignal()
    # Which notification area this segment's errors belong to. Declared rather
    # than guessed from the class name; TrendSegment overrides it.
    editorName = 'taf'

    def __init__(self, name=None, editor=None, conf=None, context=None):
        super().__init__()
        self.rules = Pattern()
        self.editor = editor
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

    def onContentChanged(self):
        """The single entry point: a widget changed, so re-read the state."""
        self.collect()
        self.contentChanged.emit()

    def fields(self):
        """The line edits whose text feeds the state."""
        return [self.wind, self.gust, self.vis,
                self.weather.lineEdit(), self.weatherWithIntensity.lineEdit(),
                self.cloud1, self.cloud2, self.cloud3, self.cb]

    def toggles(self):
        """The check boxes and radio buttons whose value feeds the state."""
        return [self.cavok, self.nsc] if hasattr(self, 'cavok') else []

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
            line.textChanged.connect(self.onContentChanged)
            line.textEdited.connect(lambda _, current=line: self.upperText(current))
            line.textChanged.connect(lambda _, current=line: self.coloredText(current))

        for toggle in self.toggles():
            toggle.toggled.connect(self.onContentChanged)

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

    def applyState(self):
        """Write the state back into the widgets, the inverse of collect().

        `collect(); applyState(); collect()` leaves the state unchanged, which
        is the property that keeps the two directions honest. Each subclass
        writes the fields it owns and leaves the rest alone.

        Read the state out first. Every write below fires textChanged, which
        re-enters collect() and rewrites self.state from the widgets that have
        not been written yet, so rendering straight from self.state would make
        the result depend on the order of the writes.
        """
        wind = self.state.wind
        gust = self.state.gust
        visibility = self.state.visibility
        weather = self.state.weather
        weatherWithIntensity = self.state.weatherWithIntensity
        # The CB layer is an entry with a 'CB' suffix; the widget holds the
        # bare six characters, so the suffix comes off again on the way back.
        layers = [cloud for cloud in self.state.clouds if not cloud.endswith('CB')]
        cb = next((cloud for cloud in self.state.clouds if cloud.endswith('CB')), '')
        isCavok = self.state.isCavok
        isNsc = self.state.isNsc

        self.wind.setText(wind)
        self.gust.setText(gust)
        self.vis.setText(visibility)
        self.weather.setCurrentText(weather)
        self.weatherWithIntensity.setCurrentText(weatherWithIntensity)
        self.cb.setText(cb[:-2])
        for index, line in enumerate((self.cloud1, self.cloud2, self.cloud3)):
            line.setText(layers[index] if index < len(layers) else '')

        if hasattr(self, 'cavok'):
            self.cavok.setChecked(isCavok)
            self.nsc.setChecked(isNsc)

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
        if self.wind.hasAcceptableInput() and int(self.wind.text()[-2:]) == 0:
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
            self.context.flash.editor(self.editorName, _translate(error))

    def validateGust(self):
        error = TafFormValidator.checkGust(self.state)
        if error:
            self.gust.clear()
            self.context.flash.editor(self.editorName, _translate(error))

    def validateCloud(self, line):
        error = TafFormValidator.checkCloud(self.state, line.text())
        if error:
            self.context.flash.editor(self.editorName, _translate(error))
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
        """Empty the state, then re-render it."""
        self.state.clear()
        self.applyState()


class TemperatureGroup(SegmentMixin, QWidget):

    temperatureChanged = pyqtSignal()

    def __init__(self, mode='max', canSwitch=False, primary=None, context=None):
        super().__init__(primary)
        self.state = TemperatureState(mode)
        self.canSwitch = canSwitch
        self.primary = primary
        self.context = context

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
            line.textChanged.connect(self.collect)
            line.textChanged.connect(self.temperatureChanged.emit)
            line.textEdited.connect(lambda _, current=line: self.upperText(current))
            line.textChanged.connect(lambda _, current=line: self.coloredText(current))

        self.tempTime.editingFinished.connect(self.validateTemperatureTime)
        self.temp.editingFinished.connect(self.validateTemperature)

    def collect(self):
        self.state.value = self.temp.text() if self.temp.hasAcceptableInput() else ""
        self.state.time = self.tempTime.text() if self.tempTime.hasAcceptableInput() else ""

    def setupValidator(self):
        temperature = QRegExpValidator(QRegExp(self.primary.rules.temperature, Qt.CaseInsensitive))
        self.temp.setValidator(temperature)

        dayHour = QRegExpValidator(QRegExp(self.primary.rules.dayHour))
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
        if not self.primary.period.text() or not self.tempTime.hasAcceptableInput():
            return

        primary = self.primary.state
        error = TafFormValidator.checkTemperatureTime(
            self.state,
            primary.temperatures,
            primary.durations,
        )
        if error:
            self.state.time = ""
            self.tempTime.clear()
            self.context.flash.editor('taf', _translate(error))
            return

        # Time normalization can stay in UI or move to state, keep here for now as it affects UI text
        time = parseDayHour(self.state.time[:2], self.state.time[2:], self.primary.state.durations[0], delta='month')
        normalized = normalizeTemperatureTime(time, self.primary.state.durations)
        if normalized:
            self.tempTime.setText(normalized)

    def validateTemperature(self):
        if not self.temp.hasAcceptableInput():
            return

        primary = self.primary.state
        error = TafFormValidator.checkTemperature(
            self.state,
            primary.temperatures,
        )
        if error:
            self.state.value = ""
            self.temp.clear()
            self.context.flash.editor('taf', _translate(error))
            return

    def switchMode(self):
        self.state.mode = 'min' if self.state.mode == 'max' else 'max'
        self.setLabel()
        self.validateTemperature()
        self.validateTemperatureTime()

    def composeMessage(self):
        return self.state.composeMessage()

    def widgets(self):
        if self.canSwitch:
            return [self.switchButton, self.temp, self.tempTime]
        
        return [self.temp, self.tempTime]

    def applyState(self):
        """The inverse of collect().

        The mode is not rendered: switchMode() owns it, and
        TemperatureState.clear() deliberately leaves it alone. The values are
        read out first, for the reason given in BaseSegment.applyState().
        """
        value = self.state.value
        time = self.state.time
        self.temp.setText(value)
        self.tempTime.setText(time)

    def clear(self):
        """Empty the state, then re-render it."""
        self.state.clear()
        self.applyState()


class TafPrimarySegment(BaseSegment, Ui_taf_primary.Ui_Editor):

    def __init__(self, name='PRIMARY', editor=None, conf=None, context=None, repository=None, draft=None):
        super().__init__(name, editor, conf, context)
        self.setupUi(self)

        self.repository = repository
        self.draft = draft

        self.setupValidator()
        self.period.setEnabled(False)
        self.sequence.setEnabled(False)

        self.groupCheckboxs = [
            self.fmCheckbox,
            self.becmg1Checkbox, self.becmg2Checkbox, self.becmg3Checkbox,
            self.tempo1Checkbox, self.tempo2Checkbox, self.tempo3Checkbox,
        ]

        self.tmax = TemperatureGroup(mode='max', primary=self, context=self.context)
        self.tmin = TemperatureGroup(mode='min', primary=self, context=self.context)
        self.temperatureLayout.addWidget(self.tmax)
        self.temperatureLayout.addWidget(self.tmin)
        self.temperatures = [self.tmax, self.tmin]

        if self.context.taf.spec.duration == datetime.timedelta(hours=30):
            self.temp = TemperatureGroup(canSwitch=True, primary=self, context=self.context)
            self.temperatureLayout.addWidget(self.temp)
            self.temperatures.append(self.temp)
            self.becmg3Checkbox.setStyleSheet('QCheckBox {margin-top: 4px;}')
            self.tempo3Checkbox.setStyleSheet('QCheckBox {margin-top: 4px;}')

        # Link temperature states to primary state
        self.state.temperatures = [t.state for t in self.temperatures]

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

    def applyState(self):
        """The primary segment deliberately leaves its header alone.

        `date` belongs to the clock and `period` to updateModifier(); writing
        `period` here would put a period on screen that updateModifier() did not
        choose, and clearing the form is its decision to make. The modifier radios
        are left alone for the same reason: PrimaryState.clear() drops the modifier
        back to None (a normal report), and rendering that would reset the radios in
        the middle of updateModifier()'s own re-derivation of the period.
        """
        sequence = self.state.sequence
        super().applyState()
        self.sequence.setText(sequence)
        for t in self.temperatures:
            t.applyState()

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

        self.normal.clicked.connect(self.updateModifier)
        self.cor.clicked.connect(self.updateModifier)
        self.amd.clicked.connect(self.updateModifier)
        self.cnl.clicked.connect(self.updateModifier)
        self.prevButton.clicked.connect(lambda: self.setCurrentPeriod('prev'))
        self.resetButton.clicked.connect(lambda: self.setCurrentPeriod('reset'))

        for t in self.temperatures:
            t.temperatureChanged.connect(lambda: self.contentChanged.emit())
            t.temperatureChanged.connect(self.collect)

        # Parented to the widget: an unparented timer is not in the widget tree,
        # so it kept running after the editor was destroyed.
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.setDate)
        self.timer.start(1 * 1000)

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

    def updateModifier(self):
        """Empty the form when the period changes, then refill the header.

        The period is the only trigger: a modifier does not move the validity
        window, so switching the marker keeps what has been typed, and the header
        the marker owns -- the sequence notation and its validator -- is rebuilt
        below on every run, clear or not. Nor is the trigger "this handler ran":
        a click on the radio that is already on must keep what has been typed.
        """
        self.taf = self.draft.taf()
        modifier = self.modifier
        period = self.impliedPeriod(self.taf, modifier)

        if period != self.period.text():
            self.editor.clear()

        # A clear() drops the state back to defaults and no collect runs on the
        # prev/reset path, so re-assert the modifier the radios are on.
        self.state.modifier = modifier
        self.applyPeriod(period)

        if modifier is None:
            self.sequence.clear()
            self.sequence.setEnabled(False)
        else:
            aaa = QRegExpValidator(QRegExp(self.rules.aaa, Qt.CaseInsensitive))
            ccc = QRegExpValidator(QRegExp(self.rules.ccc, Qt.CaseInsensitive))

            if modifier == 'COR':
                order = self.amendNumber(period, 'COR')
                self.sequence.setValidator(ccc)
            else:
                order = self.amendNumber(period, 'AMD')
                self.sequence.setValidator(aaa)

            self.sequence.setEnabled(True)
            self.sequence.setText(order)

        if modifier == 'CNL':
            for c in self.groupCheckboxs:
                c.setEnabled(False)
                c.setChecked(False)
        else:
            for c in self.groupCheckboxs:
                c.setEnabled(True)

    def impliedPeriod(self, taf, modifier):
        """The validity period the modifier implies, computed but not written.

        Computing it here rather than inside a setter is what lets
        updateModifier() compare the new period with the one on screen before
        anything moves.
        """
        period = taf.period()

        if modifier is None:
            # The normal report for this period is already out: leave the field
            # empty rather than offering the same report twice.
            return '' if self.repository.hasRecent(period) else period

        return period

    def applyPeriod(self, period):
        """Write the validity period, and keep the durations in step with it."""
        self.state.period = period
        self.state.durations = self.taf.durations() if period else None
        self.period.setText(period)

    def setCurrentPeriod(self, action):
        if action == 'reset':
            self.draft.reset()
            self.updateModifier()
            self.resetButton.setEnabled(self.draft.canReset())
            self.prevButton.setEnabled(self.draft.canPrev())

        if action == 'prev':
            title = QCoreApplication.translate('Editor', 'Tips')
            text = QCoreApplication.translate('Editor', 'Do you want to change the message valid period to previous?')
            ret = QMessageBox.question(self, title, text)
            if ret == QMessageBox.Yes:
                self.draft.prev()
                self.updateModifier()
                self.resetButton.setEnabled(self.draft.canReset())
                self.prevButton.setEnabled(self.draft.canPrev())

    def amendNumber(self, period, modifier):
        """The sequence to offer: how many are already out is the repository's
        count, the notation built from it is core/taf's.
        """
        count = self.repository.amendCount(period, modifier)
        return amendSequence(count, modifier)

    def setDate(self):
        time = utcnow()
        self.date.setText(time.strftime('%d%H%M'))

    def showEvent(self, event):
        self.setDate()

    def clearType(self):
        # A fresh message: the radios go back to NORMAL, and the toggled cascade
        # collects them into the state on the way.
        self.normal.setChecked(True)
        self.sequence.clear()
        self.resetButton.setEnabled(False)
        self.prevButton.setEnabled(True)
        self.draft.reset()

    def isCancelMode(self):
        return self.modifier == 'CNL'

    def clear(self):
        super().clear()


class TafGroupSegment(BaseSegment, Ui_taf_group.Ui_Editor):

    def __init__(self, name='TEMPO', editor=None, conf=None, context=None):
        super().__init__(name, editor, conf, context)
        self.setupUi(self)
        self.name.setText(name)
        self.setupFont()
        self.setupValidator()
        self.bindSignal()
        self.periodText = ''

    def fields(self):
        return super().fields() + [self.period]

    def collect(self):
        super().collect()
        self.state.period = self.period.text()

    def applyState(self):
        period = self.state.period
        super().applyState()
        self.period.setText(period)

    def bindSignal(self):
        super().bindSignal()
        self.period.textEdited.connect(self.fillPeriod)
        self.period.textChanged.connect(self.updateDurations)
        self.period.editingFinished.connect(self.validatePeriod)
        self.period.editingFinished.connect(self.validateGroupsPeriod)

    def setupFont(self):
        super().setupFont()
        self.name.setFont(fixedFont())

    def setupValidator(self):
        super().setupValidator()
        period = QRegExpValidator(QRegExp(self.rules.period))
        self.period.setValidator(period)

    def setupPeriodPlaceholder(self):
        if self.editor.primary.state.durations is None:
            self.period.setPlaceholderText('')
            return

        time = self.editor.primary.state.durations[0]
        self.period.setPlaceholderText('{:02d}'.format(time.day))

    def fillPeriod(self):
        if self.conf.autoCompletionGroupTime:
            self.autoCompletePeriod()
        else:
            self.formatPeriodSeparator(self.period)

    def autoCompletePeriod(self):
        if self.editor.primary.state.durations is None or not self.editor.primary.period.text():
            return

        text = self.period.text()
        if len(text) > len(self.periodText):
            if len(text) == 4:
                if not isGroupStartAcceptable(text, self.editor.primary.state.durations):
                    return

                if self.indicator in ('TEMPO', 'BECMG'):
                    completed = completeGroupPeriod(
                        text,
                        self.editor.primary.state.durations,
                        self.indicator,
                        self.context.taf.spec,
                    )
                    if completed is None:
                        return

                    text = completed

            self.period.setText(text)

        self.periodText = text

    def updateDurations(self):
        if self.period.hasAcceptableInput() and self.editor.primary.period.text():
            period = self.period.text()
            basetime = self.editor.primary.state.durations[0]
            start, end = parsePeriod(period, basetime)
            self.state.durations = (start, end)

            if end.hour == 0 and not period.endswith('24'):
                text = '{:02d}{:02d}/{}'.format(start.day, start.hour, formatValidityEnd(end))
                self.period.setText(text)
                end -= datetime.timedelta(minutes=1)
        else:
            self.state.durations = None

    def validate(self):
        super().validate()
        self.validatePeriod()
        self.validateGroupsPeriod()

    def validatePeriod(self):
        span = groupSpan(self.indicator, self.context.taf.spec)
        error = TafFormValidator.checkGroupPeriod(self.state, self.editor.primary.state, span)
        if error:
            self.period.clear()
            self.context.flash.editor('taf', _translate(error, span=span))

    def validateGroupsPeriod(self):
        siblings = [g.state for g in self.editor.activeGroups()
                    if g is not self and g.indicator == self.indicator]
        error = TafFormValidator.checkGroupOverlap(self.state, siblings)
        if error:
            self.period.clear()
            self.context.flash.editor('taf', _translate(error))

    def showEvent(self, event):
        self.setupPeriodPlaceholder()

    def clear(self):
        super().clear()
        # periodText is the auto-completion bookkeeping, not state.
        self.period.setPlaceholderText('')
        self.periodText = ''


class TafFmSegment(TafGroupSegment):

    def __init__(self, name='FM', editor=None, conf=None, context=None):
        super().__init__(name, editor, conf, context)

    def bindSignal(self):
        super().bindSignal()
        self.period.textEdited.disconnect(self.fillPeriod)

    def setupValidator(self):
        super().setupValidator()
        period = QRegExpValidator(QRegExp(self.rules.fmPeriod))
        self.period.setValidator(period)

    def updateDurations(self):
        if self.period.hasAcceptableInput() and self.editor.primary.period.text():
            period = self.period.text()
            basetime = self.editor.primary.state.durations[0]
            time = parseTime(period, basetime)
            self.state.durations = (time, time)
        else:
            self.state.durations = None

    def validatePeriod(self):
        # Using states for validation where possible
        error = TafFormValidator.checkFmPeriod(self.state, self.editor.primary.state)
        if error:
            self.period.clear()
            self.context.flash.editor('taf', _translate(error))

    def validateGroupsPeriod(self):
        siblings = [g.state for g in self.editor.activeGroups() if g.indicator == 'BECMG']
        error = TafFormValidator.checkFmOverlap(self.state, siblings)
        if error:
            self.period.clear()
            self.context.flash.editor('taf', _translate(error))


class TafBecmgSegment(TafGroupSegment):

    def __init__(self, name='BECMG', editor=None, conf=None, context=None):
        super().__init__(name, editor, conf, context)


class TafTempoSegment(TafGroupSegment):

    def __init__(self, name='TEMPO', editor=None, conf=None, context=None):
        super().__init__(name, editor, conf, context)
        self.cavok.hide()
        self.nsc.hide()


class TrendSegment(BaseSegment, Ui_trend.Ui_Editor):

    editorName = 'trend'

    def __init__(self, name='TREND', editor=None, conf=None, context=None):
        super().__init__(name, editor, conf, context)
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

    def applyState(self):
        # Read first: these writes fire toggled/textChanged, which re-enter
        # collect() and rewrite self.state from the widgets that have not been
        # written yet. See BaseSegment.applyState().
        isNosig = self.state.isNosig
        isBecmg = self.state.indicator == 'BECMG'
        atChecked = self.state.atChecked
        fmChecked = self.state.fmChecked
        tlChecked = self.state.tlChecked
        period = self.state.period

        super().applyState()
        self.nosig.setChecked(isNosig)
        self.becmg.setChecked(isBecmg)
        self.tempo.setChecked(not isBecmg)
        self.at.setChecked(atChecked)
        self.fm.setChecked(fmChecked)
        self.tl.setChecked(tlChecked)
        # Last: unchecking at/fm/tl clears and disables the period through
        # setAt()/setFmTl(), and setNosig() re-derives what is enabled.
        self.period.setText(period)

    def bindSignal(self):
        super().bindSignal()
        self.nosig.toggled.connect(self.setNosig)
        self.at.toggled.connect(self.setAt)
        self.fm.toggled.connect(self.setFmTl)
        self.tl.toggled.connect(self.setFmTl)

        self.becmg.clicked.connect(self.updateAtStatus)
        self.tempo.clicked.connect(self.updateAtStatus)

        self.period.textEdited.connect(self.autoFormatPeriod)
        self.period.editingFinished.connect(self.validatePeriod)

    def setupFont(self):
        super().setupFont()
        font = fixedFont()
        self.becmg.setFont(font)
        self.tempo.setFont(font)

    def autoFormatPeriod(self):
        if self.fm.isChecked() and self.tl.isChecked():   
            self.formatPeriodSeparator(self.period)

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

    def populateFromTokens(self, tokens):
        if 'sign' in tokens:
            sign = tokens['sign']['text']
            if sign == 'BECMG':
                self.becmg.setChecked(True)
            else:
                self.tempo.setChecked(True)

        if 'fmtl' in tokens:
            periods = tokens['fmtl']['text'].split()
            if len(periods) == 2:
                self.fm.setChecked(True)
                self.tl.setChecked(True)
                period = periods[0][2:] + '/' + periods[1][2:]
                self.period.setText(period)
            else:
                period = periods[0]
                if period.startswith('TL'):
                    self.tl.setChecked(True)
                if period.startswith('FM'):
                    self.fm.setChecked(True)
                if period.startswith('AT'):
                    self.at.setChecked(True)

                self.period.setText(period[2:])

        if 'wind' in tokens:
            wind = tokens['wind']['text'].replace('MPS', '')
            if 'G' in wind:
                wind, gust = wind.split('G')
                self.gust.setText(gust)

            self.wind.setText(wind)

        if 'vis' in tokens:
            vis = tokens['vis']['text']
            self.vis.setText(vis)

        if 'weather' in tokens:
            weathers = tokens['weather']['text'].split()
            for weather in weathers:
                self.weatherWithIntensity.setCurrentIndex(self.weatherWithIntensity.findText(weather))
                self.weather.setCurrentIndex(self.weather.findText(weather))

        if 'cloud' in tokens:
            clouds = tokens['cloud']['text']
            if 'NSC' in clouds:
                self.nsc.setChecked(True)
            else:
                clouds = clouds.split(' ')
                lines = [self.cloud3, self.cloud2, self.cloud1]
                for cloud in clouds:
                    if 'TCU' in cloud or 'CB' in cloud:
                        self.cb.setText(cloud[:6])
                    elif lines:
                        line = lines.pop()
                        line.setText(cloud)

        if 'cavok' in tokens:
            self.cavok.setChecked(True)

    def formatPeriod(self):
        if (self.at.isChecked() or self.fm.isChecked() and not self.tl.isChecked()) and self.period.text() == '2400':
            self.period.setText('0000')

        if self.tl.isChecked() and not self.fm.isChecked() and self.period.text() == '0000':
            self.period.setText('2400')

    def validatePeriod(self):
        self.formatPeriod()
        error = TrendFormValidator.checkPeriod(self.period.text(), now=utcnow())
        if error:
            self.period.clear()
            self.context.flash.editor('trend', _translate(error))

    def updateAtStatus(self):
        if self.tempo.isChecked():
            self.at.setEnabled(False)
            self.at.setChecked(False)
        else:
            self.at.setEnabled(True)

    def isPeriodActive(self):
        return self.period.isEnabled()
