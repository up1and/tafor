# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'D:\Work\tafor\tafor\ui\widgets_recent_item.ui'
#
# Created by: PyQt5 UI code generator 5.6
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.resize(549, 142)
        self.verticalLayout = QtWidgets.QVBoxLayout(Form)
        self.verticalLayout.setObjectName("verticalLayout")
        self.groupBox = QtWidgets.QGroupBox(Form)
        self.groupBox.setObjectName("groupBox")
        self.gridLayout = QtWidgets.QGridLayout(self.groupBox)
        self.gridLayout.setSizeConstraint(QtWidgets.QLayout.SetDefaultConstraint)
        self.gridLayout.setObjectName("gridLayout")
        self.check = QtWidgets.QLabel(self.groupBox)
        self.check.setObjectName("check")
        self.gridLayout.addWidget(self.check, 0, 1, 1, 1, QtCore.Qt.AlignRight)
        self.send_time = QtWidgets.QLabel(self.groupBox)
        self.send_time.setObjectName("send_time")
        self.gridLayout.addWidget(self.send_time, 0, 0, 1, 1)
        self.rpt = QtWidgets.QLabel(self.groupBox)
        self.rpt.setStyleSheet("font: 12pt \"微软雅黑\";")
        self.rpt.setObjectName("rpt")
        self.gridLayout.addWidget(self.rpt, 3, 0, 1, 2)
        self.verticalLayout.addWidget(self.groupBox)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        _translate = QtCore.QCoreApplication.translate
        Form.setWindowTitle(_translate("Form", "Form"))
        self.groupBox.setTitle(_translate("Form", "FC"))
        self.check.setText(_translate("Form", "√"))
        self.send_time.setText(_translate("Form", "time"))
        self.rpt.setText(_translate("Form", "rpt"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    Form = QtWidgets.QWidget()
    ui = Ui_Form()
    ui.setupUi(Form)
    Form.show()
    sys.exit(app.exec_())

