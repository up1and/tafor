# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'D:\Work\tafor\tafor\components\ui\chart.ui'
#
# Created by: PyQt5 UI code generator 5.11.3
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Chart(object):
    def setupUi(self, Chart):
        Chart.setObjectName("Chart")
        Chart.resize(800, 850)
        Chart.setMinimumSize(QtCore.QSize(800, 850))
        self.verticalLayout = QtWidgets.QVBoxLayout(Chart)
        self.verticalLayout.setObjectName("verticalLayout")
        self.calendarLayout = QtWidgets.QHBoxLayout()
        self.calendarLayout.setObjectName("calendarLayout")
        self.calendar = QtWidgets.QDateEdit(Chart)
        self.calendar.setCalendarPopup(True)
        self.calendar.setObjectName("calendar")
        self.calendarLayout.addWidget(self.calendar)
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.calendarLayout.addItem(spacerItem)
        self.latestButton = QtWidgets.QPushButton(Chart)
        self.latestButton.setObjectName("latestButton")
        self.calendarLayout.addWidget(self.latestButton)
        self.dayAgoButton = QtWidgets.QPushButton(Chart)
        self.dayAgoButton.setObjectName("dayAgoButton")
        self.calendarLayout.addWidget(self.dayAgoButton)
        self.hoursAgoButton = QtWidgets.QPushButton(Chart)
        self.hoursAgoButton.setObjectName("hoursAgoButton")
        self.calendarLayout.addWidget(self.hoursAgoButton)
        self.hoursLaterButton = QtWidgets.QPushButton(Chart)
        self.hoursLaterButton.setObjectName("hoursLaterButton")
        self.calendarLayout.addWidget(self.hoursLaterButton)
        self.dayLaterButton = QtWidgets.QPushButton(Chart)
        self.dayLaterButton.setObjectName("dayLaterButton")
        self.calendarLayout.addWidget(self.dayLaterButton)
        self.verticalLayout.addLayout(self.calendarLayout)
        self.scrollArea = QtWidgets.QScrollArea(Chart)
        self.scrollArea.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setObjectName("scrollArea")
        self.chartArea = QtWidgets.QWidget()
        self.chartArea.setGeometry(QtCore.QRect(0, 0, 782, 772))
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.chartArea.sizePolicy().hasHeightForWidth())
        self.chartArea.setSizePolicy(sizePolicy)
        self.chartArea.setMinimumSize(QtCore.QSize(500, 0))
        self.chartArea.setObjectName("chartArea")
        self.chartLayout = QtWidgets.QVBoxLayout(self.chartArea)
        self.chartLayout.setObjectName("chartLayout")
        self.scrollArea.setWidget(self.chartArea)
        self.verticalLayout.addWidget(self.scrollArea)
        self.buttonBox = QtWidgets.QDialogButtonBox(Chart)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Save)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(Chart)
        QtCore.QMetaObject.connectSlotsByName(Chart)

    def retranslateUi(self, Chart):
        _translate = QtCore.QCoreApplication.translate
        Chart.setWindowTitle(_translate("Chart", "Chart"))
        self.latestButton.setText(_translate("Chart", "Latest 24 Hours"))
        self.dayAgoButton.setText(_translate("Chart", "-1 Day"))
        self.hoursAgoButton.setText(_translate("Chart", "-3 Hours"))
        self.hoursLaterButton.setText(_translate("Chart", "+ 3 Hours"))
        self.dayLaterButton.setText(_translate("Chart", "+1 Day"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    Chart = QtWidgets.QDialog()
    ui = Ui_Chart()
    ui.setupUi(Chart)
    Chart.show()
    sys.exit(app.exec_())

