# -*- coding: utf-8 -*-
import datetime

from sqlalchemy import Column, Integer, String, DateTime, create_engine
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.schema import ForeignKey
from sqlalchemy.ext.declarative import declarative_base

# 创建对象的基类:
Base = declarative_base()

# 定义User对象:
class Tafor(Base):
    # 表的名字:
    __tablename__ = 'tafor'

    # 表的结构:
    id = Column(Integer, primary_key=True)
    tt = Column(String(2))
    rpt = Column(String(255))
    raw_rpt = Column(String(255))
    send_time = Column(DateTime, default=datetime.datetime.utcnow)
    confirm_time = Column(DateTime)

    schedule = relationship('Schedule')

    def __init__(self, tt, rpt, raw_rpt=None):
        self.tt = tt
        self.rpt = rpt
        self.raw_rpt = raw_rpt

    def __repr__(self):
        return '<TAF %r %r>' % (self.tt, self.rpt)


class Schedule(Base):

    __tablename__ = 'schedule'

    id = Column(Integer, primary_key=True)
    tt = Column(String(2))
    rpt = Column(String(255))
    create_time = Column(DateTime, default=datetime.datetime.utcnow)
    schedule_time = Column(DateTime)

    tafor_id = Column(Integer, ForeignKey('tafor.id'))

    def __init__(self, tt, rpt, schedule_time):
        self.tt = tt
        self.rpt = rpt
        self.schedule_time = schedule_time

    def __repr__(self):
        return '<Schedule TAF %r %r %r>' % (self.tt, self.rpt, self.schedule_time)

# 初始化数据库连接:
engine = create_engine('sqlite:///./db.sqlite3', echo=False)
# 创建DBSession类型:
Session = sessionmaker(bind=engine)

# 创建表
Base.metadata.create_all(engine)