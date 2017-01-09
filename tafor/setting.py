from PyQt5 import QtCore, QtGui, QtWidgets

from ui import Ui_setting


class SettingDialog(QtWidgets.QDialog, Ui_setting.Ui_Dialog):
    """docstring for SettingDialog"""
    def __init__(self, parent=None):
        super(SettingDialog, self).__init__(parent)
        self.setupUi(self)



if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    ui = SettingDialog()
    ui.show()
    sys.exit(app.exec_())
    