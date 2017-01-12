# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'D:\Chen\Work\tafor\tafor\ui\taf_send.ui'
#
# Created by: PyQt5 UI code generator 5.6
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_TAFSend(object):
    def setupUi(self, TAFSend):
        TAFSend.setObjectName("TAFSend")
        TAFSend.resize(780, 259)
        self.verticalLayout = QtWidgets.QVBoxLayout(TAFSend)
        self.verticalLayout.setSizeConstraint(QtWidgets.QLayout.SetDefaultConstraint)
        self.verticalLayout.setObjectName("verticalLayout")
        self.rpt_group = QtWidgets.QGroupBox(TAFSend)
        self.rpt_group.setObjectName("rpt_group")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.rpt_group)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.rpt = QtWidgets.QTextEdit(self.rpt_group)
        self.rpt.setTextInteractionFlags(QtCore.Qt.TextSelectableByKeyboard|QtCore.Qt.TextSelectableByMouse)
        self.rpt.setObjectName("rpt")
        self.verticalLayout_2.addWidget(self.rpt)
        self.verticalLayout.addWidget(self.rpt_group)
        self.raw_group = QtWidgets.QGroupBox(TAFSend)
        self.raw_group.setObjectName("raw_group")
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(self.raw_group)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.raw = QtWidgets.QTextEdit(self.raw_group)
        self.raw.setStyleSheet("background-color: rgb(0, 0, 0);\n"
"color: rgb(255, 255, 255);")
        self.raw.setObjectName("raw")
        self.verticalLayout_3.addWidget(self.raw)
        self.verticalLayout.addWidget(self.raw_group)
        self.button_box = QtWidgets.QDialogButtonBox(TAFSend)
        self.button_box.setOrientation(QtCore.Qt.Horizontal)
        self.button_box.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.button_box.setObjectName("button_box")
        self.verticalLayout.addWidget(self.button_box)

        self.retranslateUi(TAFSend)
        self.button_box.accepted.connect(TAFSend.accept)
        self.button_box.rejected.connect(TAFSend.reject)
        QtCore.QMetaObject.connectSlotsByName(TAFSend)

    def retranslateUi(self, TAFSend):
        _translate = QtCore.QCoreApplication.translate
        TAFSend.setWindowTitle(_translate("TAFSend", "发布 TAF 报文"))
        self.rpt_group.setTitle(_translate("TAFSend", "报文"))
        self.rpt.setHtml(_translate("TAFSend", "<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"</style></head><body style=\" font-family:\'SimSun\'; font-size:9pt; font-weight:400; font-style:normal;\">\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">Rpt Content</p></body></html>"))
        self.raw_group.setTitle(_translate("TAFSend", "已向串口发送数据"))
        self.raw.setHtml(_translate("TAFSend", "<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"</style></head><body style=\" font-family:\'SimSun\'; font-size:9pt; font-weight:400; font-style:normal;\">\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">Raw Content</p></body></html>"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    TAFSend = QtWidgets.QDialog()
    ui = Ui_TAFSend()
    ui.setupUi(TAFSend)
    TAFSend.show()
    sys.exit(app.exec_())

