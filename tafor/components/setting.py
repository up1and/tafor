import os
import json
import datetime

from PyQt5.QtGui import QIcon, QIntValidator
from PyQt5.QtCore import QCoreApplication, QSettings, QTimer, Qt
from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QTableWidgetItem, QFileDialog

from tafor import conf, logger
from tafor.utils import boolean
from tafor.models import db, User
from tafor.components.ui import Ui_setting, main_rc


_options = [
    # 通用设置
    ('General/WindowsStyle', 'windowsStyle', 'combox'),
    ('General/InterfaceScaling', 'interfaceScaling', 'comboxindex'),
    ('General/InternationalAirport', 'internationalAirport', 'bool'),
    ('General/ValidityPeriod', 'validityPeriod', 'comboxindex'),
    ('General/CloseToMinimize', 'closeToMinimize', 'bool'),
    ('General/Debug', 'debugMode', 'bool'),
    ('General/AlwaysShowEditor', 'alwaysShowEditor', 'bool'),
    ('General/AutoComletionGroupTime', 'autoComletionGroupTime', 'bool'),
    # 验证选项
    ('Validator/VisHas5000', 'visHas5000', 'bool'),
    ('Validator/CloudHeightHas450', 'cloudHeightHas450', 'bool'),
    ('Validator/WeakPrecipitationVerification', 'weakPrecipitationVerification', 'bool'),
    # 报文字符
    ('Message/ICAO', 'icao', 'text'),
    ('Message/Area', 'area', 'text'),
    ('Message/FIR', 'fir', 'text'),
    ('Message/TrendSign', 'trendSign', 'text'),
    ('Message/Weather', 'weatherList', 'list'),
    ('Message/WeatherWithIntensity', 'weatherWithIntensityList', 'list'),
    # 串口设置
    ('Communication/SerialPort', 'port', 'text'),
    ('Communication/SerialBaudrate', 'baudrate', 'text'),
    ('Communication/SerialParity', 'parity', 'combox'),
    ('Communication/SerialBytesize', 'bytesize', 'combox'),
    ('Communication/SerialStopbits', 'stopbits', 'combox'),
    # AFTN 配置
    ('Communication/Channel', 'channel', 'text'),
    ('Communication/ChannelSequenceNumber', 'channelSequenceNumber', 'text'),
    ('Communication/MaxLineChar', 'maxLineChar', 'text'),
    ('Communication/MaxSendAddress', 'maxSendAddress', 'text'),
    ('Communication/OriginatorAddress', 'originatorAddress', 'text'),
    ('Communication/TAFAddress', 'tafAddress', 'plaintext'),
    ('Communication/AIRMETAddress', 'airmetAddress', 'plaintext'),
    ('Communication/SIGMETAddress', 'sigmetAddress', 'plaintext'),
    ('Communication/TrendAddress', 'trendAddress', 'plaintext'),
    # 数据源
    ('Monitor/WebApiURL', 'webApiURL', 'text'),
    ('Monitor/FirApiURL', 'firApiURL', 'text'),
    ('General/FirCanvasSize', 'firCanvasSize', 'slider'),
    # TAF 报文迟发告警
    ('Monitor/WarnTAFTime', 'warnTafTime', 'text'),
    ('Monitor/WarnTAFVolume', 'warnTafVolume', 'slider'),
    # 报文发送提醒
    ('Monitor/RemindTAF', 'remindTaf', 'bool'),
    ('Monitor/RemindTAFVolume', 'remindTafVolume', 'slider'),
    ('Monitor/RemindTrend', 'remindTrend', 'bool'),
    ('Monitor/RemindTrendVolume', 'remindTrendVolume', 'slider'),
    ('Monitor/RemindSIGMET', 'remindSigmet', 'bool'),
    ('Monitor/RemindSIGMETVolume', 'remindSigmetVolume', 'slider'),
    # 电话服务
    ('Monitor/CallServiceURL', 'callServiceURL', 'text'),
    ('Monitor/CallServiceToken', 'callServiceToken', 'text'),
    ('Monitor/SelectedMobile', 'selectedContract', 'mobile'),
]


def isConfigured(reportType='TAF'):
    """检查发布不同类型报文基础配置是否完成"""
    serial = ['Communication/SerialPort', 'Communication/SerialBaudrate', 'Communication/SerialParity',
            'Communication/SerialBytesize', 'Communication/SerialStopbits']
    aftn = ['Communication/Channel', 'Communication/ChannelSequenceNumber', 'Communication/MaxLineChar',
            'Communication/MaxSendAddress', 'Communication/OriginatorAddress']
    taf = ['Message/ICAO', 'Message/Area', 'Communication/TAFAddress']
    trend = ['Message/TrendSign', 'Communication/TrendAddress']
    sigmet = ['Message/ICAO', 'Message/FIR', 'Message/Area', 'Communication/SIGMETAddress', 'Communication/AIRMETAddress']

    options = serial + aftn
    if reportType == 'TAF':
        options += taf

    if reportType == 'Trend':
        options += trend

    if reportType == 'SIGMET':
        options += sigmet

    values = [conf.value(path) for path in options]
    return all(values)

def loadConf(filename):
    with open(filename) as file:
        data = json.load(file)

    for path, val in data.items():
        conf.setValue(path, val)

def saveConf(filename, options=None):
    options = _options if options is None else options
    paths = [option[0] for option in options]
    data = {path: conf.value(path) for path in paths}
    with open(filename, 'w') as file:
        json.dump(data, file)


class SettingDialog(QDialog, Ui_setting.Ui_Settings):
    """设置窗口"""

    def __init__(self, parent=None):
        super(SettingDialog, self).__init__(parent)
        self.parent = parent
        self.setupUi(self)
        self.setWindowIcon(QIcon(':/setting.png'))

        # 开机自动启动设置
        self.autoRun = QSettings('HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Run', QSettings.NativeFormat)

        self.clockTimer = QTimer()
        self.clockTimer.timeout.connect(self.checkChannelNumber)
        self.clockTimer.start(1 * 1000)

        # 禁用项
        self.closeToMinimize.setEnabled(False)
        self.closeToMinimize.setChecked(True)

        self.contractTable.setColumnWidth(0, 210)

        self.buttonBox.button(QDialogButtonBox.Ok).setText(QCoreApplication.translate('Settings', 'OK'))
        self.buttonBox.button(QDialogButtonBox.Apply).setText(QCoreApplication.translate('Settings', 'Apply'))
        self.buttonBox.button(QDialogButtonBox.Cancel).setText(QCoreApplication.translate('Settings', 'Cancel'))

        if not boolean(conf.value('General/Sigmet')):
            self.fir.hide()
            self.firLabel.hide()
            self.firApiURL.hide()
            self.firApiLabel.hide()
            self.firCanvasSize.hide()
            self.firCanvasSizeLabel.hide()
            self.remindSigmet.hide()
            self.remindSigmetVolume.hide()
            self.addressTab.removeTab(3)
            self.addressTab.removeTab(3)

        self.bindSignal()
        self.setValidator()
        self.setValidityPeriod()
        self.updateContract()
        self.load()

    def bindSignal(self):
        """绑定信号"""
        self.addWeatherButton.clicked.connect(lambda: self.addWeather('weather'))
        self.addWeatherWithIntensityButton.clicked.connect(lambda: self.addWeather('weatherWithIntensity'))

        self.delWeatherButton.clicked.connect(lambda: self.delWeather('weather'))
        self.delWeatherWithIntensityButton.clicked.connect(lambda: self.delWeather('weatherWithIntensity'))

        self.addPersonButton.clicked.connect(self.addPerson)
        self.delPersonButton.clicked.connect(self.delPerson)

        self.resetNumberButton.clicked.connect(self.resetChannelNumber)

        self.callUpButton.clicked.connect(self.testCallUp)

        self.internationalAirport.clicked.connect(self.setValidityPeriod)

        self.importBrowseButton.clicked.connect(lambda: self.openFile(self.importPath))
        self.exportBrowseButton.clicked.connect(lambda: self.openDirectory(self.exportPath))
        self.importButton.clicked.connect(self.importConf)
        self.exportButton.clicked.connect(self.exportConf)

        self.buttonBox.accepted.connect(self.save)
        self.buttonBox.accepted.connect(self.parent.updateGui)

    def setValidator(self):
        """设置验证器"""
        self.baudrate.setValidator(QIntValidator(self.baudrate))
        self.channelSequenceNumber.setValidator(QIntValidator(self.channelSequenceNumber))
        self.maxSendAddress.setValidator(QIntValidator(self.maxSendAddress))
        self.maxLineChar.setValidator(QIntValidator(self.maxLineChar))
        self.warnTafTime.setValidator(QIntValidator(self.warnTafTime))

    def setValidityPeriod(self, checked=None):
        checked = boolean(conf.value('General/InternationalAirport')) if checked is None else checked
        self.validityPeriod.setEnabled(checked)

    def checkChannelNumber(self):
        """检查是否是世界时日界，如果是重置流水号"""
        utc = datetime.datetime.utcnow()
        if utc.hour == 0 and utc.minute == 0 and utc.second == 0:
            self.resetChannelNumber()

    def resetChannelNumber(self):
        """重置流水号"""
        conf.setValue('Communication/ChannelSequenceNumber', '1')
        self.channelSequenceNumber.setText('1')
        logger.info('Reset channel sequence number to one')

    def loadSerialNumber(self):
        """单独载入流水号"""
        self.loadValue('Communication/ChannelSequenceNumber', 'channelSequenceNumber')

    def addWeather(self, weather):
        """添加天气现象"""
        line = getattr(self, weather)
        if line.text():
            getattr(self, weather + 'List').addItem(line.text())
            line.clear()

    def delWeather(self, weather):
        """删除天气现象"""
        option = getattr(self, weather + 'List')
        option.takeItem(option.currentRow())

    def addPerson(self):
        """添加联系人"""
        name = self.personName.text()
        number = self.personMobile.text()
        if name and number:
            person = User(name, number)
            db.add(person)
            db.commit()

        self.updateContract()

    def delPerson(self):
        """删除联系人"""
        row = self.contractTable.currentRow()
        name = self.contractTable.item(row, 0).text()

        person = db.query(User).filter_by(name=name).first()
        db.delete(person)
        db.commit()

        self.updateContract()

    def updateContract(self):
        """更新联系人列表"""
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
        """更新提醒声音音量"""
        self.parent.ringSound.setVolume(conf.value('Monitor/RemindTAFVolume'))
        self.parent.alarmSound.setVolume(conf.value('Monitor/WarnTAFVolume'))
        self.parent.trendSound.setVolume(conf.value('Monitor/RemindTrendVolume'))
        self.parent.sigmetSound.setVolume(conf.value('Monitor/RemindSIGMETVolume'))

    def testCallUp(self):
        """手动测试电话拨号"""
        self.parent.dialer(test=True)

    def save(self):
        """保存设置"""
        import sys

        if self.runOnStart.isChecked():
            self.autoRun.setValue('Tafor', sys.argv[0])
        else:
            self.autoRun.remove('Tafor')

        if conf.value('General/FirCanvasSize') != self.firCanvasSize.value():
            self.parent.sigmetEditor.close()

        for path, option, category in _options:
            self.setValue(path, option, category)

        self.updateSoundVolume()

    def load(self):
        """载入设置"""
        self.runOnStart.setChecked(self.autoRun.contains('Tafor'))

        for path, option, category in _options:
            self.loadValue(path, option, category)

    def loadValue(self, path, option, category='text'):
        val = conf.value(path)
        option = getattr(self, option)

        if val is None:
            return 0

        if category in ['text', 'plaintext']:
            option.setText(val)

        if category == 'bool':
            val = boolean(val)
            option.setChecked(val)

        if category == 'combox':
            index = option.findText(val, Qt.MatchFixedString)
            option.setCurrentIndex(index)

        if category == 'comboxindex':
            option.setCurrentIndex(int(val))

        if category == 'slider':
            option.setValue(int(val))

        if category == 'list':
            try:
                items = json.loads(val)
                option.clear()
                option.addItems(items)
            except (ValueError, TypeError):
                pass

        if category == 'mobile':
            person = db.query(User).filter_by(mobile=val).first()
            if person:
                index = option.findText(person.name, Qt.MatchFixedString)
                option.setCurrentIndex(index)

    def setValue(self, path, option, category='text'):
        option = getattr(self, option)

        if category == 'text':
            val = option.text()

        if category == 'bool':
            val = option.isChecked()

        if category == 'combox':
            val = option.currentText()

        if category == 'comboxindex':
            val = option.currentIndex()

        if category == 'slider':
            val = option.value()

        if category == 'plaintext':
            val = option.toPlainText()

        if category == 'list':
            items = [option.item(i).text() for i in range(option.count())]
            val = json.dumps(items)

        if category == 'mobile':
            name = option.currentText()
            person = db.query(User).filter_by(name=name).first()
            val = person.mobile if person else ''

        conf.setValue(path, val)

    def exportConf(self):
        filename = self.exportPath.text()
        try:
            saveConf(filename)

        except Exception as e:
            logger.error(e)

        else:
            self.parent.statusBar.showMessage(QCoreApplication.translate('Settings', 'Configuration has been exported'), 5000)

    def importConf(self):
        filename = self.importPath.text()
        try:
            loadConf(filename)

        except Exception as e:
            logger.error(e)

        else:
            self.load()
            self.parent.statusBar.showMessage(QCoreApplication.translate('Settings', 'Configuration has been imported'), 5000)

    def openFile(self, receiver):
        title = QCoreApplication.translate('Settings', 'Open Configuration File')
        filename, _ = QFileDialog.getOpenFileName(self, title, '.', '(*.json)')
        receiver.setText(filename)

    def openDirectory(self, receiver):
        title = QCoreApplication.translate('Settings', 'Open Directory')
        path = str(QFileDialog.getExistingDirectory(self, title))
        filename = os.path.join(path, 'default.json').replace('\\', '/') if path else path
        receiver.setText(filename)
