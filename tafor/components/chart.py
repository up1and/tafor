import datetime

from PyQt5.QtGui import QPainter, QColor, QImage, QBrush
from PyQt5.QtCore import QCoreApplication, QDate, Qt
from PyQt5.QtWidgets import QDialog
from PyQt5.QtChart import (QChart, QChartView, QSplineSeries, QLineSeries, QScatterSeries, QAreaSeries,
    QDateTimeAxis, QLogValueAxis, QValueAxis, QCategoryAxis)

from tafor.models import db, Metar
from tafor.utils import MetarParser
from tafor.components.ui import Ui_chart, main_rc


class ChartViewer(QDialog, Ui_chart.Ui_Chart):

    def __init__(self, parent=None):
        super(ChartViewer, self).__init__(parent)
        self.setupUi(self)

        self.bindSignal()
        self.initChart()

    def bindSignal(self):
        self.dayAgoButton.clicked.connect(lambda: self.updateDateRange(-24))
        self.dayLaterButton.clicked.connect(lambda: self.updateDateRange(24))
        self.hoursAgoButton.clicked.connect(lambda: self.updateDateRange(-3))
        self.hoursLaterButton.clicked.connect(lambda: self.updateDateRange(3))
        self.latestButton.clicked.connect(lambda: self.updateDateRange('latest'))
        self.calendar.dateChanged.connect(self.updateDateRange)

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
        self.drawChart()

    def queryset(self):
        start, end = self.dateRange
        query = db.query(Metar).filter(Metar.created >= start, Metar.created < end + datetime.timedelta(minutes=20)) \
            .order_by(Metar.created.desc()).all()
        # query = db.query(Metar).order_by(Metar.created.desc()).limit(25).all()

        query.reverse()

        return query

    def showEvent(self, event):
        self.updateDateRange()

    def createChart(self, title):
        chart = QChart()
        chart.setTitle(title)
        chart.setMinimumSize(720, 250)
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

    def addWindDirectionAxis(self, chart, queryset):
        series = chart.series()
        if not series:
            return

        def findIndex(queryset, timestamp):
            deltas = []
            for q in queryset:
                delta = abs(q.created.timestamp() - timestamp)
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
            index = findIndex(queryset, timestamp)
            metar = queryset[index].parser().primary
            label = '<span class="label-{}">{}</span>'.format(i, metar.windDirection)
            axisX.append(label, minx + i * step)

        chart.addAxis(axisX, Qt.AlignTop)

        for s in series:
            s.attachAxis(axisX)

    def initChart(self):
        self.charts = []

        self.windChart = self.createChart('Wind / Gust (m/s)')
        self.visChart = self.createChart('Visibility / RVR (m)')
        self.weatherChart = self.createChart('Weather Phenomenon')
        # self.cloudChart = self.createChart('Clouds (m)')
        self.tempdewChart = self.createChart('Temperature / Dewpoint (°C)')
        self.pressureChart = self.createChart('Query Normal Height (hPa)')

        self.charts.append(self.windChart)
        self.charts.append(self.visChart)
        self.charts.append(self.weatherChart)
        # self.charts.append(self.cloudChart)
        self.charts.append(self.tempdewChart)
        self.charts.append(self.pressureChart)

        for chart in self.charts:
            view = QChartView(chart)
            view.setRenderHint(QPainter.Antialiasing)
            self.chartLayout.addWidget(view)

    def clearChart(self):
        for chart in self.charts:
            chart.removeAllSeries()
            for axis in chart.axes():
                chart.removeAxis(axis)

    def drawPhenomenonSeries(self, phenomenons, weathers):

        def findWeather(name, weathers):
            for weather in weathers:
                if name in weather:
                    return weather

        valueMaps = {}
        for timestamp, weather in weathers:
            if weather:
                enums = [16, 4, 13, 7, 10]
                values = {
                    'weak': enums,
                    'normal': [e + 20 for e in enums],
                    'strong': [e + 40 for e in enums]
                }
                valueMaps[timestamp] = values

        series = []
        for name in set(phenomenons):
            serie = QScatterSeries()
            serie.setMarkerSize(8)
            serie.setName(name)

            if 'RA' in name:
                serie.setColor(Qt.green)
                serie.setMarkerShape(QScatterSeries.MarkerShapeRectangle)

            if 'TS' in name:
                serie.setColor(Qt.red)
                serie.setMarkerShape(QScatterSeries.MarkerShapeRectangle)

            if 'FG' == name:
                serie.setColor(Qt.yellow)
                serie.setMarkerShape(QScatterSeries.MarkerShapeRectangle)

            for timestamp, weather in weathers:
                text = findWeather(name, weather)
                if text:
                    values = valueMaps[timestamp]
                    enums = values['normal']

                    if text.startswith('-'):
                        enums = values['weak']

                    if text.startswith('+'):
                        enums = values['strong']

                    serie.append(timestamp, enums.pop())

            series.append(serie)

        return series

    def drawCloudSeries(self, clouds):
        series = []

        serie = QSplineSeries()
        serie.setName('Cloud')

        for timestamp, cloud in clouds:
            cover, height = cloud
            serie.append(timestamp, height)
            bkns.append(timestamp, height + cover * 10)


        series.append(serie)

        return series

    def drawChart(self):
        queries = self.queryset()

        if not queries:
            return

        xmin = queries[0].created
        xmax = queries[-1].created

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

        clouds = []
        weathers = []
        phenomenons = []

        for q in queries:
            metar = q.parser().primary
            timestamp = round(q.created.timestamp() * 1000)

            winds.append(timestamp, metar.windSpeed)
            visibilities.append(timestamp, metar.vis)
            temperatures.append(timestamp, metar.temperature)
            dewpoints.append(timestamp, metar.dewpoint)
            pressures.append(timestamp, metar.pressure)

            weathers.append((timestamp, metar.weather.split()))
            phenomenons += metar.phenomenons

            # clouds.append((timestamp, metar.cloud))

            if metar.rvr:
                rvrs.append(timestamp, metar.rvr)

            if metar.gust:
                gusts.append(timestamp, metar.gust)


        self.windChart.addSeries(winds)
        self.windChart.addSeries(gusts)
        self.addAxisY(self.windChart)
        self.addAxisX(self.windChart, xmin, xmax)
        self.addWindDirectionAxis(self.windChart, queries)

        self.visChart.addSeries(visibilities)
        self.visChart.addSeries(rvrs)
        self.addAxisY(self.visChart)
        self.addAxisX(self.visChart, xmin, xmax)

        for serie in self.drawPhenomenonSeries(phenomenons, weathers):
            self.weatherChart.addSeries(serie)

        self.addWeatherAxis(self.weatherChart)
        self.addAxisX(self.weatherChart, xmin, xmax)
        
        # for serie in self.drawCloudSeries(clouds):
        #     self.cloudChart.addSeries(serie)

        # self.addAxisY(self.cloudChart)
        # self.addAxisX(self.cloudChart, xmin, xmax)

        self.tempdewChart.addSeries(temperatures)
        self.tempdewChart.addSeries(dewpoints)
        self.addAxisY(self.tempdewChart)
        self.addAxisX(self.tempdewChart, xmin, xmax)

        self.pressureChart.addSeries(pressures)
        self.addAxisY(self.pressureChart)
        self.addAxisX(self.pressureChart, xmin, xmax)