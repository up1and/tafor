# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'D:\Work\tafor\tafor\components\ui\sigmet_general.ui'
#
# Created by: PyQt5 UI code generator 5.13.2
#
# WARNING! All changes made in this file will be lost!


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Editor(object):
    def setupUi(self, Editor):
        Editor.setObjectName("Editor")
        Editor.resize(312, 334)
        Editor.setWindowTitle("Sigmet")
        self.gridLayout = QtWidgets.QGridLayout(Editor)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.gridLayout.setObjectName("gridLayout")
        self.descriptionGroup = QtWidgets.QGroupBox(Editor)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.descriptionGroup.sizePolicy().hasHeightForWidth())
        self.descriptionGroup.setSizePolicy(sizePolicy)
        self.descriptionGroup.setObjectName("descriptionGroup")
        self.descriptionLayout = QtWidgets.QGridLayout(self.descriptionGroup)
        self.descriptionLayout.setObjectName("descriptionLayout")
        self.base = QtWidgets.QLineEdit(self.descriptionGroup)
        self.base.setObjectName("base")
        self.descriptionLayout.addWidget(self.base, 3, 2, 1, 1)
        self.baseLabel = QtWidgets.QLabel(self.descriptionGroup)
        self.baseLabel.setObjectName("baseLabel")
        self.descriptionLayout.addWidget(self.baseLabel, 2, 2, 1, 1)
        self.speedLabel = QtWidgets.QLabel(self.descriptionGroup)
        self.speedLabel.setObjectName("speedLabel")
        self.descriptionLayout.addWidget(self.speedLabel, 8, 2, 1, 1)
        self.level = QtWidgets.QComboBox(self.descriptionGroup)
        self.level.setObjectName("level")
        self.descriptionLayout.addWidget(self.level, 1, 2, 1, 1)
        self.intensityChangeLabel = QtWidgets.QLabel(self.descriptionGroup)
        self.intensityChangeLabel.setObjectName("intensityChangeLabel")
        self.descriptionLayout.addWidget(self.intensityChangeLabel, 10, 2, 1, 1)
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
        self.descriptionLayout.addWidget(self.movement, 7, 2, 1, 1)
        self.topLabel = QtWidgets.QLabel(self.descriptionGroup)
        self.topLabel.setObjectName("topLabel")
        self.descriptionLayout.addWidget(self.topLabel, 4, 2, 1, 1)
        self.forecastTime = QtWidgets.QLineEdit(self.descriptionGroup)
        self.forecastTime.setEnabled(False)
        self.forecastTime.setObjectName("forecastTime")
        self.descriptionLayout.addWidget(self.forecastTime, 13, 2, 1, 1)
        self.intensityChange = QtWidgets.QComboBox(self.descriptionGroup)
        self.intensityChange.setObjectName("intensityChange")
        self.intensityChange.addItem("")
        self.intensityChange.setItemText(0, "NC")
        self.intensityChange.addItem("")
        self.intensityChange.setItemText(1, "INTSF")
        self.intensityChange.addItem("")
        self.intensityChange.setItemText(2, "WKN")
        self.descriptionLayout.addWidget(self.intensityChange, 11, 2, 1, 1)
        self.forecastTimeLabel = QtWidgets.QLabel(self.descriptionGroup)
        self.forecastTimeLabel.setEnabled(False)
        self.forecastTimeLabel.setObjectName("forecastTimeLabel")
        self.descriptionLayout.addWidget(self.forecastTimeLabel, 12, 2, 1, 1)
        self.movementLabel = QtWidgets.QLabel(self.descriptionGroup)
        self.movementLabel.setObjectName("movementLabel")
        self.descriptionLayout.addWidget(self.movementLabel, 6, 2, 1, 1)
        self.speed = QtWidgets.QLineEdit(self.descriptionGroup)
        self.speed.setObjectName("speed")
        self.descriptionLayout.addWidget(self.speed, 9, 2, 1, 1)
        self.top = QtWidgets.QLineEdit(self.descriptionGroup)
        self.top.setObjectName("top")
        self.descriptionLayout.addWidget(self.top, 5, 2, 1, 1)
        self.levelLabel = QtWidgets.QLabel(self.descriptionGroup)
        self.levelLabel.setObjectName("levelLabel")
        self.descriptionLayout.addWidget(self.levelLabel, 0, 2, 1, 1)
        self.gridLayout.addWidget(self.descriptionGroup, 0, 1, 1, 1, QtCore.Qt.AlignLeft|QtCore.Qt.AlignTop)
        self.headGroup = QtWidgets.QGroupBox(Editor)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.headGroup.sizePolicy().hasHeightForWidth())
        self.headGroup.setSizePolicy(sizePolicy)
        self.headGroup.setObjectName("headGroup")
        self.gridLayout_2 = QtWidgets.QGridLayout(self.headGroup)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.beginningTimeLabel = QtWidgets.QLabel(self.headGroup)
        self.beginningTimeLabel.setObjectName("beginningTimeLabel")
        self.gridLayout_2.addWidget(self.beginningTimeLabel, 0, 0, 1, 1)
        self.observationTimeLabel = QtWidgets.QLabel(self.headGroup)
        self.observationTimeLabel.setObjectName("observationTimeLabel")
        self.gridLayout_2.addWidget(self.observationTimeLabel, 12, 0, 1, 1)
        self.endingTimeLabel = QtWidgets.QLabel(self.headGroup)
        self.endingTimeLabel.setObjectName("endingTimeLabel")
        self.gridLayout_2.addWidget(self.endingTimeLabel, 2, 0, 1, 1)
        self.observationTime = QtWidgets.QLineEdit(self.headGroup)
        self.observationTime.setObjectName("observationTime")
        self.gridLayout_2.addWidget(self.observationTime, 13, 0, 1, 1)
        self.observationLabel = QtWidgets.QLabel(self.headGroup)
        self.observationLabel.setObjectName("observationLabel")
        self.gridLayout_2.addWidget(self.observationLabel, 10, 0, 1, 1)
        self.observation = QtWidgets.QComboBox(self.headGroup)
        self.observation.setObjectName("observation")
        self.gridLayout_2.addWidget(self.observation, 11, 0, 1, 1)
        self.descriptionLabel = QtWidgets.QLabel(self.headGroup)
        self.descriptionLabel.setObjectName("descriptionLabel")
        self.gridLayout_2.addWidget(self.descriptionLabel, 6, 0, 1, 1)
        self.sequence = QtWidgets.QLineEdit(self.headGroup)
        self.sequence.setObjectName("sequence")
        self.gridLayout_2.addWidget(self.sequence, 5, 0, 1, 1)
        self.phenomenaLabel = QtWidgets.QLabel(self.headGroup)
        self.phenomenaLabel.setObjectName("phenomenaLabel")
        self.gridLayout_2.addWidget(self.phenomenaLabel, 8, 0, 1, 1)
        self.sequenceLabel = QtWidgets.QLabel(self.headGroup)
        self.sequenceLabel.setObjectName("sequenceLabel")
        self.gridLayout_2.addWidget(self.sequenceLabel, 4, 0, 1, 1)
        self.description = QtWidgets.QComboBox(self.headGroup)
        self.description.setObjectName("description")
        self.gridLayout_2.addWidget(self.description, 7, 0, 1, 1)
        self.endingTime = QtWidgets.QLineEdit(self.headGroup)
        self.endingTime.setObjectName("endingTime")
        self.gridLayout_2.addWidget(self.endingTime, 3, 0, 1, 1)
        self.phenomena = QtWidgets.QComboBox(self.headGroup)
        self.phenomena.setObjectName("phenomena")
        self.gridLayout_2.addWidget(self.phenomena, 9, 0, 1, 1)
        self.beginningTime = QtWidgets.QLineEdit(self.headGroup)
        self.beginningTime.setObjectName("beginningTime")
        self.gridLayout_2.addWidget(self.beginningTime, 1, 0, 1, 1)
        self.gridLayout.addWidget(self.headGroup, 0, 0, 1, 1, QtCore.Qt.AlignLeft|QtCore.Qt.AlignTop)
        self.baseLabel.setBuddy(self.base)
        self.speedLabel.setBuddy(self.speed)
        self.intensityChangeLabel.setBuddy(self.intensityChange)
        self.topLabel.setBuddy(self.top)
        self.forecastTimeLabel.setBuddy(self.forecastTime)
        self.movementLabel.setBuddy(self.movement)
        self.levelLabel.setBuddy(self.level)
        self.beginningTimeLabel.setBuddy(self.beginningTime)
        self.observationTimeLabel.setBuddy(self.observationTime)
        self.endingTimeLabel.setBuddy(self.endingTime)
        self.observationLabel.setBuddy(self.observation)
        self.descriptionLabel.setBuddy(self.description)
        self.phenomenaLabel.setBuddy(self.phenomena)
        self.sequenceLabel.setBuddy(self.sequence)

        self.retranslateUi(Editor)
        QtCore.QMetaObject.connectSlotsByName(Editor)
        Editor.setTabOrder(self.level, self.base)
        Editor.setTabOrder(self.base, self.top)
        Editor.setTabOrder(self.top, self.movement)
        Editor.setTabOrder(self.movement, self.speed)
        Editor.setTabOrder(self.speed, self.intensityChange)
        Editor.setTabOrder(self.intensityChange, self.forecastTime)

    def retranslateUi(self, Editor):
        _translate = QtCore.QCoreApplication.translate
        self.descriptionGroup.setTitle(_translate("Editor", "Description"))
        self.baseLabel.setText(_translate("Editor", "Base"))
        self.speedLabel.setText(_translate("Editor", "Speed"))
        self.intensityChangeLabel.setText(_translate("Editor", "Intensity"))
        self.topLabel.setText(_translate("Editor", "Top"))
        self.forecastTimeLabel.setText(_translate("Editor", "Forecast Time"))
        self.movementLabel.setText(_translate("Editor", "Movement"))
        self.levelLabel.setText(_translate("Editor", "Fight Level"))
        self.headGroup.setTitle(_translate("Editor", "Head"))
        self.beginningTimeLabel.setText(_translate("Editor", "Beginning"))
        self.observationTimeLabel.setText(_translate("Editor", "Observation Time"))
        self.endingTimeLabel.setText(_translate("Editor", "Ending"))
        self.observationLabel.setText(_translate("Editor", "Observation"))
        self.descriptionLabel.setText(_translate("Editor", "Description"))
        self.phenomenaLabel.setText(_translate("Editor", "Phenomena"))
        self.sequenceLabel.setText(_translate("Editor", "Sequence"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    Editor = QtWidgets.QWidget()
    ui = Ui_Editor()
    ui.setupUi(Editor)
    Editor.show()
    sys.exit(app.exec_())
