class MockConfig(object):

    config = {
        'General/Sigmet': 'true',
        'General/WindowsStyle': 'System',
        'General/CommunicationProtocol': 'AFTN',
        'General/InterfaceScaling': 0,
        'General/TAFSpec': 1,
        'General/CloseToMinimize': 'true',
        'General/Debug': 'true',
        'General/AutoComletionGroupTime': 'true',
        'Validation/VisHas5000': 'false',
        'Validation/CloudHeightHas450': 'true',
        'Validation/WeakPrecipitationVerification': 'false',
        'Message/Airport': 'YUSO',
        'Message/BulletinNumber': 'NT36',
        'Message/TrendIdentifier': 'TRENDING',
        'Message/Weather': '["FG", "FU", "HZ", "TS", "NSW", "MIFG", "BCFG", "PRFG", "BR BCFG"]',
        'Message/WeatherWithIntensity': '["DZ", "RA", "TSRA", "TSGR"]',
        'Communication/SerialPort': 'COM1',
        'Communication/SerialBaudrate': '2400',
        'Communication/SerialParity': 'NONE',
        'Communication/SerialBytesize': '8',
        'Communication/SerialStopbits': '1',
        'Communication/Channel': 'YMC',
        'Communication/ChannelSequenceNumber': '1',
        'Communication/ChannelSequenceLength': '4',
        'Communication/MaxSendAddress': '21',
        'Communication/OriginatorAddress': 'YUSOYMYX',
        'Communication/TAFAddress': 'YUSOYMYX',
        'Communication/TrendAddress': 'YUSOYMYX',
        'Communication/FTPHost': 'ftp://speedtest.tele2.net/upload',
        'Interface/RPC': 'true',
        'Interface/MessageURL': 'http://127.0.0.1:8000/messages/yuso',
        'Monitor/DelayMinutes': '30',
        'Monitor/AlarmVolume': 60,
        'Monitor/RemindTAF': 'true',
        'Monitor/TAFVolume': 60,
        'Monitor/RemindTrend': 'true',
        'Monitor/TrendVolume': 60,
        'Message/FIRName': 'YUDD SHANLON FIR',
        'Communication/AIRMETAddress': 'YXXXYMYX',
        'Communication/SIGMETAddress': 'EGXXMASI KWXXYMYX NFXXYPYX RCXXYMYX RCXXZQZX RJXXYMYX RJXXZQZX RJUUYMYX RKXXZQZX RKXXYMYX',
        'Interface/LayerURL': 'http://127.0.0.1:8000/layers',
        'Monitor/RemindSIGMET': 'true',
        'Monitor/SIGMETVolume': 60,
        'Layer/Projection': '+proj=webmerc +datum=WGS84',
        'Layer/FIRBoundary': '[\n  [\n    114.000001907,\n    14.500001907\n  ],\n  [\n    112.000001908,\n    14.500001907\n  ],\n  [\n    108.716665268,\n    17.416666031\n  ],\n  [\n    107.683332443,\n    18.333333969\n  ],\n  [\n    107.18972222,\n    19.26777778\n  ],\n  [\n    107.929967,\n    19.9567\n  ],\n  [\n    108.050001145,\n    20.500001907\n  ],\n  [\n    111.500001908,\n    20.500001907\n  ],\n  [\n    111.500001908,\n    19.500001907\n  ],\n  [\n    114.000001907,\n    16.666666031\n  ],\n  [\n    114.000001907,\n    14.500001907\n  ]\n]'
    }

    def value(self, path):
        return self.config.get(path, None)

    def setValue(self, path, value):
        self.config[path] = value


conf = MockConfig()



if __name__ == '__main__':
    import json
    item = conf.weatherList
    print(json.loads(item))
