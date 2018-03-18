import math
import serial


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

    # 一个 ascii 8 位，停止位 2 位，起始位 1 位，校验位 1 位
    timeout = math.ceil(12 * len(message) / baudrate)

    with serial.Serial(port, baudrate, timeout=timeout, bytesize=bytesize, 
                        parity=parity, stopbits=stopbits) as ser:
        lenth = len(message)
        message = bytes(message, 'ascii')
        sentLenth = ser.write(message)
        end = ser.readline()

        if lenth != sentLenth:
            raise serial.SerialException('Send data is incomplete')


if __name__ == '__main__':
    s = serialComm('The quick brown fox jumped over the lazy dog', 'COM5')