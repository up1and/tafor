# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'D:\Work\tafor\tafor\components\ui\sigmet_ash.ui'
#
# Created by: PyQt5 UI code generator 5.11.3
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Editor(object):
    def setupUi(self, Editor):
        Editor.setObjectName("Editor")
        Editor.resize(819, 146)
        Editor.setWindowTitle("Sigmet")
        self.verticalLayout = QtWidgets.QVBoxLayout(Editor)
        self.verticalLayout.setContentsMargins(-1, 0, -1, 0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.descriptionGroup = QtWidgets.QGroupBox(Editor)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.descriptionGroup.sizePolicy().hasHeightForWidth())
        self.descriptionGroup.setSizePolicy(sizePolicy)
        self.descriptionGroup.setObjectName("descriptionGroup")
        self.descriptionLayout = QtWidgets.QGridLayout(self.descriptionGroup)
        self.descriptionLayout.setObjectName("descriptionLayout")
        self.level = QtWidgets.QComboBox(self.descriptionGroup)
        self.level.setObjectName("level")
        self.level.addItem("")
        self.level.setItemText(0, "")
        self.level.addItem("")
        self.level.setItemText(1, "SFC")
        self.descriptionLayout.addWidget(self.level, 1, 2, 1, 1)
        self.forecastTime = QtWidgets.QLineEdit(self.descriptionGroup)
        self.forecastTime.setEnabled(False)
        self.forecastTime.setObjectName("forecastTime")
        self.descriptionLayout.addWidget(self.forecastTime, 1, 8, 1, 1)
        self.top = QtWidgets.QLineEdit(self.descriptionGroup)
        self.top.setObjectName("top")
        self.descriptionLayout.addWidget(self.top, 1, 4, 1, 1)
        self.movement = QtWidgets.QComboBox(self.descriptionGroup)
        self.movement.setObjectName("movement")
        self.movement.addItem("")
        self.movement.setItemText(0, "N")
        self.movement.addItem("")
        self.movement.setItemText(1, "NNE")
        self.movement.addItem("")
        self.movement.setItemText(2, "NE")
        self.movement.addItem("")
        self.movement.setItemText(3, "ENE")
        self.movement.addItem("")
        self.movement.setItemText(4, "E")
        self.movement.addItem("")
        self.movement.setItemText(5, "ESE")
        self.movement.addItem("")
        self.movement.setItemText(6, "SE")
        self.movement.addItem("")
        self.movement.setItemText(7, "SSE")
        self.movement.addItem("")
        self.movement.setItemText(8, "S")
        self.movement.addItem("")
        self.movement.setItemText(9, "SSW")
        self.movement.addItem("")
        self.movement.setItemText(10, "SW")
        self.movement.addItem("")
        self.movement.setItemText(11, "WSW")
        self.movement.addItem("")
        self.movement.setItemText(12, "W")
        self.movement.addItem("")
        self.movement.setItemText(13, "WNW")
        self.movement.addItem("")
        self.movement.setItemText(14, "NW")
        self.movement.addItem("")
        self.movement.setItemText(15, "NNW")
        self.movement.addItem("")
        self.movement.setItemText(16, "STNR")
        self.descriptionLayout.addWidget(self.movement, 1, 5, 1, 1)
        self.intensityChange = QtWidgets.QComboBox(self.descriptionGroup)
        self.intensityChange.setObjectName("intensityChange")
        self.intensityChange.addItem("")
        self.intensityChange.setItemText(0, "NC")
        self.intensityChange.addItem("")
        self.intensityChange.setItemText(1, "INTSF")
        self.intensityChange.addItem("")
        self.intensityChange.setItemText(2, "WKN")
        self.descriptionLayout.addWidget(self.intensityChange, 1, 7, 1, 1)
        self.forecastTimeLabel = QtWidgets.QLabel(self.descriptionGroup)
        self.forecastTimeLabel.setEnabled(False)
        self.forecastTimeLabel.setObjectName("forecastTimeLabel")
        self.descriptionLayout.addWidget(self.forecastTimeLabel, 0, 8, 1, 1)
        self.speed = QtWidgets.QLineEdit(self.descriptionGroup)
        self.speed.setObjectName("speed")
        self.descriptionLayout.addWidget(self.speed, 1, 6, 1, 1)
        self.intensityChangeLabel = QtWidgets.QLabel(self.descriptionGroup)
        self.intensityChangeLabel.setObjectName("intensityChangeLabel")
        self.descriptionLayout.addWidget(self.intensityChangeLabel, 0, 7, 1, 1)
        self.speedLabel = QtWidgets.QLabel(self.descriptionGroup)
        self.speedLabel.setObjectName("speedLabel")
        self.descriptionLayout.addWidget(self.speedLabel, 0, 6, 1, 1)
        self.baseLabel = QtWidgets.QLabel(self.descriptionGroup)
        self.baseLabel.setObjectName("baseLabel")
        self.descriptionLayout.addWidget(self.baseLabel, 0, 3, 1, 1)
        self.levelLabel = QtWidgets.QLabel(self.descriptionGroup)
        self.levelLabel.setObjectName("levelLabel")
        self.descriptionLayout.addWidget(self.levelLabel, 0, 2, 1, 1)
        self.movementLabel = QtWidgets.QLabel(self.descriptionGroup)
        self.movementLabel.setObjectName("movementLabel")
        self.descriptionLayout.addWidget(self.movementLabel, 0, 5, 1, 1)
        self.topLabel = QtWidgets.QLabel(self.descriptionGroup)
        self.topLabel.setObjectName("topLabel")
        self.descriptionLayout.addWidget(self.topLabel, 0, 4, 1, 1)
        self.base = QtWidgets.QLineEdit(self.descriptionGroup)
        self.base.setObjectName("base")
        self.descriptionLayout.addWidget(self.base, 1, 3, 1, 1)
        self.verticalLayout.addWidget(self.descriptionGroup)
        self.postionGroup = QtWidgets.QGroupBox(Editor)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.postionGroup.sizePolicy().hasHeightForWidth())
        self.postionGroup.setSizePolicy(sizePolicy)
        self.postionGroup.setObjectName("postionGroup")
        self.gridLayout_3 = QtWidgets.QGridLayout(self.postionGroup)
        self.gridLayout_3.setObjectName("gridLayout_3")
        self.currentLongitude = QtWidgets.QLineEdit(self.postionGroup)
        self.currentLongitude.setObjectName("currentLongitude")
        self.gridLayout_3.addWidget(self.currentLongitude, 1, 1, 1, 1)
        self.currentLongitudeLabel = QtWidgets.QLabel(self.postionGroup)
        self.currentLongitudeLabel.setObjectName("currentLongitudeLabel")
        self.gridLayout_3.addWidget(self.currentLongitudeLabel, 0, 1, 1, 1)
        self.currentLatitude = QtWidgets.QLineEdit(self.postionGroup)
        self.currentLatitude.setObjectName("currentLatitude")
        self.gridLayout_3.addWidget(self.currentLatitude, 1, 0, 1, 1)
        self.currentLatitudeLabel = QtWidgets.QLabel(self.postionGroup)
        self.currentLatitudeLabel.setObjectName("currentLatitudeLabel")
        self.gridLayout_3.addWidget(self.currentLatitudeLabel, 0, 0, 1, 1)
        self.verticalLayout.addWidget(self.postionGroup)
        self.intensityChangeLabel.setBuddy(self.intensityChange)
        self.speedLabel.setBuddy(self.speed)
        self.baseLabel.setBuddy(self.base)
        self.levelLabel.setBuddy(self.level)
        self.movementLabel.setBuddy(self.movement)
        self.topLabel.setBuddy(self.top)

        self.retranslateUi(Editor)
        QtCore.QMetaObject.connectSlotsByName(Editor)
        Editor.setTabOrder(self.level, self.base)
        Editor.setTabOrder(self.base, self.top)
        Editor.setTabOrder(self.top, self.movement)
        Editor.setTabOrder(self.movement, self.speed)
        Editor.setTabOrder(self.speed, self.intensityChange)
        Editor.setTabOrder(self.intensityChange, self.forecastTime)
        Editor.setTabOrder(self.forecastTime, self.currentLatitude)
        Editor.setTabOrder(self.currentLatitude, self.currentLongitude)

    def retranslateUi(self, Editor):
        _translate = QtCore.QCoreApplication.translate
        self.descriptionGroup.setTitle(_translate("Editor", "Description"))
        self.forecastTimeLabel.setText(_translate("Editor", "Forecast Time"))
        self.intensityChangeLabel.setText(_translate("Editor", "Intensity"))
        self.speedLabel.setText(_translate("Editor", "Speed"))
        self.baseLabel.setText(_translate("Editor", "Base"))
        self.levelLabel.setText(_translate("Editor", "Fight Level"))
        self.movementLabel.setText(_translate("Editor", "Movement"))
        self.topLabel.setText(_translate("Editor", "Top"))
        self.postionGroup.setTitle(_translate("Editor", "Postion"))
        self.currentLongitudeLabel.setText(_translate("Editor", "Longitude"))
        self.currentLatitudeLabel.setText(_translate("Editor", "Latitude"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    Editor = QtWidgets.QWidget()
    ui = Ui_Editor()
    ui.setupUi(Editor)
    Editor.show()
    sys.exit(app.exec_())

