import re
import logging
import datetime

from collections import OrderedDict

from tafor.core.geometry.coordinate import degreeToDecimal
from tafor.core.utils.units import toKmh, toKt
from tafor.core.parsers.base import AdvisoryGrammar

logger = logging.getLogger('tafor.parser.advisory')


class AdvisoryParser:
    """解析咨询报的基类

    :param message: 咨询报内容
    :param grammar: 解析咨询报的语法类
    """

    grammarClass = AdvisoryGrammar

    type = None

    def __init__(self, message, grammar=None):
        if not grammar:
            grammar = self.grammarClass()

        self.grammar = grammar
        self.message = message
        self.tokens = OrderedDict()
        self.time = None
        self.parse()

    def parse(self):
        if not self.type:
            raise NotImplementedError('Advisory parser subclasses must define the type of the advisory')

        regex = r'{}((?:\s?.+\s?)*)'.format(self.type)
        if '=' in self.message:
            regex += '='
        pattern = re.compile(regex)
        match = pattern.search(self.message)
        if not match:
            return
        text = match.group(1)
        matches = re.finditer(r'^\s*([^:]+?)\s*:\s*(.*?)\s*$', text, re.MULTILINE)
        prev = None
        for match in matches:
            key, value = match.groups()
            values = key.split('\n')
            if len(values) > 1:
                *temps, key = values
                if prev:
                    self.tokens[prev] = self.tokens[prev] + ' ' + ' '.join(temps)

            self.tokens[key] = value
            prev = key

        if 'DTG' in self.tokens:
            self.time = datetime.datetime.strptime(self.tokens['DTG'], '%Y%m%d/%H%MZ')

    def position(self):
        keys = ['PSN', 'OBS PSN']
        text = self._findText(keys)
        if text:
            match = self.grammar.point.search(text)
            if match:
                return match.groups()

    def name(self):
        field = self.fields['name']
        if field in self.tokens:
            text = self.tokens[field]
            match = self.grammar.name.match(text)
            if match:
                return match.group()

        return None

    def movement(self):
        field = self.fields['movement']
        if field in self.tokens:
            text = self.tokens[field]
            match = self.grammar.movement.search(text)
            if match:
                return match.group(1)

        return None

    def speed(self, unit='KMH'):
        field = self.fields['movement']
        if field in self.tokens:
            text = self.tokens[field]
            match = self.grammar.speed.search(text)
            if match:
                speed, u = match.groups()
                speed = int(speed)
                if unit != u:
                    speed = toKmh(speed, u) if unit == 'KMH' else toKt(speed, u)

                return int(speed)

    def observedTime(self):
        raise NotImplementedError

    def availableLocations(self):
        keys = []
        field = self.fields['locations']
        for key in self.tokens:
            if field in key:
                keys.append(key)

        return keys

    def _findLocationTime(self, key):
        if not self.time:
            return

        match = re.search(r'\d+', key)
        obstime = self.observedTime()
        if match and obstime:
            hour = int(match.group())
            time = obstime + datetime.timedelta(hours=hour)
            return time
        else:
            return self.time

    def _findText(self, keys):
        for key in keys:
            if key in self.tokens:
                return self.tokens[key]


class TyphoonAdvisoryParser(AdvisoryParser):

    type = 'TC ADVISORY'
    fields = {
        'name': 'TC',
        'movement': 'MOV',
        'locations': 'PSN'
    }

    def observedTime(self):
        return self.time

    def location(self, key):
        if key not in self.tokens:
            return {}

        features = {
            'type': 'Feature',
            'properties': {}
        }
        text = self.tokens[key]
        coordinates = self.grammar.point.findall(text)
        coordinates = [(degreeToDecimal(lon), degreeToDecimal(lat)) for lat, lon in coordinates]
        if coordinates:
            geometry = {
                'type': 'Point',
                'coordinates': coordinates[0]
            }
            features['geometry'] = geometry

        time = self._findLocationTime(key)
        if time:
            features['properties']['time'] = time

        return features

    def height(self):
        if 'CB' in self.tokens:
            text = self.tokens['CB']
            match = self.grammar.height.search(text)
            if match:
                return match.group(1)

        return None

    def intensity(self):
        if 'INTST CHANGE' in self.tokens:
            text = self.tokens['INTST CHANGE']
            return text.strip()

        return None

    def route(self):
        locations = self.availableLocations()
        geometry = {}
        coordinates = []
        for key in locations:
            text = self.tokens[key]
            coordinates += self.grammar.point.findall(text)

        if coordinates:
            geometry = {
                'type': 'LineString',
                'coordinates': [(degreeToDecimal(lon), degreeToDecimal(lat)) for lat, lon in coordinates]
            }

        return geometry

    def polygon(self):
        geometry = {}
        if 'CB' in self.tokens:
            text = self.tokens['CB']
            coordinates = self.grammar.point.findall(text)
            if coordinates:
                geometry = {
                    'type': 'Polygon',
                    'coordinates': [(degreeToDecimal(lon), degreeToDecimal(lat)) for lat, lon in coordinates]
                }

        return geometry

    def radius(self):
        from tafor.core.geometry.algorithm import geod
        center = self.position()
        polygon = self.polygon()
        if not center or not polygon:
            return

        distances = []
        lat, lon = center
        center = degreeToDecimal(lon), degreeToDecimal(lat)
        for lon, lat in polygon['coordinates']:
            _, _, distance = geod.inv(center[0], center[1], lon, lat)
            distances.append(distance)

        return int(max(distances) / 1000)


class AshAdvisoryParser(AdvisoryParser):

    type = 'VA ADVISORY'
    fields = {
        'name': 'VOLCANO',
        'movement': 'OBS VA CLD',
        'locations': 'VA CLD'
    }

    def observedTime(self):
        if self.time and 'OBS VA DTG' in self.tokens:
            text = self.tokens['OBS VA DTG']
            match = self.grammar.time.search(text)
            if match:
                day, hour, minute = match.groups()
                time = self.time.replace(day=int(day), hour=int(hour), minute=int(minute))
                return time

    def location(self, key):
        if key not in self.tokens:
            return {}

        features = {
            'type': 'Feature',
            'properties': {}
        }
        text = self.tokens[key]
        coordinates = self.grammar.point.findall(text)
        coordinates = [(degreeToDecimal(lon), degreeToDecimal(lat)) for lat, lon in coordinates]
        if coordinates:
            geometry = {
                'type': 'Polygon',
                'coordinates': coordinates
            }
            features['geometry'] = geometry

        time = self._findLocationTime(key)
        if time:
            features['properties']['time'] = time

        match = self.grammar.flightLevel.search(text)
        if match:
            features['properties']['flightLevel'] = match.group()

        return features
