import os
import random
import logging
import datetime

from PyQt5.QtGui import QPainter, QColor, QBrush, QPixmap, QPolygonF
from PyQt5.QtCore import QCoreApplication, QStandardPaths, QDate, QPointF, Qt
from PyQt5.QtWidgets import QDialog, QFileDialog, QDialogButtonBox, QCalendarWidget, QGraphicsRectItem, QGraphicsPolygonItem, QGraphicsTextItem
from PyQt5.QtChart import (QChart, QChartView, QSplineSeries, QScatterSeries, QDateTimeAxis, QCategoryAxis)

from tafor.core.repositories import MetarRepository
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
    phenomenons = set()
    for timestamp, codes in weathers:
        if codes:
            enums = list(range(2, 20, 4))
            valueMaps[timestamp] = {
                'weak': enums,
                'normal': [e + 20 for e in enums],
                'strong': [e + 40 for e in enums],
            }

            for code in codes:
                phenomenons.add(stripIntensity(code))

    points = {}
    for name in sorted(phenomenons):
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


class MarkerGraphicsItem(QGraphicsRectItem):
    """Marker graphics item for series data"""

    def __init__(self, chart, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.chart = chart
        self.polygon = QGraphicsPolygonItem(self)
        self.text = QGraphicsTextItem(self)

    def currentMetar(self, series, point):
        try:
            index = series.pointsVector().index(point)
            metar = self.chart.metars[index]
            return metar
        except IndexError:
            pass

    def setSeriesText(self, items):
        title = self.chart.title()

        labels = []
        for _, series, point in items:
            value = int(point.y())
            name = series.name()
            time = datetime.datetime.fromtimestamp(float(point.x()) / 1000)

            if title == 'Weather Phenomenon':
                if value < 20:
                    name = '-' + name
                if value > 40:
                    name = '+' + name

                text = name
            else:
                unit = title.split('(')[-1].replace(')', '')
                text = '{}: {} {}'.format(name, value, unit)

                metar = self.currentMetar(series, point)
                if metar:
                    direction = metar.windDirection()
                    if name == 'Wind' and direction:
                        if direction == 'VRB':
                            text += ' from VRB'
                        else:
                            text += ' from {} ({}°)'.format(metar.windDirection('compass'), direction)

            labels.append(text)

        html = '{:%d %b %H:%M} UTC<br>{}'.format(time, '<br>'.join(labels))
        self.text.setHtml(html)

    def setSeriesColor(self, color):
        # Set primary text and background color
        self.polygon.setBrush(QBrush(color))
        # https://stackoverflow.com/questions/3942878/how-to-decide-font-color-in-white-or-black-depending-on-background-color
        if (color.red()*0.299 + color.green()*0.587 + color.blue()*0.114) > 186:
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
        _, series, point = items[0]
        visible = series.at(0).x() <= point.x() <= series.at(series.count()-1).x() and self.isVisible()
        self.setVisible(visible and series.chart().plotArea().contains(self.pos()))
        self.setPos(series.chart().mapToPosition(point))
        self.setSeriesText(items)
        self.setSeriesColor(series.pen().color())
        self.updateGeometry()


class Chart(QChart):

    def __init__(self):
        super().__init__()
        self.metars = []

    def setMetars(self, metars):
        self.metars = metars


class ChartView(QChartView):
    """Custom chart view class providing points marker"""
    markerRadius = 16

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMarker(MarkerGraphicsItem(self.chart()))

    def setMarker(self, item):
        self.marker = item
        item.setZValue(100)
        self.scene().addItem(item)

    def nearestPoints(self, series, pos):
        items = []
        chart = self.chart()
        for point in series.pointsVector():
            distance = (pos - chart.mapToPosition(point)).manhattanLength()
            items.append((distance, series, point))
        items.sort(key=lambda item: item[0])
        return items

    def mouseMoveEvent(self, event):
        """Draws marker and symbols/labels."""
        chart = self.chart()
        if not chart.series():
            return
        # Position in data
        value = chart.mapToValue(event.pos())
        # Position in plot
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
            distance, series, point = items[0]
            if distance < self.markerRadius:
                samePointItems = list(filter(lambda x: x[2] == point, items))
                self.marker.place(samePointItems)
            else:
                self.marker.setVisible(False)

        super().mouseMoveEvent(event)


class ChartViewer(QDialog, Ui_chart.Ui_Chart):

    def __init__(self, parent=None, database=None):
        super().__init__(parent)
        self.setupUi(self)
        self.metarRepository = MetarRepository(database)

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
        self.calendar.dateChanged.disconnect(self.updateDateRange)
        maxDate = QDate.currentDate()
        start = self.dateRange[0]
        date = QDate(start.year, start.month, start.day)
        self.calendar.calendarWidget().setSelectedDate(date)
        self.calendar.setMaximumDate(maxDate)
        self.calendar.dateChanged.connect(self.updateDateRange)

    def updateDateRange(self, date='latest'):
        utcnow = datetime.datetime.utcnow()
        if utcnow.minute < 30:
            utcnow = utcnow.replace(minute=0, second=0, microsecond=0)
        else:
            utcnow = utcnow.replace(minute=30, second=0, microsecond=0)

        if isinstance(date, QDate):
            date = date.toPyDate()
            start = datetime.datetime(date.year, date.month, date.day)
            self.dateRange = (start, start + datetime.timedelta(hours=24))

        if isinstance(date, int):
            timedelta = datetime.timedelta(hours=date)
            start, _ = self.dateRange
            self.dateRange = (start + timedelta, start + timedelta + datetime.timedelta(hours=24))

        if date == 'latest' or self.dateRange[1] > utcnow:
            self.dateRange = (utcnow - datetime.timedelta(hours=24), utcnow)

        self.setCalendar()
        self.clearChart()

        try:
            self.drawChart()
        except Exception as e:
            start, end = self.dateRange
            logger.error('Failed to draw chart, date range {} - {}, {}'.format(start, end, e))

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

        tickCount = (xmax - xmin).total_seconds() / (3600 * 3)
        tickCount = round(tickCount) + 1

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

        def findIndex(records, timestamp):
            deltas = []
            for record in records:
                delta = abs(record.created.timestamp() - timestamp)
                deltas.append(delta)

            return deltas.index(min(deltas))

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
            metar = chart.metars[index]
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
        series = []
        for name, points in weatherPoints(weathers).items():
            serie = QScatterSeries()
            serie.setMarkerSize(8)
            serie.setName(name)

            if 'TS' in name or name == 'FG' or 'SH' in name:
                serie.setMarkerSize(10)

            for timestamp, value in points:
                serie.append(timestamp, value)

            series.append(serie)

        return series

    def drawCloudSeries(self, clouds):
        orders = ['FEW', 'SCT', 'BKN', 'OVC', 'VV', 'TCU', 'CB']
        points = cloudPoints(clouds)

        series = []
        for key in orders:
            if key not in points:
                continue

            serie = QScatterSeries()
            serie.setName(key)
            serie.setMarkerSize(8)

            if key in ['TCU', 'CB', 'VV']:
                serie.setMarkerSize(10)

            for timestamp, height in points[key]:
                serie.append(timestamp, height)

            series.append(serie)

        return series

    def drawChart(self):
        start, end = self.dateRange
        results = self.metarRepository.range(start, end + datetime.timedelta(minutes=20))

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

        clouds = []
        weathers = []

        metars = []

        for m in results:
            metar = m.parser().primary
            timestamp = round(m.created.timestamp() * 1000)

            metars.append(metar)

            winds.append(timestamp, metar.windSpeed())
            visibilities.append(timestamp, metar.vis())
            ceilings.append(timestamp, metar.ceiling())
            temperatures.append(timestamp, metar.temperature())
            dewpoints.append(timestamp, metar.dewpoint())
            pressures.append(timestamp, metar.pressure())

            clouds.append((timestamp, metar.clouds()))

            if metar.weathers():
                weathers.append((timestamp, metar.weathers()))

            if metar.rvr():
                rvrs.append(timestamp, metar.rvr())

            if metar.gust():
                gusts.append(timestamp, metar.gust())


        for chart in self.charts:
            chart.setMetars(metars)

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

        for serie in self.drawPhenomenonSeries(weathers):
            self.weatherChart.addSeries(serie)

        self.addWeatherAxis(self.weatherChart)
        self.addAxisX(self.weatherChart, xmin, xmax)

        self.cloudChart.addSeries(ceilings)

        for serie in self.drawCloudSeries(clouds):
            self.cloudChart.addSeries(serie)

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
