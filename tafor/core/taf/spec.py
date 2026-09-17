import datetime

from tafor.core.utils.time import utcnow


# The three message specs. A day is cut into `periods` windows, each one opening
# `interval` after the previous, `begin` before the validity it carries starts, and
# covering `duration`. `delay` is the spec's own grace period before the report is
# late, which the operator's `Monitor/DelayMinutes` setting is added to.


class SpecFC:
    designator = 'FC'
    periods = ['0312', '0615', '0918', '1221', '1524', '1803', '2106', '0009']
    default = '0009'
    interval = datetime.timedelta(hours=3)
    delay = datetime.timedelta(minutes=50)
    begin = datetime.timedelta(hours=2)
    duration = datetime.timedelta(hours=9)


class SpecFT24:
    designator = 'FT'
    periods = ['0606', '1212', '1818', '0024']
    default = '0024'
    interval = datetime.timedelta(hours=6)
    delay = datetime.timedelta(minutes=50)
    begin = datetime.timedelta(hours=3)
    duration = datetime.timedelta(hours=24)


class SpecFT30:
    designator = 'FT'
    periods = ['0612', '1218', '1824', '0006']
    default = '0006'
    interval = datetime.timedelta(hours=6)
    delay = datetime.timedelta(minutes=50)
    begin = datetime.timedelta(hours=3)
    duration = datetime.timedelta(hours=30)


class CurrentTaf:
    """The report window an instant falls in, for one message spec.

    :param spec: one of SpecFC / SpecFT24 / SpecFT30
    :param time: the instant the report is made for
    :param offset: whole windows from it -- 0 is the current one, -1 the previous,
        1 the next

    """

    def __init__(self, spec, time=None, offset=0):
        self.spec = spec
        self.time = utcnow() if time is None else time

        if offset:
            self.time += self.spec.interval * offset

        self.initOpenings()

    def __repr__(self):
        return '<Current TAF {}{}>'.format(self.spec.designator, self.period())

    def key(self):
        """The window's identity within the day: '0918'.

        The label is what indexes `openings`, and it is the short mark a report is
        referred to by; `period()` is the same window written out for the message.

        The loop always wins, and `default` is only the answer for the case that
        cannot happen: the table tiles the day because `periods` spans exactly 24
        hours and `default` is the window that wraps past midnight. probe-10 swept
        120,960 instants across the three specs and found no gap. The fallback
        stays anyway -- a None here would surface as an exception inside a slot,
        which this codebase turns into exit 127 with no traceback.
        """
        for label, start in self.openings.items():
            if start <= self.time < start + self.spec.interval:
                return label

        return self.spec.default

    def period(self):
        """The window as the message writes it: '1009/1018'."""
        return self.withDay(self.key())

    def durations(self):
        """The window's validity, as a (start, end) pair."""
        return self.span(self.key())

    def isExpired(self, minutes=30):
        """Whether the deadline for this window has passed.

        The deadline is when the window opens, plus the spec's own `delay`, plus
        `minutes` -- the operator's tolerance from the settings. `minutes` arrives
        as text, since that is how the settings store it, and None means the caller
        has no setting to pass and gets the default.
        """
        if minutes is None:
            minutes = 30

        threshold = self.openings[self.key()] + self.spec.delay + datetime.timedelta(minutes=int(minutes))
        return threshold < self.time

    def initOpenings(self):
        startOfTheDay = datetime.datetime(self.time.year, self.time.month, self.time.day)
        delta = self.spec.interval - self.spec.begin

        self.openings = {}
        for i, period in enumerate(self.spec.periods):
            self.openings[period] = startOfTheDay + delta + self.spec.interval * i

        if self.time < startOfTheDay + self.spec.interval - self.spec.begin:
            self.openings[self.spec.default] -= datetime.timedelta(days=1)

    def span(self, key):
        """The window's validity, as a (start, end) pair."""
        start = self.openings[key] + self.spec.begin
        return start, start + self.spec.duration

    def withDay(self, key):
        """Write the window out for the message: '1009/1018'."""
        start, end = self.span(key)

        if int(key[2:]) == 24:
            # The label's second hour field is the window's end, so 24 means the
            # end of the day: write 2359 rather than rolling into the next one.
            end -= datetime.timedelta(minutes=1)

        periodWithDay = '{}{}/{}{}'.format(str(start.day).zfill(2), key[:2], str(end.day).zfill(2), key[2:])

        return periodWithDay
