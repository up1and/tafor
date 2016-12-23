# -*- coding: utf-8 -*-
import datetime

from sqlalchemy import Column, Integer, String, DateTime, create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# 创建对象的基类:
Base = declarative_base()

# 定义User对象:
class Tafor(Base):
    # 表的名字:
    # __tablename__ = 'tafor'

    # # 表的结构:
    # id = Column(Integer, primary_key=True)
    # tt = Column(String(2))
    # rpt = Column(String(255))
    # time = Column(DateTime, default=datetime.datetime.utcnow)

    # def __init__(self, tt=None, rpt=None):
    #     self.tt = tt
    #     self.rpt = rpt

    # def __repr__(self):
    #     return '<TAF %r %r>' % (self.tt, self.rpt)
    pass


class Schedule(base):
    pass

# 初始化数据库连接:
engine = create_engine('sqlite:///./db.sqlite3', echo=False)
# 创建DBSession类型:
session = sessionmaker(bind=engine)

# 创建表
Base.metadata.create_all(engine)