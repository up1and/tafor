from PyQt5.QtWidgets import QCheckBox, QComboBox, QLineEdit, QTextEdit

from tafor.ui.fonts import fixedFont
from tafor.ui.styles import invalidTextStyle, validTextStyle


class TextFieldMixin:
    """Shared text-field behaviour for the message editors.

    The methods here walk the widget tree of whatever editor mixes them in,
    so they assume nothing beyond a QWidget host.
    """

    @classmethod
    def upperText(cls, line):
        line.setText(line.text().upper())

    @classmethod
    def coloredText(cls, line):
        if line.hasAcceptableInput():
            line.setStyleSheet(validTextStyle)
        else:
            line.setStyleSheet(invalidTextStyle)

    def setupFont(self):
        font = fixedFont()
        for line in self.findChildren(QLineEdit):
            line.setFont(font)

        for combox in self.findChildren(QComboBox):
            combox.setFont(font)

        for checkbox in self.findChildren(QCheckBox):
            checkbox.setFont(font)

        for text in self.findChildren(QTextEdit):
            text.setFont(font)
