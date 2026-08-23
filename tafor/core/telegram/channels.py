import datetime

from tafor.core.telegram.generator import (
    AFTNMessageGenerator, FileMessageGenerator, aftnPriority, fileMessageName
)


class BaseChannel:
    generator = None
    configName = None

    def __init__(self, conf, context=None):
        self.conf = conf
        self.context = context

    def buildText(self, message, reportType):
        if reportType == 'Custom':
            return self.context.other.message

        heading = self.conf.trendIdentifier if reportType == 'Trend' else message.heading
        spacer = ' ' if reportType == 'Trend' else '\n'
        return spacer.join([heading, message.text])

    def buildParams(self, message, reportType):
        raise NotImplementedError

    def generateRawText(self, message, reportType):
        generator = self.generator(**self.buildParams(message, reportType))
        return generator, generator.toString()


class AFTNChannel(BaseChannel):
    generator = AFTNMessageGenerator
    configName = 'channelSequenceNumber'

    def buildParams(self, message, reportType):
        if reportType == 'Custom':
            return {
                'text': self.context.other.message,
                'channel': self.conf.channel,
                'number': self.conf.get(self.configName),
                'priority': self.context.other.priority,
                'address': self.context.other.address,
                'originator': self.conf.originatorAddress,
                'sequenceLength': self.conf.channelSequenceLength,
                'maxSendAddress': self.conf.maxSendAddress,
            }

        priority = aftnPriority(reportType, message.text)
        address = self.conf.get(f'{reportType.lower()}Address')

        return {
            'text': self.buildText(message, reportType),
            'channel': self.conf.channel,
            'number': self.conf.get(self.configName),
            'priority': priority,
            'address': address,
            'originator': self.conf.originatorAddress,
            'sequenceLength': self.conf.channelSequenceLength or 4,
            'maxSendAddress': self.conf.maxSendAddress or 21,
        }


class FileChannel(BaseChannel):
    generator = FileMessageGenerator
    configName = 'fileSequenceNumber'

    def buildParams(self, message, reportType):
        return {
            'text': self.buildText(message, reportType),
            'number': self.conf.get(self.configName),
        }

    def ftpParams(self, valids=None):
        valids = valids or (datetime.datetime.utcnow(), datetime.datetime.utcnow())
        return {
            'url': self.conf.ftpHost,
            'filename': fileMessageName(self.conf.airport, valids, self.conf.get(self.configName)),
        }


def createChannel(protocol, conf, context=None):
    if protocol == 'ftp':
        return FileChannel(conf, context)
    return AFTNChannel(conf, context)


def canResend(message, now):
    return (
        not message.confirmed and
        now - message.created < datetime.timedelta(hours=2)
    )
