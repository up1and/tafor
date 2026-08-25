import pytest

from tafor.core.telegram.encoder import ITA2_STANDARD, encode
from tafor.core.telegram.transport import serialComm


class FakePort(object):

    def __init__(self):
        self.written = b''

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def reset_output_buffer(self):
        pass

    def write(self, data):
        self.written += data

    def flush(self):
        pass


@pytest.fixture
def port(monkeypatch):
    fake = FakePort()
    monkeypatch.setattr('tafor.core.telegram.transport.serial.Serial', lambda *a, **kw: fake)
    monkeypatch.setattr('tafor.core.telegram.transport.time.sleep', lambda seconds: None)
    return fake


class TestSerialCommCodec(object):

    def test_ita2_codec_encodes_via_table(self, port):
        message = 'AB1'
        serialComm(message, 'COM3', codec='ITA2')
        assert port.written == encode(message, ITA2_STANDARD)

    def test_default_codec_encodes_utf8(self, port):
        serialComm('AB1', 'COM3')
        assert port.written == b'AB1'

    def test_bytes_pass_through_unchanged(self, port):
        payload = b'\x01\x02\x1b\r\n'
        serialComm(payload, 'COM3')
        assert port.written == payload

    def test_non_ita2_codec_falls_back_to_utf8(self, port):
        serialComm('AB1', 'COM3', codec='ASCII')
        assert port.written == b'AB1'
