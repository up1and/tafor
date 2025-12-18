import json
import logging

from PyQt5.QtCore import QSettings, QObject, pyqtSignal

logger = logging.getLogger('tafor.config')

def validateFirBoundary(value):
    import shapely
    try:
        boundaries = json.loads(value)
        boundary = shapely.geometry.Polygon(boundaries)
        return boundary.is_valid and not boundary.is_empty
    except ValueError:
        return False

class ConfigItem:
    """Descriptor for configuration items"""
    
    def __init__(self, key, default='', scope='immediate', bindProperty=None, group=None, validator=None):
        self.key = key
        self.default = default
        self.scope = scope
        self.bindProperty = bindProperty  # UI control binding name
        self.validator = validator
        self.value = None
        self.group = group or []
        
    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        return instance.manager.get(self.key, self.default)
    
    def __set__(self, instance, value):
        if self.validator and not self.validator(value):
            raise ValueError(f'Invalid value for {self.key}: {value}')

        currentValue = instance.manager.get(self.key, self.default)
        instance.manager.set(self.key, value)

        if type(value) != type(currentValue) and isinstance(currentValue, (list, dict)):
            value = json.loads(value)

        if currentValue != value:
            instance.manager.forwardChange(self.key, value, self.scope)
            logger.debug(f'{self.key} changed: {currentValue!r} -> {value!r}')

    def __repr__(self):
        return f'Config<{self.key}>'


class AppConfig:
    """
    Application configuration
    Includes general settings, validation options, message configuration, 
    communication configuration, interface configuration, monitoring configuration, and layer configuration
    """
    
    def __init__(self, manager):
        self.manager = manager
    
    # General settings
    windowsStyle = ConfigItem(
        'General/WindowsStyle',
        default='System',
        scope='restart',
        bindProperty='windowsStyle'
    )
    communicationProtocol = ConfigItem(
        'General/CommunicationProtocol',
        default='AFTN',
        scope='reload',
        bindProperty='communicationProtocol'
    )
    interfaceScaling = ConfigItem(
        'General/InterfaceScaling',
        default=0,
        scope='restart',
        bindProperty='interfaceScaling'
    )
    tafSpec = ConfigItem(
        'General/TAFSpec',
        default=0,
        scope='restart',
        bindProperty='tafSpecification'
    )
    closeToMinimize = ConfigItem(
        'General/CloseToMinimize',
        default=True,
        bindProperty='closeToMinimize'
    )
    debugMode = ConfigItem(
        'General/Debug',
        default=False,
        scope='restart',
        bindProperty='debugMode'
    )
    autoCompletionGroupTime = ConfigItem(
        'General/AutoComletionGroupTime',
        default=True,
        bindProperty='autoComletionGroupTime'
    )
    
    # Validation options
    visHas5000 = ConfigItem(
        'Validation/VisHas5000',
        default=False,
        bindProperty='visHas5000'
    )
    cloudHeightHas450 = ConfigItem(
        'Validation/CloudHeightHas450',
        default=False,
        bindProperty='cloudHeightHas450'
    )
    weakPrecipitationVerification = ConfigItem(
        'Validation/WeakPrecipitationVerification',
        default=False,
        bindProperty='weakPrecipitationVerification'
    )
    
    # Message configuration
    airport = ConfigItem(
        'Message/Airport',
        default='YUSO',
        scope='reload',
        bindProperty='airport',
        group=['taf', 'sigmet']
    )
    bulletinNumber = ConfigItem(
        'Message/BulletinNumber',
        scope='reload',
        bindProperty='bulletinNumber',
        group=['taf', 'sigmet']
    )
    trendIdentifier = ConfigItem(
        'Message/TrendIdentifier',
        default='TRENDING',
        scope='reload',
        bindProperty='trendIdentifier',
        group=['trend']
    )
    weatherList = ConfigItem(
        'Message/Weather',
        default=[],
        scope='restart',
        bindProperty='weatherList'
    )
    weatherWithIntensityList = ConfigItem(
        'Message/WeatherWithIntensity',
        default=[],
        scope='restart',
        bindProperty='weatherWithIntensityList'
    )
    firName = ConfigItem(
        'Message/FIRName',
        default='SHANLON FIR',
        scope='reload',
        bindProperty='firName',
        group=['sigmet']
    )
    
    # Communication configuration - Serial port settings
    port = ConfigItem(
        'Communication/SerialPort',
        default='COM1',
        bindProperty='port',
        group=['core']
    )
    baudrate = ConfigItem(
        'Communication/SerialBaudrate',
        default='9600',
        bindProperty='baudrate',
        group=['core']
    )
    parity = ConfigItem(
        'Communication/SerialParity',
        default='NONE',
        bindProperty='parity',
        group=['core']
    )
    bytesize = ConfigItem(
        'Communication/SerialBytesize',
        default='8',
        bindProperty='bytesize',
        group=['core']
    )
    stopbits = ConfigItem(
        'Communication/SerialStopbits',
        default='1',
        bindProperty='stopbits',
        group=['core']
    )
    
    # Communication configuration - AFTN settings
    channel = ConfigItem(
        'Communication/Channel',
        scope='reload',
        bindProperty='channel',
        group=['core']
    )
    channelSequenceNumber = ConfigItem(
        'Communication/ChannelSequenceNumber',
        default='1',
        scope='reload',
        bindProperty='channelSequenceNumber',
        group=['core']
    )
    channelSequenceLength = ConfigItem(
        'Communication/ChannelSequenceLength',
        default='4',
        scope='reload',
        bindProperty='channelSequenceLength',
        group=['core']
    )
    fileSequenceNumber = ConfigItem(
        'Communication/FileSequenceNumber',
        default='1',
        scope='reload',
        group=['core']
    )
    maxSendAddress = ConfigItem(
        'Communication/MaxSendAddress',
        default='10',
        scope='reload',
        bindProperty='maxSendAddress',
        group=['core']
    )
    originatorAddress = ConfigItem(
        'Communication/OriginatorAddress',
        scope='reload',
        bindProperty='originatorAddress',
        group=['core']
    )
    tafAddress = ConfigItem(
        'Communication/TAFAddress',
        scope='reload',
        bindProperty='tafAddress',
        group=['taf']
    )
    trendAddress = ConfigItem(
        'Communication/TrendAddress',
        scope='reload',
        bindProperty='trendAddress',
        group=['trend']
    )
    airmetAddress = ConfigItem(
        'Communication/AIRMETAddress',
        scope='reload',
        bindProperty='airmetAddress',
        group=['sigmet']
    )
    sigmetAddress = ConfigItem(
        'Communication/SIGMETAddress',
        scope='reload',
        bindProperty='sigmetAddress',
        group=['sigmet']
    )
    
    # Communication configuration - FTP settings
    ftpHost = ConfigItem(
        'Communication/FTPHost',
        bindProperty='ftpHost'
    )

    # Interface configuration
    rpc = ConfigItem(
        'Interface/RPC',
        default=False,
        scope='restart',
        bindProperty='serviceGroup'
    )
    messageUrl = ConfigItem(
        'Interface/MessageURL',
        bindProperty='messageURL'
    )
    layerUrl = ConfigItem(
        'Interface/LayerURL',
        bindProperty='layerURL'
    )
    authToken = ConfigItem(
        'Interface/AuthToken',
        default='VGhlIFZveWFnZSBvZiB0aGUgTW9vbg==',
        bindProperty='token'
    )
    
    # Monitoring configuration
    delayMinutes = ConfigItem(
        'Monitor/DelayMinutes',
        default='5',
        bindProperty='delayMinutes'
    )
    alarmVolume = ConfigItem(
        'Monitor/AlarmVolume',
        default=30,
        bindProperty='alarmVolume'
    )
    remindTaf = ConfigItem(
        'Monitor/RemindTAF',
        default=True,
        bindProperty='remindTaf'
    )
    tafVolume = ConfigItem(
        'Monitor/TAFVolume',
        default=100,
        bindProperty='tafVolume'
    )
    remindTrend = ConfigItem(
        'Monitor/RemindTrend',
        default=True,
        bindProperty='remindTrend'
    )
    trendVolume = ConfigItem(
        'Monitor/TrendVolume',
        default=100,
        bindProperty='trendVolume'
    )
    remindSigmet = ConfigItem(
        'Monitor/RemindSIGMET',
        default=True,
        bindProperty='remindSigmet'
    )
    sigmetVolume = ConfigItem(
        'Monitor/SIGMETVolume',
        default=100,
        bindProperty='sigmetVolume'
    )
    
    # Layer configuration
    projection = ConfigItem(
        'Layer/Projection',
        default='+proj=webmerc +datum=WGS84',
        scope='restart',
        bindProperty='projection'
    )
    firBoundary = ConfigItem(
        'Layer/FIRBoundary',
        default='[]',
        scope='restart',
        bindProperty='firBoundary',
        validator=validateFirBoundary,
        group=['sigmet']
    )

    sigmetEnabled = ConfigItem('General/Sigmet', default=False)
    license = ConfigItem('License')
    unit = ConfigItem('General/Unit', default='metric')
    codec = ConfigItem('Communication/Codec', default='ASCII')

class ConfigManager(QObject):
    """Configuration manager"""

    configChanged = pyqtSignal(str, object, str)  # (key, value, scope)
    
    def __init__(self, organization, application):
        super().__init__()
        self.settings = QSettings(organization, application)
        
    def get(self, key, default=None):
        """Get configuration value"""
        value = self.settings.value(key)
        if value is None:
            return default
        
        # Convert the value to the type of the default value
        if default is not None and type(default) != type(value):
            if isinstance(default, bool):
                return str(value).lower() in ('true', 't', 'yes', 'y', '1', 'on')
            
            if isinstance(default, int):
                return int(value)
            
            if isinstance(default, str):
                return str(value)
            
            if isinstance(default, (list, dict)):
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return default

        return value
    
    def set(self, key, value):
        """Set configuration value"""
        self.settings.setValue(key, value)

    def forwardChange(self, key, value, scope):
        """Receive notification from ConfigItem and forward via signal"""
        self.configChanged.emit(key, value, scope)


class ConfigRegistry(QObject):
    """Configuration registry with composition pattern"""

    reloadRequired = pyqtSignal()
    restartRequired = pyqtSignal()
    
    def __init__(self, manager, cls=AppConfig):
        super().__init__()
        self._manager = manager
        self._config = cls(manager)
        # List to store pending changes as (key, value, scope) tuples
        self._pending = []

        self._manager.configChanged.connect(self.handleChange)

    def __getattr__(self, name):
        if hasattr(self._config, name):
            return getattr(self._config, name)
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
    
    def __setattr__(self, name, value):
        if name.startswith('_'):
            # Set private attributes directly
            super().__setattr__(name, value)
        elif hasattr(self._config, name):
            setattr(self._config, name, value)
        else:
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def get(self, name):
        return getattr(self._config, name)
    
    def set(self, name, value):
        setattr(self._config, name, value)
    
    def __iter__(self):
        for attr in dir(self._config.__class__):
            item = getattr(self._config.__class__, attr)
            if isinstance(item, ConfigItem) and item.bindProperty:
                item.value = getattr(self._config, attr)
                yield attr, item

    def handleChange(self, key, value, scope):
        """Store configuration changes"""
        if scope in ('reload', 'restart'):
            self._pending.append((key, value, scope))

    def emit(self):
        """Emit signals for all pending changes and clear the list"""
        hasReload = any(scope == 'reload' for _, _, scope in self._pending)
        hasRestart = any(scope == 'restart' for _, _, scope in self._pending)
        
        # Emit signals if needed
        if hasReload:
            self.reloadRequired.emit()
        
        if hasRestart:
            self.restartRequired.emit()

        self._pending.clear()

    def checkCompleteness(self, name):
        """Check if required configuration items are set"""
        groupsToCheck = {name}
        if name in ['taf', 'sigmet', 'trend']:
            groupsToCheck = {'core', name}

        for _, item in self:
            groups = set(item.group)
            if groups.intersection(groupsToCheck) and not item.value:
                return False
        return True
