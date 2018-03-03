# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'D:\Work\tafor\tafor\components\ui\sigmet_type.ui'
#
# Created by: PyQt5 UI code generator 5.6
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Editor(object):
    def setupUi(self, Editor):
        Editor.setObjectName("Editor")
        Editor.resize(654, 54)
        Editor.setWindowTitle("Sigmet")
        self.horizontalLayout = QtWidgets.QHBoxLayout(Editor)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.groupBox = QtWidgets.QGroupBox(Editor)
        self.groupBox.setTitle("")
        self.groupBox.setObjectName("groupBox")
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout(self.groupBox)
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.significantWeather = QtWidgets.QRadioButton(self.groupBox)
        self.significantWeather.setChecked(True)
        self.significantWeather.setObjectName("significantWeather")
        self.horizontalLayout_3.addWidget(self.significantWeather)
        self.tropicalCyclone = QtWidgets.QRadioButton(self.groupBox)
        self.tropicalCyclone.setObjectName("tropicalCyclone")
        self.horizontalLayout_3.addWidget(self.tropicalCyclone)
        self.volcanicAsh = QtWidgets.QRadioButton(self.groupBox)
        self.volcanicAsh.setObjectName("volcanicAsh")
        self.horizontalLayout_3.addWidget(self.volcanicAsh)
        self.horizontalLayout.addWidget(self.groupBox)
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.sortGroup = QtWidgets.QGroupBox(Editor)
        self.sortGroup.setTitle("")
        self.sortGroup.setObjectName("sortGroup")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(self.sortGroup)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.template = QtWidgets.QRadioButton(self.sortGroup)
        self.template.setChecked(True)
        self.template.setObjectName("template")
        self.horizontalLayout_2.addWidget(self.template)
        self.custom = QtWidgets.QRadioButton(self.sortGroup)
        self.custom.setObjectName("custom")
        self.horizontalLayout_2.addWidget(self.custom)
        self.cancel = QtWidgets.QRadioButton(self.sortGroup)
        self.cancel.setObjectName("cancel")
        self.horizontalLayout_2.addWidget(self.cancel)
        self.horizontalLayout.addWidget(self.sortGroup)

        self.retranslateUi(Editor)
        QtCore.QMetaObject.connectSlotsByName(Editor)

    def retranslateUi(self, Editor):
        _translate = QtCore.QCoreApplication.translate
        self.significantWeather.setText(_translate("Editor", "Significant Weather"))
        self.tropicalCyclone.setText(_translate("Editor", "Tropical Cyclone"))
        self.volcanicAsh.setText(_translate("Editor", "Volcanic Ash"))
        self.template.setText(_translate("Editor", "Template"))
        self.custom.setText(_translate("Editor", "Custom"))
        self.cancel.setText(_translate("Editor", "Cancel"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    Editor = QtWidgets.QWidget()
    ui = Ui_Editor()
    ui.setupUi(Editor)
    Editor.show()
    sys.exit(app.exec_())

