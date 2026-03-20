import calendar
import datetime

from dateutil import relativedelta


def isOverlap(basetime, reftime):
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
        'day': datetime.timedelta(days=1),
    }

    timedelta = deltas.get(delta, None)
    if timedelta and time < basetime:
        time += timedelta

    return time


def parseStandardPeriod(period, basetime=None):
    basetime = basetime if basetime else datetime.datetime.utcnow()
    startTime, endTime = period.split('/')

    if max([int(startTime[:2]), int(endTime[:2])]) > calendar.monthrange(basetime.year, basetime.month)[1]:
        basetime -= relativedelta.relativedelta(months=1)

    start = parseDayHour(startTime[:2], startTime[2:], basetime, delta='month')
    end = parseDayHour(endTime[:2], endTime[2:], basetime, delta='month')

    if end <= start:
        end += relativedelta.relativedelta(months=1)

    return start, end


def parseOldPeriod(interval, basetime=None):
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

    return None


def parseHourMinute(hour, minute, basetime=None):
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


def parseTime(value, basetime=None):
    if len(value) == 6:
        return parseDayHourMinute(value[:2], value[2:4], value[4:], basetime)

    if len(value) == 4:
        return parseHourMinute(value[:2], value[2:], basetime)

    return None


def parseTimez(timez):
    basetime = datetime.datetime.utcnow()
    day = int(timez[:2])
    hour = int(timez[2:4])
    minute = int(timez[4:6])

    if day > calendar.monthrange(basetime.year, basetime.month)[1]:
        basetime -= relativedelta.relativedelta(months=1)

    return datetime.datetime(basetime.year, basetime.month, day, hour, minute)


def ceilTime(value, amount=10):
    value = value - datetime.timedelta(
        minutes=value.minute % 5,
        seconds=value.second,
        microseconds=value.microsecond,
    )
    return value + datetime.timedelta(minutes=amount)


def roundTime(value):
    value = value.replace(minute=0, second=0, microsecond=0)
    return value + datetime.timedelta(hours=1)


def timeAgo(date, now=None):
    sec_array = [60.0, 60.0, 24.0, 7.0, 365.0 / 7.0 / 12.0, 12.0]

    if now is None:
        now = datetime.datetime.utcnow()

    diff = now - date
    seconds = diff.seconds

    agoIn = 0
    if seconds < 0:
        agoIn = 1
        seconds *= -1

    i = 0
    while i < len(sec_array):
        tmp = sec_array[i]
        if seconds >= tmp:
            i += 1
            seconds /= tmp
        else:
            break
    seconds = int(seconds)
    i *= 2

    if seconds > (9 if i == 0 else 1):
        i += 1

    locales = [
        ['just now', 'a while'],
        ['{} seconds ago', 'in {} seconds'],
        ['1 minute ago', 'in 1 minute'],
        ['{} minutes ago', 'in {} minutes'],
        ['1 hour ago', 'in 1 hour'],
        ['{} hours ago', 'in {} hours'],
        ['1 day ago', 'in 1 day'],
        ['{} days ago', 'in {} days'],
        ['1 week ago', 'in 1 week'],
        ['{} weeks ago', 'in {} weeks'],
        ['1 month ago', 'in 1 month'],
        ['{} months ago', 'in {} months'],
        ['1 year ago', 'in 1 year'],
        ['{} years ago', 'in {} years'],
    ]

    template = locales[i][agoIn]
    return template.format(seconds) if '{}' in template else template


class Layer(object):
    def __init__(self, layers=None):
        if layers is None:
            layers = {}

        self.image = layers.get('image', None)
        self.name = layers.get('name', 'Untititled')
        self.extent = layers.get('extent', [])
        self.proj = layers.get('proj', '')
        self.overlay = layers.get('overlay', 'standalone')
        self._updated = layers.get('updated', None)

    def __bool__(self):
        return self.image is not None

    def __repr__(self):
        return '<Layer {} ({}) {}>'.format(self.name, self.overlay, self._updated)

    def updatedTime(self):
        fmt = '%a, %d %b %Y %H:%M:%S GMT'
        try:
            return datetime.datetime.strptime(self._updated, fmt)
        except Exception:
            return None
