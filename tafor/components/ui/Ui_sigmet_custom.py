# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'D:\Work\tafor\tafor\components\ui\sigmet_custom.ui'
#
# Created by: PyQt5 UI code generator 5.6
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Editor(object):
    def setupUi(self, Editor):
        Editor.setObjectName("Editor")
        Editor.resize(618, 298)
        Editor.setWindowTitle("Sigmet")
        self.verticalLayout = QtWidgets.QVBoxLayout(Editor)
        self.verticalLayout.setContentsMargins(-1, 0, -1, 0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.textGroup = QtWidgets.QGroupBox(Editor)
        self.textGroup.setObjectName("textGroup")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.textGroup)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.text = QtWidgets.QTextEdit(self.textGroup)
        self.text.setMinimumSize(QtCore.QSize(575, 0))
        self.text.setHtml("<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"</style></head><body style=\" font-family:\'SimSun\'; font-size:9pt; font-weight:400; font-style:normal;\">\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><br /></p></body></html>")
        self.text.setAcceptRichText(False)
        self.text.setObjectName("text")
        self.verticalLayout_2.addWidget(self.text)
        self.verticalLayout.addWidget(self.textGroup)

        self.retranslateUi(Editor)
        QtCore.QMetaObject.connectSlotsByName(Editor)

    def retranslateUi(self, Editor):
        _translate = QtCore.QCoreApplication.translate
        self.textGroup.setTitle(_translate("Editor", "Text"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    Editor = QtWidgets.QWidget()
    ui = Ui_Editor()
    ui.setupUi(Editor)
    Editor.show()
    sys.exit(app.exec_())

