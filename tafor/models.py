import os
import re
import json
import datetime

from uuid import uuid4

from sqlalchemy import Column, Integer, String, Text, DateTime, create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.schema import ForeignKey
from sqlalchemy.ext.declarative import declarative_base

from tafor import root

if os.environ.get('TAFOR_ENV') == 'TEST':
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(root, '../tests/db.sqlite3')
else:
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(root, 'db.sqlite3')

uniqueid = lambda: str(uuid4())

Base = declarative_base()

class Taf(Base):
    __tablename__ = 'tafs'

    id = Column(Integer, primary_key=True)
    uuid = Column(String(36), default=uniqueid)
    tt = Column(String(2), nullable=False)
    sign = Column(String(36))
    rpt = Column(Text, nullable=False)
    raw = Column(Text)
    file = Column(Text)
    source = Column(String(16), default='self')
    sent = Column(DateTime, default=datetime.datetime.utcnow)
    confirmed = Column(DateTime)

    def __repr__(self):
        return '<TAF %r %r>' % (self.tt, self.rpt)

    @property
    def rptInline(self):
        return self.rpt.replace('\n', ' ')

    @property
    def report(self):
        parser = self.parser()
        parts = [self.sign, parser.renderer()]
        return '\n'.join(filter(None, parts))

    def parser(self):
        from tafor.utils import TafParser
        return TafParser(self.rpt)

    def rawText(self):
        if not self.raw:
            return ''
        messages = json.loads(self.raw)
        return '\r\n\r\n\r\n\r\n'.join(messages)

    def isCnl(self):
        items = self.rpt.split()
        return 'CNL' in items

class Metar(Base):
    __tablename__ = 'metars'

    id = Column(Integer, primary_key=True)
    uuid = Column(String(36), default=uniqueid)
    tt = Column(String(2), nullable=False)
    rpt = Column(Text, nullable=False)
    created = Column(DateTime, default=datetime.datetime.utcnow)

    def __repr__(self):
        return '<METAR %r %r>' % (self.tt, self.rpt)

    def parser(self):
        from tafor.utils import MetarParser
        return MetarParser(self.rpt)

class Task(Base):
    __tablename__ = 'tasks'

    id = Column(Integer, primary_key=True)
    tt = Column(String(2), nullable=False)
    sign = Column(String(36))
    rpt = Column(Text, nullable=False)
    created = Column(DateTime, default=datetime.datetime.utcnow)
    planning = Column(DateTime)

    taf_id = Column(Integer, ForeignKey('tafs.id'))

    def __repr__(self):
        return '<Task %r %r %r>' % (self.tt, self.rpt, self.planning)

class Trend(Base):
    __tablename__ = 'trends'

    id = Column(Integer, primary_key=True)
    uuid = Column(String(36), default=uniqueid)
    sign = Column(String(36))
    rpt = Column(Text, nullable=False)
    raw = Column(Text)
    source = Column(String(16), default='self')
    sent = Column(DateTime, default=datetime.datetime.utcnow)

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
    uuid = Column(String(36), default=uniqueid)
    tt = Column(String(2), nullable=False)
    sign = Column(String(36))
    rpt = Column(Text, nullable=False)
    raw = Column(Text)
    file = Column(Text)
    source = Column(String(16), default='self')
    sent = Column(DateTime, default=datetime.datetime.utcnow)
    confirmed = Column(DateTime, nullable=True)

    def __repr__(self):
        return '<SIGMET %r %r>' % (self.tt, self.rpt)

    @property
    def report(self):
        parts = [self.sign, self.rpt]
        return '\n'.join(filter(None, parts))

    def parser(self):
        from tafor.utils import SigmetParser
        return SigmetParser(self.report)

    def rawText(self):
        if not self.raw:
            return ''
        messages = json.loads(self.raw)
        return '\r\n\r\n\r\n\r\n'.join(messages)

    def expired(self):
        from tafor.utils.convert import parseTime
        parser = self.parser()
        _, ending = parser.valids()
        return parseTime(ending, self.sent)

    def isCnl(self):
        items = self.rpt.split()
        return 'CNL' in items

    def isExpired(self):
        return datetime.datetime.utcnow() > self.expired()

class Other(Base):
    __tablename__ = 'others'

    id = Column(Integer, primary_key=True)
    uuid = Column(String(36), default=uniqueid)
    tt = Column(String(2))
    sign = Column(String(36))
    rpt = Column(Text, nullable=False)
    raw = Column(Text)
    file = Column(Text)
    source = Column(String(16), default='self')
    sent = Column(DateTime, default=datetime.datetime.utcnow)

    def __repr__(self):
        return '<Other %r %r>' % (self.tt, self.rpt)

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    name = Column(String(8))
    mobile = Column(String(20))

    def __repr__(self):
        return '<User %r %r>' % (self.name, self.mobile)



engine = create_engine(SQLALCHEMY_DATABASE_URI, echo=False)
Session = sessionmaker(bind=engine)
db = Session()

Base.metadata.create_all(engine)
