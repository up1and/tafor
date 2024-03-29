from PyQt5.QtCore import QCoreApplication, QTimer, Qt, pyqtSignal
from PyQt5.QtWidgets import QWidget, QDialog, QMessageBox, QHBoxLayout, QLabel, QPushButton

from tafor.states import context


class BaseEditor(QDialog):

    finished = pyqtSignal(object)

    def __init__(self, parent=None, sender=None):
        super(BaseEditor, self).__init__(parent)
        self.parent = parent
        self.sender = sender
        self.isStaged = False

        self.defaultAction()
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

    def initUI(self):
        raise NotImplementedError

    def bindSignal(self):
        raise NotImplementedError

    def defaultAction(self):
        self.finished.connect(self.showSender)
        self.sender.backed.connect(self.showEditor)
        self.sender.closed.connect(self.close)

        context.flash.editorMessageChanged.connect(self.showNotification)

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
        self.notificationArea = QLabel()
        self.notificationArea.setStyleSheet('QLabel {color: grey;}')
        bottomLayout.addWidget(self.notificationArea)
        bottomLayout.addWidget(self.nextButton, 0, Qt.AlignRight|Qt.AlignBottom)
        self.bottomBox.setLayout(bottomLayout)
        layout.addWidget(self.bottomBox)

    def showNotification(self, editorname, message):
        if editorname in self.__class__.__name__.lower():
            self.notificationArea.setText(message)
            QTimer.singleShot(10 * 1000, self.notificationArea.clear)

    def previewMessage(self):
        raise NotImplementedError

    def enbaleNextButton(self):
        raise NotImplementedError

    def keyPressEvent(self, event):
        if event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_Return:
            self.beforeNext()

    def closeEvent(self, event):
        self.isStaged = False
