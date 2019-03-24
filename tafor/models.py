import os
import re
import json
import datetime

from sqlalchemy import Column, Integer, String, DateTime, create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.schema import ForeignKey
from sqlalchemy.ext.declarative import declarative_base

from tafor import root

if os.environ.get('TAFOR_ENV') == 'TEST':
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(root, '../tests/db.sqlite3')
else:
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(root, 'db.sqlite3')

Base = declarative_base()


class Taf(Base):
    __tablename__ = 'tafs'

    id = Column(Integer, primary_key=True)
    tt = Column(String(2))
    sign = Column(String(255), nullable=True)
    rpt = Column(String(255))
    raw = Column(String(255), nullable=True)
    sent = Column(DateTime, default=datetime.datetime.utcnow)
    confirmed = Column(DateTime, nullable=True)

    def __init__(self, tt, rpt, sign=None, raw=None, confirmed=None):
        self.tt = tt
        self.sign = sign
        self.rpt = rpt
        self.raw = raw
        self.confirmed = confirmed

    def __repr__(self):
        return '<TAF %r %r>' % (self.tt, self.rpt)

    @property
    def rptInline(self):
        return self.rpt.replace('\n', ' ')

    @property
    def report(self):
        from tafor.utils import TafParser
        rpt = TafParser(self.rpt)
        parts = [self.sign, rpt.renderer()]
        return '\n'.join(filter(None, parts))

    def rawText(self):
        if not self.raw:
            return ''
        messages = json.loads(self.raw)
        return '\r\n\r\n\r\n\r\n'.join(messages)

class Metar(Base):
    __tablename__ = 'metars'

    id = Column(Integer, primary_key=True)
    tt = Column(String(2))
    rpt = Column(String(255))
    created = Column(DateTime, default=datetime.datetime.utcnow)

    def __init__(self, tt, rpt):
        self.tt = tt
        self.rpt = rpt

    def __repr__(self):
        return '<METAR %r %r>' % (self.tt, self.rpt)

class Task(Base):
    __tablename__ = 'tasks'

    id = Column(Integer, primary_key=True)
    tt = Column(String(2))
    sign = Column(String(255))
    rpt = Column(String(255))
    created = Column(DateTime, default=datetime.datetime.utcnow)
    planning = Column(DateTime)

    taf_id = Column(Integer, ForeignKey('tafs.id'))

    def __init__(self, tt, sign, rpt, planning):
        self.tt = tt
        self.sign = sign
        self.rpt = rpt
        self.planning = planning

    def __repr__(self):
        return '<Task %r %r %r>' % (self.tt, self.rpt, self.planning)

class Trend(Base):
    __tablename__ = 'trends'

    id = Column(Integer, primary_key=True)
    sign = Column(String(16))
    rpt = Column(String(255))
    raw = Column(String(255))
    sent = Column(DateTime, default=datetime.datetime.utcnow)

    def __init__(self, sign, rpt, raw=None):
        self.sign = sign
        self.rpt = rpt
        self.raw = raw

    def __repr__(self):
        return '<Trend %r>' % (self.rpt)

    @property
    def tt(self):
        return 'TREND'

    @property
    def report(self):
        return self.rpt

    def rawText(self):
        if not self.raw:
            return ''
        messages = json.loads(self.raw)
        return '\r\n\r\n\r\n\r\n'.join(messages)

    def isNosig(self):
        return self.rpt == 'NOSIG='

class Sigmet(Base):
    __tablename__ = 'sigmets'

    id = Column(Integer, primary_key=True)
    tt = Column(String(2))
    sign = Column(String(255))
    rpt = Column(String(255))
    raw = Column(String(255))
    sent = Column(DateTime, default=datetime.datetime.utcnow)
    confirmed = Column(DateTime, nullable=True)

    def __init__(self, tt, sign, rpt, raw=None, confirmed=None):
        self.tt = tt
        self.sign = sign
        self.rpt = rpt
        self.raw = raw
        self.confirmed = confirmed

    def __repr__(self):
        return '<Sigmet %r %r>' % (self.tt, self.rpt)

    @property
    def report(self):
        parts = [self.sign, self.rpt]
        return '\n'.join(filter(None, parts))

    @property
    def sequence(self):
        pattern = re.compile(r'SIGMET ([A-Z]?\d{1,2}) VALID')
        return pattern.search(self.rpt).group(1)

    @property
    def cancelSequence(self):
        pattern = re.compile(r'CNL SIGMET ([A-Z]?\d{1,2})')
        return pattern.search(self.rpt).group(1)

    @property
    def valids(self):
        from tafor.utils.validator import SigmetGrammar
        pattern = SigmetGrammar.valid
        return pattern.search(self.rpt).groups()

    def rawText(self):
        if not self.raw:
            return ''
        messages = json.loads(self.raw)
        return '\r\n\r\n\r\n\r\n'.join(messages)

    def type(self):
        text = 'other'
        if self.tt == 'WS':
            if 'TS' in self.rpt:
                text = 'ts'
            elif 'TURB' in self.rpt:
                text = 'turb'
            elif 'ICE' in self.rpt:
                text = 'ice'

        if self.tt == 'WV':
            text = 'ash'

        if self.tt == 'WC':
            text = 'typhoon'

        return text

    def area(self):
        from tafor.utils.validator import SigmetGrammar
        rules = SigmetGrammar()
        patterns = {
            'POLYGON': rules.polygon,
            'LINE': rules.lines,
            'RECTANGULAR': rules.rectangulars,
            'ENTIRE': re.compile('ENTIRE')
        }
        _area = {
            'type': 'unknow',
            'area': []
        }

        for key, pattern in patterns.items():
            m = pattern.search(self.rpt)
            if not m:
                continue

            if key == 'POLYGON':
                text = m.group()
                point = rules.point
                points = point.findall(text)
                _area = {
                    'type': 'polygon',
                    'area': points
                }

            if key == 'LINE':
                text = m.group()
                point = rules.point
                line = rules.line
                locations = []
                for l in line.finditer(text):
                    identifier = l.group(1)
                    part = l.group()
                    points = point.findall(part)
                    points.insert(0, identifier)
                    locations.append(points)

                _area = {
                    'type': 'line',
                    'area': locations
                }

            if key == 'RECTANGULAR':
                text = m.group()
                line = rules.rectangular
                lines = line.findall(text)

                _area = {
                    'type': 'rectangular',
                    'area': lines
                }

            if key == 'ENTIRE':
                _area = {
                    'type': 'entire',
                    'area': []
                }

        return _area

    def expired(self):
        from tafor.utils.convert import parseTime
        ending = self.valids[1]
        return parseTime(ending, self.sent)

    def isCnl(self):
        return 'CNL' in self.rpt

    def isExpired(self):
        return datetime.datetime.utcnow() > self.expired()

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    name = Column(String(8))
    mobile = Column(String(20))

    def __init__(self, name, mobile):
        self.name = name
        self.mobile = mobile

    def __repr__(self):
        return '<User %r %r>' % (self.name, self.mobile)



engine = create_engine(SQLALCHEMY_DATABASE_URI, echo=False)
Session = sessionmaker(bind=engine)
db = Session()

Base.metadata.create_all(engine)