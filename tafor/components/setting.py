import os
import sys
import json
import datetime

from PyQt5.QtGui import QIcon, QIntValidator
from PyQt5.QtCore import QCoreApplication, QStandardPaths, QSettings, QTimer, Qt
from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QTableWidgetItem, QFileDialog, QMessageBox

from tafor import conf, logger
from tafor.utils import boolean, ftpComm
from tafor.components.ui import Ui_setting, main_rc


baseOptions = [
    # 通用设置
    ('General/WindowsStyle', 'windowsStyle', 'combox'),
    ('General/CommunicationLine', 'communicationLine', 'combox'),
    ('General/InterfaceScaling', 'interfaceScaling', 'comboxindex'),
    ('General/TAFSpec', 'tafSpecification', 'comboxindex'),
    ('General/CloseToMinimize', 'closeToMinimize', 'bool'),
    ('General/Debug', 'debugMode', 'bool'),
    ('General/RPC', 'rpcService', 'bool'),
    ('General/AlwaysShowEditor', 'alwaysShowEditor', 'bool'),
    ('General/AutoComletionGroupTime', 'autoComletionGroupTime', 'bool'),
    # 验证选项
    ('Validator/VisHas5000', 'visHas5000', 'bool'),
    ('Validator/CloudHeightHas450', 'cloudHeightHas450', 'bool'),
    ('Validator/WeakPrecipitationVerification', 'weakPrecipitationVerification', 'bool'),
    # 报文字符
    ('Message/ICAO', 'icao', 'text'),
    ('Message/Area', 'area', 'text'),
    ('Message/TrendSign', 'trendSign', 'text'),
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
    # 数据源
    ('Monitor/WebApiURL', 'webApiURL', 'text'),
    # TAF 报文迟发告警
    ('Monitor/WarnTAFTime', 'warnTafTime', 'text'),
    ('Monitor/WarnTAFVolume', 'warnTafVolume', 'slider'),
    # 报文发送提醒
    ('Monitor/RemindTAF', 'remindTaf', 'bool'),
    ('Monitor/RemindTAFVolume', 'remindTafVolume', 'slider'),
    ('Monitor/RemindTrend', 'remindTrend', 'bool'),
    ('Monitor/RemindTrendVolume', 'remindTrendVolume', 'slider'),
]

sigmetOptions = [
    # 报文字符
    ('Message/FIR', 'fir', 'text'),
    # AFTN 配置
    ('Communication/AIRMETAddress', 'airmetAddress', 'plaintext'),
    ('Communication/SIGMETAddress', 'sigmetAddress', 'plaintext'),
    # 数据源
    ('Monitor/FirApiURL', 'firApiURL', 'text'),
    # 报文发送提醒
    ('Monitor/RemindSIGMET', 'remindSigmet', 'bool'),
    ('Monitor/RemindSIGMETVolume', 'remindSigmetVolume', 'slider'),
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
            self.fir.hide()
            self.firLabel.hide()
            self.firApiURL.hide()
            self.firApiLabel.hide()
            self.firCanvasSize.hide()
            self.firCanvasSizeLabel.hide()
            self.remindSigmet.hide()
            self.remindSigmetVolume.hide()
            self.addressTab.removeTab(2)
            self.addressTab.removeTab(2)

        self.options = setupOptions(options)

        self.icao.setPlaceholderText('YUSO')
        self.fir.setPlaceholderText('YUDD SHANLON FIR')
        self.originatorAddress.setPlaceholderText('YUSOYMYX')

        self.bindSignal()
        self.setValidator()
        self.load()

    def bindSignal(self):
        """绑定信号"""
        self.addWeatherButton.clicked.connect(lambda: self.addWeather('weather'))
        self.addWeatherWithIntensityButton.clicked.connect(lambda: self.addWeather('weatherWithIntensity'))

        self.delWeatherButton.clicked.connect(lambda: self.delWeather('weather'))
        self.delWeatherWithIntensityButton.clicked.connect(lambda: self.delWeather('weatherWithIntensity'))

        self.resetNumberButton.clicked.connect(self.resetChannelNumber)
        self.testLoginButton.clicked.connect(self.testFtpLogin)
        self.ftpHost.textEdited.connect(self.resetFtpLoginButton)

        self.importBrowseButton.clicked.connect(lambda: self.openFile(self.importPath))
        self.exportBrowseButton.clicked.connect(lambda: self.openDirectory(self.exportPath))
        self.importButton.clicked.connect(self.importConf)
        self.exportButton.clicked.connect(self.exportConf)

        self.buttonBox.accepted.connect(self.save)
        self.buttonBox.accepted.connect(self.onConfigChanged)
        self.buttonBox.button(QDialogButtonBox.Apply).clicked.connect(self.save)
        self.buttonBox.button(QDialogButtonBox.Apply).clicked.connect(self.onConfigChanged)

    def setValidator(self):
        """设置验证器"""
        self.baudrate.setValidator(QIntValidator(self.baudrate))
        self.channelSequenceNumber.setValidator(QIntValidator(self.channelSequenceNumber))
        self.maxSendAddress.setValidator(QIntValidator(self.maxSendAddress))
        self.warnTafTime.setValidator(QIntValidator(self.warnTafTime))

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

    def updateSoundVolume(self):
        """更新提醒声音音量"""
        self.parent.ringSound.setVolume(conf.value('Monitor/RemindTAFVolume'))
        self.parent.alarmSound.setVolume(conf.value('Monitor/WarnTAFVolume'))
        self.parent.trendSound.setVolume(conf.value('Monitor/RemindTrendVolume'))
        self.parent.sigmetSound.setVolume(conf.value('Monitor/RemindSIGMETVolume'))

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
            'General/WindowsStyle', 'General/InterfaceScaling', 'General/TAFSpec',
            'General/Debug', 'General/RPC', 'Message/Weather', 'Message/WeatherWithIntensity',
        ]

        closeSenderOptions = [
            'General/CommunicationLine', 'Communication/Channel', 'Communication/ChannelSequenceNumber', 
            'Communication/ChannelSequenceLength', 'Communication/MaxSendAddress', 'Communication/OriginatorAddress',
            'Message/ICAO', 'Message/Area', 'Communication/TAFAddress', 'Message/TrendSign', 'Communication/TrendAddress',
            'Message/FIR', 'Message/Area', 'Communication/SIGMETAddress', 'Communication/AIRMETAddress',
        ]

        if self.hasValueChanged('General/FirCanvasSize'):
            self.parent.sigmetEditor.close()

        for key in closeSenderOptions:
            if self.hasValueChanged(key):
                self.parent.tafSender.close()
                self.parent.trendSender.close()
                self.parent.sigmetSender.close()
                break

        for key in restartRequiredOptions:
            if self.hasValueChanged(key):
                self.promptRestartRequired()
                break

        self.updateSoundVolume()
        self.parent.updateGui()

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

    def cachePrevConf(self):
        self.prevConf = {}
        for path in self.options:
            self.prevConf[path] = conf.value(path)

    def promptRestartRequired(self):
        title = QCoreApplication.translate('Settings', 'Restart Required')
        text = QCoreApplication.translate('Settings', 'Program need to restart to apply the configuration, do you wish to restart now?')
        ret = QMessageBox.information(self, title, text, QMessageBox.Yes | QMessageBox.No)
        if ret == QMessageBox.Yes:
            self.parent.restart()

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

        for key, value in self.options.items():
            self.loadValue(key, value['object'], value['type'])

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
            self.parent.statusBar.showMessage(QCoreApplication.translate('Settings', 'Configuration has been exported'), 5000)

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
            self.parent.statusBar.showMessage(QCoreApplication.translate('Settings', 'Configuration has been imported'), 5000)

    def openFile(self, receiver):
        title = QCoreApplication.translate('Settings', 'Open Configuration File')
        path = QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation)
        filename, _ = QFileDialog.getOpenFileName(self, title, path, '(*.json)')
        receiver.setText(filename)

    def openDirectory(self, receiver):
        title = QCoreApplication.translate('Settings', 'Save Configuration File')
        path = QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation)
        filename, _ = QFileDialog.getSaveFileName(self, title, os.path.join(path, 'tafor.json'), '(*.json)')
        receiver.setText(filename)
