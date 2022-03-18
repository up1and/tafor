# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'D:\Work\tafor\tafor\components\ui\sigmet.ui'
#
# Created by: PyQt5 UI code generator 5.13.2
#
# WARNING! All changes made in this file will be lost!


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Editor(object):
    def setupUi(self, Editor):
        Editor.setObjectName("Editor")
        Editor.resize(776, 95)
        Editor.setWindowTitle("Sigmet")
        self.layout = QtWidgets.QVBoxLayout(Editor)
        self.layout.setSizeConstraint(QtWidgets.QLayout.SetFixedSize)
        self.layout.setObjectName("layout")
        self.typeLayout = QtWidgets.QHBoxLayout()
        self.typeLayout.setObjectName("typeLayout")
        self.typeGroup = QtWidgets.QGroupBox(Editor)
        self.typeGroup.setTitle("")
        self.typeGroup.setObjectName("typeGroup")
        self.typeGroupLayout = QtWidgets.QHBoxLayout(self.typeGroup)
        self.typeGroupLayout.setObjectName("typeGroupLayout")
        self.significantWeather = QtWidgets.QRadioButton(self.typeGroup)
        self.significantWeather.setChecked(True)
        self.significantWeather.setObjectName("significantWeather")
        self.typeGroupLayout.addWidget(self.significantWeather)
        self.tropicalCyclone = QtWidgets.QRadioButton(self.typeGroup)
        self.tropicalCyclone.setObjectName("tropicalCyclone")
        self.typeGroupLayout.addWidget(self.tropicalCyclone)
        self.volcanicAsh = QtWidgets.QRadioButton(self.typeGroup)
        self.volcanicAsh.setObjectName("volcanicAsh")
        self.typeGroupLayout.addWidget(self.volcanicAsh)
        self.airmansWeather = QtWidgets.QRadioButton(self.typeGroup)
        self.airmansWeather.setObjectName("airmansWeather")
        self.typeGroupLayout.addWidget(self.airmansWeather)
        self.typeLayout.addWidget(self.typeGroup)
        spacerItem = QtWidgets.QSpacerItem(0, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.typeLayout.addItem(spacerItem)
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
        self.typeLayout.addWidget(self.sortGroup)
        self.layout.addLayout(self.typeLayout)
        self.mainLayout = QtWidgets.QHBoxLayout()
        self.mainLayout.setObjectName("mainLayout")
        self.leftLayout = QtWidgets.QVBoxLayout()
        self.leftLayout.setObjectName("leftLayout")
        self.contentLayout = QtWidgets.QHBoxLayout()
        self.contentLayout.setContentsMargins(-1, -1, -1, 10)
        self.contentLayout.setObjectName("contentLayout")
        self.leftLayout.addLayout(self.contentLayout)
        self.location = QtWidgets.QLabel(Editor)
        self.location.setMinimumSize(QtCore.QSize(180, 0))
        self.location.setMaximumSize(QtCore.QSize(270, 16777215))
        self.location.setText("Location")
        self.location.setWordWrap(True)
        self.location.setTextInteractionFlags(QtCore.Qt.NoTextInteraction)
        self.location.setObjectName("location")
        self.leftLayout.addWidget(self.location, 0, QtCore.Qt.AlignLeft|QtCore.Qt.AlignTop)
        self.mainLayout.addLayout(self.leftLayout)
        self.layout.addLayout(self.mainLayout)

        self.retranslateUi(Editor)
        QtCore.QMetaObject.connectSlotsByName(Editor)

    def retranslateUi(self, Editor):
        _translate = QtCore.QCoreApplication.translate
        self.significantWeather.setText(_translate("Editor", "Significant Weather"))
        self.tropicalCyclone.setText(_translate("Editor", "Tropical Cyclone"))
        self.volcanicAsh.setText(_translate("Editor", "Volcanic Ash"))
        self.airmansWeather.setText(_translate("Editor", "Airman\'s Weather"))
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