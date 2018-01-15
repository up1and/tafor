from PyQt5.QtGui import QRegExpValidator
from PyQt5.QtCore import QRegExp
from PyQt5.QtWidgets import QLineEdit


class Input(QLineEdit):
    def __init__(self, regex, parent=None):
        super(Input, self).__init__(parent)
        self.regex = regex
        self.textEdited.connect(self.upper_text)
        self.set_validator()

    def set_validator(self):
        pattern = QRegExpValidator(QRegExp(self.regex))
        self.setValidator(pattern)

    def upper_text(self):
        print(self.text())
        self.setText(self.text().upper())
        
