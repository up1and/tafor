import os
import random
import logging
import datetime

from PyQt5.QtGui import QPainter, QColor, QBrush, QPixmap, QPolygonF
from PyQt5.QtCore import QCoreApplication, QStandardPaths, QDate, QPointF, Qt
from PyQt5.QtWidgets import QDialog, QFileDialog, QDialogButtonBox, QCalendarWidget, QGraphicsRectItem, QGraphicsPolygonItem, QGraphicsTextItem
from PyQt5.QtChart import (QChart, QChartView, QSplineSeries, QScatterSeries, QDateTimeAxis, QCategoryAxis)

from tafor.ui.qt import Ui_chart
from tafor.ui.styles import calendarStyle

logger = logging.getLogger('tafor.chart')


def weatherPoints(weathers):
    """Map observed weather codes to scatter points grouped by phenomenon.

    weathers is a sequence of (timestamp, codes) pairs, codes being METAR
    weather strings such as '-SHRA' or 'FG'. An intensity prefix selects
    the y-value band: '-' weak (2..18), plain normal (22..38) and '+'
    strong (42..58); values are drawn without replacement within a
    timestamp so points never overlap exactly.

    Returns {phenomenon: [(timestamp, value), ...]} sorted by name.
    """
    def stripIntensity(code):
        return code[1:] if code.startswith(('+', '-')) else code

    def findWeather(name, codes):
        for code in codes:
            if name == stripIntensity(code):
                return code

    valueMaps = {}
    phenomena = set()
    for timestamp, codes in weathers:
        if codes:
            enums = list(range(2, 20, 4))
            valueMaps[timestamp] = {
                'weak': enums,
                'normal': [e + 20 for e in enums],
                'strong': [e + 40 for e in enums],
            }

            for code in codes:
                phenomena.add(stripIntensity(code))

    points = {}
    for name in sorted(phenomena):
        group = []
        for timestamp, codes in weathers:
            code = findWeather(name, codes)
            if not code:
                continue

            bands = valueMaps[timestamp]
            band = bands['normal']
            if code.startswith('-'):
                band = bands['weak']
            if code.startswith('+'):
                band = bands['strong']

            value = random.choice(band)
            band.remove(value)
            group.append((timestamp, value))

        points[name] = group

    return points


def cloudPoints(clouds):
    """Map observed cloud layers to scatter points grouped by cover kind.

    clouds is a sequence of (timestamp, layers) pairs, layers being METAR
    cloud strings such as 'FEW030', 'BKN040CB' or 'VV002'. Kinds are the
    cover prefixes FEW/SCT/BKN/OVC plus VV, TCU and CB detected by
    containment; height is the digits times 30 metres.

    Returns {kind: [(timestamp, height), ...]}.
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

    return covers


def metarSamples(records):
    """Map metar records to time series samples grouped by quantity.

    records is a sequence of records exposing .created and .parser() whose
    primary metar provides windSpeed()/vis()/... accessors.

    Returns (samples, primaries) where samples is a dict of
    list-of-(timestamp_ms, value) tuples keyed by quantity name (gusts, rvrs
    and weathers only present when non-empty) and primaries is the parsed
    metar list aligned with the samples.
    """
    samples = {
        'winds': [],
        'gusts': [],
        'visibilities': [],
        'rvrs': [],
        'temperatures': [],
        'dewpoints': [],
        'pressures': [],
        'ceilings': [],
        'clouds': [],
        'weathers': [],
    }
    primaries = []

    for record in records:
        metar = record.parser().primary
        timestamp = round(record.created.timestamp() * 1000)

        primaries.append(metar)

        samples['winds'].append((timestamp, metar.windSpeed()))
        samples['visibilities'].append((timestamp, metar.vis()))
        samples['ceilings'].append((timestamp, metar.ceiling()))
        samples['temperatures'].append((timestamp, metar.temperature()))
        samples['dewpoints'].append((timestamp, metar.dewpoint()))
        samples['pressures'].append((timestamp, metar.pressure()))

        samples['clouds'].append((timestamp, metar.clouds()))

        if metar.weathers():
            samples['weathers'].append((timestamp, metar.weathers()))

        if metar.rvr():
            samples['rvrs'].append((timestamp, metar.rvr()))

        if metar.gust():
            samples['gusts'].append((timestamp, metar.gust()))

    return samples, primaries


def roundToHalfHour(dt):
    """Round a datetime down to the nearest full or half hour."""
    if dt.minute < 30:
        return dt.replace(minute=0, second=0, microsecond=0)
    return dt.replace(minute=30, second=0, microsecond=0)


def computeDateRange(utcnow, currentRange, request='latest'):
    """Compute a 24 hour (start, end) chart query window.

    utcnow is the anchor time (already rounded to a full/half hour),
    currentRange the previous (start, end) and request one of 'latest', an
    hour offset int, or a datetime.date selecting that day.
    """
    if request == 'latest':
        return (utcnow - datetime.timedelta(hours=24), utcnow)

    if isinstance(request, datetime.date):
        start = datetime.datetime(request.year, request.month, request.day)
        dateRange = (start, start + datetime.timedelta(hours=24))

    elif isinstance(request, int):
        timedelta = datetime.timedelta(hours=request)
        start, _ = currentRange
        dateRange = (start + timedelta, start + timedelta + datetime.timedelta(hours=24))

    else:
        dateRange = currentRange

    if dateRange[1] > utcnow:
        dateRange = (utcnow - datetime.timedelta(hours=24), utcnow)

    return dateRange


def computeTickCount(xmin, xmax):
    """Number of 3-hourly x ticks spanning the range, inclusive."""
    tickCount = (xmax - xmin).total_seconds() / (3600 * 3)
    return round(tickCount) + 1


def findIndex(records, timestamp):
    """Index of the record whose created time is closest to timestamp."""
    deltas = []
    for record in records:
        delta = abs(record.created.timestamp() - timestamp)
        deltas.append(delta)

    return deltas.index(min(deltas))


def markerHtml(title, points):
    """Build the marker tooltip html for the given sample points.

    points is a sequence of (name, value, timestamp_ms, metar) tuples; only
    the Wind entry consults metar for a direction suffix.
    """
    labels = []
    for name, value, timestamp, metar in points:
        if title == 'Weather Phenomenon':
            if value < 20:
                name = '-' + name
            if value > 40:
                name = '+' + name

            text = name
        else:
            unit = title.split('(')[-1].replace(')', '')
            text = '{}: {} {}'.format(name, value, unit)

            if name == 'Wind' and metar:
                direction = metar.windDirection()
                if direction:
                    if direction == 'VRB':
                        text += ' from VRB'
                    else:
                        text += ' from {} ({}°)'.format(metar.windDirection('compass'), direction)

        labels.append(text)

    time = datetime.datetime.fromtimestamp(float(timestamp) / 1000)
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

    def metarAt(self, index):
        """Return the metar at the given index, or None when out of range."""
        records = self.chart.records
        try:
            return records[index]
        except IndexError:
            logger.debug('Metar index %d out of range (%d records)', index, len(records))
            return None

    def setSeriesText(self, items):
        title = self.chart.title()

        points = []
        for _, series, point, index in items:
            name = series.name()
            if name == 'Wind':
                metar = self.metarAt(index)
            else:
                metar = None

            points.append((name, int(point.y()), float(point.x()), metar))

        self.text.setHtml(markerHtml(title, points))

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
        # Divide height by four to create left point
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
        """Place marker for series at position of first point"""
        _, series, point, _ = items[0]
        visible = series.at(0).x() <= point.x() <= series.at(series.count()-1).x() and self.isVisible()
        self.setVisible(visible and series.chart().plotArea().contains(self.pos()))
        self.setPos(series.chart().mapToPosition(point))
        self.setSeriesText(items)
        self.setSeriesColor(series.pen().color())
        self.updateGeometry()


class Chart(QChart):

    def __init__(self):
        super().__init__()
        self.records = []

    def setRecords(self, records):
        self.records = records


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


class ChartViewer(QDialog, Ui_chart.Ui_Chart):

    def __init__(self, parent=None, repository=None, clock=None):
        super().__init__(parent)
        self.setupUi(self)
        self.repository = repository
        self.clock = clock or datetime.datetime.utcnow
        self.dateRange = None

        self.saveButton = self.buttonBox.button(QDialogButtonBox.Save)
        self.saveButton.setText(QCoreApplication.translate('Chart', 'Save'))
        self.calendar.calendarWidget().setHorizontalHeaderFormat(QCalendarWidget.NoHorizontalHeader)
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint)
        self.setStyleSheet(calendarStyle)

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
        title = QCoreApplication.translate('Chart', 'Save to Directory')
        path = QStandardPaths.writableLocation(QStandardPaths.PicturesLocation)
        directory = str(QFileDialog.getExistingDirectory(self, title, path))

        if not directory:
            return

        for view in self.views:
            title = view.chart().title()
            title = title.split('(')[0]
            title = title.replace('/', '&').strip()
            fmt = '%Y-%m-%d %H-%M-%S'
            time = self.dateRange[0].strftime(fmt)
            filename = '{} {}.png'.format(title, time)
            filepath = os.path.join(directory, filename)

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
        utcnow = roundToHalfHour(self.clock())

        if isinstance(date, QDate):
            date = date.toPyDate()

        self.dateRange = computeDateRange(utcnow, self.dateRange, date)

        self.setCalendar()
        self.clearChart()

        try:
            self.drawChart()
        except Exception:
            start, end = self.dateRange
            logger.exception('Failed to draw chart, date range %s - %s', start, end)

    def showEvent(self, event):
        self.updateDateRange()

    def createChart(self, title):
        chart = Chart()
        chart.setTitle(title)
        chart.setMinimumSize(750, 250)
        chart.setAnimationOptions(QChart.SeriesAnimations)
        chart.legend().setVisible(True)
        chart.legend().setAlignment(Qt.AlignBottom)

        return chart

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

        chart.addAxis(axisX, Qt.AlignBottom)

        for s in series:
            s.attachAxis(axisX)

    def addAxisY(self, chart):
        chart.createDefaultAxes()
        chart.removeAxis(chart.axisX())
        chart.axisY().applyNiceNumbers()
        chart.axisY().setLabelFormat('%d')

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

        chart.addAxis(axisY, Qt.AlignLeft)

        for s in series:
            s.attachAxis(axisY)

    def addWindDirectionAxis(self, chart, records):
        series = chart.series()
        if not series:
            return

        tickCount = chart.axisX().tickCount()
        minx = chart.axisX().min().toMSecsSinceEpoch()
        maxx = chart.axisX().max().toMSecsSinceEpoch()

        axisX = QCategoryAxis(chart, labelsPosition=QCategoryAxis.AxisLabelsPositionOnValue)
        axisX.setTickCount(tickCount)
        step = (maxx - minx) / (tickCount - 1)
        for i in range(tickCount):
            tickCountTime = minx + i * step
            timestamp = tickCountTime / 1000
            index = findIndex(records, timestamp)
            metar = chart.records[index]
            label = '<span class="label-{}">{}</span>'.format(i, metar.windDirection('arrow'))
            axisX.append(label, minx + i * step)

        chart.addAxis(axisX, Qt.AlignTop)

        for s in series:
            s.attachAxis(axisX)

    def initChart(self):
        self.views = []
        self.charts = []

        self.windChart = self.createChart('Wind / Gust (m/s)')
        self.visChart = self.createChart('Visibility / RVR (m)')
        self.weatherChart = self.createChart('Weather Phenomenon')
        self.cloudChart = self.createChart('Clouds / Ceiling (m)')
        self.tempdewChart = self.createChart('Temperature / Dewpoint (°C)')
        self.pressureChart = self.createChart('Query Normal Height (hPa)')

        self.charts.append(self.windChart)
        self.charts.append(self.visChart)
        self.charts.append(self.weatherChart)
        self.charts.append(self.cloudChart)
        self.charts.append(self.tempdewChart)
        self.charts.append(self.pressureChart)

        for chart in self.charts:
            view = ChartView(chart)
            view.setRenderHint(QPainter.Antialiasing)
            self.views.append(view)
            self.chartLayout.addWidget(view)

    def clearChart(self):
        for chart in self.charts:
            chart.removeAllSeries()
            for axis in chart.axes():
                chart.removeAxis(axis)

    def drawPhenomenonSeries(self, weathers):
        graphs = []
        for name, points in weatherPoints(weathers).items():
            series = QScatterSeries()
            series.setMarkerSize(8)
            series.setName(name)

            if 'TS' in name or name == 'FG' or 'SH' in name:
                series.setMarkerSize(10)

            for timestamp, value in points:
                series.append(timestamp, value)

            graphs.append(series)

        return graphs

    def drawCloudSeries(self, clouds):
        orders = ['FEW', 'SCT', 'BKN', 'OVC', 'VV', 'TCU', 'CB']
        points = cloudPoints(clouds)

        graphs = []
        for key in orders:
            if key not in points:
                continue

            series = QScatterSeries()
            series.setName(key)
            series.setMarkerSize(8)

            if key in ['TCU', 'CB', 'VV']:
                series.setMarkerSize(10)

            for timestamp, height in points[key]:
                series.append(timestamp, height)

            graphs.append(series)

        return graphs

    def drawChart(self):
        start, end = self.dateRange
        results = self.repository.range(start, end + datetime.timedelta(minutes=20))

        if not results:
            return

        xmin = results[0].created
        xmax = results[-1].created

        winds = QSplineSeries()
        winds.setName('Wind')

        gusts = QScatterSeries()
        gusts.setMarkerSize(8)
        gusts.setColor(Qt.darkYellow)
        gusts.setName('Gust')

        visibilities = QSplineSeries()
        visibilities.setName('Visibility')

        rvrs = QScatterSeries()
        rvrs.setMarkerSize(8)
        rvrs.setColor(Qt.darkCyan)
        rvrs.setName('RVR')

        temperatures = QSplineSeries()
        temperatures.setName('Temperature')

        dewpoints = QSplineSeries()
        dewpoints.setName('Dewpoint')

        pressures = QSplineSeries()
        pressures.setName('Pressure')

        ceilings = QSplineSeries()
        ceilings.setName('Ceiling')

        samples, records = metarSamples(results)

        for chart in self.charts:
            chart.setRecords(records)

        for series, values in (
            (winds, samples['winds']),
            (gusts, samples['gusts']),
            (visibilities, samples['visibilities']),
            (rvrs, samples['rvrs']),
            (temperatures, samples['temperatures']),
            (dewpoints, samples['dewpoints']),
            (pressures, samples['pressures']),
            (ceilings, samples['ceilings']),
        ):
            for timestamp, value in values:
                series.append(timestamp, value)

        self.windChart.addSeries(winds)
        if gusts.count():
            self.windChart.addSeries(gusts)
        self.addAxisY(self.windChart)
        self.addAxisX(self.windChart, xmin, xmax)
        self.addWindDirectionAxis(self.windChart, results)

        self.visChart.addSeries(visibilities)
        if rvrs.count():
            self.visChart.addSeries(rvrs)
        self.addAxisY(self.visChart)
        self.addAxisX(self.visChart, xmin, xmax)
        self.visChart.axisY().setRange(0, 10000)
        self.visChart.axisY().setTickCount(5)

        for series in self.drawPhenomenonSeries(samples['weathers']):
            self.weatherChart.addSeries(series)

        self.addWeatherAxis(self.weatherChart)
        self.addAxisX(self.weatherChart, xmin, xmax)

        self.cloudChart.addSeries(ceilings)

        for series in self.drawCloudSeries(samples['clouds']):
            self.cloudChart.addSeries(series)

        self.addAxisY(self.cloudChart)
        self.addAxisX(self.cloudChart, xmin, xmax)
        self.cloudChart.axisY().setRange(0, 1500)
        self.cloudChart.axisY().setTickCount(4)

        self.tempdewChart.addSeries(temperatures)
        self.tempdewChart.addSeries(dewpoints)
        self.addAxisY(self.tempdewChart)
        self.addAxisX(self.tempdewChart, xmin, xmax)

        self.pressureChart.addSeries(pressures)
        self.addAxisY(self.pressureChart)
        self.addAxisX(self.pressureChart, xmin, xmax)
