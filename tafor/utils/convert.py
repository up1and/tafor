import math
import calendar
import datetime

from dateutil import relativedelta

from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import QRect, Qt

from tafor import logger


def isOverlap(basetime, reftime):
    """判断时间是否有重叠

    :param basetime: Datetime 对象
    :param reftime: Datetime 对象
    :return: 返回布尔值，时间是否有重叠
    """
    start = max(basetime[0], reftime[0])
    end = min(basetime[1], reftime[1])
    total = (end - start).total_seconds()
    return total > 0

def parseDayHour(day, hour, basetime, delta=None):
    day = int(day)
    hour = int(hour)
    if hour == 24:
        time = datetime.datetime(basetime.year, basetime.month, day) + datetime.timedelta(days=1)
    else:
        time = datetime.datetime(basetime.year, basetime.month, day, hour)

    deltas = {
        'month': relativedelta.relativedelta(months=1),
        'day': datetime.timedelta(days=1)
    }

    timedelta = deltas.get(delta, None)
    if timedelta and time < basetime:
        time += timedelta

    return time

def parseStandardPeriod(period, basetime=None):
    """解析字符为时间间隔

    :param period: 时间间隔，如 0912/0921
    :param basetime: 基准时间，默认为当前时间，自定义时需传入 Datetime 对象
    :return: 返回元组，包含起始时间和结束时间的 Datetime 对象
    """
    basetime = basetime if basetime else datetime.datetime.utcnow()
    startTime, endTime = period.split('/')

    # 基准时间月份没有 31 日时，用过去一月视为基准时间，仅适用于解析已发布的报文
    if max([int(startTime[:2]), int(endTime[:2])]) > calendar.monthrange(basetime.year, basetime.month)[1]:
        basetime -= relativedelta.relativedelta(months=1)

    start = parseDayHour(startTime[:2], startTime[2:], basetime, delta='month')
    end = parseDayHour(endTime[:2], endTime[2:], basetime, delta='month')

    if end <= start:
        end += relativedelta.relativedelta(months=1)

    return start, end

def parseOldPeriod(interval, basetime=None):
    """解析字符为时间间隔
    :param interval: 时间间隔，如 0312
    :param basetime: 基准时间，默认为当前时间，自定义时需传入 Datetime 对象
    :return: 返回元组，包含起始时间和结束时间的 Datetime 对象
    """
    basetime = basetime if basetime else datetime.datetime.utcnow()

    start = parseDayHour(basetime.day, interval[:2], basetime, delta='day')
    end = parseDayHour(basetime.day, interval[2:], basetime, delta='day')

    if end <= start:
        end += datetime.timedelta(days=1)

    return start, end

def parsePeriod(period, basetime=None):
    if len(period) == 9:
        return parseStandardPeriod(period, basetime)

    if len(period) == 6:
        return parseOldPeriod(period[2:], basetime)

    if len(period) == 4:
        return parseOldPeriod(period, basetime)

def parseHourMinute(hour, minute, basetime=None):
    """解析小时分钟字符为 Datetime 对象, 如果小于当前时间视为第二天

    :param hour: 小时
    :param minute: 分钟
    :param basetime: 基准时间，默认为当前时间，自定义时需传入 Datetime 对象
    :return: 返回 Datetime 对象
    """
    basetime = basetime if basetime else datetime.datetime.utcnow()
    hour = int(hour)
    minute = int(minute)

    if hour == 24:
        time = datetime.datetime(basetime.year, basetime.month, basetime.day, 0, minute) + datetime.timedelta(days=1)
    else:
        time = datetime.datetime(basetime.year, basetime.month, basetime.day, hour, minute)

    if time < basetime:
        time += datetime.timedelta(days=1)

    return time

def parseDayHourMinute(day, hour, minute, basetime=None):
    """解析包含日期的小时分钟字符为 Datetime 对象, 如果小于当前时间视为下一个月

    :param day: 日期
    :param hour: 小时
    :param minute: 分钟
    :param basetime: 基准时间，默认为当前时间，自定义时需传入 Datetime 对象
    :return: 返回 Datetime 对象
    """
    basetime = basetime if basetime else datetime.datetime.utcnow()
    day = int(day)
    hour = int(hour)
    minute = int(minute)

    if day > calendar.monthrange(basetime.year, basetime.month)[1]:
        basetime = basetime + relativedelta.relativedelta(months=1)
        time = datetime.datetime(basetime.year, basetime.month, day, hour, minute)
    else:
        time = datetime.datetime(basetime.year, basetime.month, day, hour, minute)
        if time < basetime:
            time = time + relativedelta.relativedelta(months=1)

    return time

def parseTime(time, basetime=None):
    if len(time) == 6:
        return parseDayHourMinute(time[:2], time[2:4], time[4:], basetime)

    if len(time) == 4:
        return parseHourMinute(time[:2], time[2:], basetime)

def parseTimez(timez):
    """解析报文的日期组，推算报文的发送时间，当月没有的日期视为上一个月

    :param timez: 报文日期组，如 150113Z
    :return: 返回 Datetime 对象
    """
    basetime = datetime.datetime.utcnow()
    day = int(timez[:2])
    hour = int(timez[2:4])
    minute = int(timez[4:6])

    if day > calendar.monthrange(basetime.year, basetime.month)[1]:
        basetime -= relativedelta.relativedelta(months=1)

    current = datetime.datetime(basetime.year, basetime.month, day, hour, minute)
    return current

def ceilTime(time, amount=10):
    """时间添加一个增量，并使分钟为 5 的倍数

    :param time: Datetime 对象
    :param amount: 需要增加的量，单位分钟
    :return: 返回 Datetime 对象
    """
    time = time - datetime.timedelta(minutes=time.minute % 5,
                             seconds=time.second,
                             microseconds=time.microsecond)
    return time + datetime.timedelta(minutes=amount)

def roundTime(time):
    """当前时间以小时为单位向前取整

    :param time: Datetime 对象
    :return: 返回 Datetime 对象
    """
    time = time.replace(minute=0, second=0, microsecond=0)
    return time + datetime.timedelta(hours=1)

def degreeToDecimal(text):
    """转换度分为十进制角度

    :param text: 字符，如 E11021
    :return: 字符，如 110.30
    """
    identifier = text[0]
    value = text[1:]
    if len(value) in [2, 3]:
        degree = int(value)
    else:
        integer, decimal = value[:-2], value[-2:]
        degree = int(integer) + int(decimal) / 60.0

    if identifier in ['S', 'W']:
        return -degree

    return degree

def decimalToDegree(degree, fmt='latitude'):
    """转换十进制角度为度分

    :param degree: 字符，如 -20.5
    :param fmt: 格式化方式，可选参数 'longitude'、'latitude'，代表经度或是纬度
    :return: 字符，如 S2030
    """
    integer = int(abs(degree))
    decimal = int(abs(degree) % 1 * 60) / 100

    if fmt == 'latitude':
        if degree >= 0:
            identifier = 'N'
        else:
            identifier = 'S'

        template = '{:05.2f}'
    else:
        if degree >= 0:
            identifier = 'E'
        else:
            identifier = 'W'

        template = '{:06.2f}'

    value = template.format(integer + decimal)
    text = identifier + str(value).replace('.', '')
    return text

def calcPosition(latitude, longitude, speed, time, degree):
    """根据当前的经纬度，已知点的移动方向和速度，计算一定时间之后的经纬度坐标

    :param latitude: 字符，如 N1930
    :param longitude: 字符，如 E11236
    :param speed: 移动速度，单位千米每小时，如 25
    :param time: 移动时间，单位秒，如 7200
    :param degree: 移动方向，如 90
    :return: 元组，如 ('N2021', 'E11042')
    """
    def distance(speed, time, degree):
        dis = int(speed) * int(time) / 3600
        theta = math.radians(int(degree))
        dy = math.cos(theta) * dis
        dx = math.sin(theta) * dis

        return dx, dy

    latitude = degreeToDecimal(latitude)
    longitude = degreeToDecimal(longitude)
    dx, dy = distance(speed, time, degree)

    radius = 6378 # 地球半径

    dlong = math.pi * radius * math.cos(latitude * math.pi / 180) / 180 # 每度精度的长度
    dlat = math.pi * radius / 180 # 每度纬度的长度，约 111 km

    newLatitude = latitude + dy / dlat
    newLongitude = longitude + dx / dlong

    if abs(newLatitude) > 90:
        newLatitude = 90 if newLatitude > 0 else -90

    if abs(newLongitude) > 180:
        newLongitude =  abs(newLongitude) % 180 - 180

    return decimalToDegree(newLatitude), decimalToDegree(newLongitude, fmt='longitude')

def distanceBetweenPoints(point1, point2):
    x = point1[0] - point2[0]
    y = point1[1] - point2[1]
    return math.sqrt(x ** 2 + y ** 2)

def distanceBetweenLatLongPoints(point1, point2):
    """Use haversine formula to calculate the great-circle distance between two points
    """
    deg2rad = lambda deg: deg * math.pi / 180

    long1, lat1 = point1
    long2, lat2 = point2

    radius = 6378
    dlat = deg2rad(lat2-lat1)
    dlong = deg2rad(long2-long1)

    a = math.sin(dlat/2) * math.sin(dlat/2) + math.cos(deg2rad(lat1)) * math.cos(deg2rad(lat2)) * math.sin(dlong/2) * math.sin(dlong/2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return radius * c

def listToPoint(points):
    """列表格式的坐标点转换为 QPoint

    :param points: 列表，如 [[20, 30], [10, 15]]
    :return: 列表，如 [QPoint(20, 30), QPoint(10, 15)]
    """
    from PyQt5.QtCore import QPoint
    return [QPoint(p[0], p[1]) for p in points]

def pointToList(points):
    """QPoint 格式的坐标点转换为列表

    :param points: 列表，如 [QPoint(20, 30), QPoint(10, 15)]
    :return: 列表，如 [[20, 30], [10, 15]]
    """
    return [[p.x(), p.y()] for p in points]


class Layer(object):

    def __init__(self, layers, width=300):
        self.image = layers.get('image', None)
        self.name = layers.get('name', '')
        self._size = layers.get('size', [0, 0])
        self._coordinates = layers.get('coordinates', [])
        self._rect = layers.get('rect', [0, 0, 0, 0])
        self._updated = layers.get('updated', None)
        self.width = width
        try:
            self.computed()
            self.drawable = True
        except Exception:
            self.drawable = False

    @property
    def scale(self):
        imageWidth = self._rect[2]
        if imageWidth == 0:
            return 1
        return self.width / imageWidth

    def rect(self):
        return [self.scale * i for i in self._rect]

    def size(self):
        return [self.scale * i for i in self._size]

    def updatedTime(self):
        fmt = '%a, %d %b %Y %H:%M:%S GMT'
        try:
            return datetime.datetime.strptime(self._updated, fmt)
        except Exception as e:
            return None

    def pixmap(self):
        if self.image is None:
            raw = QPixmap(*self.size())
            raw.fill(Qt.gray)
        else:
            raw = QPixmap()
            raw.loadFromData(self.image)
            raw = raw.scaled(*self.size())

        rect = QRect(*self.rect())
        image = raw.copy(rect)
        return image

    def computed(self):
        size = self.size()
        rect = self.rect()
        latRange = self._coordinates[0][1] - self._coordinates[1][1]
        longRange = self._coordinates[1][0] - self._coordinates[0][0]
        self.initLong = self._coordinates[0][0]
        self.initLat = self._coordinates[0][1]
        self.dlat = latRange / size[1]
        self.dlong = longRange / size[0]
        self.offsetX = rect[0]
        self.offsetY = rect[1]

        self.topLeft = [rect[0], rect[1]]
        self.topRight = [rect[0] + rect[2], rect[1]]
        self.bottomRight = [rect[0] + rect[2], rect[1] + rect[3]]
        self.bottomLeft = [rect[0], rect[1] + rect[3]]

    def dimension(self, mode='kilometer'):
        if mode == 'kilometer':
            distance = distanceBetweenLatLongPoints(*self._coordinates)

        if mode == 'nauticalmile':
            distance = distanceBetweenLatLongPoints(*self._coordinates) / 1.852

        if mode == 'decimal':
            distance = distanceBetweenPoints(*self._coordinates)

        if mode == 'pixel':
            distance = distanceBetweenPoints([0, 0], self._size)

        return distance

    def decimalToPixel(self, degreePoints):
        points = []
        for lng, lat in degreePoints:
            x = (lng - self.initLong) / self.dlong - self.offsetX
            y = (self.initLat - lat) / self.dlat - self.offsetY
            points.append((x, y))

        return points

    def pixelToDecimal(self, pixelPoints):
        points = []
        for lng, lat in pixelPoints:
            longtitude = self.initLong + (lng + self.offsetX) * self.dlong
            latitude = self.initLat - (lat + self.offsetY) * self.dlat
            points.append((longtitude, latitude))

        return points

    def pixelToDegree(self, pixelPoints):
        points = []
        for lng, lat in pixelPoints:
            longtitude = self.initLong + (lng + self.offsetX) * self.dlong
            latitude = self.initLat - (lat + self.offsetY) * self.dlat
            points.append((
                decimalToDegree(longtitude, fmt='longitude'),
                decimalToDegree(latitude)
            ))

        return points

    def decimalToDegree(self, decimalPoints):
        points = []
        for lng, lat in decimalPoints:
            points.append((
                decimalToDegree(lng, fmt='longitude'),
                decimalToDegree(lat)
            ))

        return points

    def distanceToDecimal(self, length, unit='KM'):
        mode = 'nauticalmile' if unit == 'NM' else 'kilometer'
        ratio = self.dimension('decimal') / self.dimension(mode)
        return float(length) * ratio

    def distanceToPixel(self, length, unit='KM'):
        mode = 'nauticalmile' if unit == 'NM' else 'kilometer'
        ratio = self.dimension('pixel') / self.dimension(mode)
        return float(length) * ratio * self.scale

    def pixelToDistance(self, pixel, unit='KM'):
        ratio = self.dimension('kilometer') / self.dimension('pixel')
        distance = pixel * ratio / self.scale
        if unit == 'NM':
            distance = distance / 1.852
        return distance

    def decodeSigmetArea(self, area, boundaries, trim):
        from tafor.utils.sigmet import decodeSigmetArea

        polygon = []
        maxx, maxy = self.rect()[2:]

        if area['type'] == 'polygon':
            decimals = [(degreeToDecimal(lng), degreeToDecimal(lat)) for lat, lng in area['area']]

            try:
                polygon = decodeSigmetArea(boundaries, decimals, mode='polygon', trim=trim)
                polygon = self.decimalToPixel(polygon)
            except Exception as e:
                logger.error(e)

        if area['type'] == 'line':
            decimals = []
            for identifier, *points in area['area']:
                points = [(degreeToDecimal(lng), degreeToDecimal(lat)) for lat, lng in points]
                decimals.append((identifier, points))

            try:
                polygon = decodeSigmetArea(boundaries, decimals, mode='line')
                polygon = self.decimalToPixel(polygon)
            except Exception as e:
                logger.error(e)

        if area['type'] == 'rectangular':
            maxx, maxy = self.rect()[2:]
            decimals = []
            for identifier, deg in area['area']:
                dec = degreeToDecimal(deg)
                if identifier in ['N', 'S']:
                    y = (self.initLat - dec) / self.dlat - self.offsetY
                    points = [
                        (0, y),
                        (maxx, y)
                    ]
                else:
                    x = (dec - self.initLong) / self.dlong - self.offsetX
                    points = [
                        (x, 0),
                        (x, maxy)
                    ]

                decimals.append((identifier, self.pixelToDecimal(points)))

            try:
                polygon = decodeSigmetArea(boundaries, decimals, mode='rectangular')
                polygon = self.decimalToPixel(polygon)
            except Exception as e:
                logger.error(e)

        if area['type'] == 'circle':
            point, radius = area['area']
            width = self.distanceToDecimal(*radius)
            center = [degreeToDecimal(point[1]), degreeToDecimal(point[0])]
            circles = [center, width]

            try:
                polygon = decodeSigmetArea(boundaries, circles, mode='circle')
                polygon = self.decimalToPixel(polygon)
            except Exception as e:
                logger.error(e)

        if area['type'] == 'corridor':
            points, width = area['area']
            points = [(degreeToDecimal(lng), degreeToDecimal(lat)) for lat, lng in points]
            width = self.distanceToDecimal(*width)
            corridor = [points, width]

            try:
                polygon = decodeSigmetArea(boundaries, corridor, mode='corridor', trim=trim)
                polygon = self.decimalToPixel(polygon)
            except Exception as e:
                logger.error(e)

        if area['type'] == 'entire':
            polygon = self.decimalToPixel(boundaries)

        return polygon
