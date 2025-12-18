import json

import pytest

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QMessageBox, QFileDialog

from tafor.components.setting import SettingDialog

from tests.mocks import conf


class TestSetting(object):

    @pytest.fixture
    def setting(self, qtbot):
        dialog = SettingDialog()
        qtbot.addWidget(dialog)
        return dialog

    def test_reset_channel_number(self, qtbot, setting):
        qtbot.mouseClick(setting.resetNumberButton, Qt.LeftButton)
        assert setting.channelSequenceNumber.text() == '1'

    def test_weather(self, setting):
        setting.weather.setText('BR')
        setting.addWeather('weather')
        assert setting.weatherList.item(setting.weatherList.count() - 1).text() == 'BR'

        setting.weatherWithIntensity.setText('SHRA')
        setting.addWeather('weatherWithIntensity')
        assert setting.weatherWithIntensityList.item(setting.weatherWithIntensityList.count() - 1).text() == 'SHRA'

        setting.delWeather('weather')
        setting.delWeather('weatherWithIntensity')

    def test_with_message_box(self, setting, monkeypatch):
        monkeypatch.setattr(QMessageBox, 'information', lambda *args: QMessageBox.Yes)
        setting.regenerateAuthToken()
        setting.promptRestartRequired()

    def test_export(self, setting, tmpdir):
        file = tmpdir.join('export.json')
        setting.exportPath.setText(str(file))
        setting.exportConf()

    def test_import(self, setting, tmpdir):
        file = tmpdir.join('import.json')
        file.write(json.dumps(conf.config))
        setting.importPath.setText(str(file))
        setting.importConf()

    def test_filedialog(self, qtbot, setting, monkeypatch, tmpdir):
        file = tmpdir.join('export.json')
        monkeypatch.setattr(QFileDialog, 'getSaveFileName', lambda *args, **kwargs: (str(file), None))
        qtbot.mouseClick(setting.exportBrowseButton, Qt.LeftButton)

        monkeypatch.setattr(QFileDialog, 'getOpenFileName', lambda *args, **kwargs: (str(file), None))
        qtbot.mouseClick(setting.importBrowseButton, Qt.LeftButton)

    def test_methods(self, setting):
        setting.load()
        setting.save()
        setting.checkChannelNumber()
        setting.loadSerialNumber()

        setting.copyAuthToken()
        setting.resetFtpLoginButton()

        setting.onConfigChanged()
        setting.applyChange()

    # def test_ftp(self, setting):
    #     setting.testFtpLogin()


if __name__ == '__main__':
    pytest.main()