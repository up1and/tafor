# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'D:\Work\tafor\tafor\components\ui\sigmet_head.ui'
#
# Created by: PyQt5 UI code generator 5.11.3
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Editor(object):
    def setupUi(self, Editor):
        Editor.setObjectName("Editor")
        Editor.resize(952, 70)
        Editor.setWindowTitle("Sigmet")
        self.verticalLayout = QtWidgets.QVBoxLayout(Editor)
        self.verticalLayout.setContentsMargins(-1, 0, -1, 0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.headGroup = QtWidgets.QGroupBox(Editor)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.headGroup.sizePolicy().hasHeightForWidth())
        self.headGroup.setSizePolicy(sizePolicy)
        self.headGroup.setObjectName("headGroup")
        self.gridLayout_2 = QtWidgets.QGridLayout(self.headGroup)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.description = QtWidgets.QComboBox(self.headGroup)
        self.description.setObjectName("description")
        self.gridLayout_2.addWidget(self.description, 1, 3, 1, 1)
        self.obsTime = QtWidgets.QLineEdit(self.headGroup)
        self.obsTime.setEnabled(False)
        self.obsTime.setObjectName("obsTime")
        self.gridLayout_2.addWidget(self.obsTime, 1, 7, 1, 1)
        self.beginningTime = QtWidgets.QLineEdit(self.headGroup)
        self.beginningTime.setObjectName("beginningTime")
        self.gridLayout_2.addWidget(self.beginningTime, 1, 0, 1, 1)
        self.sequence = QtWidgets.QLineEdit(self.headGroup)
        self.sequence.setObjectName("sequence")
        self.gridLayout_2.addWidget(self.sequence, 1, 2, 1, 1)
        self.obsTimeLabel = QtWidgets.QLabel(self.headGroup)
        self.obsTimeLabel.setEnabled(False)
        self.obsTimeLabel.setObjectName("obsTimeLabel")
        self.gridLayout_2.addWidget(self.obsTimeLabel, 0, 7, 1, 1)
        self.forecastLabel = QtWidgets.QLabel(self.headGroup)
        self.forecastLabel.setObjectName("forecastLabel")
        self.gridLayout_2.addWidget(self.forecastLabel, 0, 6, 1, 1)
        self.nameLabel = QtWidgets.QLabel(self.headGroup)
        self.nameLabel.setText("Name")
        self.nameLabel.setObjectName("nameLabel")
        self.gridLayout_2.addWidget(self.nameLabel, 0, 5, 1, 1)
        self.descriptionLabel = QtWidgets.QLabel(self.headGroup)
        self.descriptionLabel.setObjectName("descriptionLabel")
        self.gridLayout_2.addWidget(self.descriptionLabel, 0, 3, 1, 1)
        self.beginningTimeLabel = QtWidgets.QLabel(self.headGroup)
        self.beginningTimeLabel.setObjectName("beginningTimeLabel")
        self.gridLayout_2.addWidget(self.beginningTimeLabel, 0, 0, 1, 1)
        self.sequenceLabel = QtWidgets.QLabel(self.headGroup)
        self.sequenceLabel.setObjectName("sequenceLabel")
        self.gridLayout_2.addWidget(self.sequenceLabel, 0, 2, 1, 1)
        self.name = QtWidgets.QLineEdit(self.headGroup)
        self.name.setObjectName("name")
        self.gridLayout_2.addWidget(self.name, 1, 5, 1, 1)
        self.phenomenaLabel = QtWidgets.QLabel(self.headGroup)
        self.phenomenaLabel.setObjectName("phenomenaLabel")
        self.gridLayout_2.addWidget(self.phenomenaLabel, 0, 4, 1, 1)
        self.forecast = QtWidgets.QComboBox(self.headGroup)
        self.forecast.setObjectName("forecast")
        self.gridLayout_2.addWidget(self.forecast, 1, 6, 1, 1)
        self.phenomena = QtWidgets.QComboBox(self.headGroup)
        self.phenomena.setObjectName("phenomena")
        self.gridLayout_2.addWidget(self.phenomena, 1, 4, 1, 1)
        self.endingTime = QtWidgets.QLineEdit(self.headGroup)
        self.endingTime.setObjectName("endingTime")
        self.gridLayout_2.addWidget(self.endingTime, 1, 1, 1, 1)
        self.endingTimeLabel = QtWidgets.QLabel(self.headGroup)
        self.endingTimeLabel.setObjectName("endingTimeLabel")
        self.gridLayout_2.addWidget(self.endingTimeLabel, 0, 1, 1, 1)
        self.verticalLayout.addWidget(self.headGroup)
        self.obsTimeLabel.setBuddy(self.obsTime)
        self.forecastLabel.setBuddy(self.forecast)
        self.nameLabel.setBuddy(self.name)
        self.descriptionLabel.setBuddy(self.description)
        self.beginningTimeLabel.setBuddy(self.beginningTime)
        self.sequenceLabel.setBuddy(self.sequence)
        self.phenomenaLabel.setBuddy(self.phenomena)
        self.endingTimeLabel.setBuddy(self.endingTime)

        self.retranslateUi(Editor)
        QtCore.QMetaObject.connectSlotsByName(Editor)
        Editor.setTabOrder(self.beginningTime, self.endingTime)
        Editor.setTabOrder(self.endingTime, self.sequence)
        Editor.setTabOrder(self.sequence, self.description)
        Editor.setTabOrder(self.description, self.phenomena)
        Editor.setTabOrder(self.phenomena, self.name)
        Editor.setTabOrder(self.name, self.forecast)
        Editor.setTabOrder(self.forecast, self.obsTime)

    def retranslateUi(self, Editor):
        _translate = QtCore.QCoreApplication.translate
        self.headGroup.setTitle(_translate("Editor", "Head"))
        self.obsTimeLabel.setText(_translate("Editor", "OBS Time"))
        self.forecastLabel.setText(_translate("Editor", "Forecast"))
        self.descriptionLabel.setText(_translate("Editor", "Description"))
        self.beginningTimeLabel.setText(_translate("Editor", "Beginning"))
        self.sequenceLabel.setText(_translate("Editor", "Sequence"))
        self.phenomenaLabel.setText(_translate("Editor", "Phenomena"))
        self.endingTimeLabel.setText(_translate("Editor", "Ending"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    Editor = QtWidgets.QWidget()
    ui = Ui_Editor()
    ui.setupUi(Editor)
    Editor.show()
    sys.exit(app.exec_())

