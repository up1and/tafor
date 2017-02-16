# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'D:\Chen\Work\tafor\tafor\ui\send.ui'
#
# Created by: PyQt5 UI code generator 5.6
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Send(object):
    def setupUi(self, Send):
        Send.setObjectName("Send")
        Send.resize(738, 488)
        self.verticalLayout = QtWidgets.QVBoxLayout(Send)
        self.verticalLayout.setSizeConstraint(QtWidgets.QLayout.SetFixedSize)
        self.verticalLayout.setObjectName("verticalLayout")
        self.rpt_group = QtWidgets.QGroupBox(Send)
        self.rpt_group.setObjectName("rpt_group")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.rpt_group)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.rpt = QtWidgets.QTextEdit(self.rpt_group)
        self.rpt.setMinimumSize(QtCore.QSize(700, 0))
        self.rpt.setMaximumSize(QtCore.QSize(16777215, 100))
        self.rpt.setTextInteractionFlags(QtCore.Qt.TextSelectableByKeyboard|QtCore.Qt.TextSelectableByMouse)
        self.rpt.setObjectName("rpt")
        self.verticalLayout_2.addWidget(self.rpt)
        self.verticalLayout.addWidget(self.rpt_group)
        self.raw_group = QtWidgets.QGroupBox(Send)
        self.raw_group.setObjectName("raw_group")
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(self.raw_group)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.raw = QtWidgets.QTextEdit(self.raw_group)
        self.raw.setMinimumSize(QtCore.QSize(700, 300))
        self.raw.setStyleSheet("background-color: rgb(0, 0, 0);\n"
"color: rgb(255, 255, 255);")
        self.raw.setObjectName("raw")
        self.verticalLayout_3.addWidget(self.raw)
        self.verticalLayout.addWidget(self.raw_group)
        self.button_box = QtWidgets.QDialogButtonBox(Send)
        self.button_box.setOrientation(QtCore.Qt.Horizontal)
        self.button_box.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.button_box.setObjectName("button_box")
        self.verticalLayout.addWidget(self.button_box)

        self.retranslateUi(Send)
        self.button_box.rejected.connect(Send.reject)
        QtCore.QMetaObject.connectSlotsByName(Send)

    def retranslateUi(self, Send):
        _translate = QtCore.QCoreApplication.translate
        Send.setWindowTitle(_translate("Send", "发布报文"))
        self.rpt_group.setTitle(_translate("Send", "报文"))
        self.rpt.setHtml(_translate("Send", "<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"</style></head><body style=\" font-family:\'SimSun\'; font-size:9pt; font-weight:400; font-style:normal;\">\n"
"<p style=\" margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">Rpt Content</p></body></html>"))
        self.raw_group.setTitle(_translate("Send", "已向串口发送数据"))
        self.raw.setHtml(_translate("Send", "<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"</style></head><body style=\" font-family:\'SimSun\'; font-size:9pt; font-weight:400; font-style:normal;\">\n"
"<p style=\" margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">Raw Content</p></body></html>"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    Send = QtWidgets.QDialog()
    ui = Ui_Send()
    ui.setupUi(Send)
    Send.show()
    sys.exit(app.exec_())

