import datetime

from tafor.core.utils.time import parseDayHour


def composeHeading(spec, area, icao, date, sequence):
    tt = spec[:2].upper() if spec else "FC"
    messages = [tt + area, icao, date, sequence]
    return " ".join(filter(None, messages))


def segmentOrderKey(identifier, start):
    """Ordering key for composing the message preview: the primary segment
    comes first, then change groups chronologically by start time; on ties
    FM sorts before BECMG before TEMPO."""
    orders = ['FM', 'BECMG', 'TEMPO']
    if identifier == 'PRIMARY':
        return (0, 0, 0)

    priority = orders.index(identifier) if identifier in orders else 99
    return (1, start, priority)


def groupSpan(indicator, spec):
    """Maximum change-group span used for validation: a TEMPO group lasts
    6 hours in an FT message and 4 hours in FC, everything else 2 hours."""
    if indicator.startswith('TEMPO'):
        return 6 if 'ft' in spec else 4
    return 2


def formatValidityEnd(end):
    """Message notation for a validity end time: midnight becomes the
    previous day followed by '24', e.g. Aug 11 00:00 -> '1024'."""
    if end.hour == 0:
        previous = end - datetime.timedelta(minutes=1)
        return '{:02d}24'.format(previous.day)
    return '{:02d}{:02d}'.format(end.day, end.hour)


def isGroupStartAcceptable(text, durations):
    """Whether a freshly typed four-digit DDHH parses to a group start
    that still falls inside the message validity period."""
    baseStart, baseEnd = durations

    if len(text) != 4:
        return False

    try:
        start = parseDayHour(text[:2], text[2:], baseStart, delta='month')
    except Exception:
        return False

    return baseEnd > start


def completeGroupPeriod(text, durations, indicator, spec):
    """Complete a change-group period from a freshly typed four-digit DDHH
    without crossing the message validity period.

    durations is the base validity period as a (start, end) tuple of
    datetimes. Returns the completed text, or None when completion must not
    happen (the start falls out of range, or a BECMG end would overflow).
    """
    baseStart, baseEnd = durations

    if not isGroupStartAcceptable(text, durations):
        return None

    start = parseDayHour(text[:2], text[2:], baseStart, delta='month')

    if indicator.startswith('TEMPO'):
        end = start + datetime.timedelta(hours=groupSpan(indicator, spec))
        if baseEnd <= end:
            # Clamp to the validity end, normalised to /DD24 at midnight
            return '{:02d}{:02d}/{}'.format(start.day, start.hour, formatValidityEnd(baseEnd))
        return '{:02d}{:02d}/{:02d}{:02d}'.format(start.day, start.hour, end.day, end.hour)

    if indicator.startswith('BECMG'):
        end = start + datetime.timedelta(hours=1)
        if baseEnd <= end:
            return None
        return '{:02d}{:02d}/{:02d}{:02d}'.format(start.day, start.hour, end.day, end.hour)

    return None
