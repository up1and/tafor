import re
import json
import datetime
import textwrap

from tafor import conf


def linewrap(lines, maxLineChar):
    """对超过最大字符限制的行进行换行处理

    :return: 报文行列表
    """
    items = []
    for line in lines:
        if line:
            wraps = textwrap.wrap(line, width=maxLineChar)
            items += wraps
        else:
            items.append('')

    return items


class AFTNMessageGenerator(object):
    """航空固定电信网络（Aeronautical Fixed Telecommunication Network Message）报文的生成

    :param text: 报文内容
    :param channel: 信道
    :param priority: 电报优先级，默认 GG
    :param address: 收电地址
    :param originator: 发点地址
    :param maxLineChar: AFTN 线路每行最大字符数
    :param time: AFTN 报文生成时间

    使用方法::

        m = AFTNMessageGenerator('TAF ZJHK 150726Z 150918 03003G10MPS 1600 BR OVC040 BECMG 1112 4000 BR=')
        # 返回字符串格式 AFTN 报文
        m.toString()
        # 返回 JSON 格式 AFTN 报文
        m.toJson()

    """
    def __init__(self, text, channel='', priority='GG', address='', originator='', maxLineChar=69, time=None):
        self.texts = text.split('\n')
        self.channel = channel
        self.priority = priority
        self.address = address
        self.originator = originator
        self.maxLineChar = maxLineChar
        self.time = datetime.datetime.utcnow() if time is None else time
        sequenceLength = conf.value('Communication/ChannelSequenceLength')
        maxSendAddress = conf.value('Communication/MaxSendAddress')
        self.sequenceLength = int(sequenceLength) if sequenceLength else 3
        self.maxSendAddress = int(maxSendAddress) if maxSendAddress else 21  # AFTN 线路最大发电地址数
        self.lineBreak = '\r\n'
        self.generate()

    def toString(self):
        """生成字符串格式的报文

        :return: 字符串，多份报文用 4 个换行符连接
        """
        return '\r\n\r\n\r\n\r\n'.join(self.messages)

    def toJson(self):
        """生成 JSON 格式的报文

        :return: JSON
        """
        return json.dumps(self.messages)

    def generate(self):
        """生成 AFTN 电报格式的报文"""
        number = conf.value('Communication/ChannelSequenceNumber')
        number = int(number) if number else 1
        number = number % (10 * self.sequenceLength)

        groups = self.divideAddress(self.address)
        time = self.time.strftime('%d%H%M')

        origin = ' '.join([time, self.originator])
        ending = 'NNNN'

        self.messages = []
        for addr in groups:
            heading = ' '.join(['ZCZC', self.channel + str(number).zfill(self.sequenceLength)])
            address = ' '.join([self.priority] + addr)
            lines = [heading, address, origin] + self.texts + [''] * 3 + [ending]
            lines = linewrap(lines, self.maxLineChar)
            self.messages.append(self.lineBreak.join(lines))
            number += 1

        conf.setValue('Communication/ChannelSequenceNumber', str(number))

    def divideAddress(self, address):
        """根据最大发送地址拆分地址组，比如允许最大地址是 7，有 10 个地址就拆成 2 组

        :return: 迭代器，拆分后的地址
        """
        def chunks(lists, n):
            """Yield successive n-sized chunks from lists."""
            for i in range(0, len(lists), n):
                yield lists[i:i + n]

        items = address.split()
        return chunks(items, self.maxSendAddress)


class FileMessageGenerator(object):

    def __init__(self, text, maxLineChar=69, **kwargs):
        self.texts = text.split('\n')
        self.maxLineChar = maxLineChar
        self.sequenceLength = 3
        self.lineBreak = '\r\n'
        self.generate()

    def toString(self):
        return self.message

    def toJson(self):
        return self.message

    def generate(self):
        """生成文件类型的报文"""
        number = conf.value('Communication/FileSequenceNumber')
        number = int(number) if number else 1
        number = number % (10 * self.sequenceLength)
        ending = 'NNNN'
        heading = ' '.join(['ZCZC', str(number).zfill(self.sequenceLength)])
        lines = [heading] + self.texts + [''] * 3 + [ending]
        lines = linewrap(lines, self.maxLineChar)
        self.message = self.lineBreak.join(lines)

        conf.setValue('Communication/FileSequenceNumber', str(number + 1))


class AFTNDecoder(object):

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
        pattern = re.compile(r'^(?:GG|FF\s)?((?:\w{8}\s?)+)')
        for line in self.lines:
            m = pattern.match(line)
            if m:
                text = m.group(1)
                addressees += text.split()

        return ' '.join(addressees)
