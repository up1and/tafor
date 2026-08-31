import datetime

from tafor.core.events import Event


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
    def __init__(self):
        self.message = None
        self.validation = False
        self.created = datetime.datetime.utcnow()
        self.previous = ''


class StateProxyMixin:
    """Readonly Property Mixin"""
    fields = ['']

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        for field in cls.fields:
            getter = lambda self, f=field: getattr(self.state, f)
            setattr(cls, field, property(getter))


class RemoteMessageService:
    def __init__(self, state, event):
        self.state = state
        self.event = event

    def message(self):
        return self.state.messages

    def setState(self, values):
        if self.state.messages != values:
            self.state.messages = dict(values)
            self.event.remoteMessageChanged.emit()


class CurrentSigmetService:
    def __init__(self, state, event):
        self.state = state
        self.event = event

    def setState(self, values):
        oldSigmets = [s.text for s in self.state.sigmets]
        newSigmets = [s.text for s in values]

        if set(oldSigmets) != set(newSigmets):
            self.state.sigmets = list(values)
            self.event.currentSigmetChanged.emit()

    def filterSigmets(self, sigmetFilter=None):
        from tafor.core.repositories import SigmetFilter

        sigmetFilter = sigmetFilter or SigmetFilter()

        if sigmetFilter.includeCancelled:
            candidates = self.state.sigmets
        else:
            candidates = [s for s in self.state.sigmets if not s.isCnl()]

        designators = sigmetFilter.designators()
        if designators:
            candidates = [s for s in candidates if s.type in designators]

        return candidates


class LayerService(StateProxyMixin):
    fields = ['selected', 'showSigmet', 'trimShapes']

    def __init__(self, state, event, conf):
        self.state = state
        self.event = event
        self.conf = conf

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
        boundary = self.conf.firBoundary
        if not isinstance(boundary, list):
            return []

        return boundary

    def projection(self):
        from pyproj import Proj

        try:
            proj = Proj(self.conf.projection)

        except Exception as e:
            self.conf.projection = '+proj=webmerc +datum=WGS84'
            proj = Proj('+proj=webmerc +datum=WGS84')

        return proj

    def refreshLayers(self):
        self.event.layerRefreshRequested.emit()


class TafMonitorService(StateProxyMixin):
    fields = ['message']

    def __init__(self, state, event, conf):
        self.state = state
        self.event = event
        self.conf = conf

    def setState(self, values):
        oldShouldRemind = self.state.shouldRemind
        for key, value in values.items():
            if hasattr(self.state, key):
                setattr(self.state, key, value)

        if self.state.shouldRemind and not oldShouldRemind:
            self.event.tafReminderTriggered.emit()

    @property
    def spec(self):
        index = self.conf.tafSpec or 0
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


class SigmetMonitorService(StateProxyMixin):
    fields = ['entries']

    def __init__(self, state, event):
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

    def updateReminders(self, message):
        """Align reminders with a sent message: a cancel drops the matching
        reminder, anything else adds one expiring when the message expires."""
        sig = message.parser()
        if message.isCnl():
            cancelSequence = sig.cancelSequence()
            for uuid, value in list(self.state.entries.items()):
                parser = value['text']
                sequence = parser.sequence(), parser.validTime()
                if cancelSequence == sequence:
                    self.remove(uuid=uuid)
        else:
            self.add(uuid=message.uuid, text=sig, time=message.expired())


class NotificationService:
    def __init__(self, state, event, conf):
        self.state = state
        self.event = event
        self.conf = conf

    def setState(self, values):
        oldMessage = self.state.message
        oldValidation = self.state.validation

        for key, value in values.items():
            if hasattr(self.state, key):
                setattr(self.state, key, value)

        if oldMessage != self.state.message or oldValidation != self.state.validation:
            self.state.created = datetime.datetime.utcnow()
            self.event.notificationChanged.emit(self.category())

    def clear(self):
        self.setState({'message': None})

    def category(self):
        message = self.state.message

        if not message:
            return 'CUSTOM'

        if message.startswith('METAR'):
            return 'METAR'
        elif message.startswith('SPECI'):
            return 'SPECI'
        elif 'AIRMET' in message:
            return 'AIRMET'
        elif 'SIGMET' in message:
            return 'SIGMET'

        return 'CUSTOM'

    def parser(self):
        from tafor.core.parsers.metar import MetarParser
        from tafor.core.parsers.sigmet import SigmetParser

        message = self.state.message

        if not message:
            return None

        category = self.category()

        if category in ['SIGMET', 'AIRMET']:
            return SigmetParser(message)

        if category in ['METAR', 'SPECI']:
            return MetarParser(
                message,
                ignoreMetar=True,
                previous=self.state.previous,
                visHas5000=self.conf.visHas5000,
                cloudHeightHas450=self.conf.cloudHeightHas450,
                weakPrecipitationVerification=self.conf.weakPrecipitationVerification,
            )

        return None

    def created(self):
        return self.state.created

    def validation(self):
        return self.state.validation

    def message(self):
        return self.state.message


class NotificationManager:
    def __init__(self, states, event, conf):
        self.event = event
        self.metar = NotificationService(states.get('metar'), event, conf)
        self.sigmet = NotificationService(states.get('sigmet'), event, conf)


class FlashService:
    def __init__(self, event):
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
    def __init__(self, conf):
        from tafor.core.services import LicenseService, SerialLock

        # Shared event bus
        self.event = Event()

        # Create states
        remoteMessageState = RemoteMessageState()
        currentSigmetState = CurrentSigmetState()
        layerState = LayerState()
        tafMonitorState = TafMonitorState()
        sigmetMonitorState = SigmetMonitorState()
        notificationStates = {
            'metar': NotificationState(),
            'sigmet': NotificationState(),
        }

        # Create services with injected state, event and config
        self.message = RemoteMessageService(remoteMessageState, self.event)
        self.current = CurrentSigmetService(currentSigmetState, self.event)
        self.layer = LayerService(layerState, self.event, conf)
        self.taf = TafMonitorService(tafMonitorState, self.event, conf)
        self.sigmet = SigmetMonitorService(sigmetMonitorState, self.event)
        self.notification = NotificationManager(notificationStates, self.event, conf)
        self.flash = FlashService(self.event)

        # Utilities
        self.serial = SerialLock()
        self.license = LicenseService(conf)


def createContext(conf):
    """Build an AppContext over the given config."""
    return AppContext(conf)
