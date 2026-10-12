"""Tests for MearchParser behaviours that TAF does not share.

The parser-level cases for METAR already live in test_taf_parser.py: trend
periods, hasTrend, the NOSIG regrouping, trend time validation and
isSameObservation are all covered there, because TAF and METAR run the same
logic. What is left to test here is the METAR-only surface.
"""

from tafor.core.parsers import MetarParser


def parse(message, **kwargs):
    m = MetarParser(message, **kwargs)
    m.validate()
    return m


def test_nosig_contradicting_a_tempo_group_is_flagged():
    # NOSIG promises no significant change; a TEMPO group says otherwise.
    # The trend is kept and the contradiction is marked on the primary report.
    m = parse('METAR ZJHK 210900Z 14004MPS 4500 -RA BKN030 NOSIG TEMPO TL1020 07005MPS=')

    assert m.trends[0].sign == 'TEMPO'
    assert m.primary.tokens['nosig']['error'] == ['nosig_with_trend']
    assert not m.isValid()


def test_html_renderer_joins_elements_with_br():
    m = parse('METAR ZJHK 210900Z 14004MPS 4500 -RA BKN030 BECMG AT1020 07005MPS=')

    expected = (
        'METAR ZJHK 210900Z 14004MPS 4500 -RA BKN030'
        '<br/>BECMG AT1020 07005MPS='
    )
    assert m.renderer(style='html') == expected


def test_html_renderer_keeps_without_a_br_when_there_is_no_trend():
    m = parse('METAR ZJHK 210900Z 14004MPS 4500 -RA BKN030=')

    assert '<br/>' not in m.renderer(style='html')


def test_trend_only_html_greys_out_the_primary_report():
    m = parse('METAR ZJHK 210900Z 14004MPS 4500 -RA BKN030 BECMG AT1020 07005MPS=', trendOnly=True)

    expected = (
        '<span style="color: grey">METAR ZJHK 210900Z 14004MPS 4500 -RA BKN030</span>'
        '<br/>BECMG AT1020 07005MPS='
    )
    assert m.renderer(style='html') == expected


def test_trend_only_html_bolds_the_words_that_changed():
    previous = 'METAR ZJHK 210900Z 14004MPS 4500 -RA BKN030='
    current = 'METAR ZJHK 211000Z 15005MPS 6000 -RA BKN040 BECMG AT1030 07005MPS='
    m = parse(current, trendOnly=True, previous=previous)

    html = m.renderer(style='html')

    # a word carried over from the previous report keeps its plain styling
    assert '<strong>211000Z</strong>' in html
    assert '<strong>15005MPS</strong>' in html
    assert '<strong>6000</strong>' in html
    assert '<strong>BKN040</strong>' in html
    assert '<strong>-RA</strong>' not in html


def test_is_valid_accepts_a_runtime_override_of_the_trend_only_flag():
    # A visibility below 5000 m with no weather present breaks a primary
    # report rule; publishing a trend only excuses that, and the flag can
    # still be overridden at call time.
    m = parse('METAR ZJHK 210900Z 14004MPS 4500 NSW BKN030 BECMG AT1020 07005MPS=', trendOnly=True)

    assert m.isValid() is True
    assert m.isValid(trendOnly=False) is False
