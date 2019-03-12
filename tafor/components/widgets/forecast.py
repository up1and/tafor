import json
import datetime

from PyQt5.QtGui import QIcon, QRegExpValidator
from PyQt5.QtCore import Qt, QRegExp, QCoreApplication, QTimer, pyqtSignal
from PyQt5.QtWidgets import QWidget, QLineEdit, QComboBox, QRadioButton, QCheckBox, QMessageBox

from tafor import conf
from tafor.utils import Pattern, CurrentTaf, CheckTaf, boolean
from tafor.utils.convert import parseDayHour, parsePeriod, parseDateTime, isOverlap
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
        self.identifier = name
        self.durations = None

    def bindSignal(self):
        if hasattr(self, 'cavok'):
            self.cavok.toggled.connect(self.setCavok)
            self.nsc.toggled.connect(self.setNsc)

        if self.identifier not in ['PRIMARY']:
            self.period.textChanged.connect(lambda: self.coloredText(self.period))

        self.gust.editingFinished.connect(self.validateGust)
        self.cloud1.textEdited.connect(self.setVv)
        self.cloud1.editingFinished.connect(lambda: self.validateCloud(self.cloud1))
        self.cloud2.editingFinished.connect(lambda: self.validateCloud(self.cloud2))
        self.cloud3.editingFinished.connect(lambda: self.validateCloud(self.cloud3))

        self.wind.textEdited.connect(lambda: self.upperText(self.wind))
        self.gust.textEdited.connect(lambda: self.upperText(self.gust))
        self.cloud1.textEdited.connect(lambda: self.upperText(self.cloud1))
        self.cloud2.textEdited.connect(lambda: self.upperText(self.cloud2))
        self.cloud3.textEdited.connect(lambda: self.upperText(self.cloud3))
        self.cb.textEdited.connect(lambda: self.upperText(self.cb))

        self.wind.textEdited.connect(lambda: self.coloredText(self.wind))
        self.gust.textEdited.connect(lambda: self.coloredText(self.gust))
        self.vis.textEdited.connect(lambda: self.coloredText(self.vis))
        self.cloud1.textEdited.connect(lambda: self.coloredText(self.cloud1))
        self.cloud2.textEdited.connect(lambda: self.coloredText(self.cloud2))
        self.cloud3.textEdited.connect(lambda: self.coloredText(self.cloud3))
        self.cb.textEdited.connect(lambda: self.coloredText(self.cb))

        self.defaultSignal()

    def setPeriod(self):
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
        self.weather.addItems(weathers)

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

    def validateGust(self):
        if not self.gust.hasAcceptableInput():
            return

        wind = self.wind.text()
        windSpeed = self.wind.text()[-2:] if self.wind.hasAcceptableInput() else 0
        gust = self.gust.text()

        if gust == 'P49':
            return

        if windSpeed == 0 or int(gust) - int(windSpeed) < 5 or wind == '00000':
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
        self.validateCloud(self.cloud3)
        self.validateCloud(self.cloud2)
        self.validateCloud(self.cloud1)

    def message(self):
        wind = self.wind.text() if self.wind.hasAcceptableInput() else None
        gust = self.gust.text() if self.gust.hasAcceptableInput() else None

        if wind:
            winds = ''.join([wind, 'G', gust, 'MPS']) if gust else ''.join([wind, 'MPS'])
        else:
            winds = None

        vis = self.vis.text() if self.vis.hasAcceptableInput() else None
        weather = self.weather.currentText()
        weatherWithIntensity = self.weatherWithIntensity.currentText()
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


class TafPrimarySegment(BaseSegment, Ui_taf_primary.Ui_Editor):

    def __init__(self, name='PRIMARY', parent=None):
        super(TafPrimarySegment, self).__init__(name, parent)
        self.setupUi(self)

        self.setValidator()
        self.period.setEnabled(False)
        self.ccc.setEnabled(False)
        self.aaa.setEnabled(False)
        self.aaaCnl.setEnabled(False)
        self.tempSwitchButton.setIcon(QIcon(':/switch.png'))

        self.bindSignal()
        self.initMessageSpec()

    def setValidator(self):
        super(TafPrimarySegment, self).setValidator()

        date = QRegExpValidator(QRegExp(self.rules.date))
        self.date.setValidator(date)

        temp = QRegExpValidator(QRegExp(self.rules.temp, Qt.CaseInsensitive))
        self.tmax.setValidator(temp)
        self.tmin.setValidator(temp)

        tempHours = QRegExpValidator(QRegExp(self.rules.hours))
        self.tmaxTime.setValidator(tempHours)
        self.tminTime.setValidator(tempHours)

        aaa = QRegExpValidator(QRegExp(self.rules.aaa, Qt.CaseInsensitive))
        self.aaa.setValidator(aaa)
        self.aaaCnl.setValidator(aaa)

        ccc = QRegExpValidator(QRegExp(self.rules.ccc, Qt.CaseInsensitive))
        self.ccc.setValidator(ccc)

    def bindSignal(self):
        super(TafPrimarySegment, self).bindSignal()

        self.normal.clicked.connect(self.setMessageType)
        self.cor.clicked.connect(self.setMessageType)
        self.amd.clicked.connect(self.setMessageType)
        self.cnl.clicked.connect(self.setMessageType)
        self.prev.clicked.connect(self.setPreviousPeriod)

        self.tmaxTime.editingFinished.connect(lambda :self.validateTemperatureHour(self.tmaxTime))
        self.tminTime.editingFinished.connect(lambda :self.validateTemperatureHour(self.tminTime))
        self.tempTime.editingFinished.connect(lambda :self.validateTemperatureHour(self.tempTime))

        self.tmax.editingFinished.connect(self.validateTemperature)
        self.tmin.editingFinished.connect(self.validateTemperature)

        self.tmax.textEdited.connect(lambda: self.upperText(self.tmax))
        self.tmin.textEdited.connect(lambda: self.upperText(self.tmin))
        self.aaa.textEdited.connect(lambda: self.upperText(self.aaa))
        self.ccc.textEdited.connect(lambda: self.upperText(self.ccc))
        self.aaaCnl.textEdited.connect(lambda: self.upperText(self.aaaCnl))

        self.date.textEdited.connect(lambda: self.coloredText(self.date))
        self.tmax.textEdited.connect(lambda: self.coloredText(self.tmax))
        self.tmin.textEdited.connect(lambda: self.coloredText(self.tmin))
        self.tmaxTime.textEdited.connect(lambda: self.coloredText(self.tmaxTime))
        self.tminTime.textEdited.connect(lambda: self.coloredText(self.tminTime))
        self.aaa.textEdited.connect(lambda: self.coloredText(self.aaa))
        self.ccc.textEdited.connect(lambda: self.coloredText(self.ccc))
        self.aaaCnl.textEdited.connect(lambda: self.coloredText(self.aaaCnl))

        self.timer = QTimer()
        self.timer.timeout.connect(self.setDate)
        self.timer.start(1 * 1000)

    def initMessageSpec(self):
        international = boolean(conf.value('General/InternationalAirport'))
        if international:
            self.tt = 'FT'
            self.tempo3Checkbox.show()
        else:
            self.tt = 'FC'
            self.tempo3Checkbox.hide()
            self.tempo3Checkbox.setChecked(False)

    def setMessageType(self):
        if self.date.text():
            prev = 1 if self.prev.isChecked() else 0
            self.taf = CurrentTaf(context.taf.spec, time=self.time, prev=prev)
            if self.normal.isChecked():
                self.setNormalPeriod()

                self.ccc.clear()
                self.ccc.setEnabled(False)
                self.aaa.clear()
                self.aaa.setEnabled(False)
                self.aaaCnl.clear()
                self.aaaCnl.setEnabled(False)
            else:
                self.setAmendPeriod()

                if self.cor.isChecked():
                    self.ccc.setEnabled(True)
                    order = self.amendNumber('COR')
                    self.ccc.setText(order)
                else:
                    self.ccc.clear()
                    self.ccc.setEnabled(False)

                if self.amd.isChecked():
                    self.aaa.setEnabled(True)
                    order = self.amendNumber('AMD')
                    self.aaa.setText(order)
                else:
                    self.aaa.clear()
                    self.aaa.setEnabled(False)

                if self.cnl.isChecked():
                    self.aaaCnl.setEnabled(True)
                    order = self.amendNumber('AMD')
                    self.aaaCnl.setText(order)
                else:
                    self.aaaCnl.clear()
                    self.aaaCnl.setEnabled(False)

            self.durations = self.taf.durations()

    def setNormalPeriod(self, isTask=False):
        check = CheckTaf(self.taf)
        period = self.taf.period() if isTask else self.taf.period(strict=False)

        if period and check.local(period) or not self.date.hasAcceptableInput():
            self.period.clear()
        else:
            self.period.setText(period)

    def setAmendPeriod(self):
        self.amdPeriod = self.taf.period(strict=False)
        self.period.setText(self.amdPeriod)

    def setPreviousPeriod(self, checked):
        if checked:
            title = QCoreApplication.translate('Editor', 'Tips')
            text = QCoreApplication.translate('Editor', 'Do you want to change the message valid period to previous?')
            ret = QMessageBox.question(self, title, text)
            if ret == QMessageBox.Yes:
                self.setMessageType()
            else:
                self.prev.setChecked(False)
        else:
            self.setMessageType()

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

    def validateTemperatureHour(self, line):
        if self.durations is None:
            return

        tempHour = parseDayHour(line.text(), self.time)

        if tempHour < self.durations[0]:
            tempHour += datetime.timedelta(days=1)

        valid = self.durations[0] <= tempHour <= self.durations[1] and self.tmaxTime.text() != self.tminTime.text()

        if not valid:
            line.clear()
            self.parent.showNotificationMessage(QCoreApplication.translate('Editor', 'The time of temperature is not corret'))

    def validateTemperature(self):
        tmax = self.tmax.text()
        tmin = self.tmin.text()
        if tmax and tmin:
            tmax = -int(tmax[1:]) if 'M' in tmax else int(tmax)
            tmin = -int(tmin[1:]) if 'M' in tmin else int(tmin)
            if tmax <= tmin:
                self.tmin.clear()
                self.parent.showNotificationMessage(QCoreApplication.translate('Editor', 'The maximum temperature needs to be greater than the minimum temperature'))

    def checkComplete(self):
        self.complete = False
        mustRequired = (
            self.date.hasAcceptableInput(),
            self.period.text(),
            self.wind.hasAcceptableInput(),
            self.tmax.hasAcceptableInput(),
            self.tmaxTime.hasAcceptableInput(),
            self.tmin.hasAcceptableInput(),
            self.tminTime.hasAcceptableInput()
        )
        oneRequired = (
            self.nsc.isChecked(),
            self.cloud1.hasAcceptableInput(),
            self.cloud2.hasAcceptableInput(),
            self.cloud3.hasAcceptableInput(),
            self.cb.hasAcceptableInput()
        )

        if all(mustRequired):
            if self.cavok.isChecked():
                self.complete = True
            elif self.vis.hasAcceptableInput() and any(oneRequired):
                self.complete = True

        if self.cor.isChecked() and not self.ccc.hasAcceptableInput():
            self.complete = False

        if self.amd.isChecked() and not self.aaa.hasAcceptableInput():
            self.complete = False

        if self.cnl.isChecked():
            mustRequired = (
                self.date.hasAcceptableInput(),
                self.period.text(),
                self.aaaCnl.hasAcceptableInput(),
            )
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
        tmax = ''.join(['TX', self.tmax.text(), '/', self.tmaxTime.text(), 'Z'])
        tmin = ''.join(['TN', self.tmin.text(), '/', self.tminTime.text(), 'Z'])

        if self.cnl.isChecked():
            messages = ['TAF', amd, icao, timez, period, 'CNL']
        else:
            messages = ['TAF', amd, cor, icao, timez, period, self.text, tmax, tmin]

        self.text = ' '.join(filter(None, messages))
        return self.text

    def sign(self):
        area = conf.value('Message/Area') or ''
        icao = conf.value('Message/ICAO')
        time = self.date.text()
        tt = context.taf.spec[:2].upper()
        ccc = self.ccc.text() if self.cor.isChecked() else None
        aaa = self.aaa.text() if self.amd.isChecked() else None
        aaaCnl = self.aaaCnl.text() if self.cnl.isChecked() else None
        messages = [tt + area, icao, time, ccc, aaa, aaaCnl]
        return ' '.join(filter(None, messages))

    def setDate(self):
        self.time = datetime.datetime.utcnow()
        self.date.setText(self.time.strftime('%d%H%M'))

    def showEvent(self, event):
        self.setDate()

    def clear(self):
        super(TafPrimarySegment, self).clear()

        self.becmg1Checkbox.setChecked(False)
        self.becmg2Checkbox.setChecked(False)
        self.becmg3Checkbox.setChecked(False)
        self.tempo1Checkbox.setChecked(False)
        self.tempo2Checkbox.setChecked(False)

        self.cavok.setChecked(False)

        self.tmax.clear()
        self.tmaxTime.clear()
        self.tmin.clear()
        self.tminTime.clear()


class TafGroupSegment(BaseSegment, Ui_taf_group.Ui_Editor):

    def __init__(self, name='TEMPO', parent=None):
        super(TafGroupSegment, self).__init__(name, parent)
        self.setupUi(self)
        self.name.setText(name)
        self.setValidator()
        self.bindSignal()
        self.periodText = ''

    def bindSignal(self):
        super(TafGroupSegment, self).bindSignal()
        self.period.textEdited.connect(self.fillPeriod)
        self.period.textEdited.connect(self.updateDurations)
        self.period.editingFinished.connect(self.validatePeriod)

    def setValidator(self):
        super(TafGroupSegment, self).setValidator()
        period = QRegExpValidator(QRegExp(self.rules.period))
        self.period.setValidator(period)

    def setPeriod(self):
        if not self.parent.primary.period.text():
            return

        time = self.parent.primary.durations[0]
        self.period.setText('{:02d}'.format(time.day))

    def fillPeriod(self):
        text = self.period.text()
        if len(text) > len(self.periodText):
            if len(text) == 4:
                text += '/'

            self.period.setText(text)

        self.periodText = text

    def updateDurations(self):
        if self.period.hasAcceptableInput() and self.parent.primary.period.text():
            period = self.period.text()
            basetime = self.parent.primary.durations[0]
            durations = parsePeriod(period, basetime)
            if durations[0] < basetime:
                durations = list(durations)
                durations[0] += datetime.timedelta(days=1)
                durations[1] += datetime.timedelta(days=1)

            self.durations = durations
        else:
            self.durations = None

    def validatePeriod(self):
        if self.durations is None:
            return

        isTempo = self.identifier.startswith('TEMPO')

        if isTempo and self.taf.spec.tt == 'FC':
            maxTime = 4
        elif isTempo and self.taf.spec.tt == 'FT':
            maxTime = 6
        else:
            maxTime = 2

        primaryDurations = self.parent.primary.durations
        start, end = self.durations
        if start < primaryDurations[0] or primaryDurations[1] < start:
            self.period.clear()
            self.parent.showNotificationMessage(QCoreApplication.translate('Editor', 'Start time of change group is not corret'))
            return

        if end < primaryDurations[0] or primaryDurations[1] < end:
            self.period.clear()
            self.parent.showNotificationMessage(QCoreApplication.translate('Editor', 'End time of change group is not corret'))
            return

        if end - start > datetime.timedelta(hours=maxTime):
            self.period.clear()
            self.parent.showNotificationMessage(QCoreApplication.translate('Editor', 'Change group time more than {} hours').format(maxTime))
            return

    def checkComplete(self):
        self.complete = False
        oneRequired = (
            self.nsc.isChecked(),
            self.cavok.isChecked(),
            self.wind.hasAcceptableInput(),
            self.vis.hasAcceptableInput(),
            self.weather.currentText(),
            self.weatherWithIntensity.currentText(),
            self.cloud1.hasAcceptableInput(),
            self.cloud2.hasAcceptableInput(),
            self.cloud3.hasAcceptableInput(),
            self.cb.hasAcceptableInput()
        )

        if self.period.hasAcceptableInput() and any(oneRequired):
            self.complete = True

        self.completeSignal.emit(self.complete)

    def showEvent(self, event):
        self.setPeriod()

    def hideEvent(self, event):
        self.durations = None
        self.periodText = ''

    def clear(self):
        super(TafGroupSegment, self).clear()
        self.period.clear()


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
        self.at.toggled.connect(self.setAt)
        self.fm.toggled.connect(self.setFm)
        self.tl.toggled.connect(self.setTl)

        self.becmg.clicked.connect(self.updateAtStatus)
        self.tempo.clicked.connect(self.updateAtStatus)

    def setValidator(self):
        super(TrendSegment, self).setValidator()

        # 还未验证输入个数
        period = QRegExpValidator(QRegExp(self.rules.trendPeriod))
        self.period.setValidator(period)

    def setPeriod(self):
        time = datetime.datetime.utcnow() + datetime.timedelta(hours=1)
        self.period.setText('{:02d}'.format(time.hour))

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
            self.setPeriod()
        else:
            self.period.setEnabled(False)
            self.period.clear()

    def setFm(self, checked):
        if checked:
            self.at.setChecked(False)
            self.tl.setChecked(False)
            self.period.setEnabled(True)
            self.setPeriod()
        else:
            self.period.setEnabled(False)
            self.period.clear()

    def setTl(self, checked):
        if checked:
            self.fm.setChecked(False)
            self.at.setChecked(False)
            self.period.setEnabled(True)
            self.setPeriod()
        else:
            self.period.setEnabled(False)
            self.period.clear()

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
            self.weather.currentText(),
            self.weatherWithIntensity.currentText(),
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
                trend_type = 'BECMG'
            if self.tempo.isChecked():
                trend_type = 'TEMPO'

            messages.append(trend_type)

            if any((self.at.isChecked(), self.fm.isChecked(), self.tl.isChecked())):
                if self.at.isChecked():
                    trendPrefix = 'AT'
                if self.fm.isChecked():
                    trendPrefix = 'FM'
                if self.tl.isChecked():
                    trendPrefix = 'TL'

                period = trendPrefix + self.period.text()
                messages.append(period)

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

