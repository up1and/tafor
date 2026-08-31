import datetime
import random

from tafor.core.models import Metar
from tafor.ui.components.chart import (
    cloudPoints,
    computeDateRange,
    computeTickCount,
    findIndex,
    isLightColor,
    markerHtml,
    metarSamples,
    roundToHalfHour,
    weatherPoints,
)


def metarRecord(text, created):
    return Metar(type='SA', text=text, created=created)


class TestWeatherPoints:

    def test_groups_by_stripped_phenomenon(self):
        random.seed(1)
        points = weatherPoints([(1000, ['TSRA', '-SHRA', 'FG'])])
        assert sorted(points.keys()) == ['FG', 'SHRA', 'TSRA']
        assert [t for t, _ in points['FG']] == [1000]

    def test_intensity_selects_value_band(self):
        random.seed(2)
        points = weatherPoints([(1000, ['-DZ']), (2000, ['DZ']), (3000, ['+DZ'])])
        values = dict(points['DZ'])
        assert values[1000] in [2, 6, 10, 14, 18]
        assert values[2000] in [22, 26, 30, 34, 38]
        assert values[3000] in [42, 46, 50, 54, 58]

    def test_no_duplicate_values_within_timestamp(self):
        # two weak phenomena at the same timestamp draw from the same
        # shrinking pool, so their y-values never collide
        random.seed(3)
        points = weatherPoints([(1000, ['-SHRA', '-SN'])])
        ys = [value for group in points.values() for _, value in group]
        assert len(set(ys)) == len(ys)

    def test_empty_codes_are_ignored(self):
        random.seed(4)
        points = weatherPoints([(1000, []), (2000, ['RA'])])
        assert list(points.keys()) == ['RA']
        assert [t for t, _ in points['RA']] == [2000]

    def test_sorted_by_phenomenon_name(self):
        random.seed(5)
        points = weatherPoints([(1000, ['SN', 'RA', 'FG'])])
        assert list(points.keys()) == ['FG', 'RA', 'SN']


class TestCloudPoints:

    def test_height_is_digits_times_thirty_metres(self):
        points = cloudPoints([(1000, ['FEW030'])])
        assert points['FEW'] == [(1000, 900)]

    def test_containment_kinds(self):
        points = cloudPoints([
            (1000, ['VV002']),
            (2000, ['BKN040CB']),
            (3000, ['SCT018TCU']),
        ])
        assert points['VV'] == [(1000, 60)]
        assert points['CB'] == [(2000, 1200)]
        assert points['TCU'] == [(3000, 540)]
        assert 'SCT' not in points

    def test_plain_prefixes(self):
        points = cloudPoints([(1000, ['FEW030', 'SCT040', 'BKN050', 'OVC008'])])
        assert points['FEW'] == [(1000, 900)]
        assert points['SCT'] == [(1000, 1200)]
        assert points['BKN'] == [(1000, 1500)]
        assert points['OVC'] == [(1000, 240)]

    def test_multiple_layers_share_kind(self):
        points = cloudPoints([(1000, ['FEW030']), (2000, ['FEW010'])])
        assert points['FEW'] == [(1000, 900), (2000, 300)]

    def test_empty_layers(self):
        assert cloudPoints([(1000, [])]) == {}

class TestMetarSamples:

    def test_quantity_series(self):
        created = datetime.datetime(2026, 8, 31, 12, 0)
        record = metarRecord('YUSO 311200Z 12012KT 9999 -SHRA SCT030 BKN045 28/20 Q1013', created)
        samples, primaries = metarSamples([record])
        ts = round(created.timestamp() * 1000)

        assert samples['winds'] == [(ts, 12)]
        assert samples['visibilities'] == [(ts, 9999)]
        assert samples['ceilings'] == [(ts, 1350)]
        assert samples['temperatures'] == [(ts, 28)]
        assert samples['dewpoints'] == [(ts, 20)]
        assert samples['pressures'] == [(ts, 1013)]
        assert samples['clouds'] == [(ts, ['SCT030', 'BKN045'])]
        assert samples['weathers'] == [(ts, ['-SHRA'])]
        assert samples['gusts'] == []
        assert samples['rvrs'] == []
        assert len(primaries) == 1

    def test_gust_and_rvr_only_when_present(self):
        created = datetime.datetime(2026, 8, 31, 12, 0)
        record = metarRecord('YUSO 311200Z 12012G20KT 0800 R24/1000 FG VV002 10/09 Q1013', created)
        samples, _ = metarSamples([record])
        ts = round(created.timestamp() * 1000)

        assert samples['gusts'] == [(ts, 20)]
        assert samples['rvrs'] == [(ts, 1000)]

    def test_empty_input(self):
        samples, primaries = metarSamples([])
        assert primaries == []
        assert all(values == [] for values in samples.values())


class TestRoundToHalfHour:

    def test_rounds_down_to_hour(self):
        dt = datetime.datetime(2026, 8, 31, 14, 23, 45)
        assert roundToHalfHour(dt) == datetime.datetime(2026, 8, 31, 14, 0)

    def test_rounds_down_to_half_hour(self):
        dt = datetime.datetime(2026, 8, 31, 14, 45)
        assert roundToHalfHour(dt) == datetime.datetime(2026, 8, 31, 14, 30)

    def test_keeps_half_hour(self):
        dt = datetime.datetime(2026, 8, 31, 14, 30, 59)
        assert roundToHalfHour(dt) == datetime.datetime(2026, 8, 31, 14, 30)


class TestComputeDateRange:

    utcnow = datetime.datetime(2026, 8, 31, 14, 0)
    current = (datetime.datetime(2026, 8, 30, 14, 0), utcnow)

    def test_latest_does_not_read_current_range(self):
        start, end = computeDateRange(self.utcnow, None, 'latest')
        assert start == datetime.datetime(2026, 8, 30, 14, 0)
        assert end == self.utcnow

    def test_hour_offset(self):
        start, end = computeDateRange(self.utcnow, self.current, -3)
        assert start == datetime.datetime(2026, 8, 30, 11, 0)
        assert end == datetime.datetime(2026, 8, 31, 11, 0)

    def test_date_selection(self):
        start, end = computeDateRange(self.utcnow, self.current, datetime.date(2026, 8, 29))
        assert start == datetime.datetime(2026, 8, 29, 0, 0)
        assert end == datetime.datetime(2026, 8, 30, 0, 0)

    def test_future_end_falls_back_to_latest(self):
        future = (datetime.datetime(2026, 8, 31, 0, 0), datetime.datetime(2026, 9, 1, 0, 0))
        start, end = computeDateRange(self.utcnow, future, 24)
        assert start == datetime.datetime(2026, 8, 30, 14, 0)
        assert end == self.utcnow


class TestComputeTickCount:

    def test_three_hourly_ticks(self):
        start = datetime.datetime(2026, 8, 30, 14, 0)
        assert computeTickCount(start, start + datetime.timedelta(hours=24)) == 9


class TestFindIndex:

    def test_nearest_record(self):
        records = [
            metarRecord('A', datetime.datetime(2026, 8, 31, 12, 0)),
            metarRecord('B', datetime.datetime(2026, 8, 31, 12, 30)),
            metarRecord('C', datetime.datetime(2026, 8, 31, 13, 0)),
        ]
        assert findIndex(records, datetime.datetime(2026, 8, 31, 12, 20).timestamp()) == 1
        assert findIndex(records, datetime.datetime(2026, 8, 31, 12, 40).timestamp()) == 1
        assert findIndex(records, datetime.datetime(2026, 8, 31, 12, 55).timestamp()) == 2


class MetarStub:

    def windDirection(self, style='degree'):
        return 'SE' if style == 'compass' else 120


class VrbMetarStub:

    def windDirection(self, style='degree'):
        return 'VRB'


class TestMarkerHtml:

    def test_weather_phenomenon_intensity(self):
        html = markerHtml('Weather Phenomenon', [('SHRA', 14, 0, None)])
        assert '-SHRA' in html

    def test_unit_parsed_from_title(self):
        html = markerHtml('Wind / Gust (m/s)', [('Wind', 12, 0, None)])
        assert 'Wind: 12 m/s' in html

    def test_wind_direction_suffix(self):
        html = markerHtml('Wind / Gust (m/s)', [('Wind', 12, 0, MetarStub())])
        assert 'from SE (120\u00b0)' in html

    def test_wind_vrb(self):
        html = markerHtml('Wind / Gust (m/s)', [('Wind', 12, 0, VrbMetarStub())])
        assert 'from VRB' in html


class TestIsLightColor:

    def test_dark_background(self):
        assert not isLightColor(0, 0, 0)

    def test_light_background(self):
        assert isLightColor(255, 255, 255)

    def test_threshold(self):
        assert isLightColor(200, 200, 200)


class TestChartViewer:

    def test_update_date_range_branches(self, qtbot, database):
        from tafor.core.repositories import MetarRepository
        from tafor.ui.components.chart import ChartViewer

        viewer = ChartViewer(None, repository=MetarRepository(database))
        qtbot.addWidget(viewer)

        viewer.updateDateRange('latest')
        viewer.updateDateRange(-3)
        viewer.updateDateRange(3)
        viewer.updateDateRange(-24)
        viewer.updateDateRange(24)

        assert len(viewer.charts) == 6
        assert all(len(chart.records) == 0 for chart in viewer.charts)

    def test_clock_injection(self, qtbot, database):
        from tafor.core.repositories import MetarRepository
        from tafor.ui.components.chart import ChartViewer

        def fixedClock():
            return datetime.datetime(2026, 8, 31, 14, 23)

        viewer = ChartViewer(None, repository=MetarRepository(database), clock=fixedClock)
        qtbot.addWidget(viewer)

        viewer.updateDateRange('latest')

        assert viewer.dateRange[1] == datetime.datetime(2026, 8, 31, 14, 0)

