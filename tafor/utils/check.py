import datetime

from tafor import conf
from tafor.models import db, Taf, Metar, Sigmet
from tafor.utils.validator import SigmetParser


class SpecFC(object):
    type = 'FC'
    periods = ['0312', '0615', '0918', '1221', '1524', '1803', '2106', '0009']
    default = '0009'
    interval = datetime.timedelta(hours=3)
    delay = datetime.timedelta(minutes=50)
    begin = datetime.timedelta(hours=2)
    duration = datetime.timedelta(hours=9)


class SpecFT24(object):
    type = 'FT'
    periods = ['0606', '1212', '1818', '0024']
    default = '0024'
    interval = datetime.timedelta(hours=6)
    delay = datetime.timedelta(minutes=50)
    begin = datetime.timedelta(hours=3)
    duration = datetime.timedelta(hours=24)


class SpecFT30(object):
    type = 'FT'
    periods = ['0612', '1218', '1824', '0006']
    default = '0006'
    interval = datetime.timedelta(hours=6)
    delay = datetime.timedelta(minutes=50)
    begin = datetime.timedelta(hours=3)
    duration = datetime.timedelta(hours=30)


class CurrentTaf(object):
    """生成当前的 TAF 报文类型

    :param spec: TAF 报文规格，选项 fc, ft24, ft30
    :param time: 报文的生成时间
    :param offset: 0 代表当前报文，-1 代表上一份报文，1 代表下一份报文，以此类推

    """

    specifications = {
        'fc': SpecFC,
        'ft24': SpecFT24,
        'ft30': SpecFT30
    }

    def __init__(self, spec, time=None, offset=0):
        self.spec = self.specifications[spec]
        self.time = datetime.datetime.utcnow() if time is None else time

        if offset:
            self.time += self.spec.interval * offset

        self._initStartTime()

    def __repr__(self):
        return '<Current TAF {}{}>'.format(self.spec.type, self.period())

    def period(self, strict=True, withDay=True):
        if strict:
            return self._strict(withDay)
        else:
            return self._normal(withDay)

    def durations(self):
        """返回当前报文有效期

        """
        period = self._normal(withDay=False)
        start = self.startTime[period] + self.spec.begin
        end = start + self.spec.duration
        return start, end

    def hasExpired(self, offset=None):
        """当前时段报文是否过了有效发报时间

        :param offset: 过期时间，单位分钟
        """
        offset = offset or conf.delayMinutes
        offset = int(offset) if offset else 30
        hours = self.spec.delay // datetime.timedelta(hours=1)
        delta = datetime.timedelta(hours=hours, minutes=offset)
        period = self._normal(withDay=False)
        start = self.startTime[period]
        threshold = start + delta
        return threshold < self.time

    def _initStartTime(self):
        startOfTheDay = datetime.datetime(self.time.year, self.time.month, self.time.day)
        delta = self.spec.interval - self.spec.begin

        self.startTime = {}
        for i, period in enumerate(self.spec.periods):
            self.startTime[period] = startOfTheDay + delta + self.spec.interval * i

        if self.time < startOfTheDay + self.spec.interval - self.spec.begin:
            self.startTime[self.spec.default] -= datetime.timedelta(days=1)

    def _strict(self, withDay):
        period = self._findPeriod(self.spec.delay)

        if withDay:
            period = self._withDay(period)

        return period

    def _normal(self, withDay):
        period = self._findPeriod(self.spec.interval)

        if period is None:
            period = self.spec.default

        if withDay:
            period = self._withDay(period)

        return period

    def _findPeriod(self, delay):
        """查找当前的报文时段

        :param delay: 编辑报文的有效期
        :return: 不包含日期的报文时段
        """
        for period, start in self.startTime.items():
            if start <= self.time < start + delay:
                return period

    def _withDay(self, period):
        """返回报文时段带有日期"""
        if period is None:
            return

        start = self.startTime[period] + self.spec.begin
        end = start + self.spec.duration
        
        if '24' in period:
            end -= datetime.timedelta(minutes=1)

        periodWithDay = '{}{}/{}{}'.format(str(start.day).zfill(2), period[:2], str(end.day).zfill(2), period[2:])

        return periodWithDay


def availableMetar(type, message):
    with db.session() as session:
        last = session.query(Metar).filter_by(type=type).order_by(Metar.created.desc()).first()

    if last is None or last.text != message:
        return Metar(type=type, text=message)

def availableTaf(type, message):
    recent = datetime.datetime.utcnow() - datetime.timedelta(hours=32)
    with db.session() as session:
        tafs = session.query(Taf).filter(type==type, Taf.created > recent).all()

    def _match(objects, message):
        for taf in objects:
            if taf.flatternedText() == message:
                return taf

    matched = _match(tafs, message)
    if matched:
        if not matched.confirmed:
            matched.confirmed = datetime.datetime.utcnow()
            return matched
    else:
        return Taf(type=type, text=message, source='api', confirmed=datetime.datetime.utcnow())

def availableSigmet(type, messages):
    recent = datetime.datetime.utcnow() - datetime.timedelta(hours=24)
    time = datetime.datetime.utcnow()

    with db.session() as session:
        sigmets = session.query(Sigmet).filter(Sigmet.created > recent).all()

    availables = []
    for message in messages:
        message = ' '.join(message.split())
        parser = SigmetParser(message)

        if parser not in [sig.parser() for sig in sigmets]:
            item = Sigmet(type=type, heading=parser.heading, text=parser.text + '=', source='api', confirmed=time)
            availables.append(item)

        for sig in sigmets:
            if not sig.confirmed and sig.parser() == parser:
                sig.confirmed = time
                availables.append(sig)

    return availables


def findAvailables(messages, wishlist=None):
    availables = []
    for key, text in messages.items():
        if wishlist and key not in wishlist:
            continue

        if key in ['SA', 'SP']:
            message = availableMetar(key, text)
            if message:
                availables.append(message)

        if key in ['FC', 'FT']:
            message = availableTaf(key, text)
            if message:
                availables.append(message)

        if key in ['WS', 'WC', 'WV', 'WA']:
            message = availableSigmet(key, text)
            if message:
                availables += message

    return availables

def createTafStatus(spec):
    currentTaf = CurrentTaf(spec)
    period = currentTaf.period(strict=False)

    clockRemind = currentTaf.hasExpired(offset=5)
    hasExpired = False

    # Ignore AMD COR message
    expired = datetime.datetime.utcnow() - datetime.timedelta(hours=32)

    with db.session() as session:
        recent = session.query(Taf).filter(Taf.text.contains(period),  ~Taf.text.contains('AMD'),
        ~Taf.text.contains('COR'), Taf.created > expired).order_by(Taf.created.desc()).first()

    if currentTaf.hasExpired():
        if recent:
            if not recent.confirmed:
                hasExpired = True
        else:
            hasExpired = True

    # The alarm clock no longer rings after the cancel message is issued
    with db.session() as session:
        latest = session.query(Taf).filter_by(type=currentTaf.spec.type).order_by(Taf.created.desc()).first()

    if latest and latest.isCnl():
        hasExpired = False
        clockRemind = False

    return {
            'period': period,
            'message': recent,
            'hasExpired': hasExpired,
            'clockRemind': clockRemind,
        }

