import copy

from PyQt5.QtCore import QObject, QPoint, pyqtSignal


class MessageState(object):
    _state = {}

    def state(self):
        return self._state

    def setState(self, values):
        self._state = values


class FirState(object):
    _state = {
        'raw': None,
        'size': [0, 0],
        'coordinates': [
            [30, 90],
            [10, 120],
        ],
        'rect': [0, 0, 0, 0],
        'boundaries': []
    }

    def state(self):
        return self._state

    def setState(self, values):
        self._state.update(values)

        self.updateConst()

    def updateConst(self):
        latRange = self._state['coordinates'][0][0] - self._state['coordinates'][1][0]
        longRange = self._state['coordinates'][1][1] - self._state['coordinates'][0][1]
        self.initLat = self._state['coordinates'][0][0]
        self.initLong = self._state['coordinates'][0][1]
        self.dlat = latRange / self._state['size'][1]
        self.dlong = longRange / self._state['size'][0]
        self.offsetX = self._state['rect'][0]
        self.offsetY = self._state['rect'][1]

    def raw(self):
        return self._state['raw']

    def rect(self):
        return self._state['rect']

    def boundaries(self):
        return self.degreeToPixel(self._state['boundaries'])

    def degreeToPixel(self, degreePoints):
        points = []
        for p in degreePoints:
            x = (p[0] - self.initLong) / self.dlong - self.offsetX
            y = (self.initLat - p[1]) / self.dlat - self.offsetY
            points.append([x, y])

        return points

    def pixelToDegree(self, pixelPoints):
        from tafor.utils.convert import decimalToDegree

        points = []
        for p in pixelPoints:
            longtitude = self.initLong + (p[0] + self.offsetX) * self.dlong
            latitude = self.initLat - (p[1] + self.offsetY) * self.dlat
            points.append([
                decimalToDegree(longtitude, fmt='longitude'),
                decimalToDegree(latitude)
            ])

        return points


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
    fir = FirState()
    serial = SerialState()


context = Context()