import ast
import datetime
import pathlib

from tafor.core.taf.compose import completeGroupPeriod
from tafor.core.taf.rules import (
    formatTrendPeriod,
    groupPeriodRules,
    normalizePeriod,
    segmentRules,
    separatePeriod,
    trendRules,
)
from tafor.core.taf.spec import SpecFT24
from tafor.core.utils.time import parsePeriod


def _baseRaw(**overrides):
    raw = {
        'wind': '24008',
        'gust': '15',
        'vis': '9999',
        'weather': 'RA',
        'weatherWithIntensity': '-SHRA',
        'cloud1': 'SCT020',
        'cloud2': 'BKN030',
        'cloud3': 'OVC040',
        'cb': 'BKN025',
        'isCavok': False,
        'isNsc': False,
    }
    raw.update(overrides)
    return raw


def _trendRaw(**overrides):
    raw = _baseRaw(
        isNosig=False,
        indicator='BECMG',
        atChecked=False,
        fmChecked=False,
        tlChecked=False,
        period='',
    )
    raw.update(overrides)
    return raw


class TestPureModule:

    def test_rules_module_does_not_import_pyqt(self):
        rulesPath = pathlib.Path(__file__).resolve().parents[2] / 'tafor' / 'core' / 'taf' / 'rules.py'
        tree = ast.parse(rulesPath.read_text(encoding='utf-8'))

        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)

        assert all(not name.startswith('PyQt5') for name in imports)


class TestSegmentRules:

    def test_cavok_clears_nsc_and_weather_group(self):
        previous = _baseRaw(isNsc=True)
        raw = _baseRaw(isCavok=True, isNsc=True)

        segmentRules(raw, previous, {'isCavok'}, 'user')

        assert raw['isCavok'] is True
        assert raw['isNsc'] is False
        for key in ('vis', 'weather', 'weatherWithIntensity', 'cloud1', 'cloud2', 'cloud3', 'cb'):
            assert raw[key] == ''

    def test_nsc_clears_cavok_and_clouds_only(self):
        previous = _baseRaw(isCavok=True)
        raw = _baseRaw(isCavok=True, isNsc=True)

        segmentRules(raw, previous, {'isNsc'}, 'user')

        assert raw['isCavok'] is False
        assert raw['isNsc'] is True
        assert raw['vis'] == '9999'
        assert raw['weather'] == 'RA'
        for key in ('cloud1', 'cloud2', 'cloud3', 'cb'):
            assert raw[key] == ''

    def test_calm_wind_clears_gust(self):
        previous = _baseRaw()
        raw = _baseRaw(wind='00000', gust='15')

        segmentRules(raw, previous, {'wind'}, 'user')

        assert raw['gust'] == ''

    def test_nsw_clears_weather_with_intensity(self):
        previous = _baseRaw()
        raw = _baseRaw(weather='nsw', weatherWithIntensity='-SHRA')

        segmentRules(raw, previous, {'weather'}, 'user')

        assert raw['weatherWithIntensity'] == ''

    def test_vertical_visibility_clears_upper_clouds(self):
        previous = _baseRaw()
        raw = _baseRaw(cloud1='VV005')

        segmentRules(raw, previous, {'cloud1'}, 'user')

        assert raw['cloud1'] == 'VV005'
        assert raw['cloud2'] == ''
        assert raw['cloud3'] == ''
        assert raw['cb'] == ''


class TestTrendRules:

    def test_separate_period_and_format_trend_period(self):
        assert separatePeriod('0915', '091') == '0915/'
        assert separatePeriod('0915', '0915/') == '0915'

        assert formatTrendPeriod('2400', atChecked=True) == '0000'
        assert formatTrendPeriod('2400', fmChecked=True, tlChecked=False) == '0000'
        assert formatTrendPeriod('0000', tlChecked=True, fmChecked=False) == '2400'
        assert formatTrendPeriod('2400', fmChecked=True, tlChecked=True) == '2400'

    def test_tempo_clears_at_and_resets_period(self):
        previous = _trendRaw(indicator='BECMG', atChecked=True, period='0915')
        raw = _trendRaw(indicator='TEMPO', atChecked=True, period='0915')

        trendRules(raw, previous, {'indicator'}, 'user')

        assert raw['atChecked'] is False
        assert raw['period'] == ''

    def test_at_and_fm_tl_mutual_exclusion(self):
        previous = _trendRaw(fmChecked=True, tlChecked=True, period='0915/1015')
        raw = _trendRaw(atChecked=True, fmChecked=True, tlChecked=True, period='0915/1015')

        trendRules(raw, previous, {'atChecked'}, 'user')

        assert raw['atChecked'] is True
        assert raw['fmChecked'] is False
        assert raw['tlChecked'] is False
        assert raw['period'] == ''

        previous = _trendRaw(atChecked=True, period='0915')
        raw = _trendRaw(atChecked=True, fmChecked=True, period='0915')

        trendRules(raw, previous, {'fmChecked'}, 'user')

        assert raw['atChecked'] is False
        assert raw['fmChecked'] is True
        assert raw['period'] == ''

    def test_collect_same_snapshot_keeps_period(self):
        raw = _trendRaw(fmChecked=True, tlChecked=True, period='0915/1015')
        previous = dict(raw)

        trendRules(raw, previous, set(raw.keys()), 'collect')

        assert raw['period'] == '0915/1015'

    def test_user_typing_fm_tl_period_inserts_separator(self):
        previous = _trendRaw(fmChecked=True, tlChecked=True, period='091')
        raw = _trendRaw(fmChecked=True, tlChecked=True, period='0915')

        trendRules(raw, previous, {'period'}, 'user')

        assert raw['period'] == '0915/'


class TestGroupPeriodRules:

    WINDOW = (datetime.datetime(2026, 8, 10, 12), datetime.datetime(2026, 8, 12, 0))

    def test_normalize_period_inserts_separator_and_handles_midnight(self):
        assert normalizePeriod('1012', '101', None) == '1012/'
        assert normalizePeriod('1012', '1012/', None) == '1012'
        assert normalizePeriod('1012/1200', '1012/120', self.WINDOW) == '1012/1124'
        assert normalizePeriod('1012/1124', '1012/112', self.WINDOW) == '1012/1124'

    def test_group_period_rules_completes_and_retries_after_refused_start(self):
        base = self.WINDOW[0]
        assert groupPeriodRules(
            '1012',
            '101',
            primaryDurations=self.WINDOW,
            indicator='BECMG',
            spec=SpecFT24,
            autoComplete=True,
            parseWindow=lambda text: parsePeriod(text, base),
        ) == completeGroupPeriod('1012', self.WINDOW, 'BECMG', SpecFT24)

        assert groupPeriodRules(
            '9999',
            '999',
            primaryDurations=self.WINDOW,
            indicator='BECMG',
            spec=SpecFT24,
            autoComplete=True,
            parseWindow=lambda text: parsePeriod(text, base),
        ) == '9999'

        # Replacing a refused 4-digit start still completes cleanly
        assert groupPeriodRules(
            '1014',
            '9999',
            primaryDurations=self.WINDOW,
            indicator='BECMG',
            spec=SpecFT24,
            autoComplete=True,
            parseWindow=lambda text: parsePeriod(text, base),
        ) == '1014/1015'

        # Deleting the slash back from a completed period does not re-complete
        assert groupPeriodRules(
            '1014',
            '1014/1015',
            primaryDurations=self.WINDOW,
            indicator='BECMG',
            spec=SpecFT24,
            autoComplete=True,
            parseWindow=lambda text: parsePeriod(text, base),
        ) == '1014'

    def test_group_period_rules_without_primary_window_leaves_text(self):
        assert groupPeriodRules(
            '1012',
            '101',
            primaryDurations=None,
            indicator='BECMG',
            spec=SpecFT24,
            autoComplete=True,
        ) == '1012'
