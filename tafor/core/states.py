import datetime

from PyQt5.QtCore import QObject, pyqtSignal


class RemoteMessageState:
    def __init__(self):
        self.messages = {}


class CurrentSigmetState:
    def __init__(self):
        self.sigmets = []


class LayerState:
    def __init__(self):
        self.layers = []
        self.showSigmet = True
        self.trimShapes = True
        self.layerExtend = []
        self.selected = []


class TafMonitorState:
    def __init__(self):
        self.period = ''
        self.message = None
        self.isExpired = False
        self.shouldRemind = False


class SigmetMonitorState:
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
    # Data changes
    layerChanged = pyqtSignal(object)
    remoteMessageChanged = pyqtSignal()
    currentSigmetChanged = pyqtSignal()
    notificationChanged = pyqtSignal(str)

    # Triggers
    tafReminderTriggered = pyqtSignal()
    layerRefreshRequested = pyqtSignal()
    otherMessageReceived = pyqtSignal()

    # UI messages
    systemMessage = pyqtSignal(str, str, str)
    statusbarMessage = pyqtSignal(str, int)
    editorMessage = pyqtSignal(str, str)


class StateProxyMixin:
    """Readonly Property Mixin"""
    fields = ['']

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        for field in cls.fields:
            getter = lambda self, f=field: getattr(self.state, f)
            setattr(cls, field, property(getter))


class RemoteMessageService(QObject):
    def __init__(self, state, event):
        super().__init__()
        self.state = state
        self.event = event

    def message(self):
        return self.state.messages

    def setState(self, values):
        if self.state.messages != values:
            self.state.messages = dict(values)
            self.event.remoteMessageChanged.emit()


class CurrentSigmetService(QObject):
    def __init__(self, state, event):
        super().__init__()
        self.state = state
        self.event = event

    def setState(self, values):
        oldSigmets = [s.text for s in self.state.sigmets]
        newSigmets = [s.text for s in values]

        if set(oldSigmets) != set(newSigmets):
            self.state.sigmets = list(values)
            self.event.currentSigmetChanged.emit()

    def filterSigmets(self, sigmetFilter=None):
        from tafor.core.utils.query import SigmetFilter

        sigmetFilter = sigmetFilter or SigmetFilter()

        if sigmetFilter.includeCancelled:
            candidates = self.state.sigmets
        else:
            candidates = [s for s in self.state.sigmets if not s.isCnl()]

        typeCodes = sigmetFilter.typeCodes()
        if typeCodes:
            candidates = [s for s in candidates if s.type in typeCodes]

        return candidates


class LayerService(QObject, StateProxyMixin):
    fields = ['selected', 'showSigmet', 'trimShapes']

    def __init__(self, state, event):
        super().__init__()
        self.state = state
        self.event = event

    def setLayer(self, layerData):
        from tafor.core.utils.time import Layer

        layers = [Layer(data) for data in layerData]
        oldNames = [l.name for l in self.state.layers]
        newNames = [l.name for l in layers]

        self.state.layers = layers
        if oldNames != newNames:
            self.event.layerChanged.emit(self.state)

    def setState(self, values):
        normalized = {}
        for key, value in values.items():
            if key == 'selected':
                normalized[key] = list(value)
            if key in ['showSigmet', 'trimShapes']:
                normalized[key] = bool(value)

        if any(
            getattr(self.state, key) != value
            for key, value in normalized.items()
        ):
            for key, value in normalized.items():
                setattr(self.state, key, value)

            self.event.layerChanged.emit(self.state)

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
        from tafor.core.globals import conf

        try:
            boundary = json.loads(conf.firBoundary)
            if not isinstance(boundary, list):
                return []
        except Exception as e:
            return []

        return boundary

    def projection(self):
        from pyproj import Proj
        from tafor.core.globals import conf

        try:
            proj = Proj(conf.projection)

        except Exception as e:
            conf.projection = '+proj=webmerc +datum=WGS84'
            proj = Proj('+proj=webmerc +datum=WGS84')

        return proj

    def refreshLayers(self):
        self.event.layerRefreshRequested.emit()


class TafMonitorService(QObject, StateProxyMixin):
    fields = ['message']

    def __init__(self, state, event):
        super().__init__()
        self.state = state
        self.event = event

    def setState(self, values):
        oldShouldRemind = self.state.shouldRemind
        for key, value in values.items():
            if hasattr(self.state, key):
                setattr(self.state, key, value)

        if self.state.shouldRemind and not oldShouldRemind:
            self.event.tafReminderTriggered.emit()

    @property
    def spec(self):
        from tafor.core.globals import conf

        index = conf.tafSpec or 0
        if int(index) == 1:
            return 'ft24'
        if int(index) == 2:
            return 'ft30'
        return 'fc'

    def shouldRemind(self):
        return self.state.shouldRemind and self.state.message is None

    def isExpired(self):
        return self.state.isExpired

    def period(self):
        return self.state.period


class SigmetMonitorService(QObject, StateProxyMixin):
    fields = ['entries']

    def __init__(self, state, event):
        super().__init__()
        self.state = state
        self.event = event

    def add(self, uuid, text, time):
        self.state.entries[uuid] = {'text': text, 'time': time}

    def update(self, uuid, time):
        if uuid in self.state.entries:
            self.state.entries[uuid]['time'] = time

    def remove(self, uuid):
        self.state.entries.pop(uuid, None)

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
            self.event.notificationChanged.emit(self.getMessageType())

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
        from tafor.core.globals import conf
        from tafor.core.parsers.metar import MetarParser
        from tafor.core.parsers.sigmet import SigmetParser
        from tafor.core.utils.common import boolean

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
        self.event.otherMessageReceived.emit()


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


class AppContext:
    def __init__(self):
        from tafor.core.services import AppInfoService, LicenseService, ResourceService, SerialLock

        # Shared event bus
        self.event = Event()

        # Create states
        remoteMessageState = RemoteMessageState()
        currentSigmetState = CurrentSigmetState()
        layerState = LayerState()
        tafMonitorState = TafMonitorState()
        sigmetMonitorState = SigmetMonitorState()
        otherState = OtherState()
        notificationStates = {
            'metar': NotificationState(expireMinutes=10),
            'sigmet': NotificationState(),
        }

        # Create services with injected state and event
        self.message = RemoteMessageService(remoteMessageState, self.event)
        self.current = CurrentSigmetService(currentSigmetState, self.event)
        self.layer = LayerService(layerState, self.event)
        self.taf = TafMonitorService(tafMonitorState, self.event)
        self.sigmet = SigmetMonitorService(sigmetMonitorState, self.event)
        self.other = OtherService(otherState, self.event)
        self.notification = NotificationManager(notificationStates, self.event)
        self.flash = FlashService(self.event)

        # Utilities
        self.serial = SerialLock()
        self.info = AppInfoService()
        self.license = LicenseService()
        self.resource = ResourceService()


# Global singleton
context = AppContext()
