import datetime

from PyQt5.QtGui import QIcon, QRegExpValidator
from PyQt5.QtCore import Qt, QRegExp, QCoreApplication, QTimer, pyqtSignal
from PyQt5.QtWidgets import QWidget, QLabel, QLineEdit, QComboBox, QRadioButton, QToolButton, QCheckBox, QTextEdit, QMessageBox, QHBoxLayout, QVBoxLayout

from tafor.core.models import Taf, db
from tafor.core.parsers.base import Pattern
from tafor.core.utils.check import CurrentTaf
from tafor.core.utils.time import isOverlap, parseDayHour, parsePeriod, parseTime
from tafor.ui.qt import Ui_taf_group, Ui_taf_primary, Ui_trend, main_rc


def parseTemperature(value):
    return -int(value[1:]) if 'M' in value else int(value)


def normalizeTemperatureTime(time, primary):
    if time.hour != 0:
        return None

    if time == primary[1]:
        normalizedTime = time - datetime.timedelta(hours=1)
        return '{}24'.format(str(normalizedTime.day).zfill(2))

    return '{}{}'.format(str(time.day).zfill(2), str(time.hour).zfill(2))


class TemperatureState:
    def __init__(self, mode="max"):
        self.mode = mode
        self.value = ""
        self.time = ""

    def isAcceptable(self):
        return bool(self.value and self.time)

    def composeMessage(self):
        if not self.isAcceptable():
            return ""
        prefix = "TX" if self.mode == "max" else "TN"
        return f"{prefix}{self.value}/{self.time}Z"

    def clear(self):
        self.value = ""
        self.time = ""


class SegmentState:
    def __init__(self, unit="KT"):
        self.unit = unit
        self.wind = ""
        self.gust = ""
        self.visibility = ""
        self.weather = ""
        self.weatherWithIntensity = ""
        self.clouds = []  # e.g., ["FEW030", "SCT040"]
        self.cb = ""      # e.g., "BKN030CB"
        self.isCavok = False
        self.isNsc = False

    def composeWeather(self):
        """Public helper to compose core meteorological elements common to all segments."""
        if self.wind:
            winds = f"{self.wind}G{self.gust}{self.unit}" if self.gust else f"{self.wind}{self.unit}"
        else:
            winds = None

        allClouds = list(filter(None, self.clouds + ([self.cb] if self.cb else [])))
        # Sort clouds by height
        sortedClouds = sorted(allClouds, key=lambda c: int(c[3:6]) if len(c) >= 6 and c[3:6].isdigit() else 0)

        if self.isCavok:
            elements = [winds, "CAVOK"]
        elif self.isNsc:
            if any([self.weather, self.weatherWithIntensity]) or (self.visibility and self.visibility != '9999'):
                elements = [winds, self.visibility, self.weatherWithIntensity, self.weather, "NSC"]
            else:
                elements = [winds, "CAVOK"]
        else:
            elements = [winds, self.visibility, self.weatherWithIntensity, self.weather] + sortedClouds
        
        return " ".join(filter(None, elements))

    def clear(self):
        self.wind = ""
        self.gust = ""
        self.visibility = ""
        self.weather = ""
        self.weatherWithIntensity = ""
        self.clouds = []
        self.cb = ""
        self.isCavok = False
        self.isNsc = False


class PrimaryState(SegmentState):
    def __init__(self, icao="", unit="KT", spec="fc"):
        super().__init__(unit)
        self.icao = icao
        self.spec = spec
        self.date = ""
        self.period = ""
        self.durations = None  # (start, end) datetime tuple
        self.type = "NORMAL"  # NORMAL, AMD, COR, CNL
        self.sequence = ""
        self.temperatures = []  # List of TemperatureState

    def isAcceptable(self):
        """Independent check for Primary segment requirements."""
        if self.type == "CNL":
            return bool(self.icao and self.date and self.period and self.sequence)
        
        # Mandatory primary header fields
        headerOk = bool(self.icao and self.date and self.period)
        
        # Core weather elements: Primary MUST have wind
        # and either CAVOK/NSC or both Visibility and some Cloud/Vertical visibility
        hasWind = bool(self.wind)
        hasClouds = any([bool(c) for c in self.clouds] + [bool(self.cb)])
        weatherOk = hasWind and (self.isCavok or self.isNsc or (bool(self.visibility) and hasClouds))
            
        # Temperatures: if any part is filled, it must be complete
        tempsOk = all(t.isAcceptable() for t in self.temperatures if t.value or t.time)
        
        # Sequence is mandatory for AMD/COR
        sequenceOk = bool(self.sequence) if self.type in ["AMD", "COR"] else True
            
        return headerOk and weatherOk and sequenceOk and tempsOk

    def composeMessage(self):
        if self.type == "CNL":
            amd = "AMD"
            messages = ["TAF", amd, self.icao, self.date + "Z" if self.date else "", self.period, "CNL"]
            return " ".join(filter(None, messages))
            
        # Use common weather element helper
        weatherPart = self.composeWeather()
        
        amd = "AMD" if self.type == "AMD" else ""
        cor = "COR" if self.type == "COR" else ""
        timez = self.date + "Z" if self.date else ""
        
        # Sort temperatures: TX first, TN second, then by time
        validTemps = [t for t in self.temperatures if t.isAcceptable()]
        sortedTemps = sorted(validTemps, key=lambda t: (0 if t.mode == "max" else 1, t.time))
        tempTexts = [t.composeMessage() for t in sortedTemps]
        
        messages = ["TAF", amd, cor, self.icao, timez, self.period, weatherPart] + tempTexts
        return " ".join(filter(None, messages))

    def clear(self):
        super().clear()
        self.date = ""
        self.period = ""
        self.durations = None
        self.type = "NORMAL"
        self.sequence = ""
        for t in self.temperatures:
            t.clear()


class GroupState(SegmentState):
    def __init__(self, indicator="TEMPO", unit="KT"):
        super().__init__(unit)
        self.indicator = indicator  # FM, BECMG, TEMPO
        self.period = ""
        self.durations = None  # (start, end) datetime tuple

    def isAcceptable(self):
        """Independent check for Group segment requirements."""
        # At least one weather element is required along with period
        oneRequired = any([self.isNsc, self.isCavok, self.wind, self.visibility, self.weather, self.weatherWithIntensity]
            + [bool(c) for c in self.clouds] + [bool(self.cb)])
        return bool(self.period) and oneRequired

    def composeMessage(self):
        # Use common weather element helper
        weatherPart = self.composeWeather()
        
        if self.indicator == "FM":
            return f"FM{self.period} {weatherPart}".strip()
        else:
            return f"{self.indicator} {self.period} {weatherPart}".strip()

    def clear(self):
        super().clear()
        self.period = ""


class TrendState(SegmentState):
    def __init__(self, unit="KT"):
        super().__init__(unit)
        self.isNosig = False
        self.type = "BECMG"  # BECMG or TEMPO
        self.atChecked = False
        self.fmChecked = False
        self.tlChecked = False
        self.period = ""

    def isAcceptable(self):
        """Independent check for Trend segment requirements."""
        if self.isNosig:
            return True
        
        # At least one weather element must be present/modified
        weatherOk = any([
            self.isNsc, self.isCavok, bool(self.wind), bool(self.visibility),
            bool(self.weather), bool(self.weatherWithIntensity),
            any(bool(c) for c in self.clouds), bool(self.cb)
        ])
        
        # If temporal prefix (AT/FM/TL) is used, period is mandatory
        if any([self.atChecked, self.fmChecked, self.tlChecked]):
            return bool(self.period) and weatherOk
        
        return weatherOk

    def composeMessage(self):
        if self.isNosig:
            return "NOSIG"
        
        # Use common weather element helper
        weatherPart = self.composeWeather()
        
        messages = [self.type]
        if self.atChecked or self.fmChecked or self.tlChecked:
            if self.fmChecked and self.tlChecked:
                # Range period: FMHHMM TLHHMM
                parts = self.period.split('/')
                if len(parts) == 2:
                    messages.append(f"FM{parts[0]} TL{parts[1]}")
            else:
                # Single prefix: AT, FM, or TL
                prefix = ""
                if self.atChecked: prefix = "AT"
                elif self.fmChecked: prefix = "FM"
                elif self.tlChecked: prefix = "TL"
                messages.append(f"{prefix}{self.period}")
        
        messages.append(weatherPart)
        return " ".join(filter(None, messages))

    def clear(self):
        super().clear()
        self.isNosig = False
        self.atChecked = False
        self.fmChecked = False
        self.tlChecked = False
        self.period = ""


class TafValidator(object):

    @staticmethod
    def checkWeather(state):
        weather = state.weather
        weatherWithIntensity = state.weatherWithIntensity
        if not weather or not weatherWithIntensity:
            return None

        if 'TS' in weather and ('TS' in weatherWithIntensity or 'RA' in weatherWithIntensity):
            return QCoreApplication.translate('Editor', 'Weather phenomena conflict')

        return None

    @staticmethod
    def checkGust(state):
        wind = state.wind
        gust = state.gust
        if not wind or not gust or gust == 'P49':
            return None

        windSpeed = wind[-2:]
        if int(windSpeed) == 0 or int(gust) - int(windSpeed) < 5:
            return QCoreApplication.translate('Editor', 'Gust speed must be greater than wind speed by at least 5')

        return None

    @staticmethod
    def checkCloud(state, lineValue):
        if not lineValue:
            return None

        height = lineValue[3:]
        allClouds = list(filter(None, state.clouds + ([state.cb] if state.cb else [])))
        # Filter out the current line value from the comparison list to avoid self-conflict
        otherClouds = [c for c in allClouds if c != lineValue]
        cloudHeights = [cloud[3:6] for cloud in otherClouds]
        
        if cloudHeights.count(height) > 0:
            return QCoreApplication.translate(
                'Editor',
                'Cloud cover with different oktas should not at the same height'
            )

        cloudCover = {'FEW': 1, 'SCT': 3, 'BKN': 5, 'OVC': 8}
        if state.cb:
            cbCover = cloudCover.get(state.cb[:3], 0)
            cbHeight = state.cb[3:6]
            for cloud in otherClouds:
                cover = cloudCover.get(cloud[:3], 0)
                if cbHeight == cloud[3:6] and cbCover + cover > 8:
                    return QCoreApplication.translate(
                        'Editor',
                        'Cloud cover cannot be more than 8 oktas at the same height'
                    )

        orderedClouds = sorted(allClouds, key=lambda cloud: int(cloud[3:6]) if cloud[3:6].isdigit() else 0)
        covers = [cloud[:3] for cloud in orderedClouds]
        if 'OVC' in covers:
            index = covers.index('OVC')
            if index + 1 < len(covers):
                return QCoreApplication.translate('Editor', 'No clouds should above overcast clouds')

        return None

    @staticmethod
    def checkGroupPeriod(groupState, primaryState, span, isBecmg=False):
        if not groupState.period or not primaryState.period:
            return None

        start, end = groupState.durations
        primaryStart, primaryEnd = primaryState.durations

        if end - start > datetime.timedelta(hours=span):
            return QCoreApplication.translate('Editor', 'Change group time more than {} hours').format(span)

        if start < primaryStart or primaryEnd < start:
            return QCoreApplication.translate('Editor', 'Start time of change group is not corret')

        if end < primaryStart or primaryEnd < end or (isBecmg and end == primaryEnd):
            return QCoreApplication.translate('Editor', 'End time of change group is not corret')

        return None

    @staticmethod
    def checkGroupOverlap(groupState, siblings):
        if groupState.durations is None:
            return None

        for sibling in siblings:
            if sibling.durations and isOverlap(groupState.durations, sibling.durations):
                return QCoreApplication.translate('Editor', 'Change group time is overlap')

        return None

    @staticmethod
    def checkFmPeriod(groupState, primaryState):
        if groupState.durations is None or primaryState.durations is None:
            return None

        start, _ = groupState.durations
        primaryStart, primaryEnd = primaryState.durations

        if start < primaryStart or primaryEnd <= start:
            return QCoreApplication.translate('Editor', 'Time of change group is not corret')

        return None

    @staticmethod
    def checkFmOverlap(groupState, siblings):
        if groupState.durations is None:
            return None

        time = groupState.durations[0]
        for sibling in siblings:
            if sibling.durations and sibling.durations[0] <= time <= sibling.durations[1]:
                return QCoreApplication.translate('Editor', 'Change group time is overlap')

        return None

    @staticmethod
    def checkTemperatureTime(tempState, primaryDurations, siblings=None, sameTypeSiblings=None):
        if not tempState.time:
            return None

        text = QCoreApplication.translate('Editor', 'The time of temperature is not corret')
        if primaryDurations is None:
            return text

        try:
            # Re-calculating time from tempState.time (DDHH)
            time = parseDayHour(tempState.time[:2], tempState.time[2:], primaryDurations[0], delta='month')
        except Exception:
            return text

        siblings = siblings or []
        sameTypeSiblings = sameTypeSiblings or []
        valid = primaryDurations[0] <= time <= primaryDurations[1] and time not in siblings

        for sibling in sameTypeSiblings:
            if sibling.day == time.day:
                valid = False

        if not valid:
            return text

        return None

    @staticmethod
    def checkTemperature(tempState, referenceValue):
        if not tempState.value:
            return None

        temperature = parseTemperature(tempState.value)
        if tempState.mode == 'max':
            if referenceValue is not None and temperature <= referenceValue:
                return QCoreApplication.translate('Editor', 'The maximum temperature needs to be greater than the minimum temperature')
        elif tempState.mode == 'min':
            if referenceValue is not None and referenceValue <= temperature:
                return QCoreApplication.translate('Editor', 'The minimum temperature needs to be less than the maximum temperature')

        return None

class TrendValidator(object):

    @staticmethod
    def checkPeriod(value, now=None):
        if not value:
            return None

        if now is None:
            now = datetime.datetime.utcnow()

        delta = datetime.timedelta(hours=2, minutes=30)
        periods = [parseTime(text) for text in value.split('/')]
        errorInfo = QCoreApplication.translate('Editor', 'Trend valid time is not corret')

        if len(periods) == 2:
            if periods[1] <= periods[0]:
                periods[1] = periods[1] + datetime.timedelta(days=1)

            if periods[1] - periods[0] > datetime.timedelta(hours=2):
                return errorInfo

        for time in periods:
            if (time - delta) > now:
                return errorInfo

        return None


class SegmentMixin(object):

    @classmethod
    def upperText(cls, line):
        line.setText(line.text().upper())

    @classmethod
    def coloredText(cls, line):
        if line.hasAcceptableInput():
            line.setStyleSheet('color: black')
        else:
            line.setStyleSheet('color: grey')

    def defaultSignal(self):
        for line in self.findChildren(QLineEdit):
            line.textChanged.connect(self.contentChanged.emit)
            line.textEdited.connect(lambda _, current=line: self.upperText(current))
            line.textChanged.connect(lambda _, current=line: self.coloredText(current))

        for combox in self.findChildren(QComboBox):
            combox.currentTextChanged.connect(lambda: self.contentChanged.emit())

        for button in self.findChildren(QRadioButton):
            button.clicked.connect(lambda: self.contentChanged.emit())

        for checkbox in self.findChildren(QCheckBox):
            checkbox.clicked.connect(lambda: self.contentChanged.emit())

    def setupFont(self):
        fixedFont = self.context.resource.fixedFont()
        for line in self.findChildren(QLineEdit):
            line.setFont(fixedFont)

        for combox in self.findChildren(QComboBox):
            combox.setFont(fixedFont)

        for checkbox in self.findChildren(QCheckBox):
            checkbox.setFont(fixedFont)

        for text in self.findChildren(QTextEdit):
            text.setFont(fixedFont)

    def clear(self):
        for line in self.findChildren(QLineEdit):
            line.clear()

        for combox in self.findChildren(QComboBox):
            combox.setCurrentIndex(0)

        for checkbox in self.findChildren(QCheckBox):
            checkbox.setChecked(False)


class BaseSegment(SegmentMixin, QWidget):

    contentChanged = pyqtSignal()

    def __init__(self, name=None, parent=None, conf=None, context=None):
        super(BaseSegment, self).__init__()
        self.rules = Pattern()
        self.parent = parent
        self.conf = conf
        self.context = context
        self.identifier = ''.join(c for c in name if c.isalpha())
        
        # Initialize specific state based on the type of widget
        unit = 'KT' if self.conf.unit == 'imperial' else 'MPS'
        if self.identifier == 'PRIMARY':
            self.state = PrimaryState(icao=self.conf.airport, unit=unit, spec=self.context.taf.spec)
        elif self.identifier in ['TEMPO', 'BECMG', 'FM']:
            self.state = GroupState(indicator=self.identifier, unit=unit)
        elif self.identifier == 'TREND':
            self.state = TrendState(unit=unit)
        else:
            self.state = SegmentState(unit=unit)

    def bindSignal(self):
        if hasattr(self, 'cavok'):
            self.cavok.toggled.connect(self.setCavok)
            self.nsc.toggled.connect(self.setNsc)

        self.wind.textChanged.connect(self.setGust)
        self.gust.editingFinished.connect(self.validateGust)
        self.weather.lineEdit().textChanged.connect(self.setWeatherWithIntensity)
        self.weather.lineEdit().editingFinished.connect(lambda: self.validateWeather(self.weather))
        self.weatherWithIntensity.lineEdit().editingFinished.connect(lambda: self.validateWeather(self.weatherWithIntensity))
        self.cloud1.textEdited.connect(self.setVv)
        self.cloud1.editingFinished.connect(lambda: self.validateCloud(self.cloud1))
        self.cloud2.editingFinished.connect(lambda: self.validateCloud(self.cloud2))
        self.cloud3.editingFinished.connect(lambda: self.validateCloud(self.cloud3))
        self.cb.editingFinished.connect(lambda: self.validateCloud(self.cb))

        for line in self.findChildren(QLineEdit):
            line.textChanged.connect(self.syncToState)
        for combo in self.findChildren(QComboBox):
            combo.currentTextChanged.connect(self.syncToState)
        for check in self.findChildren(QCheckBox):
            check.toggled.connect(self.syncToState)

        self.defaultSignal()

    def syncToState(self):
        self.state.wind = self.wind.text() if self.wind.hasAcceptableInput() else ""
        self.state.gust = self.gust.text() if self.gust.hasAcceptableInput() else ""
        self.state.visibility = self.vis.text() if self.vis.hasAcceptableInput() else ""
        self.state.weather = self.weather.currentText() if self.weather.lineEdit().hasAcceptableInput() else ""
        self.state.weatherWithIntensity = self.weatherWithIntensity.currentText() if self.weatherWithIntensity.lineEdit().hasAcceptableInput() else ""
        
        clouds = []
        if self.cloud1.hasAcceptableInput(): clouds.append(self.cloud1.text())
        if self.cloud2.hasAcceptableInput(): clouds.append(self.cloud2.text())
        if self.cloud3.hasAcceptableInput(): clouds.append(self.cloud3.text())
        self.state.clouds = clouds
        self.state.cb = self.cb.text() + 'CB' if self.cb.hasAcceptableInput() else ""
        
        if hasattr(self, 'cavok'):
            self.state.isCavok = self.cavok.isChecked()
            self.state.isNsc = self.nsc.isChecked()

    def setupPeriodPlaceholder(self):
        raise NotImplementedError

    def setClouds(self, enbale):
        if enbale:
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
        if self.identifier == 'PRIMARY':
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
        error = TafValidator.checkWeather(self.state)
        if error:
            line.setCurrentIndex(-1)
            self.context.flash.editor(self.editorname(), error)

    def validateGust(self):
        error = TafValidator.checkGust(self.state)
        if error:
            self.gust.clear()
            self.context.flash.editor(self.editorname(), error)

    def validateCloud(self, line):
        error = TafValidator.checkCloud(self.state, line.text())
        if error:
            self.context.flash.editor(self.editorname(), error)
            line.clear()
            return

    def validate(self):
        self.validateGust()
        self.validateWeather(self.weather)
        self.validateCloud(self.cloud3)
        self.validateCloud(self.cloud2)
        self.validateCloud(self.cloud1)
        self.validateCloud(self.cb)

    def editorname(self):
        return 'trend' if 'trend' in self.__class__.__name__.lower() else 'taf'

    def message(self):
        return self.state.composeMessage()

    def hasAcceptableInput(self):
        return self.state.isAcceptable()

    def clear(self):
        self.state.clear()

        for line in self.findChildren(QLineEdit):
            if line.objectName() not in ('date', 'period'):
                line.clear()

        for combox in self.findChildren(QComboBox):
            combox.setCurrentIndex(0)

        for checkbox in self.findChildren(QCheckBox):
            checkbox.setChecked(False)


class TemperatureGroup(SegmentMixin, QWidget):

    temperatureChanged = pyqtSignal()

    def __init__(self, mode='max', canSwitch=False, parent=None, context=None):
        super(TemperatureGroup, self).__init__(parent)
        self.state = TemperatureState(mode)
        self.canSwitch = canSwitch
        self.parent = parent
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

        self.temp.textChanged.connect(self.syncToState)
        self.tempTime.textChanged.connect(self.syncToState)
        self.temp.textChanged.connect(self.temperatureChanged.emit)
        self.tempTime.textChanged.connect(self.temperatureChanged.emit)

        self.tempTime.editingFinished.connect(self.validateTemperatureTime)
        self.temp.editingFinished.connect(self.validateTemperature)

    def syncToState(self):
        self.state.value = self.temp.text() if self.temp.hasAcceptableInput() else ""
        self.state.time = self.tempTime.text() if self.tempTime.hasAcceptableInput() else ""

    def setupValidator(self):
        temperature = QRegExpValidator(QRegExp(self.parent.rules.temperature, Qt.CaseInsensitive))
        self.temp.setValidator(temperature)

        dayHour = QRegExpValidator(QRegExp(self.parent.rules.dayHour))
        self.tempTime.setValidator(dayHour)

    def setLabel(self):
        if self.state.mode == 'max':
            text = QCoreApplication.translate('Editor', 'Max Temperature')
            icon = 'warm'
        else:
            text = QCoreApplication.translate('Editor', 'Min Temperature')
            icon = 'cold'

        self.label.setText(text)
        self.switchButton.setIcon(QIcon(':/{}.png'.format(icon)))

    def validateTemperatureTime(self):
        if not self.parent.period.text() or not self.tempTime.hasAcceptableInput():
            return

        error = TafValidator.checkTemperatureTime(
            self.state,
            self.parent.state.durations,
            siblings=self.parent.findTemperatureTime(self),
            sameTypeSiblings=self.parent.findTemperatureTime(self, sameType=True),
        )
        if error:
            self.state.time = ""
            self.tempTime.clear()
            self.context.flash.editor('taf', error)
            return

        # Time normalization can stay in UI or move to state, keep here for now as it affects UI text
        time = parseDayHour(self.state.time[:2], self.state.time[2:], self.parent.state.durations[0], delta='month')
        normalized = normalizeTemperatureTime(time, self.parent.state.durations)
        if normalized:
            self.tempTime.setText(normalized)

    def validateTemperature(self):
        if not self.temp.hasAcceptableInput():
            return

        error = TafValidator.checkTemperature(
            self.state,
            self.parent.findTemperature(self),
        )
        if error:
            self.state.value = ""
            self.temp.clear()
            self.context.flash.editor('taf', error)
            return

    def switchMode(self):
        self.state.mode = 'min' if self.state.mode == 'max' else 'max'
        self.setLabel()
        self.validateTemperature()
        self.validateTemperatureTime()

    def hasAcceptableInput(self):
        return self.state.isAcceptable()

    def composeMessage(self):
        return self.state.composeMessage()

    def widgets(self):
        if self.canSwitch:
            return [self.switchButton, self.temp, self.tempTime]
        
        return [self.temp, self.tempTime]

    def clear(self):
        self.state.clear()
        self.temp.clear()
        self.tempTime.clear()


class TafPrimarySegment(BaseSegment, Ui_taf_primary.Ui_Editor):

    def __init__(self, name='PRIMARY', parent=None, conf=None, context=None):
        super(TafPrimarySegment, self).__init__(name, parent, conf, context)
        self.setupUi(self)

        self.setupValidator()
        self.period.setEnabled(False)
        self.sequence.setEnabled(False)

        self.groupCheckboxs = [
            self.fmCheckbox,
            self.becmg1Checkbox, self.becmg2Checkbox, self.becmg3Checkbox,
            self.tempo1Checkbox, self.tempo2Checkbox, self.tempo3Checkbox,
        ]

        self.tmax = TemperatureGroup(mode='max', parent=self, context=self.context)
        self.tmin = TemperatureGroup(mode='min', parent=self, context=self.context)
        self.temperatureLayout.addWidget(self.tmax)
        self.temperatureLayout.addWidget(self.tmin)
        self.temperatures = [self.tmax, self.tmin]

        if self.context.taf.spec == 'ft30':
            self.temp = TemperatureGroup(canSwitch=True, parent=self, context=self.context)
            self.temperatureLayout.addWidget(self.temp)
            self.temperatures.append(self.temp)
            self.becmg3Checkbox.setStyleSheet('QCheckBox {margin-top: 4px;}')
            self.tempo3Checkbox.setStyleSheet('QCheckBox {margin-top: 4px;}')

        # Link temperature states to primary state
        self.state.temperatures = [t.state for t in self.temperatures]

        self.prevButton.setIcon(QIcon(':/back.png'))
        self.resetButton.setIcon(QIcon(':/reset.png'))

        self.offset = 0

        self.setupFont()
        self.bindSignal()
        self.initMessageSpec()
        self.setOrder()

    def syncToState(self):
        super(TafPrimarySegment, self).syncToState()
        self.state.date = self.date.text()
        self.state.period = self.period.text()
        self.state.sequence = self.sequence.text()
        
        if self.normal.isChecked(): self.state.type = 'NORMAL'
        elif self.cor.isChecked(): self.state.type = 'COR'
        elif self.amd.isChecked(): self.state.type = 'AMD'
        elif self.cnl.isChecked(): self.state.type = 'CNL'

    def setOrder(self):
        orders = [self.nsc]
        for t in self.temperatures:
            orders += t.widgets()

        for p, n in zip(orders, orders[1:]):
            self.setTabOrder(p, n)

    def setupValidator(self):
        super(TafPrimarySegment, self).setupValidator()

        date = QRegExpValidator(QRegExp(self.rules.date))
        self.date.setValidator(date)

    def bindSignal(self):
        super(TafPrimarySegment, self).bindSignal()

        self.normal.clicked.connect(self.updateMessageType)
        self.cor.clicked.connect(self.updateMessageType)
        self.amd.clicked.connect(self.updateMessageType)
        self.cnl.clicked.connect(self.updateMessageType)
        self.prevButton.clicked.connect(lambda: self.setCurrentPeriod('prev'))
        self.resetButton.clicked.connect(lambda: self.setCurrentPeriod('reset'))

        for t in self.temperatures:
            t.temperatureChanged.connect(lambda: self.contentChanged.emit())
            t.temperatureChanged.connect(self.syncToState)

        self.timer = QTimer()
        self.timer.timeout.connect(self.setDate)
        self.timer.start(1 * 1000)

    def validate(self):
        super(TafPrimarySegment, self).validate()
        for t in self.temperatures:
            t.validateTemperatureTime()
            t.validateTemperature()

    def initMessageSpec(self):
        if 'ft' in self.context.taf.spec:
            self.tempo3Checkbox.show()
        else:
            self.tempo3Checkbox.hide()
            self.tempo3Checkbox.setChecked(False)

    def updateMessageType(self):
        if not self.date.hasAcceptableInput():
            return

        self.taf = CurrentTaf(self.context.taf.spec, time=datetime.datetime.utcnow(), offset=self.offset)
        if self.normal.isChecked():
            self.setNormalPeriod(self.taf)
            self.sequence.clear()
            self.sequence.setEnabled(False)

        else:
            self.setAmendPeriod(self.taf)
            aaa = QRegExpValidator(QRegExp(self.rules.aaa, Qt.CaseInsensitive))
            ccc = QRegExpValidator(QRegExp(self.rules.ccc, Qt.CaseInsensitive))

            if self.cor.isChecked():
                order = self.amendNumber('COR')
                self.sequence.setValidator(ccc)
            else:
                order = self.amendNumber('AMD')
                self.sequence.setValidator(aaa)

            self.sequence.setEnabled(True)
            self.sequence.setText(order)

        if self.cnl.isChecked():
            for c in self.groupCheckboxs:
                c.setEnabled(False)
                c.setChecked(False)
        else:
            for c in self.groupCheckboxs:
                c.setEnabled(True)

    def setNormalPeriod(self, taf, strict=False):
        period = taf.period(strict=strict)
        expired = datetime.datetime.utcnow() - datetime.timedelta(hours=32)
        with db.session() as session:
            recent = session.query(Taf).filter(Taf.text.contains(period), Taf.created > expired).order_by(Taf.created.desc()).first()

        if period and recent or not self.date.hasAcceptableInput():
            self.period.clear()
            self.state.durations = None
            self.state.period = ""
        else:
            self.period.setText(period)
            self.state.durations = taf.durations()

    def setAmendPeriod(self, taf):
        self.amdPeriod = taf.period(strict=False)
        self.period.setText(self.amdPeriod)
        self.state.durations = taf.durations()

    def setCurrentPeriod(self, action):
        if action == 'reset':
            self.offset = 0
            self.updateMessageType()
            self.resetButton.setEnabled(False)
            self.prevButton.setEnabled(True)

        if action == 'prev':
            title = QCoreApplication.translate('Editor', 'Tips')
            text = QCoreApplication.translate('Editor', 'Do you want to change the message valid period to previous?')
            ret = QMessageBox.question(self, title, text)
            if ret == QMessageBox.Yes:
                self.offset -= 1
                self.updateMessageType()
                self.resetButton.setEnabled(True)
                self.prevButton.setEnabled(True)

                if self.offset < -1:
                    self.prevButton.setEnabled(False)

    def amendNumber(self, sort):
        expired = datetime.datetime.utcnow() - datetime.timedelta(hours=24)
        with db.session() as session:
            query = session.query(Taf).filter(Taf.text.contains(self.amdPeriod), Taf.created > expired)

            if sort == 'COR':
                count = query.filter(Taf.text.contains('COR')).count()
                order = chr(ord('A') + count)
                return 'CC' + order
            else:
                count = query.filter(Taf.text.contains('AMD')).count()
                order = chr(ord('A') + count)
                return 'AA' + order

    def findTemperature(self, oneself):
        temps = [t.state.value for t in self.temperatures if t.state.value and t is not oneself]
        if temps:
            temps = [parseTemperature(t) for t in temps]
            if oneself.state.mode == 'max':
                return min(temps)
            else:
                return max(temps)
        else:
            return None

    def findTemperatureTime(self, oneself, sameType=False):
        times = []
        for t in self.temperatures:
            condition = oneself.state.mode == t.state.mode if sameType else True
            if t.state.time and t is not oneself and condition:
                try:
                    time = parseDayHour(t.state.time[:2], t.state.time[2:], self.state.durations[0], delta='month')
                    times.append(time)
                except:
                    pass

        return times

    def setDate(self):
        time = datetime.datetime.utcnow()
        self.date.setText(time.strftime('%d%H%M'))

    def showEvent(self, event):
        self.setDate()

    def clearType(self):
        self.normal.setChecked(True)
        self.sequence.clear()
        self.resetButton.setEnabled(False)
        self.prevButton.setEnabled(True)
        self.offset = 0

    def isCancelMode(self):
        return self.cnl.isChecked()

    def clear(self):
        super(TafPrimarySegment, self).clear()

        self.cavok.setChecked(False)
        self.nsc.setChecked(False)

        for c in self.groupCheckboxs:
            c.setChecked(False)

        for t in self.temperatures:
            t.clear()


class TafGroupSegment(BaseSegment, Ui_taf_group.Ui_Editor):

    def __init__(self, name='TEMPO', parent=None, conf=None, context=None):
        super(TafGroupSegment, self).__init__(name, parent, conf, context)
        self.setupUi(self)
        self.name.setText(name)
        self.setupFont()
        self.setupValidator()
        self.bindSignal()
        self.periodText = ''

    def syncToState(self):
        super(TafGroupSegment, self).syncToState()
        self.state.period = self.period.text()

    def bindSignal(self):
        super(TafGroupSegment, self).bindSignal()
        self.period.textEdited.connect(self.fillPeriod)
        self.period.textChanged.connect(self.updateDurations)
        self.period.editingFinished.connect(self.validatePeriod)
        self.period.editingFinished.connect(self.validateGroupsPeriod)

    def setupFont(self):
        super(TafGroupSegment, self).setupFont()
        self.name.setFont(self.context.resource.fixedFont())

    def setupValidator(self):
        super(TafGroupSegment, self).setupValidator()
        period = QRegExpValidator(QRegExp(self.rules.period))
        self.period.setValidator(period)

    def setupPeriodPlaceholder(self):
        if self.parent.state.durations is None:
            self.period.setPlaceholderText('')
            return

        time = self.parent.state.durations[0]
        self.period.setPlaceholderText('{:02d}'.format(time.day))

    def fillPeriod(self):
        if self.conf.autoCompletionGroupTime:
            self.autoCompletePeriod()
        else:
            self.formatSeparator()

    def formatSeparator(self):
        text = self.period.text()
        if len(text) > len(self.periodText):
            if len(text) == 4:
                text += '/'
            self.period.setText(text)
        self.periodText = text

    def autoCompletePeriod(self):
        if self.parent.state.durations is None or not self.parent.period.text():
            return

        text = self.period.text()
        if len(text) > len(self.periodText):
            if len(text) == 4:
                durations = self.parent.state.durations
                try:
                    start = parseDayHour(text[:2], text[2:], durations[0], delta='month')
                except Exception:
                    return

                if durations[1] <= start:
                    return

                if self.identifier.startswith('TEMPO'):
                    delta = datetime.timedelta(hours=self.span())
                    end = start + delta
                    if durations[1] <= end:
                        text = '{:02d}{:02d}/{}'.format(start.day, start.hour, self.parent.period.text()[5:])
                    else:
                        text = '{:02d}{:02d}/{:02d}{:02d}'.format(start.day, start.hour, end.day, end.hour)

                if self.identifier.startswith('BECMG'):
                    delta = datetime.timedelta(hours=1)
                    end = start + delta
                    if durations[1] <= end:
                        return

                    text = '{:02d}{:02d}/{:02d}{:02d}'.format(start.day, start.hour, end.day, end.hour)

            self.period.setText(text)

        self.periodText = text

    def span(self):
        if self.identifier.startswith('TEMPO'):
            if 'ft' in self.context.taf.spec:
                duration = 6
            else:
                duration = 4
        else:
            duration = 2

        return duration

    def updateDurations(self):
        if self.period.hasAcceptableInput() and self.parent.period.text():
            period = self.period.text()
            basetime = self.parent.state.durations[0]
            start, end = parsePeriod(period, basetime)
            self.state.durations = (start, end)

            if end.hour == 0 and not period.endswith('24'):
                end -= datetime.timedelta(minutes=1)
                text = '{:02d}{:02d}/{:02d}24'.format(start.day, start.hour, end.day)
                self.period.setText(text)
        else:
            self.state.durations = None

    def validate(self):
        super(TafGroupSegment, self).validate()
        self.validatePeriod()
        self.validateGroupsPeriod()

    def validatePeriod(self):
        error = TafValidator.checkGroupPeriod(
            self.state,
            self.parent.state,
            self.span(),
            isBecmg=self.identifier.startswith('BECMG'),
        )
        if error:
            self.period.clear()
            self.context.flash.editor('taf', error)

    def validateGroupsPeriod(self):
        groups = self.parent.parent.tempos if self.identifier.startswith('TEMPO') else self.parent.parent.becmgs
        siblings = [g.state for g in groups if g.isVisible() and g.state and self != g]
        error = TafValidator.checkGroupOverlap(self.state, siblings)
        if error:
            self.period.clear()
            self.context.flash.editor('taf', error)

    def hasAcceptableInput(self):
        return self.state.isAcceptable()

    def showEvent(self, event):
        self.setupPeriodPlaceholder()

    def clear(self):
        super(TafGroupSegment, self).clear()
        self.period.clear()
        self.period.setPlaceholderText('')
        self.periodText = ''


class TafFmSegment(TafGroupSegment):

    def __init__(self, name='FM', parent=None, conf=None, context=None):
        super(TafFmSegment, self).__init__(name, parent, conf, context)

    def bindSignal(self):
        super(TafFmSegment, self).bindSignal()
        self.period.textEdited.disconnect(self.fillPeriod)

    def setupValidator(self):
        super(TafFmSegment, self).setupValidator()
        period = QRegExpValidator(QRegExp(self.rules.fmPeriod))
        self.period.setValidator(period)

    def updateDurations(self):
        if self.period.hasAcceptableInput() and self.parent.period.text():
            period = self.period.text()
            basetime = self.parent.state.durations[0]
            time = parseTime(period, basetime)
            self.state.durations = (time, time)
        else:
            self.state.durations = None

    def validatePeriod(self):
        # Using states for validation where possible
        error = TafValidator.checkFmPeriod(self.state, self.parent.state)
        if error:
            self.period.clear()
            self.context.flash.editor('taf', error)

    def validateGroupsPeriod(self):
        siblings = [g.state for g in self.parent.parent.becmgs if g.isVisible() and g.state and self != g]
        error = TafValidator.checkFmOverlap(self.state, siblings)
        if error:
            self.period.clear()
            self.context.flash.editor('taf', error)

    def message(self):
        return self.state.composeMessage()

    def clear(self):
        super(TafFmSegment, self).clear()

        self.cavok.setChecked(False)
        self.nsc.setChecked(False)


class TafBecmgSegment(TafGroupSegment):

    def __init__(self, name='BECMG', parent=None, conf=None, context=None):
        super(TafBecmgSegment, self).__init__(name, parent, conf, context)

    def message(self):
        return self.state.composeMessage()

    def clear(self):
        super(TafBecmgSegment, self).clear()

        self.cavok.setChecked(False)
        self.nsc.setChecked(False)


class TafTempoSegment(TafGroupSegment):

    def __init__(self, name='TEMPO', parent=None, conf=None, context=None):
        super(TafTempoSegment, self).__init__(name, parent, conf, context)
        self.cavok.hide()
        self.nsc.hide()

    def message(self):
        return self.state.composeMessage()


class TrendSegment(BaseSegment, Ui_trend.Ui_Editor):

    def __init__(self, name='TREND', parent=None, conf=None, context=None):
        super(TrendSegment, self).__init__(name, parent, conf, context)
        self.setupUi(self)
        self.setupFont()
        self.setupValidator()
        self.bindSignal()
        self.periodText = ''

    def syncToState(self):
        super(TrendSegment, self).syncToState()
        self.state.isNosig = self.nosig.isChecked()
        self.state.type = "BECMG" if self.becmg.isChecked() else "TEMPO"
        self.state.atChecked = self.at.isChecked()
        self.state.fmChecked = self.fm.isChecked()
        self.state.tlChecked = self.tl.isChecked()
        self.state.period = self.period.text()

    def bindSignal(self):
        super(TrendSegment, self).bindSignal()
        self.nosig.toggled.connect(self.setNosig)
        self.at.toggled.connect(self.setAt)
        self.fm.toggled.connect(self.setFmTl)
        self.tl.toggled.connect(self.setFmTl)

        self.becmg.clicked.connect(self.updateAtStatus)
        self.tempo.clicked.connect(self.updateAtStatus)

        self.period.textEdited.connect(self.autoFormatPeriod)
        self.period.editingFinished.connect(self.validatePeriod)

        # Sync state on UI toggle/click
        self.nosig.toggled.connect(self.syncToState)
        self.at.toggled.connect(self.syncToState)
        self.fm.toggled.connect(self.syncToState)
        self.tl.toggled.connect(self.syncToState)
        self.becmg.clicked.connect(self.syncToState)
        self.tempo.clicked.connect(self.syncToState)

    def setupFont(self):
        super(TrendSegment, self).setupFont()
        font = self.context.resource.fixedFont()
        self.becmg.setFont(font)
        self.tempo.setFont(font)

    def autoFormatPeriod(self):
        if self.fm.isChecked() and self.tl.isChecked():   
            self.formatSeparator()

    def formatSeparator(self):
        text = self.period.text()
        if len(text) > len(self.periodText):
            if len(text) == 4:
                text += '/'
            self.period.setText(text)
        self.periodText = text

    def setupValidator(self):
        super(TrendSegment, self).setupValidator()
        self.setupPeriodValidator()

    def setupPeriodValidator(self):
        if self.fm.isChecked() and self.tl.isChecked():
            period = QRegExpValidator(QRegExp(self.rules.trendFmTlPeriod))
        else:
            period = QRegExpValidator(QRegExp(self.rules.trendPeriod))

        self.period.setValidator(period)

    def setupPeriodPlaceholder(self):
        time = datetime.datetime.utcnow() + datetime.timedelta(hours=1)
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
        error = TrendValidator.checkPeriod(self.period.text(), now=datetime.datetime.utcnow())
        if error:
            self.period.clear()
            self.context.flash.editor('trend', error)

    def updateAtStatus(self):
        if self.tempo.isChecked():
            self.at.setEnabled(False)
            self.at.setChecked(False)
        else:
            self.at.setEnabled(True)

    def isPeriodActive(self):
        return self.period.isEnabled()

    def hasAcceptableInput(self):
        return self.state.isAcceptable()

    def message(self):
        return self.state.composeMessage()

    def clear(self):
        super(TrendSegment, self).clear()
        self.at.setChecked(False)
        self.fm.setChecked(False)
        self.tl.setChecked(False)
        self.nosig.setChecked(False)

        self.cavok.setChecked(False)
        self.nsc.setChecked(False)

        self.period.setEnabled(False)
        self.period.clear()
        self.period.setPlaceholderText('')
