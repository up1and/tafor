import re
import logging
import datetime

from tafor.core.utils.time import parseTime, parseTimez

logger = logging.getLogger('tafor.parser.metar')

from tafor.core.parsers.taf import MetarLexer, TafParser


class MetarParser(TafParser):

    lexerClass = MetarLexer

    splitPattern = re.compile(r'(BECMG|TEMPO)')

    def __init__(self, message, parse=None, validator=None, ignoreMetar=False, **kwargs):
        super().__init__(message, parse=parse, validator=validator, **kwargs)
        self.ignoreMetar = ignoreMetar
        self.previous = kwargs.get('previous')
        if len(self.elements) > 1 and self.primary:
            self.metar = MetarParser(self.primary.part, parse=parse, validator=validator, ignoreMetar=False, **kwargs)
            self.metar.validate()
        else:
            self.metar = self

    def _analyse(self):
        super()._analyse()
        if 'NOSIG' in self.message:
            metar = self.primary.part.replace('NOSIG', '').strip()
            self.primary = self.parse(metar)
            self.trends = [self.parse('NOSIG')]
            self.elements = [self.primary] + self.trends
        else:
            self.trends = self.elements[1:]

    def _parsePeriod(self):
        """解析主报文和变化组的时间顺序"""
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
                        e.periods = (parseTime(text[2:], basetime), self.primary.period[1])
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
                        'AT' in period and not (self.primary.periods[0] < e.periods[0] < self.primary.periods[1]),
                        'FM' in period and not (self.primary.periods[0] < e.periods[0] < self.primary.periods[1] and e.periods[0] < e.periods[1]),
                        'TL' in period and not (self.primary.periods[0] < e.periods[1] < self.primary.periods[1] and e.periods[0] < e.periods[1])
                    ]
                    
                    if any(conditions):
                        e.tokens['fmtl']['error'] = True
                        self.errors.append('趋势时间组错误')

    def hasMessageChanged(self):
        """校验后的报文和原始报文相比是否有变化"""
        origin = ' '.join(self.message.split())
        outputs = [e.renderer('plain') for e in self.elements if e and e != self.primary]
        if outputs:
            output = ' '.join(outputs) + '='
            return not origin.endswith(output)
        return False

    def hasTrend(self):
        return self.becmgs or self.tempos

    def hasMetar(self):
        return self.metar is not self

    def isValid(self, ignoreMetar=None):
        if ignoreMetar is None:
            ignoreMetar = self.ignoreMetar

        if ignoreMetar or not self.hasMetar():
            elements = self.elements[1:]
        else:
            elements = self.elements

        if self.failed:
            return False

        valids = [e.isValid() for e in elements]
        return all(valids)

    def isSimilar(self, other):
        other = MetarParser(other)
        return self.primary.renderer() == other.primary.renderer()

    @property
    def tips(self):
        if self.ignoreMetar and not self.metar.isValid(ignoreMetar=False):
            tips = list(set(self.errors) - set(self.metar.errors))
        else:
            tips = self.errors
        return tips

    def renderer(self, style='plain', showDiff=False, emphasizeNosig=False):
        """将解析后的报文重新渲染

        :param style:
            * plain 纯字符串风格
            * terminal 终端高亮风格
            * html HTML 高亮风格
        :return: 根据不同风格重新渲染的报文
        """
        outputs = [e.renderer(style) for e in self.elements if e]
        separator = ' '

        if style == 'html':
            if self.hasTrend() or emphasizeNosig:
                separator = '<br/>'

            metar = self.primary.part
            if self.ignoreMetar:
                if showDiff and self.previous:
                    metar = self._diff(metar, self.previous)

                outputs[0] = metar

                if self.hasTrend() or emphasizeNosig:
                    outputs[0] = '<span style="color: grey">{}</span>'.format(metar)
                else:
                    return '<span style="color: grey">{}</span>'.format(separator.join(outputs) + '=')

            return separator.join(outputs) + '='

        if self.hasTrend():
            separator = '\n'

        return separator.join(outputs) + '='

    def _diff(self, metar, previous):
        previous, *_ = self.splitPattern.split(previous)
        parts = metar.split()
        elements = []
        for e in parts:
            if e not in previous.split():
                e = '<strong>{}</strong>'.format(e)
            elements.append(e)

        return ' '.join(elements)
