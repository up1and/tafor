from PyQt5.QtCore import QCoreApplication, QTimer, Qt, pyqtSignal
from PyQt5.QtWidgets import QWidget, QDialog, QMessageBox, QHBoxLayout, QLabel, QPushButton


class BaseEditor(QDialog):

    finished = pyqtSignal(object)

    # Subclass sets this to the conf group checked before the editor can show
    confGroup = None

    def __init__(self, parent=None, sender=None, conf=None, context=None, database=None):
        super().__init__(parent)
        self.parent = parent
        self.sender = sender
        self.conf = conf
        self.context = context
        self.database = database
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

    def showNotification(self, editorname, message):
        if editorname in self.__class__.__name__.lower():
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
        if self.confGroup and not self.conf.checkCompleteness(self.confGroup):
            QTimer.singleShot(0, self.showConfigError)
            return

        if not self.isStaged:
            self.onFirstShow()

    def closeEvent(self, event):
        self.isStaged = False
        self.onClose()
