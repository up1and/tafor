import re
import logging
import datetime

from tafor.core.utils.time import parseTime, parseTimez
from tafor.core.parsers.base import SigmetGrammar, joinRendered, renderTokens

logger = logging.getLogger('tafor.parser.sigmet')

class SigmetLexer:
    """SIGMET 报文要素的解析器

    :param part: 单行报文内容
    :param grammar: 解析 SIGMET 报文的语法类
    :param keywords: SIGMET 报文允许的关键字
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

    def __init__(self, part, firCode=None, airportCode=None, grammar=None, keywords=None, rules=None, isAirmet=False, **kwargs):
        super().__init__()
        if not grammar:
            grammar = self.grammarClass()

        if not keywords:
            keywords = list(self.defaultKeywords)
            if isAirmet:
                keywords += self.airmetKeywords

        if not rules:
            rules = list(self.defaultRules)
            if isAirmet:
                rules += self.airmetRules

        if airportCode:
            keywords.append(airportCode)

        self.grammar = grammar
        self.keywords = keywords
        self.rules = rules
        self.firCode = firCode
        self.part = part.strip()
        self.tokens = []

        self.parse(self.part)

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

        prev = None
        prevPrev = None
        for i, text in enumerate(parts):
            # the FIR name is derived from the message itself, accept it as is
            recognized = (i == 0 and text == self.firCode) \
                or text in self.keywords \
                or self.matchesGrammar(text) \
                or self.isProperName(prev, prevPrev)

            self.tokens.append({
                'text': text,
                'error': not recognized
            })

            prevPrev = prev
            prev = text

    def matchesGrammar(self, text):
        """Tell whether the word is a full match of one of the grammar rules."""
        for key in self.rules:
            pattern = getattr(self.grammar, key)
            if pattern.fullmatch(text):
                return True

        return False

    def isProperName(self, prev, prevPrev):
        """Tell whether the current word is a proper name given its context.

        Volcano names follow ``MT`` and tropical cyclone names follow
        ``TC``. A word after ``TC`` only counts as a cyclone name when
        the word before ``TC`` carries no digits, e.g. when ``TC`` does
        not follow a coordinate or an observation time.
        """
        if prev == 'MT':
            return True

        if prev == 'TC':
            return prevPrev is None or not any(char.isdigit() for char in prevPrev)

        return False

    def isValid(self):
        """检查报文是否有错误

        :return: 报文是否通过验证
        """
        return all(not e['error'] for e in self.tokens)

    def renderer(self, style='plain'):
        """将解析后的报文重新渲染

        :param style:
            * plain 纯字符串风格
            * terminal 终端高亮风格
            * html HTML 高亮风格
        :return: 根据不同风格重新渲染的报文
        """
        if style == 'plain':
            return self.part

        return renderTokens(self.tokens, style)

class SigmetParser:
    """解析 SIGMET 报文

    :param message: SIGMET 报文
    :param lexer: 解析报文的类，默认 :class:`SigmetLexer`

    使用方法::

        p = SigmetParser('ZJSA SIGMET 1 VALID 310950/311350 ZJHK-
                        ZJSA SANYA FIR EMBD TS FCST WI N2030 E11118 - N2030 E10858 - N1913 E10911 - 
                        N1906 E11111 - N2030 E11118 TOP FL500 MOV NE 25KMH NC=')

        # 报文字符是否通过验证
        p.isValid()

        # 报文重新渲染成 HTML 格式，并高亮标注出错误
        p.renderer(style='html')

    """
    grammarClass = SigmetGrammar

    lexerClass = SigmetLexer

    def __init__(self, message, created=None, firCode=None, airportCode=None, lexer=None, grammar=None, **kwargs):
        self.message = message.strip()
        self.isAirmet = self.category() == 'AIRMET'

        if not grammar:
            grammar = self.grammarClass()

        self.grammar = grammar
        self.lexer = lexer or self.lexerClass
        self.firCode = firCode or self.fir()
        self.airportCode = airportCode or self.airport()

        self.valids = None
        self.created = created

        self._analyse()

    def _analyse(self):
        """拆分报头和报文内容"""
        self.heading = None
        message = self.message.replace('=', '')
        splitPattern = re.compile(r'([A-Z]{4}-)')
        validPattern = self.grammar.valid

        time = None
        valids = None
        valid = validPattern.search(self.message)
        if valid:
            valids = valid.groups()
            time = valid[0]

        if self.created is None:
            self.created = parseTimez(time) if time else datetime.datetime.utcnow()

        if valids:
            self.valids = parseTime(valids[0], self.created), parseTime(valids[1], self.created)

        *lines, text = splitPattern.split(message)
        self.firstline = ' '.join(e.strip() for e in lines)
        text = text.strip()
        self.elements = [self.lexer(e, firCode=self.firCode, airportCode=self.airportCode, isAirmet=self.isAirmet) for e in text.split('\n')]
        self.text = '\n'.join([self.firstline, text])

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            this = ' '.join(self.text.split())
            text = ' '.join(other.text.split())
            return this == text
        return False

    def airport(self):
        pattern = re.compile(r'([A-Z]{4})-')
        match = pattern.search(self.message)
        return match.group(1) if match else None

    def fir(self):
        pattern = re.compile(r'\b([A-Z]{4}(?:\s[A-Z]+)*?\s(?:FIR/UIR|FIR|CTA))\b')
        match = pattern.search(self.message)
        return match.group(1) if match else None

    def category(self):
        pattern = re.compile(r'(SIGMET|AIRMET)\s([A-Z]?\d{1,2})\sVALID')
        match = pattern.search(self.message)
        return match.group(1) if match else None

    def type(self):
        if 'AIRMET' in self.message:
            return 'WA'

        if self.hazard() == 'ash':
            return 'WV'

        if self.hazard() == 'typhoon':
            return 'WC'

        return 'WS'

    def hazard(self):
        patterns = [
            ('typhoon', re.compile(r'\b(?:WC[A-Z]{2}\d{2}|TC)\b')),
            ('ash', re.compile(r'\b(?:WV[A-Z]{2}\d{2}|VA)\b')),
            ('ice', re.compile(r'\bICE\b')),
            ('turb', re.compile(r'\bTURB\b')),
            ('ts', re.compile(r'\b(?:TS|TSGR)\b')),
        ]

        for key, pattern in patterns:
            if pattern.search(self.message):
                return key

        return 'other'

    def sequence(self):
        pattern = re.compile(r'(SIGMET|AIRMET)\s([A-Z]?\d{1,2})\sVALID')
        match = pattern.search(self.message)
        return match.group(2) if match else None

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
            if key == 'circle' and not self.grammar.radius.search(self.message):
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
        from tafor.core.geometry.algorithm import decode
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
                    'valids': valid.split('/') if valid else [],
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
        return joinRendered([e.renderer() for e in self.elements])

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
        return joinRendered([o for o in outputs if o], style)
