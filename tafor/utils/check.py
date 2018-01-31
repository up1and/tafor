import re
import datetime

from PyQt5.QtCore import QObject

from tafor import conf, logger
from tafor.models import db, Tafor, Metar

from tafor.utils.validator import Grammar


def formatTimez(message):
    try:
        m = Grammar.timez.search(message).groups()
        utc =  datetime.datetime.utcnow()
        created = datetime.datetime(utc.year, utc.month, int(m[0]), int(m[1]), int(m[2]))
        return created
    except Exception as e:
        logger.error(e, exc_info=True)
        created = datetime.datetime.utcnow()
        return created


class CheckTAF(QObject):
    """docstring for CheckTAF"""
    def __init__(self, tt, remote=None, time=None):
        super(CheckTAF, self).__init__()
        self.tt = tt
        self.remote = remote
        self.time = datetime.datetime.utcnow() if time is None else time
        startOfTheDay = datetime.datetime(self.time.year, self.time.month, self.time.day)
        self.startTime = dict()
        self.startTime['FC'] = {
                    '0009': startOfTheDay - datetime.timedelta(hours=2),
                    '0312': startOfTheDay + datetime.timedelta(hours=1),
                    '0615': startOfTheDay + datetime.timedelta(hours=4),
                    '0918': startOfTheDay + datetime.timedelta(hours=7),
                    '1221': startOfTheDay + datetime.timedelta(hours=10),
                    '1524': startOfTheDay + datetime.timedelta(hours=13),
                    '1803': startOfTheDay + datetime.timedelta(hours=16),
                    '2106': startOfTheDay + datetime.timedelta(hours=19),
        }
        self.startTime['FT'] = {
                    '0024': startOfTheDay - datetime.timedelta(hours=5),
                    '0606': startOfTheDay + datetime.timedelta(hours=1),
                    '1212': startOfTheDay + datetime.timedelta(hours=7),
                    '1818': startOfTheDay + datetime.timedelta(hours=13),
        }

        thresholdMinute = conf.value('Monitor/WarnTAFTime')
        thresholdMinute = int(thresholdMinute) if thresholdMinute else 30

        self.thresholdTime = {
            'FC': datetime.timedelta(minutes=thresholdMinute), 
            'FT': datetime.timedelta(hours=2, minutes=thresholdMinute)
        }

    def currentPeriod(self):
        increment = {'FC': datetime.timedelta(minutes=50), 'FT': datetime.timedelta(hours=2, minutes=50)}
        period = self._findPeriod(increment)
        return self._withDay(period)

    def warnPeriod(self):
        increment = {'FC': datetime.timedelta(hours=3), 'FT': datetime.timedelta(hours=6)}
        default = {'FC': '0009', 'FT': '0024'} # 00 - 01 时次人肉添加
        find = self._findPeriod(increment)
        period = find if find else default[self.tt]
        return self._withDay(period)

    def existedInLocal(self, periodWithDay=None):
        periodWithDay = self.warnPeriod() if periodWithDay is None else periodWithDay
        expired = datetime.datetime.utcnow() - datetime.timedelta(hours=24)
        recent = db.query(Tafor).filter(Tafor.rpt.contains(periodWithDay), Tafor.sent > expired).order_by(Tafor.sent.desc()).first()
        return recent

    def existedInRemote(self):
        if self.remote:
            period = Grammar.period.search(self.remote).group()
            return period == self.warnPeriod()

    def save(self):
        last = db.query(Tafor).filter_by(tt=self.tt).order_by(Tafor.sent.desc()).first()

        if last is None or last.rptInline != self.remote:  # 如果数据表为空 或 最后一条数据和远程不相等
            item = Tafor(tt=self.tt, rpt=self.remote, confirmed=self.time)
            db.add(item)
            db.commit()
            logger.info('Save {} {}'.format(self.tt, self.remote))

    def confirm(self):
        last = db.query(Tafor).filter_by(tt=self.tt).order_by(Tafor.sent.desc()).first()

        if last is not None and last.rptInline == self.remote:
            last.confirmed = self.time
            db.commit()
            logger.info('Confirm {} {}'.format(self.tt, self.remote))

    def hasExpired(self):
        startTime = self.startTime[self.tt][self.warnPeriod()[2:]]
        thresholdTime = startTime + self.thresholdTime[self.tt]
        return thresholdTime < self.time

    def _findPeriod(self, increment):
        for key, start in self.startTime[self.tt].items():
            if start <= self.time <= start + increment[self.tt]:
                period = key
                return period

    def _withDay(self, period):
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

    def save(self):
        last = db.query(Metar).filter_by(tt=self.tt).order_by(Metar.created.desc()).first()
        
        if last is None or last.rpt != self.remote:
            item = Metar(tt=self.tt, rpt=self.remote, created=formatTimez(self.remote))
            db.add(item)
            db.commit()
            logger.info('Save {} {}'.format(self.tt, self.remote))


class Listen(object):
    def __init__(self, store):
        self.store = store

    def __call__(self, tt):
        self.tt = tt
        self.remote = self.store.message.get(self.tt, None)
        method = {'FC': 'taf', 'FT': 'taf', 'SA': 'metar', 'SP': 'metar'}
        return getattr(self.__class__, method[self.tt])(self)

    def taf(self):
        expired = False

        taf = CheckTAF(self.tt, remote=self.remote)
        local = taf.existedInLocal()

        if local:
            if not local.confirmed:
                if taf.existedInRemote():
                    taf.confirm()
                elif taf.hasExpired():
                    expired = True
        else:
            if taf.existedInRemote():
                taf.save()
            elif taf.hasExpired():
                expired = True

        self.store.warning = [taf.tt, expired]

    def metar(self):
        metar = CheckMetar(self.tt, remote=self.remote)
        if self.remote:
            metar.save()

