# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'D:\Work\tafor\tafor\components\ui\main_table.ui'
#
# Created by: PyQt5 UI code generator 5.13.2
#
# WARNING! All changes made in this file will be lost!


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_DataTable(object):
    def setupUi(self, DataTable):
        DataTable.setObjectName("DataTable")
        DataTable.resize(850, 230)
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
        self.pagination = QtWidgets.QWidget(DataTable)
        self.pagination.setObjectName("pagination")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.pagination)
        self.horizontalLayout.setObjectName("horizontalLayout")
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.infoButton = QtWidgets.QToolButton(self.pagination)
        self.infoButton.setText("Info")
        self.infoButton.setAutoRaise(True)
        self.infoButton.setObjectName("infoButton")
        self.horizontalLayout.addWidget(self.infoButton)
        self.chartButton = QtWidgets.QToolButton(self.pagination)
        self.chartButton.setText("Chart")
        self.chartButton.setAutoRaise(True)
        self.chartButton.setObjectName("chartButton")
        self.horizontalLayout.addWidget(self.chartButton)
        self.exportButton = QtWidgets.QToolButton(self.pagination)
        self.exportButton.setText("Export")
        self.exportButton.setAutoRaise(True)
        self.exportButton.setObjectName("exportButton")
        self.horizontalLayout.addWidget(self.exportButton)
        self.calendarButton = QtWidgets.QToolButton(self.pagination)
        self.calendarButton.setText("Calendar")
        self.calendarButton.setCheckable(True)
        self.calendarButton.setAutoRaise(True)
        self.calendarButton.setObjectName("calendarButton")
        self.horizontalLayout.addWidget(self.calendarButton)
        self.calendar = QtWidgets.QDateEdit(self.pagination)
        self.calendar.setMaximumSize(QtCore.QSize(20, 16777215))
        self.calendar.setCalendarPopup(True)
        self.calendar.setObjectName("calendar")
        self.horizontalLayout.addWidget(self.calendar)
        self.search = QtWidgets.QLineEdit(self.pagination)
        self.search.setMaximumSize(QtCore.QSize(100, 16777215))
        self.search.setStyleSheet("border: 0;")
        self.search.setInputMethodHints(QtCore.Qt.ImhPreferUppercase)
        self.search.setClearButtonEnabled(True)
        self.search.setObjectName("search")
        self.horizontalLayout.addWidget(self.search)
        self.prevButton = QtWidgets.QToolButton(self.pagination)
        self.prevButton.setText("Prev")
        self.prevButton.setAutoRaise(True)
        self.prevButton.setArrowType(QtCore.Qt.NoArrow)
        self.prevButton.setObjectName("prevButton")
        self.horizontalLayout.addWidget(self.prevButton)
        self.pagesLabel = QtWidgets.QLabel(self.pagination)
        self.pagesLabel.setText("Pages")
        self.pagesLabel.setObjectName("pagesLabel")
        self.horizontalLayout.addWidget(self.pagesLabel)
        self.nextButton = QtWidgets.QToolButton(self.pagination)
        self.nextButton.setText("Next")
        self.nextButton.setAutoRaise(True)
        self.nextButton.setObjectName("nextButton")
        self.horizontalLayout.addWidget(self.nextButton)
        self.verticalLayout.addWidget(self.pagination)

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
        self.search.setPlaceholderText(_translate("DataTable", "Search..."))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    DataTable = QtWidgets.QWidget()
    ui = Ui_DataTable()
    ui.setupUi(DataTable)
    DataTable.show()
    sys.exit(app.exec_())
