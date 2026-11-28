import datetime

from PyQt5.QtGui import QIcon, QRegExpValidator
from PyQt5.QtCore import Qt, QRegExp, QCoreApplication, QTimer, pyqtSignal
from PyQt5.QtWidgets import QComboBox, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QToolButton, QVBoxLayout, QWidget

from tafor.core.parsers.base import Pattern
from tafor.core.taf import (
    GroupState, PrimaryState, SegmentState, TemperatureState, TrendState,
    TafFormValidator, TrendFormValidator, formatTrendPeriod, groupPeriodRules,
    normalizeTemperatureTime, segmentRules, trendRules,
)
from tafor.core.utils.time import parseDayHour, parsePeriod, parseTime, utcnow
from tafor.core.utils.common import iconPath
from tafor.ui.fonts import fixedFont
from tafor.ui.forms.base import TextFieldMixin, isAcceptable, setChecked, setComboText, setLineText
from tafor.ui.forms.pipeline import FormPipeline
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


class BaseSegment(TextFieldMixin, QWidget):

    contentChanged = pyqtSignal()
    notified = pyqtSignal(str)
    rules = staticmethod(segmentRules)

    def __init__(self, name=None, conf=None, context=None):
        super().__init__()
        self.patterns = Pattern()
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

        self.pipeline = FormPipeline(
            initial=self.fromState(),
            apply=self.apply,
            rules=self.rules,
            validator=self.check,
            render=lambda: self.populate(self.pipeline.raw),
            notify=self.notified.emit,
            changed=self.contentChanged.emit,
        )

    def fromState(self):
        layers = [cloud for cloud in self.state.clouds if not cloud.endswith('CB')]
        cb = next((cloud for cloud in self.state.clouds if cloud.endswith('CB')), '')
        return {
            'wind': self.state.wind,
            'gust': self.state.gust,
            'vis': self.state.visibility,
            'weather': self.state.weather,
            'weatherWithIntensity': self.state.weatherWithIntensity,
            'cloud1': layers[0] if len(layers) > 0 else '',
            'cloud2': layers[1] if len(layers) > 1 else '',
            'cloud3': layers[2] if len(layers) > 2 else '',
            'cb': cb[:-2] if cb else '',
            'isCavok': self.state.isCavok,
            'isNsc': self.state.isNsc,
        }

    def fromWidgets(self):
        raw = {
            'wind': self.wind.text(),
            'gust': self.gust.text(),
            'vis': self.vis.text(),
            'weather': self.weather.currentText(),
            'weatherWithIntensity': self.weatherWithIntensity.currentText(),
            'cloud1': self.cloud1.text(),
            'cloud2': self.cloud2.text(),
            'cloud3': self.cloud3.text(),
            'cb': self.cb.text(),
        }
        if hasattr(self, 'cavok'):
            raw['isCavok'] = self.cavok.isChecked()
            raw['isNsc'] = self.nsc.isChecked()
        else:
            raw['isCavok'] = False
            raw['isNsc'] = False
        return raw

    def apply(self, raw):
        self.state.wind = raw.get('wind', '') if isAcceptable(self.wind, raw.get('wind', '')) else ''
        self.state.gust = raw.get('gust', '') if isAcceptable(self.gust, raw.get('gust', '')) else ''
        self.state.visibility = raw.get('vis', '') if isAcceptable(self.vis, raw.get('vis', '')) else ''
        self.state.weather = (
            raw.get('weather', '')
            if isAcceptable(self.weather, raw.get('weather', ''))
            else ''
        )
        self.state.weatherWithIntensity = (
            raw.get('weatherWithIntensity', '')
            if isAcceptable(self.weatherWithIntensity, raw.get('weatherWithIntensity', ''))
            else ''
        )

        clouds = []
        for field, line in (('cloud1', self.cloud1), ('cloud2', self.cloud2), ('cloud3', self.cloud3)):
            value = raw.get(field, '')
            if isAcceptable(line, value):
                clouds.append(value)

        cb = raw.get('cb', '')
        if isAcceptable(self.cb, cb):
            clouds.append(cb + 'CB')
        self.state.clouds = clouds

        if hasattr(self, 'cavok'):
            self.state.isCavok = bool(raw.get('isCavok'))
            self.state.isNsc = bool(raw.get('isNsc'))

    def fields(self):
        return [
            (self.wind, 'wind'),
            (self.gust, 'gust'),
            (self.vis, 'vis'),
            (self.weather, 'weather'),
            (self.weatherWithIntensity, 'weatherWithIntensity'),
            (self.cloud1, 'cloud1'),
            (self.cloud2, 'cloud2'),
            (self.cloud3, 'cloud3'),
            (self.cb, 'cb'),
        ]

    def toggles(self):
        if not hasattr(self, 'cavok'):
            return []
        return [
            (self.cavok, lambda checked: {'isCavok': checked}),
            (self.nsc, lambda checked: {'isNsc': checked}),
        ]

    def editText(self, field, line, text):
        upper = text.upper()
        if upper != text:
            setLineText(line, upper)
        self.pipeline.edit({field: upper})

    def finishText(self, field, line):
        if not line.isEnabled():
            return
        self.editText(field, line, line.text())
        self.pipeline.validate(field)

    def bindSignal(self):
        for widget, field in self.fields():
            if isinstance(widget, QComboBox):
                line = widget.lineEdit()
                line.textEdited.connect(lambda text, f=field, w=line: self.editText(f, w, text))
                widget.activated[str].connect(lambda text, f=field, w=line: self.editText(f, w, text))
            else:
                widget.textEdited.connect(lambda text, f=field, w=widget: self.editText(f, w, text))

        for toggle, makePatch in self.toggles():
            toggle.clicked.connect(lambda checked, fn=makePatch: self.pipeline.edit(fn(checked)))

        self.gust.editingFinished.connect(lambda: self.finishText('gust', self.gust))
        self.weather.lineEdit().editingFinished.connect(
            lambda: self.finishText('weather', self.weather.lineEdit())
        )
        self.weatherWithIntensity.lineEdit().editingFinished.connect(
            lambda: self.finishText('weatherWithIntensity', self.weatherWithIntensity.lineEdit())
        )
        for field, line in (
            ('cloud1', self.cloud1),
            ('cloud2', self.cloud2),
            ('cloud3', self.cloud3),
            ('cb', self.cb),
        ):
            line.editingFinished.connect(lambda f=field, w=line: self.finishText(f, w))

    def collect(self):
        """Read the widgets into the state and re-run segment rules."""
        self.pipeline.sync(self.fromWidgets(), source='collect', derive=True, changed=False)

    def populate(self, raw=None, active=True):
        """Render ``raw`` (or current state when omitted) back into the widgets."""
        if raw is None:
            self.pipeline.sync(self.fromState())
            return

        hasCavok = hasattr(self, 'cavok')
        cavok = bool(raw.get('isCavok')) if hasCavok else False
        nsc = bool(raw.get('isNsc')) if hasCavok else False
        calm = raw.get('wind', '') == '00000'
        nsw = raw.get('weather', '').upper() == 'NSW'
        vv = raw.get('cloud1', '').upper().startswith('V')
        cloudsActive = active and not cavok and not nsc

        setLineText(self.wind, raw.get('wind', ''))
        setLineText(self.gust, raw.get('gust', ''))
        setLineText(self.vis, raw.get('vis', ''))
        setComboText(self.weather, raw.get('weather', ''))
        setComboText(self.weatherWithIntensity, raw.get('weatherWithIntensity', ''))
        setLineText(self.cloud1, raw.get('cloud1', ''))
        setLineText(self.cloud2, raw.get('cloud2', ''))
        setLineText(self.cloud3, raw.get('cloud3', ''))
        setLineText(self.cb, raw.get('cb', ''))

        if hasCavok:
            setChecked(self.cavok, cavok)
            setChecked(self.nsc, nsc)
            self.cavok.setEnabled(active)
            self.nsc.setEnabled(active)

        self.wind.setEnabled(active)
        self.gust.setEnabled(active and not calm)
        self.vis.setEnabled(active and not cavok)
        self.weather.setEnabled(active and not cavok)
        self.weatherWithIntensity.setEnabled(active and not cavok and not nsw)
        self.cloud1.setEnabled(cloudsActive)
        self.cloud2.setEnabled(cloudsActive and not vv)
        self.cloud3.setEnabled(cloudsActive and not vv)
        self.cb.setEnabled(cloudsActive and not vv)

        label = (
            QCoreApplication.translate('Editor', 'Vertical Visibility')
            if vv
            else QCoreApplication.translate('Editor', 'Cloud')
        )
        if self.cloud1Label.text() != label:
            self.cloud1Label.setText(label)

        for widget, _ in BaseSegment.fields(self):
            self.coloredText(widget.lineEdit() if isinstance(widget, QComboBox) else widget)

    def setupPeriodPlaceholder(self):
        raise NotImplementedError

    def setupValidator(self):
        wind = QRegExpValidator(QRegExp(self.patterns.wind, Qt.CaseInsensitive))
        self.wind.setValidator(wind)

        gust = QRegExpValidator(QRegExp(self.patterns.gust, Qt.CaseInsensitive))
        self.gust.setValidator(gust)

        vis = QRegExpValidator(QRegExp(self.patterns.vis))
        self.vis.setValidator(vis)

        cloud = QRegExpValidator(QRegExp(self.patterns.cloud, Qt.CaseInsensitive))
        vvCloud = QRegExpValidator(QRegExp(r'({})|({})'.format(self.patterns.cloud, self.patterns.vv), Qt.CaseInsensitive))
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

    def check(self, scope):
        if scope == 'gust':
            if not self.gust.isEnabled() or not self.state.gust:
                return ({}, [])
            error = TafFormValidator.checkGust(self.state)
            if error:
                return ({'gust': ''}, [_translate(error)])
            return ({}, [])

        if scope in ('weather', 'weatherWithIntensity'):
            error = TafFormValidator.checkWeather(self.state)
            if error:
                return ({scope: ''}, [_translate(error)])
            return ({}, [])

        if scope in ('cloud1', 'cloud2', 'cloud3', 'cb'):
            value = self.pipeline.value(scope)
            if not value:
                return ({}, [])
            error = TafFormValidator.checkCloud(self.state, value)
            if error:
                return ({scope: ''}, [_translate(error)])
            return ({}, [])

        return ({}, [])

    def validate(self):
        for scope in ('gust', 'weather', 'cloud3', 'cloud2', 'cloud1', 'cb'):
            self.pipeline.validate(scope)

    def message(self):
        return self.state.composeMessage()

    def hasAcceptableInput(self):
        return self.state.isAcceptable()

    def clear(self):
        """Empty the state, then render that emptiness."""
        self.state.clear()
        self.pipeline.sync(self.fromState(), source='clear', derive=False, changed=True)


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
        self.patterns = Pattern()
        self.primary = primary

        primary.addTemperature(self.state)

        self.pipeline = FormPipeline(
            initial=self.fromState(),
            apply=self.apply,
            validator=self.check,
            render=lambda: self.populate(self.pipeline.raw),
            notify=self.notified.emit,
            changed=self.contentChanged.emit,
        )

        self.setupUi()
        self.setupValidator()
        self.bindSignal()
        self.populate(self.pipeline.raw)

    def fromState(self):
        return {
            'mode': self.state.mode,
            'value': self.state.value,
            'time': self.state.time,
        }

    def fromWidgets(self):
        return {
            'mode': self.state.mode,
            'value': self.temp.text(),
            'time': self.tempTime.text(),
        }

    def apply(self, raw):
        self.state.mode = raw.get('mode', self.state.mode)
        value = raw.get('value', '')
        self.state.value = value if isAcceptable(self.temp, value) else ''
        time = raw.get('time', '')
        self.state.time = time if isAcceptable(self.tempTime, time) else ''

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

    def editText(self, field, line, text):
        upper = text.upper()
        if upper != text:
            setLineText(line, upper)
        self.pipeline.edit({field: upper})

    def finishText(self, field, line):
        self.editText(field, line, line.text())
        self.pipeline.validate(field)

    def bindSignal(self):
        if self.canSwitch:
            self.switchButton.clicked.connect(self.switchMode)

        for line, field in ((self.temp, 'value'), (self.tempTime, 'time')):
            line.textEdited.connect(lambda text, f=field, w=line: self.editText(f, w, text))
            line.editingFinished.connect(lambda f=field, w=line: self.finishText(f, w))

    def collect(self):
        self.pipeline.sync(self.fromWidgets(), source='collect', derive=True, changed=False)

    def setupValidator(self):
        temperature = QRegExpValidator(QRegExp(self.patterns.temperature, Qt.CaseInsensitive))
        self.temp.setValidator(temperature)

        dayHour = QRegExpValidator(QRegExp(self.patterns.dayHour))
        self.tempTime.setValidator(dayHour)

    def setLabel(self, mode=None):
        if mode is None:
            mode = self.state.mode
        if mode == 'max':
            text = QCoreApplication.translate('Editor', 'Max Temperature')
            icon = 'warm'
        else:
            text = QCoreApplication.translate('Editor', 'Min Temperature')
            icon = 'cold'

        if self.label.text() != text:
            self.label.setText(text)
            self.switchButton.setIcon(QIcon(iconPath('{}.png'.format(icon))))

    def check(self, scope):
        if scope == 'time':
            if not self.primary.period or not self.state.time:
                return ({}, [])

            error = TafFormValidator.checkTemperatureTime(
                self.state,
                self.primary.temperatures,
                self.primary.durations,
            )
            if error:
                return ({'time': ''}, [_translate(error)])

            time = parseDayHour(
                self.state.time[:2],
                self.state.time[2:],
                self.primary.durations[0],
                delta='month',
            )
            normalized = normalizeTemperatureTime(time, self.primary.durations)
            if normalized and normalized != self.pipeline.value('time'):
                return ({'time': normalized}, [])
            return ({}, [])

        if scope == 'value':
            if not self.state.value:
                return ({}, [])

            error = TafFormValidator.checkTemperature(
                self.state,
                self.primary.temperatures,
            )
            if error:
                return ({'value': ''}, [_translate(error)])
            return ({}, [])

        return ({}, [])

    def validate(self):
        self.pipeline.validate('time')
        self.pipeline.validate('value')

    def switchMode(self):
        mode = 'min' if self.state.mode == 'max' else 'max'
        self.pipeline.edit({'mode': mode})
        self.pipeline.validate('value')
        self.pipeline.validate('time')

    def widgets(self):
        if self.canSwitch:
            return [self.switchButton, self.temp, self.tempTime]

        return [self.temp, self.tempTime]

    def populate(self, raw=None):
        """Render ``raw`` (or current state when omitted) back into the widgets."""
        if raw is None:
            self.pipeline.sync(self.fromState())
            return

        self.setLabel(raw.get('mode', self.state.mode))
        setLineText(self.temp, raw.get('value', ''))
        setLineText(self.tempTime, raw.get('time', ''))
        self.coloredText(self.temp)
        self.coloredText(self.tempTime)

    def clear(self):
        """Empty the state, then populate it again."""
        self.state.clear()
        self.pipeline.sync(self.fromState(), source='clear', derive=False, changed=True)


class TafPrimarySegment(BaseSegment, Ui_taf_primary.Ui_Editor):

    modifierChanged = pyqtSignal(object)
    periodShiftRequested = pyqtSignal(str)

    def __init__(self, name='PRIMARY', conf=None, context=None):
        super().__init__(name, conf, context)
        self.setupUi(self)

        self.setupValidator()
        self.period.setEnabled(False)

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
        self.populate(self.pipeline.raw)

    def fromState(self):
        raw = super().fromState()
        date = self.state.date or (self.date.text() if hasattr(self, 'date') else '')
        raw.update({
            'date': date,
            'period': self.state.period,
            'sequence': self.state.sequence,
            'modifier': self.state.modifier,
        })
        return raw

    def fromWidgets(self):
        raw = super().fromWidgets()
        raw.update({
            'date': self.date.text(),
            'period': self.period.text(),
            'sequence': self.sequence.text(),
            'modifier': self.modifier,
        })
        return raw

    def apply(self, raw):
        super().apply(raw)
        date = raw.get('date', '')
        self.state.date = date if isAcceptable(self.date, date) else ''
        self.state.period = raw.get('period', '')
        modifier = raw.get('modifier')
        self.state.modifier = modifier
        sequence = raw.get('sequence', '')
        self.state.sequence = (
            sequence if (modifier is not None and isAcceptable(self.sequence, sequence)) else ''
        )

    def collect(self):
        super().collect()
        for t in self.temperatures:
            t.collect()

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

    def populate(self, raw=None):
        """Draw the whole header from the draft or render ``raw`` into widgets."""
        if raw is None:
            if not self.state.date and self.date.text():
                text = self.date.text()
                self.state.date = text if isAcceptable(self.date, text) else ''
            self.pipeline.sync(self.fromState())
            for t in self.temperatures:
                t.populate()
            return

        super().populate(raw)
        modifier = raw.get('modifier')
        self.setSequenceValidator(modifier)
        self.setGroupCheckboxes(modifier != 'CNL')
        setLineText(self.date, raw.get('date', ''))
        setLineText(self.period, raw.get('period', ''))
        setLineText(self.sequence, raw.get('sequence', ''))
        radios = {'AMD': self.amd, 'COR': self.cor, 'CNL': self.cnl}
        setChecked(radios.get(modifier, self.normal), True)
        self.coloredText(self.date)
        self.coloredText(self.sequence)

    def setOrder(self):
        orders = [self.nsc]
        for t in self.temperatures:
            orders += t.widgets()

        for p, n in zip(orders, orders[1:]):
            self.setTabOrder(p, n)

    def setupValidator(self):
        super().setupValidator()

        date = QRegExpValidator(QRegExp(self.patterns.date))
        self.date.setValidator(date)

    def fields(self):
        return super().fields() + [
            (self.date, 'date'),
            (self.period, 'period'),
            (self.sequence, 'sequence'),
        ]

    def toggles(self):
        return super().toggles() + [
            (self.normal, lambda _: {'modifier': None}),
            (self.cor, lambda _: {'modifier': 'COR'}),
            (self.amd, lambda _: {'modifier': 'AMD'}),
            (self.cnl, lambda _: {'modifier': 'CNL'}),
        ]

    def bindSignal(self):
        super().bindSignal()

        self.normal.clicked.connect(lambda: self.modifierChanged.emit(self.modifier))
        self.cor.clicked.connect(lambda: self.modifierChanged.emit(self.modifier))
        self.amd.clicked.connect(lambda: self.modifierChanged.emit(self.modifier))
        self.cnl.clicked.connect(lambda: self.modifierChanged.emit(self.modifier))
        self.prevButton.clicked.connect(lambda: self.requestPeriodShift('prev'))
        self.resetButton.clicked.connect(lambda: self.requestPeriodShift('current'))

        for t in self.temperatures:
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
            t.validate()

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

        pattern = self.patterns.ccc if modifier == 'COR' else self.patterns.aaa
        validator = self.sequence.validator()
        if validator is None or validator.regExp().pattern() != pattern:
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
        self.pipeline.edit({'date': time.strftime('%d%H%M')}, source='clock')

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
        self.populate(self.pipeline.raw)

    def rules(self, raw, previous, changed, source):
        segmentRules(raw, previous, changed, source)
        if source == 'user' and 'period' in changed:
            primaryDurations = self.primary.durations if self.primary.period else None
            raw['period'] = groupPeriodRules(
                raw.get('period', ''),
                previous.get('period', ''),
                window=self.state.durations,
                primaryDurations=primaryDurations,
                indicator=self.indicator,
                spec=self.context.taf.spec,
                autoComplete=self.conf.autoCompletionGroupTime,
                parseWindow=self.durations,
            )

    def fromState(self):
        raw = super().fromState()
        raw['period'] = self.state.period
        return raw

    def fromWidgets(self):
        raw = super().fromWidgets()
        raw['period'] = self.period.text()
        return raw

    def apply(self, raw):
        super().apply(raw)
        period = raw.get('period', '')
        self.state.period = period
        self.state.durations = self.durations(period)

    def clearPeriod(self):
        self.pipeline.edit({'period': ''}, source='validate', force=True)

    def fields(self):
        return super().fields() + [(self.period, 'period')]

    def durations(self, text=None):
        """The window this period spells, against the primary's base time."""
        if text is None:
            text = self.pipeline.value('period')

        if not (isAcceptable(self.period, text) and self.primary.period and self.primary.durations is not None):
            return None

        return parsePeriod(text, self.primary.durations[0])

    def populate(self, raw=None):
        if raw is None:
            self.pipeline.sync(self.fromState())
            return

        super().populate(raw)
        setLineText(self.period, raw.get('period', ''))
        self.coloredText(self.period)

    def bindSignal(self):
        super().bindSignal()
        self.period.editingFinished.connect(self.periodFinished.emit)

    def setupFont(self):
        super().setupFont()
        self.name.setFont(fixedFont())

    def setupValidator(self):
        super().setupValidator()
        period = QRegExpValidator(QRegExp(self.patterns.period))
        self.period.setValidator(period)

    def setupPeriodPlaceholder(self):
        if self.primary.durations is None:
            self.period.setPlaceholderText('')
            return

        time = self.primary.durations[0]
        self.period.setPlaceholderText('{:02d}'.format(time.day))

    def showEvent(self, event):
        super().showEvent(event)
        self.setupPeriodPlaceholder()


class TafFmSegment(TafGroupSegment):

    rules = staticmethod(segmentRules)

    def __init__(self, name='FM', conf=None, context=None, primary=None):
        super().__init__(name, conf, context, primary)

    def setupValidator(self):
        super().setupValidator()
        period = QRegExpValidator(QRegExp(self.patterns.fmPeriod))
        self.period.setValidator(period)

    def durations(self, text=None):
        if text is None:
            text = self.pipeline.value('period')

        if not (isAcceptable(self.period, text) and self.primary.period and self.primary.durations is not None):
            return None

        time = parseTime(text, self.primary.durations[0])
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

    rules = staticmethod(trendRules)

    def __init__(self, name='TREND', conf=None, context=None):
        super().__init__(name, conf, context)
        self.setupUi(self)
        self.setupFont()
        self.setupValidator()
        self.bindSignal()
        self.populate(self.pipeline.raw)

    def fromState(self):
        raw = super().fromState()
        raw.update({
            'isNosig': self.state.isNosig,
            'indicator': self.state.indicator,
            'atChecked': self.state.atChecked,
            'fmChecked': self.state.fmChecked,
            'tlChecked': self.state.tlChecked,
            'period': self.state.period,
        })
        return raw

    def fromWidgets(self):
        raw = super().fromWidgets()
        raw.update({
            'isNosig': self.nosig.isChecked(),
            'indicator': 'BECMG' if self.becmg.isChecked() else 'TEMPO',
            'atChecked': self.at.isChecked(),
            'fmChecked': self.fm.isChecked(),
            'tlChecked': self.tl.isChecked(),
            'period': self.period.text(),
        })
        return raw

    def apply(self, raw):
        super().apply(raw)
        self.state.isNosig = bool(raw.get('isNosig'))
        self.state.indicator = raw.get('indicator', 'BECMG')
        self.state.atChecked = bool(raw.get('atChecked'))
        self.state.fmChecked = bool(raw.get('fmChecked'))
        self.state.tlChecked = bool(raw.get('tlChecked'))
        self.state.period = raw.get('period', '')

    def fields(self):
        return super().fields() + [(self.period, 'period')]

    def toggles(self):
        return super().toggles() + [
            (self.nosig, lambda checked: {'isNosig': checked}),
            (self.becmg, lambda _: {'indicator': 'BECMG'}),
            (self.tempo, lambda _: {'indicator': 'TEMPO'}),
            (self.at, lambda checked: {'atChecked': checked}),
            (self.fm, lambda checked: {'fmChecked': checked}),
            (self.tl, lambda checked: {'tlChecked': checked}),
        ]

    def bindSignal(self):
        super().bindSignal()
        self.period.editingFinished.connect(lambda: self.finishText('period', self.period))

    def setupFont(self):
        super().setupFont()
        font = fixedFont()
        self.becmg.setFont(font)
        self.tempo.setFont(font)

    def setupValidator(self):
        super().setupValidator()
        self.setPeriodValidator(False)

    def setPeriodValidator(self, isRange):
        pattern = self.patterns.trendFmTlPeriod if isRange else self.patterns.trendPeriod
        validator = self.period.validator()
        if validator is None or validator.regExp().pattern() != pattern:
            self.period.setValidator(QRegExpValidator(QRegExp(pattern)))

    def setupPeriodPlaceholder(self):
        time = utcnow() + datetime.timedelta(hours=1)
        self.period.setPlaceholderText('{:02d}'.format(time.hour))

    def populate(self, raw=None):
        if raw is None:
            self.pipeline.sync(self.fromState())
            return

        isNosig = bool(raw.get('isNosig'))
        active = not isNosig
        super().populate(raw, active=active)

        indicator = raw.get('indicator', 'BECMG')
        atChecked = bool(raw.get('atChecked'))
        fmChecked = bool(raw.get('fmChecked'))
        tlChecked = bool(raw.get('tlChecked'))
        period = raw.get('period', '')

        setChecked(self.nosig, isNosig)
        setChecked(self.becmg, indicator == 'BECMG')
        setChecked(self.tempo, indicator != 'BECMG')
        setChecked(self.at, atChecked)
        setChecked(self.fm, fmChecked)
        setChecked(self.tl, tlChecked)

        self.typeGroup.setEnabled(active)
        self.prefixGroup.setEnabled(active)
        self.at.setEnabled(active and indicator != 'TEMPO')

        self.setPeriodValidator(fmChecked and tlChecked)
        setLineText(self.period, period)

        periodActive = active and (atChecked or fmChecked or tlChecked)
        self.period.setEnabled(periodActive)
        if periodActive:
            if not self.period.placeholderText():
                self.setupPeriodPlaceholder()
        elif self.period.placeholderText():
            self.period.setPlaceholderText('')

        self.coloredText(self.period)

    def load(self, tokens):
        """Seed the form from a parsed trend group: state first, then render."""
        self.state = TrendState.fromTokens(tokens, self.conf.units.tafSpeed,
                                           self.conf.weatherWithIntensityList)
        self.pipeline.sync(self.fromState(), source='load', derive=False, changed=True)

    def check(self, scope):
        if scope == 'period':
            if not self.isPeriodActive():
                return ({}, [])
            rawPeriod = self.pipeline.value('period')
            formatted = formatTrendPeriod(
                rawPeriod,
                atChecked=self.state.atChecked,
                fmChecked=self.state.fmChecked,
                tlChecked=self.state.tlChecked,
            )
            error = TrendFormValidator.checkPeriod(formatted, now=utcnow())
            if error:
                return ({'period': ''}, [_translate(error)])
            if formatted != rawPeriod:
                return ({'period': formatted}, [])
            return ({}, [])

        return super().check(scope)

    def validate(self):
        super().validate()
        self.pipeline.validate('period')

    def isPeriodActive(self):
        return (not self.state.isNosig) and any((self.state.atChecked, self.state.fmChecked, self.state.tlChecked))
