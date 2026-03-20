import re
import logging


logger = logging.getLogger('tafor.parser')


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

    airmansFlightLevel = re.compile(r'(FL\d{3}/\d{3})|(FL\d{3})|(\d{4,5}FT)|(\d{4,5}M)|(SFC/FL\d{3})')
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


__all__ = [
    '_purePattern',
    'Pattern',
    'TafGrammar',
    'MetarGrammar',
    'SigmetGrammar',
    'AdvisoryGrammar',
]
