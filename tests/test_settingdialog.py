# -*- coding: utf-8 -*-

from .context import tafor

import sys
import unittest

from PyQt5.QtCore import Qt
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication

app = QApplication(sys.argv)


class TestMainWindow(unittest.TestCase):
    def setUp(self):
        self.main = tafor.app.MainWindow()
        self.dialog = tafor.components.SettingDialog(self.main)

    def testResetChannelNumber(self):
        button = self.dialog.resetNumberButton
        QTest.mouseClick(button, Qt.LeftButton)
        self.assertEqual(self.dialog.channelSequenceNumber.text(), '1')


if __name__ == '__main__':
    unittest.main()