import csv
import datetime

import requests

from PyQt5.QtCore import QThread, pyqtSignal

from tafor import conf, logger, __version__
from tafor.rpc import server
from tafor.states import context
from tafor.utils import serialComm, ftpComm
from tafor.utils.baudot import encode, ITA2_STANDARD


_headers = {
    'User-Agent': 'tafor/{}'.format(__version__)
}


def remoteMessage(url):
    try:
        r = requests.get(url, headers=_headers, timeout=30)
        if r.status_code == 200:
            return r.json()
        else:
            logger.warn('GET {} 404 Not Found'.format(url))

    except requests.exceptions.ConnectionError:
        logger.warn('GET {} 408 Request Timeout'.format(url))

    except Exception as e:
        logger.error(e)

    return {}

def layerInfo(url):
    try:
        r = requests.get(url, headers=_headers, timeout=30)
        if r.status_code == 200:
            data = r.json()
            for layer in data:
                imageUrl = layer['image']
                try:
                    req = requests.get(imageUrl)
                    layer['image'] = req.content
                except Exception as e:
                    layer['image'] = None
            return {'layers': data}
        else:
            logger.warn('GET {} 404 Not Found'.format(url))

    except requests.exceptions.ConnectionError:
        logger.warn('GET {} 408 Request Timeout'.format(url))

    except Exception as e:
        logger.error(e)

    return {}

def callUp(url, token, mobile):
    try:
        r = requests.post(url, headers=_headers, auth=('api', token), data={'mobile': mobile, 'code': '000000'}, timeout=30)
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
        r = requests.get(url, headers=_headers, timeout=5)
        return r.json()

    except requests.exceptions.ConnectionError:
            logger.info('GET {} 408 Request Timeout'.format(url))

    except Exception as e:
        logger.error(e)

def repoRelease(url):
    try:
        r = requests.get(url, headers=_headers, timeout=30)
        return r.json()

    except requests.exceptions.ConnectionError:
            logger.info('GET {} 408 Request Timeout'.format(url))

    except Exception as e:
        logger.error(e)

    return {}


class WorkThread(QThread):

    def run(self):
        if conf.value('Monitor/WebApiURL'):
            url = conf.value('Monitor/WebApiURL') or 'http://127.0.0.1:6575'
            context.message.setState(remoteMessage(url))

        if conf.value('Monitor/SelectedMobile'):
            url = conf.value('Monitor/CallServiceURL') or 'http://127.0.0.1:5000/api/call/'
            context.callService.setState(callService(url))


class LayerThread(QThread):

    def run(self):
        url = conf.value('Monitor/FirApiURL')
        context.layer.setState(layerInfo(url))


class CallThread(QThread):

    def run(self):
        url = conf.value('Monitor/CallServiceURL') or 'http://127.0.0.1:5000/api/call/'
        token = conf.value('Monitor/CallServiceToken') or ''
        mobile = conf.value('Monitor/SelectedMobile')
        callUp(url, token, mobile)


class ExportRecordThread(QThread):

    def __init__(self, filename, data, headers=None, timefield='sent'):
        super(ExportRecordThread, self).__init__()
        self.data = data
        self.headers = headers
        self.timefield = timefield
        self.filename = filename

    def run(self):
        with open(self.filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            if self.headers:
                writer.writerow(self.headers)
            for row in self.data:
                writer.writerow(row)


class SerialThread(QThread):

    done = pyqtSignal(str)

    def __init__(self, message):
        super(SerialThread, self).__init__()
        self.message = message

    def run(self):
        port = conf.value('Communication/SerialPort')
        baudrate = int(conf.value('Communication/SerialBaudrate'))
        bytesize = conf.value('Communication/SerialBytesize')
        parity = conf.value('Communication/SerialParity')
        stopbits = conf.value('Communication/SerialStopbits')
        codec = conf.value('Communication/Codec')

        try:
            context.serial.lock()
            if codec == 'ITA2':
                message = encode(self.message, ITA2_STANDARD)
            else:
                message = self.message.encode()
            serialComm(message, port, baudrate=baudrate, bytesize=bytesize, parity=parity, stopbits=stopbits)
            error = ''
        except Exception as e:
            error = str(e)
            logger.error(e)
        finally:
            context.serial.release()
            self.done.emit(error)


class FtpThread(QThread):

    done = pyqtSignal(str)

    def __init__(self, message):
        super(FtpThread, self).__init__()
        self.message = message

    def run(self):
        url = conf.value('Communication/FTPHost')
        time = datetime.datetime.utcnow()
        filename = time.strftime('%Y%m%d%H%M%S%f')
        filename = 'M1{}.TXT'.format(filename[:-3])

        try:
            ftpComm(self.message, url, filename)
            error = ''
        except Exception as e:
            error = str(e)
            logger.error(e)
        finally:
            self.done.emit(error)


class CheckUpgradeThread(QThread):

    done = pyqtSignal(dict)

    def run(self):
        url = 'https://api.github.com/repos/up1and/tafor/releases/latest'
        data = repoRelease(url)
        self.done.emit(data)


class RpcThread(QThread):

    def __init__(self, port=9407):
        super(RpcThread, self).__init__()
        self.app = server
        self.port = port

    def __del__(self):
        self.wait()

    def run(self):
        from waitress import serve
        serve(self.app, port=self.port)
