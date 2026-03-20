import re
import logging
import datetime

from collections import OrderedDict

from tafor.core.utils.geo import degreeToDecimal
from tafor.core.utils.time import parseTime, parseTimez

logger = logging.getLogger('tafor.parser.sigmet')

from tafor.core.parsers.base import AdvisoryGrammar, SigmetGrammar

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

    airmetRules = ['airmansFlightLevel', 'wind', 'vis', 'cloud']

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

    def __init__(self, message, created=None, parse=None, grammar=None, **kwargs):
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

        self.valids = None
        self.created = created

        self._analyse()

    def _analyse(self):
        """拆分报头和报文内容"""
        self.heading = None
        message = self.message.replace('=', '')
        headingPattern = re.compile(r'\w{4}\d{2}\s\w{4}\s(\d{6})')
        splitPattern = re.compile(r'([A-Z]{4}-)')
        validPattern = self.grammar.valid
        
        time = None
        valids = None
        heading = headingPattern.match(message)
        valid = validPattern.search(self.message)
        if valid:
            valids = valid.groups()
            time = valid[0]

        if heading:
            self.heading = heading.group()
            message = headingPattern.sub('', message).strip()
            time = heading.group(1)

        if self.created is None:
            self.created = parseTimez(time) if time else datetime.datetime.utcnow()

        if valids:
            self.valids = parseTime(valids[0], self.created), parseTime(valids[1], self.created)

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

    def validTime(self):
        pattern = self.grammar.valid
        m = pattern.search(self.message)
        if m:
            return '/'.join(m.groups())

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
        from tafor.core.utils.algorithm import decode
        collections = {
            'type': 'FeatureCollection',
            'features': []
        }

        sequence = self.sequence()
        valid = self.validTime()
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
                    'valids': valid.split('/'),
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

    def observedTime(self):
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
        obstime = self.observedTime()
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

    def observedTime(self):
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
        from tafor.core.utils.algorithm import wgs84
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

    def observedTime(self):
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
