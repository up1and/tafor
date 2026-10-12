"""Tests for serialComm and ftpComm."""

import pytest
import serial

from tafor.core.telegram.transport import ftpComm, serialComm


class FakePort:
    """Captures what serialComm writes and how it opens the port."""

    def __init__(self):
        self.written = b''
        self.opened = None
        self.reset = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def reset_output_buffer(self):
        self.reset = True

    def write(self, data):
        self.written += data

    def flush(self):
        pass


@pytest.fixture
def port(monkeypatch):
    fake = FakePort()

    def openPort(*args, **kwargs):
        fake.opened = (args, kwargs)
        return fake

    monkeypatch.setattr('tafor.core.telegram.transport.serial.Serial', openPort)
    monkeypatch.setattr('tafor.core.telegram.transport.time.sleep', lambda seconds: None)
    return fake


@pytest.fixture
def slept(monkeypatch):
    delays = []
    monkeypatch.setattr('tafor.core.telegram.transport.serial.Serial',
                        lambda *a, **kw: FakePort())
    monkeypatch.setattr('tafor.core.telegram.transport.time.sleep', delays.append)
    return delays


def test_the_port_is_opened_with_the_mapped_serial_constants(port):
    serialComm('X', 'COM3', baudrate=1200, bytesize='7', parity='EVEN', stopbits='2')

    args, kwargs = port.opened
    assert args == ('COM3', 1200)
    assert kwargs['bytesize'] == serial.SEVENBITS
    assert kwargs['parity'] == serial.PARITY_EVEN
    assert kwargs['stopbits'] == serial.STOPBITS_TWO


def test_an_unknown_setting_falls_back_to_the_defaults(port):
    serialComm('X', 'COM3', bytesize='9', parity='MAYBE', stopbits='3')

    _, kwargs = port.opened
    assert kwargs['bytesize'] == serial.EIGHTBITS
    assert kwargs['parity'] == serial.PARITY_NONE
    assert kwargs['stopbits'] == serial.STOPBITS_ONE


def test_the_output_buffer_is_reset_before_writing(port):
    serialComm('X', 'COM3')

    assert port.reset


def test_the_wait_covers_the_time_on_the_wire(slept):
    # 10 bytes, 8 data bits, no parity, 1 stop bit = 10 bits each,
    # 100 bits at 9600 baud is 0.0104 s, plus the fixed 0.1 s margin
    serialComm('X' * 10, 'COM3', baudrate=9600)

    assert slept == [pytest.approx(10 * 10 / 9600 + 0.1)]


def test_a_parity_bit_lengthens_the_wait(slept):
    serialComm('X' * 10, 'COM3', baudrate=9600, parity='EVEN')

    assert slept == [pytest.approx(10 * 11 / 9600 + 0.1)]


def test_stop_bits_lengthen_the_wait(slept):
    serialComm('X' * 10, 'COM3', baudrate=9600, stopbits='2')

    assert slept == [pytest.approx(10 * 11 / 9600 + 0.1)]


class FakeFtp:
    """Records the FTP calls ftpComm makes."""

    def __init__(self):
        self.calls = []
        self.stored = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def connect(self, **kwargs):
        self.calls.append(('connect', kwargs))

    def login(self, **kwargs):
        self.calls.append(('login', kwargs))

    def cwd(self, path):
        self.calls.append(('cwd', path))

    def storbinary(self, cmd, fileobj):
        self.stored = (cmd, fileobj.read())

    def rename(self, src, dst):
        self.calls.append(('rename', src, dst))


@pytest.fixture
def ftp(monkeypatch):
    fake = FakeFtp()
    monkeypatch.setattr('tafor.core.telegram.transport.FTP', lambda *a, **kw: fake)
    return fake


def test_ftp_connects_with_the_parsed_url(ftp):
    ftpComm('DATA', 'ftp://user:secret@example.com:2121/drop/', 'tafor.txt')

    assert ('connect', {'host': 'example.com', 'port': 2121, 'timeout': 30}) in ftp.calls
    assert ('login', {'user': 'user', 'passwd': 'secret'}) in ftp.calls
    assert ('cwd', '/drop/') in ftp.calls


def test_ftp_uploads_under_a_temporary_name_then_renames(ftp):
    ftpComm('DATA', 'ftp://example.com/drop/', 'tafor.txt')

    assert ftp.stored == ('STOR tafor.txt.part', b'DATA')
    assert ('rename', 'tafor.txt.part', 'tafor.txt') in ftp.calls


def test_ftp_uses_the_configured_temporary_suffix(ftp):
    ftpComm('DATA', 'ftp://example.com/drop/', 'tafor.txt', tempsuffix='tmp')

    assert ftp.stored[0] == 'STOR tafor.txt.tmp'
    assert ('rename', 'tafor.txt.tmp', 'tafor.txt') in ftp.calls


def test_ftp_leaves_an_existing_port_out_of_the_connect_call(ftp):
    ftpComm('DATA', 'ftp://example.com/drop/', 'tafor.txt')

    assert ('connect', {'host': 'example.com', 'port': 0, 'timeout': 30}) in ftp.calls


def test_an_empty_message_is_not_uploaded(ftp):
    ftpComm('', 'ftp://example.com/drop/', 'tafor.txt')

    assert ftp.stored is None
    assert not any(call[0] == 'rename' for call in ftp.calls)


def test_bytes_are_uploaded_unchanged(ftp):
    ftpComm(b'\x01\x02', 'ftp://example.com/drop/', 'tafor.txt')

    assert ftp.stored[1] == b'\x01\x02'
