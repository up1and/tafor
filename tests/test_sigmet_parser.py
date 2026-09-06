import os
import datetime

from tafor.core.parsers import SigmetParser, TyphoonAdvisoryParser, AshAdvisoryParser
from tafor.core.parsers.sigmet import SigmetLexer

root = os.path.dirname(__file__)


def read_fixture(folder, name):
    filepath = os.path.join(root, 'fixtures', folder, name + '.text')
    with open(filepath) as f:
        return f.read()


def test_keywords_not_polluted():
    before = len(SigmetLexer.defaultKeywords)
    message = read_fixture('sigmet', 'va_pass')
    SigmetParser(message)
    SigmetParser(message)

    assert len(SigmetLexer.defaultKeywords) == before
    assert 'ZJHK' not in SigmetLexer.defaultKeywords


def test_leading_whitespace_keeps_fir():
    lexer = SigmetLexer('  ZJSA SANYA FIR VA CLD', firCode='ZJSA SANYA FIR')

    assert lexer.isValid()
    assert lexer.tokens[0]['text'] == 'ZJSA SANYA FIR'


def test_fir_uir():
    message = 'ZJSA SIGMET 1 VALID 300855/301255 ZJHK-\nZJSA FIR/UIR VA CLD WI S1500 E07348 - S1530 E07642='
    parser = SigmetParser(message)

    assert parser.firCode == 'ZJSA FIR/UIR'
    assert parser.isValid()


def test_atc_is_not_typhoon():
    message = 'ZJSA SIGMET 1 VALID 300855/301255 ZJHK-\nZJSA SANYA FIR SEV TURB FL250 ATC='
    parser = SigmetParser(message)

    assert parser.hazard() == 'turb'
    assert parser.type() == 'WS'


def test_three_digit_speed():
    assert SigmetLexer('MOV N 120KMH NC').isValid()
    assert SigmetLexer('MOV N 100KT NC').isValid()
    assert SigmetLexer('MOV N 300KMH NC').isValid()


def test_fir_code_argument():
    message = 'ZJSA SIGMET 1 VALID 300855/301255 ZJHK-\nZJSA SANYA FIR VA CLD='
    parser = SigmetParser(message, firCode='ZJSA SANYA FIR', airportCode='ZJHK')

    assert parser.firCode == 'ZJSA SANYA FIR'
    assert parser.airportCode == 'ZJHK'
    assert parser.isValid()


def test_error_fixture_tokens():
    parser = SigmetParser(read_fixture('sigmet', 'error1'))

    assert not parser.isValid()
    tokens = {t['text']: t['error'] for e in parser.elements for t in e.tokens}
    assert tokens['N203']
    assert tokens['E109017']
    assert tokens['FL030']
    assert not tokens['300KMH']


def test_current_standard_tc_circle():
    message = ('ZJSA SIGMET 1 VALID 300855/301255 ZJHK-\n'
               'ZJSA SANYA FIR TC YAGI PSN N2300 E11304 CB TOP FL420 WI 300KM OF CENTER MOV NE 30KMH INTSF=')
    parser = SigmetParser(message)

    assert parser.location() == [{'type': 'circle', 'coordinates': (('N2300', 'E11304'), ('300', 'KM'))}]

    collections = parser.geo(None)
    assert len(collections['features']) == 1
    assert collections['features'][0]['geometry']['type'] == 'Polygon'
    assert collections['features'][0]['properties']['hazard'] == 'typhoon'


def test_tc_fixture_geometry():
    parser = SigmetParser(read_fixture('sigmet', 'tc_pass'))

    assert parser.type() == 'WC'
    assert parser.location() == [
        {'type': 'circle', 'coordinates': (('N2300', 'E11304'), ('300', 'KM'))},
        {'type': 'circle', 'coordinates': (('N2401', 'E11411'), ('300', 'KM'))},
    ]

    features = parser.geo(None)['features']
    assert [f['properties']['location'] for f in features] == ['initial', 'final']
    assert all(f['properties']['hazard'] == 'typhoon' for f in features)


def test_va_fixture_geometry():
    parser = SigmetParser(read_fixture('sigmet', 'va_pass'))

    assert parser.type() == 'WV'
    assert parser.location() == [
        {'type': 'corridor', 'coordinates': ([('S1500', 'E07348'), ('S1530', 'E07642')], ('35', 'KM'))}
    ]

    features = parser.geo(None)['features']
    assert len(features) == 1
    assert features[0]['properties']['hazard'] == 'ash'
    assert features[0]['geometry']['type'] == 'Polygon'


def test_geo_without_valid_group():
    parser = SigmetParser('ZJSA SANYA FIR VA CLD WI S1500 E07348 - S1530 E07642 - S1600 E07700')

    assert parser.validTime() is None
    feature = parser.geo(None)['features'][0]
    assert feature['properties']['valids'] == []


def test_sigmet_accessors_return_none_for_missing_groups():
    parser = SigmetParser('ZJSA SANYA FIR VA CLD=')

    assert parser.category() is None
    assert parser.sequence() is None
    assert parser.validTime() is None
    assert parser.airport() is None

    parser = SigmetParser('ZJSA SIGMET 1 VALID 300855/301255 ZJHK-\nSEV TS WI S1500 E07348=')

    assert parser.fir() is None


def test_advisory_accessors_return_none_for_missing_fields():
    ash = AshAdvisoryParser('VA ADVISORY\nDTG: 20210814/2100Z\nPSN: N2417 E14129=')

    assert ash.name() is None
    assert ash.movement() is None
    assert ash.speed() is None

    typhoon = TyphoonAdvisoryParser('TC ADVISORY\nDTG: 20220702/0600Z\nTC: CHABA=')

    assert typhoon.height() is None
    assert typhoon.movement() is None
    assert typhoon.intensity() is None


def test_typhoon_advisory():
    parser = TyphoonAdvisoryParser(read_fixture('advisory', 'tc_chaba'))

    assert parser.time == datetime.datetime(2022, 7, 2, 6, 0)
    assert parser.name() == 'CHABA'
    assert parser.position() == ('N2110', 'E11120')
    assert parser.movement() == 'NNW'
    assert parser.speed(unit='KT') == 7
    assert parser.speed() == 12
    assert parser.height() == '530'
    assert parser.intensity() == 'WKN'
    assert parser.availableLocations() == [
        'PSN', 'FCST PSN +6 HR', 'FCST PSN +12 HR', 'FCST PSN +18 HR', 'FCST PSN +24 HR'
    ]

    location = parser.location('PSN')
    assert location['geometry']['type'] == 'Point'
    assert location['properties']['time'] == datetime.datetime(2022, 7, 2, 6, 0)

    forecast = parser.location('FCST PSN +6 HR')
    assert forecast['geometry']['type'] == 'Point'
    assert forecast['properties']['time'] == datetime.datetime(2022, 7, 2, 12, 0)

    polygon = parser.polygon()
    assert polygon['type'] == 'Polygon'
    assert len(polygon['coordinates']) == 6

    route = parser.route()
    assert route['type'] == 'LineString'
    assert len(route['coordinates']) == 5

    assert parser.radius() > 300


def test_ash_advisory():
    parser = AshAdvisoryParser(read_fixture('advisory', 'va_fukutoku'))

    assert parser.time == datetime.datetime(2021, 8, 14, 21, 0)
    assert parser.name() == 'FUKUTOKU-OKA-NO-BA'
    assert parser.position() == ('N2417', 'E14129')
    assert parser.movement() == 'W'
    assert parser.speed(unit='KT') == 55
    assert parser.speed() == 101
    assert parser.observedTime() == datetime.datetime(2021, 8, 14, 20, 20)
    assert parser.availableLocations() == [
        'OBS VA CLD', 'FCST VA CLD +6 HR', 'FCST VA CLD +12 HR', 'FCST VA CLD +18 HR'
    ]

    # 折行的坐标对被拼回上一字段，而不是生成畸形的 key
    assert parser.tokens['OBS VA CLD'].endswith('N2314 E13222 MOV W 55KT')

    location = parser.location('OBS VA CLD')
    assert location['geometry']['type'] == 'Polygon'
    assert len(location['geometry']['coordinates']) == 8
    assert location['properties']['flightLevel'] == 'SFC/FL480'
    assert location['properties']['time'] == datetime.datetime(2021, 8, 14, 21, 0)

    forecast = parser.location('FCST VA CLD +12 HR')
    assert len(forecast['geometry']['coordinates']) == 9
    assert forecast['properties']['time'] == datetime.datetime(2021, 8, 15, 8, 20)


if __name__ == '__main__':
    import pytest
    pytest.main()
