import datetime

from PyQt5 import QtCore, QtGui, QtWidgets

from tafor.components.ui import Ui_task
from tafor.models import db, Task
from tafor import logger


class TaskBrowser(QtWidgets.QDialog, Ui_task.Ui_Tasks):
    def __init__(self, parent=None):
        super(TaskBrowser, self).__init__(parent)
        self.setupUi(self)
        self.parent = parent
        self.updateGUI()

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.updateGUI)
        self.timer.start(60 * 1000)

    def updateGUI(self):
        items = db.query(Task).filter(Task.tafor_id == None).order_by(Task.plan.desc()).all()
        header = self.taskTable.horizontalHeader()
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        self.taskTable.setRowCount(len(items))
        self.taskTable.resizeRowsToContents()

        for row, item in enumerate(items):
            self.taskTable.setItem(row, 0, QtWidgets.QTableWidgetItem(item.tt))
            self.taskTable.setItem(row, 1, QtWidgets.QTableWidgetItem(item.rpt))
            self.taskTable.setItem(row, 2, QtWidgets.QTableWidgetItem(item.plan.strftime("%m-%d %H:%M:%S")))
            self.taskTable.setItem(row, 3, QtWidgets.QTableWidgetItem(item.created.strftime("%m-%d %H:%M:%S")))

    def contextMenuEvent(self, event):
        menu = QtWidgets.QMenu()

        copyAction = QtWidgets.QAction('复制', self)
        copyAction.triggered.connect(self.copySelectItem)

        delAction = QtWidgets.QAction('删除', self)
        delAction.triggered.connect(self.delSelectItem)

        menu.addAction(copyAction)
        menu.addAction(delAction)
        menu.exec_(QtGui.QCursor.pos())

    def delSelectItem(self):
        row = self.taskTable.currentRow()
        rpt = self.taskTable.item(row, 1).text()

        item = db.query(Task).filter_by(rpt=rpt).first()
        db.delete(item)
        db.commit()

        self.update_gui()
        logger.debug('Del', item)

    def copySelectItem(self):
        print('Copy')


