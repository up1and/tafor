# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'D:\Work\tafor\tafor\components\ui\taf_primary.ui'
#
# Created by: PyQt5 UI code generator 5.6
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.resize(1024, 198)
        self.verticalLayout = QtWidgets.QVBoxLayout(Form)
        self.verticalLayout.setObjectName("verticalLayout")
        self.mainLayout = QtWidgets.QGridLayout()
        self.mainLayout.setObjectName("mainLayout")
        self.skc = QtWidgets.QCheckBox(Form)
        self.skc.setObjectName("skc")
        self.mainLayout.addWidget(self.skc, 4, 8, 1, 1)
        self.weatherWithIntensity = QtWidgets.QComboBox(Form)
        self.weatherWithIntensity.setObjectName("weatherWithIntensity")
        self.mainLayout.addWidget(self.weatherWithIntensity, 3, 6, 1, 1)
        self.vis = QtWidgets.QLineEdit(Form)
        self.vis.setObjectName("vis")
        self.mainLayout.addWidget(self.vis, 3, 4, 1, 1)
        self.gust = QtWidgets.QLineEdit(Form)
        self.gust.setObjectName("gust")
        self.mainLayout.addWidget(self.gust, 3, 3, 1, 1)
        self.tempo1Checkbox = QtWidgets.QCheckBox(Form)
        self.tempo1Checkbox.setObjectName("tempo1Checkbox")
        self.mainLayout.addWidget(self.tempo1Checkbox, 5, 1, 1, 1)
        self.nsc = QtWidgets.QCheckBox(Form)
        self.nsc.setObjectName("nsc")
        self.mainLayout.addWidget(self.nsc, 4, 9, 1, 1)
        self.cloud1Label = QtWidgets.QLabel(Form)
        self.cloud1Label.setObjectName("cloud1Label")
        self.mainLayout.addWidget(self.cloud1Label, 2, 8, 1, 1)
        self.gustLabel = QtWidgets.QLabel(Form)
        self.gustLabel.setObjectName("gustLabel")
        self.mainLayout.addWidget(self.gustLabel, 2, 3, 1, 1)
        self.cloud2 = QtWidgets.QLineEdit(Form)
        self.cloud2.setObjectName("cloud2")
        self.mainLayout.addWidget(self.cloud2, 3, 9, 1, 1)
        self.cloud3Label = QtWidgets.QLabel(Form)
        self.cloud3Label.setObjectName("cloud3Label")
        self.mainLayout.addWidget(self.cloud3Label, 2, 10, 1, 1)
        self.visLabel = QtWidgets.QLabel(Form)
        self.visLabel.setObjectName("visLabel")
        self.mainLayout.addWidget(self.visLabel, 2, 4, 1, 1)
        self.cloud2Label = QtWidgets.QLabel(Form)
        self.cloud2Label.setObjectName("cloud2Label")
        self.mainLayout.addWidget(self.cloud2Label, 2, 9, 1, 1)
        self.becmg2Checkbox = QtWidgets.QCheckBox(Form)
        self.becmg2Checkbox.setObjectName("becmg2Checkbox")
        self.mainLayout.addWidget(self.becmg2Checkbox, 6, 0, 1, 1)
        self.cloud1 = QtWidgets.QLineEdit(Form)
        self.cloud1.setObjectName("cloud1")
        self.mainLayout.addWidget(self.cloud1, 3, 8, 1, 1)
        self.tempMinLabel = QtWidgets.QLabel(Form)
        self.tempMinLabel.setObjectName("tempMinLabel")
        self.mainLayout.addWidget(self.tempMinLabel, 5, 11, 1, 1)
        self.tempo2Checkbox = QtWidgets.QCheckBox(Form)
        self.tempo2Checkbox.setObjectName("tempo2Checkbox")
        self.mainLayout.addWidget(self.tempo2Checkbox, 6, 1, 1, 1)
        self.dateLabel = QtWidgets.QLabel(Form)
        self.dateLabel.setObjectName("dateLabel")
        self.mainLayout.addWidget(self.dateLabel, 2, 0, 1, 1)
        self.period = QtWidgets.QLineEdit(Form)
        self.period.setObjectName("period")
        self.mainLayout.addWidget(self.period, 3, 1, 1, 1)
        self.tminLayout = QtWidgets.QFormLayout()
        self.tminLayout.setObjectName("tminLayout")
        self.tmin = QtWidgets.QLineEdit(Form)
        self.tmin.setMaximumSize(QtCore.QSize(40, 16777215))
        self.tmin.setObjectName("tmin")
        self.tminLayout.setWidget(0, QtWidgets.QFormLayout.LabelRole, self.tmin)
        self.tminTime = QtWidgets.QLineEdit(Form)
        self.tminTime.setMaximumSize(QtCore.QSize(40, 16777215))
        self.tminTime.setObjectName("tminTime")
        self.tminLayout.setWidget(0, QtWidgets.QFormLayout.FieldRole, self.tminTime)
        self.mainLayout.addLayout(self.tminLayout, 6, 11, 1, 1)
        self.tempMaxLabel = QtWidgets.QLabel(Form)
        self.tempMaxLabel.setObjectName("tempMaxLabel")
        self.mainLayout.addWidget(self.tempMaxLabel, 5, 10, 1, 1)
        self.weatherWithIntensityLabel = QtWidgets.QLabel(Form)
        self.weatherWithIntensityLabel.setObjectName("weatherWithIntensityLabel")
        self.mainLayout.addWidget(self.weatherWithIntensityLabel, 2, 6, 1, 1)
        self.tmaxLayout = QtWidgets.QFormLayout()
        self.tmaxLayout.setObjectName("tmaxLayout")
        self.tmax = QtWidgets.QLineEdit(Form)
        self.tmax.setMaximumSize(QtCore.QSize(40, 16777215))
        self.tmax.setObjectName("tmax")
        self.tmaxLayout.setWidget(0, QtWidgets.QFormLayout.LabelRole, self.tmax)
        self.tmaxTime = QtWidgets.QLineEdit(Form)
        self.tmaxTime.setMaximumSize(QtCore.QSize(40, 16777215))
        self.tmaxTime.setObjectName("tmaxTime")
        self.tmaxLayout.setWidget(0, QtWidgets.QFormLayout.FieldRole, self.tmaxTime)
        self.mainLayout.addLayout(self.tmaxLayout, 6, 10, 1, 1)
        self.becmg3Checkbox = QtWidgets.QCheckBox(Form)
        self.becmg3Checkbox.setObjectName("becmg3Checkbox")
        self.mainLayout.addWidget(self.becmg3Checkbox, 7, 0, 1, 1)
        self.cb = QtWidgets.QLineEdit(Form)
        self.cb.setObjectName("cb")
        self.mainLayout.addWidget(self.cb, 3, 11, 1, 1)
        self.cbLabel = QtWidgets.QLabel(Form)
        self.cbLabel.setObjectName("cbLabel")
        self.mainLayout.addWidget(self.cbLabel, 2, 11, 1, 1)
        self.becmg1Checkbox = QtWidgets.QCheckBox(Form)
        self.becmg1Checkbox.setObjectName("becmg1Checkbox")
        self.mainLayout.addWidget(self.becmg1Checkbox, 5, 0, 1, 1)
        self.cloud3 = QtWidgets.QLineEdit(Form)
        self.cloud3.setObjectName("cloud3")
        self.mainLayout.addWidget(self.cloud3, 3, 10, 1, 1)
        self.windLabel = QtWidgets.QLabel(Form)
        self.windLabel.setObjectName("windLabel")
        self.mainLayout.addWidget(self.windLabel, 2, 2, 1, 1)
        self.date = QtWidgets.QLineEdit(Form)
        self.date.setObjectName("date")
        self.mainLayout.addWidget(self.date, 3, 0, 1, 1)
        self.wind = QtWidgets.QLineEdit(Form)
        self.wind.setObjectName("wind")
        self.mainLayout.addWidget(self.wind, 3, 2, 1, 1)
        self.periodLabel = QtWidgets.QLabel(Form)
        self.periodLabel.setObjectName("periodLabel")
        self.mainLayout.addWidget(self.periodLabel, 2, 1, 1, 1)
        self.typeGroup = QtWidgets.QGroupBox(Form)
        self.typeGroup.setTitle("")
        self.typeGroup.setObjectName("typeGroup")
        self.gridLayout_6 = QtWidgets.QGridLayout(self.typeGroup)
        self.gridLayout_6.setObjectName("gridLayout_6")
        self.fc = QtWidgets.QRadioButton(self.typeGroup)
        self.fc.setChecked(True)
        self.fc.setObjectName("fc")
        self.gridLayout_6.addWidget(self.fc, 0, 0, 1, 1)
        self.ft = QtWidgets.QRadioButton(self.typeGroup)
        self.ft.setObjectName("ft")
        self.gridLayout_6.addWidget(self.ft, 0, 1, 1, 1)
        self.mainLayout.addWidget(self.typeGroup, 0, 0, 1, 2)
        self.cavok = QtWidgets.QCheckBox(Form)
        self.cavok.setCheckable(True)
        self.cavok.setObjectName("cavok")
        self.mainLayout.addWidget(self.cavok, 4, 4, 1, 1)
        self.weather = QtWidgets.QComboBox(Form)
        self.weather.setObjectName("weather")
        self.mainLayout.addWidget(self.weather, 3, 7, 1, 1)
        self.weatherLabel = QtWidgets.QLabel(Form)
        self.weatherLabel.setObjectName("weatherLabel")
        self.mainLayout.addWidget(self.weatherLabel, 2, 7, 1, 1)
        self.sortGroup = QtWidgets.QGroupBox(Form)
        self.sortGroup.setTitle("")
        self.sortGroup.setObjectName("sortGroup")
        self.gridLayout_5 = QtWidgets.QGridLayout(self.sortGroup)
        self.gridLayout_5.setObjectName("gridLayout_5")
        self.amd = QtWidgets.QRadioButton(self.sortGroup)
        self.amd.setObjectName("amd")
        self.gridLayout_5.addWidget(self.amd, 0, 3, 1, 1)
        self.normal = QtWidgets.QRadioButton(self.sortGroup)
        self.normal.setChecked(True)
        self.normal.setObjectName("normal")
        self.gridLayout_5.addWidget(self.normal, 0, 0, 1, 1)
        self.cnl = QtWidgets.QRadioButton(self.sortGroup)
        self.cnl.setObjectName("cnl")
        self.gridLayout_5.addWidget(self.cnl, 0, 5, 1, 1)
        self.cor = QtWidgets.QRadioButton(self.sortGroup)
        self.cor.setObjectName("cor")
        self.gridLayout_5.addWidget(self.cor, 0, 1, 1, 1)
        self.aaaCnl = QtWidgets.QLineEdit(self.sortGroup)
        self.aaaCnl.setObjectName("aaaCnl")
        self.gridLayout_5.addWidget(self.aaaCnl, 0, 6, 1, 1)
        self.ccc = QtWidgets.QLineEdit(self.sortGroup)
        self.ccc.setObjectName("ccc")
        self.gridLayout_5.addWidget(self.ccc, 0, 2, 1, 1)
        self.aaa = QtWidgets.QLineEdit(self.sortGroup)
        self.aaa.setObjectName("aaa")
        self.gridLayout_5.addWidget(self.aaa, 0, 4, 1, 1)
        self.missed = QtWidgets.QRadioButton(self.sortGroup)
        self.missed.setObjectName("missed")
        self.gridLayout_5.addWidget(self.missed, 0, 7, 1, 1)
        self.mainLayout.addWidget(self.sortGroup, 0, 4, 1, 8)
        self.verticalLayout.addLayout(self.mainLayout)
        self.cloud1Label.setBuddy(self.cloud1)
        self.gustLabel.setBuddy(self.gust)
        self.cloud3Label.setBuddy(self.cloud3)
        self.visLabel.setBuddy(self.vis)
        self.cloud2Label.setBuddy(self.cloud2)
        self.tempMinLabel.setBuddy(self.tmin)
        self.dateLabel.setBuddy(self.date)
        self.tempMaxLabel.setBuddy(self.tmax)
        self.weatherWithIntensityLabel.setBuddy(self.weatherWithIntensity)
        self.cbLabel.setBuddy(self.cb)
        self.windLabel.setBuddy(self.wind)
        self.periodLabel.setBuddy(self.period)
        self.weatherLabel.setBuddy(self.weather)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)
        Form.setTabOrder(self.fc, self.ft)
        Form.setTabOrder(self.ft, self.normal)
        Form.setTabOrder(self.normal, self.cor)
        Form.setTabOrder(self.cor, self.amd)
        Form.setTabOrder(self.amd, self.cnl)
        Form.setTabOrder(self.cnl, self.date)
        Form.setTabOrder(self.date, self.period)
        Form.setTabOrder(self.period, self.wind)
        Form.setTabOrder(self.wind, self.gust)
        Form.setTabOrder(self.gust, self.vis)
        Form.setTabOrder(self.vis, self.weatherWithIntensity)
        Form.setTabOrder(self.weatherWithIntensity, self.cloud1)
        Form.setTabOrder(self.cloud1, self.cloud2)
        Form.setTabOrder(self.cloud2, self.cloud3)
        Form.setTabOrder(self.cloud3, self.cb)
        Form.setTabOrder(self.cb, self.cavok)
        Form.setTabOrder(self.cavok, self.skc)
        Form.setTabOrder(self.skc, self.nsc)
        Form.setTabOrder(self.nsc, self.tmax)
        Form.setTabOrder(self.tmax, self.tmaxTime)
        Form.setTabOrder(self.tmaxTime, self.tmin)
        Form.setTabOrder(self.tmin, self.tminTime)
        Form.setTabOrder(self.tminTime, self.becmg1Checkbox)
        Form.setTabOrder(self.becmg1Checkbox, self.becmg2Checkbox)
        Form.setTabOrder(self.becmg2Checkbox, self.tempo1Checkbox)
        Form.setTabOrder(self.tempo1Checkbox, self.tempo2Checkbox)

    def retranslateUi(self, Form):
        _translate = QtCore.QCoreApplication.translate
        Form.setWindowTitle(_translate("Form", "Form"))
        self.skc.setText(_translate("Form", "SKC"))
        self.tempo1Checkbox.setText(_translate("Form", "TEMPO1"))
        self.nsc.setText(_translate("Form", "NSC"))
        self.cloud1Label.setText(_translate("Form", "云组1"))
        self.gustLabel.setText(_translate("Form", "阵风"))
        self.cloud3Label.setText(_translate("Form", "云组3"))
        self.visLabel.setText(_translate("Form", "能见度"))
        self.cloud2Label.setText(_translate("Form", "云组2"))
        self.becmg2Checkbox.setText(_translate("Form", "BECMG2"))
        self.tempMinLabel.setText(_translate("Form", "最低温"))
        self.tempo2Checkbox.setText(_translate("Form", "TEMPO2"))
        self.dateLabel.setText(_translate("Form", "日期"))
        self.tempMaxLabel.setText(_translate("Form", "最高温"))
        self.weatherWithIntensityLabel.setText(_translate("Form", "天气现象1"))
        self.becmg3Checkbox.setText(_translate("Form", "BECMG3"))
        self.cbLabel.setText(_translate("Form", "积雨云"))
        self.becmg1Checkbox.setText(_translate("Form", "BECMG1"))
        self.windLabel.setText(_translate("Form", "风向风速"))
        self.periodLabel.setText(_translate("Form", "时段"))
        self.fc.setText(_translate("Form", "FC"))
        self.ft.setText(_translate("Form", "FT"))
        self.cavok.setText(_translate("Form", "CAVOK"))
        self.weatherLabel.setText(_translate("Form", "天气现象2"))
        self.amd.setText(_translate("Form", "修订报"))
        self.normal.setText(_translate("Form", "正常报"))
        self.cnl.setText(_translate("Form", "取消报"))
        self.cor.setText(_translate("Form", "更正报"))
        self.missed.setText(_translate("Form", "漏发报"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    Form = QtWidgets.QWidget()
    ui = Ui_Form()
    ui.setupUi(Form)
    Form.show()
    sys.exit(app.exec_())

