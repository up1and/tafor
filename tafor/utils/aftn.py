import json
import datetime

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
        ending = '\n\n\n' + 'NNNN'

        self.messages = []
        for addr in groups:
            heading = ' '.join(['ZCZC', channel + str(number).zfill(4)])
            address = ' '.join([level] + addr)
            items = [heading, address, origin] + self.texts + [ending]
            items = self.formatLinefeed(items)
            self.messages.append(self.lineBreak.join(items))
            number += 1

        conf.setValue('Communication/ChannelSequenceNumber', str(number))
        
        return self.messages

    def formatLinefeed(self, messages):
        """对超过最大字符限制的行进行换行处理
        
        :return: 报文行列表
        """
        def findSubscript(parts):
            subscripts = []
            num = 0
            for i, part in enumerate(parts):
                num += len(part) + 1
                if num > self.maxLineChar:
                    subscripts.append(i)
                    num = len(part) + 1

            subscripts.append(len(parts))

            return subscripts

        items = []
        for message in messages:
            if len(message) > self.maxLineChar:
                parts = message.split()
                subscripts = findSubscript(parts)
                sup = 0
                for sub in subscripts:
                    part = ' '.join(parts[sup:sub])
                    sup = sub
                    items.append(part)
            else:
                items.append(message)

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