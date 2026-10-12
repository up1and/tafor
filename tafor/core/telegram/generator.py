import re
import json
import textwrap

from tafor.core.utils.time import utcnow


def linewrap(lines, maxLineChar):
    """Wrap every line that runs past the character limit.

    Blank lines are kept as they are, so the message keeps its shape.

    :return: the message as a list of lines
    """
    items = []
    for line in lines:
        if line:
            wraps = textwrap.wrap(line, width=maxLineChar)
            items += wraps
        else:
            items.append('')

    return items


def aftnPriority(category, text):
    """SIGMET/AIRMET and amended TAF go out with the higher FF priority."""
    if category in ['SIGMET', 'AIRMET'] or text.startswith('TAF AMD'):
        return 'FF'
    return 'GG'


def fileMessageName(airport, valids, number, created=None):
    format = '%Y%m%d%H%M%S'
    created = created or utcnow()
    return '9_OTHE_C_{airport}_{created}_STUB-WTMG-MULT-{validfrom}-{validto}-XXX-1,{number}.txt'.format(
        airport=airport,
        created=created.strftime(format),
        validfrom=valids[0].strftime(format),
        validto=valids[1].strftime(format),
        number=str(number).zfill(5)
    )


class AFTNMessageGenerator:
    """Builds messages for the Aeronautical Fixed Telecommunication Network.

    :param text: message content
    :param channel: channel
    :param priority: telegram priority, GG by default
    :param address: addressee addresses
    :param originator: originator address
    :param maxLineChar: maximum characters per line on an AFTN circuit
    :param time: the time the AFTN message is generated

    Usage::

        m = AFTNMessageGenerator('TAF ZJHK 150726Z 150918 03003G10MPS 1600 BR OVC040 BECMG 1112 4000 BR=')
        # the message as a string
        m.toString()
        # the message as JSON
        m.toJson()

    """
    def __init__(self, text, channel='', number=1, priority='GG', address='', 
            originator='', maxLineChar=69, sequenceLength=4, maxSendAddress=21, time=None):
        self.texts = text.split('\n')
        self.channel = channel
        self.number = int(number)
        self.priority = priority
        self.address = address
        self.originator = originator
        self.maxLineChar = maxLineChar
        self.sequenceLength = int(sequenceLength)
        self.maxSendAddress = int(maxSendAddress)  # most addressees per AFTN circuit
        self.time = utcnow() if time is None else time
        self.lineBreak = '\r\n'
        self.generate()

    def toString(self):
        """The message as a string.

        :return: the messages joined by four line breaks
        """
        return '\r\n\r\n\r\n\r\n'.join(self.messages)

    def toJson(self):
        """The message as JSON.

        :return: JSON
        """
        return json.dumps(self.messages)

    def generate(self):
        """Lay out the messages in AFTN telegram form."""
        self.number = self.number % (10 ** self.sequenceLength)

        groups = self.divideAddress(self.address)
        time = self.time.strftime('%d%H%M')

        origin = ' '.join([time, self.originator])
        ending = 'NNNN'

        self.messages = []
        for addr in groups:
            heading = ' '.join(['ZCZC', self.channel + str(self.number).zfill(self.sequenceLength)])
            address = ' '.join([self.priority] + addr)
            lines = [heading, address, origin] + self.texts + [''] * 3 + [ending]
            lines = linewrap(lines, self.maxLineChar)
            self.messages.append(self.lineBreak.join(lines))
            self.number += 1

    def divideAddress(self, address):
        """Split the addresses into groups of maxSendAddress.

        With a limit of 7 and 10 addresses given, for example, that is two
        groups.

        :return: an iterator over the address groups
        """
        def chunks(lists, n):
            """Yield successive n-sized chunks from lists."""
            for i in range(0, len(lists), n):
                yield lists[i:i + n]

        items = address.split()
        return chunks(items, self.maxSendAddress)


class FileMessageGenerator:

    def __init__(self, text, number=1, maxLineChar=69, **kwargs):
        self.texts = text.split('\n')
        self.number = int(number)
        self.maxLineChar = maxLineChar
        self.sequenceLength = 3
        self.lineBreak = '\r\n'
        self.generate()

    def toString(self):
        return self.message

    def toJson(self):
        return self.message

    def generate(self):
        """Lay out the message in file form."""
        self.number = self.number % (10 ** self.sequenceLength)
        ending = 'NNNN'
        heading = ' '.join(['ZCZC', str(self.number).zfill(self.sequenceLength)])
        lines = [heading] + self.texts + [''] * 3 + [ending]
        lines = linewrap(lines, self.maxLineChar)
        self.message = self.lineBreak.join(lines)
        self.number += 1


class AFTNDecoder:

    def __init__(self, raw):
        if isinstance(raw, str):
            self.messages = json.loads(raw)
        else:
            self.messages = raw

        text = '\n'.join(self.messages)
        self.lines = [line.strip() for line in text.split('\n')]

    @property
    def priority(self):
        pattern = re.compile(r'^(GG|FF)\s')
        for line in self.lines:
            m = pattern.match(line)
            if m:
                return m.group(1)

    @property
    def originator(self):
        pattern = re.compile(r'^\d{6}\s(\w{8})')
        for line in self.lines:
            m = pattern.match(line)
            if m:
                return m.group(1)

    @property
    def address(self):
        addressees = []
        pattern = re.compile(r'^(?:GG\s|FF\s)?((?:\w{8}\s?)+)')
        for line in self.lines:
            m = pattern.match(line)
            if m and m.group() == line:
                text = m.group(1)
                addressees += text.split()

        return ' '.join(addressees)
