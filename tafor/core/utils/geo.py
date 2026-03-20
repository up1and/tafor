import math


def degreeToDecimal(text):
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
    integer = int(abs(degree))
    decimal = int(abs(degree) % 1 * 60) / 100

    if fmt == 'latitude':
        identifier = 'N' if degree >= 0 else 'S'
        template = '{:05.2f}'
    else:
        identifier = 'E' if degree >= 0 else 'W'
        template = '{:06.2f}'

    value = template.format(integer + decimal)
    return identifier + str(value).replace('.', '')


def calcPosition(latitude, longitude, speed, time, degree):
    def distance(speed, time, degree):
        dis = int(speed) * int(time) / 3600
        theta = math.radians(int(degree))
        dy = math.cos(theta) * dis
        dx = math.sin(theta) * dis
        return dx, dy

    latitude = degreeToDecimal(latitude)
    longitude = degreeToDecimal(longitude)
    dx, dy = distance(speed, time, degree)

    radius = 6378
    dlong = math.pi * radius * math.cos(latitude * math.pi / 180) / 180
    dlat = math.pi * radius / 180

    newLatitude = latitude + dy / dlat
    newLongitude = longitude + dx / dlong

    if abs(newLatitude) > 90:
        newLatitude = 90 if newLatitude > 0 else -90

    if abs(newLongitude) > 180:
        newLongitude = abs(newLongitude) % 180 - 180

    return decimalToDegree(newLatitude), decimalToDegree(newLongitude, fmt='longitude')


def distanceBetweenPoints(point1, point2):
    x = point1[0] - point2[0]
    y = point1[1] - point2[1]
    return math.sqrt(x ** 2 + y ** 2)


def distanceBetweenLatLongPoints(point1, point2):
    deg2rad = lambda deg: deg * math.pi / 180

    long1, lat1 = point1
    long2, lat2 = point2

    radius = 6378
    dlat = deg2rad(lat2 - lat1)
    dlong = deg2rad(long2 - long1)

    a = math.sin(dlat / 2) * math.sin(dlat / 2) + math.cos(deg2rad(lat1)) * math.cos(deg2rad(lat2)) * math.sin(dlong / 2) * math.sin(dlong / 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius * c


def listToPoint(points):
    from PyQt5.QtCore import QPoint

    return [QPoint(p[0], p[1]) for p in points]


def pointToList(points):
    return [[p.x(), p.y()] for p in points]
