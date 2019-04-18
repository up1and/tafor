import pytest

from PyQt5.QtCore import Qt

from tafor.app import MainWindow
from tafor.components.setting import isConfigured


def test_is_configured():
    assert isConfigured('TAF')
    assert isConfigured('Trend')
    assert isConfigured('SIGMET')


class TestSetting(object):

    @pytest.fixture
    def setting(self, qtbot):
        window = MainWindow()
        qtbot.addWidget(window)
        return window.settingDialog

    def test_reset_channel_number(self, qtbot, setting):
        qtbot.mouseClick(setting.resetNumberButton, Qt.LeftButton)
        assert setting.channelSequenceNumber.text() == '1'

    def test_methods(self, setting):
        setting.load()
        setting.save()
        setting.checkChannelNumber()
        setting.loadSerialNumber()
        setting.addWeather('weather')
        setting.addWeather('weatherWithIntensity')
        setting.delWeather('weather')
        setting.delWeather('weatherWithIntensity')
        setting.updateSoundVolume()


if __name__ == '__main__':
    pytest.main()