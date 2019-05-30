import datetime

from sqlalchemy import or_

from tafor import conf, logger
from tafor.models import db, Taf, Metar
from tafor.utils.validator import TafParser


class SpecFC(object):
    tt = 'FC'
    periods = ['0312', '0615', '0918', '1221', '1524', '1803', '2106', '0009']
    default = '0009'
    interval = datetime.timedelta(hours=3)
    delay = datetime.timedelta(minutes=50)
    begin = datetime.timedelta(hours=2)
    duration = datetime.timedelta(hours=9)


class SpecFT24(object):
    tt = 'FT'
    periods = ['0606', '1212', '1818', '0024']
    default = '0024'
    interval = datetime.timedelta(hours=6)
    delay = datetime.timedelta(hours=2, minutes=50)
    begin = datetime.timedelta(hours=5)
    duration = datetime.timedelta(hours=24)


class SpecFT30(object):
    tt = 'FT'
    periods = ['0612', '1218', '1824', '0006']
    default = '0006'
    interval = datetime.timedelta(hours=6)
    delay = datetime.timedelta(hours=2, minutes=50)
    begin = datetime.timedelta(hours=5)
    duration = datetime.timedelta(hours=30)


class CurrentTaf(object):
    """生成当前的 TAF 报文类型

    :param spec: TAF 报文规格，选项 fc, ft24, ft30
    :param time: 报文的生成时间
    :param prev: 0 代表当前报文，1 代表上一份报文，以此类推

    """

    specifications = {
        'fc': SpecFC,
        'ft24': SpecFT24,
        'ft30': SpecFT30
    }

    def __init__(self, spec, time=None, prev=0):
        self.spec = self.specifications[spec]
        self.time = datetime.datetime.utcnow() if time is None else time

        if prev:
            self.time -= self.spec.interval * prev

        self._initStartTime()

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
        offset = offset or conf.value('Monitor/WarnTAFTime')
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

        if self.time < startOfTheDay + datetime.timedelta(hours=1):
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
            if start <= self.time <= start + delay:
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


class CheckTaf(object):
    """检查 TAF 报文并储存

    :param taf: 当前报文对象
    :param message: TAF 报文内容

    """
    def __init__(self, taf, message=None):
        self.taf = taf
        self.tt = self.taf.spec.tt
        self.message = message

    def local(self, period=None):
        """返回本地数据当前时次的最新报文，忽略 AMD COR 报文

        :param period: 报文的有效时段
        :return: ORM 对象
        """
        period = self.taf.period(strict=False) if period is None else period
        expired = datetime.datetime.utcnow() - datetime.timedelta(hours=24)
        recent = db.query(Taf).filter(Taf.rpt.contains(period), ~Taf.rpt.contains('AMD'),
            ~Taf.rpt.contains('COR'), Taf.sent > expired).order_by(Taf.sent.desc()).first()
        return recent

    def isExist(self):
        """查询有没有已经入库的报文

        :return: ORM 对象
        """
        expired = datetime.datetime.utcnow() - datetime.timedelta(hours=24)
        try:
            taf = TafParser(self.message)
            last = db.query(Taf).filter(or_(Taf.rpt == self.message, Taf.rpt == taf.renderer()), Taf.sent > expired).order_by(Taf.sent.desc()).first()
        except Exception:
            last = db.query(Taf).filter(Taf.rpt == self.message, Taf.sent > expired).order_by(Taf.sent.desc()).first()

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

            item = Taf(tt=self.tt, rpt=self.message, confirmed=self.taf.time)
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

    def __call__(self, tt, spec=None):
        from tafor.states import context

        self.tt = tt
        self.spec = spec or context.taf.spec
        state = context.message.state()
        self.message = state.get(self.tt, None)
        method = {'FC': 'taf', 'FT': 'taf', 'SA': 'metar', 'SP': 'metar'}
        return getattr(self.__class__, method[self.tt])(self)

    def taf(self):
        """储存并更新本地 TAF 报文状态"""
        from tafor.states import context

        taf = CurrentTaf(self.spec)
        check = CheckTaf(taf, message=self.message)
        clock = taf.hasExpired(offset=5)

        # 储存确认报文
        if self.message:
            check.save(callback=self.callback)

            latest = check.latest()
            if latest and not latest.confirmed:
                check.confirm(callback=self.callback)

        # 查询报文是否过期
        expired = False

        if taf.hasExpired():
            local = check.local()
            if local:
                if not local.confirmed:
                    expired = True
            else:
                expired = True

        # 最后一份报文不存在或是取消报时不再告警
        latest = check.latest()
        if latest and latest.isCnl() or not latest:
            expired = False
            clock = False

        # 更新状态
        context.taf.setState({
            taf.spec.tt: {
                'period': taf.period(strict=False),
                'sent': True if check.local() else False,
                'warning': expired,
                'clock': clock,
            }
        })

    def metar(self):
        """储存 METAR 报文"""
        metar = CheckMetar(self.tt, message=self.message)
        if self.message:
            metar.save()

