from PyQt5.QtCore import QCoreApplication, QTimer, Qt, pyqtSignal
from PyQt5.QtWidgets import (QCheckBox, QComboBox, QDialog, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QPushButton, QTextEdit, QWidget)

from tafor.ui.fonts import fixedFont


class BaseEditor(QDialog):

    finished = pyqtSignal(object)

    # The name this editor answers to. The editorMessage bus addresses it
    # by this, and it also selects the conf groups checked before the
    # editor can show. Subclass sets it.
    editorName = None

    def __init__(self, parent=None, sender=None, conf=None, context=None):
        super().__init__(parent)
        self.sender = sender
        self.conf = conf
        self.context = context
        self.presenter = None
        self.isStaged = False

        self.defaultAction()
        self.setStyleSheet('QLineEdit {width: 50px;} QComboBox {width: 50px;}')
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

    def initUI(self):
        raise NotImplementedError

    def defaultAction(self):
        self.finished.connect(self.showSender)
        self.sender.backed.connect(self.showEditor)
        self.sender.closed.connect(self.close)

        self.context.event.editorMessage.connect(self.showNotification)

    def showEditor(self):
        self.isStaged = True
        self.show()

    def showSender(self, message):
        if self.sender.isVisible():
            self.sender.clear()

        self.hide()
        self.sender.receive(message)
        self.sender.show()

    def showConfigError(self):
        title = QCoreApplication.translate('Editor', 'Config Error')
        text = QCoreApplication.translate('Editor', 'Please complete the basic configuration first, otherwise you cannot send messages correctly')
        QMessageBox.warning(self, title, text)

    def addBottomBox(self, layout):
        self.bottomBox = QWidget()
        bottomLayout = QHBoxLayout()
        bottomLayout.setContentsMargins(0, 9, 0, 0)
        self.nextButton = QPushButton()
        self.nextButton.setEnabled(False)
        self.nextButton.setText(QCoreApplication.translate('Editor', 'Next'))
        self.nextButton.clicked.connect(self.beforeNext)
        self.notificationArea = QLabel()
        self.notificationArea.setStyleSheet('QLabel {color: grey;}')
        bottomLayout.addWidget(self.notificationArea)
        bottomLayout.addWidget(self.nextButton, 0, Qt.AlignRight|Qt.AlignBottom)
        self.bottomBox.setLayout(bottomLayout)
        layout.addWidget(self.bottomBox)

    def showNotification(self, editorName, message):
        if editorName == self.editorName:
            self.notificationArea.setText(message)
            QTimer.singleShot(10 * 1000, self.notificationArea.clear)

    def beforeNext(self):
        if self.presenter:
            self.presenter.beforeNext()

    def onFirstShow(self):
        pass

    def onClose(self):
        pass

    def keyPressEvent(self, event):
        if event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_Return:
            self.beforeNext()

    def showEvent(self, event):
        if self.editorName and not self.conf.checkCompleteness(self.editorName):
            QTimer.singleShot(0, self.showConfigError)
            return

        if not self.isStaged:
            self.onFirstShow()

    def closeEvent(self, event):
        self.isStaged = False
        self.onClose()


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
            line.setStyleSheet('color: black')
        else:
            line.setStyleSheet('color: grey')

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
