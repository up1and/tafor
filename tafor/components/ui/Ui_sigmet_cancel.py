# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'D:\Work\tafor\tafor\components\ui\sigmet_cancel.ui'
#
# Created by: PyQt5 UI code generator 5.13.2
#
# WARNING! All changes made in this file will be lost!


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Editor(object):
    def setupUi(self, Editor):
        Editor.setObjectName("Editor")
        Editor.resize(330, 158)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(Editor.sizePolicy().hasHeightForWidth())
        Editor.setSizePolicy(sizePolicy)
        Editor.setWindowTitle("Sigmet")
        self.horizontalLayout = QtWidgets.QHBoxLayout(Editor)
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.headGroup = QtWidgets.QGroupBox(Editor)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.headGroup.sizePolicy().hasHeightForWidth())
        self.headGroup.setSizePolicy(sizePolicy)
        self.headGroup.setObjectName("headGroup")
        self.gridLayout_2 = QtWidgets.QGridLayout(self.headGroup)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.endingTime = QtWidgets.QLineEdit(self.headGroup)
        self.endingTime.setObjectName("endingTime")
        self.gridLayout_2.addWidget(self.endingTime, 3, 0, 1, 1)
        self.endingTimeLabel = QtWidgets.QLabel(self.headGroup)
        self.endingTimeLabel.setObjectName("endingTimeLabel")
        self.gridLayout_2.addWidget(self.endingTimeLabel, 2, 0, 1, 1)
        self.beginningTime = QtWidgets.QLineEdit(self.headGroup)
        self.beginningTime.setObjectName("beginningTime")
        self.gridLayout_2.addWidget(self.beginningTime, 1, 0, 1, 1)
        self.beginningTimeLabel = QtWidgets.QLabel(self.headGroup)
        self.beginningTimeLabel.setObjectName("beginningTimeLabel")
        self.gridLayout_2.addWidget(self.beginningTimeLabel, 0, 0, 1, 1)
        self.sequence = QtWidgets.QLineEdit(self.headGroup)
        self.sequence.setObjectName("sequence")
        self.gridLayout_2.addWidget(self.sequence, 5, 0, 1, 1)
        self.sequenceLabel = QtWidgets.QLabel(self.headGroup)
        self.sequenceLabel.setObjectName("sequenceLabel")
        self.gridLayout_2.addWidget(self.sequenceLabel, 4, 0, 1, 1)
        self.horizontalLayout.addWidget(self.headGroup, 0, QtCore.Qt.AlignLeft|QtCore.Qt.AlignTop)
        self.cancelGroup = QtWidgets.QGroupBox(Editor)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.cancelGroup.sizePolicy().hasHeightForWidth())
        self.cancelGroup.setSizePolicy(sizePolicy)
        self.cancelGroup.setObjectName("cancelGroup")
        self.gridLayout = QtWidgets.QGridLayout(self.cancelGroup)
        self.gridLayout.setObjectName("gridLayout")
        self.cancelEndingTimeLabel = QtWidgets.QLabel(self.cancelGroup)
        self.cancelEndingTimeLabel.setObjectName("cancelEndingTimeLabel")
        self.gridLayout.addWidget(self.cancelEndingTimeLabel, 5, 0, 1, 1)
        self.cancelBeginningTimeLabel = QtWidgets.QLabel(self.cancelGroup)
        self.cancelBeginningTimeLabel.setObjectName("cancelBeginningTimeLabel")
        self.gridLayout.addWidget(self.cancelBeginningTimeLabel, 3, 0, 1, 1)
        self.cancelSequence = QtWidgets.QComboBox(self.cancelGroup)
        self.cancelSequence.setEditable(True)
        self.cancelSequence.setObjectName("cancelSequence")
        self.gridLayout.addWidget(self.cancelSequence, 2, 0, 1, 1)
        self.cancelBeginningTime = QtWidgets.QLineEdit(self.cancelGroup)
        self.cancelBeginningTime.setObjectName("cancelBeginningTime")
        self.gridLayout.addWidget(self.cancelBeginningTime, 4, 0, 1, 1)
        self.cancelSequenceLabel = QtWidgets.QLabel(self.cancelGroup)
        self.cancelSequenceLabel.setObjectName("cancelSequenceLabel")
        self.gridLayout.addWidget(self.cancelSequenceLabel, 0, 0, 1, 1)
        self.cancelEndingTime = QtWidgets.QLineEdit(self.cancelGroup)
        self.cancelEndingTime.setObjectName("cancelEndingTime")
        self.gridLayout.addWidget(self.cancelEndingTime, 6, 0, 1, 1)
        self.horizontalLayout.addWidget(self.cancelGroup, 0, QtCore.Qt.AlignLeft|QtCore.Qt.AlignTop)
        self.endingTimeLabel.setBuddy(self.cancelEndingTime)
        self.beginningTimeLabel.setBuddy(self.cancelBeginningTime)
        self.sequenceLabel.setBuddy(self.cancelSequence)
        self.cancelEndingTimeLabel.setBuddy(self.cancelEndingTime)
        self.cancelBeginningTimeLabel.setBuddy(self.cancelBeginningTime)
        self.cancelSequenceLabel.setBuddy(self.cancelSequence)

        self.retranslateUi(Editor)
        QtCore.QMetaObject.connectSlotsByName(Editor)

    def retranslateUi(self, Editor):
        _translate = QtCore.QCoreApplication.translate
        self.headGroup.setTitle(_translate("Editor", "Head"))
        self.endingTimeLabel.setText(_translate("Editor", "Ending"))
        self.beginningTimeLabel.setText(_translate("Editor", "Beginning"))
        self.sequenceLabel.setText(_translate("Editor", "Sequence"))
        self.cancelGroup.setTitle(_translate("Editor", "Cancel Information"))
        self.cancelEndingTimeLabel.setText(_translate("Editor", "Ending"))
        self.cancelBeginningTimeLabel.setText(_translate("Editor", "Beginning"))
        self.cancelSequenceLabel.setText(_translate("Editor", "Sequence"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    Editor = QtWidgets.QWidget()
    ui = Ui_Editor()
    ui.setupUi(Editor)
    Editor.show()
    sys.exit(app.exec_())
