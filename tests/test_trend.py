import pytest

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QMessageBox

from tafor.components.trend import TrendEditor


def test_send_trend(qtbot, monkeypatch, app):
    editor = app.trendEditor
    sender = app.trendSender
    idx = editor.trend.weatherWithIntensity.findText('TSRA')
    editor.trend.weatherWithIntensity.setCurrentIndex(idx)
    editor.trend.cloud1.setText('SCT020')
    editor.trend.cb.setText('FEW026')
    qtbot.mouseClick(editor.nextButton, Qt.LeftButton)
    qtbot.mouseClick(sender.sendButton, Qt.LeftButton)
    monkeypatch.setattr(QMessageBox, 'critical', lambda *args: 'critical')
    sender.close()

def test_trend_editor(qtbot, app):
    trend = app.trendEditor.trend
    qtbot.mouseClick(trend.becmg, Qt.LeftButton)
    qtbot.mouseClick(trend.tempo, Qt.LeftButton)
    qtbot.mouseClick(trend.cavok, Qt.LeftButton)
    qtbot.mouseClick(trend.nsc, Qt.LeftButton)
    qtbot.mouseClick(trend.fm, Qt.LeftButton)
    qtbot.mouseClick(trend.tl, Qt.LeftButton)
    qtbot.mouseClick(trend.at, Qt.LeftButton)
    qtbot.mouseClick(trend.nosig, Qt.LeftButton)

def test_trend_validate(qtbot, app):
    trend = app.trendEditor.trend
    qtbot.mouseClick(trend.at, Qt.LeftButton)
    trend.period.setText('2400')
    trend.period.editingFinished.emit()

    qtbot.mouseClick(trend.tl, Qt.LeftButton)
    trend.period.setText('0000')
    trend.period.editingFinished.emit()


if __name__ == '__main__':
    pytest.main()