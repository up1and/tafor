from PyQt5.QtCore import QCoreApplication, pyqtSignal
from PyQt5.QtWidgets import QDialog, QMessageBox

from tafor import boolean, conf


class BaseEditor(QDialog):
    previewSignal = pyqtSignal(dict)

    def __init__(self, parent=None, sender=None):
        super(BaseEditor, self).__init__(parent)
        self.parent = parent
        self.sender = sender

        self.actionController()

    def initUI(self):
        raise NotImplementedError

    def bindSignal(self):
    	raise NotImplementedError

    def actionController(self):
        alwaysShow = boolean(conf.value('General/AlwaysShowEditor'))

        if not alwaysShow:
            self.previewSignal.connect(self.hide)

        self.previewSignal.connect(self.sender.receive)
        self.previewSignal.connect(self.sender.show)
        self.sender.sendSignal.connect(self.parent.updateGui)
        self.sender.backSignal.connect(self.show)
        self.sender.closeSignal.connect(self.close)

    def showConfigError(self):
        title = QCoreApplication.translate('Editor', 'Config Error')
        text = QCoreApplication.translate('Editor', 'Please complete the basic configuration first, otherwise you cannot send messages correctly.')
        QMessageBox.warning(self, title, text)

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

