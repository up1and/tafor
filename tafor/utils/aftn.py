import json
import datetime

from tafor import conf


class AFTNMessage(object):
    """Aeronautical Fixed Telecommunication Network Message"""
    def __init__(self, text, reportType='TAF', time=None):
        super(AFTNMessage, self).__init__()
        self.text = text.split('\n')
        self.reportType = reportType
        self.time = datetime.datetime.utcnow() if time is None else time
        maxSendAddress = conf.value('Communication/MaxSendAddress')
        maxLineChar = conf.value('Communication/MaxLineChar')
        self.maxSendAddress = int(maxSendAddress) if maxSendAddress else 21  # AFTN 线路最大发电地址数
        self.maxLineChar = int(maxLineChar) if maxLineChar else 69  # AFTN 线路每行最大字符数
        self.lineBreak = '\n'

        self.generate()

    def toString(self):
        return '\n\n\n\n'.join(self.messages)

    def toJson(self):
        return json.dumps(self.messages)

    def generate(self):
        """生成 AFTN 电报格式的报文"""
        channel = conf.value('Communication/Channel')
        number = conf.value('Communication/ChannelSequenceNumber')
        number = int(number) if number else 0
        sendAddress = conf.value('Communication/{}Address'.format(self.reportType)) or ''
        originatorAddress = conf.value('Communication/OriginatorAddress') or ''

        groups = self.divideAddress(sendAddress)
        time = self.time.strftime('%d%H%M')

        origin = ' '.join([time, originatorAddress])
        ending = 'NNNN'

        self.messages = []
        for addr in groups:
            heading = ' '.join(['ZCZC', channel + str(number).zfill(4)])
            address = ' '.join(['GG'] + addr)
            items = [heading, address, origin] + self.text + [ending]
            items = self.formatLinefeed(items)
            self.messages.append(self.lineBreak.join(items))
            number += 1

        conf.setValue('Communication/ChannelSequenceNumber', str(number))
        
        return self.messages

    def formatLinefeed(self, messages):
        """对超过 maxLineChar 的行进行换行处理"""
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
        """根据 maxSendAddress 拆分地址，比如允许最大地址是 7，有 10 个地址就拆成 2 组"""
        def chunks(lists, n):
            """Yield successive n-sized chunks from lists."""
            for i in range(0, len(lists), n):
                yield lists[i:i + n]

        items = address.split()
        return chunks(items, self.maxSendAddress)