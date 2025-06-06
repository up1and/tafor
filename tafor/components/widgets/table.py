import os
import datetime

from PyQt5.QtGui import QIcon, QRegExpValidator, QColor, QPixmap, QCursor
from PyQt5.QtCore import QCoreApplication, QStandardPaths, QRegExp, QDate, Qt, pyqtSignal
from PyQt5.QtWidgets import (QDialog, QFileDialog, QWidget, QDialogButtonBox, QTableWidgetItem, QHeaderView, QLabel, QCalendarWidget,
    QVBoxLayout, QFormLayout, QLabel, QDateEdit, QLayout, QApplication)

from sqlalchemy import and_

from tafor.states import context
from tafor.styles import calendarStyle, dateEditHiddenStyle, buttonHoverStyle
from tafor.models import db, Taf, Metar, Sigmet
from tafor.utils import paginate
from tafor.utils.thread import ExportRecordWorker, threadManager
from tafor.components.ui import Ui_main_table, main_rc



class ExportDialog(QDialog):

    def __init__(self, parent=None):
        super(ExportDialog, self).__init__(parent)
        self.parent = parent

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
        query = self.queryset()
        num = query.count()

        if num == 0:
            self.countLabel.setText('')
            self.saveButton.setEnabled(False)
        else:
            text = QCoreApplication.translate('DataTable', '{} records found')
            text = text.format(query.count())
            self.countLabel.setText(text)
            self.saveButton.setEnabled(True)

    def queryset(self):
        model = self.parent.model
        reportType = self.parent.reportType
        query = db.query(model)

        if reportType == 'SIGMET':
            query = query.filter(model.type != 'WA')

        if reportType == 'AIRMET':
            query = query.filter(model.type == 'WA')

        start, end = self.startDate.date().toPyDate(), self.endDate.date().toPyDate()
        query = query.filter(
            model.created >= start, model.created < end + datetime.timedelta(hours=24)).order_by(model.created.desc())

        return query

    def exportToCsv(self):
        fmt = '%Y-%m-%d'
        start, end = self.startDate.date().toPyDate(), self.endDate.date().toPyDate()
        name = '{} {} {}.csv'.format(self.parent.reportType, start.strftime(fmt), end.strftime(fmt))
        title = QCoreApplication.translate('DataTable', 'Save as CSV')
        path = QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation)
        filename, _ = QFileDialog.getSaveFileName(self, title, os.path.join(path, name), '(*.csv)')

        if not filename:
            return

        headers = ('type', 'text', 'created')
        data = [(e.type, e.text, e.created) for e in self.queryset()]

        # Use new worker-based approach
        workerId = f"export_{id(self)}"
        worker, thread = threadManager.createWorker(ExportRecordWorker, workerId, filename, data, headers=headers)
        worker.finished.connect(self.close)
        threadManager.startWorker(workerId)


class BaseDataTable(QWidget, Ui_main_table.Ui_DataTable):

    chartClicked = pyqtSignal()

    def __init__(self, parent, layout):
        super(BaseDataTable, self).__init__()
        self.setupUi(self)
        self.setupStyle()
        self.setupValidator()
        self.page = 1
        self.pagination = None
        self.reportType = ''
        self.date = None
        self.keywords = []
        self.parent = parent
        self.color = QColor(200, 20, 40)

        self.calendar.calendarWidget().setSelectedDate(QDate.currentDate())
        self.calendar.calendarWidget().setHorizontalHeaderFormat(QCalendarWidget.NoHorizontalHeader)

        self.exportDialog = ExportDialog(self)

        font = context.environ.fixedFont()
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

        self.setPage(1)

    def setupStyle(self):
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setStyleSheet('QTableWidget {border: 0;} QTableWidget::item {padding: 5px 0;}')

        self.calendar.setStyleSheet(calendarStyle + dateEditHiddenStyle + buttonHoverStyle)

        self.prevButton.setIcon(QIcon(':/prev.png'))
        self.nextButton.setIcon(QIcon(':/next.png'))
        self.chartButton.setIcon(QIcon(':/chart.png'))
        self.calendarButton.setIcon(QIcon(':/calendar.png'))
        self.exportButton.setIcon(QIcon(':/export.png'))
        self.infoButton.setIcon(QIcon(':/info.png'))
        self.infoButton.hide()
        self.chartButton.hide()

    def setupValidator(self):
        pattern = r'[a-zA-Z0-9\s\/\-\+]+'
        word = QRegExpValidator(QRegExp(pattern))
        self.search.setValidator(word)

    def queryset(self):
        query = db.query(self.model).order_by(self.model.created.desc())

        if self.reportType == 'SIGMET':
            query = query.filter(self.model.type != 'WA')

        if self.reportType == 'AIRMET':
            query = query.filter(self.model.type == 'WA')

        if self.date:
            delta = datetime.timedelta(days=1)
            query = query.filter(and_(self.model.created >= self.date, self.model.created < self.date + delta))

        if self.keywords:
            words = [self.model.text.like('%'+word+'%') for word in self.keywords]
            query = query.filter(and_(*words))

        return query

    def autoSearch(self):
        self.search.setText(self.search.text().upper())
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

        self.calendar.setMaximumDate(QDate.currentDate())

    def updateTable(self):
        raise NotImplementedError

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
        context.flash.statusbar(QCoreApplication.translate('MainWindow', 'Selected message has been copied'), 5000)

    def view(self):
        message = self.selected
        self.reviewer.receive(message)
        self.reviewer.show()

    def checkmarkLabel(self, item):
        if item.confirmed:
            iconSrc = ':/checkmark.png'
        else:
            iconSrc = ':/questionmark.png'

        label = QLabel()
        icon = QPixmap(iconSrc)
        label.setPixmap(icon.scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        label.setAlignment(Qt.AlignCenter)
        return label


class TafTable(BaseDataTable):

    def __init__(self, parent, layout):
        super(TafTable, self).__init__(parent, layout)
        self.reportType = 'TAF'
        self.model = Taf
        self.reviewer = self.parent.tafSender

    def updateTable(self):
        queryset = self.queryset()
        self.pagination = paginate(queryset, self.page, perPage=12)
        items = self.pagination.items
        self.table.setRowCount(len(items))
        self.table.setColumnWidth(0, 50)
        self.table.setColumnWidth(2, 140)
        self.table.setColumnWidth(3, 50)

        for row, item in enumerate(items):
            self.table.setItem(row, 0, QTableWidgetItem(item.type))
            self.table.setItem(row, 1, QTableWidgetItem(item.flatternedText()))
            if item.created:
                created = item.created.strftime('%Y-%m-%d %H:%M:%S')
                self.table.setItem(row, 2, QTableWidgetItem(created))

            label = self.checkmarkLabel(item)
            self.table.setCellWidget(row, 3, label)

            if 'COR' in item.text or 'AMD' in item.text:
                self.table.item(row, 0).setForeground(self.color)
                self.table.item(row, 1).setForeground(self.color)
                self.table.item(row, 2).setForeground(self.color)

            self.table.item(row, 0).setTextAlignment(Qt.AlignCenter)
            self.table.item(row, 2).setTextAlignment(Qt.AlignCenter)

        self.table.resizeRowsToContents()


class MetarTable(BaseDataTable):

    def __init__(self, parent, layout):
        super(MetarTable, self).__init__(parent, layout)
        self.reportType = 'METAR'
        self.model = Metar
        self.chartButton.show()
        self.hideColumns()

    def hideColumns(self):
        self.table.setColumnHidden(3, True)

    def updateTable(self):
        queryset = self.queryset()
        self.pagination = paginate(queryset, self.page, perPage=24)
        items = self.pagination.items
        self.table.setRowCount(len(items))
        self.table.setColumnWidth(0, 50)
        self.table.setColumnWidth(2, 140)

        for row, item in enumerate(items):
            self.table.setItem(row, 0,  QTableWidgetItem(item.type))
            self.table.setItem(row, 1,  QTableWidgetItem(item.text))
            if item.created:
                created = item.created.strftime('%Y-%m-%d %H:%M:%S')
                self.table.setItem(row, 2, QTableWidgetItem(created))

            if item.type == 'SP':
                self.table.item(row, 0).setForeground(self.color)
                self.table.item(row, 1).setForeground(self.color)
                self.table.item(row, 2).setForeground(self.color)

            self.table.item(row, 0).setTextAlignment(Qt.AlignCenter)
            self.table.item(row, 2).setTextAlignment(Qt.AlignCenter)

        self.table.resizeRowsToContents()

    def updateInfoButton(self):
        self.infoButton.hide()


class SigmetTable(BaseDataTable):

    def __init__(self, parent, layout):
        super(SigmetTable, self).__init__(parent, layout)
        self.reportType = 'SIGMET'
        self.model = Sigmet
        self.reviewer = self.parent.sigmetSender

    def updateTable(self):
        queryset = self.queryset()
        self.pagination = paginate(queryset, self.page, perPage=8)
        items = self.pagination.items
        self.table.setRowCount(len(items))
        self.table.setColumnWidth(0, 50)
        self.table.setColumnWidth(2, 140)
        self.table.setColumnWidth(3, 50)

        for row, item in enumerate(items):
            self.table.setItem(row, 0, QTableWidgetItem(item.type))
            self.table.setItem(row, 1, QTableWidgetItem(item.text))
            if item.created:
                created = item.created.strftime('%Y-%m-%d %H:%M:%S')
                self.table.setItem(row, 2, QTableWidgetItem(created))

            label = self.checkmarkLabel(item)
            self.table.setCellWidget(row, 3, label)

            self.table.item(row, 0).setTextAlignment(Qt.AlignCenter)
            self.table.item(row, 2).setTextAlignment(Qt.AlignCenter)

        self.table.resizeRowsToContents()


class AirmetTable(SigmetTable):

    def __init__(self, parent, layout):
        super(AirmetTable, self).__init__(parent, layout)
        self.reportType = 'AIRMET'
