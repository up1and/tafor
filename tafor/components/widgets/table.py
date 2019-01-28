import datetime

from PyQt5.QtGui import QIcon, QRegExpValidator
from PyQt5.QtCore import QCoreApplication, Qt, QRegExp
from PyQt5.QtWidgets import QWidget, QTableWidgetItem, QHeaderView

from sqlalchemy import or_, and_

from tafor.components.ui import main_rc
from tafor.models import db, Taf, Metar, Sigmet
from tafor.utils import paginate, TafParser, SigmetParser
from tafor.components.ui import Ui_main_table


class BaseDataTable(QWidget, Ui_main_table.Ui_DataTable):
    
    def __init__(self, parent, layout):
        super(BaseDataTable, self).__init__()
        self.setupUi(self)
        self.setStyle()
        self.setValidator()
        self.page = 1
        self.pagination = None
        self.searchText = ''
        self.date = None
        self.parent = parent
        self.color = Qt.red

        layout.addWidget(self)
        self.bindSignal()

    def bindSignal(self):
        self.search.textEdited.connect(self.autoSearch)
        self.table.itemDoubleClicked.connect(self.copySelected)
        self.prevButton.clicked.connect(self.prev)
        self.nextButton.clicked.connect(self.next)
        self.table.itemSelectionChanged.connect(self.updateInfoButton)
        self.infoButton.clicked.connect(self.resend)

    def setStyle(self):
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setStyleSheet('QTableWidget {border: 0;} QTableWidget::item {padding: 5px 0;}')

        self.prevButton.setIcon(QIcon(':/prev.png'))
        self.nextButton.setIcon(QIcon(':/next.png'))
        self.infoButton.setIcon(QIcon(':/info.png'))
        self.infoButton.hide()

    def setValidator(self):
        pattern = r'\d{4}\/\d{1,2}\/\d{1,2}'
        date = QRegExpValidator(QRegExp(pattern))
        self.search.setValidator(date)

    def queryset(self):
        if hasattr(self.model, 'sent'):
            dateField = self.model.sent
        else:
            dateField = self.model.created

        query = db.query(self.model).order_by(dateField.desc())

        if self.date:
            delta = datetime.timedelta(days=1)
            query = query.filter(and_(dateField >= self.date, dateField < self.date + delta))

        return query

    def fillDate(self):
        text = self.search.text()
        if len(text) > len(self.searchText):
            if len(text) == 4:
                text += '/'
            elif len(text) == 7 and not text.endswith('/'):
                text += '/'

            self.search.setText(text)

        self.searchText = text

    def autoSearch(self):
        self.fillDate()
        dates = [int(n) for n in self.search.text().split('/') if n]
        if len(dates) == 3:
            try:
                self.date = datetime.date(*dates)
                self.page = 1
                self.updateGui()
            except Exception as e:
                pass
        else:
            self.date = None
        
        if len(dates) == 0:
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

    def updateTable(self):
        raise NotImplementedError

    def updatePages(self):
        text = '{}/{}'.format(self.page, self.pagination.pages)
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

    def copySelected(self, item):
        self.parent.clip.setText(item.text())
        self.parent.statusBar.showMessage(QCoreApplication.translate('MainWindow', 'Selected message has been copied'), 5000)

    def resend(self):
        message = {
            'item': self.selected,
            'sign': self.selected.sign,
            'rpt': self.selected.rpt,
            'full': '\n'.join(filter(None, [self.selected.sign, self.selected.rpt]))
        }
        self.reviewer.receive(message, mode='view')
        self.reviewer.show()
        

class TafTable(BaseDataTable):

    def __init__(self, parent, layout):
        super(TafTable, self).__init__(parent, layout)
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

            if item.confirmed:
                checkedItem = QTableWidgetItem()
                checkedItem.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
                checkedItem.setIcon(QIcon(':/checkmark.png'))
                self.table.setItem(row, 3, checkedItem)
            else:
                checkedItem = QTableWidgetItem()
                checkedItem.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
                checkedItem.setIcon(QIcon(':/cross.png'))
                self.table.setItem(row, 3, checkedItem)

            if 'COR' in item.rpt or 'AMD' in item.rpt:
                self.table.item(row, 0).setForeground(self.color)
                self.table.item(row, 1).setForeground(self.color)
                self.table.item(row, 2).setForeground(self.color)

        self.table.resizeRowsToContents()


class MetarTable(BaseDataTable):

    def __init__(self, parent, layout):
        super(MetarTable, self).__init__(parent, layout)
        self.model = Metar
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

        self.table.resizeRowsToContents()

    def updateInfoButton(self, current=None):
        self.infoButton.hide()


class SigmetTable(BaseDataTable):

    def __init__(self, parent, layout):
        super(SigmetTable, self).__init__(parent, layout)
        self.model = Sigmet
        self.reviewer = self.parent.sigmetSender
        self.hideColumns()

    def hideColumns(self):
        self.table.setColumnHidden(3, True)

    def updateTable(self):
        queryset = self.queryset()
        self.pagination = paginate(queryset, self.page, perPage=6)
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

        self.table.resizeRowsToContents()
