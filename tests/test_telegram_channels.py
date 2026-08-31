import datetime
import re

from tafor.core.models import Other
from tafor.core.telegram.channels import AFTNChannel, FileChannel, canResend, createChannel


class FakeConf:

    def __init__(self, values):
        self.values = values

    def __getattr__(self, name):
        try:
            return self.values[name]
        except KeyError:
            raise AttributeError(name)

    def get(self, name):
        return self.values[name]


class FakeMessage:

    def __init__(self, heading='NT36 YUSO 231200', text='TAF YUSO 231200Z 2312/2412 03003MPS=',
                 confirmed=False, created=None, category='TAF'):
        self.heading = heading
        self.text = text
        self.confirmed = confirmed
        self.created = created or datetime.datetime.utcnow()
        self.category = category


def makeConf():
    return FakeConf({
        'channel': 'YMC',
        'channelSequenceNumber': '3',
        'channelSequenceLength': '4',
        'maxSendAddress': '21',
        'originatorAddress': 'YUSOYMYX',
        'tafAddress': 'YUSO3001',
        'trendAddress': 'YUSO3010',
        'sigmetAddress': 'YUSOSIGM',
        'airmetAddress': 'YUSOAIRM',
        'trendIdentifier': 'TRENDING',
        'ftpHost': 'ftp://example.com/upload',
        'airport': 'YUSO',
        'fileSequenceNumber': '9',
    })


def test_create_channel_by_protocol():
    conf = makeConf()

    assert isinstance(createChannel('aftn', conf), AFTNChannel)
    assert isinstance(createChannel('ftp', conf), FileChannel)
    assert isinstance(createChannel('serial', conf), AFTNChannel)


def test_aftn_build_params_for_taf():
    channel = AFTNChannel(makeConf())
    params = channel.buildParams(FakeMessage())

    assert params['text'] == 'NT36 YUSO 231200\nTAF YUSO 231200Z 2312/2412 03003MPS='
    assert params['channel'] == 'YMC'
    assert params['number'] == '3'
    assert params['priority'] == 'GG'
    assert params['address'] == 'YUSO3001'
    assert params['originator'] == 'YUSOYMYX'
    assert params['sequenceLength'] == '4'
    assert params['maxSendAddress'] == '21'


def test_aftn_priority_ff_for_sigmet_and_amended_taf():
    channel = AFTNChannel(makeConf())

    assert channel.buildParams(FakeMessage(category='SIGMET'))['priority'] == 'FF'
    assert channel.buildParams(FakeMessage(text='TAF AMD YUSO ...'))['priority'] == 'FF'


def test_aftn_defaults_when_blank():
    conf = makeConf()
    conf.values['channelSequenceLength'] = ''
    conf.values['maxSendAddress'] = ''
    channel = AFTNChannel(conf)

    params = channel.buildParams(FakeMessage())

    assert params['sequenceLength'] == 4
    assert params['maxSendAddress'] == 21


def test_aftn_build_params_for_trend():
    channel = AFTNChannel(makeConf())
    message = FakeMessage(heading='ignored', text='NOSIG=', category='TREND')

    params = channel.buildParams(message)

    assert params['address'] == 'YUSO3010'
    assert params['text'] == 'TRENDING NOSIG='


def test_aftn_build_params_for_custom():
    channel = AFTNChannel(makeConf())
    message = Other(text='SOME TEXT')

    params = channel.buildParams(message, priority='FF', address='YUSO YUSI')

    assert params == {
        'text': 'SOME TEXT',
        'channel': 'YMC',
        'number': '3',
        'priority': 'FF',
        'address': 'YUSO YUSI',
        'originator': 'YUSOYMYX',
        'sequenceLength': '4',
        'maxSendAddress': '21',
    }


def test_aftn_generate_for_custom():
    channel = AFTNChannel(makeConf())
    message = Other(text='SOME TEXT')

    generator = channel.generate(message, priority='FF', address='YUSO YUSI')
    lines = generator.toString().split('\r\n')

    assert lines[0] == 'ZCZC YMC0003'
    assert lines[1] == 'FF YUSO YUSI'
    assert 'SOME TEXT' in generator.toString()
    assert generator.toString().endswith('NNNN')


def test_file_channel_build_params():
    channel = FileChannel(makeConf())

    params = channel.buildParams(FakeMessage())

    assert params == {
        'text': 'NT36 YUSO 231200\nTAF YUSO 231200Z 2312/2412 03003MPS=',
        'number': '9',
    }


def test_file_channel_ftp_params():
    channel = FileChannel(makeConf())

    valids = (datetime.datetime(2026, 8, 23, 0), datetime.datetime(2026, 8, 23, 12))
    ftp = channel.ftpParams(valids)

    assert ftp['url'] == 'ftp://example.com/upload'
    assert re.match(r'^9_OTHE_C_YUSO_\d{14}_STUB', ftp['filename'])
    assert '_STUB-WTMG-MULT-20260823000000-20260823120000-XXX-1,00009.txt' in ftp['filename']


def test_file_channel_ftp_params_fallback_to_now():
    channel = FileChannel(makeConf())

    ftp = channel.ftpParams()

    match = re.search(r'MULT-(\d{14})-(\d{14})-', ftp['filename'])
    assert match
    assert match.group(1) == match.group(2)


def test_can_resend_window():
    now = datetime.datetime.utcnow()
    fresh = FakeMessage(created=now - datetime.timedelta(hours=1))
    stale = FakeMessage(created=now - datetime.timedelta(hours=3))
    confirmed = FakeMessage(created=now - datetime.timedelta(hours=1), confirmed=True)

    assert canResend(fresh, now) is True
    assert canResend(stale, now) is False
    assert canResend(confirmed, now) is False
