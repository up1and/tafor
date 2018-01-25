import requests

from PyQt5.QtCore import QThread, pyqtSignal

from tafor import conf, logger


def remoteMessage():
    url = conf.value('Monitor/WebApiURL')
    try:
        r = requests.get(url, timeout=30)
        if r.status_code == 200:
            return r.json()
        else:
            logger.warn('GET {} 404 Not Found'.format(url))

    except requests.exceptions.ConnectionError:
        logger.warn('GET {} 408 Request Timeout'.format(url))

    except Exception as e:
        logger.error(e, exc_info=True)

    return {}

def callUp(mobile):
    url = conf.value('Monitor/CallServiceURL')
    token = conf.value('Monitor/CallServiceToken') or ''
    try:
        r = requests.post(url, auth=('api', token), data={'mobile': mobile}, timeout=30)
        if r.status_code == 201:
            logger.info('Dial {} successfully'.format(mobile))
            return r.json()
        else:
            logger.warn('Dial {} failed {}'.format(mobile, r.text))

    except requests.exceptions.ConnectionError:
        logger.warn('POST {} 408 Request Timeout'.format(url))

    except Exception as e:
        logger.error(e, exc_info=True)

def callService():
    url = conf.value('Monitor/CallServiceURL')
    try:
        r = requests.get(url, timeout=5)
        return r.json()

    except requests.exceptions.ConnectionError:
            logger.info('GET {} 408 Request Timeout'.format(url))

    except Exception:
        pass

def repoRelease():
    url = 'https://api.github.com/repos/up1and/tafor/releases/latest'
    try:
        r = requests.get(url, timeout=30)
        return r.json()

    except Exception as e:
        logger.error(e)

    return {}


class WorkThread(QThread):
    def __init__(self, parent=None):
        super(WorkThread, self).__init__(parent)
        self.parent = parent

    def run(self):
        if conf.value('Monitor/WebApiURL'):
            self.parent.store.message = remoteMessage()

        if conf.value('Monitor/SelectedMobile'):
            self.parent.store.callService = callService()


class CallThread(QThread):
    def __init__(self, parent=None):
        super(CallThread, self).__init__(parent)
        self.parent = parent

    def run(self):
        mobile = conf.value('Monitor/SelectedMobile')
        callUp(mobile)


class CheckUpgradeThread(QThread):
    doneSignal = pyqtSignal(dict)

    def __init__(self, parent=None):
        super(CheckUpgradeThread, self).__init__(parent)
        self.parent = parent

    def run(self):
        data = repoRelease()
        self.doneSignal.emit(data)