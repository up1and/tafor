from PyQt5.QtCore import QCoreApplication, QTimer, Qt, pyqtSignal
from PyQt5.QtWidgets import QDialog, QHBoxLayout, QLabel, QMessageBox, QPushButton, QWidget

from tafor.ui.styles import mutedStyle


class BaseEditor(QDialog):

    finished = pyqtSignal(object)

    # The name this editor answers to. Segments address their validation
    # messages by it, and it also selects the conf groups checked before
    # the editor can show. Subclass sets it.
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
        self.nextButton.clicked.connect(self.commit)
        self.notificationArea = QLabel()
        self.notificationArea.setStyleSheet(mutedStyle)
        bottomLayout.addWidget(self.notificationArea)
        bottomLayout.addWidget(self.nextButton, 0, Qt.AlignRight|Qt.AlignBottom)
        self.bottomBox.setLayout(bottomLayout)
        layout.addWidget(self.bottomBox)

    def notify(self, message):
        """Show a message in this editor's own notification area.

        Editors hand this to their forms, so a form reports a rejected value
        without knowing what an editor is.
        """
        self.showNotification(self.editorName, message)

    def showNotification(self, editorName, message):
        if editorName == self.editorName:
            self.notificationArea.setText(message)
            QTimer.singleShot(10 * 1000, self.notificationArea.clear)

    def commit(self):
        if self.presenter:
            self.presenter.commit()

    def onOpen(self):
        """A fresh open: the editor was shown to start a report.

        Not called when returning from the sender with a failed report --
        that path must keep what the operator typed.
        """
        pass

    def onClose(self):
        pass

    def keyPressEvent(self, event):
        if event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_Return:
            self.commit()

    def showEvent(self, event):
        if self.editorName and not self.conf.checkCompleteness(self.editorName):
            QTimer.singleShot(0, self.showConfigError)
            return

        if not self.isStaged:
            self.onOpen()

    def closeEvent(self, event):
        self.isStaged = False
        self.onClose()
