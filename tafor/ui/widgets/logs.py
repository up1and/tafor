"""The log window.

A read-only view of the ring in ``core.utils.log``. It never opens the log
file: the file rotates, may not be writable, and is someone else's business.
The panel asks the ring what is new on a timer and draws that.

Pulling rather than pushing is deliberate. Records are written from worker
threads and from the RPC server's threads as well as from the GUI thread, so
a signal per record would mean a queued connection from every one of them --
and a burst of logging would then arrive as a burst of events competing with
the painting that is already struggling. A timer reads whatever accumulated
since the last look and costs nothing at all while the panel is closed.
"""

import datetime
import logging

from PyQt5.QtCore import QCoreApplication, QEvent, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QPalette, QTextCharFormat, QTextCursor
from PyQt5.QtWidgets import (QCheckBox, QComboBox, QDialog, QHBoxLayout, QLabel,
    QLineEdit, QPlainTextEdit, QVBoxLayout)

from tafor.core.utils.log import logBuffer
from tafor.ui.fonts import fixedFont


class LogPanel(QDialog):
    """One window, owned by the main window for as long as the app lives.

    Closing hides it rather than discarding it, so its filters and its
    scroll position are still there next time. ``closed`` lets the presenter
    stop reading the ring while nobody is looking. The window holds no
    records of its own: it draws what the ring holds and forgets at
    refiltering whatever the ring has evicted since.
    """

    closed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.seq = 0            # how far into the ring this panel has read

        self.setupUi()
        self.bindSignal()

    def setupUi(self):
        self.setWindowTitle(QCoreApplication.translate('LogPanel', 'View Logs'))
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setMinimumSize(860, 480)

        self.levelLabel = QLabel(QCoreApplication.translate('LogPanel', 'Level'))
        self.levelBox = QComboBox()
        for name in ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'):
            # Numbers from the standard library's own level table --
            # getLevelName accepts names too (3.4+). WARN and FATAL are
            # aliases, same numbers, not offered twice.
            level = logging.getLevelName(name)
            # The ring is filled at the logger's own level; a level under it
            # can never appear, so it is not offered. The number rides along
            # as the item's data, which is what the filter compares against.
            if level >= logging.getLogger('tafor').level:
                self.levelBox.addItem(name, level)
        self.levelBox.setCurrentText('INFO')

        self.filterLabel = QLabel(QCoreApplication.translate('LogPanel', 'Filter'))
        self.filterEdit = QLineEdit()
        self.filterEdit.setPlaceholderText(
            QCoreApplication.translate('LogPanel', 'Show lines containing'))

        self.followBox = QCheckBox(QCoreApplication.translate('LogPanel', 'Follow'))
        self.followBox.setChecked(True)
        self.followBox.setToolTip(QCoreApplication.translate(
            'LogPanel', 'Scroll to the newest line as it arrives'))

        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)
        # Appending is the widget's whole life; undo history would only grow
        # with every tick and serve a view nobody can edit.
        self.text.setUndoRedoEnabled(False)
        self.text.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.text.setFont(fixedFont())
        # The plain surface of a read-only view follows the theme; a literal
        # would stay white on a dark desktop.
        self.text.setBackgroundRole(QPalette.Base)

        top = QHBoxLayout()
        top.addWidget(self.levelLabel)
        top.addWidget(self.levelBox)
        top.addSpacing(12)
        top.addWidget(self.filterLabel)
        top.addWidget(self.filterEdit)
        top.addStretch(1)
        top.addWidget(self.followBox)

        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self.text)

    def bindSignal(self):
        self.levelBox.currentTextChanged.connect(self.refilter)
        self.filterEdit.textChanged.connect(self.refilter)

    def showEvent(self, event):
        """Read what is already in the ring before the window is painted.

        The records were logged while the panel was closed, so waiting for
        the first tick would open an empty window and fill it half a second
        later.
        """
        super().showEvent(event)
        self.poll()

    def changeEvent(self, event):
        """A theme switch changes what the level hues resolve to."""
        super().changeEvent(event)
        if event.type() == QEvent.PaletteChange:
            self.refilter()

    def poll(self):
        """Take whatever the ring has and draw it."""
        new = logBuffer.since(self.seq)
        if not new:
            return

        self.seq = new[-1].seq
        self.append(new)

    def append(self, records):
        """Add the records that pass the filters, at the end."""
        keep = [record for record in records if self.accepts(record)]
        if not keep:
            return

        bar = self.text.verticalScrollBar()
        staying = self.followBox.isChecked() or self.atBottom()
        position = bar.value()

        # Whether the window already holds lines decides the separator
        # before every record, not just between the ones arriving now: a
        # record appended in an earlier poll is just as much a previous line
        # as one appended a moment ago, and without this the two runs are
        # written into the same block and read as one line. isEmpty() is
        # the O(1) wording of the same fact: a document with a single
        # block whose only character is the block separator.
        started = not self.text.document().isEmpty()

        cursor = self.text.textCursor()
        cursor.movePosition(QTextCursor.End)
        for index, record in enumerate(keep):
            fmt = self.levelFormat(record)
            if started or index:
                # The separator takes the incoming record's format, so a
                # filled critical line cannot bleed its background onto
                # the plain line after it.
                cursor.setCharFormat(fmt)
                cursor.insertBlock()
            # The format goes on the block being started, so a line -- and an
            # expanded traceback under it -- is coloured as a whole.
            cursor.insertText(self.format(record), fmt)
        self.text.setTextCursor(cursor)

        if staying:
            bar.setValue(bar.maximum())
        else:
            # The operator was reading further up and has stopped following;
            # the line under their eye must not move as new ones arrive.
            bar.setValue(position)

    def accepts(self, record):
        if record.level < self.levelBox.currentData():
            return False

        needle = self.filterEdit.text().strip()
        if not needle:
            return True

        haystack = '{} {}'.format(record.name, record.message)
        return needle.lower() in haystack.lower()

    def format(self, record):
        """One line: date, time, level, logger, message, then the traceback.

        The full date rides along because a shift runs past midnight and
        the window keeps what was logged days ago: without the year,
        opened-fresh can only guess which year those stamps fell in.
        The traceback keeps its own lines rather than being truncated away:
        it is the part that says what actually broke.
        """
        stamp = datetime.datetime.fromtimestamp(record.created)
        line = '{} {:<8} [{}] {}'.format(
            stamp.strftime('%m-%d %H:%M:%S'),
            record.levelname, record.name, record.message)
        if record.traceback:
            line = '{}\n{}'.format(line, record.traceback)
        return line

    def levelFormat(self, record):
        """The format for one line, on the live palette.

        Information takes the ordinary text role. The two levels that ask
        for attention take a hue, lifted to a brightness that sits against
        the surface the theme actually chose: a literal red glares on a
        light desktop and disappears on a dark one, so the value follows
        the base instead of the level.
        """
        fmt = QTextCharFormat()
        fmt.setFont(fixedFont())

        # Critical reverses the surface: red ground, light text, no doubt
        # about which line is the emergency. Theme-agnostic on purpose --
        # a filled bar asks nothing of the desktop it landed on.
        if record.level == logging.CRITICAL:
            fmt.setBackground(QColor.fromHsv(0, 255, 205, 255))
            fmt.setForeground(QColor.fromHsv(0, 0, 250, 255))
            return fmt

        hues = {logging.WARNING: 38, logging.ERROR: 0}
        hue = hues.get(record.level)
        if hue is None:
            role = QPalette.PlaceholderText if record.level < logging.INFO else QPalette.Text
            fmt.setForeground(self.palette().color(role))
            return fmt

        base = self.palette().color(QPalette.Base)
        value = 235 if base.lightness() < 128 else 200
        fmt.setForeground(QColor.fromHsv(hue, 255, value, 255))
        return fmt

    def refilter(self):
        """Redraw what the ring holds against the new filter.

        The ring is the only record the window has, so this is a full
        redraw of it: widening the filter brings lines back, and the lines
        the ring has already evicted stay gone for good.
        """
        self.text.setPlainText('')
        self.append(logBuffer.records)

    def atBottom(self):
        bar = self.text.verticalScrollBar()
        return bar.value() >= bar.maximum() - 1

    def closeEvent(self, event):
        # Deliberately no super() toward QDialog: on this binding the
        # inherited slot returns the event ignored, and the window then
        # survives its own close button. Closing is always welcome there.
        event.accept()
        self.closed.emit()

    def reject(self):
        """Send ESC and friends through close instead of hide.

        A QDialog's own reject hides without a closeEvent, which would
        strand the ``closed`` signal and leave the presenter polling for
        an audience that has left.
        """
        self.close()
