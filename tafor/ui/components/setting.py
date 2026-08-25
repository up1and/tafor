import os
import sys
import json
import secrets
import logging
import datetime

from PyQt5.QtGui import QIcon, QIntValidator, QTextCursor
from PyQt5.QtCore import QCoreApplication, QStandardPaths, QSettings, QTimer, Qt
from PyQt5.QtWidgets import (QDialog, QDialogButtonBox, QFileDialog, QMessageBox, QApplication, QCheckBox, 
                             QLineEdit, QComboBox, QPlainTextEdit, QSlider, QListWidget, QGroupBox)

from tafor.core.utils.common import ipAddress
from tafor.ui.qt import Ui_setting, main_rc
from tafor.ui.styles import tabStyle
from tafor.ui.workers import FtpWorker, threadManager

logger = logging.getLogger('tafor.setting')


class SettingDialog(QDialog, Ui_setting.Ui_Settings):

    def __init__(self, parent=None, conf=None, context=None):
        super(SettingDialog, self).__init__(parent)
        self.parent = parent
        self.conf = conf
        self.context = context
        self.setupUi(self)
        self.setWindowIcon(QIcon(':/setting.png'))
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        # Auto-start on system boot
        self.autoRun = QSettings('HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Run', QSettings.NativeFormat)

        self.utcCheckpoint = datetime.datetime.utcnow()

        self.clockTimer = QTimer()
        self.clockTimer.timeout.connect(self.checkChannelNumber)
        self.clockTimer.start(1 * 1000)

        # Disabled items
        self.closeToMinimize.setEnabled(False)
        self.closeToMinimize.setChecked(True)

        self.buttonBox.button(QDialogButtonBox.Ok).setText(QCoreApplication.translate('Settings', 'OK'))
        self.buttonBox.button(QDialogButtonBox.Apply).setText(QCoreApplication.translate('Settings', 'Apply'))
        self.buttonBox.button(QDialogButtonBox.Cancel).setText(QCoreApplication.translate('Settings', 'Cancel'))

        if self.conf.sigmetEnabled:
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

        self.buttonBox.accepted.connect(self.save)
        self.buttonBox.button(QDialogButtonBox.Apply).clicked.connect(self.save)

    def setupValidator(self):
        self.baudrate.setValidator(QIntValidator(self.baudrate))
        self.channelSequenceNumber.setValidator(QIntValidator(self.channelSequenceNumber))
        self.maxSendAddress.setValidator(QIntValidator(self.maxSendAddress))
        self.delayMinutes.setValidator(QIntValidator(self.delayMinutes))

    def checkChannelNumber(self):
        """Reset the sequence numbers once the UTC calendar day rolls over"""
        utc = datetime.datetime.utcnow()
        if utc.date() > self.utcCheckpoint.date():
            self.utcCheckpoint = utc
            self.resetChannelNumber()

    def resetChannelNumber(self):
        """Reset the sequence numbers to one"""
        self.conf.channelSequenceNumber = '1'
        self.conf.fileSequenceNumber = '1'
        self.channelSequenceNumber.setText('1')
        logger.info('Reset sequence number to one')

    def regenerateAuthToken(self):
        title = QCoreApplication.translate('Settings', 'Regenerate Auth Token')
        text = QCoreApplication.translate('Settings', 
        'Regenerating the token will cause the existing service to be unavailable due to authentication failure, are you sure you want to do this?')
        ret = QMessageBox.information(self, title, text, QMessageBox.Yes | QMessageBox.No)
        if ret == QMessageBox.Yes:
            self.conf.authToken = secrets.token_urlsafe(24)
            self.bindValue(self.conf.authToken, 'token')

    def copyAuthToken(self):
        QApplication.clipboard().setText(self.conf.authToken)

    def addWeather(self, weather):
        """Add a weather phenomenon"""
        line = getattr(self, weather)
        if line.text():
            getattr(self, weather + 'List').addItem(line.text())
            line.clear()

    def delWeather(self, weather):
        """Remove a weather phenomenon"""
        option = getattr(self, weather + 'List')
        option.takeItem(option.currentRow())

    def showEvent(self, event):
        self.bindValue(self.conf.channelSequenceNumber, 'channelSequenceNumber')

    def testFtpLogin(self):
        self.testLoginButton.setEnabled(False)
        worker, thread = threadManager.createWorker(FtpWorker, '', self.ftpHost.text(), 'test')
        worker.done.connect(self.handleFtpLoginResult)
        thread.start()

    def handleFtpLoginResult(self, error):
        if error:
            text = QCoreApplication.translate('Settings', 'Retry')
            self.testLoginButton.setText(text)
            self.testLoginButton.setEnabled(True)
        else:
            text = QCoreApplication.translate('Settings', 'Done')
            self.testLoginButton.setText(text)

    def resetFtpLoginButton(self):
        text = QCoreApplication.translate('Settings', 'Login')
        self.testLoginButton.setText(text)
        self.testLoginButton.setEnabled(True)

    def save(self):
        if self.runOnStart.isChecked():
            self.autoRun.setValue('Tafor', sys.argv[0])
        else:
            self.autoRun.remove('Tafor')

        errors = []
        for attr, config in self.conf:
            value = self.getValue(config.default, config.bindProperty)
            try:
                self.conf.set(attr, value)
            except ValueError as e:
                logger.warning('Failed to save setting: %s', e)
                if attr == 'firBoundary':
                    text = QCoreApplication.translate(
                        'Settings',
                        'FIR boundary format is invalid. Please enter JSON coordinates like [[lon, lat], [lon, lat], ...], and make sure they form a valid polygon.'
                    )
                else:
                    text = str(e)

                if text not in errors:
                    errors.append(text)

        self.conf.emit()

        if errors:
            title = QCoreApplication.translate('Settings', 'Format Error')
            QMessageBox.warning(self, title, '\n\n'.join(errors))

    def load(self):
        self.runOnStart.setChecked(self.autoRun.contains('Tafor'))

        self.serviceHost.setText('http://{}:9407'.format(ipAddress()))

        for attr, config in self.conf:
            self.bindValue(self.conf.get(attr), config.bindProperty)

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
            data = {attr: self.conf.get(attr) for attr, config in self.conf}
            with open(filename, 'w') as file:
                json.dump(data, file)

            self.context.flash.statusbar(QCoreApplication.translate('Settings', 'Configuration has been exported'), 5000)
        except Exception as e:
            logger.error('Export configuration file failed, {}'.format(e))

    def importConf(self):
        filename = self.importPath.text()
        try:
            with open(filename) as file:
                data = json.load(file)

            for attr, value in data.items():
                self.conf.set(attr, value)

            self.conf.emit()
            self.load()
            self.context.flash.statusbar(QCoreApplication.translate('Settings', 'Configuration has been imported'), 5000)
        except Exception as e:
            logger.error('Import configuration file failed, {}'.format(e), exc_info=True)

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
