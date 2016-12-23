# -*- coding: utf-8 -*-

from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

from ui import Ui_taf


class TAFWizard(QDialog, Ui_taf.Ui_TAF):
    """
    主窗口
    """
    def __init__(self, parent=None):
        """
        初始化主窗口
        """
        QDialog.__init__(self, parent)
        self.setupUi(self)
        self.becmg1_frame.hide()
        self.becmg2_frame.hide()
        self.becmg3_frame.hide()
        self.tempo1_frame.hide()
        self.tempo2_frame.hide()

        # self.connect(self.becmg1_checkbox, SIGNAL("toggled(bool)"), self.becmg1_frame, SLOT("setVisible(bool)"))
        # self.connect(self.becmg2_checkbox, SIGNAL("toggled(bool)"), self.becmg2_frame, SLOT("setVisible(bool)"))
        # self.connect(self.becmg3_checkbox, SIGNAL("toggled(bool)"), self.becmg3_frame, SLOT("setVisible(bool)"))

        # self.connect(self.tempo1_checkbox, SIGNAL("toggled(bool)"), self.tempo1_frame, SLOT("setVisible(bool)"))
        # self.connect(self.tempo2_checkbox, SIGNAL("toggled(bool)"), self.tempo2_frame, SLOT("setVisible(bool)"))



if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    ui = TAFWizard()
    ui.show()
    sys.exit(app.exec_())
    
