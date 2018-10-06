import datetime

from sqlalchemy import or_

from tafor import conf, logger
from tafor.models import db, Taf, Metar
from tafor.states import context
from tafor.utils.validator import TafParser


class CheckTaf(object):
    """检查 TAF 报文并储存

    :param tt: TAF 报文类型，FC 或 FT
    :param message: TAF 报文内容
    :param time: 报文的生成时间
    :param prev: 0 代表当前报文，1 代表上一份报文，以此类推

    """
    def __init__(self, tt, message=None, time=None, prev=0):
        self.tt = tt
        self.message = message
        self.time = datetime.datetime.utcnow() if time is None else time

        interval = {
            'FC': 3,
            'FT': 6,
        }

        self.interval = interval.get(self.tt)

        if prev:
            self.time -= datetime.timedelta(hours=self.interval * prev)

        startOfTheDay = datetime.datetime(self.time.year, self.time.month, self.time.day)
        startTime = dict()
        startTime['FC'] = {
                    '0312': startOfTheDay + datetime.timedelta(hours=1),
                    '0615': startOfTheDay + datetime.timedelta(hours=4),
                    '0918': startOfTheDay + datetime.timedelta(hours=7),
                    '1221': startOfTheDay + datetime.timedelta(hours=10),
                    '1524': startOfTheDay + datetime.timedelta(hours=13),
                    '1803': startOfTheDay + datetime.timedelta(hours=16),
                    '2106': startOfTheDay + datetime.timedelta(hours=19),
                    '0009': startOfTheDay + datetime.timedelta(hours=22),
        }
        startTime['FT'] = {
                    '0606': startOfTheDay + datetime.timedelta(hours=1),
                    '1212': startOfTheDay + datetime.timedelta(hours=7),
                    '1818': startOfTheDay + datetime.timedelta(hours=13),
                    '0024': startOfTheDay + datetime.timedelta(hours=19),
        }

        if self.time < startOfTheDay + datetime.timedelta(hours=1):
            startTime['FC']['0009'] -= datetime.timedelta(days=1)
            startTime['FT']['0024'] -= datetime.timedelta(days=1)

        endTimeDelta = {
            'FC': {
                'normal': datetime.timedelta(minutes=50),
                'warning': datetime.timedelta(hours=3),
            },
            'FT': {
                'normal': datetime.timedelta(hours=2, minutes=50),
                'warning': datetime.timedelta(hours=6),
            }
        }

        # 00 - 01 时次特殊情况
        defaultPeriod = {
            'FC': '0009', 
            'FT': '0024',
        }

        self.startTime = startTime.get(self.tt)
        self.endTimeDelta = endTimeDelta.get(self.tt)
        self.defaultPeriod = defaultPeriod.get(self.tt)

    def normalPeriod(self, withDay=True):
        """严格按照报文的发送时间生成报文时段

        :param withDay: 生成的时段是否带有日期
        :return: 报文时段
        """
        period = self._findPeriod(self.endTimeDelta['normal'])

        if withDay:
            return self._withDay(period)

        return period

    def warningPeriod(self, withDay=True):
        """根据告警模式的有效期生成报文时段

        :param withDay: 生成的时段是否带有日期
        :return: 报文时段
        """
        period = self._findPeriod(self.endTimeDelta['warning'], self.defaultPeriod)

        if withDay:
            return self._withDay(period)

        return period

    def local(self, period=None):
        """返回本地数据当前时次的最新报文，忽略 AMD COR 报文

        :param period: 报文的有效时段
        :return: ORM 对象
        """
        period = self.warningPeriod() if period is None else period
        expired = datetime.datetime.utcnow() - datetime.timedelta(hours=24)
        recent = db.query(Taf).filter(Taf.rpt.contains(period), ~Taf.rpt.contains('AMD'), 
            ~Taf.rpt.contains('COR'), Taf.sent > expired).order_by(Taf.sent.desc()).first()
        return recent

    def isExist(self):
        """查询有没有已经入库的报文

        :return: ORM 对象
        """
        expired = datetime.datetime.utcnow() - datetime.timedelta(hours=24)
        taf = TafParser(self.message)
        last = db.query(Taf).filter(or_(Taf.rpt == self.message, Taf.rpt == taf.renderer()), Taf.sent > expired).order_by(Taf.sent.desc()).first()
        return last

    def latest(self):
        """查询本地最新的报文

        :return: ORM 对象
        """
        last = db.query(Taf).filter_by(tt=self.tt).order_by(Taf.sent.desc()).first()
        return last

    def save(self, callback=None):
        """储存远程报文数据

        :param callback: 储存完成后的回掉函数
        """
        isExist = self.isExist()

        if isExist is None:  # 没有报文入库
            # 本地正常报已发，远程数据和本地数据不一样的情况不作入库处理
            # 修订报报文如果字符出了错误无法识别是否和本地是同一份，则会直接入库
            local = self.local()
            remote = TafParser(self.message)
            if local and not remote.isAmended() and remote.primary.tokens['period']['text'] in local.rpt:
                return 

            item = Taf(tt=self.tt, rpt=self.message, confirmed=self.time)
            db.add(item)
            db.commit()
            logger.info('Save {} {}'.format(self.tt, self.message))

            if callback:
                callback()

    def confirm(self, callback=None):
        """确认本地数据和远程数据是否一致

        :param callback: 确认完成后的回掉函数
        """
        last = self.latest()

        if last is not None and last.rptInline == self.message:
            last.confirmed = self.time
            db.commit()
            logger.info('Confirm {} {}'.format(self.tt, self.message))

            if callback:
                callback()

    def hasExpired(self, offset=None):
        """当前时段报文是否过了有效发报时间

        :param offset: 过期时间，单位分钟
        """
        offset = offset or conf.value('Monitor/WarnTAFTime')
        offset = int(offset) if offset else 30
        offsetTimeDelta = {
            'FC': datetime.timedelta(minutes=offset), 
            'FT': datetime.timedelta(hours=2, minutes=offset)
        }

        timedelta = offsetTimeDelta.get(self.tt)
        period = self.warningPeriod(withDay=False)
        start = self.startTime.get(period)

        threshold = start + timedelta
        return threshold < self.time

    def _findPeriod(self, endTimeDelta, default=None):
        """查找当前的报文时段

        :param endTimeDelta: 编辑报文的有效期
        :param default: 查询不到时返回默认值
        :return: 不包含日期的报文时段
        """
        for period, start in self.startTime.items():
            if start <= self.time <= start + endTimeDelta:
                return period

        if default:
            return default

    def _withDay(self, period):
        """返回报文时段带有日期"""
        if period is None:
            return None
        
        time = self.time

        # 跨越 UTC 日界
        if period in ('0009', '0024') and self.time.hour != 0:
            time = self.time + datetime.timedelta(days=1)

        periodWithDay = str(time.day).zfill(2) + period

        return periodWithDay


class CheckMetar(object):
    """检查 METAR 报文并储存

    :param tt: METAR 报文类型，SA 或 SP
    :param message: METAR 报文内容
    """
    def __init__(self, tt, message):
        self.tt = tt
        self.message = message

    def save(self):
        """储存远程报文数据"""
        last = db.query(Metar).filter_by(tt=self.tt).order_by(Metar.created.desc()).first()
        
        if last is None or last.rpt != self.message:
            item = Metar(tt=self.tt, rpt=self.message)
            db.add(item)
            db.commit()
            logger.info('Save {} {}'.format(self.tt, self.message))


class Listen(object):
    """监听远程报文数据

    :param callback: 回调函数

    使用方法::

        listen = Listen()
        # 监听不同类型的报文
        listen('SA')
        listen('FC')
        listen('FT')
        
    """
    def __init__(self, callback=None):
        self.callback = callback

    def __call__(self, tt):
        self.tt = tt
        state = context.message.state()
        self.message = state.get(self.tt, None)
        method = {'FC': 'taf', 'FT': 'taf', 'SA': 'metar', 'SP': 'metar'}
        return getattr(self.__class__, method[self.tt])(self)

    def taf(self):
        """储存并更新本地 TAF 报文状态"""
        taf = CheckTaf(self.tt, message=self.message)

        # 储存确认报文
        if self.message:
            taf.save(callback=self.callback)

            latest = taf.latest()
            if latest and not latest.confirmed:
                taf.confirm(callback=self.callback)

        # 查询报文是否过期
        expired = False
        
        if taf.hasExpired():
            local = taf.local()
            if local:
                if not local.confirmed:
                    expired = True
            else:
                expired = True

        # 更新状态
        context.taf.setState({
            taf.tt: {
                'period': taf.warningPeriod(),
                'sent': True if taf.local() else False,
                'warning': expired,
                'clock': taf.hasExpired(offset=5),
            }
        })

    def metar(self):
        """储存 METAR 报文"""
        metar = CheckMetar(self.tt, message=self.message)
        if self.message:
            metar.save()

