import datetime

from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtCore import QCoreApplication, QTimer, Qt
from PyQt5.QtWidgets import QWidget, QDialog, QMessageBox, QLabel, QHBoxLayout

from tafor import conf
from tafor.utils import CurrentTaf, CheckTaf
from tafor.styles import buttonHoverStyle
from tafor.states import context
from tafor.components.ui import main_rc, Ui_main_recent, Ui_main_license


class RemindMessageBox(QMessageBox):
    """闹钟对话框"""
    def __init__(self, parent):
        super(RemindMessageBox, self).__init__(parent=parent)
        icon = QPixmap(':/time.png')
        title = QCoreApplication.translate('MainWindow', 'Alarm')
        self.setIconPixmap(icon)
        self.setWindowTitle(title)
        self.addButton(QCoreApplication.translate('MainWindow', 'Snooze'), QMessageBox.ApplyRole)
        self.addButton(QCoreApplication.translate('MainWindow', 'Dismiss'), QMessageBox.RejectRole)
        self.parent = parent

    def showEvent(self, event):
        self.parent.showNormal()


class RecentMessage(QWidget, Ui_main_recent.Ui_Recent):

    def __init__(self, parent, layout, item):
        super(RecentMessage, self).__init__(parent)
        self.setupUi(self)
        self.item = item
        self.parent = parent
        self.reviewer = None
        self.setText()
        self.setButton()
        layout.addWidget(self)

    def setButton(self):
        if self.item.tt not in ['FC', 'FT', 'WS', 'WC', 'WV', 'WA']:
            self.markButton.hide()
            return

        if self.item.tt in ['FC', 'FT']:
            self.reviewer = self.parent.tafSender
        else:
            self.reviewer = self.parent.sigmetSender

        if self.item.confirmed:
            iconSrc = ':/checkmark.png'
        else:
            iconSrc = ':/cross.png'

        self.markButton.setIcon(QIcon(iconSrc))
        self.markButton.setStyleSheet(buttonHoverStyle)
        self.markButton.clicked.connect(self.view)

    def setText(self):
        self.groupBox.setTitle(self.item.tt)
        self.sendTime.setText(self.item.sent.strftime('%Y-%m-%d %H:%M:%S'))
        self.rpt.setText(self.item.report)
        self.rpt.setStyleSheet('font: 14px "Segoe UI";')

    def view(self):
        message = {
            'uuid': self.item.uuid,
            'item': self.item,
            'sign': self.item.sign,
            'rpt': self.item.rpt,
            'full': '\n'.join(filter(None, [self.item.sign, self.item.rpt]))
        }

        self.reviewer.receive(message, mode='view')
        self.reviewer.show()


class TafBoard(QWidget):

    def __init__(self, parent, container):
        super(TafBoard, self).__init__(parent)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self.board = QLabel()
        layout.addWidget(self.board)

        container.addWidget(self)

    def updateGui(self):
        self.board.setText(self.current())

    def current(self):
        taf = CurrentTaf(context.taf.spec)
        check = CheckTaf(taf)
        if check.local():
            text = ''
        else:
            text = taf.spec.tt + taf.period(strict=False, withDay=False)
        return text


class Clock(QWidget):

    def __init__(self, parent, container):
        super(Clock, self).__init__(parent)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 5)
        self.setLayout(layout)

        self.zone = QLabel('UTC')
        self.zone.setStyleSheet('QLabel {color: grey;}')
        self.label = QLabel()
        layout.addWidget(self.zone)
        layout.addWidget(self.label)

        self.timer = QTimer()
        self.timer.timeout.connect(self.updateGui)
        self.timer.start(1 * 1000)

        self.updateGui()

        container.addWidget(self)

    def updateGui(self):
        utc = datetime.datetime.utcnow()
        self.label.setText(utc.strftime('%Y-%m-%d %H:%M:%S'))


class LicenseEditor(QDialog, Ui_main_license.Ui_Editor):

    def __init__(self, parent):
        super(LicenseEditor, self).__init__(parent)
        self.setupUi(self)
        self.parent = parent
        self.buttonBox.accepted.connect(self.save)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

    def save(self):
        license = self.textarea.toPlainText().strip()
        conf.setValue('License', license)
        if context.environ.license():
            self.parent.setAboutMenu()
        else:
            conf.setValue('License', '')
            text = QCoreApplication.translate('Editor', 'That license key doesn\'t appear to be valid')
            QMessageBox.critical(self, 'Tafor', text)

    def enter(self):
        if not conf.value('Message/ICAO'):
            text = QCoreApplication.translate('Editor', 'Please fill in the airport information or flight information region in the settings first')
            QMessageBox.information(self, 'Tafor', text)
        else:
            self.show()
