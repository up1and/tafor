from PyQt5.QtCore import QSignalBlocker
from PyQt5.QtGui import QValidator
from PyQt5.QtWidgets import QCheckBox, QComboBox, QLineEdit, QTextEdit

from tafor.ui.fonts import fixedFont
from tafor.ui.styles import invalidTextStyle, validTextStyle


def isAcceptable(widget, text):
    """Return True when ``text`` satisfies ``widget``'s validator (or no validator exists)."""
    if isinstance(widget, QComboBox):
        validator = widget.validator() or (widget.lineEdit().validator() if widget.isEditable() else None)
    else:
        validator = widget.validator()

    if validator is None:
        return True

    text = '' if text is None else str(text)
    return validator.validate(text, 0)[0] == QValidator.Acceptable


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


def coloredText(widget):
    """Style a QLineEdit (or editable QComboBox) according to validator acceptability."""
    line = widget.lineEdit() if isinstance(widget, QComboBox) else widget
    if line is None:
        return
    style = validTextStyle if line.hasAcceptableInput() else invalidTextStyle
    if line.styleSheet() != style:
        line.setStyleSheet(style)


def setupFont(widget):
    """Apply the fixed-width font to form input controls inside ``widget``."""
    font = fixedFont()
    for cls in (QLineEdit, QComboBox, QCheckBox, QTextEdit):
        for child in widget.findChildren(cls):
            child.setFont(font)
