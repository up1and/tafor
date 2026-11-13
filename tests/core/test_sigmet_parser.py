import re
import datetime

from tafor.core.parsers import SigmetParser, TyphoonAdvisoryParser, AshAdvisoryParser
from tafor.core.parsers.sigmet import SigmetLexer


# The four messages the identity tests compare. A report, the cancellation
# that names it, and two reports that merely look like the first one.
REPORT_SIGMET = ('ZJSA SIGMET 2 VALID 100730/101430 ZJHK-\n'
                 'ZJSA SANYA FIR OBSC TS FCST WI E11223 N1829 - E11142 N1916 TOP FL030 MOV N 300KMH NC=')
CANCEL_SIGMET = ('ZJSA SIGMET 5 VALID 101200/101900 ZJHK-\n'
                 'ZJSA SANYA FIR CNL SIGMET 2 100730/101430=')
REPORT_AIRMET = ('ZJSA AIRMET 2 VALID 100730/101430 ZJHK-\n'
                 'ZJSA SANYA FIR ISOL TS WI E11223 N1829 - E11142 N1916 TOP FL 030=')
CANCEL_AIRMET = ('ZJSA AIRMET 7 VALID 101200/101900 ZJHK-\n'
                 'ZJSA SANYA FIR CNL AIRMET 2 100730/101430=')
REPORT_OTHER_UNIT = ('ZBPE SIGMET 2 VALID 100730/101430 ZBAA-\n'
                     'ZBPE BEIJING FIR SEV TURB FCST WI N4000 E11600 - N4100 E11700 TOP FL300 MOV E 20KT NC=')


def test_keywords_not_polluted(read_fixture):
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


def test_lexer_word_matchers():
    lexer = SigmetLexer('S1500 E07348')

    assert lexer.matchesGrammar('N2300')
    assert not lexer.matchesGrammar('N203')
    assert not lexer.matchesGrammar('YAGI')

    assert lexer.isProperName('MT', None)
    assert lexer.isProperName('TC', None)
    assert lexer.isProperName('TC', 'ZJSA SANYA FIR')
    assert not lexer.isProperName('TC', '1400Z')
    assert not lexer.isProperName('PSN', 'YAGI')


def test_fir_code_argument():
    message = 'ZJSA SIGMET 1 VALID 300855/301255 ZJHK-\nZJSA SANYA FIR VA CLD='
    parser = SigmetParser(message, firCode='ZJSA SANYA FIR', airportCode='ZJHK')

    assert parser.firCode == 'ZJSA SANYA FIR'
    assert parser.airportCode == 'ZJHK'
    assert parser.isValid()


def test_sigmet_parser(fixtures_dir):
    folder = fixtures_dir / 'sigmet'
    for filepath in sorted(folder.glob('*.text')):
        content = filepath.read_text()

        m = SigmetParser(content, firCode='ZJSA SANYA FIR')
        html = m.renderer(style='html')
        result = filepath.with_suffix('.html').read_text()

        html = re.sub(r'\s', '', html)
        result = re.sub(r'\s', '', result)
        assert result == html


def test_repr_and_terminal_renderer():
    s = SigmetParser('ZJSA SIGMET 1 VALID 311430/311830 ZJHK-\nZJSA SANYA FIR EMBD TS FCST N OF N16 TOP FL300 MOV N 30KMH NC=', firCode='ZJSA SANYA FIR', airportCode='ZJHK')
    repr(s)
    s.renderer('terminal')

    assert s.isValid()
    assert not s.hasMessageChanged()


def test_error_fixture_tokens(read_fixture):
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


def test_tc_fixture_geometry(read_fixture):
    parser = SigmetParser(read_fixture('sigmet', 'tc_pass'))

    assert parser.type() == 'WC'
    assert parser.location() == [
        {'type': 'circle', 'coordinates': (('N2300', 'E11304'), ('300', 'KM'))},
        {'type': 'circle', 'coordinates': (('N2401', 'E11411'), ('300', 'KM'))},
    ]

    features = parser.geo(None)['features']
    assert [f['properties']['location'] for f in features] == ['initial', 'final']
    assert all(f['properties']['hazard'] == 'typhoon' for f in features)


def test_va_fixture_geometry(read_fixture):
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


def test_identity_pairs_a_report_with_the_cancellation_that_names_it():
    """The two sides of a cancellation answer in the same shape.

    This is the seam the repository and the reminder list both match on, so a
    report and its cancellation have to produce an equal key.
    """
    report = SigmetParser(REPORT_SIGMET)
    cancel = SigmetParser(CANCEL_SIGMET)

    assert report.identity() == cancel.cancelledIdentity()


def test_identity_carries_the_product_category():
    """A cancellation names the class it applies to, and the class is part of
    what identifies the target: SIGMET 2 and AIRMET 2 are different reports."""
    sigmet = SigmetParser(REPORT_SIGMET)
    airmet = SigmetParser(REPORT_AIRMET)

    assert sigmet.identity()[:2] == ('ZJSA', 'SIGMET')
    assert airmet.identity()[:2] == ('ZJSA', 'AIRMET')
    assert sigmet.identity() != airmet.identity()


def test_identity_carries_the_issuing_unit():
    """Two units can issue the same number for the same window."""
    ours = SigmetParser(REPORT_SIGMET).identity()
    theirs = SigmetParser(REPORT_OTHER_UNIT).identity()

    assert ours[0] == 'ZJSA'
    assert theirs[0] == 'ZBPE'
    assert ours != theirs


def test_a_cancel_target_names_the_class_it_cancels():
    assert SigmetParser(CANCEL_AIRMET).cancelledIdentity()[:2] == ('ZJSA', 'AIRMET')


def test_a_cancel_composed_by_this_app_still_has_an_identity():
    """The composed form carries no FIR in its text, which is why the key is
    built on the originator rather than on fir()."""
    text = 'ZJSA SIGMET 1 VALID 100930/101430 ZJHK-\nZJSA CNL SIGMET 1 100930/101430='
    composed = SigmetParser(text)

    assert composed.fir() is None
    assert composed.cancelledIdentity() == ('ZJSA', 'SIGMET', '1', '100930/101430')


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


def test_typhoon_advisory(read_fixture):
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


def test_ash_advisory(read_fixture):
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

    # A wrapped coordinate pair is folded back into the previous field
    # instead of producing a malformed key
    assert parser.tokens['OBS VA CLD'].endswith('N2314 E13222 MOV W 55KT')

    location = parser.location('OBS VA CLD')
    assert location['geometry']['type'] == 'Polygon'
    assert len(location['geometry']['coordinates']) == 8
    assert location['properties']['flightLevel'] == 'SFC/FL480'
    assert location['properties']['time'] == datetime.datetime(2021, 8, 14, 21, 0)

    forecast = parser.location('FCST VA CLD +12 HR')
    assert len(forecast['geometry']['coordinates']) == 9
    assert forecast['properties']['time'] == datetime.datetime(2021, 8, 15, 8, 20)




def test_typhoon_advisory_formatted_position(read_fixture):
    parser = TyphoonAdvisoryParser(read_fixture('advisory', 'tc_chaba'))

    # Latitude first, matching the single-value DMS format used elsewhere
    assert parser.formattedPosition('PSN') == ('N2110', 'E11120')
    assert parser.formattedPosition('FCST PSN +6 HR') == ('N2155', 'E11050')


def test_formatted_position_matches_the_raw_text(read_fixture):
    parser = TyphoonAdvisoryParser(read_fixture('advisory', 'tc_chaba'))

    assert parser.position() == ('N2110', 'E11120')
    assert parser.formattedPosition('PSN') == ('N2110', 'E11120')


def test_advisory_formatted_position_is_none_when_unavailable(read_fixture):
    parser = TyphoonAdvisoryParser(read_fixture('advisory', 'tc_chaba'))

    assert parser.formattedPosition('FCST PSN +48 HR') is None
    assert parser.formattedPosition('MOV') is None


def test_split_flight_level():
    parser = AshAdvisoryParser('VA ADVISORY\nDTG: 20210814/2100Z=')

    assert parser.splitFlightLevel('SFC/FL480') == ('SFC', 'FL480')
    assert parser.splitFlightLevel('FL450') == (None, 'FL450')
    assert parser.splitFlightLevel(' FL450 / FL600 ') == ('FL450', 'FL600')
    assert parser.splitFlightLevel('') == (None, None)
    assert parser.splitFlightLevel(None) == (None, None)


def test_ash_advisory_flight_level_splits_for_the_editor():
    parser = AshAdvisoryParser(
        'VA ADVISORY\nDTG: 20210814/2100Z\nOBS VA CLD: SFC/FL480 N2314 E13222=')

    feature = parser.location('OBS VA CLD')
    assert parser.splitFlightLevel(feature['properties']['flightLevel']) == ('SFC', 'FL480')

if __name__ == '__main__':
    import pytest
    pytest.main()
