import math
import datetime

from PyQt5.QtGui import QPixmap, QIcon, QBrush, QPen, QFontMetrics, QPainterPath, QPainter
from PyQt5.QtCore import QCoreApplication, QTimer, QSize, Qt, pyqtSignal
from PyQt5.QtWidgets import QWidget, QDialog, QMessageBox, QLabel, QHBoxLayout

from tafor import conf, logger
from tafor.utils import CurrentTaf, timeAgo
from tafor.styles import buttonHoverStyle
from tafor.states import context
from tafor.components.widgets.geometry import SigmetBackground
from tafor.components.ui import main_rc, Ui_main_recent, Ui_main_license


class OutlinedLabel(QLabel):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.w = 1 / 25
        self.mode = True
        self.setBrush(Qt.white)
        self.setPen(Qt.black)

    def scaledOutlineMode(self):
        return self.mode

    def setScaledOutlineMode(self, state):
        self.mode = state

    def outlineThickness(self):
        thickness = self.w * self.font().pointSize() if self.mode else self.w
        if thickness < 1:
            thickness = 1
        return thickness

    def setOutlineThickness(self, value):
        self.w = value

    def setBrush(self, brush):
        if not isinstance(brush, QBrush):
            brush = QBrush(brush)
        self.brush = brush

    def setPen(self, pen):
        if not isinstance(pen, QPen):
            pen = QPen(pen)
        pen.setJoinStyle(Qt.RoundJoin)
        self.pen = pen

    def sizeHint(self):
        w = math.ceil(self.outlineThickness() * 2)
        return super().sizeHint() + QSize(w, w)
    
    def minimumSizeHint(self):
        w = math.ceil(self.outlineThickness() * 2)
        return super().minimumSizeHint() + QSize(w, w)
    
    def paintEvent(self, event):
        w = self.outlineThickness()
        rect = self.rect()
        metrics = QFontMetrics(self.font())
        tr = metrics.boundingRect(self.text()).adjusted(0, 0, w, w)
        if self.indent() == -1:
            if self.frameWidth():
                indent = (metrics.boundingRect('x').width() + w * 2) / 2
            else:
                indent = w
        else:
            indent = self.indent()

        if self.alignment() & Qt.AlignLeft:
            x = rect.left() + indent - min(metrics.leftBearing(self.text()[0]), 0)
        elif self.alignment() & Qt.AlignRight:
            x = rect.x() + rect.width() - indent - tr.width()
        else:
            x = (rect.width() - tr.width()) / 2
            
        if self.alignment() & Qt.AlignTop:
            y = rect.top() + indent + metrics.ascent()
        elif self.alignment() & Qt.AlignBottom:
            y = rect.y() + rect.height() - indent - metrics.descent()
        else:
            y = (rect.height() + metrics.ascent() - metrics.descent()) / 2

        path = QPainterPath()
        path.addText(x, y, self.font(), self.text())
        qp = QPainter(self)
        qp.setRenderHint(QPainter.Antialiasing)

        self.pen.setWidthF(w * 2)
        qp.strokePath(path, self.pen)
        if 1 < self.brush.style() < 15:
            qp.fillPath(path, self.palette().window())
        qp.fillPath(path, self.brush)


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
        self.remind = False
        self.updateText()
        self.updateButton()
        self.bindSignal()

        if hasattr(self.item, 'validations'):
            self.notificationMode()
            self.timer = QTimer(self)
            self.timer.timeout.connect(self.countdown)
            self.timer.start(1000)
            self.countdown()
        else:
            self.reviewMode()

        font = context.environ.fixedFont()
        self.setFont(font)
        self.timeLabel.setFont(font)
        font.setPointSize(12)
        self.text.setFont(font)
        layout.addWidget(self)

        if self.item.type in ['WS', 'WC', 'WV', 'WA'] and not self.item.isCnl():
            parser = self.item.parser()
            geos = parser.geo(context.layer.boundaries(), trim=True)
            if geos['features']:
                height = self.group.sizeHint().height() - 30
                size = (int(height / 0.6), height)
                try:
                    background = SigmetBackground(geos, size=size, parent=self)
                    background.adjustSize()
                    background.move(self.width() - background.width() - 110, 16)
                    background.setAttribute(Qt.WA_TransparentForMouseEvents)

                except Exception as e:
                    logger.exception(e)

    def countdown(self):
        created = self.item.created
        now = datetime.datetime.utcnow()
        expire = 10

        if now - created > datetime.timedelta(minutes=expire):
            self.timer.stop()
            context.notification.metar.clear()

        ago = timeAgo(created, now)
        self.timeLabel.setText(ago.capitalize())

    def reviewMode(self):
        self.replyButton.hide()
        self.signLabel.hide()
        self.reminderButton.hide()

        if self.item.type not in ['FC', 'FT', 'WS', 'WC', 'WV', 'WA']:
            self.markButton.hide()
            return

        if self.item.type in ['FC', 'FT']:
            self.reviewer = self.parent.tafSender
        else:
            self.reviewer = self.parent.sigmetSender
            if self.item.uuid in context.sigmet.state():
                self.remind = True
            else:
                self.remind = False

            self.updateGui()
            self.reminderButton.show()

        if self.item.confirmed:
            icon = ':/checkmark.png'
        else:
            icon = ':/cross.png'

        self.markButton.setIcon(QIcon(icon))

    def notificationMode(self):
        self.markButton.hide()
        self.reminderButton.hide()
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
        self.reminderButton.clicked.connect(self.updateRemindState)

    def updateButton(self):
        self.replyButton.setIcon(QIcon(':/reply-arrow.png'))
        self.replyButton.setStyleSheet(buttonHoverStyle)
        self.markButton.setStyleSheet(buttonHoverStyle)
        self.reminderButton.setStyleSheet(buttonHoverStyle)

    def updateText(self):
        self.group.setTitle(self.item.type)
        self.timeLabel.setText(self.item.created.strftime('%Y-%m-%d %H:%M:%S'))
        self.text.setText(self.item.report)

    def updateGui(self):
        if self.remind:
            icon = ':/reminder.png'
        else:
            icon = ':/no-reminder.png'

        self.reminderButton.setIcon(QIcon(icon))
        self.reminderButton.setStyleSheet(buttonHoverStyle)

    def updateRemindState(self):
        if self.remind:
            context.sigmet.remove(self.item.uuid)
        else:
            time = self.item.expired()
            sig = self.item.parser()
            context.sigmet.add(self.item.uuid, sig, time)

        self.remind = not self.remind
        self.updateGui()

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
        self.board.setFont(context.environ.fixedFont())
        layout.addWidget(self.board)

        container.addWidget(self)

    def updateGui(self):
        self.board.setText(self.current())

    def current(self):
        taf = CurrentTaf(context.taf.spec)
        if context.taf.message():
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
        self.zone.setFont(context.environ.fixedFont())
        self.zone.setStyleSheet('QLabel {color: grey;}')
        self.label = QLabel()
        self.label.setFont(context.environ.fixedFont())
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

    licenseChanged = pyqtSignal()

    def __init__(self, parent):
        super(LicenseEditor, self).__init__(parent)
        self.setupUi(self)
        self.parent = parent
        self.buttonBox.accepted.connect(self.save)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

    def save(self):
        license = self.textarea.toPlainText().strip()
        license = ''.join(license.split())
        if context.environ.license(license):
            self.setLicense(license)
            self.textarea.clear()
        else:
            text = QCoreApplication.translate('Editor', 'That license key doesn\'t appear to be valid')
            QMessageBox.critical(self, 'Tafor', text)

    def enter(self):
        if not conf.value('Message/ICAO'):
            text = QCoreApplication.translate('Editor', 'Please fill in the airport information or flight information region in the settings first')
            QMessageBox.information(self, 'Tafor', text)
        else:
            self.show()

    def setLicense(self, text):
        prev = conf.value('License')
        conf.setValue('License', text)

        if prev != text:
            self.licenseChanged.emit()

    def removeLicense(self):
        self.setLicense('')
