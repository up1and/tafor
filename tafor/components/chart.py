import datetime

from PyQt5.QtGui import QPainter
from PyQt5.QtCore import QCoreApplication, QDate, Qt
from PyQt5.QtWidgets import QDialog
from PyQt5.QtChart import QChart, QChartView, QSplineSeries, QScatterSeries, QDateTimeAxis, QLogValueAxis, QValueAxis, QCategoryAxis

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
        self.tempdewChart = self.createChart('Temperature / Dewpoint (°C)')
        self.pressureChart = self.createChart('Query Normal Height (hPa)')

        self.charts.append(self.windChart)
        self.charts.append(self.visChart)
        self.charts.append(self.tempdewChart)
        self.charts.append(self.pressureChart)

        for chart in self.charts:
            view = QChartView(chart)
            view.setRenderHint(QPainter.Antialiasing)
            self.chartLayout.addWidget(view)

    def clearChart(self):
        for chart in self.charts:
            chart.removeAllSeries()

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

        for q in queries:
            metar = q.parser().primary
            timestamp = round(q.created.timestamp() * 1000)

            winds.append(timestamp, metar.windSpeed)
            visibilities.append(timestamp, metar.vis)
            temperatures.append(timestamp, metar.temperature)
            dewpoints.append(timestamp, metar.dewpoint)
            pressures.append(timestamp, metar.pressure)

            if metar.rvr:
                rvrs.append(timestamp, metar.rvr)

            if metar.gust:
                gusts.append(timestamp, metar.gust)


        self.windChart.addSeries(winds)
        self.windChart.addSeries(gusts)
        self.addAxisY(self.windChart)
        self.addAxisX(self.windChart, xmin, xmax)
        self.addWindDirectionAxis(self.windChart, queries)

        self.tempdewChart.addSeries(temperatures)
        self.tempdewChart.addSeries(dewpoints)
        self.addAxisY(self.tempdewChart)
        self.addAxisX(self.tempdewChart, xmin, xmax)

        self.pressureChart.addSeries(pressures)
        self.addAxisY(self.pressureChart)
        self.addAxisX(self.pressureChart, xmin, xmax)

        self.visChart.addSeries(visibilities)
        self.visChart.addSeries(rvrs)
        self.addAxisY(self.visChart)
        self.addAxisX(self.visChart, xmin, xmax)