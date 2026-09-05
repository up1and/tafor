import datetime
import re

from tafor.core.geometry.algorithm import depth, encode
from tafor.core.geometry.coordinate import decimalToDegree
from tafor.core.geometry.sketch import (
    CircleSketch, CorridorSketch, EntireSketch, LineSketch, PolygonSketch,
    RectangularSketch,
)
from tafor.core.utils.time import ceilTime, parseTime, roundTime


def composeHeading(designator, area, icao, now):
    time = now.strftime('%d%H%M')
    messages = [designator + area, icao, time]
    return ' '.join(filter(None, messages))


def validDuration(designator):
    durations = {
        'WS': 4,
        'WC': 6,
        'WV': 6,
        'WA': 4,
    }
    return durations[designator]


def nextSequence(headings, today):
    """Number SIGMETs issued today, ignoring entries from yesterday."""
    def isYesterday(text):
        if text:
            m = re.compile(r'\d{6}').search(text)
            if m:
                issueTime = m.group()
                return int(issueTime[:2]) != today.day or issueTime[2:] == '0000'

        return False

    return len([h for h in headings if not isYesterday(h)]) + 1


def validPeriod(designator, span, now):
    """Valid period start: next full hour for WC, otherwise ceil to 10 minutes."""
    if designator == 'WC':
        start = roundTime(now)
    else:
        start = ceilTime(now, amount=10)

    end = start + datetime.timedelta(hours=span)
    return start, end


def adjustCancelBeginning(beginningText, periodStart, endingText, now):
    """Resolve the cancel report beginning time: keep the period start unless
    the selected time is later and within 12 hours, then back off 10 minutes
    when it collides with the ending time."""
    beginning = periodStart
    selected = parseTime(beginningText, now)

    if beginning < selected and selected - now < datetime.timedelta(hours=12):
        beginning = selected

    if beginning.strftime('%d%H%M') == endingText:
        beginning = beginning - datetime.timedelta(minutes=10)

    return beginning


def formatCoordinate(lon, lat):
    """Format a point as DMS text, latitude first: ``N2000 E11000``."""
    return '{} {}'.format(decimalToDegree(lat), decimalToDegree(lon, fmt='longitude'))


def inProgressText(coordinates):
    """List the drawn points while the area is not finished yet."""
    return ' - '.join(formatCoordinate(lon, lat) for lon, lat in coordinates)


def polygonText(sketch, boundaries):
    coords = inProgressText(sketch.coordinates)
    if sketch.done:
        return 'WI ' + coords
    return coords


def lineText(sketch, boundaries):
    if not sketch.done:
        return inProgressText(sketch.coordinates)

    area = encode(boundaries, sketch.coordinates, mode='line')
    lines = []
    for identifier, *pts in area:
        coords = [formatCoordinate(lon, lat) for lon, lat in pts]
        lines.append('{} OF LINE {}'.format(identifier, ' - '.join(coords)))
    return ' AND '.join(lines)


def circleText(sketch, boundaries):
    if not sketch.done:
        return inProgressText(sketch.coordinates)

    lon, lat = sketch.coordinates[0]
    msg = 'PSN {}'.format(formatCoordinate(lon, lat))
    if sketch.withRadius:
        msg += ' / WI {}KM OF CENTRE'.format(round(sketch.radius / 1000))
    return msg


def corridorText(sketch, boundaries):
    coords = inProgressText(sketch.coordinates)
    if not sketch.done:
        return coords
    return 'APRX {}KM WID LINE BTN {}'.format(round(sketch.radius * 2 / 1000), coords)


def rectangularText(sketch, boundaries):
    if depth(sketch.coordinates) <= 1 and len(sketch.coordinates) <= 2:
        return ''

    area = encode(boundaries, sketch.coordinates, mode='rectangular')
    lines = []
    for identifier, *pts in area:
        # the encode sides are boundary-parallel lines: a N/S line
        # shares one latitude, an E/W line shares one longitude
        lon, lat = pts[0]
        coordinate = (decimalToDegree(lat) if identifier in ('N', 'S')
                      else decimalToDegree(lon, fmt='longitude'))
        lines.append('{} OF {}'.format(identifier, coordinate))
    return ' AND '.join(lines)


def entireText(sketch, boundaries):
    return 'ENTIRE FIR' if sketch.done else ''


def formatLocation(sketch, boundaries):
    formatters = {
        PolygonSketch: polygonText,
        LineSketch: lineText,
        CircleSketch: circleText,
        CorridorSketch: corridorText,
        RectangularSketch: rectangularText,
        EntireSketch: entireText,
    }
    return formatters[type(sketch)](sketch, boundaries)
