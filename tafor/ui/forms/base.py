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

    def reload(self):
        """Adopt what the widgets now say: read them into the state, announce.

        Filling widgets is not a user edit, so textEdited does not fire; whoever
        wrote the widgets has to say so here. Every programmatic write that
        the editor cares about ends with this call -- state has one writer,
        collect(), and this is the pair that tells the editor it happened.
        """
        self.collect()
        self.contentChanged.emit()

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
