import datetime

from PyQt5.QtGui import QPixmap, QIcon, QFontDatabase
from PyQt5.QtCore import QCoreApplication, QTimer, Qt
from PyQt5.QtWidgets import QWidget, QDialog, QMessageBox, QLabel, QHBoxLayout

from tafor import conf
from tafor.utils import CurrentTaf, CheckTaf, timeAgo
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
        self.bindSignal()

        if hasattr(self.item, 'validations'):
            self.setNotificationMode()
            self.timer = QTimer(self)
            self.timer.timeout.connect(self.countdown)
            self.timer.start(1000)
            self.countdown()
        else:
            self.setReviewMode()

        layout.addWidget(self)

    def countdown(self):
        created = self.item.created
        now = datetime.datetime.utcnow()
        expire = 10

        if now - created > datetime.timedelta(minutes=expire):
            self.timer.stop()
            context.notification.metar.clear()

        ago = timeAgo(created, now)
        self.timeLabel.setText(ago.capitalize())

    def setReviewMode(self):
        self.replyButton.hide()
        self.signLabel.hide()

        if self.item.type not in ['FC', 'FT', 'WS', 'WC', 'WV', 'WA']:
            self.markButton.hide()
            return

        if self.item.type in ['FC', 'FT']:
            self.reviewer = self.parent.tafSender
        else:
            self.reviewer = self.parent.sigmetSender

        if self.item.confirmed:
            iconSrc = ':/checkmark.png'
        else:
            iconSrc = ':/cross.png'

        self.markButton.setIcon(QIcon(iconSrc))

    def setNotificationMode(self):
        self.markButton.hide()
        isValidationEnabled = self.item.validations['validation']
        isPass = self.item.validations['pass']
        
        if isValidationEnabled:
            if isPass:
                icon = ':/protect.png'
            else:
                icon = ':/warning-shield.png'

            shieldIcon = QPixmap(icon)
            self.signLabel.setPixmap(shieldIcon.scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.signLabel.hide()

        style = """
            QGroupBox {
                border: 2px dotted #dcdcdc;
            }
            """
        self.setStyleSheet(style)

    def bindSignal(self):
        self.markButton.clicked.connect(self.review)
        self.replyButton.clicked.connect(self.parent.trendEditor.show)

    def setButton(self):
        self.replyButton.setIcon(QIcon(':/reply-arrow.png'))
        self.replyButton.setStyleSheet(buttonHoverStyle)
        self.markButton.setStyleSheet(buttonHoverStyle)

    def setText(self):
        self.groupBox.setTitle(self.item.type)
        time = self.item.sent if hasattr(self.item, 'sent') else self.item.created
        self.timeLabel.setText(time.strftime('%Y-%m-%d %H:%M:%S'))
        self.text.setText(self.item.report)
        font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        self.text.setStyleSheet('font: 13px "Microsoft YaHei", "{}";'.format(font.family()))

    def review(self):
        self.reviewer.receive(self.item)
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
            text = taf.spec.type + taf.period(strict=False, withDay=False)
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
        license = ''.join(license.split())
        conf.setValue('License', license)
        if context.environ.license():
            self.parent.setAboutMenu()
            self.textarea.clear()
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
