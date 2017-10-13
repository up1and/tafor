import re

from collections import OrderedDict

class Validator(object):
    """docstring for Validator"""

    @staticmethod
    def wind(str_wind1, str_wind2):
        """
        风：
        1.当预报平均地面风向的变化大于等于 60°，且平均风速在变化前和（或）变化后大于等于 5m/s 时
        2.当预报平均地面风速的变化大于等于 5m/s 时
        3.当预报平均地面风风速变差（阵风）增加(或减少)大于等于 5m/s，且平均风速在变化前和（或）变化后大于等于 8m/s 时  ***有异议
        """
        regex_wind = re.compile(REGEX_TAF['common']['wind'])
        wind1 = regex_wind.match(str_wind1).groupdict()
        wind2 = regex_wind.match(str_wind2).groupdict()

        speed1 = int(wind1['speed'])
        speed2 = int(wind2['speed'])

        gust1 = int(wind1['gust']) if wind1['gust'] else None
        gust2 = int(wind2['gust']) if wind2['gust'] else None

        # print(wind1, wind2)

        def direction():
            # 有一个风向为 VRB, 返回 True
            if 'VRB' in (wind1['direction'], wind2['direction']):
                return True

            direction1 = int(wind1['direction'])
            direction2 = int(wind2['direction'])

            # 计算夹角
            # 风向变化大于180度
            if abs(direction1 - direction2) > 180:
                angle = min(direction1, direction2) + 360 - max(direction1, direction2)
            else:
                angle = abs(direction1 - direction2)

            # print(angle)

            if angle < 60:
                return False

            return True

        # def gust(wind):
        #     if int(wind['gust']) - int(wind['speed']) < 5:
        #         return False

        # 1.当预报平均地面风向的变化大于等于 60°，且平均风速在变化前和（或）变化后大于等于 5m/s 时
        if direction() and max(speed1, speed2) >= 5:
            return True

        # 2.当预报平均地面风速的变化大于等于 5m/s 时
        if abs(speed1 - speed2) >= 5:
            return True

        # 3.当预报平均地面风风速变差（阵风）增加(或减少)大于等于 5m/s，且平均风速在变化前和（或）变化后大于等于 8m/s 时
        if gust1 and gust2 and abs(gust1 - gust2) >= 5 and max(speed1, speed2) >=8:
            return True

        return False


    @staticmethod
    def vis(vis1, vis2, thresholds=None):
        """
        当预报主导能见度上升并达到或经过下列一个或多个数值，或下降并经过下列一个或多个数值时：
        1. 150 m、350 m、600 m、800 m、1500 m 或 3000 m
        2. 5000 m（当有大量的按目视飞行规则的飞行时） # 我们没有

        """
        trend = 'down' if vis1 > vis2 else 'up'

        # print(vis1, vis2, trend)

        thresholds = thresholds if thresholds else [150, 350, 600, 800, 1500, 3000, 5000]
        for threshold in thresholds:
            if trend == 'up':
                if vis1 < threshold <= vis2:
                    return True
            if trend == 'down':
                if vis2 < threshold < vis1:
                    return True

        return False

        

    @staticmethod
    def weather(wx1, wx2):
        """
        天气现象：
           1. 当预报下列一种或几种天气现象开始、终止或强度变化时：
              冻降水
              中或大的降水（包括阵性降水）包括雷暴
              尘暴
              沙暴

           2. 当预报下列一种或几种天气现象开始、终止时
              冻雾
              低吹尘、低吹沙或低吹雪
              高吹尘、高吹沙或高吹雪
              雷暴（伴或不伴有降水）
              飑
              漏斗云（陆龙卷或水龙卷）
        """
        # regex = r'(BR|HZ|FU|DU|-RA|-SN)'
        # 特殊情况 NSW 未考虑

        regex = r'((?P<intensity>[+-])?(?P<wx1>DZ|RA|SN|SG|PL|DS|SS|SHRA|SHSN|SHGR|SHGS|FZRA|FZDZ|TSRA|TSSN|TSPL|TSGR|TSGS|TSSH)|(?P<wx2>SQ|PO|FC|TS|FZFG|BLSN|BLSA|BLDU|DRSN|DRSA|DRDU))'

        match1 = re.search(regex, wx1)
        match2 = re.search(regex, wx2)

        # print(match1, match2)

        if match1 and match2:
            if match1.group() == match2.group():
                return False

        return True

    @staticmethod
    def clouds(cloud1, cloud2):
        '''   
          当预报BKN或OVC云量的最低云层的云高抬升并达到或经过下列一个或多个数值，或降低并经过下列一个或多个数值时：
            1. 30 m、60 m、150 m 或 300 m
            2. 450 m（在有大量的按目视飞行规则的飞行时）

          当预报低于450 m的云层或云块的量的变化满足下列条件之一时：
            1. 从SCT或更少到BKN、OVC
            2. 从BKN、OVC到SCT或更少

          当预报积雨云将发展或消失时
        '''
        regex = REGEX_TAF['common']['cloud']
        thresholds = [1, 2, 5, 10, 15]

        # 同为NSC
        if cloud1 == 'NSC' and cloud2 == 'NSC':
            return False

        # 有积雨云CB
        match1 = re.finditer(regex, cloud1)
        match2 = re.finditer(regex, cloud2)
        print(match1)
        print(match2)
        for i in match2:
            print(i.groupdict())


_weather1 = [
    'NSW', 'IC', 'FG', 'BR', 'SA', 'DU', 'HZ', 'FU', 'VA', 'SQ', 
    'PO', 'FC', 'TS', 'FZFG', 'BLSN', 'BLSA', 'BLDU', 'DRSN', 'DRSA', 
    'DRDU', 'MIFG', 'BCFG', 'PRFG'
]
_weather2 = [
    'DZ', 'RA', 'SN', 'SG', 'PL', 'DS', 'SS', 'TSRA', 'TSSN', 'TSPL', 
    'TSGR', 'TSGS', 'SHRA', 'SHSN', 'SHGR', 'SHGS', 'FZRA', 'FZDZ'
]
_split_pattern = re.compile(r'(BECMG|FM|TEMPO|PROB[34]0\sTEMPO)')


def _pure_pattern(regex):
    pattern = regex.pattern
    if pattern.startswith('^'):
        pattern = pattern[1:]
    return pattern


class Grammar(object):
    sign = re.compile(r'(TAF|BECMG|FM|TEMPO)\b')
    amend = re.compile(r'\b(AMD|\bCOR)\b')
    icao = re.compile(r'\b([A-Z]{4})\b')
    timez = re.compile(r'\b(0[1-9]|[12][0-9]|3[0-1])([01][0-9]|2[0-3])([0-5][0-9])Z\b')
    date = re.compile(r'\b(0[1-9]|[12][0-9]|3[0-1])([01][0-9]|2[0-3])([0-5][0-9])\b')
    period = re.compile(r'\b(0[1-9]|[12][0-9]|3[0-1])(0009|0312|0615|0918|1221|1524|1803|2106|0024|0606|1212|1818)\b')
    tmax = re.compile(r'\b(TXM?(\d{2})/(\d{2})Z)\b')
    tmin = re.compile(r'\b(TNM?(\d{2})/(\d{2})Z)\b')

    wind = re.compile(r'\b(?:00000|(VRB|0[1-9]0|[12][0-9]0|3[0-6]0)(0[1-9]|[1-4][0-9]|P49)(?:G(0[1-9]|[1-4][0-9]|P49))?)MPS\b')
    vis = re.compile(r'\b(9999|[5-9]000|[01234][0-9]00|0[0-7]50)\b')
    wx1 = re.compile(r'\b({})\b'.format('|'.join(_weather1)))
    wx2 = re.compile(r'\b([-+]?)({})\b'.format('|'.join(_weather2)))
    cloud = re.compile(r'\bNSC|(FEW|SCT|BKN|OVC)(\d{3})(CB|TCU)?\b')
    vv = re.compile(r'\b(VV/{3}|VV\d{3})\b')
    cavok = re.compile(r'\bCAVOK\b')

    prob = re.compile(r'\b(PROB[34]0)\b')
    interval = re.compile(r'\b([01][0-9]|2[0-3])([01][0-9]|2[0-3])\b')


class EditRegex(object):
    date = r'(0[1-9]|[12][0-9]|3[0-1])([01][0-9]|2[0-3])([0-5][0-9])'
    wind = r'00000|(VRB|0[1-9]0|[12][0-9]0|3[0-6]0)(0[1-9]|[1-4][0-9]|P49)'
    gust = r'(0[1-9]|[1-4][0-9]|P49)'
    vis = r'(9999|[5-9]000|[01234][0-9]00|0[0-7]50)'
    cloud = r'(FEW|SCT|BKN|OVC)(0[0-4][0-9]|050)'
    temp = r'M?([0-5][0-9])'
    hours = r'([01][0-9]|2[0-3])'
    interval = r'([01][0-9]|2[0-3])(0[1-9]|1[0-9]|2[0-4])'


class Lexer(object):
    grammar_class = Grammar

    default_rules = [
        'sign', 'amend', 'icao', 'timez', 'date', 'period', 'tmax', 'tmin',
        'wind', 'vis', 'wx1', 'wx2', 'cloud', 'vv', 'cavok',
        'prob', 'interval'
    ]

    def __init__(self, message, rules=None, **kwargs):
        if not rules:
            rules = self.grammar_class()
        self.rules = rules

        self.message = message
        self.parse(message)

    def __call__(self, message, rules=None):
        return self.parse(message, rules)

    def parse(self, message, rules=None):
        if not rules:
            rules = self.default_rules

        for key in rules:
            rule = getattr(self.rules, key)
            m = rule.search(message)
            if not m:
                continue
            
            if key in ('period', 'wind', 'wx2', 'cloud', 'interval'):
                self.parse_muti(key, m)
            else:
                self.parse_single(key, m)





    def parse_single(self, key, m):
        setattr(self, key, m.group(0))

    def parse_muti(self, key, m):
        setattr(self, key, m.groups())

    # def parse_amend(self, m):
    #     self.amend = m.group(0)

    # def parse_icao(self, m):
    #     self.icao = m.group(0)



class Parser(object):

    def __init__(self, message, parse=None):
        self.message = message
        self.becmgs = []
        self.tempos = []

        if not parse:
            self.parse = Lexer

        self.split()

    def split(self):
        message = self.message.replace('=', '')
        self.elements = _split_pattern.split(message)
        self.primary = self.parse(self.elements[0])

        if len(self.elements) > 1:
            becmg_index = [i for i, item in enumerate(self.elements) if item == 'BECMG']
            tempo_index = [i for i, item in enumerate(self.elements) if 'TEMPO' in item]

            for i, index in enumerate(becmg_index):
                e = self.elements[index] + self.elements[index+1]
                self.becmgs.append(self.parse(e))

            for i, index in enumerate(tempo_index):
                e = self.elements[index] + self.elements[index+1]
                self.tempos.append(self.parse(e))
        

class Renderer(object):
    def __init__(self, **kwargs):
        self.options = kwargs
        



if __name__ == '__main__':
    # print(Validator.clouds('SCT020', 'SCT010 FEW023CB'))
    message = 'TAF AMD ZJHK 110702Z 110918 19003MPS 9999 SCT020 TX32/09Z TN27/18Z TEMPO 0912 TS SCT020 FEW026CB='
    # m = Grammar.taf.search(message)
    # print(m.group(0))
    # m = Grammar.timez.search(message)
    # print(m.groups())

    e = Parser(message)

    print(e.tempos)
