import sys

import pytest

from PyQt5.QtCore import Qt

from tafor.app import MainWindow
from tafor.components import SettingDialog


@pytest.fixture
def window():
    widget = MainWindow()
    return widget

def test_reset_channel_number(qtbot, window):
    dialog = SettingDialog(window)
    qtbot.addWidget(dialog)
    qtbot.mouseClick(dialog.resetNumberButton, Qt.LeftButton)
    assert dialog.channelSequenceNumber.text() == '1'


if __name__ == '__main__':
    pytest.main()