# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'd:\Work\tafor\tafor\components\ui\sigmet_cancel.ui'
#
# Created by: PyQt5 UI code generator 5.15.4
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Editor(object):
    def setupUi(self, Editor):
        Editor.setObjectName("Editor")
        Editor.resize(431, 152)
        Editor.setWindowTitle("Sigmet")
        self.verticalLayout = QtWidgets.QVBoxLayout(Editor)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.headingGroup = QtWidgets.QGroupBox(Editor)
        self.headingGroup.setObjectName("headingGroup")
        self.gridLayout_2 = QtWidgets.QGridLayout(self.headingGroup)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.endingTime = QtWidgets.QLineEdit(self.headingGroup)
        self.endingTime.setObjectName("endingTime")
        self.gridLayout_2.addWidget(self.endingTime, 1, 1, 1, 1)
        self.endingTimeLabel = QtWidgets.QLabel(self.headingGroup)
        self.endingTimeLabel.setObjectName("endingTimeLabel")
        self.gridLayout_2.addWidget(self.endingTimeLabel, 0, 1, 1, 1)
        self.beginningTimeLabel = QtWidgets.QLabel(self.headingGroup)
        self.beginningTimeLabel.setObjectName("beginningTimeLabel")
        self.gridLayout_2.addWidget(self.beginningTimeLabel, 0, 0, 1, 1)
        self.beginningTime = QtWidgets.QLineEdit(self.headingGroup)
        self.beginningTime.setObjectName("beginningTime")
        self.gridLayout_2.addWidget(self.beginningTime, 1, 0, 1, 1)
        self.sequenceLabel = QtWidgets.QLabel(self.headingGroup)
        self.sequenceLabel.setObjectName("sequenceLabel")
        self.gridLayout_2.addWidget(self.sequenceLabel, 0, 2, 1, 1)
        self.sequence = QtWidgets.QLineEdit(self.headingGroup)
        self.sequence.setObjectName("sequence")
        self.gridLayout_2.addWidget(self.sequence, 1, 2, 1, 1)
        self.verticalLayout.addWidget(self.headingGroup)
        self.cancelGroup = QtWidgets.QGroupBox(Editor)
        self.cancelGroup.setObjectName("cancelGroup")
        self.gridLayout = QtWidgets.QGridLayout(self.cancelGroup)
        self.gridLayout.setObjectName("gridLayout")
        self.cancelSequenceLabel = QtWidgets.QLabel(self.cancelGroup)
        self.cancelSequenceLabel.setObjectName("cancelSequenceLabel")
        self.gridLayout.addWidget(self.cancelSequenceLabel, 0, 0, 1, 1)
        self.cancelEndingTimeLabel = QtWidgets.QLabel(self.cancelGroup)
        self.cancelEndingTimeLabel.setObjectName("cancelEndingTimeLabel")
        self.gridLayout.addWidget(self.cancelEndingTimeLabel, 0, 2, 1, 1)
        self.cancelBeginningTime = QtWidgets.QLineEdit(self.cancelGroup)
        self.cancelBeginningTime.setObjectName("cancelBeginningTime")
        self.gridLayout.addWidget(self.cancelBeginningTime, 2, 1, 1, 1)
        self.cancelSequence = QtWidgets.QComboBox(self.cancelGroup)
        self.cancelSequence.setEditable(True)
        self.cancelSequence.setObjectName("cancelSequence")
        self.gridLayout.addWidget(self.cancelSequence, 2, 0, 1, 1)
        self.cancelBeginningTimeLabel = QtWidgets.QLabel(self.cancelGroup)
        self.cancelBeginningTimeLabel.setObjectName("cancelBeginningTimeLabel")
        self.gridLayout.addWidget(self.cancelBeginningTimeLabel, 0, 1, 1, 1)
        self.cancelEndingTime = QtWidgets.QLineEdit(self.cancelGroup)
        self.cancelEndingTime.setObjectName("cancelEndingTime")
        self.gridLayout.addWidget(self.cancelEndingTime, 2, 2, 1, 1)
        self.verticalLayout.addWidget(self.cancelGroup)
        spacerItem = QtWidgets.QSpacerItem(20, 0, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem)
        self.endingTimeLabel.setBuddy(self.endingTime)
        self.beginningTimeLabel.setBuddy(self.beginningTime)
        self.sequenceLabel.setBuddy(self.sequence)
        self.cancelSequenceLabel.setBuddy(self.cancelSequence)
        self.cancelEndingTimeLabel.setBuddy(self.cancelEndingTime)
        self.cancelBeginningTimeLabel.setBuddy(self.cancelBeginningTime)

        self.retranslateUi(Editor)
        QtCore.QMetaObject.connectSlotsByName(Editor)
        Editor.setTabOrder(self.beginningTime, self.endingTime)
        Editor.setTabOrder(self.endingTime, self.sequence)
        Editor.setTabOrder(self.sequence, self.cancelSequence)
        Editor.setTabOrder(self.cancelSequence, self.cancelBeginningTime)
        Editor.setTabOrder(self.cancelBeginningTime, self.cancelEndingTime)

    def retranslateUi(self, Editor):
        _translate = QtCore.QCoreApplication.translate
        self.headingGroup.setTitle(_translate("Editor", "Heading"))
        self.endingTimeLabel.setText(_translate("Editor", "Ending"))
        self.beginningTimeLabel.setText(_translate("Editor", "Beginning"))
        self.sequenceLabel.setText(_translate("Editor", "Sequence"))
        self.cancelGroup.setTitle(_translate("Editor", "Cancel Information"))
        self.cancelSequenceLabel.setText(_translate("Editor", "Sequence"))
        self.cancelEndingTimeLabel.setText(_translate("Editor", "Ending"))
        self.cancelBeginningTimeLabel.setText(_translate("Editor", "Beginning"))
