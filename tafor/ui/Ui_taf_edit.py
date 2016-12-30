# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'D:\Work\tafor\tafor\ui\taf_edit.ui'
#
# Created by: PyQt5 UI code generator 5.6
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_TAFEdit(object):
    def setupUi(self, TAFEdit):
        TAFEdit.setObjectName("TAFEdit")
        TAFEdit.resize(1024, 243)
        TAFEdit.setMaximumSize(QtCore.QSize(1024, 16777215))
        self.verticalLayout = QtWidgets.QVBoxLayout(TAFEdit)
        self.verticalLayout.setSizeConstraint(QtWidgets.QLayout.SetFixedSize)
        self.verticalLayout.setObjectName("verticalLayout")
        self.main_frame = QtWidgets.QFrame(TAFEdit)
        self.main_frame.setObjectName("main_frame")
        self.main = QtWidgets.QVBoxLayout(self.main_frame)
        self.main.setSizeConstraint(QtWidgets.QLayout.SetDefaultConstraint)
        self.main.setObjectName("main")
        self.verticalLayout.addWidget(self.main_frame)
        self.taf_next = QtWidgets.QPushButton(TAFEdit)
        self.taf_next.setMaximumSize(QtCore.QSize(70, 23))
        self.taf_next.setObjectName("taf_next")
        self.verticalLayout.addWidget(self.taf_next, 0, QtCore.Qt.AlignRight|QtCore.Qt.AlignBottom)

        self.retranslateUi(TAFEdit)
        QtCore.QMetaObject.connectSlotsByName(TAFEdit)

    def retranslateUi(self, TAFEdit):
        _translate = QtCore.QCoreApplication.translate
        TAFEdit.setWindowTitle(_translate("TAFEdit", "TAF"))
        self.taf_next.setText(_translate("TAFEdit", "下一步"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    TAFEdit = QtWidgets.QDialog()
    ui = Ui_TAFEdit()
    ui.setupUi(TAFEdit)
    TAFEdit.show()
    sys.exit(app.exec_())

