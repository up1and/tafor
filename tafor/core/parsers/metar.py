import re
import datetime

from tafor.core.utils.time import parseTime, parseTimez
from tafor.core.parsers.taf import MetarLexer, TafParser

class MetarParser(TafParser):

    lexerClass = MetarLexer

    splitPattern = re.compile(r'(BECMG|TEMPO)')

    def __init__(self, message, lexer=None, validator=None, trendOnly=False, previous=None, **kwargs):
        super().__init__(message, lexer=lexer, validator=validator, **kwargs)
        self.trendOnly = trendOnly
        self.previous = previous

    def _analyse(self):
        super()._analyse()
        if self.becmgs or self.tempos:
            self.trends = self.elements[1:]
            if 'NOSIG' in self.message:
                self.errors.append('NOSIG 不能与 BECMG 或 TEMPO 同时存在')
                if 'nosig' in self.primary.tokens:
                    self.primary.tokens['nosig']['error'] = True
        elif 'NOSIG' in self.message:
            metar = self.primary.part.replace('NOSIG', '').strip()
            self.primary = self.lexer(metar)
            self.trends = [self.lexer('NOSIG')]
            self.elements = [self.primary] + self.trends
        else:
            self.trends = self.elements[1:]

    def _parsePeriod(self):
        """Parse the time order of the primary report and trend groups."""
        time = parseTimez(self.primary.tokens['timez']['text'])
        self.primary.periods = (time, time + datetime.timedelta(hours=2))
        basetime = self.primary.periods[0]

        for e in self.elements[1:]:
            if 'fmtl' in e.tokens:
                periods = e.tokens['fmtl']['text'].split()
                if len(periods) == 2:
                    start = parseTime(periods[0][2:], basetime)
                    end = parseTime(periods[1][2:], basetime)
                    if start > end:
                        end += datetime.timedelta(days=1)
                    e.periods = (start, end)
                else:
                    text = periods[0]
                    if text.startswith('FM'):
                        e.periods = (parseTime(text[2:], basetime), self.primary.periods[1])
                    if text.startswith('TL'):
                        e.periods = (basetime, parseTime(text[2:], basetime))
                    if text.startswith('AT'):
                        time = parseTime(text[2:], basetime)
                        e.periods = (time, time)
            else:
                e.periods = self.primary.periods

    def _validateFormat(self):
        for e in self.elements[1:]:
            if 'fmtl' in e.tokens:
                text = e.tokens['fmtl']['text']
                periods = text.split()
                for period in periods:
                    conditions = [
                        period.startswith('AT') and not (self.primary.periods[0] < e.periods[0] < self.primary.periods[1]),
                        period.startswith('FM') and not (self.primary.periods[0] < e.periods[0] < self.primary.periods[1] and e.periods[0] < e.periods[1]),
                        period.startswith('TL') and not (self.primary.periods[0] < e.periods[1] < self.primary.periods[1] and e.periods[0] < e.periods[1])
                    ]

                    if any(conditions):
                        e.tokens['fmtl']['error'] = True
                        self.errors.append('趋势时间组错误')

    def _validateChange(self):
        """Validate element changes against the reference."""
        count = len(self.errors)
        self._validateElement(self.reference, self.primary.tokens)
        if self.trendOnly:
            # keep only the token flags from the primary validation; its
            # error messages are irrelevant when publishing trends
            del self.errors[count:]
        self._validateGroups()

    def hasTrend(self):
        return bool(self.trends)

    def isValid(self, trendOnly=None):
        if trendOnly is None:
            trendOnly = self.trendOnly

        if self.failed:
            return False

        if trendOnly and self.trends:
            elements = self.trends
        else:
            elements = self.elements

        return all(e.isValid() for e in elements)

    def isSameObservation(self, other):
        """Whether the primary report matches another message's, ignoring
        trend groups, whitespace and unrecognized tokens.

        :param other: the other message as raw text
        """
        other = MetarParser(other)
        return self.primary.renderer() == other.primary.renderer()

    def renderer(self, style='plain', previous=None):
        """Render the parsed message back into a string.

        :param style:
            * plain plain string style
            * terminal terminal highlight style
            * html HTML highlight style
        :param previous: the previous message; when given, words newly
            appearing in the primary report are marked in bold
        :return: the rendered message for the given style
        """
        previous = previous or self.previous
        outputs = [e.renderer(style) for e in self.elements if e]

        if style == 'html':
            separator = '<br/>' if self.hasTrend() else ' '

            if self.trendOnly:
                metar = self.primary.part
                if previous:
                    metar = self._highlightChanges(metar, previous)
                outputs[0] = '<span style="color: grey">{}</span>'.format(metar)

            return separator.join(outputs) + '='

        separator = '\n' if self.hasTrend() else ' '
        return separator.join(outputs) + '='

    def _highlightChanges(self, metar, previous):
        previous, *_ = self.splitPattern.split(previous)
        words = previous.split()
        elements = []
        for e in metar.split():
            if e not in words:
                e = '<strong>{}</strong>'.format(e)
            elements.append(e)

        return ' '.join(elements)
