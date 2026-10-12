import calendar
import datetime

from dateutil import relativedelta


def utcnow():
    """Return a naive datetime representing current UTC time.
    
    A drop-in replacement for the deprecated datetime.datetime.utcnow().
    """
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)


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
    basetime = basetime if basetime else utcnow()
    startTime, endTime = period.split('/')

    if max([int(startTime[:2]), int(endTime[:2])]) > calendar.monthrange(basetime.year, basetime.month)[1]:
        basetime -= relativedelta.relativedelta(months=1)

    start = parseDayHour(startTime[:2], startTime[2:], basetime, delta='month')
    end = parseDayHour(endTime[:2], endTime[2:], basetime, delta='month')

    if end <= start:
        end += relativedelta.relativedelta(months=1)

    return start, end


def parseOldPeriod(interval, basetime=None):
    basetime = basetime if basetime else utcnow()

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
    basetime = basetime if basetime else utcnow()
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
    basetime = basetime if basetime else utcnow()
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


def parseTimez(timez, basetime=None):
    basetime = basetime if basetime else utcnow()
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
    """Describe how long ago ``date`` happened, relative to ``now``.

    Returns phrases like 'just now', '5 minutes ago' or 'in 2 days' when
    the date lies in the future.
    """
    # Divisor applied at each step of the walk: seconds -> minutes ->
    # hours -> days -> weeks -> months -> years.
    unitDivisors = [60.0, 60.0, 24.0, 7.0, 365.0 / 7.0 / 12.0, 12.0]

    if now is None:
        now = utcnow()

    # utcnow() is naive, so an aware date would raise on subtraction.
    # Normalise the odd one out rather than letting the caller crash.
    if date.tzinfo is not None and now.tzinfo is None:
        date = date.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    elif date.tzinfo is None and now.tzinfo is not None:
        now = now.astimezone(datetime.timezone.utc).replace(tzinfo=None)

    # total_seconds, not .seconds: the latter drops the days component, so
    # anything three or more days old looked like it happened just now.
    seconds = (now - date).total_seconds()

    suffix = 0
    if seconds < 0:
        suffix = 1
        seconds *= -1

    index = 0
    while index < len(unitDivisors):
        divisor = unitDivisors[index]
        if seconds >= divisor:
            seconds /= divisor
            index += 1
        else:
            break

    seconds = int(seconds)

    # Units below 10 stay in the current bucket: '9 seconds ago' rather than
    # '9 seconds' rounding up into minutes. Every coarser unit reads as a
    # singular once it is the current one.
    threshold = 9 if index == 0 else 1
    row = index * 2 + (1 if seconds > threshold else 0)

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

    template = locales[row][suffix]
    return template.format(seconds) if '{}' in template else template
