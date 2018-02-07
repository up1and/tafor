# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'C:\Users\Upland\Work\tafor\tafor\components\ui\sigmet_type.ui'
#
# Created by: PyQt5 UI code generator 5.6
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Editor(object):
    def setupUi(self, Editor):
        Editor.setObjectName("Editor")
        Editor.resize(831, 201)
        Editor.setWindowTitle("Sigmet")
        self.verticalLayout = QtWidgets.QVBoxLayout(Editor)
        self.verticalLayout.setObjectName("verticalLayout")
        self.typeGroup = QtWidgets.QGroupBox(Editor)
        self.typeGroup.setObjectName("typeGroup")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(self.typeGroup)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.normal = QtWidgets.QRadioButton(self.typeGroup)
        self.normal.setObjectName("normal")
        self.horizontalLayout_2.addWidget(self.normal)
        self.tropicalCyclone = QtWidgets.QRadioButton(self.typeGroup)
        self.tropicalCyclone.setObjectName("tropicalCyclone")
        self.horizontalLayout_2.addWidget(self.tropicalCyclone)
        self.volcanicAsh = QtWidgets.QRadioButton(self.typeGroup)
        self.volcanicAsh.setObjectName("volcanicAsh")
        self.horizontalLayout_2.addWidget(self.volcanicAsh)
        self.cancel = QtWidgets.QRadioButton(self.typeGroup)
        self.cancel.setObjectName("cancel")
        self.horizontalLayout_2.addWidget(self.cancel)
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_2.addItem(spacerItem)
        self.verticalLayout.addWidget(self.typeGroup)
        self.headGroup = QtWidgets.QGroupBox(Editor)
        self.headGroup.setObjectName("headGroup")
        self.gridLayout_2 = QtWidgets.QGridLayout(self.headGroup)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.phenomenaLabel = QtWidgets.QLabel(self.headGroup)
        self.phenomenaLabel.setObjectName("phenomenaLabel")
        self.gridLayout_2.addWidget(self.phenomenaLabel, 0, 3, 1, 1)
        self.validLabel = QtWidgets.QLabel(self.headGroup)
        self.validLabel.setObjectName("validLabel")
        self.gridLayout_2.addWidget(self.validLabel, 0, 0, 1, 1)
        self.sequence = QtWidgets.QLineEdit(self.headGroup)
        self.sequence.setObjectName("sequence")
        self.gridLayout_2.addWidget(self.sequence, 1, 1, 1, 1)
        self.phenomena = QtWidgets.QComboBox(self.headGroup)
        self.phenomena.setObjectName("phenomena")
        self.gridLayout_2.addWidget(self.phenomena, 1, 3, 1, 1)
        self.valid = QtWidgets.QLineEdit(self.headGroup)
        self.valid.setObjectName("valid")
        self.gridLayout_2.addWidget(self.valid, 1, 0, 1, 1)
        self.forecast = QtWidgets.QComboBox(self.headGroup)
        self.forecast.setObjectName("forecast")
        self.forecast.addItem("")
        self.forecast.addItem("")
        self.forecast.addItem("")
        self.gridLayout_2.addWidget(self.forecast, 1, 4, 1, 1)
        self.forecastLabel = QtWidgets.QLabel(self.headGroup)
        self.forecastLabel.setObjectName("forecastLabel")
        self.gridLayout_2.addWidget(self.forecastLabel, 0, 4, 1, 1)
        self.sequenceLabel = QtWidgets.QLabel(self.headGroup)
        self.sequenceLabel.setObjectName("sequenceLabel")
        self.gridLayout_2.addWidget(self.sequenceLabel, 0, 1, 1, 1)
        self.description = QtWidgets.QComboBox(self.headGroup)
        self.description.setObjectName("description")
        self.gridLayout_2.addWidget(self.description, 1, 2, 1, 1)
        self.descriptionLabel = QtWidgets.QLabel(self.headGroup)
        self.descriptionLabel.setObjectName("descriptionLabel")
        self.gridLayout_2.addWidget(self.descriptionLabel, 0, 2, 1, 1)
        self.verticalLayout.addWidget(self.headGroup)

        self.retranslateUi(Editor)
        QtCore.QMetaObject.connectSlotsByName(Editor)

    def retranslateUi(self, Editor):
        _translate = QtCore.QCoreApplication.translate
        self.typeGroup.setTitle(_translate("Editor", "Type"))
        self.normal.setText(_translate("Editor", "Normal"))
        self.tropicalCyclone.setText(_translate("Editor", "Tropical Cyclone"))
        self.volcanicAsh.setText(_translate("Editor", "Volcanic Ash"))
        self.cancel.setText(_translate("Editor", "Cancel"))
        self.headGroup.setTitle(_translate("Editor", "Head"))
        self.phenomenaLabel.setText(_translate("Editor", "Phenomena"))
        self.validLabel.setText(_translate("Editor", "Valid"))
        self.forecast.setItemText(0, _translate("Editor", "FCST"))
        self.forecast.setItemText(1, _translate("Editor", "OBS"))
        self.forecast.setItemText(2, _translate("Editor", "OBS AND FCST"))
        self.forecastLabel.setText(_translate("Editor", "Forecast"))
        self.sequenceLabel.setText(_translate("Editor", "Sequence"))
        self.descriptionLabel.setText(_translate("Editor", "Phenomena Description"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    Editor = QtWidgets.QWidget()
    ui = Ui_Editor()
    ui.setupUi(Editor)
    Editor.show()
    sys.exit(app.exec_())

