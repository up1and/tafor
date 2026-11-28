import ast
import datetime
import pathlib

from tafor.core.sigmet.compose import adjustCancelBeginning
from tafor.core.sigmet.rules import (
    ashRules,
    cancelRules,
    customRules,
    filterCustomText,
    flightLevelFormats,
    flightLevelRules,
    forecastRules,
    generalRules,
    movementRules,
    observationRules,
    typhoonRules,
)


def _generalRaw(**overrides):
    raw = {
        'sequence': '1',
        'beginningTime': '100810',
        'endingTime': '101210',
        'description': 'EMBD',
        'phenomenon': 'TS',
        'intensityChange': 'NC',
        'comeFrom': 'FCST',
        'observedTime': '',
        'hasForecast': False,
        'forecastTime': '',
        'flightLevelFormat': 'TOP',
        'flightLevelBase': '',
        'flightLevelTop': '360',
        'direction': 'N',
        'speed': '20',
    }
    raw.update(overrides)
    return raw


class TestPureSigmetRulesModule:

    def test_rules_module_does_not_import_pyqt(self):
        rulesPath = pathlib.Path(__file__).resolve().parents[2] / 'tafor' / 'core' / 'sigmet' / 'rules.py'
        tree = ast.parse(rulesPath.read_text(encoding='utf-8'))

        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)

        assert all(not name.startswith('PyQt5') for name in imports)


class TestSigmetPartRules:

    def test_flight_level_rules_clear_masked_endpoint(self):
        raw = _generalRaw(flightLevelFormat='TOP', flightLevelBase='080', flightLevelTop='360')
        flightLevelRules(raw, dict(raw), {'flightLevelFormat'}, 'user')
        assert raw['flightLevelBase'] == ''
        assert raw['flightLevelTop'] == '360'

        raw = _generalRaw(flightLevelFormat='ABV', flightLevelBase='080', flightLevelTop='360')
        flightLevelRules(raw, dict(raw), {'flightLevelFormat'}, 'user')
        assert raw['flightLevelBase'] == '080'
        assert raw['flightLevelTop'] == ''

    def test_movement_rules_clear_speed_when_stationary(self):
        raw = _generalRaw(direction='STNR', speed='25')
        movementRules(raw, dict(raw), {'direction'}, 'user')
        assert raw['speed'] == ''

    def test_observation_rules_sync_and_clear_by_source(self):
        previous = _generalRaw(comeFrom='FCST', observedTime='')
        raw = _generalRaw(comeFrom='OBS', observedTime='')
        observationRules(raw, previous, {'comeFrom'}, 'user')
        assert raw['observedTime'] == '0810'

        # Switching away from OBS clears observedTime when it matches beginningTime suffix
        previous = dict(raw)
        raw['comeFrom'] = 'FCST'
        observationRules(raw, previous, {'comeFrom'}, 'user')
        assert raw['observedTime'] == ''

        # collect preserves manual values
        raw = _generalRaw(comeFrom='OBS', observedTime='0750')
        observationRules(raw, dict(raw), set(raw.keys()), 'collect')
        assert raw['observedTime'] == '0750'

    def test_forecast_rules_sync_and_clear_on_overlap(self):
        previous = _generalRaw(hasForecast=False, forecastTime='')
        raw = _generalRaw(hasForecast=True, forecastTime='')
        forecastRules(raw, previous, {'hasForecast'}, 'overlap', hasDurations=True)
        assert raw['forecastTime'] == '1210'

        previous = dict(raw)
        raw['hasForecast'] = False
        forecastRules(raw, previous, {'hasForecast'}, 'overlap', hasDurations=True)
        assert raw['forecastTime'] == ''


class TestSigmetConcreteRules:

    PHENOMENA = {
        'EMBD': ['TS', 'TSGR'],
        'SEV': ['TURB', 'ICE'],
    }

    def test_general_rules_update_phenomenon_and_flight_level_format(self):
        previous = _generalRaw()
        raw = _generalRaw(description='SEV')

        generalRules(
            raw,
            previous,
            {'description'},
            'user',
            phenomenaMap=self.PHENOMENA,
            defaultPhenomena=['TS', 'TSGR'],
        )

        assert raw['phenomenon'] == 'TURB'
        assert raw['flightLevelFormat'] == ''
        assert 'TOP' not in flightLevelFormats('TURB')

    def test_ash_rules_derive_is_eruption(self):
        raw = {'phenomenon': 'CLD', 'flightLevelFormat': '', 'direction': 'N', 'comeFrom': 'FCST', 'hasForecast': False}
        ashRules(raw, dict(raw), {'phenomenon'}, 'user', hasDurations=False)
        assert raw['isEruption'] is False

        raw['phenomenon'] = 'ERUPTION'
        ashRules(raw, dict(raw), {'phenomenon'}, 'user', hasDurations=False)
        assert raw['isEruption'] is True

    def test_typhoon_rules_recompute_forecast_only_on_user_edits(self):
        called = []

        def fakeCalc():
            called.append(True)
            return ('N2200', 'E11500')

        previous = _generalRaw(speed='10', forecastLatitude='', forecastLongitude='')
        raw = _generalRaw(speed='20', forecastLatitude='', forecastLongitude='')
        typhoonRules(raw, previous, {'speed'}, 'user', calcForecast=fakeCalc)
        assert called == [True]
        assert (raw['forecastLatitude'], raw['forecastLongitude']) == ('N2200', 'E11500')

        # Map/advisory updates never overwrite coordinates with calcForecast
        called.clear()
        mapRaw = _generalRaw(speed='20', forecastLatitude='N2300', forecastLongitude='E11600')
        typhoonRules(mapRaw, previous, {'speed', 'forecastLatitude', 'forecastLongitude'}, 'map', calcForecast=fakeCalc)
        assert called == []
        assert (mapRaw['forecastLatitude'], mapRaw['forecastLongitude']) == ('N2300', 'E11600')

    def test_custom_rules_filter_and_uppercase(self):
        assert filterCustomText('embd ts= #12/3') == 'EMBD TS 12/3'
        raw = {'text': 'embd ts='}
        customRules(raw, {}, {'text'}, 'user')
        assert raw['text'] == 'EMBD TS'

    def test_cancel_rules_fill_candidate_valid_and_sync_header(self):
        now = datetime.datetime(2026, 6, 10, 8, 0)

        def resolveValid(key):
            return '100930/101430' if key in (0, '2') else None

        def adjustBeginning(raw, cancelBegin, cancelEnd):
            if cancelEnd:
                raw['endingTime'] = cancelEnd
            if cancelBegin:
                raw['beginningTime'] = adjustCancelBeginning(
                    cancelBegin,
                    now + datetime.timedelta(minutes=10),
                    raw.get('endingTime', ''),
                    now,
                ).strftime('%d%H%M')

        raw = {
            'cancelIndex': 0,
            'cancelSequence': '2',
            'cancelBeginningTime': '',
            'cancelEndingTime': '',
            'beginningTime': '100810',
            'endingTime': '101210',
        }
        cancelRules(
            raw,
            {},
            {'cancelIndex', 'cancelSequence'},
            'seed',
            resolveValid=resolveValid,
            adjustBeginning=adjustBeginning,
        )
        assert raw['cancelBeginningTime'] == '100930'
        assert raw['cancelEndingTime'] == '101430'
        assert raw['endingTime'] == '101430'
        assert raw['beginningTime'] == '100930'
