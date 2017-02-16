# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'D:\Chen\Work\tafor\tafor\ui\schedule.ui'
#
# Created by: PyQt5 UI code generator 5.6
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Schedule(object):
    def setupUi(self, Schedule):
        Schedule.setObjectName("Schedule")
        Schedule.resize(950, 243)
        self.verticalLayout = QtWidgets.QVBoxLayout(Schedule)
        self.verticalLayout.setObjectName("verticalLayout")
        self.sch_table = QtWidgets.QTableWidget(Schedule)
        self.sch_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.sch_table.setObjectName("sch_table")
        self.sch_table.setColumnCount(4)
        self.sch_table.setRowCount(0)
        item = QtWidgets.QTableWidgetItem()
        self.sch_table.setHorizontalHeaderItem(0, item)
        item = QtWidgets.QTableWidgetItem()
        self.sch_table.setHorizontalHeaderItem(1, item)
        item = QtWidgets.QTableWidgetItem()
        self.sch_table.setHorizontalHeaderItem(2, item)
        item = QtWidgets.QTableWidgetItem()
        self.sch_table.setHorizontalHeaderItem(3, item)
        self.verticalLayout.addWidget(self.sch_table)

        self.retranslateUi(Schedule)
        QtCore.QMetaObject.connectSlotsByName(Schedule)

    def retranslateUi(self, Schedule):
        _translate = QtCore.QCoreApplication.translate
        Schedule.setWindowTitle(_translate("Schedule", "定时任务列表"))
        item = self.sch_table.horizontalHeaderItem(0)
        item.setText(_translate("Schedule", "类型"))
        item = self.sch_table.horizontalHeaderItem(1)
        item.setText(_translate("Schedule", "报文内容"))
        item = self.sch_table.horizontalHeaderItem(2)
        item.setText(_translate("Schedule", "执行时间"))
        item = self.sch_table.horizontalHeaderItem(3)
        item.setText(_translate("Schedule", "添加时间"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    Schedule = QtWidgets.QDialog()
    ui = Ui_Schedule()
    ui.setupUi(Schedule)
    Schedule.show()
    sys.exit(app.exec_())

