import sys
import copy
import datetime

from PyQt5.QtCore import QObject, pyqtSignal

from tafor import conf


class MessageState(object):
    _state = {}

    def state(self):
        return self._state

    def setState(self, values):
        self._state = values


class FirState(object):

    _state = {
        'boundaries': [],
        'layers': [],
        'sigmets': []
    }

    showSigmet = True
    trimShapes = True
    layerIndex = 0
    layers = []

    def setState(self, values):
        from tafor.utils.convert import Layer
        self._state.update(values)
        width = conf.value('General/FirCanvasSize') or 300

        self.layers = []
        for data in self._state['layers']:
            layer = Layer(data, width=int(width))
            self.layers.append(layer)

    @property
    def layer(self):
        from tafor.utils.convert import Layer
        try:
            return self.layers[self.layerIndex]
        except Exception:
            return Layer({})

    def layersName(self):
        names = []
        for layer in self.layers:
            if layer.name:
                names.append(layer.name)
        return names

    def sigmets(self):
        return self._state['sigmets']

    def boundaries(self):
        return self.layer.decimalToPixel(self._state['boundaries'])

    def sigmetsInfo(self, isAirmet=False):
        infos = []
        if isAirmet:
            sigmets = [s for s in self._state['sigmets'] if s.tt == 'WA']
        else:
            sigmets = [s for s in self._state['sigmets'] if s.tt != 'WA']

        for sig in sigmets:
            area = {}
            parser = sig.parser()
            for key, item in parser.area().items():
                polygon = self.decodeSigmetArea(item)
                area[key] = polygon

            infos.append({
                'type': parser.type(),
                'area': area
            })

        return infos

    def decodeSigmetArea(self, area):
        return self.layer.decodeSigmetArea(area, self._state['boundaries'], self.trimShapes)


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

    def busy(self):
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
                'warning': False,
                'clock': False,
            },
            'FT': {
                'period': '',
                'sent': False,
                'warning': False,
                'clock': False,
            }
        }

    def isWarning(self):
        warnings = [v['warning'] for k, v in self._state.items()]
        return any(warnings)

    def state(self):
        return self._state

    @property
    def spec(self):
        from tafor.utils import boolean

        international = boolean(conf.value('General/InternationalAirport'))
        index = conf.value('General/ValidityPeriod')
        if international:
            if index:
                specification = 'ft30'
            else:
                specification = 'ft24'
        else:
            specification = 'fc'

        return specification

    def setState(self, values):
        refs = copy.deepcopy(self._state)
        self._state.update(values)

        for tt, state in values.items():
            if 'warning' in state:
                self.warningSignal.emit()

            if 'clock' in state:
                if refs[tt]['clock'] != state['clock']:
                    self.clockSignal.emit(tt)


class MetarState(QObject):
    messageChanged = pyqtSignal()

    _state = {
        'message': None,
        'updated': datetime.datetime.utcnow(),
    }

    def state(self):
        return self._state

    def setState(self, values):
        message = self._state['message']
        self._state.update(values)
        self._state['updated'] = datetime.datetime.utcnow()
        if message != self._state['message']:
            self.messageChanged.emit()


class EnvironState(object):
    key = """-----BEGIN PUBLIC KEY-----
    MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA2AZZfefXdgpvnWcV9xMf
    qlBqTS/8XZXq9BwFRpe0thoS3fER8s5fGKDWiOzO2I2PEwvahXyPny4hxHll7vF+
    lgd3dl0Z5BRslDGzSUe3/S2vqu4jAiyFmF3z8HZ9Jcr7BXi8yYUOr/LUfOP2gWK3
    GnORnWhBTb/llaGjN72yoJKJpKEbJYlrBJdsOyBrAeXbg1QNktOuqPf5toP/72qU
    2a/RRvpK9koSHMvhqd6ex5h+MHvcQZ759Fi1wxj5ChkB6BGgsHGR+7f49c92Gd4o
    2TKLicLL6vcidL4QkXdhRaZTJyd8pYI6Su+FUK7mcaBDpEaUl9xWupJnjsfKx1bf
    WQIDAQAB
    -----END PUBLIC KEY-----"""
    exp = 0

    def environment(self):
        import platform

        from PyQt5.QtCore import QT_VERSION_STR
        from tafor import __version__

        if not sys.platform == 'darwin':  # To avoid a crash with our Mac app
            system = platform.system()
        else:
            system = 'Darwin'

        return {
            'version': __version__,
            'python': platform.python_version(),
            'bitness': 64 if sys.maxsize > 2**32 else 32,
            'qt': QT_VERSION_STR,
            'system': system,
            'release': platform.release(),
            'revision': self.ghash()
        }

    def ghash(self):
        if hasattr(sys, '_MEIPASS'):
            from tafor._environ import ghash
            return ghash
        else:
            from tafor.utils import gitRevisionHash
            return gitRevisionHash()

    def license(self):
        from tafor.utils import verifyToken
        payload = verifyToken(conf.value('License'), self.key)

        if payload is None:
            return {}

        if 'exp' in payload:
            exp = datetime.datetime.fromtimestamp(payload['exp'])
            now = datetime.datetime.utcnow()
            self.exp = (exp - now).days

        data = {}
        for k, info in self.register().items():
            if k in payload and info == payload[k]:
                data[k] = info

        return data

    def register(self):
        infos = {}
        if conf.value('Message/ICAO'):
            infos['airport'] = conf.value('Message/ICAO')
        if conf.value('Message/FIR'):
            infos['fir'] = conf.value('Message/FIR')[:4]

        return infos

    def canEnable(self, reportType):
        if reportType == 'Trend':
            return True

        if reportType == 'TAF':
            return 'airport' in self.license()

        if reportType in ['SIGMET', 'AIRMET']:
            return 'fir' in self.license()


class Context(object):
    message = MessageState()
    webApi = WebApiState(message)
    callService = CallServiceState()
    taf = TafState()
    metar = MetarState()
    fir = FirState()
    serial = SerialState()
    environ = EnvironState()


context = Context()
