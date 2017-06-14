import json
import datetime

from PyQt5 import QtCore, QtGui, QtWidgets

from tafor.widgets.ui import Ui_widget_primary, Ui_widget_becmg, Ui_widget_tempo, Ui_widget_trend, Ui_widget_recent_item
from tafor import setting, log
from tafor.utils import Parser, REGEX_TAF

class EditWidgetBase(QtWidgets.QWidget):
    """docstring for EditWidgetBase"""

    signal_required = QtCore.pyqtSignal(bool)

    def __init__(self):
        super(EditWidgetBase, self).__init__()
        self.regex = REGEX_TAF['edit']
        self.required = False
        # self.one_second_timer = QtCore.QTimer()
        # self.one_second_timer.timeout.connect(self.message)
        # self.one_second_timer.start(1 * 1000)

    def bind_signal(self):

        if hasattr(self, 'cavok'):
            self.cavok.toggled.connect(self.set_cavok)
            self.skc.toggled.connect(self.set_skc)
            self.nsc.toggled.connect(self.set_nsc)
            self.cavok.clicked.connect(self.check_required)
            self.nsc.clicked.connect(self.check_required)
            self.skc.clicked.connect(self.check_required)
        else:
            self.prob30.toggled.connect(self.set_prob30)
            self.prob40.toggled.connect(self.set_prob40)

        self.cloud1.textEdited.connect(lambda:self._upper_text(self.cloud1))
        self.cloud2.textEdited.connect(lambda:self._upper_text(self.cloud2))
        self.cloud3.textEdited.connect(lambda:self._upper_text(self.cloud3))
        self.cb.textEdited.connect(lambda:self._upper_text(self.cb))

        self.wind.textChanged.connect(self.check_required)
        self.vis.textChanged.connect(self.check_required)
        self.cloud1.textChanged.connect(self.check_required)
        self.cloud2.textChanged.connect(self.check_required)
        self.cloud3.textChanged.connect(self.check_required)
        self.cb.textChanged.connect(self.check_required)


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
        cb = self.cb.text() + 'CB' if self.cb.hasAcceptableInput() else None

        clouds = sorted(filter(None, [cloud1, cloud2, cloud3, cb]), key=lambda cloud: int(cloud[3:6]))

        if hasattr(self, 'cavok'):
            if self.cavok.isChecked():
                msg_list = [winds, 'CAVOK']
            elif self.skc.isChecked():
                msg_list = [winds, vis, wx1, wx2, 'SKC']
            elif self.nsc.isChecked():
                msg_list = [winds, vis, wx1, wx2, 'NSC']
            else:
                msg_list = [winds, vis, wx1, wx2] + clouds
        else:
            msg_list = [winds, vis, wx1, wx2] + clouds
        self.msg = ' '.join(filter(None, msg_list))
        # log.debug(self.msg)

    def _upper_text(self, line):
        line.setText(line.text().upper())

    def check_required(self):
        raise NotImplemented

    def clear(self):
        self.wind.clear()
        self.gust.clear()
        self.vis.clear()
        self.weather1.setCurrentIndex(-1)
        self.weather2.setCurrentIndex(-1)
        self.cloud1.clear()
        self.cloud2.clear()
        self.cloud3.clear()
        self.cb.clear()


class TAFWidgetPrimary(EditWidgetBase, Ui_widget_primary.Ui_Form):

    def __init__(self):
        super(TAFWidgetPrimary, self).__init__()
        self.setupUi(self)

        self.validate()
        self.period.setEnabled(False)
        self.ccc.setEnabled(False)
        self.aaa.setEnabled(False)
        self.aaa_cnl.setEnabled(False)

        self.bind_signal()

    def validate(self):
        super(TAFWidgetPrimary, self).validate()

        valid_date = QtGui.QRegExpValidator(QtCore.QRegExp(self.regex['date']))
        self.date.setValidator(valid_date)

        valid_temp = QtGui.QRegExpValidator(QtCore.QRegExp(self.regex['temp']))
        self.tmax.setValidator(valid_temp)
        self.tmin.setValidator(valid_temp)

        valid_temp_hours = QtGui.QRegExpValidator(QtCore.QRegExp(self.regex['hours']))
        self.tmax_time.setValidator(valid_temp_hours)
        self.tmin_time.setValidator(valid_temp_hours)

    def bind_signal(self):
        super(TAFWidgetPrimary, self).bind_signal()

        # 设置下一步按钮
        self.date.textEdited.connect(self.check_required)
        self.period.textChanged.connect(self.check_required)
        self.tmax.textChanged.connect(self.check_required)
        self.tmax_time.textChanged.connect(self.check_required)
        self.tmin.textChanged.connect(self.check_required)
        self.tmin_time.textChanged.connect(self.check_required)

    def check_required(self):
        self.required = False
        must_required = (
                        self.date.hasAcceptableInput(), 
                        self.period.text(), 
                        self.wind.hasAcceptableInput(), 
                        self.tmax.hasAcceptableInput(), 
                        self.tmax_time.hasAcceptableInput(), 
                        self.tmin.hasAcceptableInput(), 
                        self.tmin_time.hasAcceptableInput()
                        )
        one_required = (
                        self.nsc.isChecked(), 
                        self.skc.isChecked(), 
                        self.cloud1.hasAcceptableInput(), 
                        self.cloud2.hasAcceptableInput(), 
                        self.cloud3.hasAcceptableInput(), 
                        self.cb.hasAcceptableInput()
                        )
        
        if all(must_required):
            if self.cavok.isChecked():
                self.required = True
            elif self.vis.hasAcceptableInput() and any(one_required):
                self.required = True

        self.signal_required.emit(self.required)


    def message(self):
        super(TAFWidgetPrimary, self).message()
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

    def clear(self):
        super(TAFWidgetPrimary, self).clear()

        self.becmg1_checkbox.setChecked(False)
        self.becmg2_checkbox.setChecked(False)
        self.becmg3_checkbox.setChecked(False)
        self.tempo1_checkbox.setChecked(False)
        self.tempo2_checkbox.setChecked(False)

        self.cavok.setChecked(False)
        self.skc.setChecked(False)
        self.nsc.setChecked(False)

        self.tmax.clear()
        self.tmax_time.clear()
        self.tmin.clear()
        self.tmin_time.clear()


class TAFWidgetBecmg(EditWidgetBase, Ui_widget_becmg.Ui_Form):

    def __init__(self, name='becmg'):
        super(TAFWidgetBecmg, self).__init__()
        self.setupUi(self)
        self.name.setText(name)

        self.validate()

        # self.cavok.clicked.connect(self.set_cavok)
        # self.skc.clicked.connect(self.set_skc_nsc)
        # self.nsc.clicked.connect(self.set_skc_nsc)

        self.bind_signal()

    def validate(self):
        super(TAFWidgetBecmg, self).validate()

        valid_interval = QtGui.QRegExpValidator(QtCore.QRegExp(self.regex['interval']))
        self.interval.setValidator(valid_interval)

    def bind_signal(self):
        super(TAFWidgetBecmg, self).bind_signal()

        self.interval.textChanged.connect(self.check_required)
        self.weather1.currentIndexChanged.connect(self.check_required)
        self.weather2.currentIndexChanged.connect(self.check_required)

    def message(self):
        super(TAFWidgetBecmg, self).message()
        interval = self.interval.text()
        msg_list = ['BECMG', interval, self.msg]
        self.msg = ' '.join(msg_list)
        # log.debug(self.msg)
        return self.msg

    def check_required(self):
        self.required = False
        one_required = (
                        self.nsc.isChecked(), 
                        self.skc.isChecked(),
                        self.cavok.isChecked(), 
                        self.wind.hasAcceptableInput(), 
                        self.vis.hasAcceptableInput(), 
                        self.weather1.currentText(),
                        self.weather2.currentText(),
                        self.cloud1.hasAcceptableInput(), 
                        self.cloud2.hasAcceptableInput(), 
                        self.cloud3.hasAcceptableInput(), 
                        self.cb.hasAcceptableInput()
                        )

        if self.interval.hasAcceptableInput() and any(one_required):
            self.required = True

        self.signal_required.emit(self.required)

    def clear(self):
        super(TAFWidgetBecmg, self).clear()

        self.interval.clear()

        self.cavok.setChecked(False)
        self.skc.setChecked(False)
        self.nsc.setChecked(False)


class TAFWidgetTempo(EditWidgetBase, Ui_widget_tempo.Ui_Form):

    def __init__(self, name='tempo'):
        super(TAFWidgetTempo, self).__init__()
        self.setupUi(self)
        self.name.setText(name)

        self.validate()

        self.bind_signal()

    def validate(self):
        super(TAFWidgetTempo, self).validate()

        valid_interval = QtGui.QRegExpValidator(QtCore.QRegExp(self.regex['interval']))
        self.interval.setValidator(valid_interval)

    def bind_signal(self):
        super(TAFWidgetTempo, self).bind_signal()

        self.interval.textChanged.connect(self.check_required)
        self.weather1.currentIndexChanged.connect(self.check_required)
        self.weather2.currentIndexChanged.connect(self.check_required)

    def message(self):
        super(TAFWidgetTempo, self).message()
        interval = self.interval.text()
        msg_list = ['TEMPO', interval, self.msg]
        if self.prob30.isChecked():
            msg_list.insert(0, 'PROB30')
        if self.prob40.isChecked():
            msg_list.insert(0, 'PROB40')
        self.msg = ' '.join(msg_list)
        # log.debug(self.msg)
        return self.msg

    def check_required(self):
        self.required = False
        one_required = (
                        self.wind.hasAcceptableInput(), 
                        self.vis.hasAcceptableInput(), 
                        self.weather1.currentText(),
                        self.weather2.currentText(),
                        self.cloud1.hasAcceptableInput(), 
                        self.cloud2.hasAcceptableInput(), 
                        self.cloud3.hasAcceptableInput(), 
                        self.cb.hasAcceptableInput()
                        )

        if self.interval.hasAcceptableInput() and any(one_required):
            self.required = True

        self.signal_required.emit(self.required)

    def clear(self):
        super(TAFWidgetTempo, self).clear()

        self.interval.clear()

        self.prob30.setChecked(False)
        self.prob40.setChecked(False)


class TrendWidget(EditWidgetBase, Ui_widget_trend.Ui_Form):

    def __init__(self):
        super(TrendWidget, self).__init__()
        self.setupUi(self)
        self.validate()
        self.bind_signal()

    def bind_signal(self):
        super(TrendWidget, self).bind_signal()

        self.nosig.toggled.connect(self.set_nosig)
        self.at.toggled.connect(self.set_at)
        self.fm.toggled.connect(self.set_fm)
        self.tl.toggled.connect(self.set_tl)

        self.nosig.clicked.connect(self.check_required)
        self.at.clicked.connect(self.check_required)
        self.fm.clicked.connect(self.check_required)
        self.tl.clicked.connect(self.check_required)

    def validate(self):
        super(TrendWidget, self).validate()

        valid_period = QtGui.QRegExpValidator(QtCore.QRegExp(self.regex['interval']))
        self.period.setValidator(valid_period)

    def set_nosig(self, checked):
        boolean = not checked

        self.group_prefix.setEnabled(boolean)
        self.group_type.setEnabled(boolean)

        self.period.setEnabled(boolean)
        self.wind.setEnabled(boolean)
        self.gust.setEnabled(boolean)
        self.vis.setEnabled(boolean)
        self.weather1.setEnabled(boolean)
        self.weather2.setEnabled(boolean)
        self.cloud1.setEnabled(boolean)
        self.cloud2.setEnabled(boolean)
        self.cloud3.setEnabled(boolean)
        self.cb.setEnabled(boolean)

        self.cavok.setEnabled(boolean)
        self.skc.setEnabled(boolean)
        self.nsc.setEnabled(boolean)


    def set_at(self, checked):
        if checked:
            self.fm.setChecked(False)
            self.tl.setChecked(False)
            self.period.setEnabled(True)
        else:
            self.period.setEnabled(False)

    def set_fm(self, checked):
        if checked:
            self.at.setChecked(False)
            self.tl.setChecked(False)
            self.period.setEnabled(True)
        else:
            self.period.setEnabled(False)

    def set_tl(self, checked):
        if checked:
            self.fm.setChecked(False)
            self.at.setChecked(False)
            self.period.setEnabled(True)
        else:
            self.period.setEnabled(False)

    def check_required(self):
        self.required = False
        one_required = (
            self.wind.hasAcceptableInput(), 
            self.vis.hasAcceptableInput(), 
            self.weather1.currentText(),
            self.weather2.currentText(),
            self.cloud1.hasAcceptableInput(), 
            self.cloud2.hasAcceptableInput(), 
            self.cloud3.hasAcceptableInput(), 
            self.cb.hasAcceptableInput()
        )

        prefix_checked = (
            self.at.isChecked(),
            self.fm.isChecked(),
            self.tl.isChecked()
        )

        if self.nosig.isChecked():
            self.required = True

        if any(one_required):
            if any(prefix_checked):
                if self.period.hasAcceptableInput():
                    self.required = True
            else:
                self.required = True

        self.signal_required.emit(self.required)


class RecentItem(QtWidgets.QWidget, Ui_widget_recent_item.Ui_Form):
    """docstring for RecentItem"""
    def __init__(self):
        super(RecentItem, self).__init__()
        self.setupUi(self)

    def set_item(self, item):
        self.groupBox.setTitle(item.tt)
        self.send_time.setText(item.sent.strftime("%Y-%m-%d %H:%M:%S"))
        rpt_with_head = filter(None, [item.head, item.rpt])
        self.rpt.setText('\n'.join(rpt_with_head))
        if item.confirmed:
            self.check.setText('√')
        else:
            self.check.setText('×')
        