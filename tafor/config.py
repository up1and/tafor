import json

from PyQt5.QtCore import QSettings


class ConfigItem:
    """Descriptor for configuration items"""
    
    def __init__(self, key, default=None, bindProperty=None):
        self.key = key
        self.default = default
        self.bindProperty = bindProperty  # UI control binding name
        self.value = None
        
    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        return instance.manager.get(self.key, self.default)
    
    def __set__(self, instance, value):
        instance.manager.set(self.key, value)

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
    windowsStyle = ConfigItem('General/WindowsStyle', default='System', bindProperty='windowsStyle')
    communicationProtocol = ConfigItem('General/CommunicationProtocol', default='AFTN', bindProperty='communicationProtocol')
    interfaceScaling = ConfigItem('General/InterfaceScaling', default=0, bindProperty='interfaceScaling')
    tafSpec = ConfigItem('General/TAFSpec', default=0, bindProperty='tafSpecification')
    closeToMinimize = ConfigItem('General/CloseToMinimize', default=True, bindProperty='closeToMinimize')
    debugMode = ConfigItem('General/Debug', default=False, bindProperty='debugMode')
    autoCompletionGroupTime = ConfigItem('General/AutoComletionGroupTime', default=True, bindProperty='autoComletionGroupTime')
    
    # Validation options
    visHas5000 = ConfigItem('Validation/VisHas5000', default=False, bindProperty='visHas5000')
    cloudHeightHas450 = ConfigItem('Validation/CloudHeightHas450', default=False, bindProperty='cloudHeightHas450')
    weakPrecipitationVerification = ConfigItem('Validation/WeakPrecipitationVerification', default=False, bindProperty='weakPrecipitationVerification')
    
    # Message configuration
    airport = ConfigItem('Message/Airport', default='YUSO', bindProperty='airport')
    bulletinNumber = ConfigItem('Message/BulletinNumber', default='', bindProperty='bulletinNumber')
    trendIdentifier = ConfigItem('Message/TrendIdentifier', default='TRENDING', bindProperty='trendIdentifier')
    weatherList = ConfigItem('Message/Weather', default=[], bindProperty='weatherList')
    weatherWithIntensityList = ConfigItem('Message/WeatherWithIntensity', default=[], bindProperty='weatherWithIntensityList')
    firName = ConfigItem('Message/FIRName', default='SHANLON FIR', bindProperty='firName')
    
    # Communication configuration - Serial port settings
    port = ConfigItem('Communication/SerialPort', default='COM1', bindProperty='port')
    baudrate = ConfigItem('Communication/SerialBaudrate', default='9600', bindProperty='baudrate')
    parity = ConfigItem('Communication/SerialParity', default='NONE', bindProperty='parity')
    bytesize = ConfigItem('Communication/SerialBytesize', default='8', bindProperty='bytesize')
    stopbits = ConfigItem('Communication/SerialStopbits', default='1', bindProperty='stopbits')
    
    # Communication configuration - AFTN settings
    channel = ConfigItem('Communication/Channel', default='', bindProperty='channel')
    channelSequenceNumber = ConfigItem('Communication/ChannelSequenceNumber', default='1', bindProperty='channelSequenceNumber')
    channelSequenceLength = ConfigItem('Communication/ChannelSequenceLength', default='4', bindProperty='channelSequenceLength')
    maxSendAddress = ConfigItem('Communication/MaxSendAddress', default='10', bindProperty='maxSendAddress')
    originatorAddress = ConfigItem('Communication/OriginatorAddress', default='', bindProperty='originatorAddress')
    tafAddress = ConfigItem('Communication/TAFAddress', default='', bindProperty='tafAddress')
    trendAddress = ConfigItem('Communication/TrendAddress', default='', bindProperty='trendAddress')
    airmetAddress = ConfigItem('Communication/AIRMETAddress', default='', bindProperty='airmetAddress')
    sigmetAddress = ConfigItem('Communication/SIGMETAddress', default='', bindProperty='sigmetAddress')
    
    # Communication configuration - FTP settings
    ftpHost = ConfigItem('Communication/FTPHost', default='', bindProperty='ftpHost')
    
    # Interface configuration
    rpc = ConfigItem('Interface/RPC', default=False, bindProperty='serviceGroup')
    messageUrl = ConfigItem('Interface/MessageURL', default='', bindProperty='messageURL')
    layerUrl = ConfigItem('Interface/LayerURL', default='', bindProperty='layerURL')
    authToken = ConfigItem('Interface/AuthToken', default='VGhlIFZveWFnZSBvZiB0aGUgTW9vbg==', bindProperty='token')
    
    # Monitoring configuration
    delayMinutes = ConfigItem('Monitor/DelayMinutes', default='5', bindProperty='delayMinutes')
    alarmVolume = ConfigItem('Monitor/AlarmVolume', default=30, bindProperty='alarmVolume')
    remindTaf = ConfigItem('Monitor/RemindTAF', default=True, bindProperty='remindTaf')
    tafVolume = ConfigItem('Monitor/TAFVolume', default=100, bindProperty='tafVolume')
    remindTrend = ConfigItem('Monitor/RemindTrend', default=True, bindProperty='remindTrend')
    trendVolume = ConfigItem('Monitor/TrendVolume', default=100, bindProperty='trendVolume')
    remindSigmet = ConfigItem('Monitor/RemindSIGMET', default=True, bindProperty='remindSigmet')
    sigmetVolume = ConfigItem('Monitor/SIGMETVolume', default=100, bindProperty='sigmetVolume')
    
    # Layer configuration
    projection = ConfigItem('Layer/Projection', default='+proj=webmerc +datum=WGS84', bindProperty='projection')
    firBoundary = ConfigItem('Layer/FIRBoundary', default='[]', bindProperty='firBoundary')

    sigmetEnabled = ConfigItem('General/Sigmet', default=False)
    license = ConfigItem('License', default='')


class ConfigManager:
    """Configuration manager"""
    
    def __init__(self, organization, application):
        self.settings = QSettings(organization, application)
        
    def get(self, key, default=None):
        """Get configuration value"""
        value = self.settings.value(key)
        if value is None:
            return default
        
        # Convert the value to the type of the default value
        if default is not None:
            if isinstance(default, bool):
                return str(value).lower() in ('true', 't', 'yes', 'y', '1', 'on')
            
            if isinstance(default, int):
                return int(value)
            
            if isinstance(default, (list, dict)):
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return default

        return value
    
    def set(self, key, value):
        """Set configuration value"""
        self.settings.setValue(key, value)


class ConfigRegistry:
    """Configuration registry with composition pattern"""
    
    def __init__(self, manager, cls=AppConfig):
        self._manager = manager
        self._config = cls(manager)

    @property
    def app(self):
        return self._config

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
    
    def __getitem__(self, key):
        return self._manager.get(key)
    
    def __setitem__(self, key, value):
        self._manager.set(key, value)
    
    def __iter__(self):
        for attrName in dir(self._config.__class__):
            attr = getattr(self._config.__class__, attrName)
            if isinstance(attr, ConfigItem) and attr.bindProperty:
                attr.value = getattr(self._config, attrName)
                yield attr
