import datetime

from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QTableWidgetItem, QHeaderView

from tafor.models import db, Taf, Metar, Sigmet
from tafor.utils import paginate
from tafor.components.ui import Ui_main_table


class BaseDataTable(QWidget, Ui_main_table.Ui_DataTable):
    
    def __init__(self, layout):
        super(BaseDataTable, self).__init__()
        self.setupUi(self)
        self.setStyle()
        self.page = 1
        self.pagination = None

        layout.addWidget(self)

    def setStyle(self):
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setStyleSheet('QTableWidget::item {padding: 5px 0;}')

    def hideColumns(self):
        raise NotImplemented

    def prev(self):
        if self.pagination.hasPrev:
            self.setPage(self.pagination.prevNum)

    def next(self):
        if self.pagination.hasNext:
            self.setPage(self.pagination.nextNum)

    def setPage(self, page):
        print(page)
        self.page = page
        self.updateGUI()
        

class TafTable(BaseDataTable):

    def __init__(self, layout):
        super(TafTable, self).__init__(layout)

    def updateGUI(self):
        queryset = db.query(Taf).order_by(Taf.sent.desc())
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

        self.table.resizeRowsToContents()


class MetarTable(BaseDataTable):

    def __init__(self, layout):
        super(MetarTable, self).__init__(layout)

        self.hideColumns()

    def hideColumns(self):
        self.table.setColumnHidden(2, True)
        self.table.setColumnHidden(3, True)

    def updateGUI(self):
        queryset = db.query(Metar).order_by(Metar.created.desc())
        self.pagination = paginate(queryset, self.page, perPage=24)
        items = self.pagination.items
        self.table.setRowCount(len(items))
        self.table.setColumnWidth(0, 50)

        for row, item in enumerate(items):
            self.table.setItem(row, 0,  QTableWidgetItem(item.tt))
            self.table.setItem(row, 1,  QTableWidgetItem(item.rpt))
            if item.tt == 'SP':
                self.table.item(row, 0).setForeground(Qt.red)
                self.table.item(row, 1).setForeground(Qt.red)

        self.table.resizeRowsToContents()


class SigmetTable(BaseDataTable):

    def __init__(self, layout):
        super(SigmetTable, self).__init__(layout)

        self.hideColumns()

    def hideColumns(self):
        self.table.setColumnHidden(3, True)

    def updateGUI(self):
        queryset = db.query(Sigmet).order_by(Sigmet.sent.desc())
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
