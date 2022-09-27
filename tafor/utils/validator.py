import re
import copy
import datetime

from collections import OrderedDict

from tafor import logger
from tafor.utils.convert import parseTimez, parsePeriod, parseTime, degreeToDecimal


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
    vis = r'(9999|[5-9]000|[0-4][0-9]00|0[0-7]50)'
    cloud = r'(FEW|SCT|BKN|OVC)(00[1-9]|0[1-4][0-9]|050)'
    vv = r'VV(00[1-9]|010)'
    temperature = r'M?([0-5][0-9])'
    dayHour = r'(0[1-9]|[12][0-9]|3[0-1])([01][0-9]|2[0-4])'
    period = r'(0[1-9]|[12][0-9]|3[0-1])([01][0-9]|2[0-3])/(0[1-9]|[12][0-9]|3[0-1])([01][0-9]|2[0-4])'
    fmPeriod = r'(0[1-9]|[12][0-9]|3[0-1])([01][0-9]|2[0-3])([0-5][0-9])'
    trendPeriod = r'([01][0-9]|2[0-3])([0-5][0-9])|2400'
    trendFmTlPeriod = r'([01][0-9]|2[0-3])([0-5][0-9])/(0[1-9]|1[0-9]|2[0-3])([0-5][0-9])|2400'
    time = r'([01][0-9]|2[0-3])([0-5][0-9])'

    aaa = r'(AA[A-Z])'
    ccc = r'(CC[A-Z])'

    latitude = r'(N|S)(90(0{2})?|[0-8]\d([0-5]\d)?)'
    longitude = r'(E|W)(180(0{2})?|((1[0-7]\d)|(0\d{2}))([0-5]\d)?)'
    sequence = r'[A-Z]?([1-9][0-9]?|0[1-9])'


class TafGrammar(object):
    sign = re.compile(r'\b(TAF|BECMG|(?:FM(?:\d{4}|\d{6}))|TEMPO)\b')
    amend = re.compile(r'\b(AMD|COR)\b')
    icao = re.compile(r'\b((A|B|E|K|P|L|R|Y|U|V|Z)[A-Z]{3})\b')
    timez = re.compile(r'\b(0[1-9]|[12][0-9]|3[0-1])([01][0-9]|2[0-3])([0-5][0-9])Z\b')
    period = re.compile(r'\b((?:\d{4}/\d{4})|(?:\d{6})|(?:[01][0-9]|2[0-3])(?:[01][0-9]|2[0-4]))\b')
    cnl = re.compile(r'\b(CNL)\b')
    temperature = re.compile(r'\b(T(?:X|N)M?(\d{2})/(\d{2}|\d{4})Z)\b')

    wind = re.compile(r'\b(VRB|0[0-9]0|[12][0-9]0|3[0-6]0)(0[0-9]|[1-4][0-9]|P49)(?:G(0[1-9]|[1-4][0-9]|P49))?(?:MPS|KT)\b')
    vis = re.compile(r'\b(?<!/)(9999|[5-9]000|[0-4][0-9]00|0[0-7]50)(?!/)\b')
    weather = re.compile(r'([-+]?\b({})\b)|(\b({})\b)'.format('|'.join(weatherWithIntensity), '|'.join(weather)))
    cloud = re.compile(r'\b(?:SKC|NSC|(FEW|SCT|BKN|OVC)(\d{3})(CB|TCU)?)\b|\b(?:(VV)(///|\d{3}\b))')
    cavok = re.compile(r'\bCAVOK\b')

    prob = re.compile(r'\b(PROB[34]0)\b')


class MetarGrammar(TafGrammar):
    sign = re.compile(r'\b(METAR|SPECI|BECMG|TEMPO)\b')
    amend = re.compile(r'\b(COR)\b')
    auto = re.compile(r'\b(AUTO|NIL)\b')
    rvr = re.compile(r'\b(R\d{2}[A-Z]?/[A-Z]?\d{4}[A-Z]?\d{0,4}[A-Z]?)\b')
    windrange = re.compile(r'\b(\d{3}V\d{3})\b')
    tempdew = re.compile(r'\b(M?\d{2}/(?:M)?\d{2})\b')
    pressure = re.compile(r'\b(Q\d{4})\b')
    reweather = re.compile(r'\b(RE\w+)\b')
    windshear = re.compile(r'\b(WS\s(?:(?:ALL\sRWY)|(?:R\d{2})))\b')
    nosig = re.compile(r'\bNOSIG\b')
    fmtl = re.compile(r'\b((?:AT|FM|TL)\d{4})\b')


class SigmetGrammar(object):
    latitude = re.compile(r'(N|S)(90(0{2})?|[0-8]\d([0-5]\d)?)')
    longitude = re.compile(r'(E|W)(180(0{2})?|((1[0-7]\d)|(0\d{2}))([0-5]\d)?)')
    flightLevel = re.compile(r'(FL(?:[1-9]\d{2}|0[1-9]\d|00[1-9])/[1-9]\d{2})|(FL[1-9]\d{2})|(\d{4,5}FT)|(\d{4,5}M)|(SFC/FL[1-9]\d{2})')
    speed = re.compile(r'(\d{1,3})(KMH|KT)')
    obsTime = re.compile(r'(\d{4}Z)')
    typhoonRange = re.compile(r'(\d{1,3}KM)')
    sequence = re.compile(r'([A-Z]?\d{1,2})')
    valid = re.compile(r'(\d{6})/(\d{6})')
    width = re.compile(r'(\d{1,3})NM')

    wind = re.compile(r'(0[1-9]0|[12][0-9]0|3[0-6]0)/(1[5-9]|[2-4][0-9]|P49)(MPS|KT)')
    vis = re.compile(r'(9999|5000|[01234][0-9]00|0[0-7]50)(M|FT)')
    cloud = re.compile(r'((?:\d{3,4}|SFC)/(?:ABV)?\d{3,5}(?:M|FT))')

    _point = r'((?:N|S)(?:\d{4}|\d{2}))\s((?:E|W)(?:\d{5}|\d{3}))'
    _pointSpacer = r'\s?-\s?'
    _radius = r'WI\s(\d{1,3})(KM|NM)\sOF\s(?:TC\s)?(?:CENTRE|CENTER)'

    @property
    def point(self):
        return re.compile(self._point)

    @property
    def radius(self):
        return re.compile(self._radius)

    @property
    def line(self):
        pattern = re.compile(
            r'(N|NE|E|SE|S|SW|W|NW)'
            r'\sOF\sLINE\s'
            r'(%s(?:%s)?)+' % (self._point, self._pointSpacer)
        )
        return pattern

    @property
    def lines(self):
        pattern = re.compile(
            r'({}(?:\sAND\s)?)+'.format(_purePattern(self.line))
        )
        return pattern

    @property
    def polygon(self):
        pattern = re.compile(
            r'(WI\s(?:{}(?:{})?)+)'.format(self._point, self._pointSpacer)
        )
        return pattern

    @property
    def corridor(self):
        pattern = re.compile(
            r'APRX\s(\d{1,3})(KM|NM)'
            r'\sWID\sLINE\sBTN\s'
            r'(%s(?:%s)?)+' % (self._point, self._pointSpacer)
        )
        return pattern

    @property
    def rectangular(self):
        pattern = re.compile(
            r'(?:(N|S)\sOF\s((?:N|S)(?:\d{4}|\d{2}))|(W|E)\sOF\s((?:W|E)(?:\d{5}|\d{3})))'
        )
        return pattern

    @property
    def rectangulars(self):
        pattern = re.compile(
            r'({}(?:\sAND\s)?)+'.format(_purePattern(self.rectangular))
        )
        return pattern

    @property
    def position(self):
        return re.compile(r'PSN\s{}'.format(self._point))


class AdvisoryGrammar(object):
    name = re.compile(r'\b([A-Z-]+)\b')
    time = re.compile(r'(\d{2})/(\d{2})(\d{2})Z')
    flightLevel = re.compile(r'(FL[1-9]\d{2}/[1-9]\d{2})|(FL[1-9]\d{2})|(\d{4,5}FT)|(\d{4,5}M)|(SFC/FL[1-9]\d{2})')
    height = re.compile(r'TOP\sFL(\d+)')
    movement = re.compile(r'\b(STNR|N|NNE|NE|ENE|E|ESE|SE|SSE|S|SSW|SW|WSW|W|WNW|NW|NNW)\b')
    speed = re.compile(r'(\d{1,2})(KMH|KT)')

    _point = r'((?:N|S)(?:\d{4}|\d{2}))\s((?:E|W)(?:\d{5}|\d{3}))'
    _pointSpacer = r'\s?-\s?'

    @property
    def point(self):
        return re.compile(self._point)

    @property
    def polygon(self):
        pattern = re.compile(
            r'(?:{}(?:{})?)+'.format(self._point, self._pointSpacer)
        )
        return pattern


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
        self.weakPrecipitationVerification = False

        if kwargs.get('visHas5000', True):
            self.visThresholds.append(5000)

        if kwargs.get('cloudHeightHas450', True):
            self.cloudHeightThresholds.append(15)

        if kwargs.get('weakPrecipitationVerification', False):
            self.weakPrecipitationVerification = True

    def wind(self, refWind, wind):
        """风组的转折验证

        1. 当预报平均地面风向的变化大于等于 60°，且平均风速在变化前和（或）变化后大于等于 5m/s 时
        2. 当预报平均地面风速的变化大于等于 5m/s 时
        3. 当预报地面风的阵风变化大于等于 5m/s，且变化前和（或）变化后的平均风速大于等于 8m/s 时

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

        # 3. 当预报地面风的阵风变化大于等于 5m/s，且变化前和（或）变化后的平均风速大于等于 8m/s 时
        if refGust and gust and abs(refGust - gust) >= 5 and max(refSpeed, speed) >= 8:
            return True

        if any([refGust, gust]) and None in [refGust, gust] and max(refSpeed, speed) >= 8:
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
            * 中或大降水（需要时可以包含阵性或非阵性的小雨或小雪）
            * 尘暴
            * 沙暴

        2. 当预报下列一种或几种天气现象开始、终止时：
            * 冻雾
            * 低吹尘、低吹沙或低吹雪
            * 高吹尘、高吹沙或高吹雪
            * 雷暴
            * 飑
            * 漏斗云（陆龙卷或水龙卷）

        :param refWeather: 参照天气现象
        :param weather: 天气现象
        :returns: 验证是否通过
        """
        weatherWithIntensityPattern = re.compile(r'([+-])?(DZ|RA|SN|SG|PL|DS|SS|SHRA|SHSN|SHGR|SHGS|FZRA|FZDZ|TSRA|TSSN|TSPL|TSGR|TSGS|TSSH)')
        weatherPattern = re.compile(r'(SQ|PO|FC|TS|FZFG|BLSN|BLSA|BLDU|DRSN|DRSA|DRDU)')
        weakPrecipitationPattern = re.compile(r'-(DZ|RA|SN|SG|PL|SHRA|SHSN|SHGR|SHGS)')

        def condition(weather):
            # 根据弱降水是否参与验证判断符合转折条件
            if self.weakPrecipitationVerification:
                precipitation = weatherWithIntensityPattern.search(weather)
            else:
                precipitation = weatherWithIntensityPattern.search(weather) and not weakPrecipitationPattern.search(weather)

            return precipitation or weatherPattern.search(weather)

        if condition(weather) or condition(refWeather):

            if condition(weather) and condition(refWeather):
                refWeathers = refWeather.split()
                weathers = weather.split()
                common = set(weathers) & set(refWeathers)
                if condition(' '.join(common)):
                    return False

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
                    if 'VV' in m.group():
                        cov, height = m.group(4), int(m.group(5))
                    else:
                        cov, height = m.group(1), int(m.group(2))

                    if cloudCover[cov] > 2:
                        minHeight = min(minHeight, height)

                    if height < 15:
                        maxCover = max(maxCover, cloudCover[cov])

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
        'prob', 'sign', 'amend', 'icao', 'timez', 'period', 'cnl',
        'wind', 'vis', 'cavok', 'weather', 'cloud', 'temperature'
    ]

    def __init__(self, part, grammar=None, **kwargs):
        if not grammar:
            grammar = self.grammarClass()
        self.grammar = grammar
        self.part = part.strip()
        self.tokens = OrderedDict()
        self.period = None
        self.order = 0

        self.parse(part)

    def __repr__(self):
        return '<{} {!r}>'.format(self.__class__.__name__, self.part)

    def __bool__(self):
        return bool(self.part)

    @property
    def sign(self):
        return self.tokens['sign']['text']

    def parse(self, part, rules=None):
        if not rules:
            rules = self.defaultRules

        for key in rules:
            if self.part.startswith('FM') and key == 'period' or not self.part.startswith(('TAF', 'METAR', 'SPECI')) and key == 'icao':
                continue

            pattern = getattr(self.grammar, key)
            m = pattern.search(part)
            if not m:
                continue

            if key in ('weather', 'cloud', 'temperature', 'fmtl', 'rvr'):
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

    validatorClass = TafValidator
    
    lexerClass = TafLexer

    defaultRules = [
        'wind', 'vis', 'weather', 'cloud'
    ]

    splitPattern = re.compile(r'(BECMG|(?:FM(?:\d{4}|\d{6}))|TEMPO|PROB[34]0\sTEMPO)')

    def __init__(self, message, parse=None, validator=None, **kwargs):
        message = message.strip()
        if not message.endswith('='):
            message = message + '='
        self.message = message
        self.becmgs = []
        self.tempos = []
        self.errors = []
        self.failed = False

        self.reference = None

        if not parse:
            self.parse = self.lexerClass

        if not validator:
            self.validator = self.validatorClass(**kwargs)

        self._split()

    def __eq__(self, other):
        """判断两份报文是否相等"""
        if isinstance(other, self.__class__):
            return self.renderer() == other.renderer()
        return False

    def __repr__(self):
        return '<{} {!r}>'.format(self.__class__.__name__, self.renderer())

    def _split(self):
        """拆分主报文和变化组"""
        message = self.message.replace('=', '')
        elements = self.splitPattern.split(message)
        self.primary = self.parse(elements[0])

        if len(elements) > 1:
            becmgIndex = [i for i, item in enumerate(elements) if item == 'BECMG']
            fmIndex = [i for i, item in enumerate(elements) if item.startswith('FM')]
            tempoIndex = [i for i, item in enumerate(elements) if 'TEMPO' in item]

            for index in becmgIndex:
                e = elements[index] + elements[index+1]
                becmg = self.parse(e)
                becmg.order = index
                self.becmgs.append(becmg)

            for index in fmIndex:
                e = elements[index] + elements[index+1]
                fm = self.parse(e)
                fm.order = index
                self.becmgs.append(fm)

            for index in tempoIndex:
                e = elements[index] + elements[index+1]
                tempo = self.parse(e)
                tempo.order = index
                self.tempos.append(tempo)

        self.elements = [self.primary] + sorted(self.becmgs + self.tempos, key=lambda x: x.order)

    def _parsePeriod(self):
        """解析主报文和变化组的时间顺序"""
        if len(self.primary.tokens['period']['text']) not in [6, 9]:
            raise 

        time = parseTimez(self.primary.tokens['timez']['text'])
        self.primary.period = parsePeriod(self.primary.tokens['period']['text'], time)
        basetime = self.primary.period[0]

        for e in self.elements[1:]:
            if e.tokens['sign']['text'].startswith('FM'):
                time = parseTime(e.tokens['sign']['text'][2:], basetime)
                e.period = (time, time)
            else:
                e.period = parsePeriod(e.tokens['period']['text'], basetime)

    def _regroup(self):
        """根据报文的时序重新分组 TEMPO BECMG"""
        self.becmgs.sort(key=lambda x: x.period[1])
        self.tempos.sort(key=lambda x: x.period[0])

        def nextBecmg(groups, tempo):
            index = groups.index(tempo)
            items = []
            for group in groups[index:]:
                if group.sign != 'TEMPO':
                    items.append(group)

            return items

        def group(becmgs, tempos):
            groups = becmgs + tempos
            groups.sort(key=lambda x: x.period[0] if x.sign == 'TEMPO' else x.period[1])

            for tempo in tempos:
                items = nextBecmg(groups, tempo)
                for becmg in items:
                    if becmg.period[1] < tempo.period[1]:
                        index = groups.index(becmg)
                        groups.insert(index + 1, tempo)

            return groups

        self.groups = group(self.becmgs, self.tempos)

    def _createRefs(self):
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
        if self.hasMessageChanged():
            self.errors.append('经过校验后的报文和原始报文有些不同')
            self._forceError()

        try:
            self._parsePeriod()
            self._regroup()
            self._createRefs()
            self._validateFormat()
            self._validateChange()
        except Exception as e:
            self.failed = True
            self.errors.append('报文无法被正确解析')
            self._forceError()
            logger.exception(e)

        self.errors = list(set(self.errors))

    def _forceError(self):
        for e in self.elements:
            for key in e.tokens:
                e.tokens[key]['error'] = True

    def _validateFormat(self):
        pass

    def _validateChange(self):
        """验证单项和多项转折"""

        # 验证主报文多个要素匹配
        self._validateElement(self.reference, self.primary.tokens)

        for e in self.groups:
            for key in e.tokens:
                # 依次验证单项要素转折
                verify = getattr(self.validator, key, None)
                if verify:
                    if key == 'cavok':
                        legal = verify(self.reference['vis']['text'], self.reference['weather']['text'], self.reference['cloud']['text'])
                    else:
                        legal = verify(self.reference[key]['text'], e.tokens[key]['text'])

                    if key == 'weather' and e.tokens[key]['text'] != self.reference[key]['text'] \
                        and 'vis' in e.tokens and not e.tokens['vis']['error'] \
                        or e.tokens[key]['error']:
                        # 天气现象发生改变，并引起能见度变化，同时天气现象不为 NSW
                        # 单项已判断为有误
                        pass
                    else:
                        e.tokens[key]['error'] = not legal

                    if e.sign == 'BECMG' or e.sign.startswith('FM'):
                        if key == 'cavok':
                            self.reference['vis']['text'] = '9999'
                            self.reference['weather']['text'] = 'NSW'
                            self.reference['cloud']['text'] = 'NSC'
                        else:
                            self.reference[key]['text'] = e.tokens[key]['text']

            # 验证参照组与转折组之间多个要素匹配
            self._validateElement(self.reference, e.tokens)

    def _validateElement(self, ref, tokens):
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

        def validateVisWeather(vis, weathers):
            key = 'weather' if 'weather' in tokens else 'vis'

            if 'NSW' in weathers:
                if vis <= 5000:
                    tokens[key]['error'] = True
                    self.errors.append('能见度小于 5000 米时应有天气现象')

            else:
                if vis < 1000 and set(weathers) & set(['BR', '-DZ']):
                    tokens[key]['error'] = True
                    self.errors.append('能见度小于 1000 米，BR、-DZ 不能有')

                if 1000 <= vis <= 5000 and set(weathers) & set(['FG', '+DZ']):
                    tokens[key]['error'] = True
                    self.errors.append('能见度大于 1000 米、小于 5000 米，FG、+DZ 不能有')

                if vis > 5000 and set(weathers) & set(['FG', 'FU', 'BR', 'HZ', 'SA', 'DU']):
                    tokens[key]['error'] = True
                    self.errors.append('能见度大于 5000 米，FG、FU、BR、HZ、SA、DU 不能有')

        # 检查能见度和天气现象
        if 'vis' in tokens:
            vis = int(tokens['vis']['text'])
            weathers = mixture['weather']['text'].split()

            validateVisWeather(vis, weathers)

        if 'weather' in tokens:
            weather = tokens['weather']['text']
            weathers = weather.split()
            vis = int(mixture['vis']['text'])

            validateVisWeather(vis, weathers)

            # 检查阵性降水和积雨云
            cloud = mixture['cloud']['text']
            if ('TS' in weather or ('SH' in weather and '-' not in weather)) and not ('CB' in cloud or 'TCU' in cloud):
                tokens['weather']['error'] = True
                self.errors.append('阵性降水应包含对流云')

            if 'NSW' in weathers and len(weathers) > 1:
                tokens['weather']['error'] = True
                self.errors.append('NSW 不能和其他天气现象同时存在')

            weatherCount = set(weathers) & set(['BR', 'HZ', 'FG', 'FU'])
            if len(weatherCount) > 1:
                tokens['weather']['error'] = True
                self.errors.append('BR，HZ，FG，FU 不能同时存在')


        if 'cloud' in tokens:
            # 检查云组转折天气现象的匹配
            weather = mixture['weather']['text']
            cloud = tokens['cloud']['text']
            if ('TS' in weather or ('SH' in weather and '-' not in weather)) and not ('CB' in cloud or 'TCU' in cloud):
                tokens['cloud']['error'] = True
                self.errors.append('阵性降水应包含对流云')

            # 不同高度云组云量的验证
            clouds = [c for c in cloud.split() if not ('CB' in c or 'TCU' in c)]

            for i, cloud in enumerate(clouds):
                if i == 1 and 'FEW' in cloud:
                    tokens['cloud']['error'] = True
                    self.errors.append('云组第二层云量不能为 FEW')

                if i == 2 and ('FEW' in cloud or 'SCT' in cloud):
                    tokens['cloud']['error'] = True
                    self.errors.append('云组第三层云量不能为 FEW 或 SCT')

    @property
    def tips(self):
        return self.errors

    def isValid(self):
        """报文是否通过验证"""
        if self.failed:
            return False

        valids = [e.isValid() for e in self.elements]
        return all(valids)

    def isAmended(self):
        """报文是否是修订报或者更正报"""
        items = self.message.split()
        return 'COR' in items or 'AMD' in items

    def hasMessageChanged(self):
        """校验后的报文和原始报文相比是否有变化"""
        origin = ' '.join(self.message.split())
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
        outputs = [e.renderer(style) for e in self.elements if e]

        if style == 'html':
            return '<br/>'.join(outputs) + '='

        return '\n'.join(outputs) + '='


class MetarLexer(TafLexer):

    grammarClass = MetarGrammar

    defaultRules = [
        'sign', 'amend', 'icao', 'timez', 'fmtl', 'auto',
        'wind', 'windrange', 'vis', 'cavok', 'rvr', 'weather', 'cloud',
        'tempdew', 'pressure', 'reweather', 'windshear', 'nosig'
    ]

    def degToCompass(self, direction):
        val = int((direction / 22.5) + 0.5)
        directions = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']
        return directions[(val % 16)]

    def degToArrow(self, direction):
        val = int((direction / 45) + 0.5)
        directions = ['↓', '↙', '←', '↖', '↑', '↗', '→', '↘']
        return directions[(val % 8)]

    def windDirection(self, style='degree'):
        text = self.tokens['wind']['text']
        m = self.grammar.wind.match(text)
        direction = m.group(1)

        if direction == 'VRB' and style == 'arrow':
            return '⊙'

        if direction == 'VRB':
            return direction

        if direction is None:
            return ''

        if style == 'arrow':
            direction = self.degToArrow(int(direction))

        if style == 'compass':
            direction = self.degToCompass(int(direction))

        if style == 'degree':
            direction = int(direction)

        return direction

    def windSpeed(self):
        text = self.tokens['wind']['text']
        m = self.grammar.wind.match(text)
        speed = m.group(2)

        if speed is None:
            speed = 0

        if speed == 'P49':
            speed = 50
        
        return int(speed)

    def gust(self):
        text = self.tokens['wind']['text']
        m = self.grammar.wind.match(text)
        speed = m.group(3)

        if speed == 'P49':
            speed = 50

        if speed:
            speed = int(speed)
        
        return speed

    def vis(self):
        if 'CAVOK' in self.part:
            return 9999

        return int(self.tokens['vis']['text'])

    def rvr(self):
        if 'rvr' in self.tokens:
            text = self.tokens['rvr']['text']
            rvrs = []
            for t in text.split():
                _, rvr = t.split('/')
                rvrs += re.findall(r'\d+', rvr)

            return min(map(int, rvrs))

    def weathers(self):
        if 'weather' in self.tokens:
            text = self.tokens['weather']['text']
            return text.split()

        return []

    def clouds(self):
        if 'CAVOK' in self.part or 'NSC' in self.part:
            return []

        if 'cloud' in self.tokens:
            text = self.tokens['cloud']['text']
            clouds = sorted(text.split(), key=lambda cloud: int(cloud[3:6]))

            return clouds

    def ceiling(self):
        if 'CAVOK' in self.part or 'NSC' in self.part:
            return 1500

        if 'cloud' in self.tokens:
            text = self.tokens['cloud']['text']
            clouds = sorted(text.split(), key=lambda cloud: int(cloud[3:6]))

            ceiling = 1500
            for cloud in clouds:
                if cloud.startswith(('BKN', 'OVC', 'VV')):
                    height = ''.join([c for c in cloud if c.isdigit()])
                    ceiling = int(height) * 30
                    break

            return ceiling

    def temperature(self):
        temp, _ = self.tokens['tempdew']['text'].split('/')
        temp = - int(temp[1:]) if 'M' in temp else int(temp)
        return temp

    def dewpoint(self):
        _, dew = self.tokens['tempdew']['text'].split('/')
        dew = - int(dew[1:]) if 'M' in dew else int(dew)
        return dew

    def pressure(self):
        return int(self.tokens['pressure']['text'][1:])


class MetarParser(TafParser):

    lexerClass = MetarLexer

    splitPattern = re.compile(r'(BECMG|TEMPO)')

    def __init__(self, message, parse=None, validator=None, ignoreMetar=False, **kwargs):
        super().__init__(message, parse=parse, validator=validator, **kwargs)
        self.ignoreMetar = ignoreMetar
        self.previous = kwargs.get('previous')
        if len(self.elements) > 1 and self.primary:
            self.metar = MetarParser(self.primary.part, parse=parse, validator=validator, ignoreMetar=False, **kwargs)
            self.metar.validate()
        else:
            self.metar = self

    def _split(self):
        super()._split()
        if 'NOSIG' in self.message:
            metar = self.primary.part.replace('NOSIG', '').strip()
            self.primary = self.parse(metar)
            self.trends = [self.parse('NOSIG')]
            self.elements = [self.primary] + self.trends
        else:
            self.trends = self.elements[1:]

    def _parsePeriod(self):
        """解析主报文和变化组的时间顺序"""
        time = parseTimez(self.primary.tokens['timez']['text'])
        self.primary.period = (time, time + datetime.timedelta(hours=2))
        basetime = self.primary.period[0]

        for e in self.elements[1:]:
            if 'fmtl' in e.tokens:
                periods = e.tokens['fmtl']['text'].split()
                if len(periods) == 2:
                    start = parseTime(periods[0][2:], basetime)
                    end = parseTime(periods[1][2:], basetime)
                    if start > end:
                        end += datetime.timedelta(days=1)
                    e.period = (start, end)
                else:
                    text = periods[0]
                    if text.startswith('FM'):
                        e.period = (parseTime(text[2:], basetime), self.primary.period[1])
                    if text.startswith('TL'):
                        e.period = (basetime, parseTime(text[2:], basetime))
                    if text.startswith('AT'):
                        time = parseTime(text[2:], basetime)
                        e.period = (time, time)
            else:
                e.period = self.primary.period

    def _validateFormat(self):
        for e in self.elements[1:]:
            if 'fmtl' in e.tokens:
                text = e.tokens['fmtl']['text']
                periods = text.split()
                for period in periods:
                    conditions = [
                        'AT' in period and not (self.primary.period[0] < e.period[0] < self.primary.period[1]),
                        'FM' in period and not (self.primary.period[0] < e.period[0] < self.primary.period[1] and e.period[0] < e.period[1]),
                        'TL' in period and not (self.primary.period[0] < e.period[1] < self.primary.period[1] and e.period[0] < e.period[1])
                    ]
                    
                    if any(conditions):
                        e.tokens['fmtl']['error'] = True
                        self.errors.append('趋势时间组错误')

    def hasMessageChanged(self):
        """校验后的报文和原始报文相比是否有变化"""
        origin = ' '.join(self.message.split())
        outputs = [e.renderer('plain') for e in self.elements if e and e != self.primary]
        if outputs:
            output = ' '.join(outputs) + '='
            return not origin.endswith(output)
        return False

    def hasTrend(self):
        return self.becmgs or self.tempos

    def hasMetar(self):
        return self.metar is not self

    def isValid(self, ignoreMetar=None):
        if ignoreMetar is None:
            ignoreMetar = self.ignoreMetar

        if ignoreMetar or not self.hasMetar():
            elements = self.elements[1:]
        else:
            elements = self.elements

        if self.failed:
            return False

        valids = [e.isValid() for e in elements]
        return all(valids)

    def isSimilar(self, other):
        other = MetarParser(other)
        return self.primary.renderer() == other.primary.renderer()

    @property
    def tips(self):
        if self.ignoreMetar and not self.metar.isValid(ignoreMetar=False):
            tips = list(set(self.errors) - set(self.metar.errors))
        else:
            tips = self.errors
        return tips

    def renderer(self, style='plain', showDiff=False, emphasizeNosig=False):
        """将解析后的报文重新渲染

        :param style:
            * plain 纯字符串风格
            * terminal 终端高亮风格
            * html HTML 高亮风格
        :return: 根据不同风格重新渲染的报文
        """
        outputs = [e.renderer(style) for e in self.elements if e]
        separator = ' '

        if style == 'html':
            if self.hasTrend() or emphasizeNosig:
                separator = '<br/>'

            metar = self.primary.part
            if self.ignoreMetar:
                if showDiff and self.previous:
                    metar = self._diff(metar, self.previous)

                outputs[0] = metar

                if self.hasTrend() or emphasizeNosig:
                    outputs[0] = '<span style="color: grey">{}</span>'.format(metar)
                else:
                    return '<span style="color: grey">{}</span>'.format(separator.join(outputs) + '=')

            return separator.join(outputs) + '='

        if self.hasTrend():
            separator = '\n'

        return separator.join(outputs) + '='

    def _diff(self, metar, previous):
        previous, *_ = self.splitPattern.split(previous)
        parts = metar.split()
        elements = []
        for e in parts:
            if e not in previous.split():
                e = '<strong>{}</strong>'.format(e)
            elements.append(e)

        return ' '.join(elements)


class SigmetLexer(object):
    """SIGMET 报文要素的解析器

    :param part: 单行报文内容
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

    airmetKeywords = ['ISOL', 'OCNL', 'MOD', 'BKN', 'OVC', 'WIND', 'VIS', 'AIRMET',
        'BR', 'DU', 'DZ', 'FC', 'FG', 'FU', 'GR', 'GS', 'HZ', 'PL', 'PO', 'RA', 'SA', 'SG', 'SN', 'SQ', 'TCU'
    ]

    defaultRules = ['latitude', 'longitude', 'flightLevel', 'speed', 'obsTime', 'typhoonRange', 'sequence', 'valid', 'width']

    airmetRules = ['wind', 'vis', 'cloud']

    def __init__(self, part, firCode=None, airportCode=None, grammar=None, keywords=None, rules=None, isAirmet=False,**kwargs):
        super(SigmetLexer, self).__init__()
        if not grammar:
            grammar = self.grammarClass()

        if not keywords:
            keywords = self.defaultKeywords + self.airmetKeywords if isAirmet else self.defaultKeywords

        if not rules:
            rules = self.defaultRules + self.airmetRules if isAirmet else self.defaultRules

        if airportCode:
            keywords.append(airportCode)

        self.grammar = grammar
        self.keywords = keywords
        self.rules = rules
        self.firCode = firCode
        self.part = part.strip()
        self.tokens = []

        self.parse(part)

    def __repr__(self):
        return '<SigmetLexer {!r}>'.format(self.part)

    def __bool__(self):
        return bool(self.part)

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
        for key in self.rules:
            pattern = getattr(self.grammar, key)
            m = pattern.match(text)
            if m:
                if m.group() == text:
                    return True

    def isSpecialName(self, index, parts):
        """检查字符是否是特殊名字，如情报区名、热带气旋名、火山名

        :return: 是否是特殊名字
        """
        hasNumber = lambda chars: any(char.isdigit() for char in chars)
        try:
            if parts[index] == self.firCode \
                or parts[index-1] == 'MT' \
                or (parts[index-1] == 'TC' and not hasNumber(parts[index-2])):
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

    使用方法::

        p = SigmetParser('ZJSA SIGMET 1 VALID 300855/301255 ZJHK-
                        ZJSA SANYA FIR VA ERUPTION MT ASHVAL LOC E S1500 E07348 VA CLD OBS AT 1100Z FL310/450
                        APRX 220KM BY 35KM S1500 E07348 - S1530 E07642 MOV ESE 65KMH
                        FCST 1700Z VA CLD APRX S1506 E07500 - S1518 E08112 - S1712 E08330 - S1824 E07836=')

        # 报文字符是否通过验证
        p.isValid()

        # 报文重新渲染成 HTML 格式，并高亮标注出错误
        p.renderer(style='html')

    """
    grammarClass = SigmetGrammar

    lexerClass = SigmetLexer

    def __init__(self, message, parse=None, grammar=None, **kwargs):
        self.message = message.strip()
        self.isAirmet = True if self.reportType() == 'AIRMET' else False

        if not grammar:
            grammar = self.grammarClass()

        if not parse:
            parse = self.lexerClass

        self.grammar = grammar
        self.parse = parse
        self.firCode = self.fir()
        self.airportCode = self.airport()

        self._split()

    def _split(self):
        """拆分报头和报文内容"""
        self.heading = None
        message = self.message.replace('=', '')
        headingPattern = re.compile(r'(\w{4}\d{2}\s\w{4}\s\d{6}(?:\s\w{3})?)\b')
        splitPattern = re.compile(r'([A-Z]{4}-)')
        m = headingPattern.match(message)
        if m:
            self.heading = m.group()
            message = headingPattern.sub('', message).strip()

        *lines, text = splitPattern.split(message)
        self.firstline = ' '.join(e.strip() for e in lines)
        text = text.strip()
        self.elements = [self.parse(e, firCode=self.firCode, airportCode=self.airportCode, isAirmet=self.isAirmet) for e in text.split('\n')]
        self.text = '\n'.join([self.firstline, text])

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            this = ' '.join(self.text.split())
            text = ' '.join(other.text.split())
            return this == text
        return False

    def airport(self):
        pattern = re.compile(r'([A-Z]{4})-')
        m = pattern.search(self.message)
        if m:
            return m.group(1)
        else:
            return ''

    def fir(self):
        pattern = re.compile(r'\b([A-Z]{4}\s.+\s(?:FIR|FIR/UIR|CTA))\b')
        m = pattern.search(self.message)
        if m:
            return m.group(1)
        else:
            return ''

    def reportType(self):
        pattern = re.compile(r'(SIGMET|AIRMET) ([A-Z]?\d{1,2}) VALID')
        m = pattern.search(self.message)
        if m:
            return m.group(1)
        else:
            return ''

    def type(self):
        if 'AIRMET' in self.message:
            return 'WA'

        if self.hazard() == 'ash':
            return 'WV'

        if self.hazard() == 'typhoon':
            return 'WC'

        return 'WS'

    def hazard(self):
        text = 'other'
        patterns = {
            'ts': re.compile(r'\b(TS|TSGR)\b'),
            'turb': re.compile(r'\b(TURB)\b'),
            'ice': re.compile(r'\b(ICE)\b'),
            'ash': re.compile(r'\b(WV\w{2}\d{2})|(VA)\b'),
            'typhoon': re.compile(r'\b(WC\w{2}\d{2})|(TC)\b'),
        }

        for key, pattern in patterns.items():
            m = pattern.search(self.message)
            if m:
                text = key

        return text

    def sequence(self):
        pattern = re.compile(r'(SIGMET|AIRMET)\s([A-Z]?\d{1,2})\sVALID')
        m = pattern.search(self.message)
        if m:
            return m.group(2)

    def cancelSequence(self):
        pattern = re.compile(r'CNL\s(SIGMET|AIRMET)\s([A-Z]?\d{1,2})\s(\d{6}/\d{6})')
        m = pattern.search(self.message)
        if m:
            return m.group(2), m.group(3)

    def valids(self):
        pattern = self.grammar.valid
        return pattern.search(self.message).groups()

    def location(self, mode='object'):
        patterns = {
            'polygon': self.grammar.polygon,
            'line': self.grammar.lines,
            'corridor': self.grammar.corridor,
            'rectangular': self.grammar.rectangulars,
            'circle': self.grammar.position,
            'entire': re.compile('ENTIRE')
        }

        geometries = []
        for key, pattern in patterns.items():
            m = pattern.search(self.message)
            if not m:
                continue

            if key == 'circle':
                m = self.grammar.radius.search(self.message)
                if not m:
                    continue

            for match in pattern.finditer(self.message):
                text = match.group()
                item = self._parseLocation(key, text) if mode == 'object' else text
                geometry = {
                    'type': key,
                    'coordinates': item
                }
                geometries.append(geometry)

        return geometries

    def _parseLocation(self, key, text):
        if key == 'polygon':
            point = self.grammar.point
            points = point.findall(text)

            return points

        if key == 'line':
            point = self.grammar.point
            line = self.grammar.line
            locations = []
            for l in line.finditer(text):
                identifier = l.group(1)
                part = l.group()
                points = point.findall(part)
                points.insert(0, identifier)
                locations.append(points)

            return locations

        if key == 'corridor':
            pattern = self.grammar.corridor
            point = self.grammar.point
            m = pattern.search(text)
            width = (m.group(1), m.group(2))
            points = point.findall(text)
            return points, width

        if key == 'rectangular':
            line = self.grammar.rectangular
            lines = line.findall(text)
            lines = [tuple(filter(None, l)) for l in lines]

            return lines

        if key == 'circle':
            point = self.grammar.point
            radius = self.grammar.radius
            center = point.search(text)
            width = radius.search(self.message)
            return center.groups(), width.groups()

        return []

    def geo(self, boundaries, trim=None):
        from tafor.utils.algorithm import decode
        collections = {
            'type': 'FeatureCollection',
            'features': []
        }

        sequence = self.sequence()
        valids = self.valids()
        hazard = self.hazard()

        locations = self.location()
        for i, item in enumerate(locations):
            polygon = decode(boundaries, item['coordinates'], mode=item['type'], trim=trim)
            features = {
                'type': 'Feature',
                'geometry': {
                    'type': 'Polygon',
                    'coordinates': []
                },
                'properties': {
                    'sequence': sequence,
                    'valids': valids,
                    'hazard': hazard,
                    'location': 'initial'
                }
            }
            if polygon.geom_type == 'MultiPolygon':
                coords = []
                for p in polygon.geoms:
                    coords.append(list(p.exterior.coords))
                features['geometry']['type'] = 'MultiPolygon'
            else:
                coords = list(polygon.exterior.coords)

            features['geometry']['coordinates'] = coords

            if i > 0:
                features['properties']['location'] = 'final'

            collections['features'].append(features)

        return collections

    def content(self):
        outputs = [e.renderer() for e in self.elements]
        return '\n'.join(outputs) + '='

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
        outputs = [self.heading, self.firstline] + [e.renderer(style) for e in self.elements if e]
        outputs = filter(None, outputs)

        if style == 'html':
            return '<br/>'.join(outputs) + '='

        return '\n'.join(outputs) + '='


class AdvisoryParser(object):

    grammarClass = AdvisoryGrammar

    def __init__(self, message, grammar=None):
        if not grammar:
            grammar = self.grammarClass()

        self.grammar = grammar
        self.message = message
        self.tokens = OrderedDict()
        self.time = None
        self.parse()

    def parse(self):
        regex = r'{}((?:\s?.+\s?)*)'.format(self.type)
        if '=' in self.message:
            regex += '='
        pattern = re.compile(regex)
        match = pattern.search(self.message)
        if not match:
            return
        text = match.group(1)
        matches = re.finditer(r'^\s*([^:]+?)\s*:\s*(.*?)\s*$', text, re.MULTILINE)
        prev = None
        for match in matches:
            key, value = match.groups()
            values = key.split('\n')
            if len(values) > 1:
                *temps, key = values
                if prev:
                    self.tokens[prev] = self.tokens[prev] + ' '.join(temps)

            self.tokens[key] = value
            prev = key

        if 'DTG' in self.tokens:
            self.time = datetime.datetime.strptime(self.tokens['DTG'], '%Y%m%d/%H%MZ')

    def position(self):
        keys = ['PSN', 'OBS PSN']
        text = self._findText(keys)
        if text:
            match = self.grammar.point.search(text)
            if match:
                return match.groups()

    def name(self):
        field = self.fields['name']
        if field in self.tokens:
            text = self.tokens[field]
            match = self.grammar.name.match(text)
            if match:
                return match.group()

        return ''

    def movement(self):
        field = self.fields['movement']
        if field in self.tokens:
            text = self.tokens[field]
            match = self.grammar.movement.search(text)
            if match:
                return match.group(1)

        return ''

    def speed(self, unit='KMH'):
        field = self.fields['movement']
        if field in self.tokens:
            text = self.tokens[field]
            match = self.grammar.speed.search(text)
            if match:
                speed, u = match.groups()
                if unit == 'KMH' and u == 'KT':
                    speed = int(speed) * 1.852

                if unit == 'KT' and u == 'KMH':
                    speed = int(speed) / 1.852
                
                return int(speed)

    def observationTime(self):
        raise NotImplementedError

    def availableLocations(self):
        keys = []
        field = self.fields['locations']
        for key in self.tokens:
            if field in key:
                keys.append(key)

        return keys

    def _findLocationTime(self, key):
        if not self.time:
            return

        match = re.search(r'\d+', key)
        obstime = self.observationTime()
        if match and obstime:
            hour = int(match.group())
            time = obstime + datetime.timedelta(hours=hour)
            return time
        else:
            return self.time

    def _findText(self, keys):
        for key in keys:
            if key in self.tokens:
                return self.tokens[key]


class TyphoonAdvisoryParser(AdvisoryParser):

    type = 'TC ADVISORY'
    fields = {
        'name': 'TC',
        'movement': 'MOV',
        'locations': 'PSN'
    }

    def observationTime(self):
        return self.time

    def location(self, key):
        if key not in self.tokens:
            return {}

        features = {
            'type': 'Feature',
            'properties': {}
        }
        text = self.tokens[key]
        coordinates = self.grammar.point.findall(text)
        coordinates = [(degreeToDecimal(lon), degreeToDecimal(lat)) for lat, lon in coordinates]
        if coordinates:
            geometry = {
                'type': 'Point',
                'coordinates': coordinates[0]
            }
            features['geometry'] = geometry

        time = self._findLocationTime(key)
        if time:
            features['properties']['time'] = time

        return features

    def height(self):
        if 'CB' in self.tokens:
            text= self.tokens['CB']
            match = self.grammar.height.search(text)
            if match:
                return match.group(1)

        return ''

    def intensity(self):
        if 'INTST CHANGE' in self.tokens:
            text= self.tokens['INTST CHANGE']
            return text.strip()

    def route(self):
        locations = self.availableLocations()
        geometry = {}
        coordinates = []
        for key in locations:
            text = self.tokens[key]
            coordinates += self.grammar.point.findall(text)

        if coordinates:
            geometry = {
                'type': 'LineString',
                'coordinates': [(degreeToDecimal(lon), degreeToDecimal(lat)) for lat, lon in coordinates]
            }

        return geometry

    def polygon(self):
        geometry = {}
        if 'CB' in self.tokens:
            text = self.tokens['CB']
            coordinates = self.grammar.point.findall(text)
            if coordinates:
                geometry = {
                    'type': 'Polygon',
                    'coordinates': [(degreeToDecimal(lon), degreeToDecimal(lat)) for lat, lon in coordinates]
                }

        return geometry

    def radius(self):
        from tafor.utils.algorithm import wgs84
        center = self.position()
        polygon = self.polygon()
        if not center or not polygon:
            return

        distances = []
        lat, lon = center
        center = degreeToDecimal(lon), degreeToDecimal(lat)
        for lon, lat in polygon['coordinates']:
            _, _, distance = wgs84.inv(center[0], center[1], lon, lat)
            distances.append(distance)

        return int(max(distances) / 1000)


class AshAdvisoryParser(AdvisoryParser):

    type = 'VA ADVISORY'
    fields = {
        'name': 'VOLCANO',
        'movement': 'OBS VA CLD',
        'locations': 'VA CLD'
    }

    def observationTime(self):
        if self.time and 'OBS VA DTG' in self.tokens:
            text = self.tokens['OBS VA DTG']
            match = self.grammar.time.search(text)
            if match:
                day, hour, minute = match.groups()
                time = self.time.replace(day=int(day), hour=int(hour), minute=int(minute))
                return time

    def location(self, key):
        if key not in self.tokens:
            return {}

        features = {
            'type': 'Feature',
            'properties': {}
        }
        text = self.tokens[key]
        coordinates = self.grammar.point.findall(text)
        coordinates = [(degreeToDecimal(lon), degreeToDecimal(lat)) for lat, lon in coordinates]
        if coordinates:
            geometry = {
                'type': 'Polygon',
                'coordinates': coordinates
            }
            features['geometry'] = geometry

        time = self._findLocationTime(key)
        if time:
            features['properties']['time'] = time

        match = self.grammar.flightLevel.search(text)
        if match:
            features['properties']['flightLevel'] = match.group()

        return features
