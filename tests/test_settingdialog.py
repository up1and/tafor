import sys

import pytest

from PyQt5.QtCore import Qt

from tafor.components import SettingDialog


def test_reset_channel_number(qtbot, window):
    dialog = SettingDialog(window)
    qtbot.addWidget(dialog)
    qtbot.mouseClick(dialog.resetNumberButton, Qt.LeftButton)
    assert dialog.channelSequenceNumber.text() == '1'


if __name__ == '__main__':
    pytest.main()