import datetime

from tafor import setting, db
from tafor.models import Tafor


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

    def current(self):
        increment = {'FC': datetime.timedelta(minutes=50), 'FT': datetime.timedelta(hours=2, minutes=50)}
        period = self._find_period(increment)
        return self._with_day(period)

    def is_existed(self, period_with_day):
        expired = datetime.datetime.utcnow() - datetime.timedelta(hours=24)
        recent = db.query(Tafor).filter(Tafor.rpt.contains(period_with_day), Tafor.sent > expired).all()
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


if __name__ == '__main__':
    taf = TAFPeriod('FT')
    print(taf.warn())