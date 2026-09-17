import datetime

from tafor.core.models import Metar
from tafor.ui.components.chart import (
    ChartSpec,
    cloudPoints,
    computeDateRange,
    computeTickCount,
    findIndex,
    isLightColor,
    markerHtml,
    metarSamples,
    roundToHalfHour,
    weatherMarkerSize,
    weatherPoints,
)


def metar_record(text, created):
    return Metar(type='SA', text=text, created=created)


def pairs(samples):
    """The (timestamp, value) pairs of a sample list."""
    return [(sample.timestamp, sample.value) for sample in samples]


class TestWeatherPoints:

    def test_key_is_the_code_as_reported(self):
        # the intensity prefix stays on the key: Qt gives a series a single
        # marker size, so a phenomenon has to be split into one series per
        # intensity for the size to be able to follow it
        points = weatherPoints([(1000, ['TSRA', '-SHRA', 'FG'])])
        assert sorted(points.keys()) == ['-SHRA', 'FG', 'TSRA']
        assert [t for t, _ in points['FG']] == [1000]

    def test_intensities_of_one_phenomenon_stay_together(self):
        # and in intensity order, so the legend reads light to heavy rather
        # than '-RA' first and the rest by ASCII
        points = weatherPoints([(1000, ['-RA', 'RA', '+RA'])])
        assert list(points.keys()) == ['-RA', 'RA', '+RA']

    def test_intensity_selects_value_band(self):
        # one code per report, so each is the only one in its band
        points = weatherPoints([(1000, ['-DZ']), (2000, ['DZ']), (3000, ['+DZ'])])
        assert 2 <= points['-DZ'][0][1] <= 18
        assert 22 <= points['DZ'][0][1] <= 38
        assert 42 <= points['+DZ'][0][1] <= 58

    def test_a_lone_phenomenon_draws_mid_band(self):
        # there is nothing for it to avoid overlapping with, so it belongs in
        # the middle of its band rather than against either edge, where it
        # would sit close to the boundary with the next intensity
        points = weatherPoints([(1000, ['-DZ']), (2000, ['DZ']), (3000, ['+DZ'])])
        assert [points[key][0][1] for key in ('-DZ', 'DZ', '+DZ')] == [10, 30, 50]

    def test_three_codes_in_a_band_are_spread_evenly(self):
        # the whole reason these are scattered is that simultaneous phenomena
        # must not hide one another, so the usual case of three codes has to
        # come out spread across the band. Pinned exactly, because the fixed
        # seed is what makes it true: changing the seed has to be deliberate.
        points = weatherPoints([(1000, ['-SHRA', '-SN', '-DZ'])])
        values = sorted(value for group in points.values() for _, value in group)

        assert values == [2, 10, 18]

    def test_no_duplicate_values_within_timestamp(self):
        points = weatherPoints([(1000, ['-SHRA', '-SN', '-DZ'])])
        ys = [value for group in points.values() for _, value in group]
        assert len(set(ys)) == len(ys)

    def test_layout_is_reproducible(self):
        # guards the fixed seed: the same report has to draw in the same place
        # every time the window is redrawn
        assert weatherPoints([(1000, ['-SHRA', '-SN'])]) == weatherPoints([(1000, ['-SHRA', '-SN'])])

    def test_report_order_does_not_matter(self):
        assert weatherPoints([(1000, ['-SN', '-SHRA'])]) == weatherPoints([(1000, ['-SHRA', '-SN'])])

    def test_layout_does_not_depend_on_earlier_reports(self):
        # each report draws from its own generator, so whatever came before it
        # in the window must not move its points
        alone = weatherPoints([(2000, ['-SHRA', '-SN'])])
        after = weatherPoints([(1000, ['-DZ', '-RA']), (2000, ['-SHRA', '-SN'])])

        assert dict(after['-SHRA']) == dict(alone['-SHRA'])
        assert dict(after['-SN']) == dict(alone['-SN'])

    def test_empty_codes_are_ignored(self):
        points = weatherPoints([(1000, []), (2000, ['RA'])])
        assert list(points.keys()) == ['RA']
        assert [t for t, _ in points['RA']] == [2000]

    def test_ordered_by_phenomenon_then_intensity(self):
        # the legend is built in this order, so it reads as a list of
        # phenomena rather than as whatever ASCII order the raw codes have
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
        record = metar_record('YUSO 311200Z 12012KT 9999 -SHRA SCT030 BKN045 28/20 Q1013', created)
        samples, reports = metarSamples([record])
        ts = round(created.timestamp() * 1000)

        assert pairs(samples['winds']) == [(ts, 12)]
        assert pairs(samples['visibilities']) == [(ts, 9999)]
        assert pairs(samples['ceilings']) == [(ts, 1350)]
        assert pairs(samples['temperatures']) == [(ts, 28)]
        assert pairs(samples['dewpoints']) == [(ts, 20)]
        assert pairs(samples['pressures']) == [(ts, 1013)]
        assert pairs(samples['clouds']) == [(ts, ['SCT030', 'BKN045'])]
        assert pairs(samples['weathers']) == [(ts, ['-SHRA'])]
        assert samples['gusts'] == []
        assert samples['rvrs'] == []
        assert len(reports) == 1

    def test_gust_and_rvr_only_when_present(self):
        created = datetime.datetime(2026, 8, 31, 12, 0)
        record = metar_record('YUSO 311200Z 12012G20KT 0800 R24/1000 FG VV002 10/09 Q1013', created)
        samples, _ = metarSamples([record])
        ts = round(created.timestamp() * 1000)

        assert pairs(samples['gusts']) == [(ts, 20)]
        assert pairs(samples['rvrs']) == [(ts, 1000)]

    def test_zero_is_a_value_not_a_missing_element(self):
        # calm wind and freezing temperature are observations, not gaps
        created = datetime.datetime(2026, 8, 31, 12, 0)
        record = metar_record('YUSO 311200Z 00000KT 9999 SCT030 00/M02 Q1013', created)
        samples, _ = metarSamples([record])

        assert pairs(samples['winds']) == [(round(created.timestamp() * 1000), 0)]
        assert pairs(samples['temperatures']) == [(round(created.timestamp() * 1000), 0)]
        assert pairs(samples['dewpoints']) == [(round(created.timestamp() * 1000), -2)]

    def test_one_unparsable_report_does_not_blank_the_window(self):
        # VV/// passes the lexer but cannot be turned into a height, so the
        # record is dropped and the rest of the window still draws
        created = datetime.datetime(2026, 8, 31, 12, 0)
        good = metar_record('YUSO 311200Z 12012KT 9999 -SHRA SCT030 28/20 Q1013', created)
        bad = metar_record('YUSO 311230Z 27012KT 0500 VV/// 10/09 Q1013', created + datetime.timedelta(minutes=30))

        samples, reports = metarSamples([good, bad])

        assert len(reports) == 1
        assert len(samples['winds']) == 1
        assert pairs(samples['weathers']) == [(round(created.timestamp() * 1000), ['-SHRA'])]

    def test_empty_input(self):
        samples, reports = metarSamples([])
        assert reports == []
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
            metar_record('A', datetime.datetime(2026, 8, 31, 12, 0)),
            metar_record('B', datetime.datetime(2026, 8, 31, 12, 30)),
            metar_record('C', datetime.datetime(2026, 8, 31, 13, 0)),
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

    def test_weather_label_is_the_name_alone(self):
        # the weather chart's series are named by the code as reported, so the
        # tooltip is the name and nothing else: no unit, no value, and the
        # intensity prefix is not recovered from the value
        html = markerHtml([('-SHRA', 14, 0, None)], weather=True)
        assert html.endswith('-SHRA')

    def test_weather_label_keeps_the_reported_intensity(self):
        html = markerHtml([('+TSRA', 46, 0, None)], weather=True)
        assert html.endswith('+TSRA')

    def test_a_unitless_chart_still_prints_its_value(self):
        # the weather chart is recognised by spec.weather, not by having no
        # unit, so a unit-less chart of real measurements still shows them --
        # and without a trailing space where the unit would have been
        html = markerHtml([('Ceiling', 1350, 0, None)])
        assert html.endswith('Ceiling: 1350')

    def test_unit_comes_from_the_caller(self):
        html = markerHtml([('Wind', 12, 0, None)], 'm/s')
        assert 'Wind: 12 m/s' in html

    def test_wind_direction_suffix(self):
        html = markerHtml([('Wind', 12, 0, MetarStub())], 'm/s')
        assert 'from SE (120\u00b0)' in html

    def test_wind_vrb(self):
        html = markerHtml([('Wind', 12, 0, VrbMetarStub())], 'm/s')
        assert 'from VRB' in html


class TestWeatherMarkerSize:

    def test_the_prefix_is_the_whole_rule(self):
        # the size ladder is the intensity ladder: light, none, heavy
        assert weatherMarkerSize('-RA') == 8
        assert weatherMarkerSize('RA') == 9
        assert weatherMarkerSize('+RA') == 10
        assert weatherMarkerSize('TSRA') == weatherMarkerSize('RA') == 9
        assert weatherMarkerSize('-TSRA') == weatherMarkerSize('-RA') == 8


class TestIsLightColor:

    def test_dark_background(self):
        assert not isLightColor(0, 0, 0)

    def test_light_background(self):
        assert isLightColor(255, 255, 255)

    def test_threshold(self):
        assert isLightColor(200, 200, 200)


class TestWeatherPointsOverflow:

    def test_overflow_reuses_the_band(self):
        # a band holds five 4-unit slots; a sixth code has nowhere left to go
        # and must stay in its own band rather than spill into the
        # neighbouring one, which carries a different intensity. Staying means
        # it can land on a slot another code already took: six phenomena of
        # one intensity is well past the three a report realistically carries,
        # so the overlap is accepted rather than designed around
        codes = ['-SHRA', '-SN', '-DZ', '-RA', '-FG', '-BR']
        values = [value for group in weatherPoints([(1000, codes)]).values() for _, value in group]

        assert len(values) == len(codes)
        assert all(2 <= value <= 18 for value in values)


class TestChartSpec:

    def test_caption_appends_the_unit(self):
        # the unit is carried as data, so the title does not repeat it and
        # nothing has to strip it back out again
        assert ChartSpec('Wind / Gust', unit='m/s').caption == 'Wind / Gust (m/s)'

    def test_caption_without_a_unit_is_bare(self):
        assert ChartSpec('Weather Phenomenon').caption == 'Weather Phenomenon'

    def test_the_default_captions_are_unchanged(self):
        # the unit used to be written into each title by hand; composing it has
        # to produce exactly the same six strings the chart used to show
        from tafor.ui.components.chart import ChartViewer

        assert [spec.caption for spec in ChartViewer.specs] == [
            'Wind / Gust (m/s)',
            'Visibility / RVR (m)',
            'Weather Phenomenon',
            'Clouds / Ceiling (m)',
            'Temperature / Dewpoint (\u00b0C)',
            'Query Normal Height (hPa)',
        ]


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

        assert len(viewer.views) == 6
        assert all(view.chart().samples == {} for view in viewer.views)

    def test_clock_injection(self, qtbot, database):
        from tafor.core.repositories import MetarRepository
        from tafor.ui.components.chart import ChartViewer

        def fixedClock():
            return datetime.datetime(2026, 8, 31, 14, 23)

        viewer = ChartViewer(None, repository=MetarRepository(database), clock=fixedClock)
        qtbot.addWidget(viewer)

        viewer.updateDateRange('latest')

        assert viewer.dateRange[1] == datetime.datetime(2026, 8, 31, 14, 0)

    def build_viewer(self, database, texts, clock):
        from tafor.core.models import Metar
        from tafor.core.repositories import MetarRepository
        from tafor.ui.components.chart import ChartViewer

        with database.session() as session:
            for text, created in texts:
                session.add(Metar(type='SA', text=text, created=created))

        viewer = ChartViewer(None, repository=MetarRepository(database), clock=lambda: clock)
        viewer.updateDateRange('latest')

        return viewer

    def test_every_chart_is_built_from_the_window(self, qtbot, database):
        # the window is drawn end to end, so the code path from samples to
        # series and axes is covered, not just the pure helpers
        created = datetime.datetime(2026, 8, 31, 12, 0)
        viewer = self.build_viewer(database, [
            ('YUSO 311200Z 12012KT 9999 -SHRA SCT030 BKN045 28/20 Q1013', created),
        ], created)
        qtbot.addWidget(viewer)

        names = [[series.name() for series in view.chart().series()] for view in viewer.views]

        assert names == [
            ['Wind'],
            ['Visibility'],
            ['-SHRA'],
            ['Ceiling', 'SCT', 'BKN'],
            ['Temperature', 'Dewpoint'],
            ['Pressure'],
        ]
        assert all(view.chart().axisX() is not None for view in viewer.views if view.chart().series())

    def test_heavy_weather_draws_a_bigger_marker(self, qtbot, database):
        # the weather chart's series are keyed by the code as reported, so one
        # phenomenon reported at three intensities arrives as three series and
        # the marker size has something to follow. Qt gives a series one size,
        # so this is the only way the size can vary within one phenomenon.
        created = datetime.datetime(2026, 8, 31, 12, 0)
        viewer = self.build_viewer(database, [
            ('YUSO 311200Z 12012KT 9999 -RA SCT030 28/20 Q1013', created),
            ('YUSO 311215Z 12012KT 9999 RA SCT030 28/20 Q1013', created + datetime.timedelta(minutes=15)),
            ('YUSO 311230Z 12012KT 9999 +RA SCT030 28/20 Q1013', created + datetime.timedelta(minutes=30)),
        ], created + datetime.timedelta(hours=1))
        qtbot.addWidget(viewer)

        weather = viewer.views[2].chart()
        sizes = {series.name(): series.markerSize() for series in weather.series()}

        assert sizes == {'-RA': 8, 'RA': 9, '+RA': 10}
        # and the bands they sit in, which the sizes now mirror
        bands = {series.name(): int(series.at(0).y()) for series in weather.series()}
        assert bands['-RA'] < bands['RA'] < bands['+RA']

    def test_wind_tooltip_uses_the_report_behind_the_point(self, qtbot, database):
        # the wind series skips the report that has no wind group, so its
        # point index must not be used to index the list of reports
        created = datetime.datetime(2026, 8, 31, 12, 0)
        viewer = self.build_viewer(database, [
            ('YUSO 311200Z 9999 SCT030 28/20 Q1013', created),
            ('YUSO 311230Z 27015KT 9999 SCT030 28/20 Q1013', created + datetime.timedelta(minutes=30)),
        ], created + datetime.timedelta(hours=1))
        qtbot.addWidget(viewer)

        chart = viewer.views[0].chart()
        series = chart.series()[0]

        assert series.count() == 1
        assert chart.metarAt(series, 0).windDirection() == 270

    def test_a_single_report_window_still_draws(self, qtbot, database):
        # a one report window leaves nothing to interpolate between, which
        # used to divide by zero in the wind direction axis
        created = datetime.datetime(2026, 8, 31, 12, 0)
        viewer = self.build_viewer(database, [
            ('YUSO 311200Z 27015KT 9999 SCT030 28/20 Q1013', created),
        ], created)
        qtbot.addWidget(viewer)

        wind = viewer.views[0].chart()
        assert wind.series()[0].count() == 1
        assert wind.axisX() is not None

    def test_wind_direction_axis_labels_every_x_tick(self, qtbot, database):
        # the arrows ride on a category axis of their own, one per x tick.
        # The markup around them is load bearing even though nothing styles
        # .label-*: without it Qt lays the label out differently and the
        # gridline antialiasing shifts, so the render stops matching.
        from PyQt5.QtCore import Qt

        created = datetime.datetime(2026, 8, 31, 12, 0)
        viewer = self.build_viewer(database, [
            ('YUSO 311200Z 27015KT 9999 SCT030 28/20 Q1013', created),
            ('YUSO 311230Z 24008KT 9999 SCT030 28/20 Q1013', created + datetime.timedelta(minutes=30)),
        ], created + datetime.timedelta(hours=1))
        qtbot.addWidget(viewer)

        chart = viewer.views[0].chart()
        top = [axis for axis in chart.axes() if axis.alignment() == Qt.AlignTop]
        bottom = [axis for axis in chart.axes() if axis.alignment() == Qt.AlignBottom]

        assert len(top) == 1
        assert len(top[0].categoriesLabels()) == bottom[0].tickCount()
        assert all(label.startswith('<span class="label-') for label in top[0].categoriesLabels())

    def test_charts_without_a_window_keep_no_series(self, qtbot, database):
        # an empty database must not leave stale series or axes behind
        from tafor.core.repositories import MetarRepository
        from tafor.ui.components.chart import ChartViewer

        viewer = ChartViewer(None, repository=MetarRepository(database))
        qtbot.addWidget(viewer)
        viewer.updateDateRange('latest')

        assert all(view.chart().series() == [] for view in viewer.views)
        assert all(view.chart().axes() == [] for view in viewer.views)

    def test_the_chart_set_can_be_replaced(self, qtbot, database):
        # specs is a default, not a fixed set: passing specs= stacks exactly
        # those charts. This is the seam for showing fewer than six.
        from tafor.core.repositories import MetarRepository
        from tafor.ui.components.chart import ChartSpec, ChartViewer, SeriesSpec

        created = datetime.datetime(2026, 8, 31, 12, 0)
        with database.session() as session:
            session.add(Metar(type='SA', text='YUSO 311200Z 27015KT 9999 SCT030 28/20 Q1013', created=created))

        specs = (
            ChartSpec('Pressure only', unit='hPa', series=(
                SeriesSpec('Pressure', 'pressures'),
            )),
        )
        viewer = ChartViewer(None, repository=MetarRepository(database),
                             clock=lambda: created, specs=specs)
        qtbot.addWidget(viewer)
        viewer.updateDateRange('latest')

        assert [view.chart().spec.title for view in viewer.views] == ['Pressure only']
        assert viewer.views[0].chart().title() == 'Pressure only (hPa)'
        assert viewer.chartLayout.count() == 1
        assert [series.name() for series in viewer.views[0].chart().series()] == ['Pressure']

    def test_saved_file_names_carry_no_unit(self, qtbot, database, tmp_path, monkeypatch):
        # '/' would read as a directory separator in the path, and the unit
        # belongs to the chart header rather than to the file name
        from PyQt5.QtWidgets import QFileDialog

        created = datetime.datetime(2026, 8, 31, 12, 0)
        viewer = self.build_viewer(database, [
            ('YUSO 311200Z 27015KT 9999 SCT030 28/20 Q1013', created),
        ], created)
        qtbot.addWidget(viewer)

        monkeypatch.setattr(QFileDialog, 'getExistingDirectory',
                            staticmethod(lambda *args, **kwargs: str(tmp_path)))
        viewer.saveImages()

        # the stamp is the start of the window, so the stem is what precedes it
        names = sorted(path.stem.split(' 2026')[0] for path in tmp_path.glob('*.png'))

        assert names == [
            'Clouds & Ceiling',
            'Query Normal Height',
            'Temperature & Dewpoint',
            'Visibility & RVR',
            'Weather Phenomenon',
            'Wind & Gust',
        ]

    def test_the_tooltip_knows_which_chart_it_belongs_to(self, qtbot, database):
        # the weather chart's label is the series name alone because spec.weather
        # says its y is an intensity slot, not because its unit happens to be
        # empty: the cloud chart draws the same kind of scatter series and does
        # print its height. Driven through the real marker, so the wiring from
        # spec to markerHtml is covered and not just the helper.
        from PyQt5.QtCore import QPointF

        created = datetime.datetime(2026, 8, 31, 12, 0)
        viewer = self.build_viewer(database, [
            ('YUSO 311200Z 12012KT 9999 -SHRA SCT030 BKN045 28/20 Q1013', created),
        ], created)
        qtbot.addWidget(viewer)

        def tooltip(index):
            view = viewer.views[index]
            series = view.chart().series()[0]
            point = QPointF(series.at(0).x(), series.at(0).y())
            view.marker.setSeriesText([(0, series, point, 0)])
            return view.marker.text.toPlainText()

        assert tooltip(2).endswith('-SHRA')
        assert tooltip(3).endswith('Ceiling: 1350 m')

