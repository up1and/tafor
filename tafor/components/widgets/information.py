import re
import datetime

from itertools import cycle

from PyQt5.QtGui import QIcon, QRegExpValidator, QIntValidator, QTextCharFormat, QFont
from PyQt5.QtCore import Qt, QRegExp, QCoreApplication, pyqtSignal
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLineEdit

from tafor import conf, logger
from tafor.utils import Pattern
from tafor.utils.convert import parseTime, parseDateTime, ceilTime, calcPosition
from tafor.utils.service import currentSigmet
from tafor.models import db, Sigmet
from tafor.components.widgets.forecast import SegmentMixin
from tafor.components.widgets.area import AreaBoard
from tafor.components.ui import (Ui_sigmet_type, Ui_sigmet_general, Ui_sigmet_head, 
    Ui_sigmet_typhoon, Ui_sigmet_cancel, Ui_sigmet_custom, main_rc)


class SigmetTypeSegment(QWidget, Ui_sigmet_type.Ui_Editor):

    def __init__(self):
        super(SigmetTypeSegment, self).__init__()
        self.setupUi(self)
        self.tt = 'WS'

    def setType(self, tt):
        self.tt = tt

    def message(self):
        area = conf.value('Message/Area') or ''
        icao = conf.value('Message/ICAO')
        time = datetime.datetime.utcnow().strftime('%d%H%M')
        messages = [self.tt + area, icao, time]
        return ' '.join(filter(None, messages))

class BaseSigmetHead(QWidget, SegmentMixin, Ui_sigmet_head.Ui_Editor):
    completeSignal = pyqtSignal(bool)

    def __init__(self, mainwindow=None):
        super(BaseSigmetHead, self).__init__()
        self.duration = 4
        self.complete = True
        self.rules = Pattern()
        self.mainwindow = mainwindow

        self.setupUi(self)
        self.updateState()
        self.setValidator()
        self.bindSignal()

    def bindSignal(self):
        self.forecast.currentTextChanged.connect(self.enbaleOBSTime)
        self.endingTime.editingFinished.connect(self.validateEndingTime)

        self.typhoonName.textEdited.connect(lambda: self.upperText(self.typhoonName))

        self.beginningTime.textEdited.connect(lambda: self.coloredText(self.beginningTime))
        self.endingTime.textEdited.connect(lambda: self.coloredText(self.endingTime))
        self.obsTime.textEdited.connect(lambda: self.coloredText(self.obsTime))

        self.register()

    def enbaleOBSTime(self, text):
        if text == 'OBS':
            self.obsTime.setEnabled(True)
            self.obsTimeLabel.setEnabled(True)
        else:
            self.obsTime.setEnabled(False)
            self.obsTimeLabel.setEnabled(False)

    def updateState(self):
        self.setValidTime()
        self.setSquence()

    def durationTime(self):
        self.time = datetime.datetime.utcnow()
        start = ceilTime(self.time, amount=15)
        end = start + datetime.timedelta(hours=self.duration)
        return start, end

    def validateEndingTime(self):
        if self.beginningTime.hasAcceptableInput() and self.endingTime.hasAcceptableInput():
            start = parseDateTime(self.beginningTime.text())
            end = parseDateTime(self.endingTime.text())

            if end <= start:
                self.endingTime.clear()
                self.mainwindow.statusBar.showMessage(QCoreApplication.translate('Editor', 'Ending time must be greater than the beginning time'), 5000)

            if end - start > datetime.timedelta(hours=self.duration):
                self.endingTime.clear()
                self.mainwindow.statusBar.showMessage(QCoreApplication.translate('Editor', 'Valid period more than {} hours').format(self.duration), 5000)

    def validateObsTime(self):
        # 未启用
        if self.beginningTime.hasAcceptableInput() and self.obsTime.hasAcceptableInput():
            start = parseDateTime(self.beginningTime.text())
            obs = parseTime(self.obsTime.text())
            if obs > start:
                self.obsTime.clear()
                self.mainwindow.statusBar.showMessage(QCoreApplication.translate('Editor', 'Observation time should before the beginning time'), 5000)

    def validate(self):
        self.validateEndingTime()

    def setDuration(self, duration):
        self.duration = duration

    def setValidTime(self):
        beginningTime, endingTime = self.durationTime()
        self.beginningTime.setText(beginningTime.strftime('%d%H%M'))
        self.endingTime.setText(endingTime.strftime('%d%H%M'))

    def setValidator(self):
        date = QRegExpValidator(QRegExp(self.rules.date))
        self.beginningTime.setValidator(date)
        self.endingTime.setValidator(date)

        time = QRegExpValidator(QRegExp(self.rules.time))
        self.obsTime.setValidator(time)

        self.sequence.setValidator(QIntValidator(1, 99, self.sequence))

    def setSquence(self):
        time = datetime.datetime.utcnow()
        begin = datetime.datetime(time.year, time.month, time.day)
        count = db.query(Sigmet).filter(Sigmet.sent > begin).count() + 1
        self.sequence.setText(str(count))

    def setPhenomenaDescription(self):
        raise NotImplementedError

    def setPhenomena(self, text):
        raise NotImplementedError

    def checkComplete(self):
        raise NotImplementedError

    def message(self):
        fir = conf.value('Message/FIR')
        phenomena = self.weatherPhenomena()
        prediction = self.prediction()
        
        text = ' '.join([fir, phenomena, prediction])
        return text

    def head(self):
        area = conf.value('Message/FIR').split()[0]
        sequence = self.sequence.text()
        beginningTime = self.beginningTime.text()
        endingTime = self.endingTime.text()
        icao = conf.value('Message/ICAO')

        text = '{} SIGMET {} VALID {}/{} {}-'.format(area, sequence, beginningTime, endingTime, icao)
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


class BaseSigmetContent(QWidget, SegmentMixin):
    completeSignal = pyqtSignal(bool)

    def __init__(self, head):
        super(BaseSigmetContent, self).__init__()
        self.complete = False
        self.rules = Pattern()
        self.head = head


class BaseSegment(QWidget):
    changeSignal = pyqtSignal()

    def __init__(self, typeSegment, mainwindow=None):
        super(BaseSegment, self).__init__()
        self.type = typeSegment
        self.mainwindow = mainwindow

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.head)
        layout.addWidget(self.content)
        self.setLayout(layout)

    def head(self):
        area = conf.value('Message/Area') or ''
        icao = conf.value('Message/ICAO')
        time = self.time.strftime('%d%H%M')
        tt = self.type.tt

        messages = [tt + area, icao, time]
        return ' '.join(filter(None, messages))

    def message(self):
        content = ' '.join([self.head.message(), self.content.message()])
        text = '\n'.join([self.head.head(), content])
        text = text if text.endswith('=') else text + '='
        return text

    def setType(self, tt):
        durations = {
            'WS': 4,
            'WC': 6,
            'WV': 6
        }
        self.head.setDuration(durations[tt])
        self.type.setType(tt)

        self.changeSignal.emit()

    def clear(self):
        self.head.clear()
        self.content.clear()


class SigmetGeneralHead(BaseSigmetHead):

    def __init__(self, mainwindow=None):
        super(SigmetGeneralHead, self).__init__(mainwindow)
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
            phenomenas = ['TS', 'TSGR']

        self.phenomena.addItems(phenomenas)

    def hideTyphoonName(self):
        self.typhoonName.setVisible(False)
        self.typhoonNameLabel.setVisible(False)

    def checkComplete(self):
        mustRequired = [
            self.beginningTime.hasAcceptableInput(),
            self.endingTime.hasAcceptableInput(),
            self.sequence.hasAcceptableInput(),
        ]
        if self.obsTime.isEnabled():
            mustRequired.append(self.obsTime.hasAcceptableInput())

        self.complete = all(mustRequired)
        self.completeSignal.emit(self.complete)


class SigmetGeneralContent(BaseSigmetContent, Ui_sigmet_general.Ui_Editor):

    def __init__(self, phenomena):
        super(SigmetGeneralContent, self).__init__(phenomena)
        self.setupUi(self)
        self.canvasWidget = AreaBoard()
        self.areaLayout.addWidget(self.canvasWidget)
        self.areaGroup.setLayout(self.areaLayout)

        self.bindSignal()
        self.setValidator()
        self.setArea()
        self.setCanvasMode()

    def bindSignal(self):
        self.manual.clicked.connect(self.setArea)
        self.canvas.clicked.connect(self.setArea)
        self.entire.clicked.connect(self.setArea)

        self.modeButton.clicked.connect(self.switchCanvasMode)

        self.position.currentTextChanged.connect(self.setFightLevel)
        self.movement.currentTextChanged.connect(self.setSpeed)

        self.north.textEdited.connect(lambda: self.upperText(self.north))
        self.south.textEdited.connect(lambda: self.upperText(self.south))
        self.east.textEdited.connect(lambda: self.upperText(self.east))
        self.west.textEdited.connect(lambda: self.upperText(self.west))

        self.north.textEdited.connect(lambda: self.coloredText(self.north))
        self.south.textEdited.connect(lambda: self.coloredText(self.south))
        self.east.textEdited.connect(lambda: self.coloredText(self.east))
        self.west.textEdited.connect(lambda: self.coloredText(self.west))

        self.base.textEdited.connect(lambda: self.coloredText(self.base))
        self.top.textEdited.connect(lambda: self.coloredText(self.top))

        self.canvasWidget.canvas.stateChanged.connect(self.checkComplete)

        self.register()

    def setValidator(self):
        latitude = QRegExpValidator(QRegExp(self.rules.latitude, Qt.CaseInsensitive))
        self.north.setValidator(latitude)
        self.south.setValidator(latitude)

        longitude = QRegExpValidator(QRegExp(self.rules.longitude, Qt.CaseInsensitive))
        self.east.setValidator(longitude)
        self.west.setValidator(longitude)

        fightLevel = QRegExpValidator(QRegExp(self.rules.fightLevel))
        self.base.setValidator(fightLevel)
        self.top.setValidator(fightLevel)

        self.speed.setValidator(QIntValidator(1, 99, self.speed))

    def setArea(self):
        if self.manual.isChecked():
            self.latitudeAndLongitudeWidget.setVisible(True)
            self.canvasWidget.setVisible(False)
            self.modeButton.setVisible(False)

        if self.canvas.isChecked():
            self.latitudeAndLongitudeWidget.setVisible(False)
            self.canvasWidget.setVisible(True)
            self.modeButton.setVisible(True)

        if self.entire.isChecked():
            self.latitudeAndLongitudeWidget.setVisible(False)
            self.canvasWidget.setVisible(False)
            self.modeButton.setVisible(False)

    def setCanvasMode(self):
        canvasMode = [
            {'icon': ':/polygon.png', 'mode': 'polygon'},
            {'icon': ':/line.png', 'mode': 'line'},
            {'icon': ':/rectangular.png', 'mode': 'rectangular'}
        ]
        self.canvasMode = cycle(canvasMode)
        self.switchCanvasMode()

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

    def setSpeed(self, text):
        if text == 'STNR':
            self.speed.setEnabled(False)
            self.speedLabel.setEnabled(False)
        else:
            self.speed.setEnabled(True)
            self.speedLabel.setEnabled(True)

    def setPosition(self, text):
        if 'TS' in text:
            self.position.setCurrentIndex(self.position.findText('TOP'))
        else:
            self.position.setCurrentIndex(-1)

    def switchCanvasMode(self):
        canvasMode = next(self.canvasMode)
        self.canvasWidget.setMode(canvasMode['mode'])
        self.modeButton.setIcon(QIcon(canvasMode['icon']))
        self.canvasWidget.canvas.clear()

    def checkComplete(self):
        mustRequired = [self.area()]

        if self.base.isEnabled():
            mustRequired.append(self.base.hasAcceptableInput())

        if self.top.isEnabled():
            mustRequired.append(self.top.hasAcceptableInput())

        if self.speed.isEnabled():
            mustRequired.append(self.speed.hasAcceptableInput())

        self.complete = all(mustRequired)
        self.completeSignal.emit(self.complete)

    def message(self):
        area = self.area()
        fightLevel = self.fightLevel()
        moveState = self.moveState()
        intensityChange = self.intensityChange.currentText()
        text = ' '.join([area, fightLevel, moveState, intensityChange])
        return text

    def moveState(self):
        movement = self.movement.currentText()

        if movement == 'STNR':
            text = 'STNR'
        else:
            text = 'MOV {movement} {speed}KMH'.format(
                    movement=movement,
                    speed=int(self.speed.text())
                )

        return text

    def fightLevel(self):
        position = self.position.currentText()
        base = self.base.text()
        top = self.top.text()

        if not position:
            text = 'FL{}/{}'.format(base, top) if all([top, base]) else ''

        if position in ['TOP', 'ABV']:
            text = '{} FL{}'.format(position, top) if top else ''

        if position == 'BLW':
            text = 'BLW FL{}'.format(base) if base else ''

        return text

    def area(self):
        if self.manual.isChecked():
            north = 'N OF {}'.format(self.north.text()) if self.north.text() else ''
            south = 'S OF {}'.format(self.south.text()) if self.south.text() else ''
            east = 'E OF {}'.format(self.east.text()) if self.east.text() else ''
            west = 'W OF {}'.format(self.west.text()) if self.west.text() else ''
            areas = [north, south, east, west]

            text = ' AND '.join(filter(None, areas))

        if self.canvas.isChecked():
            text = self.canvasWidget.text()

        if self.entire.isChecked():
            suffix = conf.value('Message/FIR').split()[-1]
            text = 'ENTIRE {}'.format(suffix)

        return text

    def clear(self):
        super(SigmetGeneralContent, self).clear()
        self.canvasWidget.clear()

class SigmetTyphoonHead(BaseSigmetHead):

    def __init__(self, mainwindow=None):
        super(SigmetTyphoonHead, self).__init__(mainwindow)
        self.hideDescription()
        self.setPhenomena()
        self.duration = 6

        self.forecast.setCurrentIndex(self.forecast.findText('OBS'))

    def setPhenomena(self):
        self.phenomena.addItems(['TC'])

    def hideDescription(self):
        self.description.setVisible(False)
        self.descriptionLabel.setVisible(False)

    def weatherPhenomena(self):
        items = [self.phenomena.currentText(), self.typhoonName.text()]
        text = ' '.join(items) if all(items) else ''
        return text

    def checkComplete(self):
        mustRequired = [
            self.beginningTime.hasAcceptableInput(), 
            self.endingTime.hasAcceptableInput(),
            self.sequence.hasAcceptableInput(), 
            self.typhoonName.text(),
        ]
        if self.forecast.currentText() == 'OBS':
            mustRequired.append(self.obsTime.hasAcceptableInput())

        self.complete = all(mustRequired)
        self.completeSignal.emit(self.complete)


class SigmetTyphoonContent(BaseSigmetContent, Ui_sigmet_typhoon.Ui_Editor):

    def __init__(self, phenomena):
        super(SigmetTyphoonContent, self).__init__(phenomena)
        self.setupUi(self)
        self.bindSignal()
        self.setValidator()

    def bindSignal(self):
        self.movement.currentTextChanged.connect(self.setSpeed)

        self.currentLatitude.textEdited.connect(lambda: self.upperText(self.currentLatitude))
        self.currentLongitude.textEdited.connect(lambda: self.upperText(self.currentLongitude))
        self.forecastLatitude.textEdited.connect(lambda: self.upperText(self.forecastLatitude))
        self.forecastLongitude.textEdited.connect(lambda: self.upperText(self.forecastLongitude))

        self.currentLatitude.textEdited.connect(lambda: self.coloredText(self.currentLatitude))
        self.currentLongitude.textEdited.connect(lambda: self.coloredText(self.currentLongitude))
        self.height.textEdited.connect(lambda: self.coloredText(self.height))
        self.forecastTime.textEdited.connect(lambda: self.coloredText(self.forecastTime))
        self.forecastLatitude.textEdited.connect(lambda: self.coloredText(self.forecastLatitude))
        self.forecastLongitude.textEdited.connect(lambda: self.coloredText(self.forecastLongitude))

        self.register()

    def setValidator(self):
        latitude = QRegExpValidator(QRegExp(self.rules.latitude, Qt.CaseInsensitive))
        self.currentLatitude.setValidator(latitude)
        self.forecastLatitude.setValidator(latitude)

        longitude = QRegExpValidator(QRegExp(self.rules.longitude, Qt.CaseInsensitive))
        self.currentLongitude.setValidator(longitude)
        self.forecastLongitude.setValidator(longitude)

        fightLevel = QRegExpValidator(QRegExp(self.rules.fightLevel))
        self.height.setValidator(fightLevel)

        time = QRegExpValidator(QRegExp(self.rules.time))
        self.forecastTime.setValidator(time)

        self.speed.setValidator(QIntValidator(1, 99, self.speed))
        self.range.setValidator(QIntValidator(1, 999, self.range))

    def setSpeed(self, text):
        if text == 'STNR':
            self.speed.setEnabled(False)
            self.speedLabel.setEnabled(False)
        else:
            self.speed.setEnabled(True)
            self.speedLabel.setEnabled(True)

    def setForecastTime(self, text):
        if len(text) != 6:
            return

        time = parseDateTime(text)
        time = time - datetime.timedelta(minutes=time.minute)
        fcstTime = time.strftime('%H%M')

        self.forecastTime.setText(fcstTime)

    def setForecastPosition(self):
        mustRequired = [
            self.currentLatitude.hasAcceptableInput(),
            self.currentLongitude.hasAcceptableInput(),
            self.speed.hasAcceptableInput(),
            self.forecastTime.hasAcceptableInput(),
        ]

        anyRequired = [
            self.head.obsTime.hasAcceptableInput(),
            self.head.beginningTime.hasAcceptableInput(),
        ]

        if not (all(mustRequired) and any(anyRequired)):
            return

        movement = self.movement.currentText()

        if movement == 'STNR':
            return

        direction = {
            'N': 0,
            'NE': 45,
            'E': 90,
            'SE': 135,
            'S': 180,
            'SW': 225,
            'W': 270,
            'NW': 315
        }
        obsTime = self.head.obsTime.text() if self.head.obsTime.hasAcceptableInput() else ''
        beginningTime = self.head.beginningTime.text()[2:] if self.head.beginningTime.hasAcceptableInput() else ''
        fcstTime = self.forecastTime.text()

        time = self.moveTime(obsTime or beginningTime, fcstTime).seconds
        degree = direction[movement]
        speed = self.speed.text()
        latitude = self.currentLatitude.text()
        longitude = self.currentLongitude.text()

        forecastLatitude, forecastLongitude = calcPosition(latitude, longitude, speed, time, degree)
        self.forecastLatitude.setText(forecastLatitude)
        self.forecastLongitude.setText(forecastLongitude)

    def moveTime(self, start, end):
        return parseTime(end) - parseTime(start)

    def moveState(self):
        movement = self.movement.currentText()

        if movement == 'STNR':
            text = 'STNR'
        else:
            text = 'MOV {movement} {speed}KMH'.format(
                    movement=movement,
                    speed=int(self.speed.text())
                )

        return text

    def message(self):
        area = '{latitude} {Longitude} CB TOP FL{height} WI {range}KM OF CENTRE'.format(
                latitude=self.currentLatitude.text(),
                Longitude=self.currentLongitude.text(),
                height=self.height.text(),
                range=int(self.range.text())
            )
        moveState = self.moveState()
        intensityChange = self.intensityChange.currentText()
        forecast = 'FCST {forecastTime}Z TC CENTRE {forecastLatitude} {forecastLongitude}'.format(
                forecastTime=self.forecastTime.text(),
                forecastLatitude=self.forecastLatitude.text(),
                forecastLongitude=self.forecastLongitude.text()
            )
        text = ' '.join([area, moveState, intensityChange, forecast])
        return text

    def checkComplete(self):
        mustRequired = [line.hasAcceptableInput() for line in self.findChildren(QLineEdit) if line.isEnabled()]

        self.complete = all(mustRequired)
        self.completeSignal.emit(self.complete)


class SigmetSimpleHead(BaseSigmetHead):

    def __init__(self, mainwindow=None):
        super(SigmetSimpleHead, self).__init__(mainwindow)
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

    def message(self):
        fir = conf.value('Message/FIR')
        return fir

    def checkComplete(self):
        mustRequired = [
            self.beginningTime.hasAcceptableInput(),
            self.endingTime.hasAcceptableInput(),
            self.sequence.hasAcceptableInput(),
        ]

        self.complete = all(mustRequired)
        self.completeSignal.emit(self.complete)


class SigmetCancelContent(BaseSigmetContent, Ui_sigmet_cancel.Ui_Editor):

    def __init__(self, phenomena):
        super(SigmetCancelContent, self).__init__(phenomena)
        self.setupUi(self)
        self.setValidator()
        self.bindSignal()

    def bindSignal(self):
        self.beginningTime.textEdited.connect(lambda: self.coloredText(self.beginningTime))
        self.endingTime.textEdited.connect(lambda: self.coloredText(self.endingTime))

        self.register()

    def setValidator(self):
        date = QRegExpValidator(QRegExp(self.rules.date))
        self.beginningTime.setValidator(date)
        self.endingTime.setValidator(date)

        self.sequence.setValidator(QIntValidator(1, 99, self.sequence))

    def message(self):
        text = 'CNL SIGMET {} {}/{}'.format(int(self.sequence.currentText()), self.beginningTime.text(), self.endingTime.text())
        return text

    def checkComplete(self):
        mustRequired = [
            self.beginningTime.hasAcceptableInput(),
            self.endingTime.hasAcceptableInput(),
            self.sequence.currentText() and int(self.sequence.currentText()),
        ]

        self.complete = all(mustRequired)
        self.completeSignal.emit(self.complete)


class SigmetCustomContent(BaseSigmetContent, Ui_sigmet_custom.Ui_Editor):

    def __init__(self, phenomena):
        super(SigmetCustomContent, self).__init__(phenomena)
        self.setupUi(self)
        self.bindSignal()
        self.setUpper()

    def message(self):
        text = self.text.toPlainText().upper()
        return text

    def setUpper(self):
        upper = QTextCharFormat()
        upper.setFontCapitalization(QFont.AllUppercase)
        self.text.setCurrentCharFormat(upper)

    def bindSignal(self):
        self.text.textChanged.connect(self.checkComplete)

    def checkComplete(self):
        self.complete = True if self.text.toPlainText() else False
        self.completeSignal.emit(self.complete)


class SigmetGeneralSegment(BaseSegment):

    def __init__(self, typeSegment, mainwindow=None):
        super(SigmetGeneralSegment, self).__init__(typeSegment, mainwindow)
        self.head = SigmetGeneralHead(mainwindow)
        self.content = SigmetGeneralContent(self.head)

        self.initUI()
        self.bindSignal()

    def bindSignal(self):
        self.changeSignal.connect(self.head.updateState)

        self.head.description.currentTextChanged.connect(self.head.setPhenomena)
        self.head.phenomena.currentTextChanged.connect(self.content.setPosition)

    def showEvent(self, event):
        # 手动触发信号
        self.head.phenomena.setCurrentIndex(-1)
        self.head.phenomena.setCurrentIndex(0)

        if conf.value('Monitor/FirApiURL'):
            self.content.manual.hide()
            self.content.latitudeAndLongitudeWidget.hide()

    def clear(self):
        self.head.clear()
        self.content.clear()


class SigmetTyphoonSegment(BaseSegment):

    def __init__(self, typeSegment, mainwindow=None):
        super(SigmetTyphoonSegment, self).__init__(typeSegment, mainwindow)
        self.head = SigmetTyphoonHead(mainwindow)
        self.content = SigmetTyphoonContent(self.head)

        self.initUI()
        self.bindSignal()

    def bindSignal(self):
        self.changeSignal.connect(self.head.updateState)

        self.head.endingTime.textChanged.connect(lambda: self.content.setForecastTime(self.head.endingTime.text()))
        self.head.beginningTime.textEdited.connect(self.content.setForecastPosition)
        self.head.obsTime.textEdited.connect(self.content.setForecastPosition)
        self.content.currentLatitude.textEdited.connect(self.content.setForecastPosition)
        self.content.currentLongitude.textEdited.connect(self.content.setForecastPosition)
        self.content.speed.textEdited.connect(self.content.setForecastPosition)
        self.content.movement.currentTextChanged.connect(self.content.setForecastPosition)


class SigmetCancelSegment(BaseSegment):

    def __init__(self, typeSegment, mainwindow=None):
        super(SigmetCancelSegment, self).__init__(typeSegment, mainwindow)
        self.head = SigmetSimpleHead(mainwindow)
        self.content = SigmetCancelContent(self.head)

        self.initUI()
        self.bindSignal()

    def bindSignal(self):
        self.changeSignal.connect(self.head.updateState)
        self.changeSignal.connect(self.updateState)

        self.content.endingTime.textChanged.connect(self.setEndingTime)
        self.content.sequence.currentTextChanged.connect(self.setValids)

    def setEndingTime(self):
        ending = self.content.endingTime.text()
        self.head.endingTime.setText(ending)

    def updateState(self):
        self.prevs = {}
        sigmets = currentSigmet(tt=self.type.tt)

        for sig in sigmets:
            self.prevs[sig.sequence] = sig.valids

        sequences = [s for s in self.prevs]
        self.content.sequence.clear()
        self.content.sequence.addItems(sequences)

    def setValids(self, sequence):
        valids = self.prevs.get(sequence)
        if valids:
            self.content.beginningTime.setText(valids[0])
            self.content.endingTime.setText(valids[1])

    def clear(self):
        self.head.clear()
        self.content.clear()


class SigmetCustomSegment(BaseSegment):

    def __init__(self, typeSegment, mainwindow=None):
        super(SigmetCustomSegment, self).__init__(typeSegment, mainwindow)
        self.head = SigmetSimpleHead(mainwindow)
        self.content = SigmetCustomContent(self.head)

        self.initUI()
        self.bindSignal()

    def bindSignal(self):
        self.changeSignal.connect(self.head.updateState)
        self.changeSignal.connect(self.updateText)
        self.changeSignal.connect(self.setText)

    def updateText(self):
        self.setText()
        self.setPlaceholder()

    def setPlaceholder(self):
        tips = {
            'WS': 'EMBD TS FCST N OF N2000 TOP FL360 MOV N 25KMH NC',
            'WC': 'TC YAGI OBS AT 1400Z N2300 E11304 CB TOP FL420 WI 300KM OF CENTRE MOV NE 30KMH INTSF\nFCST 1925Z TC CENTRE N2401 E11411',
            'WV': 'VA ERUPTION MT ASHVAL LOC E S1500 E07348 VA CLD OBS AT 1100Z FL310/450\nAPRX 220KM BY 35KM S1500 E07348 - S1530 E07642 MOV ESE 65KMH\nFCST 1700Z VA CLD APRX S1506 E07500 - S1518 E08112 - S1712 E08330 - S1824 E07836',
        }
        tip = tips[self.type.tt]
        self.content.text.setPlaceholderText(tip)

    def setText(self):
        last = db.query(Sigmet).filter(Sigmet.tt == self.type.tt, ~Sigmet.rpt.contains('CNL')).order_by(Sigmet.sent.desc()).first()
        if last:
            fir = conf.value('Message/FIR')
            _, text = last.rpt.split('\n')
            text = text.replace(fir, '')
            text = text.replace('=', '').strip()

            self.content.text.setText(text)
        else:
            self.content.text.clear()

    def clear(self):
        self.head.clear()
        self.content.clear()
