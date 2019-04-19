from PyQt5.QtCore import QCoreApplication, QTimer, Qt, pyqtSignal
from PyQt5.QtWidgets import QWidget, QDialog, QMessageBox, QHBoxLayout, QLabel, QPushButton

from tafor import conf
from tafor.utils import boolean


class BaseEditor(QDialog):
    previewSignal = pyqtSignal(dict)

    def __init__(self, parent=None, sender=None):
        super(BaseEditor, self).__init__(parent)
        self.parent = parent
        self.sender = sender

        self.defaultAction()

    def initUI(self):
        raise NotImplementedError

    def bindSignal(self):
        raise NotImplementedError

    def defaultAction(self):
        self.previewSignal.connect(self.showSender)
        self.sender.backSignal.connect(self.show)
        self.sender.closeSignal.connect(self.close)

    def showSender(self, messages):
        alwaysShow = boolean(conf.value('General/AlwaysShowEditor'))
        if not alwaysShow:
            self.hide()

        if self.sender.isVisible():
            self.sender.clear()

        self.sender.receive(messages)
        self.sender.show()

    def showConfigError(self):
        title = QCoreApplication.translate('Editor', 'Config Error')
        text = QCoreApplication.translate('Editor', 'Please complete the basic configuration first, otherwise you cannot send messages correctly')
        QMessageBox.warning(self, title, text)

    def addBottomBox(self, layout):
        self.bottomBox = QWidget()
        bottomLayout = QHBoxLayout()
        self.nextButton = QPushButton()
        self.nextButton.setEnabled(False)
        self.nextButton.setText(QCoreApplication.translate('Editor', 'Next'))
        self.notificationArea = QLabel()
        self.notificationArea.setStyleSheet('QLabel {color: grey;}')
        bottomLayout.addWidget(self.notificationArea)
        bottomLayout.addWidget(self.nextButton, 0, Qt.AlignRight|Qt.AlignBottom)
        self.bottomBox.setLayout(bottomLayout)
        layout.addWidget(self.bottomBox)

    def showNotificationMessage(self, message):
        self.notificationArea.setText(message)
        QTimer.singleShot(10 * 1000, self.notificationArea.clear)

    def assembleMessage(self):
        raise NotImplementedError

    def previewMessage(self):
        raise NotImplementedError

    def enbaleNextButton(self):
        raise NotImplementedError

    def clear(self):
        raise NotImplementedError

    def closeEvent(self, event):
        raise NotImplementedError

