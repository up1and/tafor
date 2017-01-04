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
        Form.resize(991, 139)
        self.verticalLayout = QtWidgets.QVBoxLayout(Form)
        self.verticalLayout.setObjectName("verticalLayout")
        self.item_widget = QtWidgets.QWidget(Form)
        self.item_widget.setObjectName("item_widget")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.item_widget)
        self.horizontalLayout.setSizeConstraint(QtWidgets.QLayout.SetDefaultConstraint)
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.type_label = QtWidgets.QLabel(self.item_widget)
        self.type_label.setObjectName("type_label")
        self.horizontalLayout.addWidget(self.type_label)
        self.type = QtWidgets.QLabel(self.item_widget)
        self.type.setObjectName("type")
        self.horizontalLayout.addWidget(self.type)
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.send_time_label = QtWidgets.QLabel(self.item_widget)
        self.send_time_label.setObjectName("send_time_label")
        self.horizontalLayout.addWidget(self.send_time_label)
        self.send_time = QtWidgets.QLabel(self.item_widget)
        self.send_time.setObjectName("send_time")
        self.horizontalLayout.addWidget(self.send_time)
        self.check_label = QtWidgets.QLabel(self.item_widget)
        self.check_label.setObjectName("check_label")
        self.horizontalLayout.addWidget(self.check_label)
        self.check = QtWidgets.QLabel(self.item_widget)
        self.check.setObjectName("check")
        self.horizontalLayout.addWidget(self.check)
        self.verticalLayout.addWidget(self.item_widget)
        self.rpt = QtWidgets.QLabel(Form)
        self.rpt.setObjectName("rpt")
        self.verticalLayout.addWidget(self.rpt)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        _translate = QtCore.QCoreApplication.translate
        Form.setWindowTitle(_translate("Form", "Form"))
        self.type_label.setText(_translate("Form", "类型"))
        self.type.setText(_translate("Form", "tt"))
        self.send_time_label.setText(_translate("Form", "发布时间"))
        self.send_time.setText(_translate("Form", "time"))
        self.check_label.setText(_translate("Form", "检查"))
        self.check.setText(_translate("Form", "√"))
        self.rpt.setText(_translate("Form", "报文内容"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    Form = QtWidgets.QWidget()
    ui = Ui_Form()
    ui.setupUi(Form)
    Form.show()
    sys.exit(app.exec_())

