from serial import Serial
from serial import SerialException, SerialTimeoutException


def sendMessage(message, port):
    with Serial(port, timeout=1) as ser:
        message = bytes(message, 'utf-8')
        count = ser.write(message)
        return count == len(message)


if __name__ == '__main__':
    s = sendMessage('TAF ZJHK 201004Z 201221 11004MPS 9999 SCT020 TX28/12Z TN26/21Z=', 'COM4')
    print(s)