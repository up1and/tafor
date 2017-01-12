import json
import datetime

from PyQt5 import QtCore, QtGui, QtWidgets

from ui import Ui_widgets_primary, Ui_widgets_becmg, Ui_widgets_tempo, Ui_widgets_recent_item
from validator import Parser

class TAFWidgetsMixin(QtCore.QObject):
    """docstring for TAFWidgetsMixin"""
    def __init__(self):
        super(TAFWidgetsMixin, self).__init__()
        self.regex = Parser.regex_taf['edit']
        self.setting = QtCore.QSettings('Up1and', 'Tafor')

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
        valid_wind = QtGui.QRegExpValidator(QtCore.QRegExp(self.regex['wind']))
        self.wind.setValidator(valid_wind)

        valid_gust = QtGui.QRegExpValidator(QtCore.QRegExp(self.regex['gust']))
        self.gust.setValidator(valid_gust)

        valid_vis = QtGui.QRegExpValidator(QtCore.QRegExp(self.regex['vis']))
        self.vis.setValidator(valid_vis)

        valid_cloud = QtGui.QRegExpValidator(QtCore.QRegExp(self.regex['cloud']))
        self.cloud1.setValidator(valid_cloud)
        self.cloud2.setValidator(valid_cloud)
        self.cloud3.setValidator(valid_cloud)
        self.cb.setValidator(valid_cloud)

        weather1_list = [''] + json.loads(self.setting.value('message/weather1'))
        self.weather1.addItems(weather1_list)

        weather2_list = [''] + json.loads(self.setting.value('message/weather2'))
        self.weather2.addItems(weather2_list)

    def test_message(self):
        pass

    def message(self):
        if self.wind.text():
            wind = ''.join([self.wind.text(), 'G', self.gust.text(), 'MPS']) if self.gust.text() else ''.join([self.wind.text(), 'MPS'])
        else:
            wind = ''

        vis = self.vis.text()
        wx1 = self.weather1.currentText()
        wx2 = self.weather2.currentText()
        cloud1 = self.cloud1.text()
        cloud2 = self.cloud2.text()
        cloud3 = self.cloud3.text()
        cb = self.cb.text()

        if hasattr(self.ui, 'cavok'):
            if self.cavok.isChecked():
                msg_list = [wind, 'CAVOK']
            elif self.skc.isChecked():
                msg_list = [wind, vis, wx1, wx2, 'SKC']
            elif self.nsc.isChecked():
                msg_list = [wind, vis, wx1, wx2, 'NSC']
            else:
                msg_list = [wind, vis, wx1, wx2, cloud1, cloud2, cloud3, cb]
        else:
            msg_list = [wind, vis, wx1, wx2, cloud1, cloud2, cloud3, cb]
        self.msg = ' '.join(msg_list)
        # print(self.msg)



class TAFWidgetsPrimary(QtWidgets.QWidget, Ui_widgets_primary.Ui_Form, TAFWidgetsMixin):

    def __init__(self):
        super(TAFWidgetsPrimary, self).__init__()
        self.setupUi(self)

        self.validate()

        # self.cavok.clicked.connect(self.set_cavok)
        # self.skc.clicked.connect(self.set_skc_nsc)
        # self.nsc.clicked.connect(self.set_skc_nsc)

        self.period.setEnabled(False)

        # self.timer = QtCore.QTimer()
        # self.timer.timeout.connect(self.enbale_next)
        # self.timer.start(1 * 1000)

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
        icao = 'ZJHK'
        timez = self.date.text() + 'Z'
        period = self.period.text()
        tmax = ''.join(['TX', self.tmax.text(), '/', self.tmax_time.text(), 'Z'])
        tmin = ''.join(['TN', self.tmin.text(), '/', self.tmin_time.text(), 'Z'])
        msg_list = ['TAF', icao, timez, period, self.msg, tmax, tmin]
        self.msg = ' '.join(msg_list)
        # print(self.msg)
        return self.msg

    def enbale_next(self):
        # 允许下一步
        self.next = False
        required = (self.date.text(), self.period.text(), self.wind.text(), self.tmax.text(), self.tmax_time.text(), self.tmin.text(), self.tmin_time.text())
        if all(required):
            if self.cavok.isChecked():
                self.next = True
            elif self.vis.text():
                if self.nsc.text() or self.skc.text():
                    self.next = True
                elif self.cloud1.text() or self.cloud2.text() or self.cloud3.text() or self.cb.text() or self.nsc.isChecked():
                    self.next = True
        print(self.next)



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
        if self.prob30.isChecked():
            msg_list = ['PROB30', 'TEMPO', interval, self.msg]
        elif self.prob40.isChecked():
            msg_list = ['PROB40', 'TEMPO', interval, self.msg]
        else:
            msg_list = ['TEMPO', interval, self.msg]
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
        self.rpt.setText(item.rpt)
        if item.confirm_time:
            self.check.setText('√')
        else:
            self.check.setText('×')


class WidgetsClock(WidgetsItem):
    """docstring for WidgetsClock"""
    def __init__(self):
        super(WidgetsClock, self).__init__()

        self.update()

        # 计时器
        self.clock_timer = QtCore.QTimer()
        self.clock_timer.timeout.connect(self.update)
        self.clock_timer.start(1 * 1000)

    def update(self):
        utc = datetime.datetime.utcnow()
        self.groupBox.setTitle('')
        self.send_time.setText('')
        self.rpt.setText('世界时  ' + utc.strftime("%Y-%m-%d %H:%M:%S"))
        self.check.setText('')
        self.groupBox.setStyleSheet("QGroupBox {border: none;}")
        


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    widget = TAFWidgetsPrimary()
    widget.show()
    sys.exit(app.exec_())