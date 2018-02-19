import requests

from PyQt5.QtCore import QThread, pyqtSignal

from tafor import conf, logger
from tafor.utils import serialComm


def remoteMessage(url):
    try:
        r = requests.get(url, timeout=30)
        if r.status_code == 200:
            return r.json()
        else:
            logger.warn('GET {} 404 Not Found'.format(url))

    except requests.exceptions.ConnectionError:
        logger.warn('GET {} 408 Request Timeout'.format(url))

    except Exception as e:
        logger.error(e)

    return {}

def callUp(url, token, mobile):
    try:
        r = requests.post(url, auth=('api', token), data={'mobile': mobile, 'code': '000000'}, timeout=30)
        if r.status_code in [200, 201]:
            logger.info('Dial {} successfully'.format(mobile))
            return r.json()
        else:
            logger.warn('Dial {} failed {}'.format(mobile, r.text))

    except requests.exceptions.ConnectionError:
        logger.warn('POST {} 408 Request Timeout'.format(url))

    except Exception as e:
        logger.error(e)

def callService(url):
    try:
        r = requests.get(url, timeout=5)
        return r.json()

    except requests.exceptions.ConnectionError:
            logger.info('GET {} 408 Request Timeout'.format(url))

    except Exception as e:
        logger.error(e)

def repoRelease(url):
    try:
        r = requests.get(url, timeout=30)
        return r.json()

    except requests.exceptions.ConnectionError:
            logger.info('GET {} 408 Request Timeout'.format(url))

    except Exception as e:
        logger.error(e)

    return {}


class WorkThread(QThread):

    def __init__(self, parent=None):
        super(WorkThread, self).__init__(parent)
        self.parent = parent

    def run(self):
        if conf.value('Monitor/WebApiURL'):
            url = conf.value('Monitor/WebApiURL') or 'http://127.0.0.1:6575'
            self.parent.context.message = remoteMessage(url)

        if conf.value('Monitor/SelectedMobile'):
            url = conf.value('Monitor/CallServiceURL') or 'http://127.0.0.1:5000/api/call/'
            self.parent.context.callService = callService(url)


class CallThread(QThread):
    
    def __init__(self, parent=None):
        super(CallThread, self).__init__(parent)
        self.parent = parent

    def run(self):
        url = conf.value('Monitor/CallServiceURL') or 'http://127.0.0.1:5000/api/call/'
        token = conf.value('Monitor/CallServiceToken') or ''
        mobile = conf.value('Monitor/SelectedMobile')
        callUp(url, token, mobile)


class SerialThread(QThread):
    doneSignal = pyqtSignal(str)

    def __init__(self, message, parent=None):
        super(SerialThread, self).__init__(parent)
        self.message = message
        self.parent = parent

    def run(self):
        port = conf.value('Communication/SerialPort')
        baudrate = int(conf.value('Communication/SerialBaudrate'))
        bytesize = conf.value('Communication/SerialBytesize')
        parity = conf.value('Communication/SerialParity')
        stopbits = conf.value('Communication/SerialStopbits')

        try:
            serialComm(self.message, port, baudrate=baudrate, bytesize=bytesize, parity=parity, stopbits=stopbits)
            error = ''
        except Exception as e:
            error = str(e)
            logger.error(e)
        finally:
            self.doneSignal.emit(error)


class CheckUpgradeThread(QThread):
    doneSignal = pyqtSignal(dict)

    def __init__(self, parent=None):
        super(CheckUpgradeThread, self).__init__(parent)
        self.parent = parent

    def run(self):
        url = 'https://api.github.com/repos/up1and/tafor/releases/latest'
        data = repoRelease(url)
        self.doneSignal.emit(data)