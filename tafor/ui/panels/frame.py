"""Small parts of the main window: the reminder box, the clock strip, and the
board line.

They live together because they share one property -- each is owned by a
single window-level object (a presenter or MainWindow itself) and is used
nowhere else. OutlinedLabel used to sit beside them; it is a drawing label,
so it moved to tafor/ui/map/items.py with the canvas that uses it.
"""

import logging

from PyQt5.QtCore import QCoreApplication, QTimer
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QWidget, QMessageBox

from tafor.core.utils.common import iconPath
from tafor.core.utils.time import utcnow
from tafor.ui.fonts import fixedFont
from tafor.ui.styles import mutedStyle

logger = logging.getLogger('tafor.frame')


class RemindMessageBox(QMessageBox):
    """Alarm dialog."""
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
    """A passive view: the board text is computed by BoardPresenter and
    pushed in through setText()."""

    def __init__(self, parent, container):
        super().__init__(parent)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self.board = QLabel()
        self.board.setFont(fixedFont())
        layout.addWidget(self.board)

        container.addWidget(self)

    def setText(self, text):
        self.board.setText(text)


class Clock(QWidget):

    def __init__(self, parent, container):
        super().__init__(parent)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 5)
        self.setLayout(layout)

        self.zone = QLabel('UTC')
        self.zone.setFont(fixedFont())
        self.zone.setStyleSheet(mutedStyle)
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
        utc = utcnow()
        self.label.setText(utc.strftime('%Y-%m-%d %H:%M:%S'))
