import re
import copy
import logging

from collections import OrderedDict

from tafor.core.utils.time import parsePeriod, parseTime, parseTimez

logger = logging.getLogger('tafor.parser.taf')

from tafor.core.parsers.base import MetarGrammar, TafGrammar


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
        self.periods = None
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

    def __init__(self, message, created=None, parse=None, validator=None, **kwargs):
        message = message.strip()
        if not message.endswith('='):
            message = message + '='
        self.message = message
        self.becmgs = []
        self.tempos = []
        self.errors = []
        self.failed = False

        self.reference = None

        self.valids = None
        self.created = created

        if not parse:
            self.parse = self.lexerClass

        if not validator:
            self.validator = self.validatorClass(**kwargs)

        self._analyse()

    def __eq__(self, other):
        """判断两份报文是否相等"""
        if isinstance(other, self.__class__):
            return self.renderer() == other.renderer()
        return False

    def __repr__(self):
        return '<{} {!r}>'.format(self.__class__.__name__, self.renderer())

    def _analyse(self):
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

        if self.created is None:
            self.created = parseTimez(self.primary.tokens['timez']['text'])

        self.primary.periods = parsePeriod(self.primary.tokens['period']['text'], self.created)
        self.valids = self.primary.periods
        basetime = self.primary.periods[0]

        for e in self.elements[1:]:
            if e.tokens['sign']['text'].startswith('FM'):
                time = parseTime(e.tokens['sign']['text'][2:], basetime)
                e.periods = (time, time)
            else:
                e.periods = parsePeriod(e.tokens['period']['text'], basetime)

    def _regroup(self):
        """根据报文的时序重新分组 TEMPO BECMG"""
        self.becmgs.sort(key=lambda x: x.periods[1])
        self.tempos.sort(key=lambda x: x.periods[0])

        def nextBecmg(groups, tempo):
            index = groups.index(tempo)
            items = []
            for group in groups[index:]:
                if group.sign != 'TEMPO':
                    items.append(group)

            return items

        def group(becmgs, tempos):
            groups = becmgs + tempos
            groups.sort(key=lambda x: x.periods[0] if x.sign == 'TEMPO' else x.periods[1])

            for tempo in tempos:
                items = nextBecmg(groups, tempo)
                for becmg in items:
                    if becmg.periods[1] < tempo.periods[1]:
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
            logger.error('message cannot be parsed correctly, {}, {}'.format(self.message, e))

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
