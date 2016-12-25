import datetime

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