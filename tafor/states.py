import sys
import copy
import datetime

from PyQt5.QtCore import QObject, pyqtSignal

from tafor import conf
from tafor.utils import boolean, MetarParser, SigmetParser


class MessageState(QObject):

    sigmetChanged = pyqtSignal()

    _state = {
        'remote': {},
        'sigmets': []
    }

    def message(self):
        return self._state['remote']

    def sigmets(self, type=None, airsigmet=None, show='nocnl'):
        types = []

        if airsigmet == 'SIGMET':
            types = ['WS', 'WC', 'WV']

        if airsigmet == 'AIRMET':
            types = ['WV']

        if isinstance(type, str):
            types = [type]

        if show == 'all':
            sigmets = self._state['sigmets']
        else:
            sigmets = [s for s in self._state['sigmets'] if not s.isCnl()]

        if types:
            return [s for s in sigmets if s.type in types]

        return sigmets

    def setMessage(self, values):
        self._state['remote'] = values

    def setSigmet(self, values):
        def diff(origin, ref):
            return set(ref).symmetric_difference(origin)

        sigmets = [s.text for s in self.sigmets()]
        refSigmets = [s.text for s in values]
        self._state['sigmets'] = values

        if diff(sigmets, refSigmets):
            self.sigmetChanged.emit()


class LayerState(QObject):
    refreshed = pyqtSignal()
    changed = pyqtSignal()

    _state = {
        'layers': []
    }

    showSigmet = True
    trimShapes = True
    layerExtend = []
    selected = []

    def layers(self):
        return self._state['layers']

    def setLayer(self, values):
        from tafor.utils.convert import Layer

        layers = []
        for data in values:
            layer = Layer(data)
            layers.append(layer)

        refLayerNames = [e.name for e in self.layers()]
        layerNames = [e.name for e in layers]
        self._state['layers'] = layers

        if refLayerNames != layerNames:
            self.changed.emit()

    def currentLayers(self):
        layers = []
        for layer in self.layers():
            if layer.name in self.selected:
                layers.append(layer)

        layers.sort(key=lambda x: x.overlay == 'mixed')
        return layers

    def currentStandaloneLayer(self):
        for layer in self.layers():
            if layer.name in self.selected and layer.overlay == 'standalone':
                return layer

    def findLayer(self, layerName):
        for layer in self.layers():
            if layer.name == layerName:
                return layer

    def groupLayers(self):
        layers = {}
        for layer in self.layers():
            if layer.overlay not in layers:
                layers[layer.overlay] = []

            layers[layer.overlay].append(layer)

        return layers

    def canStack(self, layerName):
        layer = self.findLayer(layerName)
        standalone = self.currentStandaloneLayer()
        if not layer:
            return False

        if standalone:
            if layer.proj != standalone.proj:
                return False

        return True

    def maxExtent(self):

        def _maxExtent(extent1, extent2):
            return [min(extent1[0], extent2[0]), min(extent1[1], extent2[1]), max(extent1[2], extent2[2]), max(extent1[3], extent2[3])]

        extent = []
        for layer1, layer2 in zip(self.layers(), self.layers()[1:]):
            extent = _maxExtent(layer1.extent, layer2.extent)

        return extent

    def boundaries(self):
        return [[114.000001907,14.500001907],[112.000001908,14.500001907],[108.716665268,17.416666031],[107.683332443,18.333333969],[107.18972222,19.26777778],[107.929967,19.9567],[108.050001145,20.500001907],[111.500001908,20.500001907],[111.500001908,19.500001907],[114.000001907,16.666666031],[114.000001907,14.500001907]]

    def refresh(self):
        self.refreshed.emit()


class SerialState(object):
    _lock = False

    def busy(self):
        return self._lock

    def lock(self):
        self._lock = True

    def release(self):
        self._lock = False


class TafState(QObject):

    reminded = pyqtSignal()

    _state = {
        'period': '',
        'message': None,
        'hasExpired': False,
        'clockRemind': False,
    }

    def hasExpired(self):
        return self._state['hasExpired']

    def needReminded(self):
        return self._state['clockRemind'] and self._state['message'] is None

    def period(self):
        return self._state['period']

    def message(self):
        return self._state['message']

    def state(self):
        return self._state

    @property
    def spec(self):
        index = conf.value('General/TAFSpec')
        specification = 'fc'
        if index == 1:
            specification = 'ft24'

        if index == 2:
            specification = 'ft30'

        return specification

    def setState(self, values):
        refs = copy.deepcopy(self._state)
        self._state.update(values)

        if self._state['clockRemind'] and refs['clockRemind'] != self._state['clockRemind']:
            self.reminded.emit()


class OtherState(QObject):
    messageChanged = pyqtSignal()

    def __init__(self):
        super(OtherState, self).__init__()
        self._state = {
            'uuid': None,
            'priority': None,
            'address': None,
            'message': None,
            'created': datetime.datetime.utcnow()
        }

    def setState(self, values):
        self._state.update(values)
        self._state['created'] = datetime.datetime.utcnow()
        self.messageChanged.emit()

    def state(self):
        return self._state


class NotificationMessageState(QObject):
    messageChanged = pyqtSignal()

    def __init__(self, expire=15):
        super(NotificationMessageState, self).__init__()
        self._state = {
            'message': None,
            'validation': False,
            'created': datetime.datetime.utcnow(),
        }
        self.previous = ''
        self.expire = expire

    def state(self):
        time = self._state['created']
        if datetime.datetime.utcnow() - time > datetime.timedelta(minutes=self.expire):
            self.clear()
        return self._state

    def setState(self, values):
        self.previous = self._state['message']
        validation = self._state['validation']
        self._state.update(values)
        if self.previous != self._state['message'] or validation != self._state['validation']:
            self._state['created'] = datetime.datetime.utcnow()
            self.messageChanged.emit()

    def message(self):
        state = self.state()
        text = state['message']
        if text is None:
            return ''
        return text

    def validation(self):
        return self._state['validation']

    def created(self):
        state = self.state()
        return state['created']

    def type(self):
        message = self.message()
        if message.startswith('METAR'):
            return 'METAR'

        if message.startswith('SPECI'):
            return 'SPECI'

        if 'AIRMET' in message:
            return 'AIRMET'

        if 'SIGMET' in message:
            return 'SIGMET'

        return 'UNKNOW'

    def parser(self):
        if self.type() in ['SIGMET', 'AIRMET']:
            return SigmetParser(self.message())

        if self.type() in ['METAR', 'SPECI']:
            visHas5000 = boolean(conf.value('Validator/VisHas5000'))
            cloudHeightHas450 = boolean(conf.value('Validator/CloudHeightHas450'))
            weakPrecipitationVerification = boolean(conf.value('Validator/WeakPrecipitationVerification'))
            return MetarParser(self.message(), ignoreMetar=True, previous=self.previous,
                visHas5000=visHas5000, cloudHeightHas450=cloudHeightHas450, weakPrecipitationVerification=weakPrecipitationVerification)

    def clear(self):
        self.setState({'message': None})
        self.previous = ''


class NotificationState(object):
    metar = NotificationMessageState(expire=10)
    sigmet = NotificationMessageState()


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
    authToken = 'VGhlIFZveWFnZSBvZiB0aGUgTW9vbg=='
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
            'bitness': 'amd64' if sys.maxsize > 2**32 else 'win32',
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

    def unit(self):
        from tafor.utils import boolean
        spec = boolean(conf.value('General/ImperialUnit'))
        return 'imperial' if spec else 'metric'

    def token(self):
        return conf.value('AuthToken') or self.authToken

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

    def hasPermission(self, reportType):
        if reportType == 'Trend':
            return True

        if reportType in ['TAF', 'Custom']:
            return 'airport' in self.license()

        if reportType in ['SIGMET', 'AIRMET']:
            return 'fir' in self.license()


class Context(object):
    message = MessageState()
    taf = TafState()
    layer = LayerState()
    other = OtherState()
    notification = NotificationState()
    serial = SerialState()
    environ = EnvironState()


context = Context()
