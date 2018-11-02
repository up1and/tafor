import pytest

from PyQt5.QtCore import Qt

from tafor.components import SettingDialog
from tafor.components.setting import isConfigured


def test_is_configured():
    assert isConfigured('TAF')
    assert isConfigured('Trend')
    assert isConfigured('SIGMET')

def test_reset_channel_number(qtbot, app):
    dialog = app.settingDialog
    qtbot.addWidget(dialog)
    qtbot.mouseClick(dialog.resetNumberButton, Qt.LeftButton)
    assert dialog.channelSequenceNumber.text() == '1'

def test_methods(app):
    dialog = app.settingDialog
    dialog.load()
    dialog.save()
    dialog.checkChannelNumber()
    dialog.loadSerialNumber()
    dialog.addWeather('weather')
    dialog.addWeather('weatherWithIntensity')
    dialog.delWeather('weather')
    dialog.delWeather('weatherWithIntensity')
    dialog.updateSoundVolume()


if __name__ == '__main__':
    pytest.main()