import math
import logging
import datetime

from PyQt5.QtGui import QPixmap, QBrush, QPen, QFont, QFontMetrics, QPainterPath, QPainter
from PyQt5.QtCore import QCoreApplication, QTimer, QSize, Qt, pyqtSignal
from PyQt5.QtWidgets import QWidget, QDialog, QMessageBox, QLabel, QHBoxLayout

from tafor.core.taf import CurrentTaf
from tafor.core.utils.common import iconPath
from tafor.ui.fonts import fixedFont
from tafor.ui.qt import Ui_main_license
from tafor.ui.styles import buttonHoverStyle

logger = logging.getLogger('tafor.widgets')


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
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        icon = QPixmap(iconPath('time.png'))
        title = QCoreApplication.translate('MainWindow', 'Alarm')
        self.setIconPixmap(icon)
        self.setWindowTitle(title)
        self.addButton(QCoreApplication.translate('MainWindow', 'Dismiss'), QMessageBox.AcceptRole)
        self.addButton(QCoreApplication.translate('MainWindow', 'Snooze'), QMessageBox.RejectRole)

    def showEvent(self, event):
        self.parent().showNormal()


class TafBoard(QWidget):

    def __init__(self, parent, container, conf=None, context=None):
        super().__init__(parent)
        self.conf = conf
        self.context = context

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self.board = QLabel()
        self.board.setFont(fixedFont())
        layout.addWidget(self.board)

        container.addWidget(self)

    def updateGui(self):
        self.board.setText(self.current())

    def current(self):
        taf = CurrentTaf(self.context.taf.spec)
        if self.context.taf.message:
            text = ''
        else:
            text = taf.spec.type + taf.period(strict=False, withDay=False)
        return text


class Clock(QWidget):

    def __init__(self, parent, container, context=None):
        super().__init__(parent)
        self.context = context

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 5)
        self.setLayout(layout)

        self.zone = QLabel('UTC')
        self.zone.setFont(fixedFont())
        self.zone.setStyleSheet('QLabel {color: grey;}')
        self.label = QLabel()
        self.label.setFont(fixedFont())
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

    def __init__(self, parent=None, conf=None, context=None):
        super().__init__(parent)
        self.setupUi(self)
        self.conf = conf
        self.context = context
        self.buttonBox.accepted.connect(self.save)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

    def save(self):
        license = self.textarea.toPlainText().strip()
        license = ''.join(license.split())
        if self.context.license.license(license):
            self.setLicense(license)
            self.textarea.clear()
        else:
            text = QCoreApplication.translate('Editor', 'That license key doesn\'t appear to be valid')
            QMessageBox.critical(self, 'Tafor', text)

    def enter(self):
        if not self.conf.airport:
            text = QCoreApplication.translate('Editor', 'Please fill in the airport information or flight information region in the settings first')
            QMessageBox.information(self, 'Tafor', text)
        else:
            self.show()

    def setLicense(self, text):
        if self.conf.license != text:
            self.conf.license = text
            self.licenseChanged.emit()

    def removeLicense(self):
        self.setLicense('')
