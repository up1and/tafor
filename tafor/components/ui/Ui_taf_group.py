# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'D:\Work\tafor\tafor\components\ui\taf_group.ui'
#
# Created by: PyQt5 UI code generator 5.6
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Editor(object):
    def setupUi(self, Editor):
        Editor.setObjectName("Editor")
        Editor.resize(1024, 109)
        Editor.setWindowTitle("GROUP")
        self.gridLayout = QtWidgets.QGridLayout(Editor)
        self.gridLayout.setObjectName("gridLayout")
        self.periodLabel = QtWidgets.QLabel(Editor)
        self.periodLabel.setObjectName("periodLabel")
        self.gridLayout.addWidget(self.periodLabel, 0, 1, 1, 1)
        self.windLabel = QtWidgets.QLabel(Editor)
        self.windLabel.setObjectName("windLabel")
        self.gridLayout.addWidget(self.windLabel, 0, 2, 1, 1)
        self.gustLabel = QtWidgets.QLabel(Editor)
        self.gustLabel.setObjectName("gustLabel")
        self.gridLayout.addWidget(self.gustLabel, 0, 3, 1, 1)
        self.visLabel = QtWidgets.QLabel(Editor)
        self.visLabel.setObjectName("visLabel")
        self.gridLayout.addWidget(self.visLabel, 0, 4, 1, 1)
        self.weatherWithIntensityLabel = QtWidgets.QLabel(Editor)
        self.weatherWithIntensityLabel.setObjectName("weatherWithIntensityLabel")
        self.gridLayout.addWidget(self.weatherWithIntensityLabel, 0, 5, 1, 1)
        self.weatherLabel = QtWidgets.QLabel(Editor)
        self.weatherLabel.setObjectName("weatherLabel")
        self.gridLayout.addWidget(self.weatherLabel, 0, 6, 1, 1)
        self.cloud1Label = QtWidgets.QLabel(Editor)
        self.cloud1Label.setObjectName("cloud1Label")
        self.gridLayout.addWidget(self.cloud1Label, 0, 7, 1, 1)
        self.cloud2Label = QtWidgets.QLabel(Editor)
        self.cloud2Label.setObjectName("cloud2Label")
        self.gridLayout.addWidget(self.cloud2Label, 0, 8, 1, 1)
        self.cloud3Label = QtWidgets.QLabel(Editor)
        self.cloud3Label.setObjectName("cloud3Label")
        self.gridLayout.addWidget(self.cloud3Label, 0, 9, 1, 1)
        self.cbLabel = QtWidgets.QLabel(Editor)
        self.cbLabel.setObjectName("cbLabel")
        self.gridLayout.addWidget(self.cbLabel, 0, 10, 1, 1)
        self.name = QtWidgets.QLabel(Editor)
        self.name.setMinimumSize(QtCore.QSize(76, 0))
        self.name.setStyleSheet("color: rgb(120, 120, 120);")
        self.name.setText("GROUP")
        self.name.setObjectName("name")
        self.gridLayout.addWidget(self.name, 1, 0, 1, 1)
        self.period = QtWidgets.QLineEdit(Editor)
        self.period.setObjectName("period")
        self.gridLayout.addWidget(self.period, 1, 1, 1, 1)
        self.wind = QtWidgets.QLineEdit(Editor)
        self.wind.setObjectName("wind")
        self.gridLayout.addWidget(self.wind, 1, 2, 1, 1)
        self.gust = QtWidgets.QLineEdit(Editor)
        self.gust.setObjectName("gust")
        self.gridLayout.addWidget(self.gust, 1, 3, 1, 1)
        self.vis = QtWidgets.QLineEdit(Editor)
        self.vis.setObjectName("vis")
        self.gridLayout.addWidget(self.vis, 1, 4, 1, 1)
        self.weatherWithIntensity = QtWidgets.QComboBox(Editor)
        self.weatherWithIntensity.setEditable(True)
        self.weatherWithIntensity.setObjectName("weatherWithIntensity")
        self.gridLayout.addWidget(self.weatherWithIntensity, 1, 5, 1, 1)
        self.weather = QtWidgets.QComboBox(Editor)
        self.weather.setEditable(True)
        self.weather.setObjectName("weather")
        self.gridLayout.addWidget(self.weather, 1, 6, 1, 1)
        self.cloud1 = QtWidgets.QLineEdit(Editor)
        self.cloud1.setObjectName("cloud1")
        self.gridLayout.addWidget(self.cloud1, 1, 7, 1, 1)
        self.cloud2 = QtWidgets.QLineEdit(Editor)
        self.cloud2.setObjectName("cloud2")
        self.gridLayout.addWidget(self.cloud2, 1, 8, 1, 1)
        self.cloud3 = QtWidgets.QLineEdit(Editor)
        self.cloud3.setObjectName("cloud3")
        self.gridLayout.addWidget(self.cloud3, 1, 9, 1, 1)
        self.cb = QtWidgets.QLineEdit(Editor)
        self.cb.setObjectName("cb")
        self.gridLayout.addWidget(self.cb, 1, 10, 1, 1)
        self.cavok = QtWidgets.QCheckBox(Editor)
        self.cavok.setText("CAVOK")
        self.cavok.setObjectName("cavok")
        self.gridLayout.addWidget(self.cavok, 2, 4, 1, 1)
        self.nsc = QtWidgets.QCheckBox(Editor)
        self.nsc.setText("NSC")
        self.nsc.setObjectName("nsc")
        self.gridLayout.addWidget(self.nsc, 2, 7, 1, 1)
        self.periodLabel.setBuddy(self.period)
        self.windLabel.setBuddy(self.wind)
        self.gustLabel.setBuddy(self.gust)
        self.visLabel.setBuddy(self.vis)
        self.weatherWithIntensityLabel.setBuddy(self.weatherWithIntensity)
        self.weatherLabel.setBuddy(self.weather)
        self.cloud1Label.setBuddy(self.cloud1)
        self.cloud2Label.setBuddy(self.cloud2)
        self.cloud3Label.setBuddy(self.cloud3)
        self.cbLabel.setBuddy(self.cb)

        self.retranslateUi(Editor)
        QtCore.QMetaObject.connectSlotsByName(Editor)
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
        self.periodLabel.setText(_translate("Editor", "Period"))
        self.windLabel.setText(_translate("Editor", "Wind"))
        self.gustLabel.setText(_translate("Editor", "Gust"))
        self.visLabel.setText(_translate("Editor", "Visibility"))
        self.weatherWithIntensityLabel.setText(_translate("Editor", "Weather"))
        self.weatherLabel.setText(_translate("Editor", "Weather"))
        self.cloud1Label.setText(_translate("Editor", "Cloud"))
        self.cloud2Label.setText(_translate("Editor", "Cloud"))
        self.cloud3Label.setText(_translate("Editor", "Cloud"))
        self.cbLabel.setText(_translate("Editor", "Cumulonimbus"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    Editor = QtWidgets.QWidget()
    ui = Ui_Editor()
    ui.setupUi(Editor)
    Editor.show()
    sys.exit(app.exec_())

