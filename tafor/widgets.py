from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

from ui import Ui_widgets_primary, Ui_widgets_becmg, Ui_widgets_tempo

class TAFWidgetsMixin(object):
    """docstring for TAFWidgetsMixin"""
    def __init__(self):
        super(TAFWidgetsMixin, self).__init__()


class TAFWidgetsPrimary(QWidget, Ui_widgets_primary.Ui_Form):

    def __init__(self):
        super(TAFWidgetsPrimary, self).__init__()
        print('TAFWidgetsPrimary')


if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    ui = TAFWidgetsPrimary()
    ui.show()
    sys.exit(app.exec_())