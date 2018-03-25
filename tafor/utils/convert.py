import math
import datetime

from Polygon import Polygon, Utils


def parseTimeInterval(interval, time=None):
    """
    解析字符串（0312）为时间间隔，返回起始时间和结束时间对象
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
    """
    解析字符串（1930）为时间对象, 如果小于当前时间视为第二天
    """
    time = time if time else datetime.datetime.utcnow()
    hour = int(timeString[0:2])
    minute = int(timeString[2:])

    base = time.replace(hour=hour, minute=minute)
    current = base if base > time else base + datetime.timedelta(days=1)
    return current

def parseDateTime(datetimeString, time=None):
    """
    解析字符串（151930）为时间对象，如果小于当前时间视为下一个月
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
    """
    解析字符串（150113Z）为时间对象，当月没有的日期视为上一个月
    """
    utc =  datetime.datetime.utcnow()
    try:
        time = datetime.datetime(utc.year, utc.month, int(timez[:2]), int(timez[2:4]), int(timez[4:6]))
    except ValueError:
        time = datetime.datetime(utc.year, utc.month - 1, int(timez[:2]), int(timez[2:4]), int(timez[4:6]))

    return time

def ceilTime(time, amount=10):
    """
    时间添加一个增量，并使分钟为 5 的倍数
    """
    time = time - datetime.timedelta(minutes=time.minute % 5,
                             seconds=time.second,
                             microseconds=time.microsecond)
    return time + datetime.timedelta(minutes=amount)

def degreeToDecimal(text):
    """
    转换度分为十进制角度
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
    """
    转换十进制角度为度分
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
    """
    根据当前的经纬度，已知点的移动方向和速度，返回一定时间之后的经纬度坐标
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
    from PyQt5.QtCore import QPoint
    return [QPoint(p[0], p[1]) for p in points]

def pointToList(points):
    return [[p.x(), p.y()] for p in points]

def clipPolygon(subj, clip, maxPoint=7):
    """
    A General Polygon Clipping Library
    http://www.cs.man.ac.uk/~toby/alan/software/gpc.html
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
