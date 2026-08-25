import random

from tafor.ui.components.chart import cloudPoints, weatherPoints


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
