import json
import datetime

from PyQt5.QtGui import QIcon, QRegExpValidator
from PyQt5.QtCore import Qt, QRegExp, QCoreApplication, QTimer, pyqtSignal
from PyQt5.QtWidgets import QWidget, QLabel, QLineEdit, QComboBox, QRadioButton, QToolButton, QCheckBox, QMessageBox, QHBoxLayout, QVBoxLayout

from tafor import conf
from tafor.utils import Pattern, CurrentTaf, CheckTaf, boolean
from tafor.utils.convert import parseDayHour, parsePeriod, parseTime, isOverlap
from tafor.states import context
from tafor.models import db, Taf
from tafor.components.ui import Ui_taf_primary, Ui_taf_group, Ui_trend, main_rc


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
            line.textChanged.connect(self.checkComplete)

        for combox in self.findChildren(QComboBox):
            combox.currentTextChanged.connect(self.checkComplete)

        for button in self.findChildren(QRadioButton):
            button.clicked.connect(self.checkComplete)

        for checkbox in self.findChildren(QCheckBox):
            checkbox.clicked.connect(self.checkComplete)

    def clear(self):
        # 部分组件不能用
        for line in self.findChildren(QLineEdit):
            line.clear()

        for combox in self.findChildren(QComboBox):
            combox.setCurrentIndex(0)

        for checkbox in self.findChildren(QCheckBox):
            checkbox.setChecked(False)


class BaseSegment(QWidget, SegmentMixin):
    completeSignal = pyqtSignal(bool)

    def __init__(self, name=None, parent=None):
        super(BaseSegment, self).__init__()
        self.rules = Pattern()
        self.parent = parent
        self.complete = False
        self.identifier = ''.join(c for c in name if c.isalpha())
        self.durations = None
        self.periodText = ''

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

        self.wind.textEdited.connect(lambda: self.upperText(self.wind))
        self.gust.textEdited.connect(lambda: self.upperText(self.gust))
        self.weather.lineEdit().textChanged.connect(lambda: self.upperText(self.weather.lineEdit()))
        self.weatherWithIntensity.lineEdit().textChanged.connect(lambda: self.upperText(self.weatherWithIntensity.lineEdit()))
        self.cloud1.textEdited.connect(lambda: self.upperText(self.cloud1))
        self.cloud2.textEdited.connect(lambda: self.upperText(self.cloud2))
        self.cloud3.textEdited.connect(lambda: self.upperText(self.cloud3))
        self.cb.textEdited.connect(lambda: self.upperText(self.cb))

        self.wind.textEdited.connect(lambda: self.coloredText(self.wind))
        self.gust.textEdited.connect(lambda: self.coloredText(self.gust))
        self.weather.lineEdit().textChanged.connect(lambda: self.coloredText(self.weather.lineEdit()))
        self.weatherWithIntensity.lineEdit().textChanged.connect(lambda: self.coloredText(self.weatherWithIntensity.lineEdit()))
        self.vis.textEdited.connect(lambda: self.coloredText(self.vis))
        self.cloud1.textEdited.connect(lambda: self.coloredText(self.cloud1))
        self.cloud2.textEdited.connect(lambda: self.coloredText(self.cloud2))
        self.cloud3.textEdited.connect(lambda: self.coloredText(self.cloud3))
        self.cb.textEdited.connect(lambda: self.coloredText(self.cb))

        self.defaultSignal()

    def setPeriodPlaceholder(self):
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

    def setValidator(self):
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

        weather = conf.value('Message/Weather')
        weathers = [''] + json.loads(weather) if weather else ['']
        if self.identifier == 'PRIMARY':
            weathers = [w for w in weathers if w != 'NSW']
        self.weather.addItems(weathers)
        weather = QRegExpValidator(QRegExp(r'{}'.format('|'.join(weathers)), Qt.CaseInsensitive))
        self.weather.setValidator(weather)

        weatherWithIntensity = conf.value('Message/WeatherWithIntensity')
        intensityWeathers = ['']
        if weatherWithIntensity:
            weathers = json.loads(weatherWithIntensity)
            for w in weathers:
                intensityWeathers.append('-{}'.format(w))
            for w in weathers:
                intensityWeathers.append(w)
            for w in weathers:
                intensityWeathers.append('+{}'.format(w))
        self.weatherWithIntensity.addItems(intensityWeathers)
        intensityWeather = QRegExpValidator(QRegExp(r'[-+]?({})'.format('|'.join(weathers)), Qt.CaseInsensitive))
        self.weatherWithIntensity.setValidator(intensityWeather)

    def autoFillSlash(self):
        text = self.period.text()
        if len(text) > len(self.periodText):
            if len(text) == 4:
                text += '/'

            self.period.setText(text)

        self.periodText = text

    def validateWeather(self, line):
        if self.weather.lineEdit().hasAcceptableInput() and self.weather.currentText() and \
            self.weatherWithIntensity.lineEdit().hasAcceptableInput() and self.weatherWithIntensity.currentText():
            weather = self.weather.currentText()
            weatherWithIntensity = self.weatherWithIntensity.currentText()

            if 'TS' in weather and ('TS' in weatherWithIntensity or 'RA' in weatherWithIntensity):
                line.setCurrentIndex(-1)
                self.parent.showNotificationMessage(QCoreApplication.translate('Editor', 'Weather phenomena conflict'))

    def validateGust(self):
        if not self.gust.hasAcceptableInput() or not self.wind.hasAcceptableInput():
            self.gust.clear()
            return

        windSpeed = self.wind.text()[-2:]
        gust = self.gust.text()

        if gust == 'P49':
            return

        if int(windSpeed) == 0 or int(gust) - int(windSpeed) < 5:
            self.gust.clear()

    def validateCloud(self, line):
        if not line.hasAcceptableInput():
            return

        cloud1 = self.cloud1.text() if self.cloud1.hasAcceptableInput() else None
        cloud2 = self.cloud2.text() if self.cloud2.hasAcceptableInput() else None
        cloud3 = self.cloud3.text() if self.cloud3.hasAcceptableInput() else None
        clouds = filter(None, [cloud1, cloud2, cloud3])

        height = line.text()[3:]
        cloudHeights = [c[3:] for c in clouds]
        if cloudHeights.count(height) > 1:
            line.clear()

    def validate(self):
        self.validateGust()
        self.validateWeather(self.weather)
        self.validateCloud(self.cloud3)
        self.validateCloud(self.cloud2)
        self.validateCloud(self.cloud1)

    def message(self):
        wind = self.wind.text() if self.wind.hasAcceptableInput() else None
        gust = self.gust.text() if self.gust.hasAcceptableInput() else None
        unit = 'KT' if context.environ.unit() == 'imperial' else 'MPS'

        if wind:
            winds = ''.join([wind, 'G', gust, unit]) if gust else ''.join([wind, unit])
        else:
            winds = None

        vis = self.vis.text() if self.vis.hasAcceptableInput() else None
        weather = self.weather.currentText() if self.weather.lineEdit().hasAcceptableInput() else None
        weatherWithIntensity = self.weatherWithIntensity.currentText() if self.weatherWithIntensity.lineEdit().hasAcceptableInput() else None
        cloud1 = self.cloud1.text() if self.cloud1.hasAcceptableInput() else None
        cloud2 = self.cloud2.text() if self.cloud2.hasAcceptableInput() else None
        cloud3 = self.cloud3.text() if self.cloud3.hasAcceptableInput() else None
        cb = self.cb.text() + 'CB' if self.cb.hasAcceptableInput() else None

        clouds = sorted(filter(None, [cloud1, cloud2, cloud3, cb]), key=lambda cloud: int(cloud[3:6]))

        if hasattr(self, 'cavok'):
            if self.cavok.isChecked():
                messages = [winds, 'CAVOK']
            elif self.nsc.isChecked():
                if any([weather, weatherWithIntensity]) or vis != '9999':
                    messages = [winds, vis, weatherWithIntensity, weather, 'NSC']
                else:
                    messages = [winds, 'CAVOK']
            else:
                messages = [winds, vis, weatherWithIntensity, weather] + clouds
        else:
            messages = [winds, vis, weatherWithIntensity, weather] + clouds
        self.text = ' '.join(filter(None, messages))

    def checkComplete(self):
        raise NotImplementedError

    def clear(self):
        self.wind.clear()
        self.gust.clear()
        self.vis.clear()
        self.weather.setCurrentIndex(-1)
        self.weatherWithIntensity.setCurrentIndex(-1)
        self.cloud1.clear()
        self.cloud2.clear()
        self.cloud3.clear()
        self.cb.clear()
        self.durations = None


class TemperatureGroup(QWidget, SegmentMixin):

    def __init__(self, mode='max', canSwitch=False, parent=None):
        super(TemperatureGroup, self).__init__(parent)
        self.mode = mode
        self.canSwitch = canSwitch
        self.parent = parent
        self.temperature = None
        self.time = None

        self.setupUi()
        self.setValidator()
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

        self.temp.textEdited.connect(lambda: self.upperText(self.temp))
        self.temp.textEdited.connect(lambda: self.coloredText(self.temp))
        self.tempTime.textEdited.connect(lambda: self.coloredText(self.tempTime))

        self.tempTime.editingFinished.connect(self.validateTemperatureTime)
        self.temp.editingFinished.connect(self.validateTemperature)

        self.temp.textChanged.connect(self.parent.checkComplete)
        self.tempTime.textChanged.connect(self.parent.checkComplete)

    def setValidator(self):
        temperature = QRegExpValidator(QRegExp(self.parent.rules.temperature, Qt.CaseInsensitive))
        self.temp.setValidator(temperature)

        dayHour = QRegExpValidator(QRegExp(self.parent.rules.dayHour))
        self.tempTime.setValidator(dayHour)

    def setLabel(self):
        if self.mode == 'max':
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

        durations = self.parent.durations
        text = QCoreApplication.translate('Editor', 'The time of temperature is not corret')
        try:
            time = parseDayHour(self.tempTime.text(), durations[0], future=True)
        except Exception:
            self.time = None
            self.tempTime.clear()
            self.parent.parent.showNotificationMessage(text)
            return

        valid = durations[0] <= time <= durations[1] and time not in self.parent.findTemperatureTime(self)

        refTimes = self.parent.findTemperatureTime(self, sameType=True)
        for t in refTimes:
            if t.day == time.day:
                valid = False

        if valid:
            self.time = time
            if time.hour == 0:
                if time == durations[1]:
                    time -= datetime.timedelta(hours=1)
                    timeText = '{}24'.format(str(time.day).zfill(2))
                else:
                    timeText = '{}{}'.format(str(time.day).zfill(2), str(time.hour).zfill(2))

                self.tempTime.setText(timeText)
        else:
            self.time = None
            self.tempTime.clear()
            self.parent.parent.showNotificationMessage(text)

    def validateTemperature(self):
        if not self.temp.hasAcceptableInput():
            return

        temp = self.temp.text()
        temperature = -int(temp[1:]) if 'M' in temp else int(temp)

        if self.mode == 'max':
            minTemperature = self.parent.findTemperature(self)
            if minTemperature and temperature <= minTemperature:
                self.temperature = None
                self.temp.clear()
                self.parent.parent.showNotificationMessage(QCoreApplication.translate('Editor', 'The maximum temperature needs to be greater than the minimum temperature'))
            else:
                self.temperature = temperature

        if self.mode == 'min':
            maxTemperature = self.parent.findTemperature(self)
            if maxTemperature and maxTemperature <= temperature:
                self.temperature = None
                self.temp.clear()
                self.parent.parent.showNotificationMessage(QCoreApplication.translate('Editor', 'The minimum temperature needs to be less than the maximum temperature'))
            else:
                self.temperature = temperature

    def switchMode(self):
        self.mode = 'min' if self.mode == 'max' else 'max'
        self.setLabel()
        self.validateTemperature()
        self.validateTemperatureTime()

    def hasAcceptableInput(self):
        return self.temp.hasAcceptableInput() and self.tempTime.hasAcceptableInput()

    def text(self):
        sign = 'TX' if self.mode == 'max' else 'TN'
        text = '{}{}/{}Z'.format(sign, self.temp.text(), self.tempTime.text())
        return text

    def widgets(self):
        if self.canSwitch:
            return [self.switchButton, self.temp, self.tempTime]
        
        return [self.temp, self.tempTime]

    def clear(self):
        self.temp.clear()
        self.tempTime.clear()
        self.time = None
        self.temperature = None


class TafPrimarySegment(BaseSegment, Ui_taf_primary.Ui_Editor):

    def __init__(self, name='PRIMARY', parent=None):
        super(TafPrimarySegment, self).__init__(name, parent)
        self.setupUi(self)

        self.setValidator()
        self.period.setEnabled(False)
        self.sequence.setEnabled(False)

        self.tmax = TemperatureGroup(mode='max', parent=self)
        self.tmin = TemperatureGroup(mode='min', parent=self)
        self.temperatureLayout.addWidget(self.tmax)
        self.temperatureLayout.addWidget(self.tmin)
        self.temperatures = [self.tmax, self.tmin]

        if context.taf.spec == 'ft30':
            self.temp = TemperatureGroup(canSwitch=True, parent=self)
            self.temperatureLayout.addWidget(self.temp)
            self.temperatures.append(self.temp)
            self.becmg3Checkbox.setStyleSheet('QCheckBox {margin-top: 4px;}')
            self.tempo3Checkbox.setStyleSheet('QCheckBox {margin-top: 4px;}')

        self.prevButton.setIcon(QIcon(':/back.png'))
        self.resetButton.setIcon(QIcon(':/reset.png'))

        self.offset = 0

        self.bindSignal()
        self.initMessageSpec()
        self.setOrder()

    def setOrder(self):
        orders = [self.nsc]
        for t in self.temperatures:
            orders += t.widgets()

        for p, n in zip(orders, orders[1:]):
            self.setTabOrder(p, n)

    def setValidator(self):
        super(TafPrimarySegment, self).setValidator()

        date = QRegExpValidator(QRegExp(self.rules.date))
        self.date.setValidator(date)

    def bindSignal(self):
        super(TafPrimarySegment, self).bindSignal()

        self.normal.clicked.connect(self.setMessageType)
        self.cor.clicked.connect(self.setMessageType)
        self.amd.clicked.connect(self.setMessageType)
        self.cnl.clicked.connect(self.setMessageType)
        self.prevButton.clicked.connect(lambda: self.setCurrentPeriod('prev'))
        self.resetButton.clicked.connect(lambda: self.setCurrentPeriod('reset'))

        self.sequence.textEdited.connect(lambda: self.upperText(self.sequence))

        self.date.textEdited.connect(lambda: self.coloredText(self.date))
        self.sequence.textEdited.connect(lambda: self.coloredText(self.sequence))

        self.timer = QTimer()
        self.timer.timeout.connect(self.setDate)
        self.timer.start(1 * 1000)

    def validate(self):
        super(TafPrimarySegment, self).validate()
        for t in self.temperatures:
            t.validateTemperatureTime()
            t.validateTemperature()

    def initMessageSpec(self):
        if 'ft' in context.taf.spec:
            self.tempo3Checkbox.show()
        else:
            self.tempo3Checkbox.hide()
            self.tempo3Checkbox.setChecked(False)

    def setMessageType(self):
        if not self.date.hasAcceptableInput():
            return

        self.taf = CurrentTaf(context.taf.spec, time=datetime.datetime.utcnow(), offset=self.offset)
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

            if self.amd.isChecked() or self.cnl.isChecked():
                order = self.amendNumber('AMD')
                self.sequence.setValidator(aaa)

            self.sequence.setEnabled(True)
            if not self.sequence.hasAcceptableInput():
                self.sequence.setText(order)

    def setNormalPeriod(self, taf, strict=False):
        check = CheckTaf(taf)
        period = taf.period(strict=strict)

        if period and check.local(period) or not self.date.hasAcceptableInput():
            self.period.clear()
            self.durations = None
        else:
            self.period.setText(period)
            self.durations = taf.durations()

    def setAmendPeriod(self, taf):
        self.amdPeriod = taf.period(strict=False)
        self.period.setText(self.amdPeriod)
        self.durations = taf.durations()

    def setCurrentPeriod(self, action):
        if action == 'reset':
            self.offset = 0
            self.setMessageType()
            self.resetButton.setEnabled(False)
            self.prevButton.setEnabled(True)

        if action == 'prev':
            title = QCoreApplication.translate('Editor', 'Tips')
            text = QCoreApplication.translate('Editor', 'Do you want to change the message valid period to previous?')
            ret = QMessageBox.question(self, title, text)
            if ret == QMessageBox.Yes:
                self.offset -= 1
                self.setMessageType()
                self.resetButton.setEnabled(True)
                self.prevButton.setEnabled(True)

                if self.offset < -1:
                    self.prevButton.setEnabled(False)

    def amendNumber(self, sort):
        expired = datetime.datetime.utcnow() - datetime.timedelta(hours=24)
        query = db.query(Taf).filter(Taf.rpt.contains(self.amdPeriod), Taf.sent > expired)
        if sort == 'COR':
            items = query.filter(Taf.rpt.contains('COR')).all()
            order = chr(ord('A') + len(items))
            return 'CC' + order
        elif sort == 'AMD':
            items = query.filter(Taf.rpt.contains('AMD')).all()
            order = chr(ord('A') + len(items))
            return 'AA' + order

    def findTemperature(self, oneself):
        temps = [t.temperature for t in self.temperatures if t.temperature is not None and t is not oneself]
        if temps:
            if oneself.mode == 'max':
                return min(temps)
            else:
                return max(temps)
        else:
            return None

    def findTemperatureTime(self, oneself, sameType=False):
        times = []
        for t in self.temperatures:
            condition = oneself.mode == t.mode if sameType else True
            if t.time is not None and t is not oneself and condition:
                times.append(t.time)

        return times

    def sortedTemperatures(self):
        temperatures = [t for t in self.temperatures if t.hasAcceptableInput()]
        priority = lambda x: 0 if x == 'max' else 1
        temperatures = sorted(temperatures, key=lambda e: (priority(e.mode), e.time))
        return temperatures

    def checkComplete(self):
        self.complete = False
        tempRequired = [t.hasAcceptableInput() for t in self.temperatures]
        mustRequired = [
            self.date.hasAcceptableInput(),
            self.period.text(),
            self.wind.hasAcceptableInput(),
        ] + tempRequired
        oneRequired = [
            self.nsc.isChecked(),
            self.cloud1.hasAcceptableInput(),
            self.cloud2.hasAcceptableInput(),
            self.cloud3.hasAcceptableInput(),
            self.cb.hasAcceptableInput()
        ]

        if all(mustRequired):
            if self.cavok.isChecked():
                self.complete = True
            elif self.vis.hasAcceptableInput() and any(oneRequired):
                self.complete = True

        if self.cor.isChecked() and not self.sequence.hasAcceptableInput():
            self.complete = False

        if self.amd.isChecked() and not self.sequence.hasAcceptableInput():
            self.complete = False

        if self.cnl.isChecked():
            mustRequired = [
                self.date.hasAcceptableInput(),
                self.period.text(),
                self.sequence.hasAcceptableInput(),
            ]
            if all(mustRequired):
                self.complete = True

        self.completeSignal.emit(self.complete)

    def message(self):
        super(TafPrimarySegment, self).message()
        amd = 'AMD' if self.amd.isChecked() or self.cnl.isChecked() else ''
        cor = 'COR' if self.cor.isChecked() else ''
        icao = conf.value('Message/ICAO')
        timez = self.date.text() + 'Z'
        period = self.period.text()
        temperatures = [t.text() for t in self.sortedTemperatures()]

        if self.cnl.isChecked():
            messages = ['TAF', amd, icao, timez, period, 'CNL']
        else:
            messages = ['TAF', amd, cor, icao, timez, period, self.text] + temperatures

        self.text = ' '.join(filter(None, messages))
        return self.text

    def sign(self):
        area = conf.value('Message/Area') or ''
        icao = conf.value('Message/ICAO')
        time = self.date.text()
        tt = context.taf.spec[:2].upper()
        sequence = self.sequence.text() if not self.normal.isChecked() else ''
        messages = [tt + area, icao, time, sequence]
        return ' '.join(filter(None, messages))

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

    def clear(self):
        super(TafPrimarySegment, self).clear()

        self.fmCheckbox.setChecked(False)
        self.becmg1Checkbox.setChecked(False)
        self.becmg2Checkbox.setChecked(False)
        self.becmg3Checkbox.setChecked(False)
        self.tempo1Checkbox.setChecked(False)
        self.tempo2Checkbox.setChecked(False)

        self.cavok.setChecked(False)

        for t in self.temperatures:
            t.clear()


class TafGroupSegment(BaseSegment, Ui_taf_group.Ui_Editor):

    def __init__(self, name='TEMPO', parent=None):
        super(TafGroupSegment, self).__init__(name, parent)
        self.setupUi(self)
        self.name.setText(name)
        self.setValidator()
        self.bindSignal()

    def bindSignal(self):
        super(TafGroupSegment, self).bindSignal()
        self.period.textEdited.connect(self.fillPeriod)
        self.period.textChanged.connect(self.updateDurations)
        self.period.editingFinished.connect(self.validatePeriod)
        self.period.editingFinished.connect(self.validateGroupsPeriod)
        self.period.textChanged.connect(lambda: self.coloredText(self.period))

    def setValidator(self):
        super(TafGroupSegment, self).setValidator()
        period = QRegExpValidator(QRegExp(self.rules.period))
        self.period.setValidator(period)

    def setPeriodPlaceholder(self):
        if self.parent.primary.durations is None:
            self.period.setPlaceholderText('')
            return

        time = self.parent.primary.durations[0]
        self.period.setPlaceholderText('{:02d}'.format(time.day))

    def fillPeriod(self):
        autoComletionGroupTime = boolean(conf.value('General/AutoComletionGroupTime'))
        if autoComletionGroupTime:
            self.autoFillPeriod()
        else:
            self.autoFillSlash()

    def autoFillPeriod(self):
        if self.parent.primary.durations is None or not self.parent.primary.period.text():
            return

        text = self.period.text()
        if len(text) > len(self.periodText):
            if len(text) == 4:
                durations = self.parent.primary.durations
                try:
                    start = parseDayHour(text, durations[0], future=True)
                except Exception:
                    return

                if durations[1] <= start:
                    return

                if self.identifier.startswith('TEMPO'):
                    delta = datetime.timedelta(hours=self.span())
                    end = start + delta
                    if durations[1] <= end:
                        text = '{:02d}{:02d}/{}'.format(start.day, start.hour, self.parent.primary.period.text()[5:])
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
            if 'ft' in context.taf.spec:
                duration = 6
            else:
                duration = 4
        else:
            duration = 2

        return duration

    def updateDurations(self):
        if self.period.hasAcceptableInput() and self.parent.primary.period.text():
            period = self.period.text()
            basetime = self.parent.primary.durations[0]
            self.durations = start, end = parsePeriod(period, basetime)

            if end.hour == 0 and not period.endswith('24'):
                end -= datetime.timedelta(minutes=1)
                text = '{:02d}{:02d}/{:02d}24'.format(start.day, start.hour, end.day)
                self.period.setText(text)
        else:
            self.durations = None

    def validate(self):
        super(TafGroupSegment, self).validate()
        self.validatePeriod()
        self.validateGroupsPeriod()

    def validatePeriod(self):
        if self.durations is None:
            return

        start, end = self.durations

        if end - start > datetime.timedelta(hours=self.span()):
            self.period.clear()
            self.parent.showNotificationMessage(QCoreApplication.translate('Editor', 'Change group time more than {} hours').format(self.span()))
            return

        if self.parent.primary.durations is None:
            return

        durations = self.parent.primary.durations
        
        if start < durations[0] or durations[1] < start:
            self.period.clear()
            self.parent.showNotificationMessage(QCoreApplication.translate('Editor', 'Start time of change group is not corret'))
            return

        if end < durations[0] or durations[1] < end or (self.identifier.startswith('BECMG') and end == durations[1]):
            self.period.clear()
            self.parent.showNotificationMessage(QCoreApplication.translate('Editor', 'End time of change group is not corret'))
            return

    def validateGroupsPeriod(self):

        def isPeriodOverlay(period, periods):
            for p in periods:
                if isOverlap(period, p):
                    return True

        groups = self.parent.tempos if self.identifier.startswith('TEMPO') else self.parent.becmgs
        periods = [g.durations for g in groups if g.isVisible() and g.durations and self != g]
        if isPeriodOverlay(self.durations, periods):
            self.period.clear()
            self.parent.showNotificationMessage(QCoreApplication.translate('Editor', 'Change group time is overlap'))

    def checkComplete(self):
        self.complete = False
        oneRequired = (
            self.nsc.isChecked(),
            self.cavok.isChecked(),
            self.wind.hasAcceptableInput(),
            self.vis.hasAcceptableInput(),
            self.weather.lineEdit().hasAcceptableInput() and self.weather.currentText(),
            self.weatherWithIntensity.lineEdit().hasAcceptableInput() and self.weatherWithIntensity.currentText(),
            self.cloud1.hasAcceptableInput(),
            self.cloud2.hasAcceptableInput(),
            self.cloud3.hasAcceptableInput(),
            self.cb.hasAcceptableInput()
        )

        if self.period.hasAcceptableInput() and any(oneRequired):
            self.complete = True

        self.completeSignal.emit(self.complete)

    def showEvent(self, event):
        self.setPeriodPlaceholder()

    def clear(self):
        super(TafGroupSegment, self).clear()
        self.period.clear()
        self.period.setPlaceholderText('')
        self.periodText = ''


class TafFmSegment(TafGroupSegment):

    def __init__(self, name='FM', parent=None):
        super(TafFmSegment, self).__init__(name, parent)

    def bindSignal(self):
        super(TafFmSegment, self).bindSignal()
        self.period.textEdited.disconnect(self.fillPeriod)

    def setValidator(self):
        super(TafFmSegment, self).setValidator()
        period = QRegExpValidator(QRegExp(self.rules.fmPeriod))
        self.period.setValidator(period)

    def updateDurations(self):
        if self.period.hasAcceptableInput() and self.parent.primary.period.text():
            period = self.period.text()
            basetime = self.parent.primary.durations[0]
            time = parseTime(period, basetime)
            self.durations = (time, time)
        else:
            self.durations = None

    def validatePeriod(self):
        if self.durations is None or self.parent.primary.durations is None:
            return

        durations = self.parent.primary.durations
        start, end = self.durations
        if start < durations[0] or durations[1] <= start:
            self.period.clear()
            self.parent.showNotificationMessage(QCoreApplication.translate('Editor', 'Time of change group is not corret'))
            return

    def validateGroupsPeriod(self):

        def inPeriod(time, periods):
            for p in periods:
                if p[0] <= time <= p[1]:
                    return True

        if self.durations is None:
            return

        groups = self.parent.becmgs
        periods = [g.durations for g in groups if g.isVisible() and g.durations and self != g]
        if inPeriod(self.durations[0], periods):
            self.period.clear()
            self.parent.showNotificationMessage(QCoreApplication.translate('Editor', 'Change group time is overlap'))

    def checkComplete(self):
        self.complete = False
        hasWeather = self.weather.lineEdit().hasAcceptableInput() and self.weather.currentText() \
            or self.weatherWithIntensity.lineEdit().hasAcceptableInput() and self.weatherWithIntensity.currentText()
        mustRequired = [
            self.period.hasAcceptableInput(),
            self.wind.hasAcceptableInput()
        ]
        oneRequired = [
            self.nsc.isChecked(),
            self.cloud1.hasAcceptableInput(),
            self.cloud2.hasAcceptableInput(),
            self.cloud3.hasAcceptableInput(),
            self.cb.hasAcceptableInput()
        ]

        if all(mustRequired):
            if self.cavok.isChecked():
                self.complete = True
            elif self.vis.hasAcceptableInput() and hasWeather and any(oneRequired):
                self.complete = True

        self.completeSignal.emit(self.complete)

    def message(self):
        super(TafFmSegment, self).message()
        period = 'FM{}'.format(self.period.text())
        messages = [period, self.text]
        self.text = ' '.join(messages)
        return self.text

    def clear(self):
        super(TafFmSegment, self).clear()

        self.cavok.setChecked(False)
        self.nsc.setChecked(False)


class TafBecmgSegment(TafGroupSegment):

    def __init__(self, name='BECMG', parent=None):
        super(TafBecmgSegment, self).__init__(name, parent)

    def message(self):
        super(TafBecmgSegment, self).message()
        period = self.period.text()
        messages = ['BECMG', period, self.text]
        self.text = ' '.join(messages)
        return self.text

    def clear(self):
        super(TafBecmgSegment, self).clear()

        self.cavok.setChecked(False)
        self.nsc.setChecked(False)


class TafTempoSegment(TafGroupSegment):

    def __init__(self, name='TEMPO', parent=None):
        super(TafTempoSegment, self).__init__(name, parent)
        self.cavok.hide()
        self.nsc.hide()

    def message(self):
        super(TafTempoSegment, self).message()
        period = self.period.text()
        messages = ['TEMPO', period, self.text]
        self.text = ' '.join(messages)
        return self.text


class TrendSegment(BaseSegment, Ui_trend.Ui_Editor):

    def __init__(self, name='TREND', parent=None):
        super(TrendSegment, self).__init__(name, parent)
        self.setupUi(self)
        self.setValidator()
        self.bindSignal()

    def bindSignal(self):
        super(TrendSegment, self).bindSignal()
        self.nosig.toggled.connect(self.setNosig)
        self.at.clicked.connect(self.setAt)
        self.fm.clicked.connect(self.setFmTl)
        self.tl.clicked.connect(self.setFmTl)

        self.becmg.clicked.connect(self.updateAtStatus)
        self.tempo.clicked.connect(self.updateAtStatus)

        self.period.textEdited.connect(self.autoFillPeriodSlash)
        self.period.editingFinished.connect(self.validatePeriod)

        self.period.textChanged.connect(lambda: self.coloredText(self.period))

    def autoFillPeriodSlash(self):
        if self.fm.isChecked() and self.tl.isChecked():   
            self.autoFillSlash()

    def setValidator(self):
        super(TrendSegment, self).setValidator()
        self.setPeriodValidator()

    def setPeriodValidator(self):
        if self.fm.isChecked() and self.tl.isChecked():
            period = QRegExpValidator(QRegExp(self.rules.trendFmTlPeriod))
        else:
            period = QRegExpValidator(QRegExp(self.rules.trendPeriod))

        self.period.setValidator(period)

    def setPeriodPlaceholder(self):
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
            self.setPeriodPlaceholder()
        else:
            self.period.setEnabled(False)
            self.period.setPlaceholderText('')

        self.period.clear()
        self.setPeriodValidator()

    def setFmTl(self):
        checked = [self.fm.isChecked(), self.tl.isChecked()]
        if any(checked):
            self.at.setChecked(False)
            self.period.setEnabled(True)
            self.setPeriodPlaceholder()
        else:
            self.period.setEnabled(False)
            self.period.setPlaceholderText('')

        self.period.clear()
        self.setPeriodValidator()

    def formatPeriod(self):
        if (self.at.isChecked() or self.fm.isChecked() and not self.tl.isChecked()) and self.period.text() == '2400':
            self.period.setText('0000')

        if self.tl.isChecked() and not self.fm.isChecked() and self.period.text() == '0000':
            self.period.setText('2400')

    def validatePeriod(self):
        self.formatPeriod()
        period = self.period.text()
        utc = datetime.datetime.utcnow()
        delta = datetime.timedelta(hours=2, minutes=30)
        periods = [parseTime(text) for text in period.split('/')]
        errorInfo = QCoreApplication.translate('Editor', 'Trend valid time is not corret')

        if len(periods) == 2:
            if periods[1] <= periods[0]:
                periods[1] = datetime.timedelta(days=1)

            if periods[1] - periods[0] > datetime.timedelta(hours=2):
                self.period.clear()
                self.parent.showNotificationMessage(errorInfo)

        for time in periods:
            if (time - delta) > utc:
                self.period.clear()
                self.parent.showNotificationMessage(errorInfo)

    def updateAtStatus(self):
        if self.tempo.isChecked():
            self.at.setEnabled(False)
            self.at.setChecked(False)
        else:
            self.at.setEnabled(True)

    def checkComplete(self):
        self.complete = False
        oneRequired = (
            self.nsc.isChecked(),
            self.cavok.isChecked(),
            self.wind.hasAcceptableInput(),
            self.vis.hasAcceptableInput(),
            self.weather.lineEdit().hasAcceptableInput() and self.weather.currentText() ,
            self.weatherWithIntensity.lineEdit().hasAcceptableInput() and self.weatherWithIntensity.currentText(),
            self.cloud1.hasAcceptableInput(),
            self.cloud2.hasAcceptableInput(),
            self.cloud3.hasAcceptableInput(),
            self.cb.hasAcceptableInput()
        )

        prefixChecked = (
            self.at.isChecked(),
            self.fm.isChecked(),
            self.tl.isChecked()
        )

        if self.nosig.isChecked():
            self.complete = True

        if any(oneRequired):
            if any(prefixChecked):
                if self.period.hasAcceptableInput():
                    self.complete = True
            else:
                self.complete = True

        self.completeSignal.emit(self.complete)

    def message(self):
        super(TrendSegment, self).message()

        if self.nosig.isChecked():
            self.text = 'NOSIG'
        else:
            messages = []

            if self.becmg.isChecked():
                trendType = 'BECMG'
            if self.tempo.isChecked():
                trendType = 'TEMPO'

            messages.append(trendType)

            if self.at.isChecked() or self.fm.isChecked() or self.tl.isChecked():
                if self.fm.isChecked() and self.tl.isChecked():
                    periodText = 'FM{} TL{}'.format(*self.period.text().split('/'))
                else:
                    if self.at.isChecked():
                        trendPrefix = 'AT'
                    if self.fm.isChecked():
                        trendPrefix = 'FM'
                    if self.tl.isChecked():
                        trendPrefix = 'TL'

                    periodText = trendPrefix + self.period.text()

                messages.append(periodText)

            messages.append(self.text)
            self.text = ' '.join(messages)

        return self.text

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

