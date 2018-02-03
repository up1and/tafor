# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'D:\Work\tafor\tafor\components\ui\task.ui'
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
        self.taskTable = QtWidgets.QTableWidget(Tasks)
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

        self.retranslateUi(Tasks)
        QtCore.QMetaObject.connectSlotsByName(Tasks)

    def retranslateUi(self, Tasks):
        _translate = QtCore.QCoreApplication.translate
        Tasks.setWindowTitle(_translate("Tasks", "Timing Tasks"))
        item = self.taskTable.horizontalHeaderItem(0)
        item.setText(_translate("Tasks", "Type"))
        item = self.taskTable.horizontalHeaderItem(1)
        item.setText(_translate("Tasks", "Message Content"))
        item = self.taskTable.horizontalHeaderItem(2)
        item.setText(_translate("Tasks", "Sending Time"))
        item = self.taskTable.horizontalHeaderItem(3)
        item.setText(_translate("Tasks", "Created Time"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    Tasks = QtWidgets.QDialog()
    ui = Ui_Tasks()
    ui.setupUi(Tasks)
    Tasks.show()
    sys.exit(app.exec_())

