import datetime

from PyQt5 import QtCore
from models import Session, Tafor
from validator import Parser

class TAFPeriod(object):
    """docstring for TAFPeriod"""
    def __init__(self, tt, time=datetime.datetime.utcnow()):
        super(TAFPeriod, self).__init__()
        self.tt = tt
        self.time = time
        start_of_the_day = datetime.datetime(self.time.year, self.time.month, self.time.day)
        self.start_time= dict()
        self.start_time['FC'] = {
                    '0312': start_of_the_day + datetime.timedelta(hours=1),
                    '0615': start_of_the_day + datetime.timedelta(hours=4),
                    '0918': start_of_the_day + datetime.timedelta(hours=7),
                    '1221': start_of_the_day + datetime.timedelta(hours=10),
                    '1524': start_of_the_day + datetime.timedelta(hours=13),
                    '1803': start_of_the_day + datetime.timedelta(hours=16),
                    '2106': start_of_the_day + datetime.timedelta(hours=19),
                    '0009': start_of_the_day + datetime.timedelta(hours=22),
                    }
        self.start_time['FT'] = {
                    '0606': start_of_the_day + datetime.timedelta(hours=1),
                    '1212': start_of_the_day + datetime.timedelta(hours=7),
                    '1818': start_of_the_day + datetime.timedelta(hours=13),
                    '0024': start_of_the_day + datetime.timedelta(hours=19),
                    }
        self.db = Session()

    def current(self):
        increment = {'FC': datetime.timedelta(minutes=50), 'FT': datetime.timedelta(hours=2, minutes=50)}
        period = self._find_period(increment)
        return self._with_day(period)

    def is_existed(self):
        time_limit = datetime.datetime.utcnow() - datetime.timedelta(hours=24)
        recent = self.db.query(Tafor).filter(Tafor.rpt.contains(self.warn()), Tafor.send_time > time_limit).all()
        return recent

    def warn(self):
        increment = {'FC': datetime.timedelta(hours=3), 'FT': datetime.timedelta(hours=6)}
        default = {'FC': '0009', 'FT': '0024'} # 00 - 01 时次人肉添加
        find = self._find_period(increment)
        period = find if find else default[self.tt]
        return self._with_day(period)

    def _find_period(self, increment):
        for key, start in self.start_time[self.tt].items():
            if start <= self.time <= start + increment[self.tt]:
                period = key
                return period

    def _with_day(self, period):
        if period is None:
            return None
        else:
            time = self.time + datetime.timedelta(days=1) if period in ('0009', '0024') else self.time
            return str(time.day).zfill(2) + period


def chunks(lists, n):
    """Yield successive n-sized chunks from lists."""
    for i in range(0, len(lists), n):
        yield lists[i:i + n]


class AFTNMessage(object):
    """docstring for AFTNMessage"""
    def __init__(self, message, cls='taf'):
        super(AFTNMessage, self).__init__()
        self.message = message
        self.cls = cls
        self.setting = QtCore.QSettings('Up1and', 'Tafor')

    def raw(self):
        channel = self.setting.value('communication/other/channel')
        number = int(self.setting.value('communication/other/number'))
        send_address = self.setting.value('communication/address/' + self.cls)
        user_address = self.setting.value('communication/other/user_addr')

        addresses = self.divide_address(send_address)
        # 第三项为时间组
        time = self.message['head'].split()[2]

        # 定值
        self.aftn_time = ' '.join([time, user_address])
        self.aftn_nnnn = 'NNNN'

        aftn_message = []
        for address in addresses:
            self.aftn_zczc = ' '.join(['ZCZC', channel + str(number).zfill(4)])
            self.aftn_adress = ' '.join(['GG'] + address)
            items = [self.aftn_zczc, self.aftn_adress, self.aftn_time, self.message['head'], self.message['rpt'], self.aftn_nnnn]
            aftn_message.append('\n'.join(items))
            number += 1

        self.setting.setValue('communication/other/number', str(number))
        
        return aftn_message


    def divide_address(self, address):
        items = address.split()
        return chunks(items, 7)


if __name__ == '__main__':
    # taf = TAFPeriod('FT')
    # print(taf.current())

    message = dict()
    message['rpt'] = 'TAF ZJHK 150726Z 150918 03003G10MPS 1600 BR OVC040 BECMG 1112 4000 BR='
    message['head'] = 'FCCI35 ZJHK 150726'
    aftn = AFTNMessage(message)
    # print(aftn.rpt_with_head())
    for i in aftn.raw():
        print(i)
        print('   ')