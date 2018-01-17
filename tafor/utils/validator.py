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

_split_pattern = re.compile(r'(BECMG|FM|TEMPO|PROB[34]0\sTEMPO)')


def _pure_pattern(regex):
    pattern = regex.pattern
    if pattern.startswith('^'):
        pattern = pattern[1:]
    return pattern


def format_period(period, time):
    # will remove later
    start_hour = int(period[:2])
    end_hour = 0 if period[2:] == '24' else int(period[2:])

    base = datetime.datetime(time.year, time.month, time.day)
    delta = datetime.timedelta(hours=end_hour) if start_hour < end_hour else datetime.timedelta(days=1, hours=end_hour)
    start = base + datetime.timedelta(hours=start_hour)
    end = base + delta

    return start, end


def format_timez(timez):
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
    cloud = re.compile(r'\bNSC|(FEW|SCT|BKN|OVC)(\d{3})(CB|TCU)?\b')
    vv = re.compile(r'\b(VV/{3}|VV(\d{3}))\b')
    cavok = re.compile(r'\bCAVOK\b')

    prob = re.compile(r'\b(PROB[34]0)\b')
    interval = re.compile(r'\b([01][0-9]|2[0-3])([01][0-9]|2[0-4])\b')


class Pattern(object):
    date = r'(0[1-9]|[12][0-9]|3[0-1])([01][0-9]|2[0-3])([0-5][0-9])'
    wind = r'00000|(VRB|0[1-9]0|[12][0-9]0|3[0-6]0)(0[1-9]|[1-4][0-9]|P49)'
    gust = r'(0[1-9]|[1-4][0-9]|P49)'
    vis = r'(9999|[5-9]000|[01234][0-9]00|0[0-7]50)'
    cloud = r'(FEW|SCT|BKN|OVC)(0[0-4][0-9]|050)'
    temp = r'M?([0-5][0-9])'
    hours = r'([01][0-9]|2[0-3])'
    interval = r'([01][0-9]|2[0-3])(0[1-9]|1[0-9]|2[0-4])'


class Validator(object):
    """docstring for Validator"""

    grammar_class = Grammar

    @classmethod
    def wind(cls, ref_wind, wind):
        """
        风：
        1.当预报平均地面风向的变化大于等于 60°，且平均风速在变化前和（或）变化后大于等于 5m/s 时
        2.当预报平均地面风速的变化大于等于 5m/s 时
        3.当预报平均地面风风速变差（阵风）增加(或减少)大于等于 5m/s，且平均风速在变化前和（或）变化后大于等于 8m/s 时  ***有异议
        """
        pattern = cls.grammar_class.wind
        ref_wind_group = pattern.match(ref_wind).groups()
        wind_group = pattern.match(wind).groups()

        ref_speed = int(ref_wind_group[1])
        speed = int(wind_group[1])

        ref_gust = int(ref_wind_group[2]) if ref_wind_group[2] else None
        gust = int(wind_group[2]) if wind_group[2] else None

        def angle(ref_direction, direction):
            # 有一个风向为 VRB, 返回 True
            if 'VRB' in (ref_direction, direction):
                return True

            ref_direction = int(ref_direction)
            direction = int(direction)

            # 计算夹角
            # 风向变化大于180度
            if abs(ref_direction - direction) > 180:
                degree = min(ref_direction, direction) + 360 - max(ref_direction, direction)
            else:
                degree = abs(ref_direction - direction)

            if degree < 60:
                return False

            return True

        # 1.当预报平均地面风向的变化大于等于 60°，且平均风速在变化前和（或）变化后大于等于 5m/s 时
        if angle(ref_wind_group[0], wind_group[0]) and max(ref_speed, speed) >= 5:
            return True

        # 2.当预报平均地面风速的变化大于等于 5m/s 时
        if abs(ref_speed - speed) >= 5:
            return True

        # 3.当预报平均地面风风速变差（阵风）增加(或减少)大于等于 5m/s，且平均风速在变化前和（或）变化后大于等于 8m/s 时
        if ref_gust and gust and abs(ref_gust - gust) >= 5 and max(ref_speed, speed) >= 8:
            return True

        # if ref_gust or gust and max(ref_speed, speed) >= 8:
        #     return True

        return False

    @classmethod
    def vis(cls, ref_vis, vis, thresholds=None):
        """
        当预报主导能见度上升并达到或经过下列一个或多个数值，或下降并经过下列一个或多个数值时：
        1. 150 m、350 m、600 m、800 m、1500 m 或 3000 m
        2. 5000 m（当有大量的按目视飞行规则的飞行时）

        """
        thresholds = thresholds if thresholds else [150, 350, 600, 800, 1500, 3000, 5000]
        return cls.compare(ref_vis, vis, thresholds)

    @classmethod
    def vv(cls, ref_vv, vv, thresholds=None):
        """
        当预报垂直能见度上升并达到或经过下列一个或多个数值，
        或下降并经过下列一个或多个数值时：30 m、60 m、150 m 或 300 m；

        编报时对应 VV001、VV002、VV005、VV010
        """
        pattern = cls.grammar_class.vv
        matches = [pattern.match(ref_vv), pattern.match(vv)]
        thresholds = thresholds if thresholds else [1, 2, 5, 10]

        # 两者都包含 VV, 计算高度是否跨越阈值
        if all(matches):
            ref_vv_height, vv_height = matches[0].group(2), matches[1].group(2)
            return cls.compare(ref_vv_height, vv_height, thresholds)

        # 两者有一个是 VV, VV 高度小于最大阈值
        if any(matches):
            for m in matches:
                if m and int(m.group(2)) <= thresholds[-1]:
                    return True

        return False

    @classmethod
    def compare(cls, ref_value, value, thresholds):
        ref_value = int(ref_value)
        value = int(value)
        trend = 'down' if ref_value > value else 'up'

        for threshold in thresholds:
            if trend == 'up':
                if ref_value < threshold <= value:
                    return True
            if trend == 'down':
                if value < threshold < ref_value:
                    return True

        return False

    @classmethod
    def weather(cls, ref_weather, weather):
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
        weather_with_intensity_pattern = re.compile(r'([+-])?(DZ|RA|SN|SG|PL|DS|SS|SHRA|SHSN|SHGR|SHGS|FZRA|FZDZ|TSRA|TSSN|TSPL|TSGR|TSGS|TSSH)')
        weather_pattern = re.compile(r'(SQ|PO|FC|TS|FG|FZFG|BLSN|BLSA|BLDU|DRSN|DRSA|DRDU)')
        weak_precipitation_pattern = re.compile(r'-(DZ|RA|SN|SG|PL|SHRA|SHSN|SHGR|SHGS)')

        ref_weathers = ref_weather.split()
        weathers = weather.split()

        def condition(weather):
            # 符合转折条件，不包括弱降水
            return weather_with_intensity_pattern.match(weather) and not weak_precipitation_pattern.match(weather) \
                or weather_pattern.match(weather)

        for w in weathers:
            # NSW 无法转折的天气
            if w == 'NSW' and set(ref_weathers) & set(['BR', 'HZ', 'FU', 'DU', '-RA', '-SN']) \
                or 'NSW' in ref_weathers and w in ['BR', 'HZ', 'FU', 'DU', '-RA', '-SN']:
                return False

            if w not in ref_weathers:
                return condition(w) or condition(ref_weather)

        return False

    @classmethod
    def cloud(cls, ref_cloud, cloud, thresholds=None):
        '''   
          当预报 BKN 或 OVC 云量的最低云层的云高抬升并达到或经过下列一个或多个数值，或降低并经过下列一个或多个数值时：
            1. 30 m、60 m、150 m 或 300 m
            2. 450 m（在有大量的按目视飞行规则的飞行时）

          当预报低于 450 m 的云层或云块的量的变化满足下列条件之一时：
            1. 从 SCT 或更少到 BKN、OVC
            2. 从 BKN、OVC 到 SCT 或更少

          当预报积雨云将发展或消失时
        '''
        pattern = cls.grammar_class.cloud
        thresholds = thresholds if thresholds else [1, 2, 5, 10, 15]
        cloud_cover = {'SKC': 0, 'FEW': 1, 'SCT': 2, 'BKN': 3, 'OVC': 4}

        ref_clouds = ref_cloud.split()
        clouds = cloud.split()

        # 同为 NSC
        if ref_cloud == 'NSC' and cloud == 'NSC':
            return False

        # 有积雨云 CB
        cb_pattern = re.compile(r'(FEW|SCT|BKN|OVC)(\d{3})(CB|TCU$)')
        matches = [cb_pattern.search(ref_cloud), cb_pattern.search(cloud)]

        if any(matches):
            if all(matches):
                return matches[0].group() != matches[1].group()
            return True

        def analyze(clouds):
            min_height = 999
            max_cover = 0
            for c in clouds:
                m = pattern.match(c)
                if m and m.group() != 'NSC':
                    if cloud_cover[m.group(1)] > 2:
                        min_height = min(min_height, int(m.group(2)))

                    if int(m.group(2)) < 15:
                        max_cover = max(max_cover, cloud_cover[m.group(1)])

            min_height = min_height if min_height < 15 else 0
            return min_height, max_cover

        min_height, max_cover = analyze(clouds)
        ref_min_height, ref_max_cover = analyze(ref_clouds)

        # 当预报 BKN 或 OVC 云量的最低云层的云高抬升并达到或经过下列一个或多个数值，或降低并经过下列一个或多个数值
        if any([ref_min_height, min_height]):
            return cls.compare(ref_min_height, min_height, thresholds)

        # 当预报低于 450 m 的云层或云块的量的变化满足下列条件之一
        if ref_max_cover > 2 and max_cover < 3 or ref_max_cover < 3 and max_cover > 2:
            return True

        return False


class Lexer(object):
    grammar_class = Grammar

    default_rules = [
        'sign', 'amend', 'icao', 'timez', 'period', 'prob', 'interval',
        'wind', 'vis', 'cavok', 'weather', 'cloud', 'vv', 'tmax', 'tmin'
    ]

    def __init__(self, part, grammar=None, **kwargs):
        if not grammar:
            grammar = self.grammar_class()
        self.grammar = grammar
        self.part = part
        self.tokens = OrderedDict()

        self.parse(part)

    def __repr__(self):
        return self.part

    def parse(self, part, rules=None):
        if not rules:
            rules = self.default_rules

        for key in rules:
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
            time = format_timez(self.tokens['timez']['text'])
            self.period = self.generate_period(period, time)

    def generate_period(self, period, time):
        self.period = format_period(period, time)
        return self.period

    def is_valid(self):
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
    default_rules = [
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

    def split(self):
        message = self.message.replace('=', '')
        elements = _split_pattern.split(message)
        self.primary = self.parse(elements[0])
        self.reference = self.primary.tokens

        if len(elements) > 1:
            becmg_index = [i for i, item in enumerate(elements) if item == 'BECMG']
            tempo_index = [i for i, item in enumerate(elements) if 'TEMPO' in item]

            for i, index in enumerate(becmg_index):
                e = elements[index] + elements[index+1]
                becmg = self.parse(e)
                becmg.generate_period(becmg.tokens['interval']['text'], self.primary.period[0])
                self.becmgs.append(becmg)

            for i, index in enumerate(tempo_index):
                e = elements[index] + elements[index+1]
                tempo = self.parse(e)
                tempo.generate_period(tempo.tokens['interval']['text'], self.primary.period[0])
                self.tempos.append(tempo)

        self.elements = [self.primary] + self.becmgs + self.tempos

    def regroup(self):
        self.becmgs.sort(key=lambda x: x.period[1])
        self.tempos.sort(key=lambda x: x.period[0])

        def group(becmgs, tempos):
            groups = []
            for becmg in becmgs:
                groups.append(becmg)
                for tempo in tempos:

                    if tempo.period[0] < becmg.period[1] < tempo.period[1]:
                        index = groups.index(becmg)
                        groups.insert(index, tempo)
                        groups.append(tempo)

                    if tempo.period[1] <= becmg.period[1] and tempo not in groups:
                        index = groups.index(becmg)
                        groups.insert(index, tempo)

                    if tempo.period[0] > becmg.period[1] and tempo not in groups:
                        groups.append(tempo)

            return groups

        def reduce(items):
            groups = []
            cache = []
            for e in items:
                sign = e.tokens['sign']['text']
                if sign == 'BECMG':
                    groups.append(e)
                    cache = []
                if sign == 'TEMPO':
                    if e not in cache:
                        groups.append(e)
                        cache.append(e)

            return groups

        self.groups = reduce(group(self.becmgs, self.tempos))
        return self.groups

    def validate(self):
        self.validate_combination(self.reference, self.primary.tokens)

        for e in self.groups:
            for key in e.tokens:
                if key not in self.reference:
                    e.tokens[key]['error'] = False
                    continue

                verify = getattr(self.validator, key, None)
                if verify:
                    legal = verify(self.reference[key]['text'], e.tokens[key]['text'])
                    e.tokens[key]['error'] = not legal

                    if e.tokens['sign'] == 'BECMG':
                        self.reference[key]['text'] = e.tokens[key]['text']

            self.validate_combination(self.reference, e.tokens)

        self.tips = list(set(self.tips))

        valids = [e.is_valid() for e in self.elements]
        return all(valids)

    def validate_combination(self, ref, tokens):
        combined = copy.deepcopy(ref)
        for key in tokens:
            if key in self.default_rules:
                if key in combined:
                    combined[key]['text'] = tokens[key]['text']
                else:
                    combined[key] = {'text': tokens[key]['text']}

        # 检查能见度和天气现象
        if 'vis' in tokens:
            vis = int(tokens['vis']['text'])
            ref_vis = int(ref['vis']['text'])

            if 'weather' in combined:
                weathers = combined['weather']['text'].split()

                if vis < 1000 and set(weathers) & set(['BR', '-DZ']):
                    tokens['vis']['error'] = True
                    if 'weather' in tokens:
                        tokens['weather']['error'] = True

                    self.tips.append('能见度小于 1000，BR -DZ 不能有')

                if 1000 < vis <= 5000 and set(weathers) & set(['FG', '+DZ']):
                    tokens['vis']['error'] = True
                    if 'weather' in tokens:
                        tokens['weather']['error'] = True

                    self.tips.append('能见度小于 5000, FG +DZ 不能有')
                
                if vis > 5000 and set(weathers) & set(['FG', 'FU', 'BR', 'HZ']):
                    if 'weather' in tokens:
                        tokens['weather']['error'] = True

                    self.tips.append('能见度大于 5000，FG、FU、BR、HZ 不能有')
            else:
                if max(ref_vis, vis) >= 1000 and min(ref_vis, vis) < 1000:
                    tokens['vis']['error'] = True
                    self.tips.append('能见度跨 1000 米时应变化天气现象')

                if vis <= 5000 and ref_vis > 5000:
                    tokens['vis']['error'] = True
                    self.tips.append('能见度降低到 5000 米以下时应有天气现象')

        # 检查阵性降水和积雨云
        if 'weather' in tokens:

            if 'cloud' in combined:
                weather = tokens['weather']['text']
                cloud = combined['cloud']['text']

                if ('TS' in weather or 'SH' in weather) and \
                    not ('CB' in cloud or 'TCU' in cloud):
                    tokens['weather']['error'] = True
                    self.tips.append('阵性降水应包含 CB 或者 TCU')

    def renderer(self, style='plain'):
        outputs = [e.renderer(style) for e in self.elements]

        if style == 'html':
            return '<br/>'.join(outputs)

        return '\n'.join(outputs)



if __name__ == '__main__':
    # print(Validator.clouds('SCT020', 'SCT010 FEW023CB'))
    # print(Validator.weather('NSW', 'BR'))
    # print(Validator.wind('03008G13MPS', '36005MPS'))
    # print(Validator.vv('VV005', 'VV003'))
    message = '''
        TAF AMD ZGGG 211338Z 211524 14004MPS 4500 -RA BKN030
        BECMG 2122 2500 BR BKN012
        TEMPO 1519 07005MPS=
    '''
    # m = Grammar.taf.search(message)
    # print(m.group(0))
    # m = Grammar.timez.search(message)
    # print(m.groups())

    e = Parser(message)
    is_valid = e.validate()
    print(is_valid)

    print(e.renderer(style='terminal'))

    # print(e.tips)

    # print(e.primary.tokens)
    # print(e.tempos[0].tokens)
