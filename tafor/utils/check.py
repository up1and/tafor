import re
import datetime

import requests

from tafor import setting, log
from tafor.models import Session, Tafor

from .validator import REGEX_TAF


def get_remote_message(tt):
    url = setting.value('monitor/db/web_url')
    try:
        response = requests.get(url)
        print(response)
        return response.json()[tt]
    except Exception as e:
        log.error(e)

def make_call(phone_number):
    print('call')


class CheckTAF(object):
    """docstring for CheckTAF"""
    def __init__(self, tt, time=None, remote=False):
        self.tt = tt
        self.time = datetime.datetime.utcnow() if time is None else time
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

        overdued_taf_time = setting.value('monitor/phone/warn_taf_time')
        overdued_taf_time = int(overdued_taf_time) if overdued_taf_time else 30

        self.overdued_time = {
            'FC': datetime.timedelta(minutes=overdued_taf_time), 
            'FT': datetime.timedelta(hours=2, minutes=overdued_taf_time)
        }

        self.db = Session()

        if remote:
            self.message = get_remote_message(self.tt)

    def current_period(self):
        increment = {'FC': datetime.timedelta(minutes=50), 'FT': datetime.timedelta(hours=2, minutes=50)}
        period = self._find_period(increment)
        return self._with_day(period)

    def warn_period(self):
        increment = {'FC': datetime.timedelta(hours=3), 'FT': datetime.timedelta(hours=6)}
        default = {'FC': '0009', 'FT': '0024'} # 00 - 01 时次人肉添加
        find = self._find_period(increment)
        period = find if find else default[self.tt]
        return self._with_day(period)

    def existed_in_local(self, period_with_day=None):
        period_with_day = self.warn_period() if period_with_day is None else period_with_day
        expired = datetime.datetime.utcnow() - datetime.timedelta(hours=24)
        recent = self.db.query(Tafor).filter(Tafor.rpt.contains(period_with_day), Tafor.sent > expired).order_by(Tafor.sent.desc()).first()
        return recent

    def existed_in_remote(self):
        if self.message:
            regex_period = re.compile(REGEX_TAF['common']['period'])
            period = regex_period.match(self.message).groupdict()
            print(period)
            # return self.message[17:23] == self.warn_period()
            return period

    def save(self):
        last = self.db.query(Tafor).filter_by(tt=self.tt).order_by(Tafor.sent.desc()).first()

        if last is None or last.rpt != self.message:  # 如果数据表为空 或 最后一条数据和远程不相等
            item = Tafor(tt=self.tt, rpt=self.message, confirmed=True)
            self.db.add(item)
            self.db.commit()
            return True
        return False

    def confirm(self):
        last = self.db.query(Tafor).filter_by(tt=self.tt).order_by(Tafor.sent.desc()).first()

        if last is not None and last.rpt == self.message:
            last.update().values(confirmed=True)
            self.db.commit()
            return True
        return False

    def overdued(self):
        start_time = self.start_time[self.tt][self.warn_period()[2:]]
        overdued_time = start_time + self.overdued_time[self.tt]
        return overdued_time < self.time

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


def listen(tt):
    taf = CheckTAF(tt, remote=True)
    call_option = setting.value('monitor/phone/phone_warn_taf')
    phone_number = 'phone_number'
    warn = False

    print(taf.existed_in_remote(), taf.existed_in_local())

    if not taf.existed_in_local():
        if taf.existed_in_remote():
            taf.save()
        elif taf.overdued():
            warn = True
    else:
        # 如果本地库有 但没确认 检查远程库
        message = taf.existed_in_local()
        if not message.confirmed and taf.existed_in_remote():
            taf.confirmed()

    return 'listen'
    # if call_option and warn:
    #     make_call(phone_number)


