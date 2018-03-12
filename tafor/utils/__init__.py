from tafor.utils.check import CheckTAF, Listen
from tafor.utils.validator import Validator, Grammar, Pattern, Parser
from tafor.utils.aftn import AFTNMessage
from tafor.utils.modem import serialComm
from tafor.utils.pagination import paginate


def checkVersion(releaseVersion, currentVersion):
    def versionNum(version):
        version = version.replace('v', '')
        if 'beta' in version:
            version, betaNum = version.split('-beta')
        else:
            betaNum = None

        nums = version.split('.')
        stableNum = 0
        multiple = 100

        for n in nums:
            stableNum += int(n) * multiple
            multiple = multiple / 10

        return {
            'stable': stableNum,
            'beta':  betaNum
        }

    current = versionNum(currentVersion)
    release = versionNum(releaseVersion)
    hasNewVersion = False

    if release['stable'] > current['stable']:
        hasNewVersion = True

    if release['stable'] == current['stable']:
        if release['beta'] is None and current['beta']:
            hasNewVersion = True

        if release['beta'] and current['beta'] and release['beta'] > current['beta']:
            hasNewVersion = True

    return hasNewVersion

def formatTimeInterval(interval, time=None):
    import datetime
    time = time if time else datetime.datetime.utcnow()
    startHour = int(interval[:2])
    endHour = 0 if interval[2:] in ['24', ''] else int(interval[2:])

    base = datetime.datetime(time.year, time.month, time.day)
    delta = datetime.timedelta(hours=endHour) if startHour < endHour else datetime.timedelta(days=1, hours=endHour)
    start = base + datetime.timedelta(hours=startHour)
    end = base + delta

    return start, end

def formatTime(timeString, time=None):
    import datetime
    time = time if time else datetime.datetime.utcnow()
    hour = int(timeString[0:2])
    minute = int(timeString[2:])

    base = time.replace(hour=hour, minute=minute)
    result = base if base > time else base + datetime.timedelta(days=1)
    return result

def ceilTime(time, amount=10):
    import datetime
    time = time - datetime.timedelta(minutes=time.minute % 5,
                             seconds=time.second,
                             microseconds=time.microsecond)
    return time + datetime.timedelta(minutes=amount)

def addMonths(date, months):
    import datetime, calendar
    month = date.month - 1 + months
    year = date.year + month // 12
    month = month % 12 + 1
    day = min(date.day, calendar.monthrange(year, month)[1])
    return datetime.date(year, month, day)

def calcPosition(latitude, longitude, speed, time, degree):
    import math

    def formatToDegree(text):
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

    def formatToString(degree, fmt='latitude'):
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

    def distance(speed, time, degree):
        dis = int(speed) * int(time) / 3600
        theta = math.radians(int(degree))
        dy = math.cos(theta) * dis
        dx = math.sin(theta) * dis

        return dx, dy

    latitude = formatToDegree(latitude)
    longitude = formatToDegree(longitude)
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

    return formatToString(newLatitude), formatToString(newLongitude, fmt='longitude')

