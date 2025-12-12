from PyQt5.QtCore import QSettings


class ConfigItem:
    """Descriptor for configuration items"""
    
    def __init__(self, key, bindProperty=None):
        self.key = key
        self.bindProperty = bindProperty  # UI control binding name
        
    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        return instance.manager.get(self.key)
    
    def __set__(self, instance, value):
        instance.manager.set(self.key, value)


class AppConfig:
    """
    Application configuration
    Includes general settings, validation options, message configuration, 
    communication configuration, interface configuration, monitoring configuration, and layer configuration
    """
    
    def __init__(self, manager):
        self.manager = manager
    
    # General settings
    windowsStyle = ConfigItem('General/WindowsStyle', 'windowsStyle')
    communicationProtocol = ConfigItem('General/CommunicationProtocol', 'communicationProtocol')
    interfaceScaling = ConfigItem('General/InterfaceScaling', 'interfaceScaling')
    tafSpec = ConfigItem('General/TAFSpec', 'tafSpecification')
    closeToMinimize = ConfigItem('General/CloseToMinimize', 'closeToMinimize')
    debugMode = ConfigItem('General/Debug', 'debugMode')
    autoCompletionGroupTime = ConfigItem('General/AutoComletionGroupTime', 'autoComletionGroupTime')
    
    # Validation options
    visHas5000 = ConfigItem('Validation/VisHas5000', 'visHas5000')
    cloudHeightHas450 = ConfigItem('Validation/CloudHeightHas450', 'cloudHeightHas450')
    weakPrecipitationVerification = ConfigItem('Validation/WeakPrecipitationVerification', 'weakPrecipitationVerification')
    
    # Message configuration
    airport = ConfigItem('Message/Airport', 'airport')
    bulletinNumber = ConfigItem('Message/BulletinNumber', 'bulletinNumber')
    trendIdentifier = ConfigItem('Message/TrendIdentifier', 'trendIdentifier')
    weatherList = ConfigItem('Message/Weather', 'weatherList')
    weatherWithIntensityList = ConfigItem('Message/WeatherWithIntensity', 'weatherWithIntensityList')
    firName = ConfigItem('Message/FIRName', 'firName')
    
    # Communication configuration - Serial port settings
    port = ConfigItem('Communication/SerialPort', 'port')
    baudrate = ConfigItem('Communication/SerialBaudrate', 'baudrate')
    parity = ConfigItem('Communication/SerialParity', 'parity')
    bytesize = ConfigItem('Communication/SerialBytesize', 'bytesize')
    stopbits = ConfigItem('Communication/SerialStopbits', 'stopbits')
    
    # Communication configuration - AFTN settings
    channel = ConfigItem('Communication/Channel', 'channel')
    channelSequenceNumber = ConfigItem('Communication/ChannelSequenceNumber', 'channelSequenceNumber')
    channelSequenceLength = ConfigItem('Communication/ChannelSequenceLength', 'channelSequenceLength')
    maxSendAddress = ConfigItem('Communication/MaxSendAddress', 'maxSendAddress')
    originatorAddress = ConfigItem('Communication/OriginatorAddress', 'originatorAddress')
    tafAddress = ConfigItem('Communication/TAFAddress', 'tafAddress')
    trendAddress = ConfigItem('Communication/TrendAddress', 'trendAddress')
    airmetAddress = ConfigItem('Communication/AIRMETAddress', 'airmetAddress')
    sigmetAddress = ConfigItem('Communication/SIGMETAddress', 'sigmetAddress')
    
    # Communication configuration - FTP settings
    ftpHost = ConfigItem('Communication/FTPHost', 'ftpHost')
    
    # Interface configuration
    rpc = ConfigItem('Interface/RPC', 'serviceGroup')
    messageUrl = ConfigItem('Interface/MessageURL', 'messageURL')
    layerUrl = ConfigItem('Interface/LayerURL', 'layerURL')
    
    # Monitoring configuration
    delayMinutes = ConfigItem('Monitor/DelayMinutes', 'delayMinutes')
    alarmVolume = ConfigItem('Monitor/AlarmVolume', 'alarmVolume')
    remindTaf = ConfigItem('Monitor/RemindTAF', 'remindTaf')
    tafVolume = ConfigItem('Monitor/TAFVolume', 'tafVolume')
    remindTrend = ConfigItem('Monitor/RemindTrend', 'remindTrend')
    trendVolume = ConfigItem('Monitor/TrendVolume', 'trendVolume')
    remindSigmet = ConfigItem('Monitor/RemindSIGMET', 'remindSigmet')
    sigmetVolume = ConfigItem('Monitor/SIGMETVolume', 'sigmetVolume')
    
    # Layer configuration
    projection = ConfigItem('Layer/Projection', 'projection')
    firBoundary = ConfigItem('Layer/FIRBoundary', 'firBoundary')


class ConfigManager:
    """Configuration manager"""
    
    def __init__(self, organization, application):
        self.settings = QSettings(organization, application)
        
    def get(self, key):
        """Get configuration value"""
        value = self.settings.value(key)
        return value
    
    def set(self, key, value):
        """Set configuration value"""
        self.settings.setValue(key, value)


class ConfigRegistry:
    """Configuration registry with composition pattern"""
    
    def __init__(self, manager, cls=AppConfig):
        self._manager = manager
        self._config = cls(manager)

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
            if isinstance(attr, ConfigItem):
                yield attr
