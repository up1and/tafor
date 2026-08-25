import time
import serial

from io import BytesIO
from ftplib import FTP
from urllib.parse import urlparse

from tafor.core.telegram.encoder import ITA2_STANDARD, encode


def serialComm(message, port, baudrate=9600, bytesize='8', parity='NONE', stopbits='1', codec=None):
    """Write a message to the serial port.

    codec 'ITA2' encodes the text through the ITA2 standard table first;
    otherwise plain text is encoded as UTF-8 unless already bytes.
    """
    if codec == 'ITA2':
        message = encode(message, ITA2_STANDARD)
    elif not isinstance(message, bytes):
        message = message.encode()

    bytesizeMap = {
        '5': serial.FIVEBITS,
        '6': serial.SIXBITS,
        '7': serial.SEVENBITS,
        '8': serial.EIGHTBITS
    }
    parityMap = {
        'NONE': serial.PARITY_NONE,
        'EVEN': serial.PARITY_EVEN,
        'ODD': serial.PARITY_ODD
    }
    stopbitsMap = {
        '1': serial.STOPBITS_ONE,
        '1.5': serial.STOPBITS_ONE_POINT_FIVE,
        '2': serial.STOPBITS_TWO
    }

    bytesize = bytesizeMap.get(bytesize, serial.EIGHTBITS)
    parity = parityMap.get(parity, serial.PARITY_NONE)
    stopbits = stopbitsMap.get(stopbits, serial.STOPBITS_ONE)

    with serial.Serial(port, baudrate, bytesize=bytesize,
                        parity=parity, stopbits=stopbits) as ser:
        ser.reset_output_buffer()
        ser.write(message)
        ser.flush()
        # wait for the UART to shift out the last bytes before the port closes.
        # one byte on the wire is start(1) + data + parity(0/1) + stop bits. 
        # add a fixed margin so short messages are not cut off by the close().
        bitsPerByte = int(bytesize) + float(stopbits) + (1 if parity in ('EVEN', 'ODD') else 0)
        transmitTime = len(message) * bitsPerByte / baudrate + 0.1
        time.sleep(transmitTime)

def ftpComm(message, url, filename, tempsuffix='part'):
    parser = urlparse(url)
    port = parser.port or 0
    tempname = filename + '.' + tempsuffix
    with FTP() as ftp:
        ftp.connect(host=parser.hostname, port=port, timeout=30)
        ftp.login(user=parser.username, passwd=parser.password)
        ftp.cwd(parser.path)
        if not message:
            return

        if not isinstance(message, bytes):
            message = message.encode()

        ftp.storbinary('STOR %s' % tempname, BytesIO(message))
        ftp.rename(tempname, filename)


if __name__ == '__main__':
    text = 'The quick brown fox jumped over the lazy dog\r\n'
    serialComm(text * 10, 'COM4', baudrate=300)