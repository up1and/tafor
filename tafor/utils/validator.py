import re
import copy

from collections import OrderedDict

from tafor.utils.convert import parseTimez, parseTimeInterval


weather = [
    'NSW', 'IC', 'FG', 'BR', 'SA', 'DU', 'HZ', 'FU', 'VA', 'SQ',
    'PO', 'FC', 'TS', 'FZFG', 'BLSN', 'BLSA', 'BLDU', 'DRSN', 'DRSA',
    'DRDU', 'MIFG', 'BCFG', 'PRFG'
]
weatherWithIntensity = [
    'DZ', 'RA', 'SN', 'SG', 'PL', 'DS', 'SS', 'TSRA', 'TSSN', 'TSPL',
    'TSGR', 'TSGS', 'SHRA', 'SHSN', 'SHGR', 'SHGS', 'FZRA', 'FZDZ'
]


def _purePattern(regex):
    pattern = regex.pattern
    if pattern.startswith('^'):
        pattern = pattern[1:]
    return pattern


class Pattern(object):
    date = r'(0[1-9]|[12][0-9]|3[0-1])([01][0-9]|2[0-3])([0-5][0-9])'
    wind = r'00000|(VRB|0[1-9]0|[12][0-9]0|3[0-6]0)(0[1-9]|[1-4][0-9]|P49)'
    gust = r'(0[1-9]|[1-4][0-9]|P49)'
    vis = r'(9999|[5-9]000|[01234][0-9]00|0[0-7]50)'
    cloud = r'(FEW|SCT|BKN|OVC)(00[1-9]|0[1-4][0-9]|050)'
    vv = r'VV(00[1-9]|010)'
    temp = r'M?([0-5][0-9])'
    hours = r'([01][0-9]|2[0-4])'
    interval = r'([01][0-9]|2[0-3])(0[1-9]|1[0-9]|2[0-4])'
    trendInterval = r'([01][0-9]|2[0-3])([0-5][0-9])|2400'
    time = r'([01][0-9]|2[0-3])([0-5][0-9])'

    aaa = r'(AA[A-Z])'
    ccc = r'(CC[A-Z])'

    latitude = r'(N|S)(90(0{2})?|[0-8]\d([0-5]\d)?)'
    longitude = r'(E|W)(180(0{2})?|((1[0-7]\d)|(0\d{2}))([0-5]\d)?)'
    fightLevel = r'([1-9]\d{2})'
    sequence = r'([A-Z]?\d{1,2})'


class TafGrammar(object):
    sign = re.compile(r'(TAF|BECMG|FM|TEMPO)\b')
    amend = re.compile(r'\b(AMD|COR)\b')
    icao = re.compile(r'\b((A|B|E|K|P|L|R|Y|U|V|Z)[A-Z]{3})\b')
    timez = re.compile(r'\b(0[1-9]|[12][0-9]|3[0-1])([01][0-9]|2[0-3])([0-5][0-9])Z\b')
    period = re.compile(r'\b(0[1-9]|[12][0-9]|3[0-1])(0009|0312|0615|0918|1221|1524|1803|2106|0024|0606|1212|1818)\b')
    cnl = re.compile(r'\b(CNL)\b')
    tmax = re.compile(r'\b(TXM?(\d{2})/(\d{2})Z)\b')
    tmin = re.compile(r'\b(TNM?(\d{2})/(\d{2})Z)\b')

    wind = re.compile(r'\b(?:00000|(VRB|0[1-9]0|[12][0-9]0|3[0-6]0)(0[1-9]|[1-4][0-9]|P49)(?:G(0[1-9]|[1-4][0-9]|P49))?)MPS\b')
    vis = re.compile(r'\b(9999|[5-9]000|[01234][0-9]00|0[0-7]50)\b')
    weather = re.compile(r'([-+]?({})\b)|(\b({})\b)'.format('|'.join(weatherWithIntensity), '|'.join(weather)))
    cloud = re.compile(r'\bSKC|NSC|(FEW|SCT|BKN|OVC|VV)(\d{3})(CB|TCU)?\b')
    cavok = re.compile(r'\bCAVOK\b')

    prob = re.compile(r'\b(PROB[34]0)\b')
    interval = re.compile(r'\b([01][0-9]|2[0-3])([01][0-9]|2[0-4])\b')


class SigmetGrammar(object):
    area = re.compile(r'(AREA\([1-9]{1}\))')
    latitude = re.compile(r'(N|S)(90(0{2})?|[0-8]\d([0-5]\d)?)')
    longitude = re.compile(r'(E|W)(180(0{2})?|((1[0-7]\d)|(0\d{2}))([0-5]\d)?)')
    fightLevel = re.compile(r'(FL[1-9]\d{2}/[1-9]\d{2})|(FL[1-9]\d{2})|(\d{4,5}FT)|(\d{4,5}M)|(SFC/FL[1-9]\d{2})')
    speed = re.compile(r'(\d{1,2})(KMH|KT)')
    obsTime = re.compile(r'(\d{4}Z)')
    typhoonRange = re.compile(r'(\d{1,3}KM)')
    sequence = re.compile(r'([A-Z]?\d{1,2})')
    valid = re.compile(r'(\d{6})/(\d{6})')
    longlat = re.compile(r'(E|W)(\d{5}|\d{3})-(N|S)(\d{4}|\d{2})')
    width = re.compile(r'(\d{1,3})NM')


class TafValidator(object):
    """根据行业标准验证 TAF 报文单项要素之间的转折

    :param kwargs: 额外参数

                    * `visHas5000=True` 开启能见度 5000 的验证
                    * `cloudHeightHas450=True` 开启云高 450 的验证

    """
    grammarClass = TafGrammar

    def __init__(self, **kwargs):

        self.visThresholds = [150, 350, 600, 800, 1500, 3000]
        self.cloudHeightThresholds = [1, 2, 5, 10]

        if kwargs.get('visHas5000', True):
            self.visThresholds.append(5000)

        if kwargs.get('cloudHeightHas450', True):
            self.cloudHeightThresholds.append(15)

    def wind(self, refWind, wind):
        """风组的转折验证

        1. 当预报平均地面风向的变化大于等于 60°，且平均风速在变化前和（或）变化后大于等于 5m/s 时
        2. 当预报平均地面风速的变化大于等于 5m/s 时
        3. 当预报平均地面风风速变差（阵风）变化 5m/s 或以上，且平均风速在变化前和变化后大于等于 8m/s 时

        :param refWind: 参照风组
        :param wind: 风组
        :returns: 验证是否通过
        """
        pattern = self.grammarClass.wind
        refWindMatch = pattern.match(refWind)
        windMatch = pattern.match(wind)

        def splitWind(m):
            # 考虑静风的特殊情况
            if m.group() == '00000MPS':
                return 360, 0, None

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

        # 1. 当预报平均地面风向的变化大于等于 60°，且平均风速在变化前和（或）变化后大于等于 5m/s 时
        if angle(refDirection, direction) and max(refSpeed, speed) >= 5:
            return True

        # 2. 当预报平均地面风速的变化大于等于 5m/s 时
        if abs(refSpeed - speed) >= 5:
            return True

        # 3. 当预报平均地面风风速变差（阵风）变化 5m/s 或以上，且平均风速在变化前和变化后大于等于 8m/s 时
        if refGust and gust and abs(refGust - gust) >= 5 and max(refSpeed, speed) >= 8:
            return True

        if refGust != gust and max(refSpeed, speed) >= 8:
            return True

        return False

    def vis(self, refVis, vis):
        """能见度的转折验证

        1. 当预报主导能见度上升并达到或经过下列一个或多个数值，或下降并经过下列一个或多个数值时：
            * 150 m、350 m、600 m、800 m、1500 m 或 3000 m
            * 5000 m（当有大量的按目视飞行规则的飞行时）

        :param refWind: 参照能见度
        :param wind: 能见度
        :returns: 验证是否通过
        """
        thresholds = self.visThresholds
        return self.compare(refVis, vis, thresholds)

    def compare(self, refValue, value, thresholds):
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

    def weather(self, refWeather, weather):
        """天气现象的转折验证

        1. 当预报下列一种或几种天气现象开始、终止或强度变化时：
            * 冻降水
            * 中或大的降水（包括阵性降水）包括雷暴
            * 尘暴
            * 沙暴

        2. 当预报下列一种或几种天气现象开始、终止时：
            * 冻雾
            * 低吹尘、低吹沙或低吹雪
            * 高吹尘、高吹沙或高吹雪
            * 雷暴（伴或不伴有降水）
            * 飑
            * 漏斗云（陆龙卷或水龙卷）

        :param refWeather: 参照天气现象
        :param weather: 天气现象
        :returns: 验证是否通过
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

    def cloud(self, refCloud, cloud):
        '''云的转折验证

        1. 当预报 BKN 或 OVC 云量的最低云层的云高抬升并达到或经过下列一个或多个数值，或降低并经过下列一个或多个数值时：
            * 30 m、60 m、150 m 或 300 m
            * 450 m（在有大量的按目视飞行规则的飞行时）

        2. 当预报低于 450 m 的云层或云块的量的变化满足下列条件之一时：
            * 从 SCT 或更少到 BKN、OVC
            * 从 BKN、OVC 到 SCT 或更少

        3. 当预报积雨云将发展或消失时

        垂直能见度的转折验证，垂直能见度可视为一种特殊的云

        1. 当预报垂直能见度上升并达到或经过下列一个或多个数值，或下降并经过下列一个或多个数值时：
            * 30 m、60 m、150 m 或 300 m，编报时对应 VV001、VV002、VV005、VV010

        :param refCloud: 参照云组
        :param cloud: 云组
        :returns: 验证是否通过
        '''
        pattern = self.grammarClass.cloud
        thresholds = self.cloudHeightThresholds
        cloudCover = {'SKC': 0, 'FEW': 1, 'SCT': 2, 'BKN': 3, 'OVC': 4, 'VV': 4}

        refClouds = refCloud.split()
        clouds = cloud.split()

        # 云组无变化
        if refCloud == cloud:
            return False

        # 有积雨云 CB
        cbPattern = re.compile(r'(FEW|SCT|BKN|OVC)(\d{3})(CB|TCU)')
        matches = [cbPattern.search(refCloud), cbPattern.search(cloud)]

        if any(matches):
            if all(matches):
                # 积雨云将发展或消失
                if matches[0].group() != matches[1].group():
                    return True
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
            return self.compare(refMinHeight, minHeight, thresholds)

        # 当预报低于 450 m 的云层或云块的量的变化满足下列条件之一
        if refMaxCover > 2 and maxCover < 3 or refMaxCover < 3 and maxCover > 2:
            return True

        return False

    def cavok(self, vis, weather, cloud):
        '''CAVOK 的转折验证

        :param vis: 能见度
        :param weather: 天气现象
        :param cloud: 云组
        :returns: 验证是否通过
        '''
        validations = [
            self.vis(vis, 9999),
            self.weather(weather, 'NSW'),
            self.cloud(cloud, 'NSC')
        ]

        return all(validations)


class TafLexer(object):
    """TAF 报文一组要素的解析器

    :param part: 单组主报文 BECMG 或 TEMPO
    :param grammar: 解析 TAF 报文的语法类
    :param kwargs: 额外参数
    """
    grammarClass = TafGrammar

    defaultRules = [
        'prob', 'sign', 'amend', 'icao', 'timez', 'period', 'interval', 'cnl',
        'wind', 'vis', 'cavok', 'weather', 'cloud', 'tmax', 'tmin'
    ]

    def __init__(self, part, grammar=None, **kwargs):
        if not grammar:
            grammar = self.grammarClass()
        self.grammar = grammar
        self.part = part.strip()
        self.tokens = OrderedDict()

        self.parse(part)

    def __repr__(self):
        return '<TafLexer {}>'.format(self.part)

    @property
    def sign(self):
        return self.tokens['sign']['text']

    def parse(self, part, rules=None):
        if not rules:
            rules = self.defaultRules

        for key in rules:
            if 'TAF' in self.part and key == 'interval' or 'TAF' not in self.part and key == 'icao':
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
            period = self.tokens['period']['text'][2:]
            time = parseTimez(self.tokens['timez']['text'])
            self.period = parseTimeInterval(period, time)

    def isValid(self):
        """检查报文是否有错误

        :return: 报文是否通过验证
        """
        for k, e in self.tokens.items():
                if e['error']:
                    return False
        
        return True

    def renderer(self, style='plain'):
        """将解析后的报文重新渲染

        :param style:
            * plain 纯字符串风格
            * terminal 终端高亮风格
            * html HTML 高亮风格
        :return: 根据不同风格重新渲染的报文
        """
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
            elements = [e['text'] for _, e in self.tokens.items()]
            return ' '.join(elements)

        func = locals().get(style, plain)
        return func()


class TafParser(object):
    """解析 TAF 报文

    :param message: TAF 报文
    :param parse: 解析报文的类，默认 :class:`TafLexer`
    :param validator: 验证报文转折关系的类，默认 :class:`TafValidator`
    :param kwargs: 额外参数

    使用方法::

        p = TafParser('TAF ZJHK 150726Z 150918 03003G10MPS 1600 BR OVC040 BECMG 1112 4000 BR=')
        p.validate()

        # 报文是否通过验证
        p.isValid()

        # 报文重新渲染成 HTML 格式，并高亮标注出错误
        p.renderer(style='html')
        
    """

    defaultRules = [
        'wind', 'vis', 'weather', 'cloud'
    ]

    def __init__(self, message, parse=None, validator=None, **kwargs):
        self.message = message
        self.becmgs = []
        self.tempos = []
        self.tips = []

        self.reference = None

        if not parse:
            self.parse = TafLexer

        if not validator:
            self.validator = TafValidator(**kwargs)

        self.split()

    def __eq__(self, other):
        """判断两份报文是否相等"""
        if isinstance(other, self.__class__):
            return self.renderer() == other.renderer()
        return False

    def split(self):
        """拆分主报文和变化组"""
        message = self.message.replace('=', '')
        splitPattern = re.compile(r'(BECMG|FM|TEMPO|PROB[34]0\sTEMPO)')
        elements = splitPattern.split(message)
        self.primary = self.parse(elements[0])

        if len(elements) > 1:
            becmgIndex = [i for i, item in enumerate(elements) if item == 'BECMG']
            tempoIndex = [i for i, item in enumerate(elements) if 'TEMPO' in item]

            for index in becmgIndex:
                e = elements[index] + elements[index+1]
                becmg = self.parse(e)
                becmg.period = parseTimeInterval(becmg.tokens['interval']['text'], self.primary.period[0])
                self.becmgs.append(becmg)

            for index in tempoIndex:
                e = elements[index] + elements[index+1]
                tempo = self.parse(e)
                tempo.period = parseTimeInterval(tempo.tokens['interval']['text'], self.primary.period[0])
                self.tempos.append(tempo)

        self.elements = [self.primary] + self.becmgs + self.tempos

    def regroup(self):
        """根据报文的时序重新分组 TEMPO BECMG"""
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

            if not becmgs:
                groups = tempos

            return groups

        def reduce(items):
            """去除分组中重复的元素"""
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

    def refs(self):
        """生成参照组"""
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

    def validate(self):
        """验证报文转折逻辑"""
        self.regroup()
        self.refs()

        # 验证主报文多个要素匹配
        self.validateMutiElements(self.reference, self.primary.tokens)

        for e in self.groups:
            for key in e.tokens:
                # 依次验证单项要素转折
                verify = getattr(self.validator, key, None)
                if verify:
                    if key == 'cavok':
                        legal = verify(self.reference['vis']['text'], self.reference['weather']['text'], self.reference['cloud']['text'])
                    else:
                        legal = verify(self.reference[key]['text'], e.tokens[key]['text'])

                    if key == 'weather' and 'vis' in e.tokens and not e.tokens['vis']['error'] or e.tokens[key]['error']:
                        # 引起能见度变化的天气现象
                        # 天气现象已判断为有误
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

            # 验证参照组与转折组之间多个要素匹配
            self.validateMutiElements(self.reference, e.tokens)

        self.tips = list(set(self.tips))

    def validateMutiElements(self, ref, tokens):
        """验证多个元素之间的匹配规则

        1. 能见度和天气现象
            * 能见度跨 1000 米时应变化天气现象
            * 能见度小于 5000 米时应有天气现象
            * 能见度小于 1000 米，BR、-DZ 不能有
            * 能见度大于 1000 米、小于 5000 米，FG、+DZ 不能有
            * 能见度大于 5000 米，FG、FU、BR、HZ 不能有

        2. 天气现象
            * 阵性降水应包含 CB
            * NSW 不能和其他天气现象同时存在
            * BR，HZ，FG，FU 不能同时存在

        3. 云组
            * 云组第二层云量不能为 FEW
            * 云组第三层云量不能为 FEW 或 SCT

        :param ref: 报文参照组
        :param tokens: 当前报文解析后的要素， `OrderedDict`
        """
        mixture = copy.deepcopy(ref)
        for key in tokens:
            if key in self.defaultRules:
                mixture[key]['text'] = tokens[key]['text']

        # 检查能见度和天气现象
        if 'vis' in tokens:
            vis = int(tokens['vis']['text'])
            weathers = mixture['weather']['text'].split()

            if 'NSW' in weathers:
                if vis <= 5000:
                    tokens['vis']['error'] = True
                    self.tips.append('能见度小于 5000 米时应有天气现象')

            else:
                if vis < 1000 and set(weathers) & set(['BR', '-DZ']):
                    if 'weather' in tokens:
                        tokens['weather']['error'] = True
                    else:
                        tokens['vis']['error'] = True

                    self.tips.append('能见度小于 1000 米，BR、-DZ 不能有')

                if 1000 <= vis <= 5000 and set(weathers) & set(['FG', '+DZ']):
                    if 'weather' in tokens:
                        tokens['weather']['error'] = True
                    else:
                        tokens['vis']['error'] = True

                    self.tips.append('能见度大于 1000 米、小于 5000 米，FG、+DZ 不能有')

                if vis > 5000 and set(weathers) & set(['FG', 'FU', 'BR', 'HZ']):
                    if 'weather' in tokens:
                        tokens['weather']['error'] = True
                        self.tips.append('能见度大于 5000 米，FG、FU、BR、HZ 不能有')

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

            weatherCount = set(weathers) & set(['BR', 'HZ', 'FG', 'FU'])
            if len(weatherCount) > 1:
                tokens['weather']['error'] = True
                self.tips.append('BR，HZ，FG，FU 不能同时存在')


        if 'cloud' in tokens:
            # 检查云组转折天气现象的匹配
            weather = mixture['weather']['text']
            cloud = tokens['cloud']['text']
            if ('TS' in weather or 'SH' in weather) and 'CB' not in cloud:
                tokens['cloud']['error'] = True
                self.tips.append('阵性降水应包含 CB')

            # 不同高度云组云量的验证
            clouds = [c for c in cloud.split() if 'CB' not in c]

            for i, cloud in enumerate(clouds):
                if i == 1 and 'FEW' in cloud:
                    tokens['cloud']['error'] = True
                    self.tips.append('云组第二层云量不能为 FEW')

                if i == 2 and ('FEW' in cloud or 'SCT' in cloud):
                    tokens['cloud']['error'] = True
                    self.tips.append('云组第三层云量不能为 FEW 或 SCT')

    def isValid(self):
        """报文是否通过验证"""
        valids = [e.isValid() for e in self.elements]
        return all(valids)

    def isAmended(self):
        """报文是否是修订报或者更正报"""
        return 'COR' in self.message or 'AMD' in self.message

    def hasMessageChanged(self):
        """校验后的报文和原始报文相比是否有变化"""
        origin = self.message.replace('\n', ' ')
        output = self.renderer().replace('\n', ' ')
        return origin != output

    def renderer(self, style='plain'):
        """将解析后的报文重新渲染

        :param style:
            * plain 纯字符串风格
            * terminal 终端高亮风格
            * html HTML 高亮风格
        :return: 根据不同风格重新渲染的报文
        """
        outputs = [e.renderer(style) for e in self.elements]

        if style == 'html':
            return '<br/>'.join(outputs) + '='

        return '\n'.join(outputs) + '='


class SigmetLexer(object):
    """SIGMET 报文要素的解析器

    :param part: 单行保温内容
    :param grammar: 解析 SIGMET 报文的语法类
    :param keywords: SIGMET 报文允许的关键字
    :param isFirst: 是否是正文的第一组
    :param kwargs: 额外参数
    """
    grammarClass = SigmetGrammar

    defaultKeywords = ['OBSC', 'EMBD', 'FRQ', 'SQL', 'SEV', 'HVY',
        'TS', 'TSGR', 'ICE', 'TURB', 'TC', 'VA', 'MTW', 'DS', 'SS', '(FZRA)', 'RDOACT', 'CLD',
        'ERUPTION', 'MT', 'LCA', 'LOC', 'WID', 'NO', 'EXP', 'APRX', 'BY',
        'OBS', 'FCST', 'AT', 'TOP', 'ABV', 'BLW', 'BTN', 'SFC', 'PSN', 'CENTRE', 'CENTER',
        'N', 'NE', 'NNE', 'NNW', 'E', 'ENE', 'ESE', 'SE', 'SSE', 'SSW', 'S', 'SW', 'W', 'NW', 'WNW', 'WSW',
        'MOV', 'STNR', 'AND', 'OF', 'WKN', 'NC', 'INTSF',
        'LINE', 'WI', '-', 'CNL', 'TO', 'ENTIRE', 'CB', 'SIGMET',
        'FIR', 'FIR/UIR', 'CTA'
    ]

    defaultRules = ['area', 'latitude', 'longitude', 'fightLevel', 'speed', 'obsTime', 'typhoonRange', 'sequence', 'valid', 'longlat', 'width']

    def __init__(self, part, firCode=None, airportCode=None, grammar=None, keywords=None, **kwargs):
        super(SigmetLexer, self).__init__()
        if not grammar:
            grammar = self.grammarClass()

        if not keywords:
            keywords = self.defaultKeywords

        if airportCode:
            keywords.append(airportCode)

        self.grammar = grammar
        self.keywords = keywords
        self.firCode = firCode
        self.part = part.strip()
        self.tokens = []

        self.parse(part)

    def __repr__(self):
        return '<SigmetLexer {}>'.format(self.part)

    def parse(self, part):
        """解析报文要素字符是否正确"""
        if self.firCode and part.startswith(self.firCode):
            part = part[len(self.firCode):].strip()
            parts = [self.firCode] + part.split()
        else:
            parts = part.split()

        for i, text in enumerate(parts):
            error = True
            if text in self.keywords or self.isMatch(text) or self.isSpecialName(i, parts):
                error = False

            self.tokens.append({
                'text': text,
                'error': error
            })

    def isMatch(self, text):
        """检查字符是否被特殊的正则表达式匹配

        :return: 是否正确匹配
        """
        rules = self.defaultRules
        for key in rules:
            pattern = getattr(self.grammar, key)
            m = pattern.match(text)
            if m:
                if m.group() == text:
                    return True

    def isSpecialName(self, index, parts):
        """检查字符是否是特殊名字，如情报区名、热带气旋名、火山名

        :return: 是否是特殊名字
        """
        try:
            if parts[index-1] in ['TC', 'MT'] or parts[index] == self.firCode:
                return True

        except IndexError:
            pass

    def isValid(self):
        """检查报文是否有错误

        :return: 报文是否通过验证
        """
        for e in self.tokens:
                if e['error']:
                    return False

        return True

    def renderer(self, style='plain'):
        """将解析后的报文重新渲染

        :param style:
            * plain 纯字符串风格
            * terminal 终端高亮风格
            * html HTML 高亮风格
        :return: 根据不同风格重新渲染的报文
        """
        def terminal():
            from colorama import init, Fore
            init(autoreset=True)

            elements = []
            for e in self.tokens:
                if e['error']:
                    elements.append(Fore.RED + e['text'])
                else:
                    elements.append(Fore.GREEN + e['text'])

            return ' '.join(elements)

        def html():
            elements = []
            for e in self.tokens:
                if e['error']:
                    elements.append('<span style="color: red">{}</span>'.format(e['text']))
                else:
                    elements.append(e['text'])

            return ' '.join(elements)

        def plain():
            return self.part

        func = locals().get(style, plain)
        return func()


class SigmetParser(object):
    """解析 SIGMET 报文

    :param message: SIGMET 报文
    :param parse: 解析报文的类，默认 :class:`SigmetLexer`
    :param kwargs: 额外参数
                * `firCode` 气象情报编码前缀
                * `airportCode` 发布机场编码

    使用方法::

        p = SigmetParser('ZJSA SIGMET 1 VALID 300855/301255 ZJHK-
                        ZJSA SANYA FIR VA ERUPTION MT ASHVAL LOC E S1500 E07348 VA CLD OBS AT 1100Z FL310/450
                        APRX 220KM BY 35KM S1500 E07348 - S1530 E07642 MOV ESE 65KMH
                        FCST 1700Z VA CLD APRX S1506 E07500 - S1518 E08112 - S1712 E08330 - S1824 E07836=',
                        firCode='ZJSA SANYA FIR')

        # 报文字符是否通过验证
        p.isValid()

        # 报文重新渲染成 HTML 格式，并高亮标注出错误
        p.renderer(style='html')

    """
    def __init__(self, message, parse=None, **kwargs):
        self.message = message.strip()

        if not parse:
            self.parse = SigmetLexer

        self.firCode = kwargs.get('firCode')
        self.airportCode = kwargs.get('airportCode')

        self.split()

    def split(self):
        """拆分报头和报文内容"""
        message = self.message.replace('=', '')
        splitPattern = re.compile(r'([A-Z]{4}-)')
        *heads, elements = splitPattern.split(message)
        self.heads = [e.strip() for e in ''.join(heads).split('\n')]
        elements = elements.strip().split('\n')
        self.elements = [self.parse(e, firCode=self.firCode, airportCode=self.airportCode) for e in elements]

    def isValid(self):
        """报文是否通过验证"""
        valids = [e.isValid() for e in self.elements]
        return all(valids)

    def hasMessageChanged(self):
        return False

    def renderer(self, style='plain'):
        """将解析后的报文重新渲染

        :param style:
            * plain 纯字符串风格
            * terminal 终端高亮风格
            * html HTML 高亮风格
        :return: 根据不同风格重新渲染的报文
        """
        outputs = self.heads + [e.renderer(style) for e in self.elements]

        if style == 'html':
            return '<br/>'.join(outputs) + '='

        return '\n'.join(outputs) + '='

