import os
import datetime

from PyQt5.QtGui import QIcon, QRegExpValidator, QColor, QPixmap
from PyQt5.QtCore import (QCoreApplication, QStandardPaths, QRegExp, QDate, QEvent, Qt, QPoint, QRect,
                          QAbstractTableModel, QModelIndex, QTimer, pyqtSignal)
from PyQt5.QtWidgets import (QDialog, QFileDialog, QWidget, QDialogButtonBox, QHeaderView, QLabel, QCalendarWidget,
    QVBoxLayout, QFormLayout, QLabel, QDateEdit, QHBoxLayout, QLayout, QApplication,
    QStyle, QStyledItemDelegate, QStyleOptionViewItem)

from tafor.core.models import Metar, Sigmet, Taf
from tafor.core.utils.common import iconPath
from tafor.ui.qt import Ui_main_table
from tafor.ui.fonts import fixedFont
from tafor.ui.styles import applyCalendarStyle, mutedStyle
from tafor.ui.workers import ExportRecordWorker



class ExportDialog(QDialog):

    def __init__(self, workers, table=None):
        super().__init__(table)
        self.table = table
        self.workers = workers

        self.setupUi()
        self.bindSignal()

    def setupUi(self):
        self.verticalLayout = QVBoxLayout(self)
        self.verticalLayout.setSizeConstraint(QLayout.SetFixedSize)
        self.formLayout = QFormLayout()
        self.startDateLabel = QLabel(self)
        self.formLayout.setWidget(0, QFormLayout.LabelRole, self.startDateLabel)
        self.startDate = QDateEdit(self)
        self.startDate.setCalendarPopup(True)
        self.formLayout.setWidget(0, QFormLayout.FieldRole, self.startDate)
        self.endDateLabel = QLabel(self)
        self.formLayout.setWidget(1, QFormLayout.LabelRole, self.endDateLabel)
        self.endDate = QDateEdit(self)
        self.endDate.setCalendarPopup(True)
        self.formLayout.setWidget(1, QFormLayout.FieldRole, self.endDate)
        self.countLabel = QLabel(self)
        self.countLabel.setMinimumSize(180, 0)
        self.countLabel.setStyleSheet(mutedStyle)
        self.formLayout.setWidget(2, QFormLayout.SpanningRole, self.countLabel)
        self.verticalLayout.addLayout(self.formLayout)
        self.buttonBox = QDialogButtonBox(self)
        self.buttonBox.setOrientation(Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Save)
        self.verticalLayout.addWidget(self.buttonBox)

        self.startDate.calendarWidget().setHorizontalHeaderFormat(QCalendarWidget.NoHorizontalHeader)
        self.endDate.calendarWidget().setHorizontalHeaderFormat(QCalendarWidget.NoHorizontalHeader)
        applyCalendarStyle(self.startDate.calendarWidget())
        applyCalendarStyle(self.endDate.calendarWidget())

        self.setWindowTitle(QCoreApplication.translate('DataTable', 'Export Records'))
        self.startDateLabel.setText(QCoreApplication.translate('DataTable', 'Start Date'))
        self.endDateLabel.setText(QCoreApplication.translate('DataTable', 'End Date'))

        self.saveButton = self.buttonBox.button(QDialogButtonBox.Save)
        self.saveButton.setText(QCoreApplication.translate('DataTable', 'Export'))

        self.setWindowModality(Qt.WindowModal)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

    def bindSignal(self):
        self.startDate.dateChanged.connect(self.updateExportStatus)
        self.endDate.dateChanged.connect(self.updateExportStatus)
        self.saveButton.clicked.connect(self.exportToCsv)

    def showEvent(self, event):
        today = QDate.currentDate()
        start = QDate(today.year(), today.month(), 1)
        self.startDate.setDate(start)
        self.startDate.setMaximumDate(today)
        self.endDate.setDate(today)
        self.endDate.setMaximumDate(today)

        self.updateExportStatus()

    def closeEvent(self, event):
        self.countLabel.setText('')

    def updateExportStatus(self):
        start, end = self.startDate.date().toPyDate(), self.endDate.date().toPyDate()
        count = self.table.repository.count(
            self.table.model, category=self.table.category, start=start, end=end)

        if count == 0:
            self.countLabel.setText('')
            self.saveButton.setEnabled(False)
        else:
            text = QCoreApplication.translate('DataTable', '{} records found')
            text = text.format(count)
            self.countLabel.setText(text)
            self.saveButton.setEnabled(True)

    def filteredReport(self):
        model = self.table.model
        category = self.table.category
        start, end = self.startDate.date().toPyDate(), self.endDate.date().toPyDate()
        return self.table.repository.filtered(model, category=category, start=start, end=end)

    def exportToCsv(self):
        fmt = '%Y-%m-%d'
        start, end = self.startDate.date().toPyDate(), self.endDate.date().toPyDate()
        name = '{} {} {}.csv'.format(self.table.category, start.strftime(fmt), end.strftime(fmt))
        title = QCoreApplication.translate('DataTable', 'Save as CSV')
        path = QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation)
        filename, _ = QFileDialog.getSaveFileName(self, title, os.path.join(path, name), '(*.csv)')

        if not filename:
            return

        headers = ('type', 'text', 'created')
        data = [(e.type, e.text, e.created) for e in self.filteredReport()]

        worker, thread = self.workers.create(ExportRecordWorker, filename, data, headers=headers)
        worker.finished.connect(self.close)
        thread.start()


class CalendarPopup(QWidget):
    """Frameless popup owning the date picker, anchored above the calendar button."""

    def __init__(self, parent=None):
        super().__init__(parent, Qt.Popup)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.calendar = QCalendarWidget(self)
        self.calendar.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        applyCalendarStyle(self.calendar)
        layout.addWidget(self.calendar)


class RecordTableModel(QAbstractTableModel):
    """One page of records, rendered by role instead of by widgets.

    Paging and searching happen in the repository, so the model only ever
    holds the current page. Sorting is deliberately left alone: re-ordering
    one page would not re-order the result set.
    """

    def __init__(self, display, color=None, parent=None):
        super().__init__(parent)
        self.records = []
        self.display = display
        self.color = color or (lambda item: None)
        self.icons = {
            True: self.icon('checkmark.png'),
            False: self.icon('questionmark.png'),
        }

    @staticmethod
    def icon(name):
        return QPixmap(iconPath(name)).scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation)

    def setRecords(self, records):
        self.beginResetModel()
        self.records = list(records)
        self.endResetModel()

    def record(self, index):
        return self.records[index.row()] if index.isValid() else None

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.records)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else 4

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation != Qt.Horizontal or role != Qt.DisplayRole:
            return None

        # The literals stay at the call site: lupdate extracts source strings
        # from translate() arguments, not from a table they are read out of.
        if section == 0:
            return QCoreApplication.translate('DataTable', 'Type')
        if section == 1:
            return QCoreApplication.translate('DataTable', 'Message Content')
        if section == 2:
            return QCoreApplication.translate('DataTable', 'Sent Time')
        if section == 3:
            return QCoreApplication.translate('DataTable', 'Check')

        return None

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None

        item = self.records[index.row()]
        column = index.column()

        if role == Qt.DisplayRole:
            if column == 0:
                return item.type
            if column == 1:
                return self.display(item)
            if column == 2:
                return item.created.strftime('%Y-%m-%d %H:%M:%S') if item.created else ''
            return None

        if role == Qt.TextAlignmentRole and column in (0, 2, 3):
            return Qt.AlignCenter

        if role == Qt.ForegroundRole and column < 3:
            return self.color(item)

        if role == Qt.DecorationRole and column == 3:
            return self.icons[bool(item.confirmed)]

        return None

    def flags(self, index):
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable


class CenteredIconDelegate(QStyledItemDelegate):
    """Draws a decoration centred in its cell; Qt pins it to the left edge."""

    def paint(self, painter, option, index):
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        pixmap = index.data(Qt.DecorationRole)
        if not isinstance(pixmap, QPixmap) or pixmap.isNull():
            super().paint(painter, option, index)
            return

        # Let the style draw the background and selection, then place the
        # icon ourselves: drawing it through the option pins it left.
        opt.icon = QIcon()
        opt.text = ''
        style = opt.widget.style() if opt.widget else QApplication.style()
        style.drawControl(QStyle.CE_ItemViewItem, opt, painter, opt.widget)

        rect = QRect(QPoint(0, 0), pixmap.size())
        rect.moveCenter(opt.rect.center())
        painter.drawPixmap(rect, pixmap)


class BaseDataTable(QWidget, Ui_main_table.Ui_DataTable):

    chartClicked = pyqtSignal()
    statusMessage = pyqtSignal(str, int)

    def __init__(self, parent, layout, workers, repository=None):
        super().__init__(parent)
        self.workers = workers
        self.perPage = 12
        self.extraColumnWidths = {}
        self.setupUi(self)
        self.records = RecordTableModel(self.displayText, self.rowColor, self)
        self.table.setModel(self.records)
        self.setupStyle()
        self.setupValidator()
        self.page = 1
        self.pagination = None
        self.category = ''
        self.date = None
        self.keywords = []
        self.color = QColor(200, 20, 40)

        self.repository = repository
        self.exportDialog = ExportDialog(workers, self)

        self.calendarPopup = CalendarPopup(self)
        self.calendarPopup.calendar.clicked.connect(self.setCalendar)
        self.calendarPopup.installEventFilter(self)

        self.searchTimer = QTimer(self)
        self.searchTimer.setSingleShot(True)
        self.searchTimer.setInterval(200)
        self.searchTimer.timeout.connect(self.applySearch)

        font = fixedFont()
        font.setPointSize(10)
        self.table.setFont(font)

        layout.addWidget(self)
        self.bindSignal()

    def bindSignal(self):
        self.search.textEdited.connect(self.autoSearch)
        self.table.doubleClicked.connect(self.copySelected)
        self.prevButton.clicked.connect(self.prev)
        self.nextButton.clicked.connect(self.next)
        self.table.selectionModel().selectionChanged.connect(lambda *_: self.updateInfoButton())
        self.infoButton.clicked.connect(self.view)
        self.calendarButton.clicked.connect(self.showCalendarPopup)
        self.chartButton.clicked.connect(self.chartClicked.emit)
        self.exportButton.clicked.connect(self.exportDialog.show)

    def showCalendarPopup(self):
        # The button doubles as the clear action while a date filter is active
        if self.date:
            self.setCalendar(None)
            return

        self.calendarPopup.calendar.setSelectedDate(QDate.currentDate())
        self.calendarPopup.calendar.setMaximumDate(QDate.currentDate())
        self.calendarPopup.ensurePolished()
        self.calendarPopup.adjustSize()
        self.calendarPopup.show()
        # The polished height is only final after show(); move afterwards so
        # the bottom edge sits exactly on the button's top edge
        anchor = self.calendarButton.mapToGlobal(QPoint(0, 0))
        self.calendarPopup.move(anchor.x(), anchor.y() - self.calendarPopup.height())

    def eventFilter(self, obj, event):
        # A click outside the popup closes it without picking a date; realign
        # the checkable button with the (unchanged) filter state.
        if obj is self.calendarPopup and event.type() == QEvent.Hide:
            self.updateCalendarButton()
        return super().eventFilter(obj, event)

    def setCalendar(self, date):
        if date:
            self.date = date.toPyDate()
        else:
            self.date = None

        self.setPage(1)

    def setupStyle(self):
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setItemDelegateForColumn(3, CenteredIconDelegate(self.table))
        self.table.setStyleSheet('QTableView {border: 0;} QTableView::item {padding: 5px 0;}')

        self.prevButton.setIcon(QIcon(iconPath('prev.png')))
        self.nextButton.setIcon(QIcon(iconPath('next.png')))
        self.chartButton.setIcon(QIcon(iconPath('chart.png')))
        self.calendarButton.setIcon(QIcon(iconPath('search.png')))
        self.exportButton.setIcon(QIcon(iconPath('export.png')))
        self.infoButton.setIcon(QIcon(iconPath('info.png')))
        self.infoButton.hide()
        self.chartButton.hide()

    def setupValidator(self):
        pattern = r'[a-zA-Z0-9\s\/\-\+]+'
        word = QRegExpValidator(QRegExp(pattern))
        self.search.setValidator(word)

    def autoSearch(self):
        # Case conversion is instant so the field never shows lowercase;
        # only the query is debounced.
        text = self.search.text()
        upper = text.upper()
        if upper != text:
            position = self.search.cursorPosition()
            self.search.setText(upper)
            self.search.setCursorPosition(position)
        self.searchTimer.start()

    def applySearch(self):
        self.keywords = self.search.text().split()
        self.setPage(1)

    def hideColumns(self):
        raise NotImplementedError

    def prev(self):
        if self.pagination.hasPrev:
            self.setPage(self.pagination.prevNum)
        else:
            if self.date:
                self.date -= datetime.timedelta(days=1)
                self.setPage(1)

    def next(self):
        if self.pagination.hasNext:
            self.setPage(self.pagination.nextNum)
        else:
            if self.date:
                self.date += datetime.timedelta(days=1)
                self.setPage(1)

    def setPage(self, page):
        self.page = page
        self.updateGui()

    def updateGui(self):
        self.updateTable()
        self.updatePages()
        self.updateInfoButton()
        self.updateCalendarButton()

    def updateTable(self):
        self.pagination = self.repository.paginated(
            self.model, category=self.category, date=self.date, keywords=self.keywords,
            page=self.page, perPage=self.perPage)

        self.records.setRecords(self.pagination.items)

        self.table.setColumnWidth(0, 50)
        self.table.setColumnWidth(2, 140)
        for column, width in self.extraColumnWidths.items():
            self.table.setColumnWidth(column, width)

        # Wrapped message text decides its own height; a fixed row height
        # clips long reports.
        self.table.resizeRowsToContents()

    def displayText(self, item):
        return item.text

    def rowColor(self, item):
        """The foreground for a record, or None for the default."""
        return None

    def updatePages(self):
        text = '{}/{}'.format(self.page, self.pagination.pages or 1)
        self.pagesLabel.setText(text)

    def updateInfoButton(self):
        indexes = self.table.selectionModel().selectedIndexes()
        if len(indexes) != 1:
            self.selected = None
            self.infoButton.hide()
            return

        self.selected = self.records.record(indexes[0])
        self.infoButton.show()

    def updateCalendarButton(self):
        source = 'calendar.png' if self.date else 'search.png'
        self.calendarButton.setIcon(QIcon(iconPath(source)))

    def copySelected(self, index):
        QApplication.clipboard().setText(index.data())
        self.statusMessage.emit(
            QCoreApplication.translate('MainWindow', 'Selected message has been copied'), 5000)

    def view(self):
        message = self.selected
        self.reviewer.receive(message)
        self.reviewer.show()


class TafTable(BaseDataTable):

    def __init__(self, parent, layout, workers, reviewer=None, repository=None):
        super().__init__(parent, layout, workers, repository=repository)
        self.category = 'TAF'
        self.model = Taf
        self.reviewer = reviewer
        self.extraColumnWidths = {3: 50}

    def displayText(self, item):
        return item.flattenedText()

    def rowColor(self, item):
        if 'COR' in item.text or 'AMD' in item.text:
            return self.color

        return None


class MetarTable(BaseDataTable):

    def __init__(self, parent, layout, workers, repository=None):
        super().__init__(parent, layout, workers, repository=repository)
        self.category = 'METAR'
        self.model = Metar
        self.perPage = 24
        self.chartButton.show()
        self.hideColumns()

    def hideColumns(self):
        self.table.setColumnHidden(3, True)

    def rowColor(self, item):
        if item.type == 'SP':
            return self.color

        return None

    def updateInfoButton(self):
        self.infoButton.hide()


class SigmetTable(BaseDataTable):

    def __init__(self, parent, layout, workers, reviewer=None, repository=None):
        super().__init__(parent, layout, workers, repository=repository)
        self.category = 'SIGMET'
        self.model = Sigmet
        self.reviewer = reviewer
        self.perPage = 8
        self.extraColumnWidths = {3: 50}


class AirmetTable(SigmetTable):

    def __init__(self, parent, layout, workers, reviewer=None, repository=None):
        super().__init__(parent, layout, workers, reviewer=reviewer, repository=repository)
        self.category = 'AIRMET'
