# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'D:\Work\tafor\tafor\components\ui\sigmet_phenomena.ui'
#
# Created by: PyQt5 UI code generator 5.6
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Editor(object):
    def setupUi(self, Editor):
        Editor.setObjectName("Editor")
        Editor.resize(550, 88)
        Editor.setWindowTitle("Sigmet")
        self.horizontalLayout = QtWidgets.QHBoxLayout(Editor)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.headGroup = QtWidgets.QGroupBox(Editor)
        self.headGroup.setObjectName("headGroup")
        self.gridLayout_2 = QtWidgets.QGridLayout(self.headGroup)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.sequenceLabel = QtWidgets.QLabel(self.headGroup)
        self.sequenceLabel.setObjectName("sequenceLabel")
        self.gridLayout_2.addWidget(self.sequenceLabel, 0, 1, 1, 1)
        self.sequence = QtWidgets.QLineEdit(self.headGroup)
        self.sequence.setObjectName("sequence")
        self.gridLayout_2.addWidget(self.sequence, 1, 1, 1, 1)
        self.valid = QtWidgets.QLineEdit(self.headGroup)
        self.valid.setObjectName("valid")
        self.gridLayout_2.addWidget(self.valid, 1, 0, 1, 1)
        self.validLabel = QtWidgets.QLabel(self.headGroup)
        self.validLabel.setObjectName("validLabel")
        self.gridLayout_2.addWidget(self.validLabel, 0, 0, 1, 1)
        self.obsTime = QtWidgets.QLineEdit(self.headGroup)
        self.obsTime.setEnabled(False)
        self.obsTime.setObjectName("obsTime")
        self.gridLayout_2.addWidget(self.obsTime, 1, 6, 1, 1)
        self.obsTimeLabel = QtWidgets.QLabel(self.headGroup)
        self.obsTimeLabel.setEnabled(False)
        self.obsTimeLabel.setObjectName("obsTimeLabel")
        self.gridLayout_2.addWidget(self.obsTimeLabel, 0, 6, 1, 1)
        self.forecast = QtWidgets.QComboBox(self.headGroup)
        self.forecast.setObjectName("forecast")
        self.forecast.addItem("")
        self.forecast.addItem("")
        self.gridLayout_2.addWidget(self.forecast, 1, 5, 1, 1)
        self.forecastLabel = QtWidgets.QLabel(self.headGroup)
        self.forecastLabel.setObjectName("forecastLabel")
        self.gridLayout_2.addWidget(self.forecastLabel, 0, 5, 1, 1)
        self.typhoonName = QtWidgets.QLineEdit(self.headGroup)
        self.typhoonName.setObjectName("typhoonName")
        self.gridLayout_2.addWidget(self.typhoonName, 1, 4, 1, 1)
        self.typhoonNameLabel = QtWidgets.QLabel(self.headGroup)
        self.typhoonNameLabel.setObjectName("typhoonNameLabel")
        self.gridLayout_2.addWidget(self.typhoonNameLabel, 0, 4, 1, 1)
        self.phenomena = QtWidgets.QComboBox(self.headGroup)
        self.phenomena.setObjectName("phenomena")
        self.gridLayout_2.addWidget(self.phenomena, 1, 3, 1, 1)
        self.phenomenaLabel = QtWidgets.QLabel(self.headGroup)
        self.phenomenaLabel.setObjectName("phenomenaLabel")
        self.gridLayout_2.addWidget(self.phenomenaLabel, 0, 3, 1, 1)
        self.descriptionLabel = QtWidgets.QLabel(self.headGroup)
        self.descriptionLabel.setObjectName("descriptionLabel")
        self.gridLayout_2.addWidget(self.descriptionLabel, 0, 2, 1, 1)
        self.description = QtWidgets.QComboBox(self.headGroup)
        self.description.setObjectName("description")
        self.gridLayout_2.addWidget(self.description, 1, 2, 1, 1)
        self.horizontalLayout.addWidget(self.headGroup)

        self.retranslateUi(Editor)
        QtCore.QMetaObject.connectSlotsByName(Editor)

    def retranslateUi(self, Editor):
        _translate = QtCore.QCoreApplication.translate
        self.headGroup.setTitle(_translate("Editor", "Head"))
        self.sequenceLabel.setText(_translate("Editor", "Sequence"))
        self.validLabel.setText(_translate("Editor", "Valid"))
        self.obsTimeLabel.setText(_translate("Editor", "OBS Time"))
        self.forecast.setItemText(0, _translate("Editor", "FCST"))
        self.forecast.setItemText(1, _translate("Editor", "OBS"))
        self.forecastLabel.setText(_translate("Editor", "Forecast"))
        self.typhoonNameLabel.setText(_translate("Editor", "Typhoon Name"))
        self.phenomenaLabel.setText(_translate("Editor", "Phenomena"))
        self.descriptionLabel.setText(_translate("Editor", "Phenomena Description"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    Editor = QtWidgets.QWidget()
    ui = Ui_Editor()
    ui.setupUi(Editor)
    Editor.show()
    sys.exit(app.exec_())

