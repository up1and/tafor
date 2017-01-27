import json
import datetime

from PyQt5 import QtCore, QtGui, QtWidgets

from ui import Ui_widgets_primary, Ui_widgets_becmg, Ui_widgets_tempo, Ui_widgets_recent_item
from config import setting
from utils import Parser, REGEX_TAF

class TAFWidgetsMixin(QtCore.QObject):
    """docstring for TAFWidgetsMixin"""
    def __init__(self):
        super(TAFWidgetsMixin, self).__init__()
        self.regex = REGEX_TAF['edit']

        # self.one_second_timer = QtCore.QTimer()
        # self.one_second_timer.timeout.connect(self.message)
        # self.one_second_timer.start(1 * 1000)

    def bind_signal(self):

        if hasattr(self, 'cavok'):
            self.cavok.toggled.connect(self.set_cavok)
            self.skc.toggled.connect(self.set_skc)
            self.nsc.toggled.connect(self.set_nsc)
        else:
            self.prob30.toggled.connect(self.set_prob30)
            self.prob40.toggled.connect(self.set_prob40)

        self.cloud1.textEdited.connect(lambda:self._upper_text(self.cloud1))
        self.cloud2.textEdited.connect(lambda:self._upper_text(self.cloud2))
        self.cloud3.textEdited.connect(lambda:self._upper_text(self.cloud3))
        self.cb.textEdited.connect(lambda:self._upper_text(self.cb))


    def clouds(self, enbale):
        if enbale:
            self.cloud1.setEnabled(True)
            self.cloud2.setEnabled(True)
            self.cloud3.setEnabled(True)
            self.cb.setEnabled(True)
        else:
            self.cloud1.clear()
            self.cloud1.setEnabled(False)
            self.cloud2.clear()
            self.cloud2.setEnabled(False)
            self.cloud3.clear()
            self.cloud3.setEnabled(False)
            self.cb.clear()
            self.cb.setEnabled(False)


    def set_cavok(self, checked):
        if checked:
            self.skc.setChecked(False)
            self.nsc.setChecked(False)

            self.vis.clear()
            self.vis.setEnabled(False)
            self.weather1.setEnabled(False)
            self.weather2.setEnabled(False)
            self.clouds(False)
        else:
            self.vis.setEnabled(True)
            self.weather1.setEnabled(True)
            self.weather2.setEnabled(True)
            self.clouds(True)

    def set_skc(self, checked):
        if checked:
            self.cavok.setChecked(False)
            self.nsc.setChecked(False)
            self.clouds(False)
        else:
            self.clouds(True)

    def set_nsc(self, checked):
        if checked:
            self.cavok.setChecked(False)
            self.skc.setChecked(False)
            self.clouds(False)
        else:
            self.clouds(True)

    def set_prob30(self, checked):
        if checked:
            self.prob40.setChecked(False)
        
    def set_prob40(self, checked):
        if checked:
            self.prob30.setChecked(False)

    def validate(self):
        self.valid_wind = QtGui.QRegExpValidator(QtCore.QRegExp(self.regex['wind']))
        self.wind.setValidator(self.valid_wind)

        valid_gust = QtGui.QRegExpValidator(QtCore.QRegExp(self.regex['gust']))
        self.gust.setValidator(valid_gust)

        valid_vis = QtGui.QRegExpValidator(QtCore.QRegExp(self.regex['vis']))
        self.vis.setValidator(valid_vis)

        valid_cloud = QtGui.QRegExpValidator(QtCore.QRegExp(self.regex['cloud'], QtCore.Qt.CaseInsensitive))
        self.cloud1.setValidator(valid_cloud)
        self.cloud2.setValidator(valid_cloud)
        self.cloud3.setValidator(valid_cloud)
        self.cb.setValidator(valid_cloud)

        weather1 = setting.value('message/weather1')
        weather1_list = [''] + json.loads(weather1) if weather1 else ['']
        self.weather1.addItems(weather1_list)

        weather2 = setting.value('message/weather2')
        weather2_list = [''] + json.loads(weather2) if weather1 else ['']
        self.weather2.addItems(weather2_list)

    def message(self):
        wind = self.wind.text() if self.wind.hasAcceptableInput() else None
        gust = self.gust.text() if self.gust.hasAcceptableInput() else None

        if wind:
            winds = ''.join([wind, 'G', gust, 'MPS']) if gust else ''.join([wind, 'MPS'])
        else:
            winds = None

        vis = self.vis.text() if self.vis.hasAcceptableInput() else None
        wx1 = self.weather1.currentText()
        wx2 = self.weather2.currentText()
        cloud1 = self.cloud1.text() if self.cloud1.hasAcceptableInput() else None
        cloud2 = self.cloud2.text() if self.cloud2.hasAcceptableInput() else None
        cloud3 = self.cloud3.text() if self.cloud3.hasAcceptableInput() else None
        cb = self.cb.text() if self.cb.hasAcceptableInput() else None

        if hasattr(self, 'cavok'):
            if self.cavok.isChecked():
                msg_list = [winds, 'CAVOK']
            elif self.skc.isChecked():
                msg_list = [winds, vis, wx1, wx2, 'SKC']
            elif self.nsc.isChecked():
                msg_list = [winds, vis, wx1, wx2, 'NSC']
            else:
                msg_list = [winds, vis, wx1, wx2, cloud1, cloud2, cloud3, cb]
        else:
            msg_list = [winds, vis, wx1, wx2, cloud1, cloud2, cloud3, cb]
        self.msg = ' '.join(filter(None, msg_list))
        # print(self.msg)

    def _upper_text(self, line):
        line.setText(line.text().upper())



class TAFWidgetsPrimary(QtWidgets.QWidget, Ui_widgets_primary.Ui_Form, TAFWidgetsMixin):

    def __init__(self):
        super(TAFWidgetsPrimary, self).__init__()
        self.setupUi(self)

        self.validate()
        self.period.setEnabled(False)
        self.ccc.setEnabled(False)
        self.aaa.setEnabled(False)
        self.aaa_cnl.setEnabled(False)

        self.bind_signal()

    def validate(self):
        super(TAFWidgetsPrimary, self).validate()

        valid_date = QtGui.QRegExpValidator(QtCore.QRegExp(self.regex['date']))
        self.date.setValidator(valid_date)

        valid_temp = QtGui.QRegExpValidator(QtCore.QRegExp(self.regex['temp']))
        self.tmax.setValidator(valid_temp)
        self.tmin.setValidator(valid_temp)

        valid_temp_hours = QtGui.QRegExpValidator(QtCore.QRegExp(self.regex['hours']))
        self.tmax_time.setValidator(valid_temp_hours)
        self.tmin_time.setValidator(valid_temp_hours)

    def message(self):
        super(TAFWidgetsPrimary, self).message()
        amd = 'AMD' if self.amd.isChecked() else ''
        cor = 'COR' if self.cor.isChecked() else ''
        icao = setting.value('message/icao')
        timez = self.date.text() + 'Z'
        period = self.period.text()
        tmax = ''.join(['TX', self.tmax.text(), '/', self.tmax_time.text(), 'Z'])
        tmin = ''.join(['TN', self.tmin.text(), '/', self.tmin_time.text(), 'Z'])
        msg_list = ['TAF', amd, cor, icao, timez, period, self.msg, tmax, tmin]
        self.msg = ' '.join(filter(None, msg_list))
        return self.msg

    def head(self):
        intelligence = setting.value('message/intelligence')
        icao = setting.value('message/icao')
        time = self.date.text()
        tt = ''
        if self.fc.isChecked():
            tt = 'FC'
        elif self.ft.isChecked():
            tt = 'FT'

        ccc = self.ccc.text() if self.cor.isChecked() else None
        aaa = self.aaa.text() if self.amd.isChecked() else None
        aaa_cnl = self.aaa_cnl.text() if self.cnl.isChecked() else None
        msg_list = [tt + intelligence, icao, time, ccc, aaa, aaa_cnl]
        return ' '.join(filter(None, msg_list))



class TAFWidgetsBecmg(QtWidgets.QWidget, Ui_widgets_becmg.Ui_Form, TAFWidgetsMixin):

    def __init__(self, name='becmg'):
        super(TAFWidgetsBecmg, self).__init__()
        self.setupUi(self)
        self.name.setText(name)

        self.validate()

        # self.cavok.clicked.connect(self.set_cavok)
        # self.skc.clicked.connect(self.set_skc_nsc)
        # self.nsc.clicked.connect(self.set_skc_nsc)

        self.bind_signal()

    def validate(self):
        super(TAFWidgetsBecmg, self).validate()

        valid_interval = QtGui.QRegExpValidator(QtCore.QRegExp(self.regex['interval']))
        self.interval.setValidator(valid_interval)

    def message(self):
        super(TAFWidgetsBecmg, self).message()
        interval = self.interval.text()
        msg_list = ['BECMG', interval, self.msg]
        self.msg = ' '.join(msg_list)
        # print(self.msg)
        return self.msg


class TAFWidgetsTempo(QtWidgets.QWidget, Ui_widgets_tempo.Ui_Form, TAFWidgetsMixin):

    def __init__(self, name='tempo'):
        super(TAFWidgetsTempo, self).__init__()
        self.setupUi(self)
        self.name.setText(name)

        self.validate()

        self.bind_signal()

    def message(self):
        super(TAFWidgetsTempo, self).message()
        interval = self.interval.text()
        msg_list = ['TEMPO', interval, self.msg]
        if self.prob30.isChecked():
            msg_list.insert(0, 'PROB30')
        if self.prob40.isChecked():
            msg_list.insert(0, 'PROB40')
        self.msg = ' '.join(msg_list)
        # print(self.msg)
        return self.msg

class WidgetsItem(QtWidgets.QWidget, Ui_widgets_recent_item.Ui_Form):
    """docstring for WidgetsItem"""
    def __init__(self):
        super(WidgetsItem, self).__init__()
        self.setupUi(self)

    def set_item(self, item):
        self.groupBox.setTitle(item.tt)
        self.send_time.setText(item.send_time.strftime("%Y-%m-%d %H:%M:%S"))
        rpt_with_head = filter(None, [item.head, item.rpt])
        self.rpt.setText('\n'.join(rpt_with_head))
        if item.confirm_time:
            self.check.setText('√')
        else:
            self.check.setText('×')
        


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    widget = TAFWidgetsPrimary()
    widget.show()
    sys.exit(app.exec_())