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
        self.main_layout = QtWidgets.QGridLayout()
        self.main_layout.setObjectName("main_layout")
        self.cloud2_label = QtWidgets.QLabel(Form)
        self.cloud2_label.setObjectName("cloud2_label")
        self.main_layout.addWidget(self.cloud2_label, 2, 8, 1, 1)
        self.cloud1_label = QtWidgets.QLabel(Form)
        self.cloud1_label.setObjectName("cloud1_label")
        self.main_layout.addWidget(self.cloud1_label, 2, 7, 1, 1)
        self.weather_with_intensity = QtWidgets.QComboBox(Form)
        self.weather_with_intensity.setObjectName("weather_with_intensity")
        self.main_layout.addWidget(self.weather_with_intensity, 3, 6, 1, 1)
        self.becmg2_checkbox = QtWidgets.QCheckBox(Form)
        self.becmg2_checkbox.setObjectName("becmg2_checkbox")
        self.main_layout.addWidget(self.becmg2_checkbox, 6, 0, 1, 1)
        self.vis = QtWidgets.QLineEdit(Form)
        self.vis.setObjectName("vis")
        self.main_layout.addWidget(self.vis, 3, 4, 1, 1)
        self.cloud3_label = QtWidgets.QLabel(Form)
        self.cloud3_label.setObjectName("cloud3_label")
        self.main_layout.addWidget(self.cloud3_label, 2, 9, 1, 1)
        self.tempo1_checkbox = QtWidgets.QCheckBox(Form)
        self.tempo1_checkbox.setObjectName("tempo1_checkbox")
        self.main_layout.addWidget(self.tempo1_checkbox, 5, 1, 1, 1)
        self.skc = QtWidgets.QCheckBox(Form)
        self.skc.setObjectName("skc")
        self.cavok_group = QtWidgets.QButtonGroup(Form)
        self.cavok_group.setObjectName("cavok_group")
        self.cavok_group.setExclusive(False)
        self.cavok_group.addButton(self.skc)
        self.main_layout.addWidget(self.skc, 4, 7, 1, 1)
        self.cloud1 = QtWidgets.QLineEdit(Form)
        self.cloud1.setObjectName("cloud1")
        self.main_layout.addWidget(self.cloud1, 3, 7, 1, 1)
        self.cloud2 = QtWidgets.QLineEdit(Form)
        self.cloud2.setObjectName("cloud2")
        self.main_layout.addWidget(self.cloud2, 3, 8, 1, 1)
        self.gust = QtWidgets.QLineEdit(Form)
        self.gust.setObjectName("gust")
        self.main_layout.addWidget(self.gust, 3, 3, 1, 1)
        self.temp_min_label = QtWidgets.QLabel(Form)
        self.temp_min_label.setObjectName("temp_min_label")
        self.main_layout.addWidget(self.temp_min_label, 5, 10, 1, 1)
        self.nsc = QtWidgets.QCheckBox(Form)
        self.nsc.setObjectName("nsc")
        self.cavok_group.addButton(self.nsc)
        self.main_layout.addWidget(self.nsc, 4, 8, 1, 1)
        self.weather = QtWidgets.QComboBox(Form)
        self.weather.setObjectName("weather")
        self.main_layout.addWidget(self.weather, 3, 5, 1, 1)
        self.gust_label = QtWidgets.QLabel(Form)
        self.gust_label.setObjectName("gust_label")
        self.main_layout.addWidget(self.gust_label, 2, 3, 1, 1)
        self.vis_label = QtWidgets.QLabel(Form)
        self.vis_label.setObjectName("vis_label")
        self.main_layout.addWidget(self.vis_label, 2, 4, 1, 1)
        self.weather_label = QtWidgets.QLabel(Form)
        self.weather_label.setObjectName("weather_label")
        self.main_layout.addWidget(self.weather_label, 2, 5, 1, 1)
        self.group_type = QtWidgets.QGroupBox(Form)
        self.group_type.setTitle("")
        self.group_type.setObjectName("group_type")
        self.gridLayout_6 = QtWidgets.QGridLayout(self.group_type)
        self.gridLayout_6.setObjectName("gridLayout_6")
        self.fc = QtWidgets.QRadioButton(self.group_type)
        self.fc.setChecked(True)
        self.fc.setObjectName("fc")
        self.gridLayout_6.addWidget(self.fc, 0, 0, 1, 1)
        self.ft = QtWidgets.QRadioButton(self.group_type)
        self.ft.setObjectName("ft")
        self.gridLayout_6.addWidget(self.ft, 0, 1, 1, 1)
        self.main_layout.addWidget(self.group_type, 0, 0, 1, 2)
        self.cb = QtWidgets.QLineEdit(Form)
        self.cb.setObjectName("cb")
        self.main_layout.addWidget(self.cb, 3, 10, 1, 1)
        self.cb_label = QtWidgets.QLabel(Form)
        self.cb_label.setObjectName("cb_label")
        self.main_layout.addWidget(self.cb_label, 2, 10, 1, 1)
        self.becmg1_checkbox = QtWidgets.QCheckBox(Form)
        self.becmg1_checkbox.setObjectName("becmg1_checkbox")
        self.main_layout.addWidget(self.becmg1_checkbox, 5, 0, 1, 1)
        self.temp_max_label = QtWidgets.QLabel(Form)
        self.temp_max_label.setObjectName("temp_max_label")
        self.main_layout.addWidget(self.temp_max_label, 5, 9, 1, 1)
        self.date_label = QtWidgets.QLabel(Form)
        self.date_label.setObjectName("date_label")
        self.main_layout.addWidget(self.date_label, 2, 0, 1, 1)
        self.wind = QtWidgets.QLineEdit(Form)
        self.wind.setObjectName("wind")
        self.main_layout.addWidget(self.wind, 3, 2, 1, 1)
        self.wind_label = QtWidgets.QLabel(Form)
        self.wind_label.setObjectName("wind_label")
        self.main_layout.addWidget(self.wind_label, 2, 2, 1, 1)
        self.cloud3 = QtWidgets.QLineEdit(Form)
        self.cloud3.setObjectName("cloud3")
        self.main_layout.addWidget(self.cloud3, 3, 9, 1, 1)
        self.period = QtWidgets.QLineEdit(Form)
        self.period.setObjectName("period")
        self.main_layout.addWidget(self.period, 3, 1, 1, 1)
        self.tempo2_checkbox = QtWidgets.QCheckBox(Form)
        self.tempo2_checkbox.setObjectName("tempo2_checkbox")
        self.main_layout.addWidget(self.tempo2_checkbox, 6, 1, 1, 1)
        self.period_label = QtWidgets.QLabel(Form)
        self.period_label.setObjectName("period_label")
        self.main_layout.addWidget(self.period_label, 2, 1, 1, 1)
        self.weather_with_intensity_label = QtWidgets.QLabel(Form)
        self.weather_with_intensity_label.setObjectName("weather_with_intensity_label")
        self.main_layout.addWidget(self.weather_with_intensity_label, 2, 6, 1, 1)
        self.cavok = QtWidgets.QCheckBox(Form)
        self.cavok.setCheckable(True)
        self.cavok.setObjectName("cavok")
        self.cavok_group.addButton(self.cavok)
        self.main_layout.addWidget(self.cavok, 4, 4, 1, 1)
        self.date = QtWidgets.QLineEdit(Form)
        self.date.setObjectName("date")
        self.main_layout.addWidget(self.date, 3, 0, 1, 1)
        self.tmin_layout = QtWidgets.QFormLayout()
        self.tmin_layout.setObjectName("tmin_layout")
        self.tmin = QtWidgets.QLineEdit(Form)
        self.tmin.setMaximumSize(QtCore.QSize(40, 16777215))
        self.tmin.setObjectName("tmin")
        self.tmin_layout.setWidget(0, QtWidgets.QFormLayout.LabelRole, self.tmin)
        self.tmin_time = QtWidgets.QLineEdit(Form)
        self.tmin_time.setMaximumSize(QtCore.QSize(40, 16777215))
        self.tmin_time.setObjectName("tmin_time")
        self.tmin_layout.setWidget(0, QtWidgets.QFormLayout.FieldRole, self.tmin_time)
        self.main_layout.addLayout(self.tmin_layout, 6, 10, 1, 1)
        self.tmax_layout = QtWidgets.QFormLayout()
        self.tmax_layout.setObjectName("tmax_layout")
        self.tmax = QtWidgets.QLineEdit(Form)
        self.tmax.setMaximumSize(QtCore.QSize(40, 16777215))
        self.tmax.setObjectName("tmax")
        self.tmax_layout.setWidget(0, QtWidgets.QFormLayout.LabelRole, self.tmax)
        self.tmax_time = QtWidgets.QLineEdit(Form)
        self.tmax_time.setMaximumSize(QtCore.QSize(40, 16777215))
        self.tmax_time.setObjectName("tmax_time")
        self.tmax_layout.setWidget(0, QtWidgets.QFormLayout.FieldRole, self.tmax_time)
        self.main_layout.addLayout(self.tmax_layout, 6, 9, 1, 1)
        self.becmg3_checkbox = QtWidgets.QCheckBox(Form)
        self.becmg3_checkbox.setObjectName("becmg3_checkbox")
        self.main_layout.addWidget(self.becmg3_checkbox, 7, 0, 1, 1)
        self.group_cls = QtWidgets.QGroupBox(Form)
        self.group_cls.setTitle("")
        self.group_cls.setObjectName("group_cls")
        self.gridLayout_5 = QtWidgets.QGridLayout(self.group_cls)
        self.gridLayout_5.setObjectName("gridLayout_5")
        self.normal = QtWidgets.QRadioButton(self.group_cls)
        self.normal.setChecked(True)
        self.normal.setObjectName("normal")
        self.gridLayout_5.addWidget(self.normal, 0, 0, 1, 1)
        self.amd = QtWidgets.QRadioButton(self.group_cls)
        self.amd.setObjectName("amd")
        self.gridLayout_5.addWidget(self.amd, 0, 3, 1, 1)
        self.cor = QtWidgets.QRadioButton(self.group_cls)
        self.cor.setObjectName("cor")
        self.gridLayout_5.addWidget(self.cor, 0, 1, 1, 1)
        self.cnl = QtWidgets.QRadioButton(self.group_cls)
        self.cnl.setObjectName("cnl")
        self.gridLayout_5.addWidget(self.cnl, 0, 5, 1, 1)
        self.aaa_cnl = QtWidgets.QLineEdit(self.group_cls)
        self.aaa_cnl.setObjectName("aaa_cnl")
        self.gridLayout_5.addWidget(self.aaa_cnl, 0, 6, 1, 1)
        self.aaa = QtWidgets.QLineEdit(self.group_cls)
        self.aaa.setObjectName("aaa")
        self.gridLayout_5.addWidget(self.aaa, 0, 4, 1, 1)
        self.ccc = QtWidgets.QLineEdit(self.group_cls)
        self.ccc.setObjectName("ccc")
        self.gridLayout_5.addWidget(self.ccc, 0, 2, 1, 1)
        self.main_layout.addWidget(self.group_cls, 0, 5, 1, 6)
        self.verticalLayout.addLayout(self.main_layout)
        self.cloud2_label.setBuddy(self.cloud2)
        self.cloud1_label.setBuddy(self.cloud1)
        self.cloud3_label.setBuddy(self.cloud3)
        self.temp_min_label.setBuddy(self.tmin)
        self.gust_label.setBuddy(self.gust)
        self.vis_label.setBuddy(self.vis)
        self.weather_label.setBuddy(self.weather)
        self.cb_label.setBuddy(self.cb)
        self.temp_max_label.setBuddy(self.tmax)
        self.date_label.setBuddy(self.date)
        self.wind_label.setBuddy(self.wind)
        self.period_label.setBuddy(self.period)
        self.weather_with_intensity_label.setBuddy(self.weather_with_intensity)

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
        Form.setTabOrder(self.vis, self.weather)
        Form.setTabOrder(self.weather, self.weather_with_intensity)
        Form.setTabOrder(self.weather_with_intensity, self.cloud1)
        Form.setTabOrder(self.cloud1, self.cloud2)
        Form.setTabOrder(self.cloud2, self.cloud3)
        Form.setTabOrder(self.cloud3, self.cb)
        Form.setTabOrder(self.cb, self.cavok)
        Form.setTabOrder(self.cavok, self.skc)
        Form.setTabOrder(self.skc, self.nsc)
        Form.setTabOrder(self.nsc, self.tmax)
        Form.setTabOrder(self.tmax, self.tmax_time)
        Form.setTabOrder(self.tmax_time, self.tmin)
        Form.setTabOrder(self.tmin, self.tmin_time)
        Form.setTabOrder(self.tmin_time, self.becmg1_checkbox)
        Form.setTabOrder(self.becmg1_checkbox, self.becmg2_checkbox)
        Form.setTabOrder(self.becmg2_checkbox, self.tempo1_checkbox)
        Form.setTabOrder(self.tempo1_checkbox, self.tempo2_checkbox)

    def retranslateUi(self, Form):
        _translate = QtCore.QCoreApplication.translate
        Form.setWindowTitle(_translate("Form", "Form"))
        self.cloud2_label.setText(_translate("Form", "云组2"))
        self.cloud1_label.setText(_translate("Form", "云组1"))
        self.becmg2_checkbox.setText(_translate("Form", "BECMG2"))
        self.cloud3_label.setText(_translate("Form", "云组3"))
        self.tempo1_checkbox.setText(_translate("Form", "TEMPO1"))
        self.skc.setText(_translate("Form", "SKC"))
        self.temp_min_label.setText(_translate("Form", "最低温"))
        self.nsc.setText(_translate("Form", "NSC"))
        self.gust_label.setText(_translate("Form", "阵风"))
        self.vis_label.setText(_translate("Form", "能见度"))
        self.weather_label.setText(_translate("Form", "天气现象1"))
        self.fc.setText(_translate("Form", "FC"))
        self.ft.setText(_translate("Form", "FT"))
        self.cb_label.setText(_translate("Form", "积雨云"))
        self.becmg1_checkbox.setText(_translate("Form", "BECMG1"))
        self.temp_max_label.setText(_translate("Form", "最高温"))
        self.date_label.setText(_translate("Form", "日期"))
        self.wind_label.setText(_translate("Form", "风向风速"))
        self.tempo2_checkbox.setText(_translate("Form", "TEMPO2"))
        self.period_label.setText(_translate("Form", "时段"))
        self.weather_with_intensity_label.setText(_translate("Form", "天气现象2"))
        self.cavok.setText(_translate("Form", "CAVOK"))
        self.becmg3_checkbox.setText(_translate("Form", "BECMG3"))
        self.normal.setText(_translate("Form", "正常报"))
        self.amd.setText(_translate("Form", "修订报"))
        self.cor.setText(_translate("Form", "更正报"))
        self.cnl.setText(_translate("Form", "取消报"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    Form = QtWidgets.QWidget()
    ui = Ui_Form()
    ui.setupUi(Form)
    Form.show()
    sys.exit(app.exec_())

