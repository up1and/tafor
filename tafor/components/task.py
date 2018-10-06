from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QCoreApplication
from PyQt5.QtWidgets import QDialog, QHeaderView, QTableWidgetItem

from tafor import logger
from tafor.components.ui import main_rc, Ui_task
from tafor.models import db, Task


class TaskBrowser(QDialog, Ui_task.Ui_Tasks):
    
    def __init__(self, parent=None):
        super(TaskBrowser, self).__init__(parent)
        self.parent = parent
        self.setupUi(self)
        self.setStyle()
        self.bindSignal()
        self.updateGui()

    def setStyle(self):
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setStyleSheet('QTableWidget::item {padding: 5px 0;}')

        self.trashButton.setIcon(QIcon(':/trash.png'))

    def bindSignal(self):
        self.table.itemDoubleClicked.connect(self.copySelected)
        self.trashButton.clicked.connect(self.remove)

    def updateGui(self):
        items = db.query(Task).filter(Task.taf_id == None).order_by(Task.planning.desc()).all()
        self.table.setRowCount(len(items))
        self.table.resizeRowsToContents()

        for row, item in enumerate(items):
            self.table.setItem(row, 0, QTableWidgetItem(item.tt))
            self.table.setItem(row, 1, QTableWidgetItem(item.rpt))
            self.table.setItem(row, 2, QTableWidgetItem(item.planning.strftime("%m-%d %H:%M:%S")))
            self.table.setItem(row, 3, QTableWidgetItem(item.created.strftime("%m-%d %H:%M:%S")))

        self.table.resizeRowsToContents()

    def remove(self):
        row = self.table.currentRow()
        rpt = self.table.item(row, 1).text()

        item = db.query(Task).filter_by(rpt=rpt).first()
        db.delete(item)
        db.commit()

        self.updateGui()

    def copySelected(self, item):
        self.parent.clip.setText(item.text())
        self.parent.statusBar.showMessage(QCoreApplication.translate('MainWindow', 'Selected message has been copied'), 5000)


