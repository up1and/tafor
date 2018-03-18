import json
import datetime

from PyQt5.QtGui import QIcon, QIntValidator
from PyQt5.QtCore import QCoreApplication, QSettings, QTimer, Qt
from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QTableWidgetItem

from tafor.components.ui import Ui_setting, main_rc
from tafor.models import db, User
from tafor import conf, boolean, logger


class SettingDialog(QDialog, Ui_setting.Ui_Settings):

    def __init__(self, parent=None):
        super(SettingDialog, self).__init__(parent)
        self.parent = parent
        self.setupUi(self)
        self.setWindowIcon(QIcon(':/setting.png'))

        # 开机自动启动设置
        self.autoRun = QSettings('HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Run', QSettings.NativeFormat)

        self.clockTimer = QTimer()
        self.clockTimer.timeout.connect(self.checkSerialNumber)
        self.clockTimer.start(1 * 1000)

        self.bindSignal()
        self.setValidator()
        self.updateContract()
        self.load()

        # 禁用项
        self.closeToMinimize.setEnabled(False)
        self.closeToMinimize.setChecked(True)

        self.buttonBox.button(QDialogButtonBox.Ok).setText(QCoreApplication.translate('Settings', 'OK'))
        self.buttonBox.button(QDialogButtonBox.Apply).setText(QCoreApplication.translate('Settings', 'Apply'))
        self.buttonBox.button(QDialogButtonBox.Cancel).setText(QCoreApplication.translate('Settings', 'Cancel'))

    def bindSignal(self):
        self.addWeatherButton.clicked.connect(lambda: self.addWeather('weather'))
        self.addWeatherWithIntensityButton.clicked.connect(lambda: self.addWeather('weatherWithIntensity'))

        self.delWeatherButton.clicked.connect(lambda: self.delWeather('weather'))
        self.delWeatherWithIntensityButton.clicked.connect(lambda: self.delWeather('weatherWithIntensity'))

        self.addPersonButton.clicked.connect(self.addPerson)
        self.delPersonButton.clicked.connect(self.delPerson)

        self.resetNumberButton.clicked.connect(self.resetSerialNumber)

        self.callUpButton.clicked.connect(self.testCallUp)

        # self.buttonBox.button(QDialogButtonBox.Reset).clicked.connect(self.load)
        self.buttonBox.button(QDialogButtonBox.Apply).clicked.connect(self.save)
        self.buttonBox.button(QDialogButtonBox.Apply).clicked.connect(self.parent.updateGui)
        self.buttonBox.accepted.connect(self.save)
        self.buttonBox.accepted.connect(self.parent.updateGui)

    def setValidator(self):
        self.baudrate.setValidator(QIntValidator(self.baudrate))
        self.channelSequenceNumber.setValidator(QIntValidator(self.channelSequenceNumber))
        self.maxSendAddress.setValidator(QIntValidator(self.maxSendAddress))
        self.maxLineChar.setValidator(QIntValidator(self.maxLineChar))
        self.warnTafTime.setValidator(QIntValidator(self.warnTafTime))

    def checkSerialNumber(self):
        utc = datetime.datetime.utcnow()
        if utc.hour == 0 and utc.minute == 0 and utc.second == 0:
            self.resetSerialNumber()

    def resetSerialNumber(self):
        conf.setValue('Communication/ChannelSequenceNumber', '1')
        self.channelSequenceNumber.setText('1')
        logger.info('Reset channel sequence number to one')

    def loadSerialNumber(self):
        self.loadValue('Communication/ChannelSequenceNumber', 'channelSequenceNumber')

    def addWeather(self, weather):
        line = getattr(self, weather)
        if line.text():
            getattr(self, weather + 'List').addItem(line.text())
            line.clear()

    def delWeather(self, weather):
        target = getattr(self, weather + 'List')
        target.takeItem(target.currentRow())

    def addPerson(self):
        name = self.personName.text()
        number = self.personMobile.text()
        if name and number:
            person = User(name, number)
            db.add(person)
            db.commit()

        self.updateContract()

    def delPerson(self):
        row = self.contractTable.currentRow()
        name = self.contractTable.item(row, 0).text()

        person = db.query(User).filter_by(name=name).first()
        db.delete(person)
        db.commit()

        self.updateContract()

    def updateContract(self):
        items = db.query(User).all()
        self.contractTable.setRowCount(len(items))

        for row, item in enumerate(items):
            self.contractTable.setItem(row, 0,  QTableWidgetItem(item.name))
            self.contractTable.setItem(row, 1,  QTableWidgetItem(item.mobile))

        self.selectedContract.clear()
        options = [item.name for item in items]
        options.insert(0, QCoreApplication.translate('MainWindow', 'None'))
        self.selectedContract.addItems(options)

    def updateSoundVolume(self):
        self.parent.ringSound.setVolume(conf.value('Monitor/RemindTAFVolume'))
        self.parent.alarmSound.setVolume(conf.value('Monitor/WarnTAFVolume'))
        self.parent.trendSound.setVolume(conf.value('Monitor/RemindTrendVolume'))
        self.parent.sigmetSound.setVolume(conf.value('Monitor/RemindSIGMETVolume'))

    def testCallUp(self):
        self.parent.dialer(test=True)

    def save(self):
        import sys

        if self.runOnStart.isChecked():
            self.autoRun.setValue('Tafor.exe', sys.argv[0])
        else:
            self.autoRun.remove('Tafor.exe')

        self.setValue('General/CloseToMinimize', 'closeToMinimize', 'bool')
        self.setValue('General/Debug', 'debugMode', 'bool')
        self.setValue('General/AlwaysShowEditor', 'alwaysShowEditor', 'bool')

        self.setValue('Validator/VisHas5000', 'visHas5000', 'bool')
        self.setValue('Validator/CloudHeightHas450', 'cloudHeightHas450', 'bool')

        self.setValue('Message/ICAO', 'icao')
        self.setValue('Message/Area', 'area')
        self.setValue('Message/FIR', 'fir')
        self.setValue('Message/TrendSign', 'trendSign')
        self.setValue('Message/Weather', 'weatherList', 'list')
        self.setValue('Message/WeatherWithIntensity', 'weatherWithIntensityList', 'list')

        self.setValue('Communication/SerialPort', 'port')
        self.setValue('Communication/SerialBaudrate', 'baudrate')
        self.setValue('Communication/SerialParity', 'parity', 'combox')
        self.setValue('Communication/SerialBytesize', 'bytesize', 'combox')
        self.setValue('Communication/SerialStopbits', 'stopbits', 'combox')

        self.setValue('Communication/Channel', 'channel')
        self.setValue('Communication/ChannelSequenceNumber', 'channelSequenceNumber')
        self.setValue('Communication/MaxLineChar', 'maxLineChar')
        self.setValue('Communication/MaxSendAddress', 'maxSendAddress')

        self.setValue('Communication/OriginatorAddress', 'originatorAddress')
        self.setValue('Communication/TAFAddress', 'tafAddress', 'plaintext')
        self.setValue('Communication/SIGMETAddress', 'sigmetAddress', 'plaintext')
        self.setValue('Communication/TrendAddress', 'trendAddress', 'plaintext')

        self.setValue('Monitor/WebApiURL', 'webApiURL')

        # self.setValue('Monitor/WarnTAF', 'warnTAF', 'bool')
        self.setValue('Monitor/WarnTAFTime', 'warnTafTime')
        self.setValue('Monitor/WarnTAFVolume', 'warnTafVolume', 'slider')

        self.setValue('Monitor/RemindTAF', 'remindTaf', 'bool')
        self.setValue('Monitor/RemindTAFVolume', 'remindTafVolume', 'slider')
        self.setValue('Monitor/RemindTrend', 'remindTrend', 'bool')
        self.setValue('Monitor/RemindTrendVolume', 'remindTrendVolume', 'slider')
        self.setValue('Monitor/RemindSIGMET', 'remindSigmet', 'bool')
        self.setValue('Monitor/RemindSIGMETVolume', 'remindSigmetVolume', 'slider')

        self.setValue('Monitor/CallServiceURL', 'callServiceURL')
        self.setValue('Monitor/CallServiceToken', 'callServiceToken')

        self.setValue('Monitor/SelectedMobile', 'selectedContract', 'mobile')

        self.updateSoundVolume()

    def load(self):
        self.runOnStart.setChecked(self.autoRun.contains('Tafor.exe'))

        self.loadValue('General/CloseToMinimize', 'closeToMinimize', 'bool')
        self.loadValue('General/Debug', 'debugMode', 'bool')
        self.loadValue('General/AlwaysShowEditor', 'alwaysShowEditor', 'bool')

        self.loadValue('Validator/VisHas5000', 'visHas5000', 'bool')
        self.loadValue('Validator/CloudHeightHas450', 'cloudHeightHas450', 'bool')

        self.loadValue('Message/ICAO', 'icao')
        self.loadValue('Message/Area', 'area')
        self.loadValue('Message/FIR', 'fir')
        self.loadValue('Message/TrendSign', 'trendSign')
        self.loadValue('Message/Weather', 'weatherList', 'list')
        self.loadValue('Message/WeatherWithIntensity', 'weatherWithIntensityList', 'list')

        self.loadValue('Communication/SerialPort', 'port')
        self.loadValue('Communication/SerialBaudrate', 'baudrate')
        self.loadValue('Communication/SerialParity', 'parity', 'combox')
        self.loadValue('Communication/SerialBytesize', 'bytesize', 'combox')
        self.loadValue('Communication/SerialStopbits', 'stopbits', 'combox')

        self.loadValue('Communication/Channel', 'channel')
        self.loadValue('Communication/ChannelSequenceNumber', 'channelSequenceNumber')
        self.loadValue('Communication/MaxLineChar', 'maxLineChar')
        self.loadValue('Communication/MaxSendAddress', 'maxSendAddress')

        self.loadValue('Communication/OriginatorAddress', 'originatorAddress')
        self.loadValue('Communication/TAFAddress', 'tafAddress')
        self.loadValue('Communication/SIGMETAddress', 'sigmetAddress')
        self.loadValue('Communication/TrendAddress', 'trendAddress')

        self.loadValue('Monitor/WebApiURL', 'webApiURL')

        self.loadValue('Monitor/WarnTAFTime', 'warnTafTime')
        self.loadValue('Monitor/WarnTAFVolume', 'warnTafVolume', 'slider')

        self.loadValue('Monitor/RemindTAF', 'remindTaf', 'bool')
        self.loadValue('Monitor/RemindTAFVolume', 'remindTafVolume', 'slider')
        self.loadValue('Monitor/RemindTrend', 'remindTrend', 'bool')
        self.loadValue('Monitor/RemindTrendVolume', 'remindTrendVolume', 'slider')
        self.loadValue('Monitor/RemindSIGMET', 'remindSigmet', 'bool')
        self.loadValue('Monitor/RemindSIGMETVolume', 'remindSigmetVolume', 'slider')

        self.loadValue('Monitor/CallServiceURL', 'callServiceURL')
        self.loadValue('Monitor/CallServiceToken', 'callServiceToken')

        self.loadValue('Monitor/SelectedMobile', 'selectedContract', 'mobile')

    def loadValue(self, path, target, mold='text'):

        val = conf.value(path)
        target = getattr(self, target)

        if val is None:
            return 0

        if mold == 'text':
            target.setText(val)

        if mold == 'bool':
            val = boolean(val)
            target.setChecked(val)

        if mold == 'combox':
            index = target.findText(val, Qt.MatchFixedString)
            target.setCurrentIndex(index)

        if mold == 'slider':
            target.setValue(int(val))

        if mold == 'list':
            try:
                items = json.loads(val)
                target.addItems(items)
            except (ValueError, TypeError):
                pass

        if mold == 'mobile':
            person = db.query(User).filter_by(mobile=val).first()
            if person:
                index = target.findText(person.name, Qt.MatchFixedString)
                target.setCurrentIndex(index)

    def setValue(self, path, target, mold='text'):
        target = getattr(self, target)

        if mold == 'text':
            val = target.text()

        if mold == 'bool':
            val = target.isChecked()

        if mold == 'combox':
            val = target.currentText()

        if mold == 'slider':
            val = target.value()

        if mold == 'plaintext':
            val = target.toPlainText()

        if mold == 'list':
            items = [item.text() for item in target.findItems('', Qt.MatchContains)]
            val = json.dumps(items)

        if mold == 'mobile':
            name = target.currentText()
            person = db.query(User).filter_by(name=name).first()
            val = person.mobile if person else ''

        conf.setValue(path, val)

