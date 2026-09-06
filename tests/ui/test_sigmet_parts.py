import pytest

from tafor.ui.widgets.sigmet import FlightLevelPart, ForecastPart, SigmetPart


class FakeWidget:

    def __init__(self, **widgets):
        self.__dict__.update(widgets)


class GreedyPart(SigmetPart):

    widgets = ('comeFrom', 'observedTime')


def test_part_fails_fast_on_missing_widgets():
    with pytest.raises(TypeError) as exc:
        GreedyPart(FakeWidget(comeFrom='combo'))

    assert 'observedTime' in str(exc.value)


def test_part_binds_required_widgets():
    part = FlightLevelPart(FakeWidget(
        format='fmt', base='b', top='t', baseLabel='bl', topLabel='tl'))

    assert part.format == 'fmt'
    assert part.top == 't'
    assert part.widget.format == 'fmt'


def test_optional_widgets_default_to_none():
    part = ForecastPart(FakeWidget(forecastTime='f', forecastTimeLabel='l'))

    assert part.forecastTime == 'f'
    assert part.finalPositionGroup is None


def test_optional_widget_bound_when_present():
    part = ForecastPart(FakeWidget(
        forecastTime='f', forecastTimeLabel='l', finalPositionGroup='group'))

    assert part.finalPositionGroup == 'group'


def test_lifecycle_defaults_are_noops():
    part = GreedyPart(FakeWidget(comeFrom='c', observedTime='o'))

    part.bindSignal()
    part.syncToState()
    part.setupValidator()
    part.clear()
    part.setOverlapMode('final')
    part.setLocationMode('polygon')
