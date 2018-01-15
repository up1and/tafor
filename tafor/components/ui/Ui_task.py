# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'D:\Work\tafor\tafor\components\ui\task.ui'
#
# Created by: PyQt5 UI code generator 5.6
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Task(object):
    def setupUi(self, Task):
        Task.setObjectName("Task")
        Task.resize(950, 243)
        self.verticalLayout = QtWidgets.QVBoxLayout(Task)
        self.verticalLayout.setObjectName("verticalLayout")
        self.tasks_table = QtWidgets.QTableWidget(Task)
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

        self.retranslateUi(Task)
        QtCore.QMetaObject.connectSlotsByName(Task)

    def retranslateUi(self, Task):
        _translate = QtCore.QCoreApplication.translate
        Task.setWindowTitle(_translate("Task", "定时任务列表"))
        item = self.tasks_table.horizontalHeaderItem(0)
        item.setText(_translate("Task", "类型"))
        item = self.tasks_table.horizontalHeaderItem(1)
        item.setText(_translate("Task", "报文内容"))
        item = self.tasks_table.horizontalHeaderItem(2)
        item.setText(_translate("Task", "执行时间"))
        item = self.tasks_table.horizontalHeaderItem(3)
        item.setText(_translate("Task", "添加时间"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    Task = QtWidgets.QDialog()
    ui = Ui_Task()
    ui.setupUi(Task)
    Task.show()
    sys.exit(app.exec_())

