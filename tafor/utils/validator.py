import re
import copy
import datetime

from collections import OrderedDict, defaultdict


weather = [
    'NSW', 'IC', 'FG', 'BR', 'SA', 'DU', 'HZ', 'FU', 'VA', 'SQ', 
    'PO', 'FC', 'TS', 'FZFG', 'BLSN', 'BLSA', 'BLDU', 'DRSN', 'DRSA', 
    'DRDU', 'MIFG', 'BCFG', 'PRFG'
]
weather_with_intensity = [
    'DZ', 'RA', 'SN', 'SG', 'PL', 'DS', 'SS', 'TSRA', 'TSSN', 'TSPL', 
    'TSGR', 'TSGS', 'SHRA', 'SHSN', 'SHGR', 'SHGS', 'FZRA', 'FZDZ'
]

splitPattern = re.compile(r'(BECMG|FM|TEMPO|PROB[34]0\sTEMPO)')


def _purePattern(regex):
    pattern = regex.pattern
    if pattern.startswith('^'):
        pattern = pattern[1:]
    return pattern


def formatTimeInterval(interval, time):
    # will remove later
    startHour = int(interval[:2])
    endHour = 0 if interval[2:] == '24' else int(interval[2:])

    base = datetime.datetime(time.year, time.month, time.day)
    delta = datetime.timedelta(hours=endHour) if startHour < endHour else datetime.timedelta(days=1, hours=endHour)
    start = base + datetime.timedelta(hours=startHour)
    end = base + delta

    return start, end


def formatTimez(timez):
    # will remove later
    utc =  datetime.datetime.utcnow()
    time = datetime.datetime(utc.year, utc.month, int(timez[:2]), int(timez[2:4]), int(timez[4:6]))
    return time


class Grammar(object):
    sign = re.compile(r'(TAF|BECMG|FM|TEMPO)\b')
    amend = re.compile(r'\b(AMD|\bCOR)\b')
    icao = re.compile(r'\b(Z[A-Z]{3})\b')
    timez = re.compile(r'\b(0[1-9]|[12][0-9]|3[0-1])([01][0-9]|2[0-3])([0-5][0-9])Z\b')
    period = re.compile(r'\b(0[1-9]|[12][0-9]|3[0-1])(0009|0312|0615|0918|1221|1524|1803|2106|0024|0606|1212|1818)\b')
    tmax = re.compile(r'\b(TXM?(\d{2})/(\d{2})Z)\b')
    tmin = re.compile(r'\b(TNM?(\d{2})/(\d{2})Z)\b')

    wind = re.compile(r'\b(?:00000|(VRB|0[1-9]0|[12][0-9]0|3[0-6]0)(0[1-9]|[1-4][0-9]|P49)(?:G(0[1-9]|[1-4][0-9]|P49))?)MPS\b')
    vis = re.compile(r'\b(9999|[5-9]000|[01234][0-9]00|0[0-7]50)\b')
    weather = re.compile(r'([-+]?({})\b)|(\b({})\b)'.format('|'.join(weather_with_intensity), '|'.join(weather)))
    cloud = re.compile(r'\bSKC|NSC|(FEW|SCT|BKN|OVC)(\d{3})(CB|TCU)?\b')
    vv = re.compile(r'\b(VV/{3}|VV(\d{3}))\b')
    cavok = re.compile(r'\bCAVOK\b')

    prob = re.compile(r'\b(PROB[34]0)\b')
    interval = re.compile(r'\b([01][0-9]|2[0-3])([01][0-9]|2[0-4])\b')


class Pattern(object):
    date = r'(0[1-9]|[12][0-9]|3[0-1])([01][0-9]|2[0-3])([0-5][0-9])'
    wind = r'00000|(VRB|0[1-9]0|[12][0-9]0|3[0-6]0)(0[1-9]|[1-4][0-9]|P49)'
    gust = r'(\d{,2}|P49)'
    vis = r'(9999|[5-9]000|[01234][0-9]00|0[0-7]50)'
    cloud = r'(FEW|SCT|BKN|OVC)(0[0-4][0-9]|050)'
    temp = r'M?([0-5][0-9])'
    hours = r'([01][0-9]|2[0-3])'
    interval = r'([01][0-9]|2[0-3])(0[1-9]|1[0-9]|2[0-4])'
    trendInterval = r'([01][0-9]|2[0-3])([0-5][0-9])'


class Validator(object):
    """docstring for Validator"""

    grammarClass = Grammar

    @classmethod
    def wind(cls, refWind, wind):
        """
        风
        1. 当预报平均地面风向的变化大于等于 60°，且平均风速在变化前和（或）变化后大于等于 5m/s 时
        2. 当预报平均地面风速的变化大于等于 5m/s 时
        3. 当预报平均地面风风速变差（阵风）增加(或减少)大于等于 5m/s，且平均风速在变化前和（或）变化后大于等于 8m/s 时  ***有异议
        """
        pattern = cls.grammarClass.wind
        refWindMatch = pattern.match(refWind)
        windMatch = pattern.match(wind)

        def splitWind(m):
            direction = m.group(1)
            speed = 50 if m.group(2) == 'P49' else int(m.group(2))
            gust = m.group(3)

            if gust == 'P49':
                gust = 50
            elif gust:
                gust = int(gust)
            else:
                gust = None

            return direction, speed, gust

        refDirection, refSpeed, refGust = splitWind(refWindMatch)
        direction, speed, gust = splitWind(windMatch)

        def angle(refDirection, direction):
            # 有一个风向为 VRB, 返回 True
            if 'VRB' in (refDirection, direction):
                return True

            refDirection = int(refDirection)
            direction = int(direction)

            # 计算夹角
            # 风向变化大于180度
            if abs(refDirection - direction) > 180:
                degree = min(refDirection, direction) + 360 - max(refDirection, direction)
            else:
                degree = abs(refDirection - direction)

            if degree < 60:
                return False

            return True

        # 1.当预报平均地面风向的变化大于等于 60°，且平均风速在变化前和（或）变化后大于等于 5m/s 时
        if angle(refDirection, direction) and max(refSpeed, speed) >= 5:
            return True

        # 2.当预报平均地面风速的变化大于等于 5m/s 时
        if abs(refSpeed - speed) >= 5:
            return True

        # 3.当预报平均地面风风速变差（阵风）增加 (或减少) 大于等于 5m/s，且平均风速在变化前和（或）变化后大于等于 8m/s 时
        if refGust and gust and abs(refGust - gust) >= 5 and max(refSpeed, speed) >= 8:
            return True

        if (refGust or gust) and max(refSpeed, speed) >= 8:
            return True

        return False

    @classmethod
    def vis(cls, refVis, vis, thresholds=None):
        """
        能见度
        当预报主导能见度上升并达到或经过下列一个或多个数值，或下降并经过下列一个或多个数值时：
        1. 150 m、350 m、600 m、800 m、1500 m 或 3000 m
        2. 5000 m（当有大量的按目视飞行规则的飞行时）

        """
        thresholds = thresholds if thresholds else [150, 350, 600, 800, 1500, 3000, 5000]
        return cls.compare(refVis, vis, thresholds)

    @classmethod
    def vv(cls, refVv, vv, thresholds=None):
        """
        垂直能见度
        当预报垂直能见度上升并达到或经过下列一个或多个数值，或下降并经过下列一个或多个数值时：
        30 m、60 m、150 m 或 300 m

        # 编报时对应 VV001、VV002、VV005、VV010
        """
        pattern = cls.grammarClass.vv
        matches = [pattern.match(refVv), pattern.match(vv)]
        thresholds = thresholds if thresholds else [1, 2, 5, 10]

        # 两者都包含 VV, 计算高度是否跨越阈值
        if all(matches):
            refVvHeight, vvHeight = matches[0].group(2), matches[1].group(2)
            return cls.compare(refVvHeight, vvHeight, thresholds)

        # 两者有一个是 VV, VV 高度小于最大阈值
        if any(matches):
            for m in matches:
                if m and int(m.group(2)) <= thresholds[-1]:
                    return True

        return False

    @classmethod
    def compare(cls, refValue, value, thresholds):
        refValue = int(refValue)
        value = int(value)
        trend = 'down' if refValue > value else 'up'

        for threshold in thresholds:
            if trend == 'up':
                if refValue < threshold <= value:
                    return True
            if trend == 'down':
                if value < threshold <= refValue:
                    return True

        return False

    @classmethod
    def weather(cls, refWeather, weather):
        """
        天气现象
        1. 当预报下列一种或几种天气现象开始、终止或强度变化时：
           冻降水
           中或大的降水（包括阵性降水）包括雷暴
           尘暴
           沙暴

        2. 当预报下列一种或几种天气现象开始、终止时：
           冻雾
           低吹尘、低吹沙或低吹雪
           高吹尘、高吹沙或高吹雪
           雷暴（伴或不伴有降水）
           飑
           漏斗云（陆龙卷或水龙卷）
        """
        weatherWithIntensityPattern = re.compile(r'([+-])?(DZ|RA|SN|SG|PL|DS|SS|SHRA|SHSN|SHGR|SHGS|FZRA|FZDZ|TSRA|TSSN|TSPL|TSGR|TSGS|TSSH)')
        weatherPattern = re.compile(r'(SQ|PO|FC|TS|FZFG|BLSN|BLSA|BLDU|DRSN|DRSA|DRDU)')
        weakPrecipitationPattern = re.compile(r'-(DZ|RA|SN|SG|PL|SHRA|SHSN|SHGR|SHGS)')

        refWeathers = refWeather.split()
        weathers = weather.split()

        def condition(weather):
            # 符合转折条件，不包括弱降水
            return weatherWithIntensityPattern.match(weather) and not weakPrecipitationPattern.match(weather) \
                or weatherPattern.match(weather)

        for w in weathers:
            # NSW 无法转折的天气
            if w == 'NSW' and set(refWeathers) & set(['BR', 'HZ', 'FU', 'DU', '-RA', '-SN']) \
                or 'NSW' in refWeathers and w in ['BR', 'HZ', 'FU', 'DU', '-RA', '-SN']:
                continue

            if w not in refWeathers:
                if condition(w) or condition(refWeather):
                    return True

        return False

    @classmethod
    def cloud(cls, refCloud, cloud, thresholds=None):
        '''
        云
        当预报 BKN 或 OVC 云量的最低云层的云高抬升并达到或经过下列一个或多个数值，或降低并经过下列一个或多个数值时：
        1. 30 m、60 m、150 m 或 300 m
        2. 450 m（在有大量的按目视飞行规则的飞行时）

        当预报低于 450 m 的云层或云块的量的变化满足下列条件之一时：
        1. 从 SCT 或更少到 BKN、OVC
        2. 从 BKN、OVC 到 SCT 或更少

        当预报积雨云将发展或消失时
        '''
        pattern = cls.grammarClass.cloud
        thresholds = thresholds if thresholds else [1, 2, 5, 10, 15]
        cloudCover = {'SKC': 0, 'FEW': 1, 'SCT': 2, 'BKN': 3, 'OVC': 4}

        refClouds = refCloud.split()
        clouds = cloud.split()

        # 云组无变化
        if refCloud == cloud:
            return False

        # 有积雨云 CB
        cbPattern = re.compile(r'(FEW|SCT|BKN|OVC)(\d{3})(CB|TCU$)')
        matches = [cbPattern.search(refCloud), cbPattern.search(cloud)]

        if any(matches):
            if all(matches):
                return matches[0].group() != matches[1].group()
            return True

        def analyze(clouds):
            minHeight = 999
            maxCover = 0
            for c in clouds:
                m = pattern.match(c)
                if m and m.group() not in ['NSC', 'SKC']:
                    if cloudCover[m.group(1)] > 2:
                        minHeight = min(minHeight, int(m.group(2)))

                    if int(m.group(2)) < 15:
                        maxCover = max(maxCover, cloudCover[m.group(1)])

            minHeight = minHeight if minHeight < 15 else 0
            return minHeight, maxCover

        minHeight, maxCover = analyze(clouds)
        refMinHeight, refMaxCover = analyze(refClouds)

        # 当预报 BKN 或 OVC 云量的最低云层的云高抬升并达到或经过下列一个或多个数值，或降低并经过下列一个或多个数值
        if any([refMinHeight, minHeight]):
            return cls.compare(refMinHeight, minHeight, thresholds)

        # 当预报低于 450 m 的云层或云块的量的变化满足下列条件之一
        if refMaxCover > 2 and maxCover < 3 or refMaxCover < 3 and maxCover > 2:
            return True

        return False

    @classmethod
    def cavok(cls, vis, weather, cloud):
        validations = [
            cls.vis(vis, 9999),
            cls.weather(weather, 'NSW'),
            cls.cloud(cloud, 'NSC')
        ]

        return all(validations)


class Lexer(object):
    grammarClass = Grammar

    defaultRules = [
        'sign', 'amend', 'icao', 'timez', 'period', 'prob', 'interval',
        'wind', 'vis', 'cavok', 'weather', 'cloud', 'vv', 'tmax', 'tmin'
    ]

    def __init__(self, part, grammar=None, **kwargs):
        if not grammar:
            grammar = self.grammarClass()
        self.grammar = grammar
        self.part = part
        self.tokens = OrderedDict()

        self.parse(part)

    def __repr__(self):
        return self.part

    @property
    def sign(self):
        return self.tokens['sign']['text']

    def parse(self, part, rules=None):
        if not rules:
            rules = self.defaultRules

        for key in rules:
            if 'TAF' in self.part and key == 'interval':
                continue

            pattern = getattr(self.grammar, key)
            m = pattern.search(part)
            if not m:
                continue

            if key in ('weather', 'cloud'):
                items = [m.group() for m in pattern.finditer(part)]
                self.tokens[key] = {
                    'text': ' '.join(items),
                    'error': None
                }
            else:
                self.tokens[key] = {
                    'text': m.group(),
                    'error': None
                }

        if self.tokens['sign']['text'] == 'TAF':
            period = self.tokens['period']['text'][:4]
            time = formatTimez(self.tokens['timez']['text'])
            self.period = self.generatePeriod(period, time)

    def generatePeriod(self, period, time):
        self.period = formatTimeInterval(period, time)
        return self.period

    def isValid(self):
        for k, e in self.tokens.items():
                if e['error']:
                    return False
        
        return True

    def renderer(self, style='plain'):

        def terminal():
            from colorama import init, Fore
            init(autoreset=True)

            elements = []
            for k, e in self.tokens.items():
                if e['error']:
                    elements.append(Fore.RED + e['text'])
                else:
                    elements.append(Fore.GREEN + e['text'])

            return ' '.join(elements)

        def html():
            elements = []
            for k, e in self.tokens.items():
                if e['error']:
                    elements.append('<span style="color: red">{}</span>'.format(e['text']))
                else:
                    elements.append(e['text'])

            return ' '.join(elements)

        def plain():
            return self.part

        func = locals().get(style, plain)
        return func()



class Parser(object):
    defaultRules = [
        'wind', 'vis', 'weather', 'cloud'
    ]

    def __init__(self, message, parse=None, validator=None):
        self.message = message
        self.becmgs = []
        self.tempos = []
        self.tips = []

        self.reference = None

        if not parse:
            self.parse = Lexer

        if not validator:
            self.validator = Validator()

        self.split()
        self.regroup()
        self.refs()

    def split(self):
        message = self.message.replace('=', '')
        elements = splitPattern.split(message)
        self.primary = self.parse(elements[0])

        if len(elements) > 1:
            becmg_index = [i for i, item in enumerate(elements) if item == 'BECMG']
            tempo_index = [i for i, item in enumerate(elements) if 'TEMPO' in item]

            for i, index in enumerate(becmg_index):
                e = elements[index] + elements[index+1]
                becmg = self.parse(e)
                becmg.generatePeriod(becmg.tokens['interval']['text'], self.primary.period[0])
                self.becmgs.append(becmg)

            for i, index in enumerate(tempo_index):
                e = elements[index] + elements[index+1]
                tempo = self.parse(e)
                tempo.generatePeriod(tempo.tokens['interval']['text'], self.primary.period[0])
                self.tempos.append(tempo)

        self.elements = [self.primary] + self.becmgs + self.tempos

    def regroup(self):
        self.becmgs.sort(key=lambda x: x.period[1])
        self.tempos.sort(key=lambda x: x.period[0])

        def group(becmgs, tempos):
            groups = []
            for becmg in becmgs:
                last = groups[-1] if groups else None
                if last and last.sign == 'TEMPO' and last.period[0] > becmg.period[1]:
                    index = groups.index(last)
                    groups.insert(index, becmg)
                else:
                    groups.append(becmg)

                for tempo in tempos:
                    if tempo.period[0] < becmg.period[1] < tempo.period[1]:
                        index = groups.index(becmg)
                        groups.insert(index, tempo)
                        groups.append(tempo)

                    if tempo.period[1] <= becmg.period[1] and tempo not in groups:
                        index = groups.index(becmg)
                        groups.insert(index, tempo)

                    if tempo.period[0] >= becmg.period[1]:
                        groups.append(tempo)

            return groups

        def reduce(items):
            groups = []
            cache = []
            for e in items:
                if e.sign == 'BECMG':
                    groups.append(e)
                    cache = []
                if e.sign == 'TEMPO':
                    if e not in cache:
                        groups.append(e)
                        cache.append(e)
            return groups

        self.groups = reduce(group(self.becmgs, self.tempos))
        return self.groups

    def validate(self):
        self.validateCombination(self.reference, self.primary.tokens)

        for e in self.groups:
            for key in e.tokens:
                verify = getattr(self.validator, key, None)
                if verify:
                    if key == 'cavok':
                        legal = verify(self.reference['vis']['text'], self.reference['weather']['text'], self.reference['cloud']['text'])
                    else:
                        legal = verify(self.reference[key]['text'], e.tokens[key]['text'])

                    if key == 'weather' and 'vis' in e.tokens and not e.tokens['vis']['error']:
                        # 引起能见度变化的天气现象
                        pass
                    else:
                        e.tokens[key]['error'] = not legal

                    if e.sign == 'BECMG':
                        if key == 'cavok':
                            self.reference['vis']['text'] = '9999'
                            self.reference['weather']['text'] = 'NSW'
                            self.reference['cloud']['text'] = 'NSC'
                        else:
                            self.reference[key]['text'] = e.tokens[key]['text']

            self.validateCombination(self.reference, e.tokens)

        self.tips = list(set(self.tips))

        valids = [e.isValid() for e in self.elements]
        return all(valids)

    def validateCombination(self, ref, tokens):
        mixture = copy.deepcopy(ref)
        for key in tokens:
            if key in self.defaultRules:
                mixture[key]['text'] = tokens[key]['text']

        # 检查能见度和天气现象
        if 'vis' in tokens:
            vis = int(tokens['vis']['text'])
            refVis = int(ref['vis']['text'])
            weathers = mixture['weather']['text'].split()

            if 'NSW' in weathers:
                if max(refVis, vis) >= 1000 and min(refVis, vis) < 1000:
                    tokens['vis']['error'] = True
                    self.tips.append('能见度跨 1000 米时应变化天气现象')

                if vis <= 5000 and refVis > 5000:
                    tokens['vis']['error'] = True
                    self.tips.append('能见度降低到 5000 米以下时应有天气现象')

                if vis == refVis:
                    if vis <= 5000:
                        tokens['vis']['error'] = True
                        self.tips.append('能见度小于 5000 米时应有天气现象')

            else:
                if vis < 1000 and set(weathers) & set(['BR', '-DZ']):
                    tokens['vis']['error'] = True
                    if 'weather' in tokens:
                        tokens['weather']['error'] = True

                    self.tips.append('能见度小于 1000，BR -DZ 不能有')

                if 1000 <= vis <= 5000 and set(weathers) & set(['FG', '+DZ']):
                    tokens['vis']['error'] = True
                    if 'weather' in tokens:
                        tokens['weather']['error'] = True

                    self.tips.append('能见度大于 1000、小于 5000，FG +DZ 不能有')
                
                if vis > 5000 and set(weathers) & set(['FG', 'FU', 'BR', 'HZ']):
                    if 'weather' in tokens:
                        tokens['weather']['error'] = True

                    self.tips.append('能见度大于 5000，FG、FU、BR、HZ 不能有')

        if 'weather' in tokens:
            weather = tokens['weather']['text']
            weathers = weather.split()

            # 检查阵性降水和积雨云
            cloud = mixture['cloud']['text']
            if ('TS' in weather or 'SH' in weather) and 'CB' not in cloud:
                tokens['weather']['error'] = True
                self.tips.append('阵性降水应包含 CB')

            if 'NSW' in weathers and len(weathers) > 1:
                tokens['weather']['error'] = True
                self.tips.append('NSW 不能和其他天气现象同时存在')

            intWeather = set(weathers) & set(['BR', 'HZ', 'FG', 'FU'])
            if len(intWeather) > 1:
                tokens['weather']['error'] = True
                self.tips.append('BR，HZ，FG，FU 不能同时存在')

        # 不用高度云组云量的验证
        if 'cloud' in tokens:
            clouds = [c for c in tokens['cloud']['text'].split() if 'CB' not in c]

            for i, cloud in enumerate(clouds):
                if i == 1 and 'FEW' in cloud:
                    tokens['cloud']['error'] = True
                    self.tips.append('云组第二层云量不能为 FEW')

                if i == 2 and ('FEW' in cloud or 'SCT' in cloud):
                    tokens['cloud']['error'] = True
                    self.tips.append('云组第三层云量不能为 FEW 或 SCT')

    def refs(self):
        self.reference = copy.deepcopy(self.primary.tokens)
        if 'weather' not in self.reference:
            self.reference['weather'] = {
                'text': 'NSW',
                'error': None
            }

        if 'cavok' in self.reference:
            self.reference['vis'] = {
                'text': '9999',
                'error': None
            }
            self.reference['cloud'] = {
                'text': 'NSC',
                'error': None
            }

        return self.reference
 
    def renderer(self, style='plain'):
        outputs = [e.renderer(style) for e in self.elements]

        if style == 'html':
            return '<br/>'.join(outputs) + '='

        return '\n'.join(outputs) + '='



if __name__ == '__main__':    
    # print(Validator.wind('03004GP49MPS', '36005MPS'))
    # print(Validator.vv('VV005', 'VV003'))
    # print(Validator.weather('TSRA', '-RA'))
    # print(Validator.cloud('SCT020', 'SCT010 FEW023CB'))
    # print(Validator.cloud('NSC', 'SKC'))

    message = '''
        TAF ZJHK 211338Z 211524 14004MPS 4000 BR SCT020 FEW026CB
        BECMG 1718 CAVOK=
    '''
    # m = Grammar.taf.search(message)
    # print(m.group(0))
    # m = Grammar.timez.search(message)
    # print(m.groups())

    e = Parser(message)
    isValid = e.validate()
    print(e.tips)
    # print(isValid)

    print(e.renderer(style='terminal'))

    # print(e.tips)

    # print(e.primary.tokens)
    # print(e.tempos[0].tokens)
