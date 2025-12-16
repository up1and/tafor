import os
import sys
import json
import secrets
import logging
import datetime

import shapely

from PyQt5.QtGui import QIcon, QIntValidator, QTextCursor
from PyQt5.QtCore import QCoreApplication, QStandardPaths, QSettings, QTimer, Qt
from PyQt5.QtWidgets import (QDialog, QDialogButtonBox, QFileDialog, QMessageBox, QApplication, QCheckBox, 
                             QLineEdit, QComboBox, QPlainTextEdit, QSlider, QListWidget, QGroupBox)

from tafor import conf
from tafor.states import context
from tafor.utils import ftpComm, ipAddress
from tafor.styles import tabStyle
from tafor.components.ui import Ui_setting, main_rc

logger = logging.getLogger('tafor.setting')


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

    return True

def loadConf(filename, options):
    with open(filename) as file:
        data = json.load(file)

    for path, val in data.items():
        if path in options:
            conf[path] = val

def saveConf(filename, options):
    data = {path: conf[path] for path in options}
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

        if conf.sigmetEnabled:
            pass
        else:
            self.firName.hide()
            self.firNameLabel.hide()
            self.layerURL.hide()
            self.layerURLLabel.hide()
            self.remindSigmet.hide()
            self.sigmetVolume.hide()
            self.addressTab.removeTab(2)
            self.addressTab.removeTab(2)
            self.settingTab.removeTab(6)

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
        conf.channelSequenceNumber = '1'
        conf.fileSequenceNumber = '1'
        self.channelSequenceNumber.setText('1')
        logger.info('Reset sequence number to one')

    def regenerateAuthToken(self):
        title = QCoreApplication.translate('Settings', 'Regenerate Auth Token')
        text = QCoreApplication.translate('Settings', 
        'Regenerating the token will cause the existing service to be unavailable due to authentication failure, are you sure you want to do this?')
        ret = QMessageBox.information(self, title, text, QMessageBox.Yes | QMessageBox.No)
        if ret == QMessageBox.Yes:
            conf.authToken = secrets.token_urlsafe(24)
            self.bindValue(conf.authToken, 'token')

    def copyAuthToken(self):
        QApplication.clipboard().setText(conf.authToken)

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
        self.bindValue(conf.channelSequenceNumber, 'channelSequenceNumber')

    def testFtpLogin(self):
        url = self.ftpHost.text()
        try:
            ftpComm('', url, 'test')
        except Exception as e:
            text = QCoreApplication.translate('Settings', 'Retry')
            self.testLoginButton.setText(text)
            logger.error('Failed to test login FTP server, {}'.format(e))
        else:
            text = QCoreApplication.translate('Settings', 'Done')
            self.testLoginButton.setText(text)
            self.testLoginButton.setEnabled(False)

    def resetFtpLoginButton(self):
        text = QCoreApplication.translate('Settings', 'Login')
        self.testLoginButton.setText(text)
        self.testLoginButton.setEnabled(True)

    def hasValidFirBoundary(self):
        text = self.firBoundary.toPlainText()
        try:
            boundaries = json.loads(text)
            boundary = shapely.geometry.Polygon(boundaries)
            return boundary.is_valid and not boundary.is_empty
        except ValueError as e:
            return False

    def applyChange(self):
        if conf.sigmetEnabled and not self.hasValidFirBoundary():
            title = QCoreApplication.translate('Settings', 'Format Error')
            text = QCoreApplication.translate('Settings', 'FIR boundary format is invalid, please check it')
            QMessageBox.warning(self, title, text)

        self.save()

    def save(self):
        """保存设置"""
        if self.runOnStart.isChecked():
            self.autoRun.setValue('Tafor', sys.argv[0])
        else:
            self.autoRun.remove('Tafor')

        for attr, config in conf:
            value = self.getValue(config.default, config.bindProperty)
            conf.set(attr, value)

        conf.emit()

    def load(self):
        """载入设置"""
        self.runOnStart.setChecked(self.autoRun.contains('Tafor'))

        self.serviceHost.setText('http://{}:9407'.format(ipAddress()))

        for attr, config in conf:
            self.bindValue(config.value, config.bindProperty)

    def bindValue(self, value, bindProperty):
        control = getattr(self, bindProperty)

        if isinstance(control, QLineEdit):
            control.setText(value)

        if isinstance(control, (QCheckBox, QGroupBox)):
            control.setChecked(value)

        if isinstance(control, QPlainTextEdit):
            control.setPlainText(value)
            control.moveCursor(QTextCursor.End)

        if isinstance(control, QListWidget):
            control.clear()
            control.addItems(value)

        if isinstance(control, QComboBox):
            index = value if isinstance(value, int) else control.findText(value, Qt.MatchFixedString)
            control.setCurrentIndex(index)

        if isinstance(control, QSlider):
            control.setValue(value)

    def getValue(self, default, bindProperty):
        control = getattr(self, bindProperty)

        if isinstance(control, QLineEdit):
            return control.text()

        if isinstance(control, (QCheckBox, QGroupBox)):
            return control.isChecked()

        if isinstance(control, QPlainTextEdit):
            return control.toPlainText()

        if isinstance(control, QListWidget):
            items = [control.item(i).text() for i in range(control.count())]
            return json.dumps(items)

        if isinstance(control, QComboBox):
            if isinstance(default, int):
                return control.currentIndex()
            else:
                return control.currentText()

        if isinstance(control, QSlider):
            return control.value()

    def exportConf(self):
        filename = self.exportPath.text()
        try:
            pass

        except Exception as e:
            logger.error('Export configuration file failed, {}'.format(e))

        else:
            context.flash.statusbar(QCoreApplication.translate('Settings', 'Configuration has been exported'), 5000)

    def importConf(self):
        filename = self.importPath.text()
        try:
            pass

        except Exception as e:
            logger.error('Import configuration file failed, {}'.format(e))

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
