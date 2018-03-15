import datetime

from PyQt5.QtGui import QCursor
from PyQt5.QtCore import QCoreApplication, QTimer
from PyQt5.QtWidgets import QDialog, QAction, QMenu, QHeaderView, QTableWidgetItem

from tafor.components.ui import Ui_task
from tafor.models import db, Task
from tafor import logger


class TaskBrowser(QDialog, Ui_task.Ui_Tasks):
    
    def __init__(self, parent=None):
        super(TaskBrowser, self).__init__(parent)
        self.setupUi(self)
        self.parent = parent
        self.updateGui()

        self.timer = QTimer()
        self.timer.timeout.connect(self.updateGui)
        self.timer.start(60 * 1000)

    def updateGui(self):
        items = db.query(Task).filter(Task.taf_id == None).order_by(Task.planning.desc()).all()
        header = self.taskTable.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        self.taskTable.setRowCount(len(items))
        self.taskTable.resizeRowsToContents()

        for row, item in enumerate(items):
            self.taskTable.setItem(row, 0, QTableWidgetItem(item.tt))
            self.taskTable.setItem(row, 1, QTableWidgetItem(item.rpt))
            self.taskTable.setItem(row, 2, QTableWidgetItem(item.planning.strftime("%m-%d %H:%M:%S")))
            self.taskTable.setItem(row, 3, QTableWidgetItem(item.created.strftime("%m-%d %H:%M:%S")))

    def contextMenuEvent(self, event):
        menu = QMenu()

        copyAction = QAction('复制', self)
        copyAction.triggered.connect(self.copySelectItem)

        delAction = QAction('删除', self)
        delAction.triggered.connect(self.delSelectItem)

        menu.addAction(copyAction)
        menu.addAction(delAction)
        menu.exec_(QCursor.pos())

    def delSelectItem(self):
        row = self.taskTable.currentRow()
        rpt = self.taskTable.item(row, 1).text()

        item = db.query(Task).filter_by(rpt=rpt).first()
        db.delete(item)
        db.commit()

        self.updateGui()
        logger.debug('Del', item)

    def copySelectItem(self):
        print('Copy')


