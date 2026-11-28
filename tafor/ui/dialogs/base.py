from PyQt5.QtCore import QCoreApplication, QTimer, Qt, pyqtSignal
from PyQt5.QtWidgets import QDialog, QHBoxLayout, QLabel, QMessageBox, QPushButton, QWidget

from tafor.ui.styles import mutedStyle


class BaseEditor(QDialog):

    finished = pyqtSignal(object)
    opened = pyqtSignal()
    closed = pyqtSignal()
    submitted = pyqtSignal()

    # Selects the conf groups checked before the editor can show. Subclass sets it.
    editorName = None

    def __init__(self, parent=None, sender=None, conf=None, context=None):
        super().__init__(parent)
        self.sender = sender
        self.conf = conf
        self.context = context
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
        self.nextButton.clicked.connect(self.submitted)
        self.notificationArea = QLabel()
        self.notificationArea.setStyleSheet(mutedStyle)
        bottomLayout.addWidget(self.notificationArea)
        bottomLayout.addWidget(self.nextButton, 0, Qt.AlignRight|Qt.AlignBottom)
        self.bottomBox.setLayout(bottomLayout)
        layout.addWidget(self.bottomBox)

    def setNextEnabled(self, enabled):
        self.nextButton.setEnabled(enabled)

    def showNotification(self, message):
        self.notificationArea.setText(message)
        QTimer.singleShot(10 * 1000, self.notificationArea.clear)

    def keyPressEvent(self, event):
        if event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_Return:
            self.submitted.emit()

    def showEvent(self, event):
        if self.editorName and not self.conf.checkCompleteness(self.editorName):
            QTimer.singleShot(0, self.showConfigError)
            return

        # Fresh open only: returning from sender keeps what the operator typed.
        if not self.isStaged:
            self.opened.emit()

    def closeEvent(self, event):
        self.isStaged = False
        self.closed.emit()
