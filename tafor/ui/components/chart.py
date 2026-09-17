import os
import random
import logging
import datetime

from typing import NamedTuple

from PyQt5.QtGui import QPainter, QColor, QBrush, QPixmap, QPolygonF
from PyQt5.QtCore import QCoreApplication, QStandardPaths, QDate, QPointF, Qt
from PyQt5.QtWidgets import QDialog, QFileDialog, QDialogButtonBox, QCalendarWidget, QGraphicsRectItem, QGraphicsPolygonItem, QGraphicsTextItem
from PyQt5.QtChart import (QChart, QChartView, QSplineSeries, QScatterSeries, QValueAxis, QDateTimeAxis, QCategoryAxis)

from tafor.ui.qt import Ui_chart
from tafor.ui.styles import applyCalendarStyle
from tafor.core.utils.time import utcnow

logger = logging.getLogger('tafor.chart')


class Sample(NamedTuple):
    """One plotted value together with the report it came from.

    Carrying the report on the sample is what keeps the marker tooltip
    honest: a series skips the reports where its quantity is missing, so a
    point's index does not line up with the index of the report list.
    """

    timestamp: int      # epoch milliseconds
    value: object
    metar: object       # the parsed primary this value was read from


def weatherPoints(weathers):
    """Map observed weather codes to scatter points, grouped by code.

    weathers is a sequence of (timestamp, codes) pairs, codes being METAR
    weather strings such as '-SHRA' or 'FG'. A phenomenon has no numeric
    value of its own, so the y axis carries intensity instead: '-' draws in
    2..18, no prefix in 22..38 and '+' in 42..58. Each band is five 4-unit
    slots and a code takes one of them, so several phenomena observed at the
    same time never land on the same y and hide one another.

    Which slot a code takes comes from a fixed seed rather than from a fixed
    order, so the spacing does not read as a ladder while the same report
    still always draws the same points, however often the window is redrawn.

    The key is the code as reported, prefix included, so a phenomenon seen at
    more than one intensity becomes more than one series. Qt gives a series a
    single marker size, so the size can only follow intensity that way.

    Returns {code: [(timestamp, value), ...]}, one group per phenomenon,
    ordered by intensity within it.
    """
    def stripIntensity(code):
        return code[1:] if code.startswith(('+', '-')) else code

    def bandMin(code):
        if code.startswith('-'):
            return 2
        if code.startswith('+'):
            return 42
        return 22

    points = {}
    for timestamp, codes in weathers:
        # a generator per report, so a report's layout depends on its own codes
        # and not on how many reports were drawn before it. The seed is fixed,
        # and picked so a lone phenomenon lands mid-band and the two and three
        # code cases come out 8 units apart, which is as far as three of the
        # five slots can sit. Three is the usual number of phenomena at once.
        rng = random.Random(52)
        bands = {}
        for code in sorted(codes):
            low = bandMin(code)
            slots = bands.setdefault(low, [low + 4 * i for i in range(5)])
            # a sixth code in one band has nowhere left to go; reuse the band
            # floor rather than spill into the next band, which the tooltip
            # would decode as a different intensity
            value = slots.pop(rng.randrange(len(slots))) if slots else low
            points.setdefault(code, []).append((timestamp, value))

    # keep the intensities of one phenomenon together; sorting the raw codes
    # would put '+RA' ahead of '-RA' and split the group apart
    return {code: points[code] for code in sorted(points, key=lambda c: (stripIntensity(c), bandMin(c)))}


def weatherMarkerSize(code):
    """Marker size for a reported weather code.

    Qt gives a series one marker size, which is why the intensity prefix has
    to reach the chart as part of the series key for the size to be able to
    follow it. The prefix is the whole rule: light weather draws the smallest
    marker, no prefix the middle one and heavy weather the largest. Which
    phenomenon it is does not enter into it.
    """
    if code.startswith('+'):
        return 10
    if code.startswith('-'):
        return 8
    return 9


def cloudPoints(clouds):
    """Map observed cloud layers to scatter points grouped by cover kind.

    clouds is a sequence of (timestamp, layers) pairs, layers being METAR
    cloud strings such as 'FEW030', 'BKN040CB' or 'VV002'. Kinds are the
    cover prefixes FEW/SCT/BKN/OVC plus VV, TCU and CB detected by
    containment; height is the digits times 30 metres.

    Returns {kind: [(timestamp, height), ...]} ordered by ascending cover,
    which is the order the chart legend and the series are built in.
    """
    def kind(text):
        if 'VV' in text:
            return 'VV'
        if 'CB' in text:
            return 'CB'
        if 'TCU' in text:
            return 'TCU'
        return text[:3]

    def height(text):
        digits = ''.join(c for c in text if c.isdigit())
        return int(digits) * 30

    covers = {}
    for timestamp, layers in clouds:
        for text in layers:
            key = kind(text)
            covers.setdefault(key, []).append((timestamp, height(text)))

    # the legend order lives here so the caller does not repeat the kinds
    order = ['FEW', 'SCT', 'BKN', 'OVC', 'VV', 'TCU', 'CB']
    return {key: covers[key] for key in order if key in covers}


def metarSamples(records):
    """Map metar records to time series samples grouped by quantity.

    records is a sequence of records exposing .created and .parser() whose
    primary metar provides windSpeed()/vis()/... accessors.

    Returns (samples, reports) where samples is a dict of list-of-Sample
    keyed by quantity name (gusts, rvrs and weathers only present when
    non-empty) and reports is the list of records that parsed, in the same
    order, so a caller can look up "the report nearest time T".
    """
    samples = {name: [] for name in (
        'winds',
        'gusts',
        'visibilities',
        'rvrs',
        'temperatures',
        'dewpoints',
        'pressures',
        'ceilings',
        'clouds',
        'weathers',
    )}
    reports = []

    for record in records:
        # one unparsable report must not blank the whole window: drop it and
        # keep drawing the rest. VV/// reaches here because the lexer accepts
        # it while ceiling()/clouds() cannot turn '///' into a height.
        try:
            metar = record.parser().primary
            windSpeed = metar.windSpeed()
            vis = metar.vis()
            ceiling = metar.ceiling()
            temperature = metar.temperature()
            dewpoint = metar.dewpoint()
            pressure = metar.pressure()
            clouds = metar.clouds()
            weathers = metar.weathers()
            rvr = metar.rvr()
            gust = metar.gust()
        except ValueError:
            logger.warning('Skipping unparsable metar: %r', record.text)
            continue

        timestamp = round(record.created.timestamp() * 1000)
        reports.append(record)

        # accessors return None when the element is missing; skip the sample
        # instead of feeding None into the chart series. The test is
        # `is not None` on purpose: wind speed 0 and temperature 0 are real
        # observations, not missing values.
        for name, value in (
            ('winds', windSpeed),
            ('visibilities', vis),
            ('ceilings', ceiling),
            ('temperatures', temperature),
            ('dewpoints', dewpoint),
            ('pressures', pressure),
        ):
            if value is not None:
                samples[name].append(Sample(timestamp, value, metar))

        samples['clouds'].append(Sample(timestamp, clouds, metar))

        if weathers:
            samples['weathers'].append(Sample(timestamp, weathers, metar))

        if rvr:
            samples['rvrs'].append(Sample(timestamp, rvr, metar))

        if gust:
            samples['gusts'].append(Sample(timestamp, gust, metar))

    return samples, reports


def roundToHalfHour(dt):
    """Round a datetime down to the nearest full or half hour."""
    if dt.minute < 30:
        return dt.replace(minute=0, second=0, microsecond=0)
    return dt.replace(minute=30, second=0, microsecond=0)


def computeDateRange(utcnow, currentRange, request='latest'):
    """Compute a 24 hour (start, end) chart query window.

    utcnow is the anchor time (already rounded to a full/half hour),
    currentRange the previous (start, end) and request one of 'latest', an
    hour offset int, or a datetime.date selecting that day. Anything else
    is rejected rather than quietly falling back to the previous window.
    """
    day = datetime.timedelta(hours=24)

    if request == 'latest':
        dateRange = (utcnow - day, utcnow)

    # datetime is a subclass of date: check it first, otherwise the hour is
    # silently dropped and the window snaps to midnight
    elif isinstance(request, datetime.datetime):
        dateRange = (request, request + day)

    elif isinstance(request, datetime.date):
        start = datetime.datetime(request.year, request.month, request.day)
        dateRange = (start, start + day)

    elif isinstance(request, int) and not isinstance(request, bool):
        start, _ = currentRange
        dateRange = (start + datetime.timedelta(hours=request), start + datetime.timedelta(hours=request) + day)

    else:
        raise ValueError('unsupported date request: {!r}'.format(request))

    if dateRange[1] > utcnow:
        dateRange = (utcnow - day, utcnow)

    return dateRange


def computeTickCount(xmin, xmax):
    """Number of 3-hourly x ticks spanning the range, inclusive."""
    tickCount = (xmax - xmin).total_seconds() / (3600 * 3)
    return round(tickCount) + 1


def findIndex(records, timestamp):
    """Index of the record whose created time is closest to timestamp.

    A window holds a few dozen reports at most, so this scans rather than
    bisects, which also means records do not have to be in any order.
    """
    best = 0
    closest = abs(records[0].created.timestamp() - timestamp)

    for index in range(1, len(records)):
        distance = abs(records[index].created.timestamp() - timestamp)
        if distance < closest:
            best, closest = index, distance

    return best


def markerHtml(points, unit='', weather=False):
    """Build the marker tooltip html for the given sample points.

    points is a sequence of (name, value, timestamp_ms, metar) tuples; only
    the Wind entry consults metar for a direction suffix.

    unit is what the values are measured in. weather marks the weather chart,
    whose y is an intensity slot rather than a measurement, so its label is the
    series name alone -- the name already is the code as reported. That is a
    property of the chart, not of the missing unit: a chart of real values
    still prints them however it is measured.
    """
    labels = []
    for name, value, timestamp, metar in points:
        if weather:
            text = name
        else:
            text = '{}: {}'.format(name, value)
            if unit:
                text += ' ' + unit

            if name == 'Wind' and metar:
                direction = metar.windDirection()
                if direction:
                    if direction == 'VRB':
                        text += ' from VRB'
                    else:
                        text += ' from {} ({}°)'.format(metar.windDirection('compass'), direction)

        labels.append(text)

    # 'timestamp' is a Unix epoch in milliseconds: interpret it as UTC,
    # otherwise the naive result shifts by the machine's UTC offset
    time = datetime.datetime.fromtimestamp(float(timestamp) / 1000, tz=datetime.timezone.utc).replace(tzinfo=None)
    return '{:%d %b %H:%M} UTC<br>{}'.format(time, '<br>'.join(labels))


def isLightColor(red, green, blue):
    """Whether a background color is light enough for dark text."""
    return (red * 0.299 + green * 0.587 + blue * 0.114) > 186


class MarkerGraphicsItem(QGraphicsRectItem):
    """Marker graphics item for series data"""

    def __init__(self, chart, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.chart = chart
        self.polygon = QGraphicsPolygonItem(self)
        self.text = QGraphicsTextItem(self)

    def setSeriesText(self, items):
        points = []
        for _, series, point, index in items:
            metar = self.chart.metarAt(series, index) if series.name() == 'Wind' else None
            points.append((series.name(), int(point.y()), float(point.x()), metar))

        self.text.setHtml(markerHtml(points, self.chart.spec.unit, self.chart.spec.weather))

    def setSeriesColor(self, color):
        # Set primary text and background color
        self.polygon.setBrush(QBrush(color))
        # https://stackoverflow.com/questions/3942878/how-to-decide-font-color-in-white-or-black-depending-on-background-color
        if isLightColor(color.red(), color.green(), color.blue()):
            penColor = QColor(70, 70, 70)
        else:
            penColor = QColor(255, 255, 255)
        self.text.setDefaultTextColor(penColor)
        self.polygon.setPen(penColor)

    def updateGeometry(self):
        rect = self.text.boundingRect()
        # half-width of the label's pointer triangle, in scene units
        quarter = 5
        self.text.setPos(rect.topLeft() + QPointF(- rect.width() / 2, - rect.height() - quarter - 2))
        # Create pointed left label box
        polygon = QPolygonF([
            rect.topLeft(),
            rect.bottomLeft(),
            rect.bottomLeft() + QPointF(rect.width() / 2 - quarter, 0),
            rect.bottomLeft() + QPointF(rect.width() / 2, quarter),
            rect.bottomLeft() + QPointF(rect.width() / 2 + quarter, 0),
            rect.bottomRight(),
            rect.topRight(),
        ])
        self.polygon.setPolygon(polygon)
        self.polygon.setPos(rect.topLeft().x() - rect.width() / 2, rect.topLeft().y() - rect.height() - quarter - 2)

    def place(self, items):
        """Place marker for series at position of first point

        Visibility is the caller's decision: the plot area test has to run
        against the position set here, not the one left over from the
        previous call, and consulting isVisible() would make the call depend
        on whoever called setVisible() last.
        """
        _, series, point, _ = items[0]
        chart = series.chart()

        self.setPos(chart.mapToPosition(point))
        self.setSeriesText(items)
        self.setSeriesColor(series.pen().color())
        self.updateGeometry()

        inside = chart.plotArea().contains(self.pos())
        first, last = series.at(0).x(), series.at(series.count() - 1).x()
        self.setVisible(inside and first <= point.x() <= last)


class Chart(QChart):
    """A chart that knows the spec behind it and the samples behind its series."""

    def __init__(self, spec):
        super().__init__()
        self.spec = spec
        self.samples = {}
        self.setTitle(spec.caption)

    def setSamples(self, series, samples):
        self.samples[series] = samples

    def metarAt(self, series, index):
        """The metar that produced the point at index of series, or None."""
        samples = self.samples.get(series)
        if samples is None or not 0 <= index < len(samples):
            logger.debug('No sample for %s at %d', series.name(), index)
            return None

        return samples[index].metar


class ChartView(QChartView):
    """Custom chart view class providing points marker"""
    markerRadius = 16

    def __init__(self, chart=None, parent=None):
        super().__init__(chart, parent)

        self.setMarker(MarkerGraphicsItem(self.chart()))

    def setMarker(self, item):
        self.marker = item
        item.setZValue(100)
        self.scene().addItem(item)

    def nearestPoints(self, series, pos):
        items = []
        chart = self.chart()
        for index, point in enumerate(series.pointsVector()):
            distance = (pos - chart.mapToPosition(point)).manhattanLength()
            items.append((distance, series, point, index))
        items.sort(key=lambda item: item[0])
        return items

    def mouseMoveEvent(self, event):
        """Draws marker and symbols/labels."""
        chart = self.chart()
        if not chart.series():
            return
        pos = chart.mapToScene(event.pos())
        visible = chart.plotArea().contains(pos)
        self.marker.setVisible(visible)

        items = []
        for series in chart.series():
            points = self.nearestPoints(series, pos)
            if len(points):
                items.append(points[0])

        items.sort(key=lambda item: item[0])

        if len(items):
            distance, series, point, _ = items[0]
            if distance < self.markerRadius:
                samePointItems = list(filter(lambda item: item[2] == point, items))
                self.marker.place(samePointItems)
            else:
                self.marker.setVisible(False)

        super().mouseMoveEvent(event)


class SeriesSpec(NamedTuple):
    """One series of a chart."""

    name: str
    source: str                     # key into the samples dict
    kind: str = 'spline'            # 'spline' | 'scatter'
    color: object = None
    optional: bool = False          # skip the series when the window has no samples


class ChartSpec(NamedTuple):
    """One of the six charts: its series and how its axes are built."""

    title: str
    series: tuple = ()
    unit: str = ''                  # what the values are measured in; '' where they are not
    yRange: tuple = None            # None means derive it from the data
    yTicks: int = 0
    windAxis: bool = False          # add the wind direction axis on top
    weather: bool = False           # series come from weather codes
    clouds: bool = False            # also draw one series per cloud kind

    @property
    def caption(self):
        """The title as shown above the chart, unit and all.

        The unit is carried separately because the file name wants the bare
        name, so writing it into title by hand would mean every consumer
        stripping it back out.
        """
        return '{} ({})'.format(self.title, self.unit) if self.unit else self.title


class ChartViewer(QDialog, Ui_chart.Ui_Chart):
    """The chart window.

    specs is the set of charts to stack, top to bottom. It is a default: pass
    specs= to the constructor to show a different set, which is what a test
    wanting fewer than six charts would do.
    """

    specs = (
        ChartSpec('Wind / Gust', unit='m/s', windAxis=True, series=(
            SeriesSpec('Wind', 'winds'),
            SeriesSpec('Gust', 'gusts', kind='scatter', color=Qt.darkYellow, optional=True),
        )),
        ChartSpec('Visibility / RVR', unit='m', yRange=(0, 10000), yTicks=5, series=(
            SeriesSpec('Visibility', 'visibilities'),
            SeriesSpec('RVR', 'rvrs', kind='scatter', color=Qt.darkCyan, optional=True),
        )),
        ChartSpec('Weather Phenomenon', weather=True),
        ChartSpec('Clouds / Ceiling', unit='m', yRange=(0, 1500), yTicks=4, clouds=True, series=(
            SeriesSpec('Ceiling', 'ceilings'),
        )),
        ChartSpec('Temperature / Dewpoint', unit='°C', series=(
            SeriesSpec('Temperature', 'temperatures'),
            SeriesSpec('Dewpoint', 'dewpoints'),
        )),
        ChartSpec('Query Normal Height', unit='hPa', series=(
            SeriesSpec('Pressure', 'pressures'),
        )),
    )

    def __init__(self, parent=None, specs=None, repository=None, clock=None):
        super().__init__(parent)
        self.setupUi(self)
        self.repository = repository
        self.clock = clock or utcnow
        self.dateRange = None
        self.views = []

        if specs is not None:
            self.specs = specs

        self.saveButton = self.buttonBox.button(QDialogButtonBox.Save)
        self.saveButton.setText(QCoreApplication.translate('Chart', 'Save'))
        self.calendar.calendarWidget().setHorizontalHeaderFormat(QCalendarWidget.NoHorizontalHeader)
        applyCalendarStyle(self.calendar.calendarWidget())
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint)

        self.bindSignal()
        self.initChart()

    def bindSignal(self):
        self.dayAgoButton.clicked.connect(lambda: self.updateDateRange(-24))
        self.dayLaterButton.clicked.connect(lambda: self.updateDateRange(24))
        self.hoursAgoButton.clicked.connect(lambda: self.updateDateRange(-3))
        self.hoursLaterButton.clicked.connect(lambda: self.updateDateRange(3))
        self.latestButton.clicked.connect(lambda: self.updateDateRange('latest'))
        self.calendar.dateChanged.connect(self.updateDateRange)

        self.saveButton.clicked.connect(self.saveImages)

    def saveImages(self):
        caption = QCoreApplication.translate('Chart', 'Save to Directory')
        path = QStandardPaths.writableLocation(QStandardPaths.PicturesLocation)
        directory = str(QFileDialog.getExistingDirectory(self, caption, path))

        if not directory:
            return

        stamp = self.dateRange[0].strftime('%Y-%m-%d %H-%M-%S')

        for view in self.views:
            spec = view.chart().spec
            # '/' reads as a directory separator in a path
            name = spec.title.replace('/', '&')
            filepath = os.path.join(directory, '{} {}.png'.format(name, stamp))

            image = QPixmap(view.grab())
            image.save(filepath, 'png')

    def setCalendar(self):
        maxDate = QDate.currentDate()
        start = self.dateRange[0]
        date = QDate(start.year, start.month, start.day)

        # Programmatic updates would re-emit dateChanged and recursively call
        # updateDateRange; block the signals instead of disconnecting the slot.
        self.calendar.blockSignals(True)
        try:
            self.calendar.calendarWidget().setSelectedDate(date)
            self.calendar.setMaximumDate(maxDate)
        finally:
            self.calendar.blockSignals(False)

    def updateDateRange(self, date='latest'):
        now = roundToHalfHour(self.clock())

        if isinstance(date, QDate):
            date = date.toPyDate()

        self.dateRange = computeDateRange(now, self.dateRange, date)

        self.setCalendar()
        self.clearChart()

        # last resort guard: metarSamples already tolerates a single bad
        # report, so anything arriving here is a genuine bug and the
        # traceback is worth keeping in the log
        try:
            self.drawChart()
        except Exception:
            start, end = self.dateRange
            logger.exception('Failed to draw chart, date range %s - %s', start, end)

    def showEvent(self, event):
        self.updateDateRange()

    def createChart(self, spec):
        chart = Chart(spec)
        chart.setMinimumSize(750, 250)
        chart.setAnimationOptions(QChart.SeriesAnimations)
        chart.legend().setVisible(True)
        chart.legend().setAlignment(Qt.AlignBottom)

        return chart

    def attachAxis(self, chart, axis, alignment):
        """Add an axis to the chart and attach every series to it."""
        chart.addAxis(axis, alignment)

        for series in chart.series():
            series.attachAxis(axis)

        return axis

    def addAxisX(self, chart, xmin, xmax):
        series = chart.series()
        if not series:
            return

        tickCount = computeTickCount(xmin, xmax)

        axisX = QDateTimeAxis()
        axisX.setTickCount(tickCount)
        axisX.setMin(xmin)
        axisX.setMax(xmax)
        axisX.setFormat('h')

        self.attachAxis(chart, axisX, Qt.AlignBottom)

    def addAxisY(self, chart, spec):
        series = chart.series()
        if not series:
            return

        if not spec.yRange:
            # let Qt derive the range from the data. It pads the raw min/max
            # to readable numbers, which setRange() on the data range followed
            # by applyNiceNumbers() does not: a window whose values are all
            # equal would collapse to a zero-height axis.
            chart.createDefaultAxes()
            chart.removeAxis(chart.axisX())
            axisY = chart.axisY()
            axisY.setLabelFormat('%d')
            axisY.applyNiceNumbers()
            return

        axisY = QValueAxis()
        axisY.setLabelFormat('%d')
        axisY.setRange(*spec.yRange)

        if spec.yTicks:
            axisY.setTickCount(spec.yTicks)

        self.attachAxis(chart, axisY, Qt.AlignLeft)

    def addWeatherAxis(self, chart):
        series = chart.series()
        if not series:
            return

        axisY = QCategoryAxis(chart, labelsPosition=QCategoryAxis.AxisLabelsPositionCenter)
        axisY.setMin(0)
        axisY.setMax(60)
        axisY.setStartValue(20)
        axisY.append('-', 0)
        axisY.append('&nbsp', 40)
        axisY.append('+', 60)

        self.attachAxis(chart, axisY, Qt.AlignLeft)

    def addWindDirectionAxis(self, chart, reports):
        series = chart.series()
        if not series or not reports:
            return

        # a window holding a single report leaves nothing to interpolate
        # between, so keep the divisor away from zero
        tickCount = max(2, chart.axisX().tickCount())
        minx = chart.axisX().min().toMSecsSinceEpoch()
        maxx = chart.axisX().max().toMSecsSinceEpoch()

        axisX = QCategoryAxis(chart, labelsPosition=QCategoryAxis.AxisLabelsPositionOnValue)
        axisX.setTickCount(tickCount)
        step = (maxx - minx) / (tickCount - 1)
        for i in range(tickCount):
            timestamp = (minx + i * step) / 1000
            index = findIndex(reports, timestamp)
            arrow = reports[index].parser().primary.windDirection('arrow') or ''
            # Nothing styles .label-*, but the markup is not inert: Qt lays the
            # label out differently without it, which shifts this axis's
            # gridline antialiasing by a fraction of a pixel. Kept verbatim so
            # the chart renders identically to before the refactor.
            label = '<span class="label-{}">{}</span>'.format(i, arrow)
            axisX.append(label, minx + i * step)

        self.attachAxis(chart, axisX, Qt.AlignTop)

    def initChart(self):
        for spec in self.specs:
            chart = self.createChart(spec)
            view = ChartView(chart)
            view.setRenderHint(QPainter.Antialiasing)
            self.views.append(view)
            self.chartLayout.addWidget(view)

    def clearChart(self):
        for view in self.views:
            chart = view.chart()
            chart.removeAllSeries()
            for axis in chart.axes():
                chart.removeAxis(axis)

    def createSeries(self, spec, samples):
        if spec.kind == 'scatter':
            series = QScatterSeries()
            series.setMarkerSize(8)
            series.setColor(spec.color)
        else:
            series = QSplineSeries()

        series.setName(spec.name)
        for sample in samples:
            series.append(sample.timestamp, sample.value)

        return series

    def scatterSeries(self, groups, emphasis):
        """One scatter series per group, its marker sized by emphasis."""
        graphs = []
        for name, points in groups.items():
            series = QScatterSeries()
            series.setName(name)
            series.setMarkerSize(emphasis(name))

            for timestamp, value in points:
                series.append(timestamp, value)

            graphs.append(series)

        return graphs

    def drawChart(self):
        start, end = self.dateRange
        results = self.repository.range(start, end + datetime.timedelta(minutes=20))

        if not results:
            return

        xmin = results[0].created
        xmax = results[-1].created

        samples, reports = metarSamples(results)

        for view in self.views:
            self.drawView(view, samples, reports, xmin, xmax)

    def drawView(self, view, samples, reports, xmin, xmax):
        """Build one chart, from its spec and the samples in the window."""
        chart = view.chart()
        spec = chart.spec

        for seriesSpec in spec.series:
            values = samples.get(seriesSpec.source)
            if seriesSpec.optional and not values:
                continue

            series = self.createSeries(seriesSpec, values)
            chart.addSeries(series)
            chart.setSamples(series, values)

        # the weather chart draws one series per reported code and the cloud
        # chart one per cover kind, instead of the series listed in the spec.
        # Both helpers take (timestamp, value) pairs, hence the unwrapping.
        if spec.weather:
            weathers = [(sample.timestamp, sample.value) for sample in samples['weathers']]
            # the series key is the code as reported, prefix included, which
            # is what lets the marker size follow the intensity
            graphs = self.scatterSeries(weatherPoints(weathers), weatherMarkerSize)
            for series in graphs:
                chart.addSeries(series)

        if spec.clouds:
            clouds = [(sample.timestamp, sample.value) for sample in samples['clouds']]
            graphs = self.scatterSeries(cloudPoints(clouds),
                                        lambda name: 9 if name in ('TCU', 'CB', 'VV') else 8)
            for series in graphs:
                chart.addSeries(series)

        # the weather chart's y axis is a category axis carrying intensity
        if spec.weather:
            self.addWeatherAxis(chart)
        else:
            self.addAxisY(chart, spec)

        self.addAxisX(chart, xmin, xmax)

        if spec.windAxis:
            self.addWindDirectionAxis(chart, reports)
