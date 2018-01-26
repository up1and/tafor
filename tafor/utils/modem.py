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

    with serial.Serial(port, baudrate, timeout=1, bytesize=bytesize, 
                        parity=parity, stopbits=stopbits) as ser:
        message = bytes(message, 'utf-8')
        count = ser.write(message)
        return count == len(message)


if __name__ == '__main__':
    s = serialComm('TEST', 'COM3')
    print(s)