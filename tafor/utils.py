import re
import datetime

from PyQt5 import QtCore

from validator import Parser


class TAF(object):
    """
    检查预报报文
    _period() 判断该时期要发的报文 return string
    """

    def __init__(self, tt, time):
        self.now = time
        start_of_the_day = datetime.datetime(self.now.year, self.now.month, self.now.day)
        self.tt = tt.upper()
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
        self.interval_time = {'FC': datetime.timedelta(hours=3), 'FT': datetime.timedelta(hours=6)}

    def get_period(self):
        # 盲区 00 - 01 人肉添加
        default_period = {'FC': '0009', 'FT': '0024'}
        period = default_period[self.tt]
        for key,value in self.start_time[self.tt].items():
            if value < self.now < value + self.interval_time[self.tt]:
                period = key
                return period
        return period

def current_taf_period(tt, time):
    start_of_the_day = datetime.datetime(time.year, time.month, time.day)
    tt = tt.upper()

    start_time= dict()
    start_time['FC'] = {
                '0312': start_of_the_day + datetime.timedelta(hours=1),
                '0615': start_of_the_day + datetime.timedelta(hours=4),
                '0918': start_of_the_day + datetime.timedelta(hours=7),
                '1221': start_of_the_day + datetime.timedelta(hours=10),
                '1524': start_of_the_day + datetime.timedelta(hours=13),
                '1803': start_of_the_day + datetime.timedelta(hours=16),
                '2106': start_of_the_day + datetime.timedelta(hours=19),
                '0009': start_of_the_day + datetime.timedelta(hours=22),
                }
    start_time['FT'] = {
                '0606': start_of_the_day + datetime.timedelta(hours=1),
                '1212': start_of_the_day + datetime.timedelta(hours=7),
                '1818': start_of_the_day + datetime.timedelta(hours=13),
                '0024': start_of_the_day + datetime.timedelta(hours=19),
                }
    interval_time = {'FC': datetime.timedelta(hours=3), 'FT': datetime.timedelta(hours=6)}
    default_period = {'FC': '0009', 'FT': '0024'}
    period = default_period[tt]
    for key,value in start_time[tt].items():
        if value < time < value + interval_time[tt]:
            period = key
            return period
    return period


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
        self._rpt_head()

    def _rpt_head(self):
        intelligence = self.setting.value('message/intelligence')
        icao = self.setting.value('message/icao')

        timez_regex = Parser.regex_taf['common']['timez']
        self.aftn_time = re.search(timez_regex, self.message['rpt']).group()[0:6]

        self.rpt_head = ' '.join([self.message['tt'] + intelligence, icao, self.aftn_time])

    def rpt_with_head(self):
        return '\n'.join([self.rpt_head, self.message['rpt']])

    def raw(self):
        channel = self.setting.value('communication/other/channel')
        number = int(self.setting.value('communication/other/number'))
        send_address = self.setting.value('communication/address/' + self.cls)
        user_address = self.setting.value('communication/other/user_addr')

        addresses = self.divide_address(send_address)

        # 定值
        self.aftn_time = ' '.join([self.aftn_time, user_address])
        self.aftn_nnnn = 'NNNN'

        aftn_message = []
        for address in addresses:
            self.aftn_zczc = ' '.join(['ZCZC', channel + str(number).zfill(4)])
            self.aftn_adress = ' '.join(['GG'] + address)
            items = [self.aftn_zczc, self.aftn_adress, self.aftn_time, self.rpt_head, self.message['rpt'], self.aftn_nnnn]
            aftn_message.append('\n'.join(items))
            number += 1

        self.setting.setValue('communication/other/number', str(number))
        
        return aftn_message


    def divide_address(self, address):
        items = address.split()
        return chunks(items, 7)


if __name__ == '__main__':
    # period = current_taf_period('FT', datetime.datetime.utcnow())
    # print(period)

    message = dict()
    message['rpt'] = 'TAF ZJHK 150726Z 150918 03003G10MPS 1600 BR OVC040 BECMG 1112 4000 BR='
    message['tt'] = 'FC'
    aftn = AFTNMessage(message)
    # print(aftn.rpt_with_head())
    for i in aftn.raw():
        print(i)
        print('   ')