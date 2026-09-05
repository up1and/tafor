import os
import re

import pytest

from tafor.core.parsers import MetarParser, SigmetParser, TafParser, TafValidator

root = os.path.dirname(__file__)


def listdir(folder):
    folder = os.path.join(root, 'fixtures', folder)
    files = os.listdir(folder)
    files = filter(lambda o: o.endswith('.text'), files)
    names = map(lambda o: o[:-5], files)
    return folder, names

@pytest.fixture
def validator():
    return TafValidator()

def test_taf_parser():
    folder, names = listdir('taf')
    for name in names:
        filepath = os.path.join(folder, name + '.text')
        with open(filepath) as f:
            content = f.read()

        m = TafParser(content)
        m.validate()
        html = m.renderer(style='html')

        filepath = os.path.join(folder, name + '.html')
        with open(filepath) as f:
            result = f.read()

        html = re.sub(r'\s', '', html)
        result = re.sub(r'\s', '', result)
        assert result == html

def test_sigmet_parser():
    folder, names = listdir('sigmet')
    for name in names:
        filepath = os.path.join(folder, name + '.text')
        with open(filepath) as f:
            content = f.read()

        m = SigmetParser(content, firCode='ZJSA SANYA FIR')
        html = m.renderer(style='html')

        filepath = os.path.join(folder, name + '.html')
        with open(filepath) as f:
            result = f.read()

        html = re.sub(r'\s', '', html)
        result = re.sub(r'\s', '', result)
        assert result == html

def test_wind(validator):
    assert validator.wind('01004MPS', '07005MPS')
    assert validator.wind('36010MPS', '36005MPS')
    assert validator.wind('03008G15MPS', '36005G10MPS')
    assert validator.wind('03008G13MPS', '36005MPS')
    assert validator.wind('03004GP49MPS', '36008MPS')
    assert validator.wind('00000MPS', '07005MPS')
    assert not validator.wind('VRB01MPS', '36004MPS')
    assert not validator.wind('36010G15MPS', '36008G15MPS')
    assert not validator.wind('36020GP49MPS', '36020GP49MPS')
    assert not validator.wind('14008G14MPS', '15005G10MPS')

def test_vis(validator):
    assert validator.vis(1600, 3000)
    assert validator.vis(1400, 6000)
    assert validator.vis(200, 400)
    assert validator.vis(3000, 1600)
    assert validator.vis(4000, 7000)

def test_weather(validator):
    assert validator.weather('TS', '-TSRA')
    assert validator.weather('-TSRA', 'TSRA')
    assert validator.weather('TSRA BR', '-TSRA')
    assert validator.weather('RA BR', 'NSW')
    assert not validator.weather('TSRA', 'TSRA')
    assert not validator.weather('NSW', 'BR')
    assert not validator.weather('-RA BR', 'BR')

def test_cloud(validator):
    assert validator.cloud('BKN015', 'SCT007 OVC010')
    assert validator.cloud('SCT020', 'SCT020 FEW023CB')
    assert validator.cloud('BKN010', 'BKN004')
    assert validator.cloud('SCT010', 'BKN010')
    assert validator.cloud('SCT007', 'BKN010')
    assert validator.cloud('SCT020', 'BKN010')
    assert validator.cloud('SCT020 FEW026CB', 'SCT010 SCT030CB')
    assert validator.cloud('BKN010', 'SCT010 BKN030')
    assert not validator.cloud('SCT007', 'SCT015')
    assert not validator.cloud('NSC', 'SKC')
    assert not validator.cloud('SCT020', 'SCT020')

    assert validator.cloud('VV002', 'VV005')
    assert validator.cloud('VV005', 'VV002')
    assert validator.cloud('VV005', 'SCT020')
    assert validator.cloud('VV015', 'BKN010')
    assert not validator.cloud('VV006', 'OVC009')
    assert not validator.cloud('VV002', 'VV003')

    # To be fixed 
    # when cloudHeightHas450 equal False, BKN016, BKN011 always return True

def test_cavok(validator):
    assert validator.cavok('4000', '-TSRA', 'SCT020 FEW026CB')
    assert not validator.cavok('4000', 'BR', 'SCT020')

def test_extra():
    m = TafParser('TAF AMD ZJHK 211338Z 211524 14004MPS 4500 -RA BKN030 BECMG 2122 2500 BR BKN012 TEMPO 1519 07005MPS=')
    s = SigmetParser('ZJSA SIGMET 1 VALID 311430/311830 ZJHK-\nZJSA SANYA FIR EMBD TS FCST N OF N16 TOP FL300 MOV N 30KMH NC=', firCode='ZJSA SANYA FIR', airportCode='ZJHK')
    text = m.renderer()
    d = TafParser(text)
    repr(m)
    repr(s)
    m.renderer('terminal')
    s.renderer('terminal')
    assert m.isValid()
    assert s.isValid()
    assert m.isAmended()
    assert m == d
    assert not m.hasMessageChanged()
    assert not s.hasMessageChanged()

def test_metar_fm_trend_period():
    m = MetarParser('METAR ZJHK 210900Z 14004MPS 4500 -RA BKN030 BECMG FM1030 9999 NSW=')
    m.validate()

    assert not m.failed
    assert m.isValid()
    assert m.trends[0].periods[0].strftime('%H%M') == '1030'
    assert m.trends[0].periods[1] == m.primary.periods[1]

def test_metar_without_trend():
    m = MetarParser('METAR ZJHK 210900Z 14004MPS 4500 -RA BKN030 Q1002=')
    m.validate()

    assert not m.failed
    assert m.isValid()
    assert not m.hasTrend()
    assert m.renderer() == 'METAR ZJHK 210900Z 14004MPS 4500 -RA BKN030 Q1002='

def test_metar_with_trend():
    m = MetarParser('METAR ZJHK 210900Z 14004MPS 4500 -RA BKN030 TEMPO AT1020 07005MPS=')
    m.validate()

    assert not m.failed
    assert m.isValid()
    assert m.hasTrend()
    assert m.valids == m.primary.periods
    assert m.trends[0].periods[0].strftime('%H%M') == '1020'
    expected = 'METAR ZJHK 210900Z 14004MPS 4500 -RA BKN030\nTEMPO AT1020 07005MPS='
    assert m.renderer() == expected

def test_metar_nosig():
    m = MetarParser('METAR ZJHK 210900Z 14004MPS 9999 NSW SKC NOSIG=')
    m.validate()

    assert not m.failed
    assert m.isValid()
    assert len(m.trends) == 1
    assert m.trends[0].tokens['nosig']['text'] == 'NOSIG'
    expected = 'METAR ZJHK 210900Z 14004MPS 9999 NSW SKC\nNOSIG='
    assert m.renderer() == expected

def test_metar_dropped_primary_token_detected():
    m = MetarParser('METAR ZJHK 210900Z 14004MPS 4500 -RA BKN030 QQ123 TEMPO AT1020 07005MPS=')
    m.validate()

    assert not m.isValid()

def test_metar_nosig_with_becmg_keeps_trend():
    m = MetarParser('METAR ZJHK 210900Z 14004MPS 4500 -RA BKN030 NOSIG BECMG AT1020 07005MPS=')
    m.validate()

    assert m.trends[0].sign == 'BECMG'
    assert not m.isValid()

def test_metar_trend_only_invalid_primary():
    m = MetarParser('METAR ZJHK 210900Z 14004MPS 4500 -RA BKN030 QQ123=', trendOnly=True)
    m.validate()

    assert not m.isValid()

def test_metar_trend_time_group_out_of_range():
    m = MetarParser('METAR ZJHK 210900Z 14004MPS 4500 -RA BKN030 TEMPO AT0800 07005MPS=')
    m.validate()

    assert '趋势时间组错误' in m.errors
    assert m.trends[0].tokens['fmtl']['error']
    assert not m.isValid()

    m = MetarParser('METAR ZJHK 210900Z 14004MPS 4500 -RA BKN030 TEMPO TL1200 07005MPS=')
    m.validate()

    assert '趋势时间组错误' in m.errors
    assert m.trends[0].tokens['fmtl']['error']

def test_metar_fm_tl_trend_period_overnight():
    m = MetarParser('METAR ZJHK 212300Z 14004MPS 4500 -RA BKN030 BECMG FM2330 TL0030 07005MPS=')
    m.validate()

    assert not m.failed
    assert m.isValid()
    assert m.trends[0].periods[0].strftime('%H%M') == '2330'
    assert m.trends[0].periods[1].strftime('%d%H%M') == '220030'

def test_metar_trend_only_tips_exclude_primary_errors():
    # primary: visibility 4500 with NSW violates the vis/weather rule
    message = 'METAR ZJHK 210900Z 14004MPS 4500 NSW SKC TEMPO AT1020 07005MPS='

    m = MetarParser(message, trendOnly=True)
    m.validate()
    assert m.tips == []

    m = MetarParser(message)
    m.validate()
    assert '能见度小于 5000 米时应有天气现象' in m.tips

def test_metar_is_same_observation():
    m = MetarParser('METAR ZJHK 210900Z 14004MPS 4500 -RA BKN030 TEMPO AT1020 07005MPS=')

    assert m.isSameObservation('METAR ZJHK 210900Z 14004MPS 4500 -RA BKN030 BECMG AT1030 9999 NSW=')
    assert not m.isSameObservation('METAR ZJHK 210900Z 15004MPS 4500 -RA BKN030=')

def test_metar_lexer_accessors():
    m = MetarParser('METAR ZJHK 210900Z 14004MPS 4500 -RA BKN030 OVC080 M03/M05 Q1002=')
    lexer = m.primary

    assert lexer.vis() == 4500
    assert lexer.windSpeed() == 4
    assert lexer.gust() is None
    assert lexer.weathers() == ['-RA']
    assert lexer.clouds() == ['BKN030', 'OVC080']
    assert lexer.ceiling() == 900
    assert lexer.temperature() == -3
    assert lexer.dewpoint() == -5
    assert lexer.pressure() == 1002

def test_metar_lexer_accessors_missing_and_special():
    cavok = MetarParser('METAR ZJHK 210900Z 14004MPS CAVOK=').primary
    assert cavok.vis() == 9999
    assert cavok.clouds() == []
    assert cavok.ceiling() == 1500

    nsc = MetarParser('METAR ZJHK 210900Z 14004MPS 9999 NSW NSC=').primary
    assert nsc.clouds() == []
    assert nsc.ceiling() == 1500

    bare = MetarParser('METAR ZJHK 210900Z=').primary
    assert bare.windSpeed() is None
    assert bare.vis() is None
    assert bare.clouds() == []
    assert bare.ceiling() is None
    assert bare.temperature() is None
    assert bare.pressure() is None

def test_taf_malformed_period(caplog):
    m = TafParser('TAF ZJHK 150726Z 0918 03003MPS 9999 FEW030=')
    m.validate()

    assert m.failed
    assert not m.isValid()
    assert '报文无法被正确解析' in m.errors
    assert 'Malformed TAF period group' in caplog.text


if __name__ == "__main__":
    pytest.main()
