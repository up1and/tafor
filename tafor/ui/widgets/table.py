import os
import datetime

from PyQt5.QtGui import QIcon, QRegExpValidator, QColor, QPixmap
from PyQt5.QtCore import QCoreApplication, QStandardPaths, QRegExp, QDate, Qt, pyqtSignal
from PyQt5.QtWidgets import (QDialog, QFileDialog, QWidget, QDialogButtonBox, QTableWidgetItem, QHeaderView, QLabel, QCalendarWidget,
    QVBoxLayout, QFormLayout, QLabel, QDateEdit, QLayout, QApplication)

from tafor.core.models import Metar, Sigmet, Taf
from tafor.core.utils.common import iconPath
from tafor.ui.qt import Ui_main_table
from tafor.ui.fonts import fixedFont
from tafor.ui.styles import flatButtonStyle, calendarStyle, dateEditHiddenStyle
from tafor.ui.workers import ExportRecordWorker, threadManager



class ExportDialog(QDialog):

    def __init__(self, table=None):
        super().__init__(table)
        self.table = table

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
        self.countLabel.setStyleSheet('QLabel {color: grey; margin: 10px 0;}')
        self.formLayout.setWidget(2, QFormLayout.SpanningRole, self.countLabel)
        self.verticalLayout.addLayout(self.formLayout)
        self.buttonBox = QDialogButtonBox(self)
        self.buttonBox.setOrientation(Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Save)
        self.verticalLayout.addWidget(self.buttonBox)

        self.startDate.calendarWidget().setHorizontalHeaderFormat(QCalendarWidget.NoHorizontalHeader)
        self.endDate.calendarWidget().setHorizontalHeaderFormat(QCalendarWidget.NoHorizontalHeader)

        self.setWindowTitle(QCoreApplication.translate('DataTable', 'Export Records'))
        self.startDateLabel.setText(QCoreApplication.translate('DataTable', 'Start Date'))
        self.endDateLabel.setText(QCoreApplication.translate('DataTable', 'End Date'))

        self.saveButton = self.buttonBox.button(QDialogButtonBox.Save)
        self.saveButton.setText(QCoreApplication.translate('DataTable', 'Export'))

        self.setStyleSheet(calendarStyle)
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
        results = self.filteredReport()
        count = len(results)

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

        # Use new worker-based approach
        worker, thread = threadManager.createWorker(ExportRecordWorker, filename, data, headers=headers)
        worker.finished.connect(self.close)
        thread.start()


class BaseDataTable(QWidget, Ui_main_table.Ui_DataTable):

    chartClicked = pyqtSignal()

    def __init__(self, parent, layout, conf=None, context=None, repository=None):
        super().__init__(parent)
        self.conf = conf
        self.context = context
        self.perPage = 12
        self.hasCheckmark = False
        self.extraColumnWidths = {}
        self.setupUi(self)
        self.setupStyle()
        self.setupValidator()
        self.page = 1
        self.pagination = None
        self.total = None
        self.category = ''
        self.date = None
        self.keywords = []
        self.color = QColor(200, 20, 40)

        self.calendar.calendarWidget().setSelectedDate(QDate.currentDate())
        self.calendar.calendarWidget().setHorizontalHeaderFormat(QCalendarWidget.NoHorizontalHeader)

        self.repository = repository
        self.exportDialog = ExportDialog(self)

        font = fixedFont()
        font.setPointSize(10)
        self.table.setFont(font)

        layout.addWidget(self)
        self.bindSignal()

    def bindSignal(self):
        self.search.textEdited.connect(self.autoSearch)
        self.table.itemDoubleClicked.connect(self.copySelected)
        self.prevButton.clicked.connect(self.prev)
        self.nextButton.clicked.connect(self.next)
        self.table.itemSelectionChanged.connect(self.updateInfoButton)
        self.infoButton.clicked.connect(self.view)
        self.calendarButton.clicked.connect(lambda : self.setCalendar(None))
        self.calendar.calendarWidget().clicked.connect(self.setCalendar)
        self.chartButton.clicked.connect(self.chartClicked.emit)
        self.exportButton.clicked.connect(self.exportDialog.show)

    def setCalendar(self, date):
        if date:
            self.date = date.toPyDate()
        else:
            self.date = None

        self.total = None
        self.setPage(1)

    def setupStyle(self):
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setStyleSheet('QTableWidget {border: 0;} QTableWidget::item {padding: 5px 0;}')

        self.calendar.setStyleSheet(calendarStyle + dateEditHiddenStyle)

        self.prevButton.setIcon(QIcon(iconPath('prev.png')))
        self.nextButton.setIcon(QIcon(iconPath('next.png')))
        self.chartButton.setIcon(QIcon(iconPath('chart.png')))
        self.calendarButton.setIcon(QIcon(iconPath('calendar.png')))
        self.exportButton.setIcon(QIcon(iconPath('export.png')))
        self.infoButton.setIcon(QIcon(iconPath('info.png')))
        self.infoButton.hide()
        self.chartButton.hide()

    def setupValidator(self):
        pattern = r'[a-zA-Z0-9\s\/\-\+]+'
        word = QRegExpValidator(QRegExp(pattern))
        self.search.setValidator(word)

    def autoSearch(self):
        self.search.setText(self.search.text().upper())
        self.keywords = self.search.text().split()
        self.total = None
        self.setPage(1)

    def hideColumns(self):
        raise NotImplementedError

    def prev(self):
        if self.pagination.hasPrev:
            self.setPage(self.pagination.prevNum)
        else:
            if self.date:
                self.date -= datetime.timedelta(days=1)
                self.total = None
                self.setPage(1)

    def next(self):
        if self.pagination.hasNext:
            self.setPage(self.pagination.nextNum)
        else:
            if self.date:
                self.date += datetime.timedelta(days=1)
                self.total = None
                self.setPage(1)

    def setPage(self, page):
        self.page = page
        self.updateGui()

    def updateGui(self):
        self.updateTable()
        self.updatePages()
        self.updateInfoButton()
        self.updateCalendarButton()

        self.calendar.setMaximumDate(QDate.currentDate())

    def updateTable(self):
        self.pagination = self.repository.paginated(
            self.model, category=self.category, date=self.date, keywords=self.keywords,
            page=self.page, perPage=self.perPage, total=self.total)
        self.total = self.pagination.total

        items = self.pagination.items
        self.table.setRowCount(len(items))
        self.table.setColumnWidth(0, 50)
        self.table.setColumnWidth(2, 140)
        for column, width in self.extraColumnWidths.items():
            self.table.setColumnWidth(column, width)

        for row, item in enumerate(items):
            self.table.setItem(row, 0, QTableWidgetItem(item.type))
            self.table.setItem(row, 1, QTableWidgetItem(self.displayText(item)))
            if item.created:
                created = item.created.strftime('%Y-%m-%d %H:%M:%S')
                self.table.setItem(row, 2, QTableWidgetItem(created))

            if self.hasCheckmark:
                self.table.setCellWidget(row, 3, self.checkmarkLabel(item))

            self.decorateRow(row, item)

            self.table.item(row, 0).setTextAlignment(Qt.AlignCenter)
            self.table.item(row, 2).setTextAlignment(Qt.AlignCenter)

        self.table.resizeRowsToContents()

    def displayText(self, item):
        return item.text

    def decorateRow(self, row, item):
        pass

    def updatePages(self):
        text = '{}/{}'.format(self.page, self.pagination.pages or 1)
        self.pagesLabel.setText(text)

    def updateInfoButton(self):
        items = self.table.selectedItems()
        if len(items) != 1:
            self.selected = None
            self.infoButton.hide()
            return

        index = items[0].row()
        self.selected = self.pagination.items[index]
        self.infoButton.show()

    def updateCalendarButton(self):
        if self.date:
            self.calendarButton.setChecked(True)
            self.calendarButton.show()
            self.calendar.hide()
        else:
            self.calendarButton.hide()
            self.calendar.show()

    def copySelected(self, item):
        QApplication.clipboard().setText(item.text())
        self.context.flash.statusbar(QCoreApplication.translate('MainWindow', 'Selected message has been copied'), 5000)

    def view(self):
        message = self.selected
        self.reviewer.receive(message)
        self.reviewer.show()

    def checkmarkLabel(self, item):
        if item.confirmed:
            iconSrc = iconPath('checkmark.png')
        else:
            iconSrc = iconPath('questionmark.png')

        label = QLabel()
        icon = QPixmap(iconSrc)
        label.setPixmap(icon.scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        label.setAlignment(Qt.AlignCenter)
        return label


class TafTable(BaseDataTable):

    def __init__(self, parent, layout, reviewer=None, conf=None, context=None, repository=None):
        super().__init__(parent, layout, conf=conf, context=context, repository=repository)
        self.category = 'TAF'
        self.model = Taf
        self.reviewer = reviewer
        self.hasCheckmark = True
        self.extraColumnWidths = {3: 50}

    def displayText(self, item):
        return item.flattenedText()

    def decorateRow(self, row, item):
        if 'COR' in item.text or 'AMD' in item.text:
            for column in (0, 1, 2):
                self.table.item(row, column).setForeground(self.color)


class MetarTable(BaseDataTable):

    def __init__(self, parent, layout, conf=None, context=None, repository=None):
        super().__init__(parent, layout, conf=conf, context=context, repository=repository)
        self.category = 'METAR'
        self.model = Metar
        self.perPage = 24
        self.chartButton.show()
        self.hideColumns()

    def hideColumns(self):
        self.table.setColumnHidden(3, True)

    def decorateRow(self, row, item):
        if item.type == 'SP':
            for column in (0, 1, 2):
                self.table.item(row, column).setForeground(self.color)

    def updateInfoButton(self):
        self.infoButton.hide()


class SigmetTable(BaseDataTable):

    def __init__(self, parent, layout, reviewer=None, conf=None, context=None, repository=None):
        super().__init__(parent, layout, conf=conf, context=context, repository=repository)
        self.category = 'SIGMET'
        self.model = Sigmet
        self.reviewer = reviewer
        self.perPage = 8
        self.hasCheckmark = True
        self.extraColumnWidths = {3: 50}


class AirmetTable(SigmetTable):

    def __init__(self, parent, layout, reviewer=None, conf=None, context=None, repository=None):
        super().__init__(parent, layout, reviewer=reviewer, conf=conf, context=context, repository=repository)
        self.category = 'AIRMET'
