from PyQt5 import QtCore, QtGui, QtWidgets

from ui import Ui_widgets_primary, Ui_widgets_becmg, Ui_widgets_tempo
from validator import Parser

class TAFWidgetsMixin(QtCore.QObject):
    """docstring for TAFWidgetsMixin"""
    def __init__(self):
        super(TAFWidgetsMixin, self).__init__()
        self.regex = Parser.regex_taf['edit']

        # self.one_second_timer = QtCore.QTimer()
        # self.one_second_timer.timeout.connect(self.message)
        # self.one_second_timer.start(1 * 1000)


    def set_cavok(self, checked):
        if checked:
            self.ui.vis.clear()
            self.ui.vis.setEnabled(False)
            self.ui.weather1.setEnabled(False)
            self.ui.weather1.clear()
            self.ui.weather2.setEnabled(False)
            self.ui.weather2.clear()
            self.ui.cloud1.clear()
            self.ui.cloud1.setEnabled(False)
            self.ui.cloud2.clear()
            self.ui.cloud2.setEnabled(False)
            self.ui.cloud3.clear()
            self.ui.cloud3.setEnabled(False)
            self.ui.cb.clear()
            self.ui.cb.setEnabled(False)
        else:
            self.ui.vis.setEnabled(True)
            self.ui.weather1.setEnabled(True)
            self.ui.weather2.setEnabled(True)
            self.ui.cloud1.setEnabled(True)
            self.ui.cloud2.setEnabled(True)
            self.ui.cloud3.setEnabled(True)
            self.ui.cb.setEnabled(True)

    def set_skc_nsc(self, checked):
        if checked:
            self.ui.cloud1.clear()
            self.ui.cloud1.setEnabled(False)
            self.ui.cloud2.clear()
            self.ui.cloud2.setEnabled(False)
            self.ui.cloud3.clear()
            self.ui.cloud3.setEnabled(False)
            self.ui.cb.clear()
            self.ui.cb.setEnabled(False)
        else:
            self.ui.cloud1.setEnabled(True)
            self.ui.cloud2.setEnabled(True)
            self.ui.cloud3.setEnabled(True)
            self.ui.cb.setEnabled(True)

    def validate(self):
        valid_wind = QtGui.QRegExpValidator(QtCore.QRegExp(self.regex['wind']))
        self.ui.wind.setValidator(valid_wind)

        valid_gust = QtGui.QRegExpValidator(QtCore.QRegExp(self.regex['gust']))
        self.ui.gust.setValidator(valid_gust)

        valid_vis = QtGui.QRegExpValidator(QtCore.QRegExp(self.regex['vis']))
        self.ui.vis.setValidator(valid_vis)

        valid_cloud = QtGui.QRegExpValidator(QtCore.QRegExp(self.regex['cloud']))
        self.ui.cloud1.setValidator(valid_cloud)
        self.ui.cloud2.setValidator(valid_cloud)
        self.ui.cloud3.setValidator(valid_cloud)
        self.ui.cb.setValidator(valid_cloud)

        # valid_temp = QtGui.QRegExpValidator(QRegExp(regex['temp']))
        # self.taf_temp_max.setValidator(valid_temp)
        # self.taf_temp_min.setValidator(valid_temp)

        wx1 = ['', 'BR', 'FG', 'SA', 'DU', 'HZ', 'FU', 'VA', 'SQ', 'PO', 'FC', 'TS', 'FZFG', 'BLSN', 'BLSA', 'BLDU', 'DRSN', 'DRSA', 'DRDU', 'MIFG', 'BCFG', 'PRFG', 'NSW']
        self.ui.weather1.addItems(wx1)

        wx2 = ['', 'DZ', 'RA', 'SN', 'SG', 'PL', 'DS', 'SS', 'TSRA', 'TSSN', 'TSPL', 'TSGR', 'TSGS', 'SHRA', 'SHSN', 'SHGR', 'SHGS', 'FZRA', 'FZDZ']
        self.ui.weather2.addItems(wx2)

    def test_message(self):
        pass

    def message(self):
        if self.ui.wind.text():
            wind = ''.join([self.ui.wind.text(), 'G', self.ui.gust.text(), 'MPS']) if self.ui.gust.text() else ''.join([self.ui.wind.text(), 'MPS'])
        else:
            wind = ''

        vis = self.ui.vis.text()
        wx1 = self.ui.weather1.currentText()
        wx2 = self.ui.weather2.currentText()
        cloud1 = self.ui.cloud1.text()
        cloud2 = self.ui.cloud2.text()
        cloud3 = self.ui.cloud3.text()
        cb = self.ui.cb.text()

        if hasattr(self.ui, 'cavok'):
            if self.ui.cavok.isChecked():
                msg_list = [wind, 'CAVOK']
            elif self.ui.skc.isChecked():
                msg_list = [wind, vis, wx1, wx2, 'SKC']
            elif self.ui.nsc.isChecked():
                msg_list = [wind, vis, wx1, wx2, 'NSC']
            else:
                msg_list = [wind, vis, wx1, wx2, cloud1, cloud2, cloud3, cb]
        else:
            msg_list = [wind, vis, wx1, wx2, cloud1, cloud2, cloud3, cb]
        self.msg = ' '.join(msg_list)
        self.msg = ' '.join(self.msg.split())
        # print(self.msg)



class TAFWidgetsPrimary(QtWidgets.QWidget, TAFWidgetsMixin):

    def __init__(self):
        super(TAFWidgetsPrimary, self).__init__()
        self.ui = Ui_widgets_primary.Ui_Form()
        self.ui.setupUi(self)

        self.validate()

        self.ui.cavok.clicked.connect(self.set_cavok)
        self.ui.skc.clicked.connect(self.set_skc_nsc)
        self.ui.nsc.clicked.connect(self.set_skc_nsc)


    def validate(self):
        super(TAFWidgetsPrimary, self).validate()

        valid_date = QtGui.QRegExpValidator(QtCore.QRegExp(self.regex['date']))
        self.ui.date.setValidator(valid_date)

        valid_temp = QtGui.QRegExpValidator(QtCore.QRegExp(self.regex['temp']))
        self.ui.tmax.setValidator(valid_temp)
        self.ui.tmin.setValidator(valid_temp)

        valid_temp_hours = QtGui.QRegExpValidator(QtCore.QRegExp(self.regex['hours']))
        self.ui.tmax_time.setValidator(valid_temp_hours)
        self.ui.tmin_time.setValidator(valid_temp_hours)

    def message(self):
        super(TAFWidgetsPrimary, self).message()
        icao = 'ZJHK'
        timez = self.ui.date.text() + 'Z'
        period = self.ui.period.text()
        msg_list = ['TAF', icao, timez, period, self.msg]
        self.msg = ' '.join(msg_list)
        # print(self.msg)



class TAFWidgetsBecmg(QtWidgets.QWidget, TAFWidgetsMixin):

    def __init__(self, name='becmg'):
        super(TAFWidgetsBecmg, self).__init__()
        self.ui = Ui_widgets_becmg.Ui_Form()
        self.ui.setupUi(self)
        self.ui.name.setText(name)

        self.validate()

        self.ui.cavok.clicked.connect(self.set_cavok)
        self.ui.skc.clicked.connect(self.set_skc_nsc)
        self.ui.nsc.clicked.connect(self.set_skc_nsc)

        self.message()


    def message(self):
        super(TAFWidgetsBecmg, self).message()
        interval = self.ui.interval.text()
        msg_list = ['BECMG', interval, self.msg]
        self.msg = ' '.join(msg_list)
        # print(self.msg)


class TAFWidgetsTempo(QtWidgets.QWidget, TAFWidgetsMixin):

    def __init__(self, name='tempo'):
        super(TAFWidgetsTempo, self).__init__()
        self.ui = Ui_widgets_tempo.Ui_Form()
        self.ui.setupUi(self)
        self.ui.name.setText(name)

        self.validate()

    def message(self):
        super(TAFWidgetsTempo, self).message()
        interval = self.ui.interval.text()
        if self.ui.prob30.isChecked():
            msg_list = ['PROB30', 'TEMPO', interval, self.msg]
        elif self.ui.prob40.isChecked():
            msg_list = ['PROB40', 'TEMPO', interval, self.msg]
        else:
            msg_list = ['TEMPO', interval, self.msg]
        self.msg = ' '.join(msg_list)
        # print(self.msg)


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    widget = TAFWidgetsPrimary()
    widget.show()
    sys.exit(app.exec_())