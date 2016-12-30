from PyQt5 import QtCore, QtGui, QtWidgets

from ui import Ui_widgets_primary, Ui_widgets_becmg, Ui_widgets_tempo

class TAFWidgetsMixin(object):
    """docstring for TAFWidgetsMixin"""
    def __init__(self):
        super(TAFWidgetsMixin, self).__init__()


class TAFWidgetsPrimary(Ui_widgets_primary.Ui_Form, TAFWidgetsMixin):

    def __init__(self):
        super(TAFWidgetsPrimary, self).__init__()
        print('TAFWidgetsPrimary')


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    Form = QtWidgets.QWidget()
    ui = TAFWidgetsPrimary()
    ui.setupUi(Form)
    Form.show()
    sys.exit(app.exec_())