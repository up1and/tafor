import json
import datetime

from PyQt5 import QtCore, QtGui, QtWidgets

from tafor import conf, logger
from tafor.utils import CheckTAF, Pattern
from tafor.components.ui import Ui_taf_primary, Ui_taf_becmg, Ui_taf_tempo, Ui_trend


class BaseSegment(QtWidgets.QWidget):
    completeSignal = QtCore.pyqtSignal(bool)

    def __init__(self):
        super(BaseSegment, self).__init__()
        self.rules = Pattern()
        self.complete = False
        # self.one_second_timer = QtCore.QTimer()
        # self.one_second_timer.timeout.connect(self.message)
        # self.one_second_timer.start(1 * 1000)

    def bindSignal(self):
        if hasattr(self, 'cavok'):
            self.cavok.toggled.connect(self.setCavok)
            self.skc.toggled.connect(self.setSkc)
            self.nsc.toggled.connect(self.setNsc)
            self.cavok.clicked.connect(self.checkComplete)
            self.nsc.clicked.connect(self.checkComplete)
            self.skc.clicked.connect(self.checkComplete)
        else:
            self.prob30.toggled.connect(self.setProb30)
            self.prob40.toggled.connect(self.setProb40)

        self.gust.editingFinished.connect(self.validGust)

        self.wind.textEdited.connect(lambda: self.upperText(self.wind))
        self.gust.textEdited.connect(lambda: self.upperText(self.gust))
        self.cloud1.textEdited.connect(lambda: self.upperText(self.cloud1))
        self.cloud2.textEdited.connect(lambda: self.upperText(self.cloud2))
        self.cloud3.textEdited.connect(lambda: self.upperText(self.cloud3))
        self.cb.textEdited.connect(lambda: self.upperText(self.cb))

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
            self.weatherWithIntensity.setEnabled(False)
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

    def setProb30(self, checked):
        if checked:
            self.prob40.setChecked(False)
        
    def setProb40(self, checked):
        if checked:
            self.prob30.setChecked(False)

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
        wind = self.wind.text()[-2:]
        gust = self.gust.text()

        if gust in ['', 'P49']:
            return

        self.gust.setText(gust.zfill(2))

        if int(gust) > 49:
            self.gust.clear()

        if not wind or int(gust) - int(wind) < 5:
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


class TAFPrimarySegment(BaseSegment, Ui_taf_primary.Ui_Form):

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


class TAFBecmgSegment(BaseSegment, Ui_taf_becmg.Ui_Form):

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


class TAFTempoSegment(BaseSegment, Ui_taf_tempo.Ui_Form):

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

        self.interval.textChanged.connect(self.checkComplete)
        self.weather.currentIndexChanged.connect(self.checkComplete)
        self.weatherWithIntensity.currentIndexChanged.connect(self.checkComplete)

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


class TrendSegment(BaseSegment, Ui_trend.Ui_Form):

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
                    trend_prefix = 'AT'
                if self.fm.isChecked():
                    trend_prefix = 'FM'
                if self.tl.isChecked():
                    trend_prefix = 'TL'

                period = trend_prefix + self.period.text()
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
