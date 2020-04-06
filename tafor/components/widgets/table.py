import datetime

from PyQt5.QtGui import QIcon, QRegExpValidator, QColor, QPixmap, QCursor
from PyQt5.QtCore import QCoreApplication, QRegExp, QDate, Qt, pyqtSignal
from PyQt5.QtWidgets import (QDialog, QFileDialog, QWidget, QDialogButtonBox, QTableWidgetItem, QHeaderView, QLabel, QLineEdit, QCalendarWidget, 
    QVBoxLayout, QFormLayout, QLabel, QDateEdit, QLayout)

from sqlalchemy import and_

from tafor.components.ui import main_rc
from tafor.models import db, Taf, Metar, Sigmet
from tafor.utils import paginate
from tafor.utils.thread import ExportRecordThread
from tafor.components.ui import Ui_main_table



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
        self.countLabel.setMinimumSize(140, 0)
        self.formLayout.setWidget(2, QFormLayout.FieldRole, self.countLabel)
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

        self.setWindowModality(Qt.WindowModal)

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

    def closeEvent(self, event):
        self.countLabel.setText('')

    def updateExportStatus(self):
        query = self.queryset()
        num = query.count()

        if num == 0:
            self.countLabel.clear()
            self.saveButton.setEnabled(False)
        else:
            text = QCoreApplication.translate('DataTable', '{} records found')
            text = text.format(query.count())
            self.countLabel.setText(text)
            self.saveButton.setEnabled(True)

    def queryset(self):
        model = self.parent.model
        reportType = self.parent.reportType

        if hasattr(model, 'sent'):
            dateField = model.sent
        else:
            dateField = model.created

        query = db.query(model)

        if reportType == 'SIGMET':
            query = query.filter(model.tt != 'WA')

        if reportType == 'AIRMET':
            query = query.filter(model.tt == 'WA')

        start, end = self.startDate.date().toPyDate(), self.endDate.date().toPyDate()
        query = query.filter(
            dateField >= start, dateField < end + datetime.timedelta(hours=24)).order_by(dateField.desc())

        return query

    def exportToCsv(self):
        fmt = '%Y-%m-%d'
        start, end = self.startDate.date().toPyDate(), self.endDate.date().toPyDate()
        defaultName = '{} {} {}.csv'.format(self.parent.reportType, start.strftime(fmt), end.strftime(fmt))
        title = QCoreApplication.translate('DataTable', 'Save as CSV')
        filename, _ = QFileDialog.getSaveFileName(self, title, defaultName, '(*.csv)')

        if not filename:
            return

        if self.parent.reportType == 'METAR':
            timefield = 'created'
        else:
            timefield = 'sent'

        headers = ('type', 'content', 'time')
        data = [(e.tt, e.rpt, getattr(e, timefield)) for e in self.queryset()]

        self.thread = ExportRecordThread(filename, data, headers=headers)
        self.thread.finished.connect(self.close)
        self.thread.start()


class BaseDataTable(QWidget, Ui_main_table.Ui_DataTable):
    chartButtonClicked = pyqtSignal()

    def __init__(self, parent, layout):
        super(BaseDataTable, self).__init__()
        self.setupUi(self)
        self.setStyle()
        self.setValidator()
        self.page = 1
        self.pagination = None
        self.reportType = ''
        self.date = None
        self.keywords = []
        self.parent = parent
        self.color = QColor(200, 20, 40)

        self.calendar.lineEdit().hide()
        style = """
            QDateEdit {
                border: 1px solid transparent;
                padding: 2px; /* This (useless) line resolves a bug with the font color */
            }

            QDateEdit:hover {
                background: #e5f3ff;
                border: 1px solid #cce8ff;
            }

            QDateEdit::drop-down 
            {
                border: 0px; /* This seems to replace the whole arrow of the combo box */
            }

            /* Define a new custom arrow icon for the combo box */
            QDateEdit::down-arrow {
                image: url(:/search.png);
                width: 16px;
                height: 16px;
            }

        """
        self.calendar.setStyleSheet(style)
        self.calendar.calendarWidget().setSelectedDate(QDate.currentDate())
        self.calendar.calendarWidget().setHorizontalHeaderFormat(QCalendarWidget.NoHorizontalHeader)

        self.exportDialog = ExportDialog(self)

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
        self.calendar.dateChanged.connect(self.setCalendar)
        self.chartButton.clicked.connect(self.chartButtonClicked.emit)
        self.exportButton.clicked.connect(self.exportDialog.show)

    def setCalendar(self, date):
        if date:
            self.date = date.toPyDate()
        else:
            self.date = None

        self.page = 1
        self.updateGui()

    def setStyle(self):
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setStyleSheet('QTableWidget {border: 0;} QTableWidget::item {padding: 5px 0;}')

        self.prevButton.setIcon(QIcon(':/prev.png'))
        self.nextButton.setIcon(QIcon(':/next.png'))
        self.chartButton.setIcon(QIcon(':/chart.png'))
        self.calendarButton.setIcon(QIcon(':/calendar.png'))
        self.exportButton.setIcon(QIcon(':/export.png'))
        self.infoButton.setIcon(QIcon(':/info.png'))
        self.infoButton.hide()
        self.chartButton.hide()

    def setValidator(self):
        pattern = r'[a-zA-Z0-9\s\/\-\+]+'
        date = QRegExpValidator(QRegExp(pattern))
        self.search.setValidator(date)

    def queryset(self):
        if hasattr(self.model, 'sent'):
            dateField = self.model.sent
        else:
            dateField = self.model.created

        query = db.query(self.model).order_by(dateField.desc())

        if self.reportType == 'SIGMET':
            query = query.filter(self.model.tt != 'WA')

        if self.reportType == 'AIRMET':
            query = query.filter(self.model.tt == 'WA')

        if self.date:
            delta = datetime.timedelta(days=1)
            query = query.filter(and_(dateField >= self.date, dateField < self.date + delta))

        if self.keywords:
            words = [self.model.rpt.like('%'+word+'%') for word in self.keywords]
            query = query.filter(and_(*words))

        return query

    def autoSearch(self):
        self.search.setText(self.search.text().upper())
        self.keywords = self.search.text().split()
        self.page = 1
        self.updateGui()

    def hideColumns(self):
        raise NotImplementedError

    def prev(self):
        if self.pagination.hasPrev:
            self.setPage(self.pagination.prevNum)

    def next(self):
        if self.pagination.hasNext:
            self.setPage(self.pagination.nextNum)

    def setPage(self, page):
        self.page = page
        self.updateGui()

    def updateGui(self):
        self.updateTable()
        self.updatePages()
        self.updateInfoButton()
        self.updateCalendarButton()

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
        self.parent.clip.setText(item.text())
        self.parent.statusBar.showMessage(QCoreApplication.translate('MainWindow', 'Selected message has been copied'), 5000)

    def view(self):
        message = {
            'uuid': self.selected.uuid,
            'item': self.selected,
            'sign': self.selected.sign,
            'rpt': self.selected.rpt,
            'full': '\n'.join(filter(None, [self.selected.sign, self.selected.rpt]))
        }
        self.reviewer.receive(message, mode='view')
        self.reviewer.show()

    def checkmarkLabel(self, item):
        if item.confirmed:
            iconSrc = ':/checkmark.png'
        else:
            iconSrc = ':/cross.png'

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
            self.table.setItem(row, 0, QTableWidgetItem(item.tt))
            self.table.setItem(row, 1, QTableWidgetItem(item.rptInline))
            if item.sent:
                sent = item.sent.strftime('%Y-%m-%d %H:%M:%S')
                self.table.setItem(row, 2, QTableWidgetItem(sent))

            label = self.checkmarkLabel(item)
            self.table.setCellWidget(row, 3, label)

            if 'COR' in item.rpt or 'AMD' in item.rpt:
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
            self.table.setItem(row, 0,  QTableWidgetItem(item.tt))
            self.table.setItem(row, 1,  QTableWidgetItem(item.rpt))
            if item.created:
                created = item.created.strftime('%Y-%m-%d %H:%M:%S')
                self.table.setItem(row, 2, QTableWidgetItem(created))

            if item.tt == 'SP':
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
            self.table.setItem(row, 0, QTableWidgetItem(item.tt))
            self.table.setItem(row, 1, QTableWidgetItem(item.rpt))
            if item.sent:
                sent = item.sent.strftime('%Y-%m-%d %H:%M:%S')
                self.table.setItem(row, 2, QTableWidgetItem(sent))

            label = self.checkmarkLabel(item)
            self.table.setCellWidget(row, 3, label)

            self.table.item(row, 0).setTextAlignment(Qt.AlignCenter)
            self.table.item(row, 2).setTextAlignment(Qt.AlignCenter)

        self.table.resizeRowsToContents()


class AirmetTable(SigmetTable):

    def __init__(self, parent, layout):
        super(AirmetTable, self).__init__(parent, layout)
        self.reportType = 'AIRMET'
