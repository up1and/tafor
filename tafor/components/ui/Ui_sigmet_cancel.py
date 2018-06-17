# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'D:\Work\tafor\tafor\components\ui\sigmet_cancel.ui'
#
# Created by: PyQt5 UI code generator 5.6
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Editor(object):
    def setupUi(self, Editor):
        Editor.setObjectName("Editor")
        Editor.resize(449, 88)
        Editor.setWindowTitle("Sigmet")
        self.verticalLayout = QtWidgets.QVBoxLayout(Editor)
        self.verticalLayout.setObjectName("verticalLayout")
        self.cancelGroup = QtWidgets.QGroupBox(Editor)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.cancelGroup.sizePolicy().hasHeightForWidth())
        self.cancelGroup.setSizePolicy(sizePolicy)
        self.cancelGroup.setObjectName("cancelGroup")
        self.gridLayout = QtWidgets.QGridLayout(self.cancelGroup)
        self.gridLayout.setObjectName("gridLayout")
        self.beginningTimeLabel = QtWidgets.QLabel(self.cancelGroup)
        self.beginningTimeLabel.setObjectName("beginningTimeLabel")
        self.gridLayout.addWidget(self.beginningTimeLabel, 0, 1, 1, 1)
        self.sequenceLabel = QtWidgets.QLabel(self.cancelGroup)
        self.sequenceLabel.setObjectName("sequenceLabel")
        self.gridLayout.addWidget(self.sequenceLabel, 0, 0, 1, 1)
        self.endingTimeLabel = QtWidgets.QLabel(self.cancelGroup)
        self.endingTimeLabel.setObjectName("endingTimeLabel")
        self.gridLayout.addWidget(self.endingTimeLabel, 0, 2, 1, 1)
        self.endingTime = QtWidgets.QLineEdit(self.cancelGroup)
        self.endingTime.setObjectName("endingTime")
        self.gridLayout.addWidget(self.endingTime, 2, 2, 1, 1)
        self.beginningTime = QtWidgets.QLineEdit(self.cancelGroup)
        self.beginningTime.setObjectName("beginningTime")
        self.gridLayout.addWidget(self.beginningTime, 2, 1, 1, 1)
        self.sequence = QtWidgets.QComboBox(self.cancelGroup)
        self.sequence.setEditable(True)
        self.sequence.setObjectName("sequence")
        self.gridLayout.addWidget(self.sequence, 2, 0, 1, 1)
        self.verticalLayout.addWidget(self.cancelGroup)
        self.beginningTimeLabel.setBuddy(self.beginningTime)
        self.sequenceLabel.setBuddy(self.sequence)
        self.endingTimeLabel.setBuddy(self.endingTime)

        self.retranslateUi(Editor)
        QtCore.QMetaObject.connectSlotsByName(Editor)
        Editor.setTabOrder(self.sequence, self.beginningTime)
        Editor.setTabOrder(self.beginningTime, self.endingTime)

    def retranslateUi(self, Editor):
        _translate = QtCore.QCoreApplication.translate
        self.cancelGroup.setTitle(_translate("Editor", "Cancel Information"))
        self.beginningTimeLabel.setText(_translate("Editor", "Beginning Time"))
        self.sequenceLabel.setText(_translate("Editor", "Sequence"))
        self.endingTimeLabel.setText(_translate("Editor", "Ending Time"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    Editor = QtWidgets.QWidget()
    ui = Ui_Editor()
    ui.setupUi(Editor)
    Editor.show()
    sys.exit(app.exec_())

