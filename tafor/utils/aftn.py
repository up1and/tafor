import re
import json
import datetime
import textwrap

from tafor import conf


class AFTNMessage(object):
    """航空固定电信网络（Aeronautical Fixed Telecommunication Network Message）报文的生成

    :param text: 报文内容
    :param reportType: 报文类型，默认 TAF
    :param time: AFTN 报文生成时间

    使用方法::

        m = AFTNMessage('TAF ZJHK 150726Z 150918 03003G10MPS 1600 BR OVC040 BECMG 1112 4000 BR=')
        # 返回字符串格式 AFTN 报文
        m.toString()
        # 返回 JSON 格式 AFTN 报文
        m.toJson()

    """
    def __init__(self, text, reportType='TAF', time=None):
        self.texts = text.split('\n')
        self.reportType = reportType
        self.time = datetime.datetime.utcnow() if time is None else time
        maxSendAddress = conf.value('Communication/MaxSendAddress')
        maxLineChar = conf.value('Communication/MaxLineChar')
        self.maxSendAddress = int(maxSendAddress) if maxSendAddress else 21  # AFTN 线路最大发电地址数
        self.maxLineChar = int(maxLineChar) if maxLineChar else 69  # AFTN 线路每行最大字符数
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
        """生成 AFTN 电报格式的报文

        :return: 报文列表
        """
        channel = conf.value('Communication/Channel')
        number = conf.value('Communication/ChannelSequenceNumber')
        number = int(number) if number else 0
        level = 'FF' if self.reportType in ['SIGMET', 'AIRMET'] else 'GG'
        sendAddress = conf.value('Communication/{}Address'.format(self.reportType)) or ''
        originatorAddress = conf.value('Communication/OriginatorAddress') or ''

        groups = self.divideAddress(sendAddress)
        time = self.time.strftime('%d%H%M')

        origin = ' '.join([time, originatorAddress])
        ending = 'NNNN'

        self.messages = []
        for addr in groups:
            heading = ' '.join(['ZCZC', channel + str(number).zfill(4)])
            address = ' '.join([level] + addr)
            lines = [heading, address, origin] + self.texts + [''] * 3 + [ending]
            lines = self.linewrap(lines)
            self.messages.append(self.lineBreak.join(lines))
            number += 1

        conf.setValue('Communication/ChannelSequenceNumber', str(number))

        return self.messages

    def linewrap(self, lines):
        """对超过最大字符限制的行进行换行处理

        :return: 报文行列表
        """
        items = []
        for line in lines:
            if line:
                wraps = textwrap.wrap(line, width=self.maxLineChar)
                items += wraps
            else:
                items.append('')

        return items

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
