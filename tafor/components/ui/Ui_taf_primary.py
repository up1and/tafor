# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'D:\Work\tafor\tafor\components\ui\taf_primary.ui'
#
# Created by: PyQt5 UI code generator 5.6
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Editor(object):
    def setupUi(self, Editor):
        Editor.setObjectName("Editor")
        Editor.resize(978, 206)
        Editor.setWindowTitle("PRIMARY")
        self.gridLayout = QtWidgets.QGridLayout(Editor)
        self.gridLayout.setObjectName("gridLayout")
        self.period = QtWidgets.QLineEdit(Editor)
        self.period.setObjectName("period")
        self.gridLayout.addWidget(self.period, 3, 1, 1, 1)
        self.cbLabel = QtWidgets.QLabel(Editor)
        self.cbLabel.setObjectName("cbLabel")
        self.gridLayout.addWidget(self.cbLabel, 2, 10, 1, 1)
        self.cloud2 = QtWidgets.QLineEdit(Editor)
        self.cloud2.setObjectName("cloud2")
        self.gridLayout.addWidget(self.cloud2, 3, 8, 1, 1)
        self.weatherLabel = QtWidgets.QLabel(Editor)
        self.weatherLabel.setObjectName("weatherLabel")
        self.gridLayout.addWidget(self.weatherLabel, 2, 6, 1, 1)
        self.visLabel = QtWidgets.QLabel(Editor)
        self.visLabel.setObjectName("visLabel")
        self.gridLayout.addWidget(self.visLabel, 2, 4, 1, 1)
        self.cloud3Label = QtWidgets.QLabel(Editor)
        self.cloud3Label.setObjectName("cloud3Label")
        self.gridLayout.addWidget(self.cloud3Label, 2, 9, 1, 1)
        self.tempo2Checkbox = QtWidgets.QCheckBox(Editor)
        self.tempo2Checkbox.setText("TEMPO2")
        self.tempo2Checkbox.setObjectName("tempo2Checkbox")
        self.gridLayout.addWidget(self.tempo2Checkbox, 6, 1, 1, 1)
        self.tempo1Checkbox = QtWidgets.QCheckBox(Editor)
        self.tempo1Checkbox.setText("TEMPO1")
        self.tempo1Checkbox.setObjectName("tempo1Checkbox")
        self.gridLayout.addWidget(self.tempo1Checkbox, 5, 1, 1, 1)
        self.cloud2Label = QtWidgets.QLabel(Editor)
        self.cloud2Label.setObjectName("cloud2Label")
        self.gridLayout.addWidget(self.cloud2Label, 2, 8, 1, 1)
        self.periodLabel = QtWidgets.QLabel(Editor)
        self.periodLabel.setObjectName("periodLabel")
        self.gridLayout.addWidget(self.periodLabel, 2, 1, 1, 1)
        self.dateLabel = QtWidgets.QLabel(Editor)
        self.dateLabel.setObjectName("dateLabel")
        self.gridLayout.addWidget(self.dateLabel, 2, 0, 1, 1)
        self.cloud1Label = QtWidgets.QLabel(Editor)
        self.cloud1Label.setObjectName("cloud1Label")
        self.gridLayout.addWidget(self.cloud1Label, 2, 7, 1, 1)
        self.weatherWithIntensityLabel = QtWidgets.QLabel(Editor)
        self.weatherWithIntensityLabel.setObjectName("weatherWithIntensityLabel")
        self.gridLayout.addWidget(self.weatherWithIntensityLabel, 2, 5, 1, 1)
        self.windLabel = QtWidgets.QLabel(Editor)
        self.windLabel.setObjectName("windLabel")
        self.gridLayout.addWidget(self.windLabel, 2, 2, 1, 1)
        self.becmg1Checkbox = QtWidgets.QCheckBox(Editor)
        self.becmg1Checkbox.setText("BECMG1")
        self.becmg1Checkbox.setObjectName("becmg1Checkbox")
        self.gridLayout.addWidget(self.becmg1Checkbox, 5, 0, 1, 1)
        self.date = QtWidgets.QLineEdit(Editor)
        self.date.setObjectName("date")
        self.gridLayout.addWidget(self.date, 3, 0, 1, 1)
        self.vis = QtWidgets.QLineEdit(Editor)
        self.vis.setObjectName("vis")
        self.gridLayout.addWidget(self.vis, 3, 4, 1, 1)
        self.wind = QtWidgets.QLineEdit(Editor)
        self.wind.setObjectName("wind")
        self.gridLayout.addWidget(self.wind, 3, 2, 1, 1)
        self.cb = QtWidgets.QLineEdit(Editor)
        self.cb.setObjectName("cb")
        self.gridLayout.addWidget(self.cb, 3, 10, 1, 1)
        self.becmg3Checkbox = QtWidgets.QCheckBox(Editor)
        self.becmg3Checkbox.setText("BECMG3")
        self.becmg3Checkbox.setObjectName("becmg3Checkbox")
        self.gridLayout.addWidget(self.becmg3Checkbox, 7, 0, 1, 1)
        self.weatherWithIntensity = QtWidgets.QComboBox(Editor)
        self.weatherWithIntensity.setObjectName("weatherWithIntensity")
        self.gridLayout.addWidget(self.weatherWithIntensity, 3, 5, 1, 1)
        spacerItem = QtWidgets.QSpacerItem(40, 10, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.gridLayout.addItem(spacerItem, 1, 0, 1, 11)
        self.cloud3 = QtWidgets.QLineEdit(Editor)
        self.cloud3.setObjectName("cloud3")
        self.gridLayout.addWidget(self.cloud3, 3, 9, 1, 1)
        self.cloud1 = QtWidgets.QLineEdit(Editor)
        self.cloud1.setObjectName("cloud1")
        self.gridLayout.addWidget(self.cloud1, 3, 7, 1, 1)
        self.gust = QtWidgets.QLineEdit(Editor)
        self.gust.setObjectName("gust")
        self.gridLayout.addWidget(self.gust, 3, 3, 1, 1)
        self.becmg2Checkbox = QtWidgets.QCheckBox(Editor)
        self.becmg2Checkbox.setText("BECMG2")
        self.becmg2Checkbox.setObjectName("becmg2Checkbox")
        self.gridLayout.addWidget(self.becmg2Checkbox, 6, 0, 1, 1)
        self.tempo3Checkbox = QtWidgets.QCheckBox(Editor)
        self.tempo3Checkbox.setText("TEMPO3")
        self.tempo3Checkbox.setObjectName("tempo3Checkbox")
        self.gridLayout.addWidget(self.tempo3Checkbox, 7, 1, 1, 1)
        self.cavok = QtWidgets.QCheckBox(Editor)
        self.cavok.setText("CAVOK")
        self.cavok.setCheckable(True)
        self.cavok.setObjectName("cavok")
        self.gridLayout.addWidget(self.cavok, 4, 4, 1, 1)
        self.gustLabel = QtWidgets.QLabel(Editor)
        self.gustLabel.setObjectName("gustLabel")
        self.gridLayout.addWidget(self.gustLabel, 2, 3, 1, 1)
        self.nsc = QtWidgets.QCheckBox(Editor)
        self.nsc.setText("NSC")
        self.nsc.setObjectName("nsc")
        self.gridLayout.addWidget(self.nsc, 4, 7, 1, 1)
        self.weather = QtWidgets.QComboBox(Editor)
        self.weather.setObjectName("weather")
        self.gridLayout.addWidget(self.weather, 3, 6, 1, 1)
        self.sortGroup = QtWidgets.QGroupBox(Editor)
        self.sortGroup.setTitle("")
        self.sortGroup.setObjectName("sortGroup")
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout(self.sortGroup)
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.normal = QtWidgets.QRadioButton(self.sortGroup)
        self.normal.setChecked(True)
        self.normal.setObjectName("normal")
        self.horizontalLayout_3.addWidget(self.normal)
        self.cor = QtWidgets.QRadioButton(self.sortGroup)
        self.cor.setObjectName("cor")
        self.horizontalLayout_3.addWidget(self.cor)
        self.ccc = QtWidgets.QLineEdit(self.sortGroup)
        self.ccc.setObjectName("ccc")
        self.horizontalLayout_3.addWidget(self.ccc)
        self.amd = QtWidgets.QRadioButton(self.sortGroup)
        self.amd.setObjectName("amd")
        self.horizontalLayout_3.addWidget(self.amd)
        self.aaa = QtWidgets.QLineEdit(self.sortGroup)
        self.aaa.setObjectName("aaa")
        self.horizontalLayout_3.addWidget(self.aaa)
        self.cnl = QtWidgets.QRadioButton(self.sortGroup)
        self.cnl.setObjectName("cnl")
        self.horizontalLayout_3.addWidget(self.cnl)
        self.aaaCnl = QtWidgets.QLineEdit(self.sortGroup)
        self.aaaCnl.setObjectName("aaaCnl")
        self.horizontalLayout_3.addWidget(self.aaaCnl)
        self.prev = QtWidgets.QCheckBox(self.sortGroup)
        self.prev.setObjectName("prev")
        self.horizontalLayout_3.addWidget(self.prev)
        self.gridLayout.addWidget(self.sortGroup, 0, 0, 1, 7)
        self.temperatureLayout = QtWidgets.QHBoxLayout()
        self.temperatureLayout.setObjectName("temperatureLayout")
        spacerItem1 = QtWidgets.QSpacerItem(0, 20, QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Minimum)
        self.temperatureLayout.addItem(spacerItem1)
        self.gridLayout.addLayout(self.temperatureLayout, 5, 8, 2, 3)
        self.fmCheckbox = QtWidgets.QCheckBox(Editor)
        self.fmCheckbox.setObjectName("fmCheckbox")
        self.gridLayout.addWidget(self.fmCheckbox, 5, 2, 1, 1)
        self.cbLabel.setBuddy(self.cb)
        self.weatherLabel.setBuddy(self.weather)
        self.visLabel.setBuddy(self.vis)
        self.cloud3Label.setBuddy(self.cloud3)
        self.cloud2Label.setBuddy(self.cloud2)
        self.periodLabel.setBuddy(self.period)
        self.dateLabel.setBuddy(self.date)
        self.cloud1Label.setBuddy(self.cloud1)
        self.weatherWithIntensityLabel.setBuddy(self.weatherWithIntensity)
        self.windLabel.setBuddy(self.wind)
        self.gustLabel.setBuddy(self.gust)

        self.retranslateUi(Editor)
        QtCore.QMetaObject.connectSlotsByName(Editor)
        Editor.setTabOrder(self.normal, self.cor)
        Editor.setTabOrder(self.cor, self.ccc)
        Editor.setTabOrder(self.ccc, self.amd)
        Editor.setTabOrder(self.amd, self.aaa)
        Editor.setTabOrder(self.aaa, self.cnl)
        Editor.setTabOrder(self.cnl, self.aaaCnl)
        Editor.setTabOrder(self.aaaCnl, self.date)
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

    def retranslateUi(self, Editor):
        _translate = QtCore.QCoreApplication.translate
        self.cbLabel.setText(_translate("Editor", "Cumulonimbus"))
        self.weatherLabel.setText(_translate("Editor", "Weather"))
        self.visLabel.setText(_translate("Editor", "Visibility"))
        self.cloud3Label.setText(_translate("Editor", "Cloud"))
        self.cloud2Label.setText(_translate("Editor", "Cloud"))
        self.periodLabel.setText(_translate("Editor", "Period"))
        self.dateLabel.setText(_translate("Editor", "Datetime"))
        self.cloud1Label.setText(_translate("Editor", "Cloud"))
        self.weatherWithIntensityLabel.setText(_translate("Editor", "Weather"))
        self.windLabel.setText(_translate("Editor", "Wind"))
        self.gustLabel.setText(_translate("Editor", "Gust"))
        self.normal.setText(_translate("Editor", "Normal"))
        self.cor.setText(_translate("Editor", "Correct"))
        self.amd.setText(_translate("Editor", "Amend"))
        self.cnl.setText(_translate("Editor", "Cancel"))
        self.prev.setText(_translate("Editor", "Previous"))
        self.fmCheckbox.setText(_translate("Editor", "FM"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    Editor = QtWidgets.QWidget()
    ui = Ui_Editor()
    ui.setupUi(Editor)
    Editor.show()
    sys.exit(app.exec_())

