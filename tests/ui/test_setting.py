import json
import datetime

import pytest

from PyQt5.QtWidgets import QMessageBox, QFileDialog

from tafor.core.config import createConfig
from tafor.core.states import SequenceService
from tafor.ui.components.setting import SettingDialog

from tests.mocks import MockConfig


class TestSetting:

    @pytest.fixture
    def conf(self):
        # Fresh config: these tests mutate configuration values
        return createConfig(settings=MockConfig())

    @pytest.fixture
    def sequence(self, conf):
        return SequenceService(conf)

    @pytest.fixture
    def setting(self, qtbot, conf, sequence):
        dialog = SettingDialog(None, conf, sequence)
        qtbot.addWidget(dialog)
        return dialog

    def test_bindings_reference_config_items(self, setting, conf):
        items = dict(conf)
        bindings = setting.bindings()

        assert set(bindings) <= set(items)
        assert all(control is not None for control in bindings.values())
        assert bindings['tafSpec'] is setting.tafSpecification
        assert bindings['rpc'] is setting.serviceGroup
        assert bindings['messageUrl'] is setting.messageURL
        assert bindings['layerUrl'] is setting.layerURL
        assert bindings['authToken'] is setting.token

    def test_every_editable_item_has_a_binding(self, setting, conf):
        unbound = {
            'sigmetEnabled', 'license', 'unit', 'codec',
            'remindSnoozeMinutes', 'fileSequenceNumber',
        }

        assert set(dict(conf)) - set(setting.bindings()) == unbound

    def test_reset_channel_number(self, setting, conf):
        setting.channelSequenceNumber.setText('5')
        setting.resetNumberButton.click()

        assert setting.channelSequenceNumber.text() == '1'
        assert conf.channelSequenceNumber == '1'

    def test_saving_settings_does_not_rewind_an_advanced_sequence(self, setting, conf):
        # The dialog loaded 1; a transmission settled while it was open and
        # advanced the runtime counter. Saving another setting must not put
        # the stale control value back.
        conf.set('channelSequenceNumber', '9')

        setting.save()

        assert conf.channelSequenceNumber == '9'

    def test_an_explicitly_edited_sequence_is_saved(self, setting, conf, qtbot):
        setting.channelSequenceNumber.clear()
        qtbot.keyClicks(setting.channelSequenceNumber, '7')

        setting.save()

        assert conf.channelSequenceNumber == '7'

    def test_showing_after_midnight_rolls_the_counters(
            self, qtbot, conf, frozen_time, time_machine):
        sequence = SequenceService(conf)
        dialog = SettingDialog(None, conf, sequence)
        qtbot.addWidget(dialog)
        conf.set('channelSequenceNumber', '9')

        time_machine.move_to(frozen_time + datetime.timedelta(days=1))
        dialog.show()

        assert conf.channelSequenceNumber == '1'
        assert dialog.channelSequenceNumber.text() == '1'

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
        setting.copyAuthToken()
        setting.resetFtpLoginButton()

        assert not warnings
        assert conf.airport == 'YUSO'
        assert conf.bulletinNumber == 'NT36'

    def test_reopen_reloads_unsaved_controls(self, setting, conf, monkeypatch):
        # The dialog is constructed once and reused: reopening must show the
        # saved config, not the last uncommitted draft. Patch the instance
        # (not the QDialog class) to bypass the modal loop.
        modal = []
        monkeypatch.setattr(setting, 'exec', lambda: modal.append(1))
        conf.airport = 'YUDD'
        setting.airport.setText('ZZZZ')

        setting.reopen()

        assert modal == [1]
        assert setting.airport.text() == 'YUDD'


if __name__ == '__main__':
    pytest.main()
