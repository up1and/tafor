import json
import datetime

from PyQt5 import QtCore, QtGui, QtWidgets

from tafor import conf, logger
from tafor.utils import CheckTAF, Pattern
from tafor.components.ui import (Ui_taf_primary, Ui_taf_becmg, Ui_taf_tempo, Ui_trend, 
    Ui_sigmet_type, Ui_sigmet_general, Ui_sigmet_phenomena, Ui_sigmet_typhoon, Ui_sigmet_custom)


class BaseSegment(QtWidgets.QWidget):
    completeSignal = QtCore.pyqtSignal(bool)

    def __init__(self):
        super(BaseSegment, self).__init__()
        self.rules = Pattern()
        self.complete = False

    def bindSignal(self):
        if hasattr(self, 'cavok'):
            self.cavok.toggled.connect(self.setCavok)
            self.skc.toggled.connect(self.setSkc)
            self.nsc.toggled.connect(self.setNsc)
            self.cavok.clicked.connect(self.checkComplete)
            self.nsc.clicked.connect(self.checkComplete)
            self.skc.clicked.connect(self.checkComplete)

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

        self.wind.textChanged.connect(self.checkComplete)
        self.vis.textChanged.connect(self.checkComplete)
        self.cloud1.textChanged.connect(self.checkComplete)
        self.cloud2.textChanged.connect(self.checkComplete)
        self.cloud3.textChanged.connect(self.checkComplete)
        self.cb.textChanged.connect(self.checkComplete)

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
            self.skc.setChecked(False)
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

    def setSkc(self, checked):
        if checked:
            self.cavok.setChecked(False)
            self.nsc.setChecked(False)
            self.clouds(False)
        else:
            self.clouds(True)

    def setNsc(self, checked):
        if checked:
            self.cavok.setChecked(False)
            self.skc.setChecked(False)
            self.clouds(False)
        else:
            self.clouds(True)

    def setValidator(self):
        wind = QtGui.QRegExpValidator(QtCore.QRegExp(self.rules.wind, QtCore.Qt.CaseInsensitive))
        self.wind.setValidator(wind)

        gust = QtGui.QRegExpValidator(QtCore.QRegExp(self.rules.gust, QtCore.Qt.CaseInsensitive))
        self.gust.setValidator(gust)

        vis = QtGui.QRegExpValidator(QtCore.QRegExp(self.rules.vis))
        self.vis.setValidator(vis)

        cloud = QtGui.QRegExpValidator(QtCore.QRegExp(self.rules.cloud, QtCore.Qt.CaseInsensitive))
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
            elif self.skc.isChecked():
                messages = [winds, vis, weatherWithIntensity, weather, 'SKC']
            elif self.nsc.isChecked():
                messages = [winds, vis, weatherWithIntensity, weather, 'NSC']
            else:
                messages = [winds, vis, weatherWithIntensity, weather] + clouds
        else:
            messages = [winds, vis, weatherWithIntensity, weather] + clouds
        self.msg = ' '.join(filter(None, messages))
        # logger.debug(self.msg)

    def upperText(self, line):
        line.setText(line.text().upper())

    def coloredText(self, line):
        if line.hasAcceptableInput():
            line.setStyleSheet('color: black')
        else:
            line.setStyleSheet('color: grey')

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

        date = QtGui.QRegExpValidator(QtCore.QRegExp(self.rules.date))
        self.date.setValidator(date)

        temp = QtGui.QRegExpValidator(QtCore.QRegExp(self.rules.temp, QtCore.Qt.CaseInsensitive))
        self.tmax.setValidator(temp)
        self.tmin.setValidator(temp)

        tempHours = QtGui.QRegExpValidator(QtCore.QRegExp(self.rules.hours))
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

        # 设置下一步按钮
        self.date.textEdited.connect(self.checkComplete)
        self.period.textChanged.connect(self.checkComplete)
        self.tmax.textChanged.connect(self.checkComplete)
        self.tmaxTime.textChanged.connect(self.checkComplete)
        self.tmin.textChanged.connect(self.checkComplete)
        self.tminTime.textChanged.connect(self.checkComplete)

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
                        self.skc.isChecked(), 
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
        self.skc.setChecked(False)
        self.nsc.setChecked(False)

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
        # self.skc.clicked.connect(self.setSkc_nsc)
        # self.nsc.clicked.connect(self.setSkc_nsc)

        self.bindSignal()

    def setValidator(self):
        super(TAFBecmgSegment, self).setValidator()

        interval = QtGui.QRegExpValidator(QtCore.QRegExp(self.rules.interval))
        self.interval.setValidator(interval)

    def bindSignal(self):
        super(TAFBecmgSegment, self).bindSignal()

        self.interval.textChanged.connect(self.checkComplete)
        self.weather.currentIndexChanged.connect(self.checkComplete)
        self.weatherWithIntensity.currentIndexChanged.connect(self.checkComplete)

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
            self.skc.isChecked(),
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
        self.skc.setChecked(False)
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

        interval = QtGui.QRegExpValidator(QtCore.QRegExp(self.rules.interval))
        self.interval.setValidator(interval)

    def bindSignal(self):
        super(TAFTempoSegment, self).bindSignal()

        self.prob30.toggled.connect(self.setProb30)
        self.prob40.toggled.connect(self.setProb40)

        self.interval.textChanged.connect(self.checkComplete)
        self.weather.currentIndexChanged.connect(self.checkComplete)
        self.weatherWithIntensity.currentIndexChanged.connect(self.checkComplete)

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

        self.nosig.clicked.connect(self.checkComplete)
        self.at.clicked.connect(self.checkComplete)
        self.fm.clicked.connect(self.checkComplete)
        self.tl.clicked.connect(self.checkComplete)

    def setValidator(self):
        super(TrendSegment, self).setValidator()

        # 还未验证输入个数
        period = QtGui.QRegExpValidator(QtCore.QRegExp(self.rules.trendInterval))
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
        self.skc.setEnabled(status)
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
            self.skc.isChecked(),
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
        self.skc.setChecked(False)
        self.nsc.setChecked(False)

        self.period.setEnabled(False)
        self.period.clear()


class SigmetTypeSegment(QtWidgets.QWidget, Ui_sigmet_type.Ui_Editor):

    def __init__(self):
        super(SigmetTypeSegment, self).__init__()
        self.setupUi(self)

class BaseSigmetPhenomena(QtWidgets.QWidget, Ui_sigmet_phenomena.Ui_Editor):

    def __init__(self):
        super(BaseSigmetPhenomena, self).__init__()
        self.setupUi(self)
        self.bindSignal()
        self.updateDate()
        self.setSquence()

        self.duration = 4

    def bindSignal(self):
        self.forecast.currentTextChanged.connect(self.enbaleOBSTime)

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

    def setSquence(self):
        self.sequence.setText('1')

    def setPhenomenaDescription(self):
        raise NotImplemented

    def setPhenomena(self, text):
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


class SigmetTyphoonPhenomena(BaseSigmetPhenomena):

    def __init__(self):
        super(SigmetTyphoonPhenomena, self).__init__()
        self.hideDescription()
        self.setPhenomena()
        self.duration = 6

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
        

class SigmetGeneralContent(QtWidgets.QWidget, Ui_sigmet_general.Ui_Editor):

    def __init__(self):
        super(SigmetGeneralContent, self).__init__()
        self.setupUi(self)
        self.bindSignal()

        self.setArea()

    def bindSignal(self):
        self.latitudeAndLongitude.clicked.connect(self.setArea)
        self.line.clicked.connect(self.setArea)
        self.points.clicked.connect(self.setArea)
        self.local.clicked.connect(self.setArea)

        self.position.currentTextChanged.connect(self.setFightLevel)

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
            self.position.setCurrentIndex(1)

    def message(self):
        area = self.area()
        fightLevel = self.fightLevel()
        movement = 'MOV {}'.format(self.movement.currentText())
        speed = '{} KMH'.format(self.speed.text())
        intensityChange = self.intensityChange.currentText()

        text = ' '.join([area, fightLevel, movement, speed, intensityChange])
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
            point1 = point(self.lineLatitude1, self.lineLongtitude1)
            point2 = point(self.lineLatitude2, self.lineLongtitude2)
            line1 = '{} OF LINE {} - {}'.format(self.lineDirection1.currentText(), point1, point2) if all([point1, point2]) else ''

            point3 = point(self.lineLatitude3, self.lineLongtitude3)
            point4 = point(self.lineLatitude4, self.lineLongtitude4)
            line2 = '{} OF LINE {} - {}'.format(self.lineDirection2.currentText(), point3, point4) if all([point3, point4]) else ''

            lines = [line1, line2]
            text = ' AND '.join(filter(None, lines))

        if self.points.isChecked():
            point1 = point(self.pointsLatitude1, self.pointsLongtitude1)
            point2 = point(self.pointsLatitude2, self.pointsLongtitude2)
            point3 = point(self.pointsLatitude3, self.pointsLongtitude3)
            point4 = point(self.pointsLatitude4, self.pointsLongtitude4)

            points = [point1, point2, point3, point4]
            text = 'WI ' + ' - '.join(filter(None, points))

        if self.local.isChecked():
            text = conf.value('Message/ICAO')

        return text


class SigmetTyphoonContent(QtWidgets.QWidget, Ui_sigmet_typhoon.Ui_Editor):

    def __init__(self):
        super(SigmetTyphoonContent, self).__init__()
        self.setupUi(self)


class SigmetCustomContent(QtWidgets.QWidget, Ui_sigmet_custom.Ui_Editor):

    def __init__(self):
        super(SigmetCustomContent, self).__init__()
        self.setupUi(self)


class SigmetGeneralSegment(QtWidgets.QWidget):

    def __init__(self):
        super(SigmetGeneralSegment, self).__init__()
        self.initUI()
        self.bindSignal()

    def initUI(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.phenomena = SigmetGeneralPhenomena()
        self.content = SigmetGeneralContent()
        layout.addWidget(self.phenomena)
        layout.addWidget(self.content)
        self.setLayout(layout)

    def bindSignal(self):
        self.phenomena.description.currentTextChanged.connect(self.phenomena.setPhenomena)
        self.phenomena.phenomena.currentTextChanged.connect(self.content.setPosition)


class SigmetTyphoonSegment(QtWidgets.QWidget):

    def __init__(self):
        super(SigmetTyphoonSegment, self).__init__()
        self.initUI()
        self.bindSignal()

    def initUI(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.phenomena = SigmetTyphoonPhenomena()
        self.content = SigmetTyphoonContent()
        layout.addWidget(self.phenomena)
        layout.addWidget(self.content)
        self.setLayout(layout)

    def bindSignal(self):
        pass


class SigmetCustomSegment(QtWidgets.QWidget):

    def __init__(self):
        super(SigmetCustomSegment, self).__init__()
        self.initUI()
        self.bindSignal()

    def initUI(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.phenomena = SigmetCustomPhenomena()
        self.content = SigmetCustomContent()
        layout.addWidget(self.phenomena)
        layout.addWidget(self.content)
        self.setLayout(layout)

    def bindSignal(self):
        pass