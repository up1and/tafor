import json
import datetime

from PyQt5.QtGui import QRegExpValidator, QIntValidator
from PyQt5.QtCore import Qt, QRegExp, pyqtSignal
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QComboBox, QRadioButton, QCheckBox

from tafor import conf, logger
from tafor.utils import CheckTAF, Pattern
from tafor.components.ui import (Ui_taf_primary, Ui_taf_becmg, Ui_taf_tempo, Ui_trend, 
    Ui_sigmet_type, Ui_sigmet_general, Ui_sigmet_phenomena, Ui_sigmet_typhoon, Ui_sigmet_custom)


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


class BaseSegment(QWidget, SegmentMixin):
    completeSignal = pyqtSignal(bool)

    def __init__(self):
        super(BaseSegment, self).__init__()
        self.rules = Pattern()
        self.complete = False

    def bindSignal(self):
        if hasattr(self, 'cavok'):
            self.cavok.toggled.connect(self.setCavok)
            self.nsc.toggled.connect(self.setNsc)

        if hasattr(self, 'prob30'):
            self.prob30.toggled.connect(self.setProb30)
            self.prob40.toggled.connect(self.setProb40)

        self.gust.editingFinished.connect(self.validGust)

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

    def clouds(self, enbale):
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
            self.clouds(False)
        else:
            self.vis.setEnabled(True)
            self.weather.setEnabled(True)
            self.weatherWithIntensity.setEnabled(True)
            self.clouds(True)

    def setNsc(self, checked):
        if checked:
            self.cavok.setChecked(False)
            self.clouds(False)
        else:
            self.clouds(True)

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

    def validGust(self):
        windSpeed = self.wind.text()[-2:] if self.wind.hasAcceptableInput() else 0
        gust = self.gust.text()

        if gust == 'P49':
            return

        if windSpeed == 0 or int(gust) - int(windSpeed) < 5:
            self.gust.clear()

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
        raise NotImplemented

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


class TAFPrimarySegment(BaseSegment, Ui_taf_primary.Ui_Editor):

    def __init__(self):
        super(TAFPrimarySegment, self).__init__()
        self.setupUi(self)

        self.setValidator()
        self.period.setEnabled(False)
        self.ccc.setEnabled(False)
        self.aaa.setEnabled(False)
        self.aaaCnl.setEnabled(False)

        self.bindSignal()

    def setValidator(self):
        super(TAFPrimarySegment, self).setValidator()

        date = QRegExpValidator(QRegExp(self.rules.date))
        self.date.setValidator(date)

        temp = QRegExpValidator(QRegExp(self.rules.temp, Qt.CaseInsensitive))
        self.tmax.setValidator(temp)
        self.tmin.setValidator(temp)

        tempHours = QRegExpValidator(QRegExp(self.rules.hours))
        self.tmaxTime.setValidator(tempHours)
        self.tminTime.setValidator(tempHours)

    def bindSignal(self):
        super(TAFPrimarySegment, self).bindSignal()

        self.tmax.textEdited.connect(lambda: self.upperText(self.tmax))
        self.tmin.textEdited.connect(lambda: self.upperText(self.tmin))

        self.tmax.textEdited.connect(lambda: self.coloredText(self.tmax))
        self.tmin.textEdited.connect(lambda: self.coloredText(self.tmin))
        self.tmaxTime.textEdited.connect(lambda: self.coloredText(self.tmaxTime))
        self.tminTime.textEdited.connect(lambda: self.coloredText(self.tminTime))

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

        self.completeSignal.emit(self.complete)

    def message(self):
        super(TAFPrimarySegment, self).message()
        amd = 'AMD' if self.amd.isChecked() else ''
        cor = 'COR' if self.cor.isChecked() else ''
        icao = conf.value('Message/ICAO')
        timez = self.date.text() + 'Z'
        period = self.period.text()
        tmax = ''.join(['TX', self.tmax.text(), '/', self.tmaxTime.text(), 'Z'])
        tmin = ''.join(['TN', self.tmin.text(), '/', self.tminTime.text(), 'Z'])
        messages = ['TAF', amd, cor, icao, timez, period, self.msg, tmax, tmin]
        self.msg = ' '.join(filter(None, messages))
        return self.msg

    def head(self):
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
        super(TAFPrimarySegment, self).clear()

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


class TAFBecmgSegment(BaseSegment, Ui_taf_becmg.Ui_Editor):

    def __init__(self, name='becmg'):
        super(TAFBecmgSegment, self).__init__()
        self.setupUi(self)
        self.name.setText(name)

        self.setValidator()

        # self.cavok.clicked.connect(self.setCavok)
        # self.nsc.clicked.connect(self.setNsc)

        self.bindSignal()

    def setValidator(self):
        super(TAFBecmgSegment, self).setValidator()

        interval = QRegExpValidator(QRegExp(self.rules.interval))
        self.interval.setValidator(interval)

    def message(self):
        super(TAFBecmgSegment, self).message()
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
        super(TAFBecmgSegment, self).clear()

        self.interval.clear()

        self.cavok.setChecked(False)
        self.nsc.setChecked(False)


class TAFTempoSegment(BaseSegment, Ui_taf_tempo.Ui_Editor):

    def __init__(self, name='tempo'):
        super(TAFTempoSegment, self).__init__()
        self.setupUi(self)
        self.name.setText(name)

        self.setValidator()

        self.bindSignal()

    def setValidator(self):
        super(TAFTempoSegment, self).setValidator()

        interval = QRegExpValidator(QRegExp(self.rules.interval))
        self.interval.setValidator(interval)

    def setProb30(self, checked):
        if checked:
            self.prob40.setChecked(False)
        
    def setProb40(self, checked):
        if checked:
            self.prob30.setChecked(False)

    def message(self):
        super(TAFTempoSegment, self).message()
        interval = self.interval.text()
        messages = ['TEMPO', interval, self.msg]
        if self.prob30.isChecked():
            messages.insert(0, 'PROB30')
        if self.prob40.isChecked():
            messages.insert(0, 'PROB40')
        self.msg = ' '.join(messages)
        # logger.debug(self.msg)
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
        super(TAFTempoSegment, self).clear()

        self.interval.clear()

        self.prob30.setChecked(False)
        self.prob40.setChecked(False)


class TrendSegment(BaseSegment, Ui_trend.Ui_Editor):

    def __init__(self):
        super(TrendSegment, self).__init__()
        self.setupUi(self)
        self.setValidator()
        self.bindSignal()

    def bindSignal(self):
        super(TrendSegment, self).bindSignal()

        self.nosig.toggled.connect(self.setNosig)
        self.at.toggled.connect(self.setAt)
        self.fm.toggled.connect(self.setFm)
        self.tl.toggled.connect(self.setTl)

        self.period.editingFinished.connect(self.validPeriod)

    def setValidator(self):
        super(TrendSegment, self).setValidator()

        # 还未验证输入个数
        period = QRegExpValidator(QRegExp(self.rules.trendInterval))
        self.period.setValidator(period)

    def setNosig(self, checked):
        status = not checked

        self.prefixGroup.setEnabled(status)
        self.typeGroup.setEnabled(status)

        self.period.setEnabled(status)
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

    def setAt(self, checked):
        if checked:
            self.fm.setChecked(False)
            self.tl.setChecked(False)
            self.period.setEnabled(True)
        else:
            self.period.setEnabled(False)

    def setFm(self, checked):
        if checked:
            self.at.setChecked(False)
            self.tl.setChecked(False)
            self.period.setEnabled(True)
        else:
            self.period.setEnabled(False)

    def setTl(self, checked):
        if checked:
            self.fm.setChecked(False)
            self.at.setChecked(False)
            self.period.setEnabled(True)
        else:
            self.period.setEnabled(False)

    def validPeriod(self):
        period = self.period.text()
        utc = datetime.datetime.utcnow()
        time = datetime.datetime(utc.year, utc.month, utc.day, int(period[:2]), int(period[2:]))
        delta = datetime.timedelta(hours=2)

        if time < utc or time - delta > utc:
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


class SigmetTypeSegment(QWidget, Ui_sigmet_type.Ui_Editor):

    def __init__(self):
        super(SigmetTypeSegment, self).__init__()
        self.setupUi(self)

class BaseSigmetPhenomena(QWidget, SegmentMixin, Ui_sigmet_phenomena.Ui_Editor):
    completeSignal = pyqtSignal(bool)

    def __init__(self):
        super(BaseSigmetPhenomena, self).__init__()
        self.duration = 4
        self.complete = True
        self.rules = Pattern()

        self.setupUi(self)
        self.updateDate()
        self.setValidator()
        self.setSquence()
        self.bindSignal()

    def enbaleOBSTime(self, text):
        if text == 'OBS':
            self.obsTime.setEnabled(True)
            self.obsTimeLabel.setEnabled(True)
        else:
            self.obsTime.setEnabled(False)
            self.obsTimeLabel.setEnabled(False)

    def updateDate(self):
        self.time = datetime.datetime.utcnow() + datetime.timedelta(minutes=15)
        self.valid.setText(self.time.strftime('%d%H%M'))

    def setValidator(self):
        date = QRegExpValidator(QRegExp(self.rules.date))
        self.valid.setValidator(date)

        time = QRegExpValidator(QRegExp(self.rules.time))
        self.obsTime.setValidator(time)

        self.sequence.setValidator(QIntValidator(self.sequence))

    def setSquence(self):
        self.sequence.setText('1')

    def setPhenomenaDescription(self):
        raise NotImplemented

    def setPhenomena(self, text):
        raise NotImplemented

    def bindSignal(self):
        self.forecast.currentTextChanged.connect(self.enbaleOBSTime)

        self.typhoonName.textEdited.connect(lambda: self.upperText(self.typhoonName))

        self.valid.textEdited.connect(lambda: self.coloredText(self.valid))
        self.obsTime.textEdited.connect(lambda: self.coloredText(self.obsTime))

        self.register()

    def checkComplete(self):
        raise NotImplemented

    def message(self):
        fir = conf.value('Message/FIR')
        phenomena = self.weatherPhenomena()
        prediction = self.prediction()
        
        text = ' '.join([fir, phenomena, prediction])
        return text

    def head(self):
        area = conf.value('Message/FIR').split()[0]
        sequence = self.sequence.text()
        validStart = self.time.strftime('%d%H%M')
        validEnd = (self.time + datetime.timedelta(hours=self.duration)).strftime('%d%H%M')
        icao = conf.value('Message/ICAO')

        text = '{} SIGMET {} VALID {}/{} {}-'.format(area, sequence, validStart, validEnd, icao)
        return text

    def prediction(self):
        if self.forecast.currentText() == 'OBS':
            text = 'OBS AT {}Z'.format(self.obsTime.text()) if self.obsTime.text() else ''
        else:
            text = self.forecast.currentText()

        return text

    def weatherPhenomena(self):
        items = [self.description.currentText(), self.phenomena.currentText()]
        text = ' '.join(items) if all(items) else ''
        return text


class SigmetGeneralPhenomena(BaseSigmetPhenomena):

    def __init__(self):
        super(SigmetGeneralPhenomena, self).__init__()
        self.hideTyphoonName()
        self.setPhenomenaDescription()
        self.setPhenomena()

    def setPhenomenaDescription(self):
        descriptions = ['OBSC', 'EMBD', 'FRQ', 'SQL', 'SEV', 'HVY']
        self.description.addItems(descriptions)

    def setPhenomena(self, text='OBSC'):
        self.phenomena.clear()

        if text == 'SEV':
            phenomenas = ['TURB', 'ICE', 'ICE (FZRA)', 'MTW']
        elif text == 'HVY':
            phenomenas = ['DS', 'SS']
        else:
            phenomenas = ['TS', 'TS GR']

        self.phenomena.addItems(phenomenas)

    def hideTyphoonName(self):
        self.typhoonName.setVisible(False)
        self.typhoonNameLabel.setVisible(False)

    def checkComplete(self):
        mustRequired = [
                        self.valid.hasAcceptableInput(), 
                        self.sequence.hasAcceptableInput(),
                        ]
        if self.obsTime.isEnabled():
            mustRequired.append(self.obsTime.hasAcceptableInput())

        self.complete = all(mustRequired)
        self.completeSignal.emit(self.complete)

class SigmetTyphoonPhenomena(BaseSigmetPhenomena):

    def __init__(self):
        super(SigmetTyphoonPhenomena, self).__init__()
        self.hideDescription()
        self.setPhenomena()
        self.duration = 6

        self.forecast.setCurrentIndex(self.forecast.findText('OBS'))

    def setPhenomena(self):
        self.phenomena.addItems(['TC'])
        # self.phenomena.setEnabled(False)

    def hideDescription(self):
        self.description.setVisible(False)
        self.descriptionLabel.setVisible(False)

    def weatherPhenomena(self):
        items = [self.phenomena.currentText(), self.typhoonName.text()]
        text = ' '.join(items) if all(items) else ''
        return text

    def checkComplete(self):
        mustRequired = [
                        self.valid.hasAcceptableInput(), 
                        self.sequence.hasAcceptableInput(), 
                        self.typhoonName.text(),
                        ]
        if self.forecast.currentText() == 'OBS':
            mustRequired.append(self.obsTime.hasAcceptableInput())

        self.complete = all(mustRequired)
        self.completeSignal.emit(self.complete)

class SigmetCustomPhenomena(BaseSigmetPhenomena):

    def __init__(self):
        super(SigmetCustomPhenomena, self).__init__()
        self.hidePhenomena()

    def hidePhenomena(self):
        self.description.setVisible(False)
        self.descriptionLabel.setVisible(False)
        self.phenomena.setVisible(False)
        self.phenomenaLabel.setVisible(False)
        self.typhoonName.setVisible(False)
        self.typhoonNameLabel.setVisible(False)
        self.forecast.setVisible(False)
        self.forecastLabel.setVisible(False)
        self.obsTime.setVisible(False)
        self.obsTimeLabel.setVisible(False)

    def checkComplete(self):
        pass


class BaseSigmetContent(QWidget, SegmentMixin):
    completeSignal = pyqtSignal(bool)

    def __init__(self):
        super(BaseSigmetContent, self).__init__()
        self.complete = False
        self.rules = Pattern()


class SigmetGeneralContent(BaseSigmetContent, Ui_sigmet_general.Ui_Editor):

    def __init__(self):
        super(SigmetGeneralContent, self).__init__()
        self.setupUi(self)
        self.bindSignal()
        self.setValidator()
        self.setArea()

    def bindSignal(self):
        self.latitudeAndLongitude.clicked.connect(self.setArea)
        self.line.clicked.connect(self.setArea)
        self.points.clicked.connect(self.setArea)
        self.local.clicked.connect(self.setArea)

        self.position.currentTextChanged.connect(self.setFightLevel)

        self.north.textEdited.connect(lambda: self.upperText(self.north))
        self.south.textEdited.connect(lambda: self.upperText(self.south))
        self.lineLatitude1.textEdited.connect(lambda: self.upperText(self.lineLatitude1))
        self.lineLatitude2.textEdited.connect(lambda: self.upperText(self.lineLatitude2))
        self.lineLatitude3.textEdited.connect(lambda: self.upperText(self.lineLatitude3))
        self.lineLatitude4.textEdited.connect(lambda: self.upperText(self.lineLatitude4))
        self.pointsLatitude1.textEdited.connect(lambda: self.upperText(self.pointsLatitude1))
        self.pointsLatitude2.textEdited.connect(lambda: self.upperText(self.pointsLatitude2))
        self.pointsLatitude3.textEdited.connect(lambda: self.upperText(self.pointsLatitude3))
        self.pointsLatitude4.textEdited.connect(lambda: self.upperText(self.pointsLatitude4))

        self.east.textEdited.connect(lambda: self.upperText(self.east))
        self.west.textEdited.connect(lambda: self.upperText(self.west))
        self.lineLongitude1.textEdited.connect(lambda: self.upperText(self.lineLongitude1))
        self.lineLongitude2.textEdited.connect(lambda: self.upperText(self.lineLongitude2))
        self.lineLongitude3.textEdited.connect(lambda: self.upperText(self.lineLongitude3))
        self.lineLongitude4.textEdited.connect(lambda: self.upperText(self.lineLongitude4))
        self.pointsLongitude1.textEdited.connect(lambda: self.upperText(self.pointsLongitude1))
        self.pointsLongitude2.textEdited.connect(lambda: self.upperText(self.pointsLongitude2))
        self.pointsLongitude3.textEdited.connect(lambda: self.upperText(self.pointsLongitude3))
        self.pointsLongitude4.textEdited.connect(lambda: self.upperText(self.pointsLongitude4))

        self.north.textEdited.connect(lambda: self.coloredText(self.north))
        self.south.textEdited.connect(lambda: self.coloredText(self.south))
        self.lineLatitude1.textEdited.connect(lambda: self.coloredText(self.lineLatitude1))
        self.lineLatitude2.textEdited.connect(lambda: self.coloredText(self.lineLatitude2))
        self.lineLatitude3.textEdited.connect(lambda: self.coloredText(self.lineLatitude3))
        self.lineLatitude4.textEdited.connect(lambda: self.coloredText(self.lineLatitude4))
        self.pointsLatitude1.textEdited.connect(lambda: self.coloredText(self.pointsLatitude1))
        self.pointsLatitude2.textEdited.connect(lambda: self.coloredText(self.pointsLatitude2))
        self.pointsLatitude3.textEdited.connect(lambda: self.coloredText(self.pointsLatitude3))
        self.pointsLatitude4.textEdited.connect(lambda: self.coloredText(self.pointsLatitude4))

        self.east.textEdited.connect(lambda: self.coloredText(self.east))
        self.west.textEdited.connect(lambda: self.coloredText(self.west))
        self.lineLongitude1.textEdited.connect(lambda: self.coloredText(self.lineLongitude1))
        self.lineLongitude2.textEdited.connect(lambda: self.coloredText(self.lineLongitude2))
        self.lineLongitude3.textEdited.connect(lambda: self.coloredText(self.lineLongitude3))
        self.lineLongitude4.textEdited.connect(lambda: self.coloredText(self.lineLongitude4))
        self.pointsLongitude1.textEdited.connect(lambda: self.coloredText(self.pointsLongitude1))
        self.pointsLongitude2.textEdited.connect(lambda: self.coloredText(self.pointsLongitude2))
        self.pointsLongitude3.textEdited.connect(lambda: self.coloredText(self.pointsLongitude3))
        self.pointsLongitude4.textEdited.connect(lambda: self.coloredText(self.pointsLongitude4))

        self.base.textEdited.connect(lambda: self.coloredText(self.base))
        self.top.textEdited.connect(lambda: self.coloredText(self.top))

        self.register()

    def setValidator(self):
        latitude = QRegExpValidator(QRegExp(self.rules.latitude, Qt.CaseInsensitive))
        self.north.setValidator(latitude)
        self.south.setValidator(latitude)
        self.lineLatitude1.setValidator(latitude)
        self.lineLatitude2.setValidator(latitude)
        self.lineLatitude3.setValidator(latitude)
        self.lineLatitude4.setValidator(latitude)
        self.pointsLatitude1.setValidator(latitude)
        self.pointsLatitude2.setValidator(latitude)
        self.pointsLatitude3.setValidator(latitude)
        self.pointsLatitude4.setValidator(latitude)

        longitude = QRegExpValidator(QRegExp(self.rules.longitude, Qt.CaseInsensitive))
        self.east.setValidator(longitude)
        self.west.setValidator(longitude)
        self.lineLongitude1.setValidator(longitude)
        self.lineLongitude2.setValidator(longitude)
        self.lineLongitude3.setValidator(longitude)
        self.lineLongitude4.setValidator(longitude)
        self.pointsLongitude1.setValidator(longitude)
        self.pointsLongitude2.setValidator(longitude)
        self.pointsLongitude3.setValidator(longitude)
        self.pointsLongitude4.setValidator(longitude)

        fightLevel = QRegExpValidator(QRegExp(self.rules.fightLevel))
        self.base.setValidator(fightLevel)
        self.top.setValidator(fightLevel)

        self.speed.setValidator(QIntValidator(self.speed))

    def setArea(self):
        if self.latitudeAndLongitude.isChecked():
            self.latitudeAndLongitudeWidget.setVisible(True)
            self.lineWidget.setVisible(False)
            self.pointsWidget.setVisible(False)

        if self.line.isChecked():
            self.latitudeAndLongitudeWidget.setVisible(False)
            self.lineWidget.setVisible(True)
            self.pointsWidget.setVisible(False)

        if self.points.isChecked():
            self.latitudeAndLongitudeWidget.setVisible(False)
            self.lineWidget.setVisible(False)
            self.pointsWidget.setVisible(True)

        if self.local.isChecked():
            self.latitudeAndLongitudeWidget.setVisible(False)
            self.lineWidget.setVisible(False)
            self.pointsWidget.setVisible(False)

    def setFightLevel(self, text):
        if text in ['TOP', 'ABV']:
            self.base.setEnabled(False)
            self.top.setEnabled(True)
            self.baseLabel.setEnabled(False)
            self.topLabel.setEnabled(True)
        elif text == 'BLW':
            self.base.setEnabled(True)
            self.top.setEnabled(False)
            self.baseLabel.setEnabled(True)
            self.topLabel.setEnabled(False)
        else:
            self.base.setEnabled(True)
            self.top.setEnabled(True)
            self.baseLabel.setEnabled(True)
            self.topLabel.setEnabled(True)

    def setPosition(self, text):
        if 'TS' in text:
            self.position.setCurrentIndex(self.position.findText('TOP'))
        else:
            self.position.setCurrentIndex(-1)

    def checkComplete(self):
        mustRequired = [self.speed.hasAcceptableInput(), self.area()]

        if self.base.isEnabled():
            mustRequired.append(self.base.hasAcceptableInput())

        if self.top.isEnabled():
            mustRequired.append(self.top.hasAcceptableInput())

        self.complete = all(mustRequired)
        self.completeSignal.emit(self.complete)

    def message(self):
        area = self.area()
        fightLevel = self.fightLevel()
        movement = 'MOV {movement} {speed} KMH {intensityChange}'.format(
                movement=self.movement.currentText(),
                speed=self.speed.text(),
                intensityChange=self.intensityChange.currentText(),
            )
        text = ' '.join([area, fightLevel, movement])
        return text

    def fightLevel(self):
        position = self.position.currentText()
        base = self.base.text()
        top = self.top.text()

        if not position:
            text = 'FL{}/FL{}'.format(base, top) if all([top, base]) else ''

        if position in ['TOP', 'ABV']:
            text = '{} FL{}'.format(position, top) if top else ''

        if position == 'BLW':
            text = 'BLW FL{}'.format(base) if base else ''

        return text

    def area(self):
        def point(latitude, longitude):
            lat = latitude.text() if latitude.text() else ''
            lon = longitude.text() if longitude.text() else ''

            text = '{} {}'.format(lat, lon) if all([lat, lon]) else ''
            return text

        if self.latitudeAndLongitude.isChecked():
            north = 'N OF {}'.format(self.north.text()) if self.north.text() else ''
            south = 'S OF {}'.format(self.south.text()) if self.south.text() else ''
            east = 'E OF {}'.format(self.east.text()) if self.east.text() else ''
            west = 'W OF {}'.format(self.west.text()) if self.west.text() else ''
            areas = [north, south, east, west]

            text = ' AND '.join(filter(None, areas))

        if self.line.isChecked():
            point1 = point(self.lineLatitude1, self.lineLongitude1)
            point2 = point(self.lineLatitude2, self.lineLongitude2)
            line1 = '{} OF LINE {} - {}'.format(self.lineDirection1.currentText(), point1, point2) if all([point1, point2]) else ''

            point3 = point(self.lineLatitude3, self.lineLongitude3)
            point4 = point(self.lineLatitude4, self.lineLongitude4)
            line2 = '{} OF LINE {} - {}'.format(self.lineDirection2.currentText(), point3, point4) if all([point3, point4]) else ''

            lines = [line1, line2]
            text = ' AND '.join(filter(None, lines))

        if self.points.isChecked():
            point1 = point(self.pointsLatitude1, self.pointsLongitude1)
            point2 = point(self.pointsLatitude2, self.pointsLongitude2)
            point3 = point(self.pointsLatitude3, self.pointsLongitude3)
            point4 = point(self.pointsLatitude4, self.pointsLongitude4)

            points = list(filter(None, [point1, point2, point3, point4]))
            text = 'WI ' + ' - '.join(points) if len(points) > 3 else ''

        if self.local.isChecked():
            text = conf.value('Message/ICAO')

        return text


class SigmetTyphoonContent(BaseSigmetContent, Ui_sigmet_typhoon.Ui_Editor):

    def __init__(self):
        super(SigmetTyphoonContent, self).__init__()
        self.setupUi(self)

    def bindSignal(self):
        self.register()

    def message(self):
        area = '{latitude} {Longitude} CB TOP FL{height} WI {range}KM OF CENTER'.format(
                latitude=self.currentLatitude.text(),
                Longitude=self.currentLongitude.text(),
                height=self.height.text(),
                range=self.range.text()
            )
        movement = 'MOV {movement} {speed}KMH {intensityChange}'.format(
                movement=self.movement.currentText(),
                speed=self.speed.text(),
                intensityChange=self.intensityChange.currentText()
            )
        forecast = 'FCST {forecastTime}Z TC CENTER {forecastLatitude} {forecastLongitude}'.format(
                forecastTime=self.forecastTime.text(),
                forecastLatitude=self.forecastLatitude.text(),
                forecastLongitude=self.forecastLongitude.text()
            )
        text = ' '.join([area, movement, forecast])
        return text


class SigmetCustomContent(BaseSigmetContent, Ui_sigmet_custom.Ui_Editor):

    def __init__(self):
        super(SigmetCustomContent, self).__init__()
        self.setupUi(self)

    def message(self):
        fir = conf.value('Message/FIR')
        text = ' '.join([fir, self.custom.toPlainText()])
        return text


class SigmetGeneralSegment(BaseSigmetContent):

    def __init__(self):
        super(SigmetGeneralSegment, self).__init__()
        self.initUI()
        self.bindSignal()

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.phenomena = SigmetGeneralPhenomena()
        self.content = SigmetGeneralContent()
        layout.addWidget(self.phenomena)
        layout.addWidget(self.content)
        self.setLayout(layout)

    def bindSignal(self):
        self.phenomena.description.currentTextChanged.connect(self.phenomena.setPhenomena)
        self.phenomena.phenomena.currentTextChanged.connect(self.content.setPosition)

    def message(self):
        content = ' '.join([self.phenomena.message(), self.content.message()])
        text = '\n'.join([self.phenomena.head(), content])
        return text


class SigmetTyphoonSegment(BaseSigmetContent):

    def __init__(self):
        super(SigmetTyphoonSegment, self).__init__()
        self.initUI()
        self.bindSignal()

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.phenomena = SigmetTyphoonPhenomena()
        self.content = SigmetTyphoonContent()
        layout.addWidget(self.phenomena)
        layout.addWidget(self.content)
        self.setLayout(layout)

    def bindSignal(self):
        pass

    def message(self):
        content = ' '.join([self.phenomena.message(), self.content.message()])
        text = '\n'.join([self.phenomena.head(), content])
        return text


class SigmetCustomSegment(BaseSigmetContent):

    def __init__(self):
        super(SigmetCustomSegment, self).__init__()
        self.initUI()
        self.bindSignal()

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.phenomena = SigmetCustomPhenomena()
        self.content = SigmetCustomContent()
        layout.addWidget(self.phenomena)
        layout.addWidget(self.content)
        self.setLayout(layout)

    def bindSignal(self):
        pass

    def message(self):
        text = '\n'.join([self.phenomena.head(), self.content.message()])
        return text
