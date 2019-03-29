import os
import re

import pytest

from tafor.utils import TafParser, TafValidator, SigmetParser

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

def test_pure_pattern():
    from tafor.utils.validator import _purePattern
    pattern = r'^(0|[1-9][0-9]*)$'
    regex = re.compile(pattern)
    assert _purePattern(regex) == pattern[1:]


if __name__ == "__main__":
    pytest.main()
