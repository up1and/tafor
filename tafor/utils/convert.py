import math
import datetime

from Polygon import Polygon, Utils


def isOverlap(datetime1, datetime2):
    """判断时间是否有重叠

    :param datetime1: Datetime 对象
    :param datetime2: Datetime 对象
    :return: 返回布尔值，时间是否有重叠
    """
    start = max(datetime1[0], datetime2[0])
    end = min(datetime1[1], datetime2[1])
    total = (end - start).total_seconds()
    return total >= 0

def parseTimeInterval(interval, time=None):
    """解析字符为时间间隔

    :param interval: 时间间隔，如 0312
    :param time: 基准时间，默认为当前时间，自定义时需传入 Datetime 对象
    :return: 返回元组，包含起始时间和结束时间的 Datetime 对象
    """
    time = time if time else datetime.datetime.utcnow()
    startHour = int(interval[:2])
    endHour = 0 if interval[2:] in ['24', ''] else int(interval[2:])

    base = datetime.datetime(time.year, time.month, time.day)
    delta = datetime.timedelta(hours=endHour) if startHour < endHour else datetime.timedelta(days=1, hours=endHour)
    start = base + datetime.timedelta(hours=startHour)
    end = base + delta

    return start, end

def parseTime(timeString, time=None):
    """解析小时分钟字符为 Datetime 对象, 如果小于当前时间视为第二天

    :param timeString: 小时分钟字符，如 1930
    :param time: 基准时间，默认为当前时间，自定义时需传入 Datetime 对象
    :return: 返回 Datetime 对象
    """
    time = time if time else datetime.datetime.utcnow()
    hour = 0 if timeString[0:2] == '24' else int(timeString[0:2])
    minute = int(timeString[2:])

    base = time.replace(hour=hour, minute=minute)
    current = base if base > time else base + datetime.timedelta(days=1)
    return current

def parseDateTime(datetimeString, time=None):
    """解析包含日期的小时分钟字符为 Datetime 对象, 如果小于当前时间视为下一个月

    :param datetimeString: 包含日期的小时分钟字符，如 151930
    :param time: 基准时间，默认为当前时间，自定义时需传入 Datetime 对象
    :return: 返回 Datetime 对象
    """
    time = time if time else datetime.datetime.utcnow()

    day = int(datetimeString[0:2])
    hour = int(datetimeString[2:4])
    minute = int(datetimeString[4:])

    try:
        current = datetime.datetime(time.year, time.month, day, hour, minute)
        if current < time:
            current = datetime.datetime(time.year, time.month + 1, day, hour, minute)

    except ValueError:
        current = datetime.datetime(time.year, time.month + 2, day, hour, minute)

    return current

def parseTimez(timez):
    """解析报文的日期组，推算报文的发送时间，当月没有的日期视为上一个月

    :param timez: 报文日期组，如 150113Z
    :return: 返回 Datetime 对象
    """
    utc =  datetime.datetime.utcnow()
    try:
        time = datetime.datetime(utc.year, utc.month, int(timez[:2]), int(timez[2:4]), int(timez[4:6]))
    except ValueError:
        time = datetime.datetime(utc.year, utc.month - 1, int(timez[:2]), int(timez[2:4]), int(timez[4:6]))

    return time

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

def clipPolygon(subj, clip, maxPoint=7):
    """计算两个多边形之间的交集，并根据允许的最大点平滑多边形

        A General Polygon Clipping Library
        http://www.cs.man.ac.uk/~toby/alan/software/gpc.html

    :param subj: 列表，目标多边形的坐标集
    :param clip: 列表，相切多边形的坐标集
    :param maxPoint: 数字，交集允许的最大点
    :return: 列表，新的多边形坐标集
    """
    subj = Polygon(subj)
    clip = Polygon(clip)
    try:
        intersection = subj & clip
        points = Utils.pointList(intersection)
    except Exception as e:
        points = []
    finally:
        if len(points) > maxPoint:
            points = Utils.reducePoints(points, maxPoint)
        return points
