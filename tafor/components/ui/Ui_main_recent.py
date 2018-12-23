# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'D:\Work\tafor\tafor\components\ui\main_recent.ui'
#
# Created by: PyQt5 UI code generator 5.6
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Recent(object):
    def setupUi(self, Recent):
        Recent.setObjectName("Recent")
        Recent.resize(845, 88)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(Recent.sizePolicy().hasHeightForWidth())
        Recent.setSizePolicy(sizePolicy)
        Recent.setWindowTitle("Recent")
        self.verticalLayout = QtWidgets.QVBoxLayout(Recent)
        self.verticalLayout.setObjectName("verticalLayout")
        self.groupBox = QtWidgets.QGroupBox(Recent)
        self.groupBox.setTitle("Report Type")
        self.groupBox.setObjectName("groupBox")
        self.gridLayout = QtWidgets.QGridLayout(self.groupBox)
        self.gridLayout.setSizeConstraint(QtWidgets.QLayout.SetDefaultConstraint)
        self.gridLayout.setObjectName("gridLayout")
        self.check = QtWidgets.QLabel(self.groupBox)
        self.check.setText("isChecked")
        self.check.setObjectName("check")
        self.gridLayout.addWidget(self.check, 0, 1, 1, 1, QtCore.Qt.AlignRight)
        self.sendTime = QtWidgets.QLabel(self.groupBox)
        self.sendTime.setText("Sent Time")
        self.sendTime.setObjectName("sendTime")
        self.gridLayout.addWidget(self.sendTime, 0, 0, 1, 1)
        self.rpt = QtWidgets.QLabel(self.groupBox)
        self.rpt.setText("Report Content")
        self.rpt.setObjectName("rpt")
        self.gridLayout.addWidget(self.rpt, 3, 0, 1, 2)
        self.verticalLayout.addWidget(self.groupBox)

        self.retranslateUi(Recent)
        QtCore.QMetaObject.connectSlotsByName(Recent)

    def retranslateUi(self, Recent):
        pass


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    Recent = QtWidgets.QWidget()
    ui = Ui_Recent()
    ui.setupUi(Recent)
    Recent.show()
    sys.exit(app.exec_())

