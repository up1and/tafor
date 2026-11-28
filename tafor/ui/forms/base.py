from PyQt5.QtCore import QSignalBlocker
from PyQt5.QtWidgets import QCheckBox, QComboBox, QLineEdit, QTextEdit

from tafor.ui.fonts import fixedFont
from tafor.ui.styles import invalidTextStyle, validTextStyle


def setLineText(line, text):
    """Write ``text`` into a QLineEdit only when changed, preserving cursor."""
    text = '' if text is None else str(text)
    old = line.text()
    if old == text:
        return False

    pos = line.cursorPosition()
    line.setText(text)
    newPos = max(0, min(pos + len(text) - len(old), len(text)))
    line.setCursorPosition(newPos)
    return True


def setPlainText(edit, text):
    """Write ``text`` into a QTextEdit only when changed, without textChanged."""
    text = '' if text is None else str(text)
    old = edit.toPlainText()
    if old == text:
        return False

    pos = edit.textCursor().position()
    with QSignalBlocker(edit):
        edit.setPlainText(text)
    newPos = max(0, min(pos + len(text) - len(old), len(text)))
    cursor = edit.textCursor()
    cursor.setPosition(newPos)
    edit.setTextCursor(cursor)
    return True


def setComboOptions(combo, options):
    """Replace QComboBox items only when texts or itemData actually differ."""
    desired = [
        (str(item[0]), item[1]) if isinstance(item, tuple) else (str(item), None)
        for item in options
    ]
    current = [(combo.itemText(i), combo.itemData(i)) for i in range(combo.count())]
    if current == desired:
        return False

    combo.clear()
    for text, data in desired:
        if data is None:
            combo.addItem(text)
        else:
            combo.addItem(text, data)
    return True


def setComboText(combo, text, *, index=None):
    """Select QComboBox item by index or text only when changed."""
    if index is not None:
        if combo.currentIndex() == index:
            return False
        combo.setCurrentIndex(index)
        return True

    text = '' if text is None else str(text)
    if combo.isEditable():
        return setLineText(combo.lineEdit(), text)

    target = combo.findText(text)
    if combo.currentIndex() == target:
        return False
    combo.setCurrentIndex(target)
    return True


def setChecked(button, checked):
    """Set checkbox or radio checked state only when it differs."""
    checked = bool(checked)
    if button.isChecked() == checked:
        return False
    button.setChecked(checked)
    return True


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
