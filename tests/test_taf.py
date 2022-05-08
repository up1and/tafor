import pytest

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QMessageBox

from tafor.components.taf import TafEditor
from tafor.components.send import TafSender


class TestTrend(object):

    @pytest.fixture
    def sender(self, qtbot):
        sender = TafSender()
        qtbot.addWidget(sender)
        return sender

    @pytest.fixture
    def editor(self, qtbot, sender):
        editor = TafEditor(parent=None, sender=sender)
        qtbot.addWidget(editor)
        return editor

    def test_send_taf(self, qtbot, monkeypatch, sender, editor):
        # idx = editor.trend.weatherWithIntensity.findText('TSRA')
        # editor.trend.weatherWithIntensity.setCurrentIndex(idx)
        # editor.trend.cloud1.setText('SCT020')
        # editor.trend.cb.setText('FEW026')
        # qtbot.mouseClick(editor.nextButton, Qt.LeftButton)
        # qtbot.mouseClick(sender.sendButton, Qt.LeftButton)
        # monkeypatch.setattr(QMessageBox, 'critical', lambda *args: 'critical')
        pass

    def test_taf_editor(self, qtbot, editor):
        # qtbot.mouseClick(editor.trend.becmg, Qt.LeftButton)
        # qtbot.mouseClick(editor.trend.tempo, Qt.LeftButton)
        # qtbot.mouseClick(editor.trend.cavok, Qt.LeftButton)
        # qtbot.mouseClick(editor.trend.nsc, Qt.LeftButton)
        # qtbot.mouseClick(editor.trend.fm, Qt.LeftButton)
        # qtbot.mouseClick(editor.trend.tl, Qt.LeftButton)
        # qtbot.mouseClick(editor.trend.at, Qt.LeftButton)
        # qtbot.mouseClick(editor.trend.nosig, Qt.LeftButton)
        pass

    def test_taf_validate(self, qtbot, editor):
        # qtbot.mouseClick(editor.trend.at, Qt.LeftButton)
        # editor.trend.period.setText('2400')
        # editor.trend.period.editingFinished.emit()

        # qtbot.mouseClick(editor.trend.tl, Qt.LeftButton)
        # editor.trend.period.setText('0000')
        # editor.trend.period.editingFinished.emit()
        pass


if __name__ == '__main__':
    pytest.main()