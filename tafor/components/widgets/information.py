import datetime

from PyQt5.QtGui import QRegExpValidator, QIntValidator
from PyQt5.QtCore import Qt, QRegExp, pyqtSignal
from PyQt5.QtWidgets import QWidget, QVBoxLayout

from tafor import conf, logger
from tafor.utils import Pattern
from tafor.components.widgets.forecast import SegmentMixin
from tafor.components.ui import (Ui_sigmet_type, Ui_sigmet_general, Ui_sigmet_phenomena, 
	Ui_sigmet_typhoon, Ui_sigmet_custom)


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
        self.time = datetime.datetime.utcnow()
        validTime = self.time + datetime.timedelta(minutes=15)
        self.valid.setText(validTime.strftime('%d%H%M'))

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


class BaseSigmetContent(QWidget, SegmentMixin):
    completeSignal = pyqtSignal(bool)

    def __init__(self):
        super(BaseSigmetContent, self).__init__()
        self.complete = False
        self.rules = Pattern()


class BaseSegment(QWidget):

    def __init__(self):
        super(BaseSegment, self).__init__()

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.phenomena)
        layout.addWidget(self.content)
        self.setLayout(layout)

    def head(self):
        area = conf.value('Message/Area') or ''
        icao = conf.value('Message/ICAO')
        time = self.time.strftime('%d%H%M')
        tt = self.tt

        messages = [tt + area, icao, time]
        return ' '.join(filter(None, messages))

    def message(self):
        content = ' '.join([self.phenomena.message(), self.content.message()])
        text = '\n'.join([self.phenomena.head(), content]) + '='
        return text

    def clear(self):
        self.phenomena.clear()
        self.content.clear()


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
        self.movement.currentTextChanged.connect(self.setSpeed)

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
            text = 'MOV {movement} {speed} KMH'.format(
                    movement=movement,
                    speed=self.speed.text()
                )

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


class SigmetCustomContent(BaseSigmetContent, Ui_sigmet_custom.Ui_Editor):

    def __init__(self):
        super(SigmetCustomContent, self).__init__()
        self.setupUi(self)

    def message(self):
        fir = conf.value('Message/FIR')
        text = ' '.join([fir, self.custom.toPlainText()])
        return text


class SigmetGeneralSegment(BaseSegment):

    def __init__(self):
        super(SigmetGeneralSegment, self).__init__()
        self.phenomena = SigmetGeneralPhenomena()
        self.content = SigmetGeneralContent()
        self.tt = 'WC'

        self.initUI()
        self.bindSignal()

    def bindSignal(self):
        self.phenomena.description.currentTextChanged.connect(self.phenomena.setPhenomena)
        self.phenomena.phenomena.currentTextChanged.connect(self.content.setPosition)

    def clear(self):
        self.phenomena.clear()
        self.content.clear()


class SigmetTyphoonSegment(BaseSegment):

    def __init__(self):
        super(SigmetTyphoonSegment, self).__init__()
        self.phenomena = SigmetTyphoonPhenomena()
        self.content = SigmetTyphoonContent()
        self.tt = 'WC'

        self.initUI()
        self.bindSignal()

    def bindSignal(self):
        pass


class SigmetCustomSegment(BaseSegment):

    def __init__(self):
        super(SigmetCustomSegment, self).__init__()
        self.phenomena = SigmetCustomPhenomena()
        self.content = SigmetCustomContent()
        self.tt = 'WS'

        self.initUI()
        self.bindSignal()

    def bindSignal(self):
        pass
