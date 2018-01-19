import json
import datetime

from PyQt5 import QtCore, QtGui, QtWidgets

from tafor.components.ui import Ui_setting, main_rc
from tafor.models import db, User
from tafor import conf, boolean, logger


class SettingDialog(QtWidgets.QDialog, Ui_setting.Ui_Setting):
    """docstring for SettingDialog"""
    def __init__(self, parent=None):
        super(SettingDialog, self).__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(QtGui.QIcon(':/setting.png'))

        # 开机自动启动设置
        self.autoRun = QtCore.QSettings('HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Run', QtCore.QSettings.NativeFormat)

        self.clockTimer = QtCore.QTimer()
        self.clockTimer.timeout.connect(self.checkSerialNumber)
        self.clockTimer.start(1 * 1000)

        self.bindSignal()
        self.updateContract()
        self.load()

        # 禁用项
        self.closeToMinimize.setEnabled(False)
        self.closeToMinimize.setChecked(True)

    def bindSignal(self):
        self.addWeatherButton.clicked.connect(lambda: self.addWeather('weather'))
        self.addWeatherWithIntensityButton.clicked.connect(lambda: self.addWeather('weatherWithIntensity'))

        self.delWeatherButton.clicked.connect(lambda: self.delWeather('weather'))
        self.delWeatherWithIntensityButton.clicked.connect(lambda: self.delWeather('weatherWithIntensity'))

        self.addPersonButton.clicked.connect(self.addPerson)
        self.delPersonButton.clicked.connect(self.delPerson)

        self.resetNumberButton.clicked.connect(self.resetSerialNumber)

        self.buttonBox.button(QtWidgets.QDialogButtonBox.Reset).clicked.connect(self.load)
        self.buttonBox.button(QtWidgets.QDialogButtonBox.Apply).clicked.connect(self.save)
        self.buttonBox.accepted.connect(self.save)

    def checkSerialNumber(self):
        utc = datetime.datetime.utcnow()
        if utc.hour == 0 and utc.minute == 0 and utc.second == 0:
            self.resetSerialNumber()

    def resetSerialNumber(self):
        conf.setValue('communication/other/number', '0')
        self.number.setText('0')
        logger.info('Reset serial number to zero')

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
            self.contractTable.setItem(row, 0,  QtWidgets.QTableWidgetItem(item.name))
            self.contractTable.setItem(row, 1,  QtWidgets.QTableWidgetItem(item.mobile))

        currentContract = self.selectContract.currentText()
        self.selectContract.clear()
        combox_items = [item.name for item in items]
        self.selectContract.addItems(combox_items)
        current_index = self.selectContract.findText(currentContract, QtCore.Qt.MatchFixedString)
        self.selectContract.setCurrentIndex(current_index)


    def save(self):
        import sys

        if self.runOnStart.isChecked():
            self.autoRun.setValue("Tafor.exe", sys.argv[0])
        else:
            self.autoRun.remove("Tafor.exe")

        self.setValue('General/CloseToMinimize', 'closeToMinimize', 'bool')
        self.setValue('General/Debug', 'debugMode', 'bool')

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
        self.setValue('Communication/Number', 'number')

        self.setValue('Communication/RequestAddress', 'requestAddress')
        self.setValue('Communication/UserAddress', 'userAddress')
        self.setValue('Communication/TAFAddress', 'tafAddress', 'plaintext')
        self.setValue('Communication/SIGMETAddress', 'sigmetAddress', 'plaintext')
        self.setValue('Communication/AIRMETAddress', 'airmetAddress', 'plaintext')
        self.setValue('Communication/TrendAddress', 'trendAddress', 'plaintext')

        self.setValue('Monitor/WebApi', 'webApi', 'bool')
        self.setValue('Monitor/WebApiURL', 'webApiURL')

        self.setValue('Monitor/WarnTAF', 'warnTAF', 'bool')
        self.setValue('Monitor/WarnTAFTime', 'warnTAFTime')
        self.setValue('Monitor/WarnTAFVolume', 'warnTAFVolume', 'slider')

        self.setValue('Monitor/RemindTAF', 'remindTAF', 'bool')
        self.setValue('Monitor/RemindTAFVolume', 'remindTAFVolume', 'slider')
        self.setValue('Monitor/RemindTrend', 'remindTrend', 'bool')
        self.setValue('Monitor/RemindTrendVolume', 'remindTrendVolume', 'slider')
        self.setValue('Monitor/RemindSIGMET', 'remindSIGMET', 'bool')
        self.setValue('Monitor/RemindSIGMETVolume', 'remindSIGMETVolume', 'slider')

        self.setValue('Monitor/CallServiceURL', 'callServiceURL')
        self.setValue('Monitor/CallServiceToken', 'callServiceToken')

        self.setValue('Monitor/SelectedMobile', 'selectContract', 'mobile')

    def load(self):
        self.runOnStart.setChecked(self.autoRun.contains("Tafor.exe"))

        self.loadValue('General/CloseToMinimize', 'closeToMinimize', 'bool')
        self.loadValue('General/Debug', 'debugMode', 'bool')

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
        self.loadValue('Communication/Number', 'number')

        self.loadValue('Communication/RequestAddress', 'requestAddress')
        self.loadValue('Communication/UserAddress', 'userAddress')
        self.loadValue('Communication/TAFAddress', 'tafAddress', 'plaintext')
        self.loadValue('Communication/SIGMETAddress', 'sigmetAddress', 'plaintext')
        self.loadValue('Communication/AIRMETAddress', 'airmetAddress', 'plaintext')
        self.loadValue('Communication/TrendAddress', 'trendAddress', 'plaintext')

        self.loadValue('Monitor/WebApi', 'webApi', 'bool')
        self.loadValue('Monitor/WebApiURL', 'webApiURL')

        self.loadValue('Monitor/WarnTAF', 'warnTAF', 'bool')
        self.loadValue('Monitor/WarnTAFTime', 'warnTAFTime')
        self.loadValue('Monitor/WarnTAFVolume', 'warnTAFVolume', 'slider')

        self.loadValue('Monitor/RemindTAF', 'remindTAF', 'bool')
        self.loadValue('Monitor/RemindTAFVolume', 'remindTAFVolume', 'slider')
        self.loadValue('Monitor/RemindTrend', 'remindTrend', 'bool')
        self.loadValue('Monitor/RemindTrendVolume', 'remindTrendVolume', 'slider')
        self.loadValue('Monitor/RemindSIGMET', 'remindSIGMET', 'bool')
        self.loadValue('Monitor/RemindSIGMETVolume', 'remindSIGMETVolume', 'slider')

        self.loadValue('Monitor/CallServiceURL', 'callServiceURL')
        self.loadValue('Monitor/CallServiceToken', 'callServiceToken')

        self.loadValue('Monitor/SelectedMobile', 'selectContract', 'mobile')

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
            index = target.findText(val, QtCore.Qt.MatchFixedString)
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
                index = target.findText(person.name, QtCore.Qt.MatchFixedString)
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
            items = [item.text() for item in target.findItems('', QtCore.Qt.MatchContains)]
            val = json.dumps(items)

        if mold == 'mobile':
            name = target.currentText()
            person = db.query(User).filter_by(name=name).first()
            val = person.mobile if person else ''

        conf.setValue(path, val)

