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
        self.taskTable = QtWidgets.QTableWidget(Task)
        self.taskTable.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.taskTable.setObjectName("taskTable")
        self.taskTable.setColumnCount(4)
        self.taskTable.setRowCount(0)
        item = QtWidgets.QTableWidgetItem()
        self.taskTable.setHorizontalHeaderItem(0, item)
        item = QtWidgets.QTableWidgetItem()
        self.taskTable.setHorizontalHeaderItem(1, item)
        item = QtWidgets.QTableWidgetItem()
        self.taskTable.setHorizontalHeaderItem(2, item)
        item = QtWidgets.QTableWidgetItem()
        self.taskTable.setHorizontalHeaderItem(3, item)
        self.verticalLayout.addWidget(self.taskTable)

        self.retranslateUi(Task)
        QtCore.QMetaObject.connectSlotsByName(Task)

    def retranslateUi(self, Task):
        _translate = QtCore.QCoreApplication.translate
        Task.setWindowTitle(_translate("Task", "Timing Tasks"))
        item = self.taskTable.horizontalHeaderItem(0)
        item.setText(_translate("Task", "Type"))
        item = self.taskTable.horizontalHeaderItem(1)
        item.setText(_translate("Task", "Message Content"))
        item = self.taskTable.horizontalHeaderItem(2)
        item.setText(_translate("Task", "Sending Time"))
        item = self.taskTable.horizontalHeaderItem(3)
        item.setText(_translate("Task", "Created Time"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    Task = QtWidgets.QDialog()
    ui = Ui_Task()
    ui.setupUi(Task)
    Task.show()
    sys.exit(app.exec_())

