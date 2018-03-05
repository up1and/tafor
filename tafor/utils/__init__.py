from tafor.utils.check import CheckTAF, Listen
from tafor.utils.validator import Validator, Grammar, Pattern, Parser
from tafor.utils.aftn import AFTNMessage
from tafor.utils.modem import serialComm


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

def calcPosition(latitude, longitude, speed, time, degree):
    # r = 6378 km
    # latitude per degree = 2 * pi * r / 360 
    # longitude per degree = 2 * pi * r * cos(latitude) / 360
    import math

    def formatToDegree(text):
        sign = text[0]
        value = text[1:]
        if len(value) in [2, 3]:
            degree = int(value)
        else:
            integer, decimal = value[:-2], value[-2:]
            degree = int(integer) + int(decimal) / 60.0

        if sign in ['S', 'W']:
            return -degree
        
        return degree

    def formatToString(degree, fmt='latitude'):
        integer = round(degree)
        decimal = round(degree % 1 * 0.6, 2)

        if decimal == 0:
            value = int(integer)
        else:
            value = integer + decimal

        if fmt == 'latitude':
            if degree >= 0:
                sign = 'N'
            else:
                sign = 'S'
        else:
            if degree >= 0:
                sign = 'E'
            else:
                sign = 'W'

        text = sign + str(value).replace('.', '')
        return text

    def distance(speed, time, degree):
        dis = int(speed) * int(time) / 3600
        theta = math.radians(int(degree))
        dx = math.cos(theta) * dis
        dy = math.sin(theta) * dis

        return dx, dy

    radius = 6378
    latitude = formatToDegree(latitude)
    longitude = formatToDegree(longitude)
    dx, dy = distance(speed, time, degree)

    newLatitude = latitude + (dy / radius) * 180 / math.pi
    newLongitude = longitude + (dx / radius) * 180 / math.pi / math.cos(latitude * math.pi / 180)

    return formatToString(newLatitude), formatToString(newLongitude, fmt='longitude')




