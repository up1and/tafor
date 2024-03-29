# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'D:\Work\tafor\tafor\components\ui\trend.ui'
#
# Created by: PyQt5 UI code generator 5.15.4
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Editor(object):
    def setupUi(self, Editor):
        Editor.setObjectName("Editor")
        Editor.resize(868, 140)
        Editor.setWindowTitle("Trend")
        self.gridLayout = QtWidgets.QGridLayout(Editor)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.gridLayout.setObjectName("gridLayout")
        self.typeGroup = QtWidgets.QGroupBox(Editor)
        self.typeGroup.setTitle("")
        self.typeGroup.setObjectName("typeGroup")
        self.gridLayout_6 = QtWidgets.QGridLayout(self.typeGroup)
        self.gridLayout_6.setObjectName("gridLayout_6")
        self.becmg = QtWidgets.QRadioButton(self.typeGroup)
        self.becmg.setText("BECMG")
        self.becmg.setChecked(True)
        self.becmg.setObjectName("becmg")
        self.gridLayout_6.addWidget(self.becmg, 0, 0, 1, 1)
        self.tempo = QtWidgets.QRadioButton(self.typeGroup)
        self.tempo.setText("TEMPO")
        self.tempo.setObjectName("tempo")
        self.gridLayout_6.addWidget(self.tempo, 0, 1, 1, 1)
        self.gridLayout.addWidget(self.typeGroup, 0, 0, 1, 2)
        self.prefixGroup = QtWidgets.QGroupBox(Editor)
        self.prefixGroup.setTitle("")
        self.prefixGroup.setObjectName("prefixGroup")
        self.gridLayout_5 = QtWidgets.QGridLayout(self.prefixGroup)
        self.gridLayout_5.setObjectName("gridLayout_5")
        self.at = QtWidgets.QCheckBox(self.prefixGroup)
        self.at.setText("AT")
        self.at.setCheckable(True)
        self.at.setObjectName("at")
        self.gridLayout_5.addWidget(self.at, 0, 2, 1, 1)
        self.fm = QtWidgets.QCheckBox(self.prefixGroup)
        self.fm.setText("FM")
        self.fm.setCheckable(True)
        self.fm.setObjectName("fm")
        self.gridLayout_5.addWidget(self.fm, 0, 0, 1, 1)
        self.tl = QtWidgets.QCheckBox(self.prefixGroup)
        self.tl.setText("TL")
        self.tl.setChecked(False)
        self.tl.setObjectName("tl")
        self.gridLayout_5.addWidget(self.tl, 0, 1, 1, 1)
        self.gridLayout.addWidget(self.prefixGroup, 0, 2, 1, 2)
        self.gustLabel = QtWidgets.QLabel(Editor)
        self.gustLabel.setObjectName("gustLabel")
        self.gridLayout.addWidget(self.gustLabel, 2, 2, 1, 1)
        self.weatherWithIntensityLabel = QtWidgets.QLabel(Editor)
        self.weatherWithIntensityLabel.setObjectName("weatherWithIntensityLabel")
        self.gridLayout.addWidget(self.weatherWithIntensityLabel, 2, 4, 1, 1)
        self.cloud2 = QtWidgets.QLineEdit(Editor)
        self.cloud2.setObjectName("cloud2")
        self.gridLayout.addWidget(self.cloud2, 3, 7, 1, 1)
        self.cloud3 = QtWidgets.QLineEdit(Editor)
        self.cloud3.setObjectName("cloud3")
        self.gridLayout.addWidget(self.cloud3, 3, 8, 1, 1)
        self.cbLabel = QtWidgets.QLabel(Editor)
        self.cbLabel.setObjectName("cbLabel")
        self.gridLayout.addWidget(self.cbLabel, 2, 9, 1, 1)
        self.weatherLabel = QtWidgets.QLabel(Editor)
        self.weatherLabel.setObjectName("weatherLabel")
        self.gridLayout.addWidget(self.weatherLabel, 2, 5, 1, 1)
        self.visLabel = QtWidgets.QLabel(Editor)
        self.visLabel.setObjectName("visLabel")
        self.gridLayout.addWidget(self.visLabel, 2, 3, 1, 1)
        self.cloud1Label = QtWidgets.QLabel(Editor)
        self.cloud1Label.setObjectName("cloud1Label")
        self.gridLayout.addWidget(self.cloud1Label, 2, 6, 1, 1)
        self.gust = QtWidgets.QLineEdit(Editor)
        self.gust.setObjectName("gust")
        self.gridLayout.addWidget(self.gust, 3, 2, 1, 1)
        self.cloud1 = QtWidgets.QLineEdit(Editor)
        self.cloud1.setObjectName("cloud1")
        self.gridLayout.addWidget(self.cloud1, 3, 6, 1, 1)
        self.cloud2Label = QtWidgets.QLabel(Editor)
        self.cloud2Label.setObjectName("cloud2Label")
        self.gridLayout.addWidget(self.cloud2Label, 2, 7, 1, 1)
        self.weatherWithIntensity = QtWidgets.QComboBox(Editor)
        self.weatherWithIntensity.setEditable(True)
        self.weatherWithIntensity.setObjectName("weatherWithIntensity")
        self.gridLayout.addWidget(self.weatherWithIntensity, 3, 4, 1, 1)
        self.cavok = QtWidgets.QCheckBox(Editor)
        self.cavok.setText("CAVOK")
        self.cavok.setCheckable(True)
        self.cavok.setObjectName("cavok")
        self.gridLayout.addWidget(self.cavok, 4, 3, 1, 1)
        self.nsc = QtWidgets.QCheckBox(Editor)
        self.nsc.setText("NSC")
        self.nsc.setObjectName("nsc")
        self.gridLayout.addWidget(self.nsc, 4, 6, 1, 1)
        self.vis = QtWidgets.QLineEdit(Editor)
        self.vis.setObjectName("vis")
        self.gridLayout.addWidget(self.vis, 3, 3, 1, 1)
        self.cb = QtWidgets.QLineEdit(Editor)
        self.cb.setObjectName("cb")
        self.gridLayout.addWidget(self.cb, 3, 9, 1, 1)
        self.windLabel = QtWidgets.QLabel(Editor)
        self.windLabel.setObjectName("windLabel")
        self.gridLayout.addWidget(self.windLabel, 2, 1, 1, 1)
        self.period = QtWidgets.QLineEdit(Editor)
        self.period.setEnabled(False)
        self.period.setObjectName("period")
        self.gridLayout.addWidget(self.period, 3, 0, 1, 1)
        self.periodLabel = QtWidgets.QLabel(Editor)
        self.periodLabel.setObjectName("periodLabel")
        self.gridLayout.addWidget(self.periodLabel, 2, 0, 1, 1)
        self.nosig = QtWidgets.QCheckBox(Editor)
        self.nosig.setText("NOSIG")
        self.nosig.setObjectName("nosig")
        self.gridLayout.addWidget(self.nosig, 5, 0, 1, 1)
        self.weather = QtWidgets.QComboBox(Editor)
        self.weather.setEditable(True)
        self.weather.setObjectName("weather")
        self.gridLayout.addWidget(self.weather, 3, 5, 1, 1)
        self.wind = QtWidgets.QLineEdit(Editor)
        self.wind.setObjectName("wind")
        self.gridLayout.addWidget(self.wind, 3, 1, 1, 1)
        self.cloud3Label = QtWidgets.QLabel(Editor)
        self.cloud3Label.setObjectName("cloud3Label")
        self.gridLayout.addWidget(self.cloud3Label, 2, 8, 1, 1)
        spacerItem = QtWidgets.QSpacerItem(40, 10, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.gridLayout.addItem(spacerItem, 1, 0, 1, 10)
        self.metarBorad = QtWidgets.QWidget(Editor)
        self.metarBorad.setObjectName("metarBorad")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.metarBorad)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.metar = QtWidgets.QLabel(self.metarBorad)
        self.metar.setWordWrap(True)
        self.metar.setObjectName("metar")
        self.horizontalLayout.addWidget(self.metar)
        self.gridLayout.addWidget(self.metarBorad, 0, 4, 1, 6)
        self.gustLabel.setBuddy(self.gust)
        self.weatherWithIntensityLabel.setBuddy(self.weatherWithIntensity)
        self.cbLabel.setBuddy(self.cb)
        self.weatherLabel.setBuddy(self.weather)
        self.visLabel.setBuddy(self.vis)
        self.cloud1Label.setBuddy(self.cloud1)
        self.cloud2Label.setBuddy(self.cloud2)
        self.windLabel.setBuddy(self.wind)
        self.periodLabel.setBuddy(self.period)
        self.cloud3Label.setBuddy(self.cloud3)

        self.retranslateUi(Editor)
        QtCore.QMetaObject.connectSlotsByName(Editor)
        Editor.setTabOrder(self.becmg, self.tempo)
        Editor.setTabOrder(self.tempo, self.fm)
        Editor.setTabOrder(self.fm, self.tl)
        Editor.setTabOrder(self.tl, self.at)
        Editor.setTabOrder(self.at, self.period)
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
        Editor.setTabOrder(self.nsc, self.nosig)

    def retranslateUi(self, Editor):
        _translate = QtCore.QCoreApplication.translate
        self.gustLabel.setText(_translate("Editor", "Gust"))
        self.weatherWithIntensityLabel.setText(_translate("Editor", "Weather"))
        self.cbLabel.setText(_translate("Editor", "Cumulonimbus"))
        self.weatherLabel.setText(_translate("Editor", "Weather"))
        self.visLabel.setText(_translate("Editor", "Visibility"))
        self.cloud1Label.setText(_translate("Editor", "Cloud"))
        self.cloud2Label.setText(_translate("Editor", "Cloud"))
        self.windLabel.setText(_translate("Editor", "Wind"))
        self.periodLabel.setText(_translate("Editor", "Period"))
        self.cloud3Label.setText(_translate("Editor", "Cloud"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    Editor = QtWidgets.QWidget()
    ui = Ui_Editor()
    ui.setupUi(Editor)
    Editor.show()
    sys.exit(app.exec_())
