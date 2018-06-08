import json
import datetime

from PyQt5.QtGui import QRegExpValidator
from PyQt5.QtCore import Qt, QRegExp, pyqtSignal
from PyQt5.QtWidgets import QWidget, QLineEdit, QComboBox, QRadioButton, QCheckBox

from tafor import conf, logger
from tafor.utils import Pattern
from tafor.components.ui import Ui_taf_primary, Ui_taf_becmg, Ui_taf_tempo, Ui_trend


class SegmentMixin(object):

    def upperText(self, line):
        line.setText(line.text().upper())

    def coloredText(self, line):
        if line.hasAcceptableInput():
            line.setStyleSheet('color: black')
        else:
            line.setStyleSheet('color: grey')

    def register(self):
        for line in self.findChildren(QLineEdit):
            line.textChanged.connect(self.checkComplete)

        for combox in self.findChildren(QComboBox):
            combox.currentTextChanged.connect(self.checkComplete)

        for button in self.findChildren(QRadioButton):
            button.clicked.connect(self.checkComplete)

        for checkbox in self.findChildren(QCheckBox):
            checkbox.clicked.connect(self.checkComplete)

    def clear(self):
        # Bug
        for line in self.findChildren(QLineEdit):
            line.clear()

        for combox in self.findChildren(QComboBox):
            combox.setCurrentIndex(0)

        for checkbox in self.findChildren(QCheckBox):
            checkbox.setChecked(False)


class BaseSegment(QWidget, SegmentMixin):
    completeSignal = pyqtSignal(bool)

    def __init__(self, name=None):
        super(BaseSegment, self).__init__()
        self.rules = Pattern()
        self.complete = False
        self.id = name
        self.periods = None

    def bindSignal(self):
        if hasattr(self, 'cavok'):
            self.cavok.toggled.connect(self.setCavok)
            self.nsc.toggled.connect(self.setNsc)

        if hasattr(self, 'prob30'):
            self.prob30.toggled.connect(self.setProb30)
            self.prob40.toggled.connect(self.setProb40)

        if hasattr(self, 'interval'):
            self.interval.textEdited.connect(lambda: self.coloredText(self.interval))
            self.interval.textChanged.connect(self.clearInterval)

        self.gust.editingFinished.connect(self.validateGust)
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

        self.register()

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

    def setValidator(self):
        wind = QRegExpValidator(QRegExp(self.rules.wind, Qt.CaseInsensitive))
        self.wind.setValidator(wind)

        gust = QRegExpValidator(QRegExp(self.rules.gust, Qt.CaseInsensitive))
        self.gust.setValidator(gust)

        vis = QRegExpValidator(QRegExp(self.rules.vis))
        self.vis.setValidator(vis)

        cloud = QRegExpValidator(QRegExp(self.rules.cloud, Qt.CaseInsensitive))
        self.cloud1.setValidator(cloud)
        self.cloud2.setValidator(cloud)
        self.cloud3.setValidator(cloud)
        self.cb.setValidator(cloud)

        weather = conf.value('Message/Weather')
        weathers = [''] + json.loads(weather) if weather else ['']
        self.weather.addItems(weathers)

        weatherWithIntensity = conf.value('Message/WeatherWithIntensity')
        intensityWeathers = ['']
        if weatherWithIntensity:
            for w in json.loads(weatherWithIntensity):
                intensityWeathers.extend(['-' + w, w, '+' + w])
        self.weatherWithIntensity.addItems(intensityWeathers)

    def validateGust(self):
        if not self.gust.hasAcceptableInput():
            return

        windSpeed = self.wind.text()[-2:] if self.wind.hasAcceptableInput() else 0
        gust = self.gust.text()

        if gust == 'P49':
            return

        if windSpeed == 0 or int(gust) - int(windSpeed) < 5:
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
        self.msg = ' '.join(filter(None, messages))
        # logger.debug(self.msg)

    def checkComplete(self):
        raise NotImplementedError

    def clearInterval(self):
        if len(self.interval.text()) < 4:
            self.periods = None

    def hideEvent(self, event):
        self.periods = None

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
        self.periods = None


class TafPrimarySegment(BaseSegment, Ui_taf_primary.Ui_Editor):

    def __init__(self, name='PRIMARY'):
        super(TafPrimarySegment, self).__init__(name)
        self.setupUi(self)

        self.setValidator()
        self.period.setEnabled(False)
        self.ccc.setEnabled(False)
        self.aaa.setEnabled(False)
        self.aaaCnl.setEnabled(False)

        self.bindSignal()

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
            messages = ['TAF', amd, cor, icao, timez, period, self.msg, tmax, tmin]

        self.msg = ' '.join(filter(None, messages))
        return self.msg

    def sign(self):
        area = conf.value('Message/Area') or ''
        icao = conf.value('Message/ICAO')
        time = self.date.text()
        tt = ''
        if self.fc.isChecked():
            tt = 'FC'
        elif self.ft.isChecked():
            tt = 'FT'

        ccc = self.ccc.text() if self.cor.isChecked() else None
        aaa = self.aaa.text() if self.amd.isChecked() else None
        aaaCnl = self.aaaCnl.text() if self.cnl.isChecked() else None
        messages = [tt + area, icao, time, ccc, aaa, aaaCnl]
        return ' '.join(filter(None, messages))

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


class TafBecmgSegment(BaseSegment, Ui_taf_becmg.Ui_Editor):

    def __init__(self, name='BECMG'):
        super(TafBecmgSegment, self).__init__(name)
        self.setupUi(self)
        self.name.setText(name)

        self.setValidator()
        self.bindSignal()

    def setValidator(self):
        super(TafBecmgSegment, self).setValidator()

        interval = QRegExpValidator(QRegExp(self.rules.interval))
        self.interval.setValidator(interval)

    def message(self):
        super(TafBecmgSegment, self).message()
        interval = self.interval.text()
        messages = ['BECMG', interval, self.msg]
        self.msg = ' '.join(messages)
        # logger.debug(self.msg)
        return self.msg

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

        if self.interval.hasAcceptableInput() and any(oneRequired):
            self.complete = True

        self.completeSignal.emit(self.complete)

    def clear(self):
        super(TafBecmgSegment, self).clear()

        self.interval.clear()

        self.cavok.setChecked(False)
        self.nsc.setChecked(False)


class TafTempoSegment(BaseSegment, Ui_taf_tempo.Ui_Editor):

    def __init__(self, name='TEMPO'):
        super(TafTempoSegment, self).__init__(name)
        self.setupUi(self)
        self.name.setText(name)

        self.setValidator()
        self.bindSignal()

    def setValidator(self):
        super(TafTempoSegment, self).setValidator()

        interval = QRegExpValidator(QRegExp(self.rules.interval))
        self.interval.setValidator(interval)

    def setProb30(self, checked):
        if checked:
            self.prob40.setChecked(False)
        
    def setProb40(self, checked):
        if checked:
            self.prob30.setChecked(False)

    def message(self):
        super(TafTempoSegment, self).message()
        interval = self.interval.text()
        messages = ['TEMPO', interval, self.msg]
        if self.prob30.isChecked():
            messages.insert(0, 'PROB30')
        if self.prob40.isChecked():
            messages.insert(0, 'PROB40')
        self.msg = ' '.join(messages)
        return self.msg

    def checkComplete(self):
        self.complete = False
        oneRequired = (
            self.wind.hasAcceptableInput(), 
            self.vis.hasAcceptableInput(), 
            self.weather.currentText(),
            self.weatherWithIntensity.currentText(),
            self.cloud1.hasAcceptableInput(), 
            self.cloud2.hasAcceptableInput(), 
            self.cloud3.hasAcceptableInput(), 
            self.cb.hasAcceptableInput()
        )

        if self.interval.hasAcceptableInput() and any(oneRequired):
            self.complete = True

        self.completeSignal.emit(self.complete)

    def clear(self):
        super(TafTempoSegment, self).clear()

        self.interval.clear()

        self.prob30.setChecked(False)
        self.prob40.setChecked(False)


class TrendSegment(BaseSegment, Ui_trend.Ui_Editor):

    def __init__(self, name='TREND'):
        super(TrendSegment, self).__init__(name)
        self.setupUi(self)
        self.setValidator()
        self.bindSignal()

    def bindSignal(self):
        super(TrendSegment, self).bindSignal()

        self.nosig.toggled.connect(self.setNosig)
        self.at.toggled.connect(self.setAt)
        self.fm.toggled.connect(self.setFm)
        self.tl.toggled.connect(self.setTl)

        self.period.textChanged.connect(lambda: self.coloredText(self.period))

    def setValidator(self):
        super(TrendSegment, self).setValidator()

        # 还未验证输入个数
        period = QRegExpValidator(QRegExp(self.rules.trendInterval))
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
            self.msg = 'NOSIG'
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

            messages.append(self.msg)
            self.msg = ' '.join(messages)

        return self.msg

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

