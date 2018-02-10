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
        Editor.resize(500, 70)
        Editor.setWindowTitle("Sigmet")
        self.horizontalLayout = QtWidgets.QHBoxLayout(Editor)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.typeGroup = QtWidgets.QGroupBox(Editor)
        self.typeGroup.setObjectName("typeGroup")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(self.typeGroup)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.general = QtWidgets.QRadioButton(self.typeGroup)
        self.general.setChecked(True)
        self.general.setObjectName("general")
        self.horizontalLayout_2.addWidget(self.general)
        self.tropicalCyclone = QtWidgets.QRadioButton(self.typeGroup)
        self.tropicalCyclone.setObjectName("tropicalCyclone")
        self.horizontalLayout_2.addWidget(self.tropicalCyclone)
        self.volcanicAsh = QtWidgets.QRadioButton(self.typeGroup)
        self.volcanicAsh.setObjectName("volcanicAsh")
        self.horizontalLayout_2.addWidget(self.volcanicAsh)
        self.custom = QtWidgets.QRadioButton(self.typeGroup)
        self.custom.setObjectName("custom")
        self.horizontalLayout_2.addWidget(self.custom)
        self.cancel = QtWidgets.QRadioButton(self.typeGroup)
        self.cancel.setObjectName("cancel")
        self.horizontalLayout_2.addWidget(self.cancel)
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_2.addItem(spacerItem)
        self.horizontalLayout.addWidget(self.typeGroup)

        self.retranslateUi(Editor)
        QtCore.QMetaObject.connectSlotsByName(Editor)

    def retranslateUi(self, Editor):
        _translate = QtCore.QCoreApplication.translate
        self.typeGroup.setTitle(_translate("Editor", "Type"))
        self.general.setText(_translate("Editor", "General"))
        self.tropicalCyclone.setText(_translate("Editor", "Tropical Cyclone"))
        self.volcanicAsh.setText(_translate("Editor", "Volcanic Ash"))
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

