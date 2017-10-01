import re
import datetime

import requests

from PyQt5.QtCore import QObject

from tafor import setting, log
from tafor.models import Session, Tafor, Metar

from tafor.utils.validator import REGEX_TAF


def remote_message():
    url = setting.value('monitor/db/web_api_url')
    try:
        r = requests.get(url)
        if r.status_code == 200:
            return r.json()
        else:
            log.warn('GET {} 404 Not Found'.format(url))

    except requests.exceptions.ConnectionError:
        log.warn('GET {} 408 Request Timeout'.format(url))

    except Exception as e:
        log.error(e, exc_info=True)

    return {}

def make_call(phone_number):
    url = setting.value('monitor/phone/call_service_url')
    token = setting.value('monitor/phone/call_service_token')
    try:
        r = requests.post(url, data={'token': token, 'phone_number': phone_number})
        if r.status_code == 201:
            log.info('call {} success'.format(phone_number))
            return r.json()
        else:
            log.warn('call {} failure'.format(phone_number))

    except requests.exceptions.ConnectionError:
        log.warn('POST {} 408 Request Timeout'.format(url))

    except Exception as e:
        log.error(e, exc_info=True)

def call_service():
    url = setting.value('monitor/phone/call_service_url')
    try:
        r = requests.get(url)
        return r.status_code == 405
    except Exception:
        pass

def format_timez(message):
    try:
        match = re.search(REGEX_TAF['common']['timez'], message)
        timez = match.groupdict()
        utc =  datetime.datetime.utcnow()
        created = datetime.datetime(utc.year, utc.month, int(timez['day']), int(timez['hour']), int(timez['minute']))
        return created
    except Exception as e:
        log.error(e, exc_info=True)
        created = datetime.datetime.utcnow()
        return created


class CheckTAF(QObject):
    """docstring for CheckTAF"""
    def __init__(self, tt, remote=None, time=None):
        super(CheckTAF, self).__init__()
        self.tt = tt
        self.remote = remote
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
        if self.remote:
            regex_period = re.compile(REGEX_TAF['common']['period'])
            period = regex_period.search(self.remote).group()
            return period == self.warn_period()

    def save(self):
        last = self.db.query(Tafor).filter_by(tt=self.tt).order_by(Tafor.sent.desc()).first()

        if last is None or last.rpt_inline != self.remote:  # 如果数据表为空 或 最后一条数据和远程不相等
            item = Tafor(tt=self.tt, rpt=self.remote, confirmed=self.time)
            self.db.add(item)
            self.db.commit()
            log.info('Save {} {}'.format(self.tt, self.remote))

    def confirm(self):
        last = self.db.query(Tafor).filter_by(tt=self.tt).order_by(Tafor.sent.desc()).first()

        if last is not None and last.rpt_inline == self.remote:
            last.confirmed = self.time
            self.db.commit()
            log.info('Confirm {} {}'.format(self.tt, self.remote))

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
            time = self.time + datetime.timedelta(days=1) if period in ('0009', '0024') and self.time.hour != 0 else self.time
            return str(time.day).zfill(2) + period


class CheckMetar(object):
    """docstring for CheckMetar"""
    def __init__(self, tt, remote):
        self.tt = tt
        self.remote = remote
        self.db = Session()

    def save(self):
        last = self.db.query(Metar).filter_by(tt=self.tt).order_by(Metar.created.desc()).first()
        
        if last is None or last.rpt != self.remote:
            item = Metar(tt=self.tt, rpt=self.remote, created=format_timez(self.remote))
            self.db.add(item)
            self.db.commit()
            log.info('Save {} {}'.format(self.tt, self.remote))


class Listen(object):
    def __init__(self, ctx):
        self.ctx = ctx

    def __call__(self, tt):
        self.tt = tt
        self.remote = self.ctx.message.get(self.tt, None)
        method = {'FC': 'taf', 'FT': 'taf', 'SA': 'metar', 'SP': 'metar'}
        return getattr(self.__class__, method[self.tt])(self)

    def taf(self):
        warn = False

        taf = CheckTAF(self.tt, remote=self.remote)
        local = taf.existed_in_local()

        if local:
            if not local.confirmed:
                if taf.existed_in_remote():
                    taf.confirm()
                elif taf.overdued():
                    warn = True
        else:
            if taf.existed_in_remote():
                taf.save()
            elif taf.overdued():
                warn = True

        self.ctx.warn = warn

    def metar(self):
        metar = CheckMetar(self.tt, remote=self.remote)
        if self.remote:
            metar.save()

