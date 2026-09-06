import json

import pytest

from PyQt5.QtWidgets import QMessageBox, QFileDialog

from tafor.core.config import createConfig
from tafor.ui.components.setting import SettingDialog

from tests.mocks import MockConfig


class TestSetting:

    @pytest.fixture
    def conf(self):
        # Fresh config: these tests mutate configuration values
        return createConfig(settings=MockConfig())

    @pytest.fixture
    def setting(self, qtbot, conf, context):
        dialog = SettingDialog(None, conf, context)
        qtbot.addWidget(dialog)
        return dialog

    def test_reset_channel_number(self, setting, conf):
        setting.channelSequenceNumber.setText('5')
        setting.resetNumberButton.click()

        assert setting.channelSequenceNumber.text() == '1'
        assert conf.channelSequenceNumber == '1'

    def test_weather(self, setting):
        # The lists start pre-filled from config (load())
        weatherCount = setting.weatherList.count()
        intensityCount = setting.weatherWithIntensityList.count()

        setting.weather.setText('BR')
        setting.addWeather('weather')
        assert setting.weatherList.item(setting.weatherList.count() - 1).text() == 'BR'

        setting.weatherWithIntensity.setText('SHRA')
        setting.addWeather('weatherWithIntensity')
        assert setting.weatherWithIntensityList.item(setting.weatherWithIntensityList.count() - 1).text() == 'SHRA'

        setting.weatherList.setCurrentRow(setting.weatherList.count() - 1)
        setting.delWeather('weather')
        assert setting.weatherList.count() == weatherCount

        setting.weatherWithIntensityList.setCurrentRow(setting.weatherWithIntensityList.count() - 1)
        setting.delWeather('weatherWithIntensity')
        assert setting.weatherWithIntensityList.count() == intensityCount

    def test_regenerate_auth_token(self, setting, conf, monkeypatch):
        monkeypatch.setattr(QMessageBox, 'information', lambda *args, **kwargs: QMessageBox.Yes)
        old = conf.authToken

        setting.regenerateAuthToken()

        assert conf.authToken != old
        assert setting.token.text() == conf.authToken

    def test_regenerate_auth_token_declined(self, setting, conf, monkeypatch):
        monkeypatch.setattr(QMessageBox, 'information', lambda *args, **kwargs: QMessageBox.No)
        old = conf.authToken

        setting.regenerateAuthToken()

        assert conf.authToken == old

    def test_export(self, setting, tmpdir):
        file = tmpdir.join('export.json')
        setting.exportPath.setText(str(file))

        setting.exportConf()

        data = json.loads(file.read())
        assert data['airport'] == 'YUSO'
        assert data['bulletinNumber'] == 'NT36'

    def test_import(self, setting, conf, tmpdir):
        file = tmpdir.join('import.json')
        file.write(json.dumps({'airport': 'YUDD', 'debugMode': 'true'}))
        setting.importPath.setText(str(file))

        setting.importConf()

        assert conf.airport == 'YUDD'
        assert setting.airport.text() == 'YUDD'
        assert conf.debugMode is True

    def test_filedialog(self, setting, monkeypatch, tmpdir):
        export = tmpdir.join('export.json')
        monkeypatch.setattr(QFileDialog, 'getSaveFileName', lambda *args, **kwargs: (str(export), None))
        setting.exportBrowseButton.click()
        assert setting.exportPath.text() == str(export)

        imported = tmpdir.join('import.json')
        monkeypatch.setattr(QFileDialog, 'getOpenFileName', lambda *args, **kwargs: (str(imported), None))
        setting.importBrowseButton.click()
        assert setting.importPath.text() == str(imported)

    def test_load_save_roundtrip(self, setting, conf, monkeypatch):
        warnings = []
        monkeypatch.setattr(QMessageBox, 'warning', lambda *args, **kwargs: warnings.append(args))

        setting.load()
        setting.save()
        setting.checkChannelNumber()
        setting.copyAuthToken()
        setting.resetFtpLoginButton()

        assert not warnings
        assert conf.airport == 'YUSO'
        assert conf.bulletinNumber == 'NT36'


if __name__ == '__main__':
    pytest.main()
