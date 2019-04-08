import sys
import copy
import datetime

from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import QObject, QRect, Qt, pyqtSignal

from tafor import conf, logger


class MessageState(object):
    _state = {}

    def state(self):
        return self._state

    def setState(self, values):
        self._state = values


class FirState(object):
    _state = {
        'image': None,
        'size': [0, 0],
        'coordinates': [],
        'rect': [0, 0, 0, 0],
        'boundaries': [],
        'updated': None,
        'sigmets': []
    } # 这里的参数会被远程参数覆盖

    drawable = False

    @property
    def scale(self):
        width = conf.value('General/FirCanvasSize') or 300
        width = int(width)
        imageWidth = self._state['rect'][2]
        if imageWidth == 0:
            return 1
        return width / imageWidth

    def state(self):
        return self._state

    def setState(self, values):
        self._state.update(values)
        try:
            self.computed()
            self.drawable = True
        except Exception:
            self.drawable = False

    def computed(self):
        size = self.size()
        rect = self.rect()
        latRange = self._state['coordinates'][0][1] - self._state['coordinates'][1][1]
        longRange = self._state['coordinates'][1][0] - self._state['coordinates'][0][0]
        self.initLong = self._state['coordinates'][0][0]
        self.initLat = self._state['coordinates'][0][1]
        self.dlat = latRange / size[1]
        self.dlong = longRange / size[0]
        self.offsetX = rect[0]
        self.offsetY = rect[1]

        self.topLeft = [rect[0], rect[1]]
        self.topRight = [rect[0] + rect[2], rect[1]]
        self.bottomRight = [rect[0] + rect[2], rect[1] + rect[3]]
        self.bottomLeft = [rect[0], rect[1] + rect[3]]

    def image(self):
        return self._state['image']

    def pixmap(self):
        if self._state['image'] is None:
            raw = QPixmap(*self.size())
            raw.fill(Qt.gray)
        else:
            raw = QPixmap()
            raw.loadFromData(self._state['image'])
            raw = raw.scaled(*self.size())

        rect = QRect(*self.rect())
        image = raw.copy(rect)
        return image

    def rect(self):
        return [self.scale * i for i in self._state['rect']]

    def size(self):
        return [self.scale * i for i in self._state['size']]

    def dimension(self, mode='kilometer'):
        from tafor.utils.convert import distanceBetweenPoints, distanceBetweenLatLongPoints

        if mode == 'kilometer':
            distance = distanceBetweenLatLongPoints(*self._state['coordinates'])

        if mode == 'nauticalmile':
            distance = distanceBetweenLatLongPoints(*self._state['coordinates']) / 1.852

        if mode == 'decimal':
            distance = distanceBetweenPoints(*self._state['coordinates'])

        if mode == 'pixel':
            distance = distanceBetweenPoints([0, 0], self._state['size'])

        return distance

    def sigmets(self):
        return self._state['sigmets']

    def updatedTime(self):
        fmt = '%a, %d %b %Y %H:%M:%S GMT'
        try:
            return datetime.datetime.strptime(self._state['updated'], fmt)
        except Exception as e:
            return None

    def boundaries(self):
        return self.decimalToPixel(self._state['boundaries'])

    def sigmetsInfo(self):
        infos = []
        for sig in self._state['sigmets']:
            area = {}
            parser = sig.parser()
            for key, item in parser.area().items():
                polygon = self.decodeSigmetArea(item)
                area[key] = polygon

            infos.append({
                'type': parser.type(),
                'area': area
            })

        return infos

    def decodeSigmetArea(self, area):
        from tafor.utils.convert import degreeToDecimal
        from tafor.utils.sigmet import decodeSigmetArea

        polygon = []
        maxx, maxy = self.rect()[2:]

        if area['type'] == 'polygon':
            decimals = [(degreeToDecimal(lng), degreeToDecimal(lat)) for lat, lng in area['area']]

            try:
                polygon = decodeSigmetArea(self._state['boundaries'], decimals, mode='polygon')
                polygon = self.decimalToPixel(polygon)
            except Exception as e:
                logger.error(e)

        if area['type'] == 'line':
            decimals = []
            for identifier, *points in area['area']:
                points = [(degreeToDecimal(lng), degreeToDecimal(lat)) for lat, lng in points]
                decimals.append((identifier, points))

            try:
                polygon = decodeSigmetArea(self._state['boundaries'], decimals, mode='line')
                polygon = self.decimalToPixel(polygon)
            except Exception as e:
                logger.error(e)

        if area['type'] == 'rectangular':
            maxx, maxy = self.rect()[2:]
            decimals = []
            for identifier, deg in area['area']:
                dec = degreeToDecimal(deg)
                if identifier in ['N', 'S']:
                    y = (self.initLat - dec) / self.dlat - self.offsetY
                    points = [
                        (0, y),
                        (maxx, y)
                    ]
                else:
                    x = (dec - self.initLong) / self.dlong - self.offsetX
                    points = [
                        (x, 0),
                        (x, maxy)
                    ]

                decimals.append((identifier, self.pixelToDecimal(points)))

            try:
                polygon = decodeSigmetArea(self._state['boundaries'], decimals, mode='rectangular')
                polygon = self.decimalToPixel(polygon)
            except Exception as e:
                logger.error(e)

        if area['type'] == 'circle':
            point, radius = area['area']
            width = self.distanceToDecimal(*radius)
            center = [degreeToDecimal(point[1]), degreeToDecimal(point[0])]
            circles = [center, width]

            try:
                polygon = decodeSigmetArea(self._state['boundaries'], circles, mode='circle')
                polygon = self.decimalToPixel(polygon)
            except Exception as e:
                logger.error(e)

        if area['type'] == 'corridor':
            points, width = area['area']
            points = [(degreeToDecimal(lng), degreeToDecimal(lat)) for lat, lng in points]
            width = self.distanceToDecimal(*width)
            corridor = [points, width]

            try:
                polygon = decodeSigmetArea(self._state['boundaries'], corridor, mode='corridor')
                polygon = self.decimalToPixel(polygon)
            except Exception as e:
                logger.error(e)

        if area['type'] == 'entire':
            polygon = self.boundaries()

        return polygon

    def decimalToPixel(self, degreePoints):
        points = []
        for lng, lat in degreePoints:
            x = (lng - self.initLong) / self.dlong - self.offsetX
            y = (self.initLat - lat) / self.dlat - self.offsetY
            points.append((x, y))

        return points

    def pixelToDecimal(self, pixelPoints):
        points = []
        for lng, lat in pixelPoints:
            longtitude = self.initLong + (lng + self.offsetX) * self.dlong
            latitude = self.initLat - (lat + self.offsetY) * self.dlat
            points.append((longtitude, latitude))

        return points

    def pixelToDegree(self, pixelPoints):
        from tafor.utils.convert import decimalToDegree

        points = []
        for lng, lat in pixelPoints:
            longtitude = self.initLong + (lng + self.offsetX) * self.dlong
            latitude = self.initLat - (lat + self.offsetY) * self.dlat
            points.append((
                decimalToDegree(longtitude, fmt='longitude'),
                decimalToDegree(latitude)
            ))

        return points

    def decimalToDegree(self, decimalPoints):
        from tafor.utils.convert import decimalToDegree

        points = []
        for lng, lat in decimalPoints:
            points.append((
                decimalToDegree(lng, fmt='longitude'),
                decimalToDegree(lat)
            ))

        return points

    def distanceToDecimal(self, length, unit='KM'):
        mode = 'nauticalmile' if unit == 'NM' else 'kilometer'
        ratio = self.dimension('decimal') / self.dimension(mode)
        return int(length) * ratio

    def distanceToPixel(self, length, unit='KM'):
        mode = 'nauticalmile' if unit == 'NM' else 'kilometer'
        ratio = self.dimension('pixel') / self.dimension(mode)
        return int(length) * ratio * self.scale

    def pixelToDistance(self, pixel):
        ratio = self.dimension('kilometer') / self.dimension('pixel')
        distance = int(pixel) * ratio / self.scale
        return int(distance)


class WebApiState(object):

    def __init__(self, store):
        self._store = store

    def isOnline(self):
        return True if self._store.state() else False


class CallServiceState(object):
    _state = None

    def isOnline(self):
        return True if self._state else False

    def setState(self, value):
        self._state = value


class SerialState(object):
    _lock = False

    def busy(self):
        return self._lock

    def lock(self):
        self._lock = True

    def release(self):
        self._lock = False


class TafState(QObject):
    warningSignal = pyqtSignal()
    clockSignal = pyqtSignal(str)

    def __init__(self):
        super(TafState, self).__init__()
        self._state = {
            'FC': {
                'period': '',
                'sent': False,
                'warning': False,
                'clock': False,
            },
            'FT': {
                'period': '',
                'sent': False,
                'warning': False,
                'clock': False,
            }
        }

    def isWarning(self):
        warnings = [v['warning'] for k, v in self._state.items()]
        return any(warnings)

    def state(self):
        return self._state

    @property
    def spec(self):
        from tafor.utils import boolean

        international = boolean(conf.value('General/InternationalAirport'))
        index = conf.value('General/ValidityPeriod')
        if international:
            if index:
                specification = 'ft30'
            else:
                specification = 'ft24'
        else:
            specification = 'fc'

        return specification

    def setState(self, values):
        refs = copy.deepcopy(self._state)
        self._state.update(values)

        for tt, state in values.items():
            if 'warning' in state:
                self.warningSignal.emit()

            if 'clock' in state:
                if refs[tt]['clock'] != state['clock']:
                    self.clockSignal.emit(tt)


class EnvironState(object):
    key = """-----BEGIN PUBLIC KEY-----
    MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA2AZZfefXdgpvnWcV9xMf
    qlBqTS/8XZXq9BwFRpe0thoS3fER8s5fGKDWiOzO2I2PEwvahXyPny4hxHll7vF+
    lgd3dl0Z5BRslDGzSUe3/S2vqu4jAiyFmF3z8HZ9Jcr7BXi8yYUOr/LUfOP2gWK3
    GnORnWhBTb/llaGjN72yoJKJpKEbJYlrBJdsOyBrAeXbg1QNktOuqPf5toP/72qU
    2a/RRvpK9koSHMvhqd6ex5h+MHvcQZ759Fi1wxj5ChkB6BGgsHGR+7f49c92Gd4o
    2TKLicLL6vcidL4QkXdhRaZTJyd8pYI6Su+FUK7mcaBDpEaUl9xWupJnjsfKx1bf
    WQIDAQAB
    -----END PUBLIC KEY-----"""
    exp = 0

    def ghash(self):
        if hasattr(sys, '_MEIPASS'):
            from tafor._environ import ghash
            return ghash
        else:
            from tafor.utils import gitRevisionHash
            return gitRevisionHash()

    def license(self):
        from tafor import conf
        from tafor.utils import verifyToken
        payload = verifyToken(conf.value('License'), self.key)

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
        if conf.value('Message/ICAO'):
            infos['airport'] = conf.value('Message/ICAO')
        if conf.value('Message/FIR'):
            infos['fir'] = conf.value('Message/FIR')[:4]

        return infos

    def canEnable(self, reportType):
        if reportType == 'Trend':
            return True

        if reportType == 'TAF':
            return 'airport' in self.license()

        if reportType == 'SIGMET':
            return 'fir' in self.license()


class Context(object):
    message = MessageState()
    webApi = WebApiState(message)
    callService = CallServiceState()
    taf = TafState()
    fir = FirState()
    serial = SerialState()
    environ = EnvironState()


context = Context()
