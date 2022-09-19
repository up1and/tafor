# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'D:\Work\tafor\tafor\components\ui\sigmet_general.ui'
#
# Created by: PyQt5 UI code generator 5.15.4
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Editor(object):
    def setupUi(self, Editor):
        Editor.setObjectName("Editor")
        Editor.resize(431, 380)
        Editor.setWindowTitle("Sigmet")
        self.verticalLayout = QtWidgets.QVBoxLayout(Editor)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.headingGroup = QtWidgets.QGroupBox(Editor)
        self.headingGroup.setObjectName("headingGroup")
        self.gridLayout_1 = QtWidgets.QGridLayout(self.headingGroup)
        self.gridLayout_1.setObjectName("gridLayout_1")
        self.sequenceLabel = QtWidgets.QLabel(self.headingGroup)
        self.sequenceLabel.setObjectName("sequenceLabel")
        self.gridLayout_1.addWidget(self.sequenceLabel, 0, 2, 1, 1)
        self.endingTimeLabel = QtWidgets.QLabel(self.headingGroup)
        self.endingTimeLabel.setObjectName("endingTimeLabel")
        self.gridLayout_1.addWidget(self.endingTimeLabel, 0, 1, 1, 1)
        self.sequence = QtWidgets.QLineEdit(self.headingGroup)
        self.sequence.setObjectName("sequence")
        self.gridLayout_1.addWidget(self.sequence, 1, 2, 1, 1)
        self.beginningTime = QtWidgets.QLineEdit(self.headingGroup)
        self.beginningTime.setObjectName("beginningTime")
        self.gridLayout_1.addWidget(self.beginningTime, 1, 0, 1, 1)
        self.beginningTimeLabel = QtWidgets.QLabel(self.headingGroup)
        self.beginningTimeLabel.setObjectName("beginningTimeLabel")
        self.gridLayout_1.addWidget(self.beginningTimeLabel, 0, 0, 1, 1)
        self.endingTime = QtWidgets.QLineEdit(self.headingGroup)
        self.endingTime.setObjectName("endingTime")
        self.gridLayout_1.addWidget(self.endingTime, 1, 1, 1, 1)
        self.verticalLayout.addWidget(self.headingGroup)
        self.typeGroup = QtWidgets.QGroupBox(Editor)
        self.typeGroup.setObjectName("typeGroup")
        self.gridLayout_2 = QtWidgets.QGridLayout(self.typeGroup)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.phenomenaLabel = QtWidgets.QLabel(self.typeGroup)
        self.phenomenaLabel.setObjectName("phenomenaLabel")
        self.gridLayout_2.addWidget(self.phenomenaLabel, 0, 1, 1, 1)
        self.description = QtWidgets.QComboBox(self.typeGroup)
        self.description.setObjectName("description")
        self.gridLayout_2.addWidget(self.description, 1, 0, 1, 1)
        self.descriptionLabel = QtWidgets.QLabel(self.typeGroup)
        self.descriptionLabel.setObjectName("descriptionLabel")
        self.gridLayout_2.addWidget(self.descriptionLabel, 0, 0, 1, 1)
        self.phenomena = QtWidgets.QComboBox(self.typeGroup)
        self.phenomena.setObjectName("phenomena")
        self.gridLayout_2.addWidget(self.phenomena, 1, 1, 1, 1)
        spacerItem = QtWidgets.QSpacerItem(0, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.gridLayout_2.addItem(spacerItem, 1, 2, 1, 1)
        self.verticalLayout.addWidget(self.typeGroup)
        self.obsFcstGroup = QtWidgets.QGroupBox(Editor)
        self.obsFcstGroup.setObjectName("obsFcstGroup")
        self.gridLayout_3 = QtWidgets.QGridLayout(self.obsFcstGroup)
        self.gridLayout_3.setObjectName("gridLayout_3")
        self.observationLabel = QtWidgets.QLabel(self.obsFcstGroup)
        self.observationLabel.setObjectName("observationLabel")
        self.gridLayout_3.addWidget(self.observationLabel, 0, 0, 1, 1)
        self.forecastTimeLabel = QtWidgets.QLabel(self.obsFcstGroup)
        self.forecastTimeLabel.setEnabled(False)
        self.forecastTimeLabel.setObjectName("forecastTimeLabel")
        self.gridLayout_3.addWidget(self.forecastTimeLabel, 0, 2, 1, 1)
        self.observationTimeLabel = QtWidgets.QLabel(self.obsFcstGroup)
        self.observationTimeLabel.setObjectName("observationTimeLabel")
        self.gridLayout_3.addWidget(self.observationTimeLabel, 0, 1, 1, 1)
        self.forecastTime = QtWidgets.QLineEdit(self.obsFcstGroup)
        self.forecastTime.setEnabled(False)
        self.forecastTime.setObjectName("forecastTime")
        self.gridLayout_3.addWidget(self.forecastTime, 1, 2, 1, 1)
        self.observation = QtWidgets.QComboBox(self.obsFcstGroup)
        self.observation.setObjectName("observation")
        self.gridLayout_3.addWidget(self.observation, 1, 0, 1, 1)
        self.observationTime = QtWidgets.QLineEdit(self.obsFcstGroup)
        self.observationTime.setObjectName("observationTime")
        self.gridLayout_3.addWidget(self.observationTime, 1, 1, 1, 1)
        self.verticalLayout.addWidget(self.obsFcstGroup)
        self.extentGroup = QtWidgets.QGroupBox(Editor)
        self.extentGroup.setObjectName("extentGroup")
        self.gridLayout_4 = QtWidgets.QGridLayout(self.extentGroup)
        self.gridLayout_4.setObjectName("gridLayout_4")
        self.formatLabel = QtWidgets.QLabel(self.extentGroup)
        self.formatLabel.setObjectName("formatLabel")
        self.gridLayout_4.addWidget(self.formatLabel, 0, 2, 1, 1)
        self.baseLabel = QtWidgets.QLabel(self.extentGroup)
        self.baseLabel.setObjectName("baseLabel")
        self.gridLayout_4.addWidget(self.baseLabel, 0, 3, 1, 1)
        self.base = QtWidgets.QLineEdit(self.extentGroup)
        self.base.setObjectName("base")
        self.gridLayout_4.addWidget(self.base, 1, 3, 1, 1)
        self.top = QtWidgets.QLineEdit(self.extentGroup)
        self.top.setObjectName("top")
        self.gridLayout_4.addWidget(self.top, 1, 4, 1, 1)
        self.format = QtWidgets.QComboBox(self.extentGroup)
        self.format.setObjectName("format")
        self.gridLayout_4.addWidget(self.format, 1, 2, 1, 1)
        self.topLabel = QtWidgets.QLabel(self.extentGroup)
        self.topLabel.setObjectName("topLabel")
        self.gridLayout_4.addWidget(self.topLabel, 0, 4, 1, 1)
        self.verticalLayout.addWidget(self.extentGroup)
        self.changeGroup = QtWidgets.QGroupBox(Editor)
        self.changeGroup.setObjectName("changeGroup")
        self.gridLayout_5 = QtWidgets.QGridLayout(self.changeGroup)
        self.gridLayout_5.setObjectName("gridLayout_5")
        self.speedLabel = QtWidgets.QLabel(self.changeGroup)
        self.speedLabel.setObjectName("speedLabel")
        self.gridLayout_5.addWidget(self.speedLabel, 0, 1, 1, 1)
        self.speed = QtWidgets.QLineEdit(self.changeGroup)
        self.speed.setObjectName("speed")
        self.gridLayout_5.addWidget(self.speed, 1, 1, 1, 1)
        self.direction = QtWidgets.QComboBox(self.changeGroup)
        self.direction.setObjectName("direction")
        self.direction.addItem("")
        self.direction.setItemText(0, "N")
        self.direction.addItem("")
        self.direction.setItemText(1, "NNE")
        self.direction.addItem("")
        self.direction.setItemText(2, "NE")
        self.direction.addItem("")
        self.direction.setItemText(3, "ENE")
        self.direction.addItem("")
        self.direction.setItemText(4, "E")
        self.direction.addItem("")
        self.direction.setItemText(5, "ESE")
        self.direction.addItem("")
        self.direction.setItemText(6, "SE")
        self.direction.addItem("")
        self.direction.setItemText(7, "SSE")
        self.direction.addItem("")
        self.direction.setItemText(8, "S")
        self.direction.addItem("")
        self.direction.setItemText(9, "SSW")
        self.direction.addItem("")
        self.direction.setItemText(10, "SW")
        self.direction.addItem("")
        self.direction.setItemText(11, "WSW")
        self.direction.addItem("")
        self.direction.setItemText(12, "W")
        self.direction.addItem("")
        self.direction.setItemText(13, "WNW")
        self.direction.addItem("")
        self.direction.setItemText(14, "NW")
        self.direction.addItem("")
        self.direction.setItemText(15, "NNW")
        self.direction.addItem("")
        self.direction.setItemText(16, "STNR")
        self.gridLayout_5.addWidget(self.direction, 1, 0, 1, 1)
        self.directionLabel = QtWidgets.QLabel(self.changeGroup)
        self.directionLabel.setObjectName("directionLabel")
        self.gridLayout_5.addWidget(self.directionLabel, 0, 0, 1, 1)
        self.intensityChangeLabel = QtWidgets.QLabel(self.changeGroup)
        self.intensityChangeLabel.setObjectName("intensityChangeLabel")
        self.gridLayout_5.addWidget(self.intensityChangeLabel, 0, 2, 1, 1)
        self.intensityChange = QtWidgets.QComboBox(self.changeGroup)
        self.intensityChange.setObjectName("intensityChange")
        self.intensityChange.addItem("")
        self.intensityChange.setItemText(0, "NC")
        self.intensityChange.addItem("")
        self.intensityChange.setItemText(1, "INTSF")
        self.intensityChange.addItem("")
        self.intensityChange.setItemText(2, "WKN")
        self.gridLayout_5.addWidget(self.intensityChange, 1, 2, 1, 1)
        self.verticalLayout.addWidget(self.changeGroup)
        spacerItem1 = QtWidgets.QSpacerItem(20, 0, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem1)
        self.sequenceLabel.setBuddy(self.sequence)
        self.endingTimeLabel.setBuddy(self.endingTime)
        self.beginningTimeLabel.setBuddy(self.beginningTime)
        self.phenomenaLabel.setBuddy(self.phenomena)
        self.descriptionLabel.setBuddy(self.description)
        self.observationLabel.setBuddy(self.observation)
        self.forecastTimeLabel.setBuddy(self.forecastTime)
        self.observationTimeLabel.setBuddy(self.observationTime)
        self.formatLabel.setBuddy(self.format)
        self.baseLabel.setBuddy(self.base)
        self.topLabel.setBuddy(self.top)
        self.speedLabel.setBuddy(self.speed)
        self.directionLabel.setBuddy(self.direction)
        self.intensityChangeLabel.setBuddy(self.intensityChange)

        self.retranslateUi(Editor)
        QtCore.QMetaObject.connectSlotsByName(Editor)
        Editor.setTabOrder(self.beginningTime, self.endingTime)
        Editor.setTabOrder(self.endingTime, self.sequence)
        Editor.setTabOrder(self.sequence, self.description)
        Editor.setTabOrder(self.description, self.phenomena)
        Editor.setTabOrder(self.phenomena, self.observation)
        Editor.setTabOrder(self.observation, self.observationTime)
        Editor.setTabOrder(self.observationTime, self.forecastTime)
        Editor.setTabOrder(self.forecastTime, self.format)
        Editor.setTabOrder(self.format, self.base)
        Editor.setTabOrder(self.base, self.top)
        Editor.setTabOrder(self.top, self.direction)
        Editor.setTabOrder(self.direction, self.speed)

    def retranslateUi(self, Editor):
        _translate = QtCore.QCoreApplication.translate
        self.headingGroup.setTitle(_translate("Editor", "Heading"))
        self.sequenceLabel.setText(_translate("Editor", "Sequence"))
        self.endingTimeLabel.setText(_translate("Editor", "Ending"))
        self.beginningTimeLabel.setText(_translate("Editor", "Beginning"))
        self.typeGroup.setTitle(_translate("Editor", "Type"))
        self.phenomenaLabel.setText(_translate("Editor", "Phenomena"))
        self.descriptionLabel.setText(_translate("Editor", "Description"))
        self.obsFcstGroup.setTitle(_translate("Editor", "Observation / Forecast"))
        self.observationLabel.setText(_translate("Editor", "Observation"))
        self.forecastTimeLabel.setText(_translate("Editor", "Forecast Time"))
        self.observationTimeLabel.setText(_translate("Editor", "Observation Time"))
        self.extentGroup.setTitle(_translate("Editor", "Extent"))
        self.formatLabel.setText(_translate("Editor", "Format"))
        self.baseLabel.setText(_translate("Editor", "Base"))
        self.topLabel.setText(_translate("Editor", "Top"))
        self.changeGroup.setTitle(_translate("Editor", "Change"))
        self.speedLabel.setText(_translate("Editor", "Speed"))
        self.directionLabel.setText(_translate("Editor", "Direction"))
        self.intensityChangeLabel.setText(_translate("Editor", "Intensity"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    Editor = QtWidgets.QWidget()
    ui = Ui_Editor()
    ui.setupUi(Editor)
    Editor.show()
    sys.exit(app.exec_())
