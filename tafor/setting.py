from PyQt5 import QtCore, QtGui, QtWidgets

from ui import Ui_setting, main_rc


class SettingDialog(QtWidgets.QDialog, Ui_setting.Ui_Dialog):
    """docstring for SettingDialog"""
    def __init__(self, parent=None):
        super(SettingDialog, self).__init__(parent)
        self.setupUi(self)

        self.setWindowIcon(QtGui.QIcon(':/setting.png'))

        self.bind_signal()

    def bind_signal(self):
        self.weather1_add_button.clicked.connect(lambda: self.add_weather(1))
        self.weather2_add_button.clicked.connect(lambda: self.add_weather(2))

        self.weather1_del_button.clicked.connect(lambda: self.del_weather(1))
        self.weather2_del_button.clicked.connect(lambda: self.del_weather(2))

    def add_weather(self, which):
        if which == 1:
            weather = self.weather1.text()
            if weather:
                self.weather1_list.addItem(weather)
        else:
            weather = self.weather2.text()
            if weather:
                self.weather2_list.addItem(weather)

    def del_weather(self, which):
        if which == 1:
            item = self.weather1_list.takeItem(self.weather1_list.currentRow())
        else:
            item = self.weather2_list.takeItem(self.weather2_list.currentRow())
        item = None



if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    ui = SettingDialog()
    ui.show()
    sys.exit(app.exec_())
    