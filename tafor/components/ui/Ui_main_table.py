# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'D:\Chen\Work\tafor\tafor\components\ui\main_table.ui'
#
# Created by: PyQt5 UI code generator 5.6
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_DataTable(object):
    def setupUi(self, DataTable):
        DataTable.setObjectName("DataTable")
        DataTable.resize(868, 381)
        DataTable.setWindowTitle("DataTable")
        self.verticalLayout = QtWidgets.QVBoxLayout(DataTable)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.table = QtWidgets.QTableWidget(DataTable)
        self.table.setMinimumSize(QtCore.QSize(850, 0))
        self.table.setFrameShadow(QtWidgets.QFrame.Raised)
        self.table.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
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

        self.retranslateUi(DataTable)
        QtCore.QMetaObject.connectSlotsByName(DataTable)

    def retranslateUi(self, DataTable):
        _translate = QtCore.QCoreApplication.translate
        item = self.table.horizontalHeaderItem(0)
        item.setText(_translate("DataTable", "Type"))
        item = self.table.horizontalHeaderItem(1)
        item.setText(_translate("DataTable", "Message Content"))
        item = self.table.horizontalHeaderItem(2)
        item.setText(_translate("DataTable", "Sent Time"))
        item = self.table.horizontalHeaderItem(3)
        item.setText(_translate("DataTable", "Check"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    DataTable = QtWidgets.QWidget()
    ui = Ui_DataTable()
    ui.setupUi(DataTable)
    DataTable.show()
    sys.exit(app.exec_())

