# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'D:\Work\tafor\tafor\components\ui\sigmet_custom.ui'
#
# Created by: PyQt5 UI code generator 5.13.2
#
# WARNING! All changes made in this file will be lost!


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Editor(object):
    def setupUi(self, Editor):
        Editor.setObjectName("Editor")
        Editor.resize(754, 158)
        Editor.setWindowTitle("Sigmet")
        self.gridLayout = QtWidgets.QGridLayout(Editor)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.gridLayout.setObjectName("gridLayout")
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
        self.gridLayout.addWidget(self.textGroup, 0, 1, 1, 1, QtCore.Qt.AlignLeft|QtCore.Qt.AlignTop)
        self.headGroup = QtWidgets.QGroupBox(Editor)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.headGroup.sizePolicy().hasHeightForWidth())
        self.headGroup.setSizePolicy(sizePolicy)
        self.headGroup.setObjectName("headGroup")
        self.gridLayout_2 = QtWidgets.QGridLayout(self.headGroup)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.sequence = QtWidgets.QLineEdit(self.headGroup)
        self.sequence.setObjectName("sequence")
        self.gridLayout_2.addWidget(self.sequence, 5, 0, 1, 1)
        self.endingTimeLabel = QtWidgets.QLabel(self.headGroup)
        self.endingTimeLabel.setObjectName("endingTimeLabel")
        self.gridLayout_2.addWidget(self.endingTimeLabel, 2, 0, 1, 1)
        self.sequenceLabel = QtWidgets.QLabel(self.headGroup)
        self.sequenceLabel.setObjectName("sequenceLabel")
        self.gridLayout_2.addWidget(self.sequenceLabel, 4, 0, 1, 1)
        self.beginningTimeLabel = QtWidgets.QLabel(self.headGroup)
        self.beginningTimeLabel.setObjectName("beginningTimeLabel")
        self.gridLayout_2.addWidget(self.beginningTimeLabel, 0, 0, 1, 1)
        self.endingTime = QtWidgets.QLineEdit(self.headGroup)
        self.endingTime.setObjectName("endingTime")
        self.gridLayout_2.addWidget(self.endingTime, 3, 0, 1, 1)
        self.beginningTime = QtWidgets.QLineEdit(self.headGroup)
        self.beginningTime.setObjectName("beginningTime")
        self.gridLayout_2.addWidget(self.beginningTime, 1, 0, 1, 1)
        self.gridLayout.addWidget(self.headGroup, 0, 0, 1, 1, QtCore.Qt.AlignLeft|QtCore.Qt.AlignTop)
        self.endingTimeLabel.setBuddy(self.endingTime)
        self.sequenceLabel.setBuddy(self.sequence)
        self.beginningTimeLabel.setBuddy(self.beginningTime)

        self.retranslateUi(Editor)
        QtCore.QMetaObject.connectSlotsByName(Editor)

    def retranslateUi(self, Editor):
        _translate = QtCore.QCoreApplication.translate
        self.textGroup.setTitle(_translate("Editor", "Text"))
        self.headGroup.setTitle(_translate("Editor", "Head"))
        self.endingTimeLabel.setText(_translate("Editor", "Ending"))
        self.sequenceLabel.setText(_translate("Editor", "Sequence"))
        self.beginningTimeLabel.setText(_translate("Editor", "Beginning"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    Editor = QtWidgets.QWidget()
    ui = Ui_Editor()
    ui.setupUi(Editor)
    Editor.show()
    sys.exit(app.exec_())
