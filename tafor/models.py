import os
import json
import datetime

from uuid import uuid4

from sqlalchemy import Column, Integer, String, Text, DateTime, create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from tafor import conf, root

if os.environ.get('TAFOR_ENV') == 'TEST':
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
else:
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(root, 'db.sqlite3')

uniqueid = lambda: str(uuid4())

Base = declarative_base()

class Taf(Base):
    __tablename__ = 'tafs'

    id = Column(Integer, primary_key=True)
    uuid = Column(String(36), default=uniqueid)
    type = Column(String(2), nullable=False)
    heading = Column(String(36))
    text = Column(Text, nullable=False)
    raw = Column(Text)
    protocol = Column(Text)
    source = Column(String(16), default='self')
    created = Column(DateTime, default=datetime.datetime.utcnow)
    confirmed = Column(DateTime)

    def __repr__(self):
        return '<TAF %r %r>' % (self.type, self.text)

    def flatternedText(self):
        return self.text.replace('\n', ' ')

    @property
    def report(self):
        parser = self.parser()
        parts = [self.heading, parser.renderer()]
        return '\n'.join(filter(None, parts))

    def parser(self, **kwargs):
        from tafor.utils import TafParser
        return TafParser(self.text, created=self.created, **kwargs)

    def rawText(self):
        if not self.raw:
            return ''

        if self.protocol == 'aftn':
            messages = json.loads(self.raw)
            return '\r\n\r\n\r\n\r\n'.join(messages)

        return self.raw

    def isCnl(self):
        items = self.text.split()
        return 'CNL' in items

class Metar(Base):
    __tablename__ = 'metars'

    id = Column(Integer, primary_key=True)
    uuid = Column(String(36), default=uniqueid)
    type = Column(String(2), nullable=False)
    text = Column(Text, nullable=False)
    created = Column(DateTime, default=datetime.datetime.utcnow)

    def __repr__(self):
        return '<METAR %r %r>' % (self.type, self.text)

    @property
    def report(self):
        return self.text

    def parser(self, ignoreMetar=True, **kwargs):
        from tafor.utils import MetarParser
        return MetarParser(self.text, ignoreMetar=ignoreMetar, **kwargs)

class Trend(Base):
    __tablename__ = 'trends'

    id = Column(Integer, primary_key=True)
    uuid = Column(String(36), default=uniqueid)
    text = Column(Text, nullable=False)
    raw = Column(Text)
    protocol = Column(Text)
    source = Column(String(16), default='self')
    created = Column(DateTime, default=datetime.datetime.utcnow)

    def __repr__(self):
        return '<Trend %r>' % (self.text)
    
    @property
    def heading(self):
        return conf.value('Message/TrendIdentifier')

    @property
    def type(self):
        return 'TREND'

    @property
    def report(self):
        return self.text

    def rawText(self):
        if not self.raw:
            return ''

        if self.protocol == 'aftn':
            messages = json.loads(self.raw)
            return '\r\n\r\n\r\n\r\n'.join(messages)

        return self.raw

    def isNosig(self):
        return self.text == 'NOSIG='

class Sigmet(Base):
    __tablename__ = 'sigmets'

    id = Column(Integer, primary_key=True)
    uuid = Column(String(36), default=uniqueid)
    type = Column(String(2), nullable=False)
    heading = Column(String(36))
    text = Column(Text, nullable=False)
    raw = Column(Text)
    protocol = Column(Text)
    source = Column(String(16), default='self')
    created = Column(DateTime, default=datetime.datetime.utcnow)
    confirmed = Column(DateTime, nullable=True)

    def __repr__(self):
        return '<SIGMET %r %r>' % (self.type, self.text)

    @property
    def report(self):
        parts = [self.heading, self.text]
        return '\n'.join(filter(None, parts))

    def parser(self, **kwargs):
        from tafor.utils import SigmetParser
        return SigmetParser(self.report, created=self.created, **kwargs)

    def rawText(self):
        if not self.raw:
            return ''

        if self.protocol == 'aftn':
            messages = json.loads(self.raw)
            return '\r\n\r\n\r\n\r\n'.join(messages)

        return self.raw

    def expired(self):
        parser = self.parser()
        ending = parser.valids[1]
        return ending

    def isCnl(self):
        items = self.text.split()
        return 'CNL' in items

    def isExpired(self):
        return datetime.datetime.utcnow() > self.expired()

class Other(Base):
    __tablename__ = 'others'

    id = Column(Integer, primary_key=True)
    uuid = Column(String(36), default=uniqueid)
    text = Column(Text, nullable=False)
    raw = Column(Text)
    protocol = Column(Text)
    source = Column(String(16), default='self')
    created = Column(DateTime, default=datetime.datetime.utcnow)

    def __repr__(self):
        return '<Other %r>' % (self.raw)

    @property
    def type(self):
        return ''

    @property
    def report(self):
        return self.text

    def rawText(self):
        if not self.raw:
            return ''

        if self.protocol == 'aftn':
            messages = json.loads(self.raw)
            return '\r\n\r\n\r\n\r\n'.join(messages)

        return self.raw


engine = create_engine(SQLALCHEMY_DATABASE_URI, echo=False)
Session = sessionmaker(bind=engine)
db = Session()

Base.metadata.create_all(engine)
