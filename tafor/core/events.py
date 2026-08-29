"""Callback-based signals used by core services to notify the ui layer."""


class Signal:
    """A list of handlers with Qt-like connect/emit verbs.

    emit() invokes handlers synchronously on the calling thread, so state
    changes must be applied on the GUI thread; background workers hand
    their payload back to the GUI thread before calling context services.
    """

    def __init__(self):
        self.handlers = []

    def connect(self, handler):
        self.handlers.append(handler)

    def disconnect(self, handler):
        if handler in self.handlers:
            self.handlers.remove(handler)

    def emit(self, *args):
        for handler in list(self.handlers):
            handler(*args)


class Event:
    """Application-wide event bus."""

    def __init__(self):
        # Data changes
        self.layerChanged = Signal()        # emits the layer state
        self.remoteMessageChanged = Signal()
        self.currentSigmetChanged = Signal()
        self.notificationChanged = Signal()  # emits the message type

        # Triggers
        self.tafReminderTriggered = Signal()
        self.trendReloadRequested = Signal()
        self.layerRefreshRequested = Signal()
        self.otherMessageReceived = Signal()  # emits the transient Other instance from the api

        # UI messages
        self.systemMessage = Signal()       # emits title, text, level
        self.statusbarMessage = Signal()    # emits text, timeout
        self.editorMessage = Signal()       # emits title, text
