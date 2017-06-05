# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'D:\Work\tafor\tafor\widgets\ui\tasks.ui'
#
# Created by: PyQt5 UI code generator 5.6
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Tasks(object):
    def setupUi(self, Tasks):
        Tasks.setObjectName("Tasks")
        Tasks.resize(950, 243)
        self.verticalLayout = QtWidgets.QVBoxLayout(Tasks)
        self.verticalLayout.setObjectName("verticalLayout")
        self.tasks_table = QtWidgets.QTableWidget(Tasks)
        self.tasks_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.tasks_table.setObjectName("tasks_table")
        self.tasks_table.setColumnCount(4)
        self.tasks_table.setRowCount(0)
        item = QtWidgets.QTableWidgetItem()
        self.tasks_table.setHorizontalHeaderItem(0, item)
        item = QtWidgets.QTableWidgetItem()
        self.tasks_table.setHorizontalHeaderItem(1, item)
        item = QtWidgets.QTableWidgetItem()
        self.tasks_table.setHorizontalHeaderItem(2, item)
        item = QtWidgets.QTableWidgetItem()
        self.tasks_table.setHorizontalHeaderItem(3, item)
        self.verticalLayout.addWidget(self.tasks_table)

        self.retranslateUi(Tasks)
        QtCore.QMetaObject.connectSlotsByName(Tasks)

    def retranslateUi(self, Tasks):
        _translate = QtCore.QCoreApplication.translate
        Tasks.setWindowTitle(_translate("Tasks", "定时任务列表"))
        item = self.tasks_table.horizontalHeaderItem(0)
        item.setText(_translate("Tasks", "类型"))
        item = self.tasks_table.horizontalHeaderItem(1)
        item.setText(_translate("Tasks", "报文内容"))
        item = self.tasks_table.horizontalHeaderItem(2)
        item.setText(_translate("Tasks", "执行时间"))
        item = self.tasks_table.horizontalHeaderItem(3)
        item.setText(_translate("Tasks", "添加时间"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    Tasks = QtWidgets.QDialog()
    ui = Ui_Tasks()
    ui.setupUi(Tasks)
    Tasks.show()
    sys.exit(app.exec_())

