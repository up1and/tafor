# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'D:\Work\tafor\tafor\components\ui\taf_primary.ui'
#
# Created by: PyQt5 UI code generator 5.15.4
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Editor(object):
    def setupUi(self, Editor):
        Editor.setObjectName("Editor")
        Editor.resize(965, 183)
        Editor.setWindowTitle("PRIMARY")
        self.gridLayout = QtWidgets.QGridLayout(Editor)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.gridLayout.setObjectName("gridLayout")
        self.date = QtWidgets.QLineEdit(Editor)
        self.date.setObjectName("date")
        self.gridLayout.addWidget(self.date, 2, 0, 1, 1)
        self.cbLabel = QtWidgets.QLabel(Editor)
        self.cbLabel.setObjectName("cbLabel")
        self.gridLayout.addWidget(self.cbLabel, 1, 10, 1, 1)
        self.becmg2Checkbox = QtWidgets.QCheckBox(Editor)
        self.becmg2Checkbox.setText("BECMG2")
        self.becmg2Checkbox.setObjectName("becmg2Checkbox")
        self.gridLayout.addWidget(self.becmg2Checkbox, 5, 0, 1, 1)
        self.becmg1Checkbox = QtWidgets.QCheckBox(Editor)
        self.becmg1Checkbox.setText("BECMG1")
        self.becmg1Checkbox.setObjectName("becmg1Checkbox")
        self.gridLayout.addWidget(self.becmg1Checkbox, 4, 0, 1, 1)
        self.wind = QtWidgets.QLineEdit(Editor)
        self.wind.setObjectName("wind")
        self.gridLayout.addWidget(self.wind, 2, 2, 1, 1)
        self.cloud2 = QtWidgets.QLineEdit(Editor)
        self.cloud2.setObjectName("cloud2")
        self.gridLayout.addWidget(self.cloud2, 2, 8, 1, 1)
        self.nsc = QtWidgets.QCheckBox(Editor)
        self.nsc.setText("NSC")
        self.nsc.setObjectName("nsc")
        self.gridLayout.addWidget(self.nsc, 3, 7, 1, 1)
        self.cavok = QtWidgets.QCheckBox(Editor)
        self.cavok.setText("CAVOK")
        self.cavok.setCheckable(True)
        self.cavok.setObjectName("cavok")
        self.gridLayout.addWidget(self.cavok, 3, 4, 1, 1)
        self.cloud2Label = QtWidgets.QLabel(Editor)
        self.cloud2Label.setObjectName("cloud2Label")
        self.gridLayout.addWidget(self.cloud2Label, 1, 8, 1, 1)
        self.gust = QtWidgets.QLineEdit(Editor)
        self.gust.setObjectName("gust")
        self.gridLayout.addWidget(self.gust, 2, 3, 1, 1)
        self.cloud1 = QtWidgets.QLineEdit(Editor)
        self.cloud1.setObjectName("cloud1")
        self.gridLayout.addWidget(self.cloud1, 2, 7, 1, 1)
        self.period = QtWidgets.QLineEdit(Editor)
        self.period.setObjectName("period")
        self.gridLayout.addWidget(self.period, 2, 1, 1, 1)
        self.dateLabel = QtWidgets.QLabel(Editor)
        self.dateLabel.setObjectName("dateLabel")
        self.gridLayout.addWidget(self.dateLabel, 1, 0, 1, 1)
        self.fmCheckbox = QtWidgets.QCheckBox(Editor)
        self.fmCheckbox.setText("FM")
        self.fmCheckbox.setObjectName("fmCheckbox")
        self.gridLayout.addWidget(self.fmCheckbox, 4, 2, 1, 1)
        self.cloud1Label = QtWidgets.QLabel(Editor)
        self.cloud1Label.setObjectName("cloud1Label")
        self.gridLayout.addWidget(self.cloud1Label, 1, 7, 1, 1)
        self.weatherWithIntensityLabel = QtWidgets.QLabel(Editor)
        self.weatherWithIntensityLabel.setObjectName("weatherWithIntensityLabel")
        self.gridLayout.addWidget(self.weatherWithIntensityLabel, 1, 5, 1, 1)
        self.cloud3Label = QtWidgets.QLabel(Editor)
        self.cloud3Label.setObjectName("cloud3Label")
        self.gridLayout.addWidget(self.cloud3Label, 1, 9, 1, 1)
        self.weatherLabel = QtWidgets.QLabel(Editor)
        self.weatherLabel.setObjectName("weatherLabel")
        self.gridLayout.addWidget(self.weatherLabel, 1, 6, 1, 1)
        self.temperatureLayout = QtWidgets.QHBoxLayout()
        self.temperatureLayout.setObjectName("temperatureLayout")
        spacerItem = QtWidgets.QSpacerItem(0, 20, QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Minimum)
        self.temperatureLayout.addItem(spacerItem)
        self.gridLayout.addLayout(self.temperatureLayout, 4, 8, 2, 3)
        self.windLabel = QtWidgets.QLabel(Editor)
        self.windLabel.setObjectName("windLabel")
        self.gridLayout.addWidget(self.windLabel, 1, 2, 1, 1)
        self.weatherWithIntensity = QtWidgets.QComboBox(Editor)
        self.weatherWithIntensity.setEditable(True)
        self.weatherWithIntensity.setObjectName("weatherWithIntensity")
        self.gridLayout.addWidget(self.weatherWithIntensity, 2, 5, 1, 1)
        self.cloud3 = QtWidgets.QLineEdit(Editor)
        self.cloud3.setObjectName("cloud3")
        self.gridLayout.addWidget(self.cloud3, 2, 9, 1, 1)
        self.tempo3Checkbox = QtWidgets.QCheckBox(Editor)
        self.tempo3Checkbox.setText("TEMPO3")
        self.tempo3Checkbox.setObjectName("tempo3Checkbox")
        self.gridLayout.addWidget(self.tempo3Checkbox, 6, 1, 1, 1)
        self.weather = QtWidgets.QComboBox(Editor)
        self.weather.setEditable(True)
        self.weather.setObjectName("weather")
        self.gridLayout.addWidget(self.weather, 2, 6, 1, 1)
        self.periodLabel = QtWidgets.QLabel(Editor)
        self.periodLabel.setObjectName("periodLabel")
        self.gridLayout.addWidget(self.periodLabel, 1, 1, 1, 1)
        self.cb = QtWidgets.QLineEdit(Editor)
        self.cb.setObjectName("cb")
        self.gridLayout.addWidget(self.cb, 2, 10, 1, 1)
        self.vis = QtWidgets.QLineEdit(Editor)
        self.vis.setObjectName("vis")
        self.gridLayout.addWidget(self.vis, 2, 4, 1, 1)
        self.gustLabel = QtWidgets.QLabel(Editor)
        self.gustLabel.setObjectName("gustLabel")
        self.gridLayout.addWidget(self.gustLabel, 1, 3, 1, 1)
        self.tempo2Checkbox = QtWidgets.QCheckBox(Editor)
        self.tempo2Checkbox.setText("TEMPO2")
        self.tempo2Checkbox.setObjectName("tempo2Checkbox")
        self.gridLayout.addWidget(self.tempo2Checkbox, 5, 1, 1, 1)
        self.tempo1Checkbox = QtWidgets.QCheckBox(Editor)
        self.tempo1Checkbox.setText("TEMPO1")
        self.tempo1Checkbox.setObjectName("tempo1Checkbox")
        self.gridLayout.addWidget(self.tempo1Checkbox, 4, 1, 1, 1)
        self.becmg3Checkbox = QtWidgets.QCheckBox(Editor)
        self.becmg3Checkbox.setText("BECMG3")
        self.becmg3Checkbox.setObjectName("becmg3Checkbox")
        self.gridLayout.addWidget(self.becmg3Checkbox, 6, 0, 1, 1)
        self.visLabel = QtWidgets.QLabel(Editor)
        self.visLabel.setObjectName("visLabel")
        self.gridLayout.addWidget(self.visLabel, 1, 4, 1, 1)
        self.headLayout = QtWidgets.QHBoxLayout()
        self.headLayout.setContentsMargins(-1, -1, -1, 10)
        self.headLayout.setObjectName("headLayout")
        self.sortGroup = QtWidgets.QGroupBox(Editor)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.sortGroup.sizePolicy().hasHeightForWidth())
        self.sortGroup.setSizePolicy(sizePolicy)
        self.sortGroup.setTitle("")
        self.sortGroup.setObjectName("sortGroup")
        self.horizontalLayout_6 = QtWidgets.QHBoxLayout(self.sortGroup)
        self.horizontalLayout_6.setObjectName("horizontalLayout_6")
        self.normal = QtWidgets.QRadioButton(self.sortGroup)
        self.normal.setChecked(True)
        self.normal.setObjectName("normal")
        self.horizontalLayout_6.addWidget(self.normal)
        self.cor = QtWidgets.QRadioButton(self.sortGroup)
        self.cor.setObjectName("cor")
        self.horizontalLayout_6.addWidget(self.cor)
        self.amd = QtWidgets.QRadioButton(self.sortGroup)
        self.amd.setObjectName("amd")
        self.horizontalLayout_6.addWidget(self.amd)
        self.cnl = QtWidgets.QRadioButton(self.sortGroup)
        self.cnl.setObjectName("cnl")
        self.horizontalLayout_6.addWidget(self.cnl)
        self.sequence = QtWidgets.QLineEdit(self.sortGroup)
        self.sequence.setObjectName("sequence")
        self.horizontalLayout_6.addWidget(self.sequence)
        self.headLayout.addWidget(self.sortGroup)
        spacerItem1 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.headLayout.addItem(spacerItem1)
        self.specLayout = QtWidgets.QHBoxLayout()
        self.specLayout.setObjectName("specLayout")
        self.prevButton = QtWidgets.QToolButton(Editor)
        self.prevButton.setText("Prev")
        self.prevButton.setAutoRaise(True)
        self.prevButton.setObjectName("prevButton")
        self.specLayout.addWidget(self.prevButton)
        self.resetButton = QtWidgets.QToolButton(Editor)
        self.resetButton.setEnabled(False)
        self.resetButton.setText("Reset")
        self.resetButton.setAutoRaise(True)
        self.resetButton.setObjectName("resetButton")
        self.specLayout.addWidget(self.resetButton)
        self.headLayout.addLayout(self.specLayout)
        self.gridLayout.addLayout(self.headLayout, 0, 0, 1, 11)
        self.cbLabel.setBuddy(self.cb)
        self.cloud2Label.setBuddy(self.cloud2)
        self.dateLabel.setBuddy(self.date)
        self.cloud1Label.setBuddy(self.cloud1)
        self.weatherWithIntensityLabel.setBuddy(self.weatherWithIntensity)
        self.cloud3Label.setBuddy(self.cloud3)
        self.weatherLabel.setBuddy(self.weather)
        self.windLabel.setBuddy(self.wind)
        self.periodLabel.setBuddy(self.period)
        self.gustLabel.setBuddy(self.gust)
        self.visLabel.setBuddy(self.vis)

        self.retranslateUi(Editor)
        QtCore.QMetaObject.connectSlotsByName(Editor)
        Editor.setTabOrder(self.normal, self.cor)
        Editor.setTabOrder(self.cor, self.amd)
        Editor.setTabOrder(self.amd, self.cnl)
        Editor.setTabOrder(self.cnl, self.sequence)
        Editor.setTabOrder(self.sequence, self.prevButton)
        Editor.setTabOrder(self.prevButton, self.resetButton)
        Editor.setTabOrder(self.resetButton, self.date)
        Editor.setTabOrder(self.date, self.period)
        Editor.setTabOrder(self.period, self.wind)
        Editor.setTabOrder(self.wind, self.gust)
        Editor.setTabOrder(self.gust, self.vis)
        Editor.setTabOrder(self.vis, self.cavok)
        Editor.setTabOrder(self.cavok, self.weatherWithIntensity)
        Editor.setTabOrder(self.weatherWithIntensity, self.weather)
        Editor.setTabOrder(self.weather, self.cloud1)
        Editor.setTabOrder(self.cloud1, self.cloud2)
        Editor.setTabOrder(self.cloud2, self.cloud3)
        Editor.setTabOrder(self.cloud3, self.cb)
        Editor.setTabOrder(self.cb, self.nsc)
        Editor.setTabOrder(self.nsc, self.becmg1Checkbox)
        Editor.setTabOrder(self.becmg1Checkbox, self.becmg2Checkbox)
        Editor.setTabOrder(self.becmg2Checkbox, self.becmg3Checkbox)
        Editor.setTabOrder(self.becmg3Checkbox, self.tempo1Checkbox)
        Editor.setTabOrder(self.tempo1Checkbox, self.tempo2Checkbox)
        Editor.setTabOrder(self.tempo2Checkbox, self.tempo3Checkbox)
        Editor.setTabOrder(self.tempo3Checkbox, self.fmCheckbox)

    def retranslateUi(self, Editor):
        _translate = QtCore.QCoreApplication.translate
        self.cbLabel.setText(_translate("Editor", "Cumulonimbus"))
        self.cloud2Label.setText(_translate("Editor", "Cloud"))
        self.dateLabel.setText(_translate("Editor", "Datetime"))
        self.cloud1Label.setText(_translate("Editor", "Cloud"))
        self.weatherWithIntensityLabel.setText(_translate("Editor", "Weather"))
        self.cloud3Label.setText(_translate("Editor", "Cloud"))
        self.weatherLabel.setText(_translate("Editor", "Weather"))
        self.windLabel.setText(_translate("Editor", "Wind"))
        self.periodLabel.setText(_translate("Editor", "Period"))
        self.gustLabel.setText(_translate("Editor", "Gust"))
        self.visLabel.setText(_translate("Editor", "Visibility"))
        self.normal.setText(_translate("Editor", "Normal"))
        self.cor.setText(_translate("Editor", "Correct"))
        self.amd.setText(_translate("Editor", "Amend"))
        self.cnl.setText(_translate("Editor", "Cancel"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    Editor = QtWidgets.QWidget()
    ui = Ui_Editor()
    ui.setupUi(Editor)
    Editor.show()
    sys.exit(app.exec_())
