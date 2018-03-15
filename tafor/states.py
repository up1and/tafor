import copy

from PyQt5.QtCore import QObject, pyqtSignal


class MessageState(object):
    _state = {}

    def state(self):
        return self._state

    def setState(self, values):
        self._state = values


class WebApiState(object):

    def __init__(self, store):
        self._store = store

    def isOnline(self):
        return True if self._store.state() else False


class CallServiceState(object):
    _state = None

    def isOnline(self):
        return True if self._state else False

    def setState(self, value):
        self._state = value


class SerialState(object):
    _lock = False

    def isBusy(self):
        return self._lock

    def lock(self):
        self._lock = True

    def release(self):
        self._lock = False


class TafState(QObject):
    warningSignal = pyqtSignal()
    clockSignal = pyqtSignal(str)

    def __init__(self):
        super(TafState, self).__init__()
        self._state = {
            'FC': {
                'period': '',
                'sent': False,
                'warnning': False,
                'clock': False,
            },
            'FT': {
                'period': '',
                'sent': False,
                'warnning': False,
                'clock': False,
            }
        }

    def isWarning(self):
        warnnings = [v['warnning'] for k, v in self._state.items()]
        return any(warnnings)

    def state(self):
        return self._state

    def setState(self, values):
        refs = copy.deepcopy(self._state)
        self._state.update(values)

        for tt, state in values.items():
            if 'warnning' in state:
                self.warningSignal.emit()

            if 'clock' in state:
                if refs[tt]['clock'] != state['clock']:
                    self.clockSignal.emit(tt)


class Context(object):
    message = MessageState()
    webApi = WebApiState(message)
    callService = CallServiceState()
    taf = TafState()
    serial = SerialState()


context = Context()