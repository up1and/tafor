import datetime

from tafor.core.telegram.generator import (
    AFTNMessageGenerator, FileMessageGenerator, aftnPriority, fileMessageName
)


class BaseChannel:
    generator = None
    configName = None

    def __init__(self, conf):
        self.conf = conf

    def buildText(self, message, category):
        heading = self.conf.trendIdentifier if category == 'trend' else message.heading
        spacer = ' ' if category == 'trend' else '\n'
        return spacer.join([heading, message.text])

    def buildParams(self, message, priority=None, address=None):
        raise NotImplementedError

    def generate(self, message, *, priority=None, address=None):
        """Build the telegram generator for a report message.

        message is a Taf/Trend/Sigmet/Other instance; its reportType
        property selects the telegram category. Standard reports derive
        priority and address from the config, custom messages (Other)
        require both explicitly.
        """
        return self.generator(**self.buildParams(message, priority, address))


class AFTNChannel(BaseChannel):
    generator = AFTNMessageGenerator
    configName = 'channelSequenceNumber'

    def buildParams(self, message, priority=None, address=None):
        category = message.reportType

        if category == 'custom':
            # Custom addressing is user-provided, not derived from config
            text = message.text
        else:
            text = self.buildText(message, category)
            priority = aftnPriority(category, message.text)
            address = self.conf.get(f'{category}Address')

        return {
            'text': text,
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

    def buildParams(self, message, priority=None, address=None):
        return {
            'text': self.buildText(message, message.reportType),
            'number': self.conf.get(self.configName),
        }

    def ftpParams(self, valids=None):
        valids = valids or (datetime.datetime.utcnow(), datetime.datetime.utcnow())
        return {
            'url': self.conf.ftpHost,
            'filename': fileMessageName(self.conf.airport, valids, self.conf.get(self.configName)),
        }


def createChannel(protocol, conf):
    if protocol == 'ftp':
        return FileChannel(conf)
    return AFTNChannel(conf)


def canResend(message, now):
    return (
        not message.confirmed and
        now - message.created < datetime.timedelta(hours=2)
    )
