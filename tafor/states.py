import os
import sys
import datetime

from PyQt5.QtCore import QObject, pyqtSignal


class MessageState:
    def __init__(self):
        self.remote = {}
        self.sigmets = []


class LayerState:
    def __init__(self):
        self.layers = []
        self.showSigmet = True
        self.trimShapes = True
        self.layerExtend = []
        self.selected = []


class TafState:
    def __init__(self):
        self.period = ''
        self.message = None
        self.hasExpired = False
        self.clockRemind = False


class SigmetState:
    def __init__(self):
        self.entries = {}
        self.aheadMinutes = 20


class NotificationState:
    def __init__(self, expireMinutes=15):
        self.message = None
        self.validation = False
        self.created = datetime.datetime.utcnow()
        self.expireMinutes = expireMinutes
        self.previous = ''


class OtherState:
    def __init__(self):
        self.uuid = None
        self.priority = None
        self.address = None
        self.message = None
        self.created = datetime.datetime.utcnow()


class Event(QObject):
    # State change events
    messageStateChanged = pyqtSignal(object)
    layerStateChanged = pyqtSignal(object)
    tafStateChanged = pyqtSignal(object)
    sigmetStateChanged = pyqtSignal(object)
    notificationStateChanged = pyqtSignal(str)
    otherMessageChanged = pyqtSignal()

    # UI events
    systemMessage = pyqtSignal(str, str, str)
    statusbarMessage = pyqtSignal(str, int)
    editorMessage = pyqtSignal(str, str)

    # Business events
    sigmetDataChanged = pyqtSignal()
    layerRefreshed = pyqtSignal()
    layerDataChanged = pyqtSignal()
    tafReminded = pyqtSignal()


class StateProxyMixin:
    """Readonly Property Mixin"""
    fields = ['']

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        for field in cls.fields:
            getter = lambda self, f=field: getattr(self.state, f)
            setattr(cls, field, property(getter))


class MessageService(QObject):
    def __init__(self, state, event):
        super().__init__()
        self.state = state
        self.event = event

    def message(self):
        return self.state.remote

    def setRemoteMessage(self, values):
        self.state.remote = values
        self.event.messageStateChanged.emit(self.state)

    def setSigmets(self, sigmets):
        oldSigmets = [s.text for s in self.state.sigmets]
        newSigmets = [s.text for s in sigmets]

        self.state.sigmets = sigmets
        self.event.messageStateChanged.emit(self.state)

        if set(oldSigmets) != set(newSigmets):
            self.event.sigmetDataChanged.emit()

    def sigmets(self, type=None, airsigmet=None, show='nocnl'):
        types = []

        if airsigmet == 'SIGMET':
            types = ['WS', 'WC', 'WV']

        if airsigmet == 'AIRMET':
            types = ['WA']

        if isinstance(type, str):
            types = [type]

        if show == 'all':
            sigmets = self.state.sigmets
        else:
            sigmets = [s for s in self.state.sigmets if not s.isCnl()]

        if types:
            return [s for s in sigmets if s.type in types]

        return sigmets


class LayerService(QObject, StateProxyMixin):
    fields = ['selected', 'showSigmet', 'trimShapes']

    def __init__(self, state, event):
        super().__init__()
        self.state = state
        self.event = event

    def setLayer(self, layerData):
        from tafor.utils.convert import Layer

        layers = [Layer(data) for data in layerData]
        oldNames = [l.name for l in self.state.layers]
        newNames = [l.name for l in layers]

        self.state.layers = layers
        self.event.layerStateChanged.emit(self.state)

        if oldNames != newNames:
            self.event.layerDataChanged.emit()

    def setState(self, values):
        changed = False
        for key, value in values.items():
            if key == 'selected':
                value = list(value)
            elif key in ['showSigmet', 'trimShapes']:
                value = bool(value)
            else:
                raise AttributeError('Unknown layer state field: {}'.format(key))

            if getattr(self.state, key) == value:
                continue

            setattr(self.state, key, value)
            changed = True

        if changed:
            self.event.layerStateChanged.emit(self.state)

        return changed

    def getLayers(self):
        return self.state.layers

    def findLayer(self, layerName):
        for layer in self.state.layers:
            if layer.name == layerName:
                return layer

    def currentLayers(self):
        layers = []
        for layer in self.state.layers:
            if layer.name in self.state.selected:
                layers.append(layer)

        layers.sort(key=lambda x: x.overlay == 'mixed')
        return layers

    def currentStandaloneLayer(self):
        for layer in self.state.layers:
            if layer.name in self.state.selected and layer.overlay == 'standalone':
                return layer

    def groupLayers(self):
        layers = {}
        for layer in self.state.layers:
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
        layers = self.state.layers
        if not layers:
            return []

        return [
            min(l.extent[0] for l in layers),
            min(l.extent[1] for l in layers),
            max(l.extent[2] for l in layers),
            max(l.extent[3] for l in layers)
        ]

    def boundaries(self):
        import json
        from tafor import conf

        try:
            boundary = json.loads(conf.firBoundary)
            if not isinstance(boundary, list):
                return []
        except Exception as e:
            return []

        return boundary

    def projection(self):
        from pyproj import Proj
        from tafor import conf

        try:
            proj = Proj(conf.projection)

        except Exception as e:
            conf.projection = '+proj=webmerc +datum=WGS84'
            proj = Proj('+proj=webmerc +datum=WGS84')

        return proj

    def refreshLayers(self):
        self.event.layerRefreshed.emit()


class TafService(QObject, StateProxyMixin):
    fields = ['message']

    def __init__(self, state, event):
        super().__init__()
        self.state = state
        self.event = event

    def setState(self, values):
        oldClockRemind = self.state.clockRemind
        for key, value in values.items():
            if hasattr(self.state, key):
                setattr(self.state, key, value)

        if self.state.clockRemind and not oldClockRemind:
            self.event.tafReminded.emit()

        self.event.tafStateChanged.emit(self.state)

    @property
    def spec(self):
        from tafor import conf

        index = conf.tafSpec or 0
        if int(index) == 1:
            return 'ft24'
        if int(index) == 2:
            return 'ft30'
        return 'fc'

    def needReminded(self):
        return self.state.clockRemind and self.state.message is None

    def hasExpired(self):
        return self.state.hasExpired

    def period(self):
        return self.state.period


class SigmetService(QObject, StateProxyMixin):
    fields = ['entries']

    def __init__(self, state, event):
        super().__init__()
        self.state = state
        self.event = event

    def add(self, uuid, text, time):
        self.state.entries[uuid] = {'text': text, 'time': time}
        self.event.sigmetStateChanged.emit(self.state)

    def update(self, uuid, time):
        if uuid in self.state.entries:
            self.state.entries[uuid]['time'] = time
            self.event.sigmetStateChanged.emit(self.state)

    def remove(self, uuid):
        self.state.entries.pop(uuid, None)
        self.event.sigmetStateChanged.emit(self.state)

    def outdate(self):
        now = datetime.datetime.utcnow()
        outdates = []
        for uuid, value in self.state.entries.items():
            if (
                value['time'] - datetime.timedelta(minutes=self.state.aheadMinutes)
                < now
            ):
                outdates.append(
                    {'uuid': uuid, 'text': value['text'], 'time': value['time']}
                )
        return outdates


class NotificationService(QObject):
    def __init__(self, state, event):
        super().__init__()
        self.state = state
        self.event = event

    def setState(self, values):
        oldMessage = self.state.message
        oldValidation = self.state.validation

        for key, value in values.items():
            if hasattr(self.state, key):
                setattr(self.state, key, value)

        if oldMessage != self.state.message or oldValidation != self.state.validation:
            self.state.created = datetime.datetime.utcnow()
            self.event.notificationStateChanged.emit(self.getMessageType())

    def clear(self):
        self.setState({'message': None})

    def getMessageType(self):
        message = self.state.message

        if not message:
            return 'UNKNOWN'

        if message.startswith('METAR'):
            return 'METAR'
        elif message.startswith('SPECI'):
            return 'SPECI'
        elif 'AIRMET' in message:
            return 'AIRMET'
        elif 'SIGMET' in message:
            return 'SIGMET'

        return 'UNKNOWN'

    def parser(self):
        from tafor import conf
        from tafor.utils import boolean, MetarParser, SigmetParser

        message = self.state.message

        if not message:
            return None

        msgType = self.getMessageType()

        if msgType in ['SIGMET', 'AIRMET']:
            return SigmetParser(message)

        if msgType in ['METAR', 'SPECI']:
            visHas5000 = boolean(conf.visHas5000)
            cloudHeightHas450 = boolean(conf.cloudHeightHas450)
            weakPrecipitationVerification = boolean(conf.weakPrecipitationVerification)
            return MetarParser(
                message,
                ignoreMetar=True,
                previous=self.state.previous,
                visHas5000=visHas5000,
                cloudHeightHas450=cloudHeightHas450,
                weakPrecipitationVerification=weakPrecipitationVerification,
            )

        return None

    def created(self):
        return self.state.created

    def validation(self):
        return self.state.validation

    def message(self):
        return self.state.message


class NotificationManager(QObject):
    def __init__(self, states, event):
        super().__init__()
        self.event = event
        self.metar = NotificationService(states.get('metar'), event)
        self.sigmet = NotificationService(states.get('sigmet'), event)


class OtherService(QObject, StateProxyMixin):
    fields = ['uuid', 'priority', 'address', 'message', 'created']

    def __init__(self, state, event):
        super().__init__()
        self.state = state
        self.event = event

    def setState(self, values):
        for key, value in values.items():
            if hasattr(self.state, key):
                setattr(self.state, key, value)
        self.state.created = datetime.datetime.utcnow()
        self.event.otherMessageChanged.emit()


class FlashService(QObject):
    def __init__(self, event):
        super().__init__()
        self.event = event

    def showSystemMessage(self, title, text, level='information'):
        self.event.systemMessage.emit(title, text, level)

    def showStatusbarMessage(self, text, timeout=5000):
        self.event.statusbarMessage.emit(text, timeout)

    def showEditorMessage(self, title, text):
        self.event.editorMessage.emit(title, text)

    def info(self, title, text):
        self.showSystemMessage(title, text)

    def warning(self, title, text):
        self.showSystemMessage(title, text, 'warning')

    def statusbar(self, text, timeout=5000):
        self.showStatusbarMessage(text, timeout)

    def editor(self, title, text):
        self.showEditorMessage(title, text)


class SerialLock:
    def __init__(self):
        self._locked = False

    @property
    def isBusy(self):
        return self._locked

    def lock(self):
        self._locked = True

    def release(self):
        self._locked = False


class EnvironManager:
    key = (
        '-----BEGIN PUBLIC KEY-----\n'
        'MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA2AZZfefXdgpvnWcV9xMf\n'
        'qlBqTS/8XZXq9BwFRpe0thoS3fER8s5fGKDWiOzO2I2PEwvahXyPny4hxHll7vF+\n'
        'lgd3dl0Z5BRslDGzSUe3/S2vqu4jAiyFmF3z8HZ9Jcr7BXi8yYUOr/LUfOP2gWK3\n'
        'GnORnWhBTb/llaGjN72yoJKJpKEbJYlrBJdsOyBrAeXbg1QNktOuqPf5toP/72qU\n'
        '2a/RRvpK9koSHMvhqd6ex5h+MHvcQZ759Fi1wxj5ChkB6BGgsHGR+7f49c92Gd4o\n'
        '2TKLicLL6vcidL4QkXdhRaZTJyd8pYI6Su+FUK7mcaBDpEaUl9xWupJnjsfKx1bf\n'
        'WQIDAQAB\n'
        '-----END PUBLIC KEY-----'
    )

    def __init__(self):
        self.exp = 0

    def environment(self):
        import platform
        from PyQt5.QtCore import QT_VERSION_STR
        from tafor import __version__

        if sys.platform != 'darwin':
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
            'revision': self.ghash(),
        }

    def ghash(self):
        if hasattr(sys, '_MEIPASS'):
            from tafor._environ import ghash

            return ghash
        else:
            from tafor.utils import gitRevisionHash

            return gitRevisionHash()

    def license(self, token=None):
        from tafor import conf
        from tafor.utils import verifyToken

        token = token or conf.license
        if not token:
            return {}

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
        from tafor import conf

        infos = {}
        if conf.airport:
            infos['airport'] = conf.airport
        if conf.firName:
            infos['fir'] = conf.firName[:4]
        return infos

    def hasPermission(self, reportType):
        if reportType == 'Trend':
            return True
        if reportType in ['TAF', 'Custom']:
            return 'airport' in self.license()
        if reportType in ['SIGMET', 'AIRMET']:
            return 'fir' in self.license()
        return False

    def bundlePath(self, relativePath):
        from tafor import root

        if hasattr(sys, '_MEIPASS'):
            base = sys._MEIPASS
        else:
            base = root
        return os.path.join(base, relativePath)

    def fixedFont(self):
        from PyQt5.QtGui import QFontDatabase

        return QFontDatabase.systemFont(QFontDatabase.FixedFont)


class AppContext:
    def __init__(self):
        # Shared event bus
        self.event = Event()

        # Create states
        messageState = MessageState()
        layerState = LayerState()
        tafState = TafState()
        sigmetState = SigmetState()
        otherState = OtherState()
        notificationStates = {
            'metar': NotificationState(expireMinutes=10),
            'sigmet': NotificationState(),
        }

        # Create services with injected state and event
        self.message = MessageService(messageState, self.event)
        self.layer = LayerService(layerState, self.event)
        self.taf = TafService(tafState, self.event)
        self.sigmet = SigmetService(sigmetState, self.event)
        self.other = OtherService(otherState, self.event)
        self.notification = NotificationManager(notificationStates, self.event)
        self.flash = FlashService(self.event)

        # Utilities
        self.serial = SerialLock()
        self.environ = EnvironManager()


# Global singleton
context = AppContext()
