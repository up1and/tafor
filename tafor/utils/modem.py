import time
import serial

from io import BytesIO
from ftplib import FTP
from urllib.parse import urlparse


def serialComm(message, port, baudrate=9600, bytesize='8', parity='NONE', stopbits='1'):
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

    if baudrate < 300:
        timeout = 6
    elif baudrate < 1200:
        timeout = 3
    elif baudrate < 9600:
        timeout = 2
    else:
        timeout = 1

    if not isinstance(message, bytes):
        message = message.encode()

    with serial.Serial(port, baudrate, bytesize=bytesize,
                        parity=parity, stopbits=stopbits) as ser:
        ser.reset_output_buffer()
        lenth = len(message)
        sentLenth = ser.write(message)
        ser.flush()
        time.sleep(timeout)

        if lenth != sentLenth:
            raise serial.SerialException('Send data is incomplete')

def ftpComm(message, url, filename):
    parser = urlparse(url)
    port = parser.port or 0
    with FTP() as ftp:
        ftp.connect(host=parser.hostname, port=port)
        ftp.login(user=parser.username, passwd=parser.password)
        ftp.cwd(parser.path)
        if not message:
            return

        if not isinstance(message, bytes):
            message = message.encode()

        ftp.storbinary('STOR %s' % filename, BytesIO(message))


if __name__ == '__main__':
    text = 'The quick brown fox jumped over the lazy dog\r\n'
    serialComm(text * 10, 'COM4', baudrate=300)