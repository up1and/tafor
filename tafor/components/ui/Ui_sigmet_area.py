# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'D:\Work\tafor\tafor\components\ui\sigmet_area.ui'
#
# Created by: PyQt5 UI code generator 5.6
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Editor(object):
    def setupUi(self, Editor):
        Editor.setObjectName("Editor")
        Editor.resize(526, 117)
        Editor.setWindowTitle("Sigmet")
        self.layout = QtWidgets.QVBoxLayout(Editor)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setObjectName("layout")
        self.areaGroup = QtWidgets.QGroupBox(Editor)
        self.areaGroup.setObjectName("areaGroup")
        self.areaLayout = QtWidgets.QVBoxLayout(self.areaGroup)
        self.areaLayout.setContentsMargins(-1, -1, -1, 5)
        self.areaLayout.setObjectName("areaLayout")
        self.changeAreaWidget = QtWidgets.QWidget(self.areaGroup)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.changeAreaWidget.sizePolicy().hasHeightForWidth())
        self.changeAreaWidget.setSizePolicy(sizePolicy)
        self.changeAreaWidget.setMinimumSize(QtCore.QSize(0, 22))
        self.changeAreaWidget.setObjectName("changeAreaWidget")
        self.changeAreaLayout = QtWidgets.QHBoxLayout(self.changeAreaWidget)
        self.changeAreaLayout.setContentsMargins(0, 0, 0, 0)
        self.changeAreaLayout.setObjectName("changeAreaLayout")
        self.canvas = QtWidgets.QRadioButton(self.changeAreaWidget)
        self.canvas.setChecked(True)
        self.canvas.setObjectName("canvas")
        self.changeAreaLayout.addWidget(self.canvas)
        self.manual = QtWidgets.QRadioButton(self.changeAreaWidget)
        self.manual.setObjectName("manual")
        self.changeAreaLayout.addWidget(self.manual)
        self.entire = QtWidgets.QRadioButton(self.changeAreaWidget)
        self.entire.setObjectName("entire")
        self.changeAreaLayout.addWidget(self.entire)
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.changeAreaLayout.addItem(spacerItem)
        self.fcstButton = QtWidgets.QToolButton(self.changeAreaWidget)
        self.fcstButton.setText("")
        self.fcstButton.setIconSize(QtCore.QSize(16, 16))
        self.fcstButton.setCheckable(True)
        self.fcstButton.setAutoRaise(True)
        self.fcstButton.setObjectName("fcstButton")
        self.changeAreaLayout.addWidget(self.fcstButton)
        self.modeButton = QtWidgets.QToolButton(self.changeAreaWidget)
        self.modeButton.setText("")
        self.modeButton.setIconSize(QtCore.QSize(16, 16))
        self.modeButton.setAutoRaise(True)
        self.modeButton.setObjectName("modeButton")
        self.changeAreaLayout.addWidget(self.modeButton)
        self.areaLayout.addWidget(self.changeAreaWidget)
        self.textAreaWidget = QtWidgets.QWidget(self.areaGroup)
        self.textAreaWidget.setObjectName("textAreaWidget")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.textAreaWidget)
        self.verticalLayout.setContentsMargins(0, 5, 0, 5)
        self.verticalLayout.setObjectName("verticalLayout")
        self.textArea = QtWidgets.QLineEdit(self.textAreaWidget)
        self.textArea.setPlaceholderText("")
        self.textArea.setObjectName("textArea")
        self.verticalLayout.addWidget(self.textArea)
        self.areaLayout.addWidget(self.textAreaWidget)
        self.layout.addWidget(self.areaGroup)

        self.retranslateUi(Editor)
        QtCore.QMetaObject.connectSlotsByName(Editor)
        Editor.setTabOrder(self.canvas, self.manual)
        Editor.setTabOrder(self.manual, self.entire)
        Editor.setTabOrder(self.entire, self.modeButton)
        Editor.setTabOrder(self.modeButton, self.textArea)

    def retranslateUi(self, Editor):
        _translate = QtCore.QCoreApplication.translate
        self.areaGroup.setTitle(_translate("Editor", "Area"))
        self.canvas.setText(_translate("Editor", "Canvas"))
        self.manual.setText(_translate("Editor", "Manual"))
        self.entire.setText(_translate("Editor", "Entire"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    Editor = QtWidgets.QWidget()
    ui = Ui_Editor()
    ui.setupUi(Editor)
    Editor.show()
    sys.exit(app.exec_())

