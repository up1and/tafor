# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'D:\Work\tafor\tafor\ui\schedule_list.ui'
#
# Created by: PyQt5 UI code generator 5.6
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_schedule_list(object):
    def setupUi(self, schedule_list):
        schedule_list.setObjectName("schedule_list")
        schedule_list.resize(857, 640)
        self.verticalLayout = QtWidgets.QVBoxLayout(schedule_list)
        self.verticalLayout.setObjectName("verticalLayout")
        self.sch_layout = QtWidgets.QHBoxLayout()
        self.sch_layout.setObjectName("sch_layout")
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.sch_layout.addItem(spacerItem)
        self.add_sch_button = QtWidgets.QPushButton(schedule_list)
        self.add_sch_button.setMaximumSize(QtCore.QSize(25, 16777215))
        self.add_sch_button.setAutoDefault(False)
        self.add_sch_button.setObjectName("add_sch_button")
        self.sch_layout.addWidget(self.add_sch_button)
        self.del_sch_button = QtWidgets.QPushButton(schedule_list)
        self.del_sch_button.setMaximumSize(QtCore.QSize(25, 16777215))
        self.del_sch_button.setAutoDefault(False)
        self.del_sch_button.setObjectName("del_sch_button")
        self.sch_layout.addWidget(self.del_sch_button)
        self.verticalLayout.addLayout(self.sch_layout)
        self.sch_table = QtWidgets.QTableWidget(schedule_list)
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

        self.retranslateUi(schedule_list)
        QtCore.QMetaObject.connectSlotsByName(schedule_list)

    def retranslateUi(self, schedule_list):
        _translate = QtCore.QCoreApplication.translate
        schedule_list.setWindowTitle(_translate("schedule_list", "定时任务列表"))
        self.add_sch_button.setText(_translate("schedule_list", "+"))
        self.del_sch_button.setText(_translate("schedule_list", "-"))
        item = self.sch_table.horizontalHeaderItem(0)
        item.setText(_translate("schedule_list", "类型"))
        item = self.sch_table.horizontalHeaderItem(1)
        item.setText(_translate("schedule_list", "报文内容"))
        item = self.sch_table.horizontalHeaderItem(2)
        item.setText(_translate("schedule_list", "执行时间"))
        item = self.sch_table.horizontalHeaderItem(3)
        item.setText(_translate("schedule_list", "添加时间"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    schedule_list = QtWidgets.QDialog()
    ui = Ui_schedule_list()
    ui.setupUi(schedule_list)
    schedule_list.show()
    sys.exit(app.exec_())

