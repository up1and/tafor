import os
import sys
import copy
import json
import datetime

from PyQt5.QtCore import QObject, pyqtSignal

from tafor import root, conf
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

    def projection(self):
        from pyproj import Proj

        try:
            proj = Proj(conf.value('Layer/Projection'))

        except Exception as e:
            conf.setValue('Layer/Projection', '+proj=webmerc +datum=WGS84')
            proj = Proj('+proj=webmerc +datum=WGS84')

        return proj

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
        try:
            boundary = json.loads(conf.value('Layer/FIRBoundary'))
            if not isinstance(boundary, list):
                return []
        except Exception as e:
            return []

        return boundary

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
        index = int(conf.value('General/TAFSpec'))
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


class SigmetState(object):

    _state = {}
    
    ahead = 20

    def add(self, uuid, text, time):
        self._state[uuid] = {
            'text': text,
            'time': time
        }

    def update(self, uuid, time):
        self._state[uuid]['time'] = time

    def remove(self, uuid):
        self._state.pop(uuid, None)

    def state(self):
        return self._state

    def outdate(self):
        outdates = []
        now = datetime.datetime.utcnow()
        for uuid, value in self._state.items():
            if value['time'] - datetime.timedelta(minutes=self.ahead) < now:
                outdates.append(
                    {'uuid': uuid, 'text': value['text'], 'time': value['time']}
                )

        return outdates
    

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


class FlashState(QObject):
    systemMessageChanged = pyqtSignal(str, str, str)
    statusbarMessageChanged = pyqtSignal(str, int)
    editorMessageChanged = pyqtSignal(str, str)

    def addMessage(self, title, text, level='information', dest='system', timeout=5000):
        if dest == 'editor':
            self.editorMessageChanged.emit(title, text)
        elif dest == 'statusbar':
            self.statusbarMessageChanged.emit(text, timeout)
        else:
            self.systemMessageChanged.emit(title, text, level)

    def info(self, title, text):
        self.addMessage(title, text)

    def warning(self, title, text):
        self.addMessage(title, text, level='warning')

    def statusbar(self, text, timeout=5000):
        self.addMessage('', text, dest='statusbar', timeout=timeout)

    def editor(self, title, text):
        self.addMessage(title, text, dest='editor')


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
            visHas5000 = boolean(conf.value('Validation/VisHas5000'))
            cloudHeightHas450 = boolean(conf.value('Validation/CloudHeightHas450'))
            weakPrecipitationVerification = boolean(conf.value('Validation/WeakPrecipitationVerification'))
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
        return conf.value('Interface/AuthToken') or self.authToken

    def license(self, token=None):
        from tafor.utils import verifyToken

        if not token:
            token = conf.value('License')

        payload = verifyToken(token, self.key)

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

    def bundlePath(self, relativePath):
        if hasattr(sys, '_MEIPASS'): 
            base = sys._MEIPASS
        else:
            base = root
        return os.path.join(base, relativePath)

    def fixedFont(self):
        from PyQt5.QtGui import QFontDatabase
        font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        return font


class Context(object):
    message = MessageState()
    taf = TafState()
    sigmet = SigmetState()
    layer = LayerState()
    other = OtherState()
    notification = NotificationState()
    flash = FlashState()
    serial = SerialState()
    environ = EnvironState()


context = Context()
