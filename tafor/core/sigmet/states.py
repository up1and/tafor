from tafor.core.utils.time import parseTime


class SigmetHeaderState:
    def __init__(self):
        self.area = ''
        self.sign = ''
        self.sequence = ''
        self.beginningTime = ''
        self.endingTime = ''
        self.icao = ''

    def compose(self):
        return '{} {} {} VALID {}/{} {}-'.format(
            self.area, self.sign, self.sequence,
            self.beginningTime, self.endingTime, self.icao,
        )

    def isAcceptable(self):
        return bool(self.area and self.sign and self.sequence
                    and self.beginningTime and self.endingTime and self.icao)

    def clear(self):
        self.area = ''
        self.sign = ''
        self.sequence = ''
        self.beginningTime = ''
        self.endingTime = ''
        self.icao = ''


class BaseState:
    def __init__(self, unit):
        self.header = SigmetHeaderState()
        self.comeFrom = ''
        self.observedTime = ''
        self.flightLevelFormat = ''
        self.flightLevelBase = ''
        self.flightLevelTop = ''
        self.direction = ''
        self.speed = ''
        self.unit = unit
        self.intensityChange = ''
        self.forecastTime = ''
        self.forecastMode = False

    def observation(self):
        if self.comeFrom == 'OBS':
            return 'OBS AT {}Z'.format(self.observedTime) if self.observedTime else ''
        else:
            return '{} AT {}Z'.format(self.comeFrom, self.observedTime) if self.observedTime else self.comeFrom

    def movement(self):
        if self.direction == 'STNR':
            return self.direction

        if not self.speed:
            return None

        return 'MOV {movement} {speed}{unit}'.format(
            movement=self.direction,
            speed=int(self.speed),
            unit=self.unit,
        )

    def flightLevel(self):
        format = self.flightLevelFormat
        base = self.flightLevelBase
        top = self.flightLevelTop

        if base:
            base = str(int(base)).zfill(3)

        if top:
            top = str(int(top)).zfill(3)

        if not format:
            if base and top:
                text = 'FL{}/{}'.format(base, top) if all([top, base]) else ''
            else:
                text = base if base else top
                text = 'FL{}'.format(text) if text else ''

        if format in ['TOP', 'TOP ABV', 'BLW']:
            text = '{} FL{}'.format(format, top) if top else ''

        if format == 'ABV':
            text = 'ABV FL{}'.format(base) if base else ''

        if format == 'SFC':
            text = 'SFC/FL{}'.format(top) if top else ''

        return text

    def forecast(self):
        return 'FCST AT {}Z'.format(self.forecastTime)

    def clear(self):
        self.header.clear()
        self.comeFrom = ''
        self.observedTime = ''
        self.flightLevelFormat = ''
        self.flightLevelBase = ''
        self.flightLevelTop = ''
        self.direction = ''
        self.speed = ''
        self.intensityChange = ''
        self.forecastTime = ''
        self.forecastMode = False


class SigmetGeneralState(BaseState):
    def __init__(self, unit):
        super().__init__(unit)
        self.description = ''
        self.phenomenon = ''

    def hazard(self):
        items = [self.description, self.phenomenon]
        return ' '.join(filter(None, items))

    def composeMessage(self, fir):
        hazard = self.hazard()
        observation = self.observation()
        flightLevel = self.flightLevel()
        moveState = self.movement()
        intensityChange = self.intensityChange

        items = [fir, hazard, observation, '{location}', flightLevel]

        if self.forecastMode:
            forecast = self.forecast()
            items += [intensityChange, forecast, '{forecastLocation}']
        else:
            items += [moveState, intensityChange]

        content = ' '.join(filter(None, items))
        return '\n'.join([self.header.compose(), content])

    def isAcceptable(self):
        if not self.header.isAcceptable():
            return False
        if self.comeFrom == 'OBS' and not self.observedTime:
            return False
        if self.forecastMode:
            return bool(self.hazard() and self.flightLevel() and self.forecast())
        return bool(self.hazard() and self.flightLevel() and self.movement())

    def clear(self):
        super().clear()
        self.description = ''
        self.phenomenon = ''


class SigmetTyphoonState(BaseState):
    def __init__(self, unit):
        super().__init__(unit)
        self.phenomenon = ''
        self.name = ''
        self.currentLatitude = ''
        self.currentLongitude = ''
        self.forecastLatitude = ''
        self.forecastLongitude = ''
        self.radius = ''
        self.top = ''
        self.mode = 'polygon'

    def hazard(self):
        items = [self.phenomenon, self.name]
        return ' '.join(filter(None, items))

    def flightLevel(self):
        return 'TOP FL{}'.format(self.top) if self.top else ''

    def forecastPosition(self):
        if not (self.forecastTime and self.forecastLatitude and self.forecastLongitude):
            return None

        return 'FCST AT {}Z TC CENTRE PSN {} {}'.format(
            self.forecastTime, self.forecastLatitude, self.forecastLongitude,
        )

    def composeMessage(self, fir):
        hazard = self.hazard()
        observation = self.observation()
        position = 'PSN {latitude} {Longitude} CB {observation}'.format(
            latitude=self.currentLatitude,
            Longitude=self.currentLongitude,
            observation=observation,
        )
        flightLevel = self.flightLevel()
        moveState = self.movement()
        intensityChange = self.intensityChange
        forecastPosition = self.forecastPosition()

        if self.mode == 'circle':
            location = 'WI {radius}{unit} OF TC CENTRE'.format(
                radius=int(self.radius) if self.radius else '',
                unit='KM',
            )
        else:
            location = '{location}'

        items = [fir, hazard, position, location, flightLevel]

        if forecastPosition:
            items += [intensityChange, forecastPosition]
        else:
            items += [moveState, intensityChange]

        content = ' '.join(filter(None, items))
        return '\n'.join([self.header.compose(), content])

    def isAcceptable(self):
        if not self.header.isAcceptable():
            return False
        if self.comeFrom == 'OBS' and not self.observedTime:
            return False
        if not (self.phenomenon and self.name and self.currentLatitude
                and self.currentLongitude and self.top):
            return False
        if self.mode == 'circle' and not self.radius:
            return False
        if self.forecastMode:
            return bool(self.forecastTime and self.forecastLatitude and self.forecastLongitude)
        return bool(self.movement())

    def calcForecastPosition(self):
        if not (self.currentLatitude and self.currentLongitude
                and self.speed and self.forecastTime):
            return None

        if not (self.observedTime or self.header.beginningTime):
            return None

        if self.direction == 'STNR':
            return None

        from tafor.core.geometry.coordinate import calcPosition

        directions = {
            'N': 0, 'NNE': 22.5, 'NE': 45, 'ENE': 67.5,
            'E': 90, 'ESE': 112.5, 'SE': 135, 'SSE': 157.5,
            'S': 180, 'SSW': 202.5, 'SW': 225, 'WSW': 247.5,
            'W': 270, 'WNW': 292.5, 'NW': 315, 'NNW': 337.5,
        }

        beginningTime = self.header.beginningTime[2:] if self.header.beginningTime else ''
        time = parseTime(self.forecastTime) - parseTime(self.observedTime or beginningTime)
        degree = directions[self.direction]

        return calcPosition(self.currentLatitude, self.currentLongitude,
                           self.speed, time.seconds, degree)

    def circleFeature(self, location):
        from tafor.core.geometry.coordinate import degreeToDecimal

        feature = {'type': 'Feature', 'properties': {'location': location}}

        if location == 'initial':
            lat, lon = self.currentLatitude, self.currentLongitude
        else:
            lat, lon = self.forecastLatitude, self.forecastLongitude

        if lat and lon:
            feature['geometry'] = {
                'type': 'Point',
                'coordinates': (degreeToDecimal(lon), degreeToDecimal(lat)),
            }
            if self.radius:
                feature['properties']['radius'] = int(self.radius)

        if 'geometry' not in feature:
            return {}

        return feature

    def clear(self):
        super().clear()
        self.phenomenon = ''
        self.name = ''
        self.currentLatitude = ''
        self.currentLongitude = ''
        self.forecastLatitude = ''
        self.forecastLongitude = ''
        self.radius = ''
        self.top = ''
        self.mode = 'polygon'


class SigmetAshState(BaseState):
    def __init__(self, unit):
        super().__init__(unit)
        self.phenomenon = ''
        self.name = ''
        self.currentLatitude = ''
        self.currentLongitude = ''
        self.isEruption = True

    def hazard(self):
        items = ['VA', self.phenomenon]
        if self.isEruption and self.name:
            items += ['MT', self.name]
        return ' '.join(filter(None, items))

    def composeMessage(self, fir):
        hazard = self.hazard()
        observation = self.observation()
        flightLevel = self.flightLevel()
        moveState = self.movement()
        intensityChange = self.intensityChange

        if self.isEruption:
            position = 'PSN {latitude} {Longitude} VA CLD {observation}'.format(
                latitude=self.currentLatitude,
                Longitude=self.currentLongitude,
                observation=observation,
            )
        else:
            position = observation

        items = [fir, hazard, position, '{location}', flightLevel]
        if self.forecastMode:
            forecast = self.forecast()
            items += [intensityChange, forecast, '{forecastLocation}']
        else:
            items += [moveState, intensityChange]

        content = ' '.join(filter(None, items))
        return '\n'.join([self.header.compose(), content])

    def isAcceptable(self):
        if not self.header.isAcceptable():
            return False
        if self.comeFrom == 'OBS' and not self.observedTime:
            return False
        if self.isEruption and not (self.currentLatitude and self.currentLongitude):
            return False
        if self.forecastMode:
            return bool(self.flightLevel() and self.forecast())
        return bool(self.flightLevel() and self.movement())

    def clear(self):
        super().clear()
        self.phenomenon = ''
        self.name = ''
        self.currentLatitude = ''
        self.currentLongitude = ''
        self.isEruption = True


class SigmetCancelState:
    def __init__(self):
        self.header = SigmetHeaderState()
        self.cancelSequence = ''
        self.cancelBeginningTime = ''
        self.cancelEndingTime = ''

    def composeMessage(self, fir):
        cancel = 'CNL {} {} {}/{}'.format(
            self.header.sign,
            self.cancelSequence,
            self.cancelBeginningTime,
            self.cancelEndingTime,
        )
        items = [fir, cancel]
        content = ' '.join(filter(None, items))
        return '\n'.join([self.header.compose(), content])

    def isAcceptable(self):
        return (self.header.isAcceptable()
                and bool(self.cancelSequence and self.cancelBeginningTime and self.cancelEndingTime))

    def clear(self):
        self.header.clear()
        self.cancelSequence = ''
        self.cancelBeginningTime = ''
        self.cancelEndingTime = ''


class SigmetCustomState:
    def __init__(self):
        self.header = SigmetHeaderState()
        self.text = ''

    def composeMessage(self, fir):
        items = [fir, self.text]
        content = ' '.join(filter(None, items))
        return '\n'.join([self.header.compose(), content])

    def isAcceptable(self):
        return self.header.isAcceptable() and bool(self.text)

    def clear(self):
        self.header.clear()
        self.text = ''
