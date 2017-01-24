import datetime

from PyQt5 import QtCore, QtGui, QtWidgets

from ui import Ui_schedule
from models import Schedule
from config import db


class ScheduleTable(QtWidgets.QDialog, Ui_schedule.Ui_schedule):
    """docstring for ScheduleTable"""
    def __init__(self, parent=None):
        super(ScheduleTable, self).__init__()
        self.setupUi(self)
        self.update()

    def update(self):
        items = db.query(Schedule).filter(Schedule.tafor_id == None).order_by(Schedule.schedule_time.desc()).all()
        header = self.sch_table.horizontalHeader()
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        self.sch_table.setRowCount(len(items))
        self.sch_table.resizeRowsToContents()

        for row, item in enumerate(items):
            self.sch_table.setItem(row, 0, QtWidgets.QTableWidgetItem(item.tt))
            self.sch_table.setItem(row, 1, QtWidgets.QTableWidgetItem(item.rpt))
            self.sch_table.setItem(row, 2, QtWidgets.QTableWidgetItem(item.schedule_time.strftime("%m-%d %H:%M:%S")))
            self.sch_table.setItem(row, 3, QtWidgets.QTableWidgetItem(item.create_time.strftime("%m-%d %H:%M:%S")))

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
        row = self.sch_table.currentRow()
        rpt = self.sch_table.item(row, 1).text()

        item = db.query(Schedule).filter_by(rpt=rpt).first()
        db.delete(item)
        db.commit()

        self.update()
        print('Del', item)

    def copy_select_item(self):
        print('Copy')






if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    ui = ScheduleTable()
    ui.show()
    sys.exit(app.exec_())