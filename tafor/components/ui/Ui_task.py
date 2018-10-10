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
        Tasks.resize(870, 243)
        self.verticalLayout = QtWidgets.QVBoxLayout(Tasks)
        self.verticalLayout.setObjectName("verticalLayout")
        self.table = QtWidgets.QTableWidget(Tasks)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.setObjectName("table")
        self.table.setColumnCount(4)
        self.table.setRowCount(0)
        item = QtWidgets.QTableWidgetItem()
        self.table.setHorizontalHeaderItem(0, item)
        item = QtWidgets.QTableWidgetItem()
        self.table.setHorizontalHeaderItem(1, item)
        item = QtWidgets.QTableWidgetItem()
        self.table.setHorizontalHeaderItem(2, item)
        item = QtWidgets.QTableWidgetItem()
        self.table.setHorizontalHeaderItem(3, item)
        self.verticalLayout.addWidget(self.table)
        self.bottom = QtWidgets.QWidget(Tasks)
        self.bottom.setObjectName("bottom")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.bottom)
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.trashButton = QtWidgets.QToolButton(self.bottom)
        self.trashButton.setText("...")
        self.trashButton.setAutoRaise(True)
        self.trashButton.setObjectName("trashButton")
        self.horizontalLayout.addWidget(self.trashButton)
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.verticalLayout.addWidget(self.bottom)

        self.retranslateUi(Tasks)
        QtCore.QMetaObject.connectSlotsByName(Tasks)

    def retranslateUi(self, Tasks):
        _translate = QtCore.QCoreApplication.translate
        Tasks.setWindowTitle(_translate("Tasks", "Delayed Tasks"))
        item = self.table.horizontalHeaderItem(0)
        item.setText(_translate("Tasks", "Type"))
        item = self.table.horizontalHeaderItem(1)
        item.setText(_translate("Tasks", "Message Content"))
        item = self.table.horizontalHeaderItem(2)
        item.setText(_translate("Tasks", "Sending Time"))
        item = self.table.horizontalHeaderItem(3)
        item.setText(_translate("Tasks", "Created Time"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    Tasks = QtWidgets.QDialog()
    ui = Ui_Tasks()
    ui.setupUi(Tasks)
    Tasks.show()
    sys.exit(app.exec_())

