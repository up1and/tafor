import datetime

from PyQt5 import QtCore, QtGui, QtWidgets

from tafor.components.ui import Ui_task
from tafor.models import db, Task
from tafor import logger


class TaskBrowser(QtWidgets.QDialog, Ui_task.Ui_Task):
    def __init__(self, parent=None):
        super(TaskBrowser, self).__init__(parent)
        self.setupUi(self)
        self.parent = parent
        self.update_gui()

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_gui)
        self.timer.start(60 * 1000)

    def update_gui(self):
        items = db.query(Task).filter(Task.tafor_id == None).order_by(Task.plan.desc()).all()
        header = self.tasks_table.horizontalHeader()
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        self.tasks_table.setRowCount(len(items))
        self.tasks_table.resizeRowsToContents()

        for row, item in enumerate(items):
            self.tasks_table.setItem(row, 0, QtWidgets.QTableWidgetItem(item.tt))
            self.tasks_table.setItem(row, 1, QtWidgets.QTableWidgetItem(item.rpt))
            self.tasks_table.setItem(row, 2, QtWidgets.QTableWidgetItem(item.plan.strftime("%m-%d %H:%M:%S")))
            self.tasks_table.setItem(row, 3, QtWidgets.QTableWidgetItem(item.created.strftime("%m-%d %H:%M:%S")))

    def contextMenuEvent(self, event):
        menu = QtWidgets.QMenu()

        copy_action = QtWidgets.QAction('复制', self)
        copy_action.triggered.connect(self.copy_select_item)

        del_action = QtWidgets.QAction('删除', self)
        del_action.triggered.connect(self.del_select_item)

        menu.addAction(copy_action)
        menu.addAction(del_action)
        menu.exec_(QtGui.QCursor.pos())

    def del_select_item(self):
        row = self.tasks_table.currentRow()
        rpt = self.tasks_table.item(row, 1).text()

        item = db.query(Task).filter_by(rpt=rpt).first()
        db.delete(item)
        db.commit()

        self.update_gui()
        logger.debug('Del', item)

    def copy_select_item(self):
        print('Copy')


