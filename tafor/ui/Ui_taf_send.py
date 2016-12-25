# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'D:\Work\tafor\tafor\ui\taf_send.ui'
#
# Created by: PyQt5 UI code generator 5.6
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_TAFSend(object):
    def setupUi(self, TAFSend):
        TAFSend.setObjectName("TAFSend")
        TAFSend.resize(1024, 300)
        self.verticalLayout = QtWidgets.QVBoxLayout(TAFSend)
        self.verticalLayout.setObjectName("verticalLayout")
        self.rpt_content = QtWidgets.QTextBrowser(TAFSend)
        self.rpt_content.setObjectName("rpt_content")
        self.verticalLayout.addWidget(self.rpt_content)
        self.post_box = QtWidgets.QDialogButtonBox(TAFSend)
        self.post_box.setOrientation(QtCore.Qt.Horizontal)
        self.post_box.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.post_box.setObjectName("post_box")
        self.verticalLayout.addWidget(self.post_box)

        self.retranslateUi(TAFSend)
        self.post_box.accepted.connect(TAFSend.accept)
        self.post_box.rejected.connect(TAFSend.reject)
        QtCore.QMetaObject.connectSlotsByName(TAFSend)

    def retranslateUi(self, TAFSend):
        _translate = QtCore.QCoreApplication.translate
        TAFSend.setWindowTitle(_translate("TAFSend", "发布 TAF 报文"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    TAFSend = QtWidgets.QDialog()
    ui = Ui_TAFSend()
    ui.setupUi(TAFSend)
    TAFSend.show()
    sys.exit(app.exec_())

