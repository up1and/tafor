import re

import pytest

from tafor.core.parsers import MetarParser, SigmetParser, TafParser, TafValidator


@pytest.fixture
def validator():
    return TafValidator()

def test_taf_parser(fixtures_dir):
    folder = fixtures_dir / 'taf'
    for filepath in sorted(folder.glob('*.text')):
        content = filepath.read_text()

        m = TafParser(content)
        m.validate()
        html = m.renderer(style='html')
        result = filepath.with_suffix('.html').read_text()

        html = re.sub(r'\s', '', html)
        result = re.sub(r'\s', '', result)
        assert result == html

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

    assert not m.error
    assert m.isValid()
    assert m.trends[0].periods[0].strftime('%H%M') == '1030'
    assert m.trends[0].periods[1] == m.primary.periods[1]

def test_metar_without_trend():
    m = MetarParser('METAR ZJHK 210900Z 14004MPS 4500 -RA BKN030 Q1002=')
    m.validate()

    assert not m.error
    assert m.isValid()
    assert not m.hasTrend()
    assert m.renderer() == 'METAR ZJHK 210900Z 14004MPS 4500 -RA BKN030 Q1002='

def test_metar_with_trend():
    m = MetarParser('METAR ZJHK 210900Z 14004MPS 4500 -RA BKN030 TEMPO AT1020 07005MPS=')
    m.validate()

    assert not m.error
    assert m.isValid()
    assert m.hasTrend()
    assert m.valids == m.primary.periods
    assert m.trends[0].periods[0].strftime('%H%M') == '1020'
    expected = 'METAR ZJHK 210900Z 14004MPS 4500 -RA BKN030\nTEMPO AT1020 07005MPS='
    assert m.renderer() == expected

def test_metar_nosig():
    m = MetarParser('METAR ZJHK 210900Z 14004MPS 9999 NSW SKC NOSIG=')
    m.validate()

    assert not m.error
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

    assert '趋势时间组错误' in m.tips
    assert m.trends[0].tokens['fmtl']['error'] == ['trend_time_invalid']
    assert not m.isValid()

    m = MetarParser('METAR ZJHK 210900Z 14004MPS 4500 -RA BKN030 TEMPO TL1200 07005MPS=')
    m.validate()

    assert '趋势时间组错误' in m.tips
    assert m.trends[0].tokens['fmtl']['error'] == ['trend_time_invalid']

def test_metar_fm_tl_trend_period_overnight():
    m = MetarParser('METAR ZJHK 212300Z 14004MPS 4500 -RA BKN030 BECMG FM2330 TL0030 07005MPS=')
    m.validate()

    assert not m.error
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

    assert m.error
    assert not m.isValid()
    assert '报文无法被正确解析' in m.tips
    assert 'Malformed TAF period group' in caplog.text

def test_pipeline_steps_exist():
    for parser in (TafParser, MetarParser):
        for step in parser.pipeline:
            assert callable(getattr(parser, step))

def test_failed_renderer_marks_whole_message():
    m = TafParser('TAF ZJHK 150726Z 0918 03003MPS 9999 FEW030=')
    m.validate()

    assert m.error
    assert 'color: red' in m.renderer(style='html')

    # message-level failure is expressed at render time, token data stays clean
    assert all(not token['error'] for e in m.elements for token in e.tokens.values())

def test_has_message_changed_sets_failed():
    m = TafParser('TAF ZJHK 150726Z 0918 03003MPS 9999 FEW030 UNKNOWN01=')
    m.validate()

    assert m.error
    assert not m.isValid()
    assert 'color: red' in m.renderer(style='html')

def test_taf_combination_returns_findings(validator):
    ref = {
        'vis': {'text': '9999', 'error': []},
        'weather': {'text': 'NSW', 'error': []},
        'cloud': {'text': 'FEW030', 'error': []},
    }
    tokens = {
        'weather': {'text': 'NSW BR', 'error': []},
        'vis': {'text': '0800', 'error': []},
    }

    violations = validator.combination(ref, tokens)

    codes = [code for _, code in violations]
    assert 'vis_weather_required' in codes
    assert 'nsw_conflict' in codes
    # 纯函数：不修改传入的 ref 和 tokens
    assert tokens['weather']['error'] == []
    assert ref['weather']['text'] == 'NSW'

def test_taf_same_token_multiple_violations_kept():
    # vis 0800 + NSW BR：能见度规则与 NSW 独占规则同时击中 weather token
    m = TafParser('TAF ZJHK 150726Z 150918 03003MPS 9999 FEW030 TEMPO 1112 0800 NSW BR=')
    m.validate()

    assert m.tempos[0].tokens['weather']['error'] == ['vis_weather_required', 'nsw_conflict']
    assert '能见度小于 5000 米时应有天气现象' in m.tips
    assert 'NSW 不能和其他天气现象同时存在' in m.tips
    assert not m.isValid()

def test_taf_turnover_failure_marks_token_without_tip():
    m = TafParser('TAF ZJHK 150726Z 150918 03003MPS 9999 FEW030 BECMG 1112 05003MPS=')
    m.validate()

    assert m.becmgs[0].tokens['wind']['error'] == ['wind_turnover']
    # 转折约定码不在文案目录中，只标红不产生提示
    assert m.tips == []
    assert not m.isValid()

def test_taf_validator_is_replaceable():
    message = 'TAF ZJHK 150726Z 150918 03003MPS 9999 FEW030 TEMPO 1112 0800 NSW BR='

    default = TafParser(message)
    default.validate()
    assert not default.isValid()
    assert '能见度小于 5000 米时应有天气现象' in default.tips

    class DemoValidator(TafValidator):
        """演示方案：转折全部放行、自定组合规则，文案换成英文"""

        messages = {'demo_conflict': 'Demo conflict message'}

        def wind(self, refWind, wind):
            return True

        def vis(self, refVis, vis):
            return True

        def weather(self, refWeather, weather):
            return True

        def cloud(self, refCloud, cloud):
            return True

        def combination(self, ref, tokens):
            return [('weather', 'demo_conflict')]

    demo = TafParser(message, validator=DemoValidator())
    demo.validate()

    assert demo.tempos[0].tokens['weather']['error'] == ['demo_conflict']
    assert demo.tempos[0].tokens['vis']['error'] == []
    assert demo.tips == ['Demo conflict message']
    assert not demo.isValid()

def test_taf_validator_protocol_duck_typing():
    """协议钉子：校验器未定义的要素方法，对应要素跳过校验"""

    class WindOnlyValidator:
        messages = {}

        def wind(self, refWind, wind):
            return False

        def skipTurnover(self, key, ref, tokens):
            return False

        def combination(self, ref, tokens):
            return []

    m = TafParser('TAF ZJHK 150726Z 150918 03003MPS 9999 FEW030 BECMG 1112 07006MPS 8000 BR BKN012=', validator=WindOnlyValidator())
    m.validate()

    group = m.becmgs[0]
    assert group.tokens['wind']['error'] == ['wind_turnover']
    assert group.tokens['vis']['error'] == []
    assert group.tokens['weather']['error'] == []
    assert group.tokens['cloud']['error'] == []
    assert m.tips == []
    assert not m.isValid()


if __name__ == "__main__":
    pytest.main()
