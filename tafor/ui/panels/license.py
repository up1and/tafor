"""The license key dialog.

It is a form, not a panel: the operator types a key, the dialog reports
whether it was accepted, and the presenter behind it does the verifying.
"""

from PyQt5.QtCore import QCoreApplication, Qt, pyqtSignal
from PyQt5.QtWidgets import QDialog, QMessageBox

from tafor.ui.qt import Ui_main_license


class LicenseEditor(QDialog, Ui_main_license.Ui_Editor):
    """A passive dialog: it normalises the typed key and reports it through
    ``submitted``; the verification and the conf write live in the
    LicensePresenter."""

    submitted = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.buttonBox.accepted.connect(self.submit)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

    def submit(self):
        license = self.textarea.toPlainText().strip()
        license = ''.join(license.split())
        self.submitted.emit(license)

    def clear(self):
        self.textarea.clear()

    def showInvalid(self):
        text = QCoreApplication.translate('Editor', 'That license key doesn\'t appear to be valid')
        QMessageBox.critical(self, 'Tafor', text)

    def showAirportHint(self):
        text = QCoreApplication.translate('Editor', 'Please fill in the airport information or flight information region in the settings first')
        QMessageBox.information(self, 'Tafor', text)
