# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'D:\Work\tafor\tafor\components\ui\send.ui'
#
# Created by: PyQt5 UI code generator 5.6
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Sender(object):
    def setupUi(self, Sender):
        Sender.setObjectName("Sender")
        Sender.resize(738, 488)
        self.verticalLayout = QtWidgets.QVBoxLayout(Sender)
        self.verticalLayout.setSizeConstraint(QtWidgets.QLayout.SetFixedSize)
        self.verticalLayout.setObjectName("verticalLayout")
        self.rptGroup = QtWidgets.QGroupBox(Sender)
        self.rptGroup.setObjectName("rptGroup")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.rptGroup)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.rpt = QtWidgets.QTextEdit(self.rptGroup)
        self.rpt.setMinimumSize(QtCore.QSize(700, 0))
        self.rpt.setMaximumSize(QtCore.QSize(16777215, 100))
        self.rpt.setHtml("<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"</style></head><body style=\" font-family:\'SimSun\'; font-size:9pt; font-weight:400; font-style:normal;\">\n"
"<p style=\" margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">Rpt Content</p></body></html>")
        self.rpt.setTextInteractionFlags(QtCore.Qt.TextSelectableByKeyboard|QtCore.Qt.TextSelectableByMouse)
        self.rpt.setObjectName("rpt")
        self.verticalLayout_2.addWidget(self.rpt)
        self.verticalLayout.addWidget(self.rptGroup)
        self.rawGroup = QtWidgets.QGroupBox(Sender)
        self.rawGroup.setObjectName("rawGroup")
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(self.rawGroup)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.raw = QtWidgets.QTextEdit(self.rawGroup)
        self.raw.setMinimumSize(QtCore.QSize(700, 300))
        self.raw.setStyleSheet("background-color: rgb(0, 0, 0);\n"
"color: rgb(255, 255, 255);")
        self.raw.setHtml("<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"</style></head><body style=\" font-family:\'SimSun\'; font-size:9pt; font-weight:400; font-style:normal;\">\n"
"<p style=\" margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">Raw Content</p></body></html>")
        self.raw.setObjectName("raw")
        self.verticalLayout_3.addWidget(self.raw)
        self.verticalLayout.addWidget(self.rawGroup)
        self.buttonBox = QtWidgets.QDialogButtonBox(Sender)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok|QtWidgets.QDialogButtonBox.Retry)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(Sender)
        self.buttonBox.rejected.connect(Sender.reject)
        QtCore.QMetaObject.connectSlotsByName(Sender)

    def retranslateUi(self, Sender):
        _translate = QtCore.QCoreApplication.translate
        Sender.setWindowTitle(_translate("Sender", "Send Message"))
        self.rptGroup.setTitle(_translate("Sender", "Message"))
        self.rawGroup.setTitle(_translate("Sender", "Data has been sent to the serial port"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    Sender = QtWidgets.QDialog()
    ui = Ui_Sender()
    ui.setupUi(Sender)
    Sender.show()
    sys.exit(app.exec_())

