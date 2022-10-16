import os
import sys
import json
import secrets
import datetime

from PyQt5.QtGui import QIcon, QIntValidator, QTextCursor
from PyQt5.QtCore import QCoreApplication, QStandardPaths, QSettings, QTimer, Qt, pyqtSignal
from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QFileDialog, QMessageBox, QApplication

from tafor import conf, logger
from tafor.states import context
from tafor.utils import boolean, ftpComm, ipAddress
from tafor.styles import tabStyle
from tafor.components.ui import Ui_setting, main_rc


baseOptions = [
    # 通用设置
    ('General/WindowsStyle', 'windowsStyle', 'combox'),
    ('General/CommunicationProtocol', 'communicationProtocol', 'combox'),
    ('General/InterfaceScaling', 'interfaceScaling', 'comboxindex'),
    ('General/TAFSpec', 'tafSpecification', 'comboxindex'),
    ('General/CloseToMinimize', 'closeToMinimize', 'bool'),
    ('General/Debug', 'debugMode', 'bool'),
    ('General/AutoComletionGroupTime', 'autoComletionGroupTime', 'bool'),
    # 验证选项
    ('Validation/VisHas5000', 'visHas5000', 'bool'),
    ('Validation/CloudHeightHas450', 'cloudHeightHas450', 'bool'),
    ('Validation/WeakPrecipitationVerification', 'weakPrecipitationVerification', 'bool'),
    # 报文字符
    ('Message/Airport', 'airport', 'text'),
    ('Message/BulletinNumber', 'bulletinNumber', 'text'),
    ('Message/TrendIdentifier', 'trendIdentifier', 'text'),
    ('Message/Weather', 'weatherList', 'list'),
    ('Message/WeatherWithIntensity', 'weatherWithIntensityList', 'list'),
    # 串口设置
    ('Communication/SerialPort', 'port', 'text'),
    ('Communication/SerialBaudrate', 'baudrate', 'text'),
    ('Communication/SerialParity', 'parity', 'combox'),
    ('Communication/SerialBytesize', 'bytesize', 'combox'),
    ('Communication/SerialStopbits', 'stopbits', 'combox'),
    # AFTN 设置
    ('Communication/Channel', 'channel', 'text'),
    ('Communication/ChannelSequenceNumber', 'channelSequenceNumber', 'text'),
    ('Communication/ChannelSequenceLength', 'channelSequenceLength', 'combox'),
    ('Communication/MaxSendAddress', 'maxSendAddress', 'text'),
    ('Communication/OriginatorAddress', 'originatorAddress', 'text'),
    ('Communication/TAFAddress', 'tafAddress', 'plaintext'),
    ('Communication/TrendAddress', 'trendAddress', 'plaintext'),
    # FTP 设置
    ('Communication/FTPHost', 'ftpHost', 'text'),
    # 接口
    ('Interface/RPC', 'serviceGroup', 'bool'),
    ('Interface/MessageURL', 'messageURL', 'text'),
    # TAF 报文迟发告警
    ('Monitor/DelayMinutes', 'delayMinutes', 'text'),
    ('Monitor/AlarmVolume', 'alarmVolume', 'slider'),
    # 报文发送提醒
    ('Monitor/RemindTAF', 'remindTaf', 'bool'),
    ('Monitor/TAFVolume', 'tafVolume', 'slider'),
    ('Monitor/RemindTrend', 'remindTrend', 'bool'),
    ('Monitor/TrendVolume', 'trendVolume', 'slider'),
]

sigmetOptions = [
    # 报文字符
    ('Message/FIRName', 'firName', 'text'),
    # AFTN 配置
    ('Communication/AIRMETAddress', 'airmetAddress', 'plaintext'),
    ('Communication/SIGMETAddress', 'sigmetAddress', 'plaintext'),
    # 接口
    ('Interface/LayerURL', 'layerURL', 'text'),
    # 报文发送提醒
    ('Monitor/RemindSIGMET', 'remindSigmet', 'bool'),
    ('Monitor/SIGMETVolume', 'sigmetVolume', 'slider'),
    # 图层
    ('Layer/Projection', 'projection', 'text'),
    ('Layer/FIRBoundary', 'firBoundary', 'plaintext'),
]


def setupOptions(options):
    configs = {}
    for path, option, category in options:
        configs[path] = {
            'object': option,
            'type': category
        }
    return configs

def isConfigured(reportType='TAF'):
    """检查发布不同类型报文基础配置是否完成"""
    serial = ['Communication/SerialPort', 'Communication/SerialBaudrate', 'Communication/SerialParity',
            'Communication/SerialBytesize', 'Communication/SerialStopbits']
    aftn = ['Communication/Channel', 'Communication/ChannelSequenceNumber', 'Communication/ChannelSequenceLength',
            'Communication/MaxSendAddress', 'Communication/OriginatorAddress']
    taf = ['Message/Airport', 'Message/BulletinNumber', 'Communication/TAFAddress']
    trend = ['Message/TrendIdentifier', 'Communication/TrendAddress']
    sigmet = ['Message/Airport', 'Message/FIRName', 'Message/BulletinNumber', 'Communication/SIGMETAddress', 'Communication/AIRMETAddress', 'Layer/FIRBoundary']

    options = serial + aftn
    if reportType == 'TAF':
        options += taf

    if reportType == 'Trend':
        options += trend

    if reportType == 'SIGMET':
        options += sigmet

    values = [conf.value(path) for path in options]
    return all(values)

def loadConf(filename, options):
    with open(filename) as file:
        data = json.load(file)

    for path, val in data.items():
        if path in options:
            conf.setValue(path, val)

def saveConf(filename, options):
    data = {path: conf.value(path) for path in options}
    with open(filename, 'w') as file:
        json.dump(data, file)


class SettingDialog(QDialog, Ui_setting.Ui_Settings):
    """设置窗口"""

    restarted = pyqtSignal()
    settingChanged = pyqtSignal()

    def __init__(self, parent=None):
        super(SettingDialog, self).__init__(parent)
        self.parent = parent
        self.setupUi(self)
        self.setWindowIcon(QIcon(':/setting.png'))
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        # 开机自动启动设置
        self.autoRun = QSettings('HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Run', QSettings.NativeFormat)

        self.clockTimer = QTimer()
        self.clockTimer.timeout.connect(self.checkChannelNumber)
        self.clockTimer.start(1 * 1000)

        # 禁用项
        self.closeToMinimize.setEnabled(False)
        self.closeToMinimize.setChecked(True)

        self.buttonBox.button(QDialogButtonBox.Ok).setText(QCoreApplication.translate('Settings', 'OK'))
        self.buttonBox.button(QDialogButtonBox.Apply).setText(QCoreApplication.translate('Settings', 'Apply'))
        self.buttonBox.button(QDialogButtonBox.Cancel).setText(QCoreApplication.translate('Settings', 'Cancel'))

        if boolean(conf.value('General/Sigmet')):
            options = baseOptions + sigmetOptions
        else:
            options = baseOptions
            self.firName.hide()
            self.firNameLabel.hide()
            self.layerURL.hide()
            self.layerURLLabel.hide()
            self.remindSigmet.hide()
            self.sigmetVolume.hide()
            self.addressTab.removeTab(2)
            self.addressTab.removeTab(2)
            self.settingTab.removeTab(6)

        self.options = setupOptions(options)

        self.setStyleSheet(tabStyle)

        self.bindSignal()
        self.setupValidator()
        self.load()

    def bindSignal(self):
        """绑定信号"""
        self.addWeatherButton.clicked.connect(lambda: self.addWeather('weather'))
        self.addWeatherWithIntensityButton.clicked.connect(lambda: self.addWeather('weatherWithIntensity'))

        self.delWeatherButton.clicked.connect(lambda: self.delWeather('weather'))
        self.delWeatherWithIntensityButton.clicked.connect(lambda: self.delWeather('weatherWithIntensity'))

        self.resetNumberButton.clicked.connect(self.resetChannelNumber)
        self.testLoginButton.clicked.connect(self.testFtpLogin)
        self.regenerateTokenButton.clicked.connect(self.regenerateAuthToken)
        self.copyTokenButton.clicked.connect(self.copyAuthToken)
        self.ftpHost.textEdited.connect(self.resetFtpLoginButton)

        self.importBrowseButton.clicked.connect(self.openFile)
        self.exportBrowseButton.clicked.connect(self.openDirectory)
        self.importButton.clicked.connect(self.importConf)
        self.exportButton.clicked.connect(self.exportConf)

        self.buttonBox.accepted.connect(self.applyChange)
        self.buttonBox.button(QDialogButtonBox.Apply).clicked.connect(self.applyChange)

    def setupValidator(self):
        """设置验证器"""
        self.baudrate.setValidator(QIntValidator(self.baudrate))
        self.channelSequenceNumber.setValidator(QIntValidator(self.channelSequenceNumber))
        self.maxSendAddress.setValidator(QIntValidator(self.maxSendAddress))
        self.delayMinutes.setValidator(QIntValidator(self.delayMinutes))

    def checkChannelNumber(self):
        """检查是否是世界时日界，如果是重置流水号"""
        utc = datetime.datetime.utcnow()
        if utc.hour == 0 and utc.minute == 0 and utc.second == 0:
            self.resetChannelNumber()

    def resetChannelNumber(self):
        """重置流水号"""
        conf.setValue('Communication/ChannelSequenceNumber', '1')
        conf.setValue('Communication/FileSequenceNumber', '1')
        self.channelSequenceNumber.setText('1')
        logger.info('Reset channel sequence number to one')

    def regenerateAuthToken(self):
        title = QCoreApplication.translate('Settings', 'Regenerate Auth Token')
        text = QCoreApplication.translate('Settings', 
        'Regenerating the token will cause the existing service to be unavailable due to authentication failure, are you sure you want to do this?')
        ret = QMessageBox.information(self, title, text, QMessageBox.Yes | QMessageBox.No)
        if ret == QMessageBox.Yes:
            authToken = secrets.token_urlsafe(24)
            conf.setValue('Interface/AuthToken', authToken)
            self.loadAuthToken()

    def copyAuthToken(self):
        authToken = context.environ.token()
        QApplication.clipboard().setText(authToken)

    def loadSerialNumber(self):
        """单独载入流水号"""
        self.loadValue('Communication/ChannelSequenceNumber', 'channelSequenceNumber')

    def loadAuthToken(self):
        token = context.environ.token()
        self.token.setText(token)

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

    def showEvent(self, event):
        self.loadSerialNumber()

    def testFtpLogin(self):
        url = self.ftpHost.text()
        try:
            ftpComm('', url, 'test')
        except Exception as e:
            text = QCoreApplication.translate('Settings', 'Retry')
            self.testLoginButton.setText(text)
            logger.error(e)
        else:
            text = QCoreApplication.translate('Settings', 'Done')
            self.testLoginButton.setText(text)
            self.testLoginButton.setEnabled(False)

    def resetFtpLoginButton(self):
        text = QCoreApplication.translate('Settings', 'Login')
        self.testLoginButton.setText(text)
        self.testLoginButton.setEnabled(True)

    def onConfigChanged(self):
        restartRequiredOptions = [
            'General/WindowsStyle', 'General/TAFSpec', 'General/Debug', 'General/InterfaceScaling',
            'Layer/FIRBoundary', 'Layer/Projection', 'Interface/RPC', 'Message/Weather', 'Message/WeatherWithIntensity',
        ]

        closeSenderOptions = [
            'General/CommunicationProtocol', 'Communication/Channel', 'Communication/ChannelSequenceNumber', 
            'Communication/ChannelSequenceLength', 'Communication/MaxSendAddress', 'Communication/OriginatorAddress',
            'Message/Airport', 'Message/BulletinNumber', 'Communication/TAFAddress', 'Message/TrendIdentifier', 'Communication/TrendAddress',
            'Message/FIRName', 'Communication/SIGMETAddress', 'Communication/AIRMETAddress',
        ]

        for key in closeSenderOptions:
            if self.hasValueChanged(key):
                self.settingChanged.emit()
                break

        for key in restartRequiredOptions:
            if self.hasValueChanged(key):
                self.promptRestartRequired()
                break

        self.load()

    def hasValueChanged(self, key):
        if key not in self.options:
            return False

        prev = self.prevConf[key]
        category = self.options[key]['type']
        option = getattr(self, self.options[key]['object'])
        value = self.loadValueFromWidget(option, category)

        if category == 'bool':
            prev = boolean(prev)

        return prev != value

    def hasValidFirBoundary(self):
        text = self.firBoundary.toPlainText()
        try:
            boundary = json.loads(text)
            if not isinstance(boundary, list):
                return False
        except ValueError as e:
            return False
        return True

    def cachePrevConf(self):
        self.prevConf = {}
        for path in self.options:
            self.prevConf[path] = conf.value(path)

    def promptRestartRequired(self):
        title = QCoreApplication.translate('Settings', 'Restart Required')
        text = QCoreApplication.translate('Settings', 'Program need to restart to apply the configuration, do you wish to restart now?')
        ret = QMessageBox.information(self, title, text, QMessageBox.Yes | QMessageBox.No)
        if ret == QMessageBox.Yes:
            self.restarted.emit()

    def applyChange(self):
        if not self.hasValidFirBoundary():
            title = QCoreApplication.translate('Settings', 'Format Error')
            text = QCoreApplication.translate('Settings', 'FIR boundary format is invalid, please check it')
            QMessageBox.warning(self, title, text)
            return

        self.save()
        self.onConfigChanged()

    def save(self):
        """保存设置"""
        if self.runOnStart.isChecked():
            self.autoRun.setValue('Tafor', sys.argv[0])
        else:
            self.autoRun.remove('Tafor')

        self.cachePrevConf()
        for key, value in self.options.items():
            self.setValue(key, value['object'], value['type'])

    def load(self):
        """载入设置"""
        self.runOnStart.setChecked(self.autoRun.contains('Tafor'))

        self.serviceHost.setText('http://{}:9407'.format(ipAddress()))

        for key, value in self.options.items():
            self.loadValue(key, value['object'], value['type'])

        self.loadAuthToken()

    def loadValue(self, path, option, category='text'):
        val = conf.value(path)
        option = getattr(self, option)

        if val is None:
            return 0

        if category == 'text':
            option.setText(val)

        if category == 'plaintext':
            option.setPlainText(val)
            option.moveCursor(QTextCursor.End)

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

    def loadValueFromWidget(self, option, category):
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

        return val

    def setValue(self, path, option, category='text'):
        option = getattr(self, option)
        val = self.loadValueFromWidget(option, category)
        conf.setValue(path, val)

    def exportConf(self):
        filename = self.exportPath.text()
        try:
            saveConf(filename, self.options)

        except Exception as e:
            logger.error(e)

        else:
            context.flash.statusbar(QCoreApplication.translate('Settings', 'Configuration has been exported'), 5000)

    def importConf(self):
        filename = self.importPath.text()
        try:
            self.cachePrevConf()
            loadConf(filename, self.options)

        except Exception as e:
            logger.error(e)

        else:
            self.load()
            self.onConfigChanged()
            context.flash.statusbar(QCoreApplication.translate('Settings', 'Configuration has been imported'), 5000)

    def openFile(self):
        title = QCoreApplication.translate('Settings', 'Open Configuration File')
        path = QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation)
        filename, _ = QFileDialog.getOpenFileName(self, title, path, '(*.json)')
        self.importPath.setText(filename)

    def openDirectory(self):
        title = QCoreApplication.translate('Settings', 'Save Configuration File')
        path = QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation)
        filename, _ = QFileDialog.getSaveFileName(self, title, os.path.join(path, 'tafor.json'), '(*.json)')
        self.exportPath.setText(filename)
