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

    def sigmets(self):
        return self._state['sigmets']

    def updatedTime(self):
        fmt = '%a, %d %b %Y %H:%M:%S GMT'
        try:
            return datetime.datetime.strptime(self._state['updated'], fmt)
        except Exception as e:
            return None

    def boundaries(self):
        return self.degreeToPixel(self._state['boundaries'])

    def sigmetsInfo(self):
        infos = []
        for sig in self._state['sigmets']:
            area = {}
            for key, item in sig.area().items():
                polygon = self.decodeSigmetArea(item)
                area[key] = polygon

            infos.append({
                'type': sig.type(),
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
                polygon = self.degreeToPixel(polygon)
            except Exception as e:
                logger.error(e)

        elif area['type'] == 'line':
            decimals = []
            for identifier, *points in area['area']:
                points = [(degreeToDecimal(lng), degreeToDecimal(lat)) for lat, lng in points]
                decimals.append((identifier, points))

            try:
                polygon = decodeSigmetArea(self._state['boundaries'], decimals, mode='line')
                polygon = self.degreeToPixel(polygon)
            except Exception as e:
                logger.error(e)

        elif area['type'] == 'rectangular':
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
                polygon = self.degreeToPixel(polygon)
            except Exception as e:
                logger.error(e)

        elif area['type'] == 'entire':
            polygon = self.boundaries()

        return polygon

    def degreeToPixel(self, degreePoints):
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


class Context(object):
    message = MessageState()
    webApi = WebApiState(message)
    callService = CallServiceState()
    taf = TafState()
    fir = FirState()
    serial = SerialState()


context = Context()
