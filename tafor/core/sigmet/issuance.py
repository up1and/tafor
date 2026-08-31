import datetime
import re

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
