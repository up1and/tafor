import math


def degreeToDecimal(text):
    """Convert a DMS string like 'N2748' or 'E03909' to decimal degrees."""
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
    """Convert decimal degrees to a DMS string like 'N2748' or 'E03909'."""
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
    """Calculate a new lat/lon position given speed, time, and direction.

    Returns a tuple of DMS-formatted strings: (latitude, longitude).
    """
    def _distance(speed, time, degree):
        dis = int(speed) * int(time) / 3600
        theta = math.radians(int(degree))
        dy = math.cos(theta) * dis
        dx = math.sin(theta) * dis
        return dx, dy

    latitude = degreeToDecimal(latitude)
    longitude = degreeToDecimal(longitude)
    dx, dy = _distance(speed, time, degree)

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


def degTodms(deg, pretty=None):
    """Convert from decimal degrees to degrees, minutes, seconds.

    If ``pretty`` is 'lat' or 'lon', return a formatted string with hemisphere
    indicator (e.g. 'N27°48′09″'). Otherwise return a (d, m, s) tuple.
    """
    m, s = divmod(abs(deg) * 3600, 60)
    d, m = divmod(m, 60)
    if deg < 0:
        d = -d
    d, m, s = int(d), int(m), int(s)

    if pretty:
        if pretty == 'lat':
            hemi = 'N' if d >= 0 else 'S'
        elif pretty == 'lon':
            hemi = 'E' if d >= 0 else 'W'
        else:
            hemi = '?'
        return '{hemi:1s}{d:02d}°{m:02d}′{s:02d}″'.format(
            d=abs(d), m=m, s=s, hemi=hemi)
    return d, m, s
