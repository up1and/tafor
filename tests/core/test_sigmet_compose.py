import datetime
import inspect

import pytest

import tafor.core.sigmet.compose as compose_module
from tafor.core.geometry.sketch import (
    CircleSketch, CorridorSketch, EntireSketch, LineSketch, PolygonSketch,
    RectangularSketch,
)
from tafor.core.sigmet.compose import (
    adjustCancelBeginning, composeHeading, formatLocation, nextSequence,
    validDuration, validPeriod,
)
from tafor.core.states import SigmetMonitorService, SigmetMonitorState

NOW = datetime.datetime(2026, 8, 23, 12, 0)
PERIOD_START = datetime.datetime(2026, 8, 23, 12, 10)


def test_compose_heading():
    now = datetime.datetime(2026, 8, 23, 12, 5)

    assert composeHeading('WS', 'NT36', 'YUSO', now) == 'WSNT36 YUSO 231205'
    assert composeHeading('WS', '', 'YUSO', now) == 'WS YUSO 231205'


def test_valid_duration():
    assert validDuration('WS') == 4
    assert validDuration('WC') == 6
    assert validDuration('WV') == 6
    assert validDuration('WA') == 4

    with pytest.raises(KeyError):
        validDuration('XX')


def test_next_sequence_ignores_yesterday_and_midnight():
    today = datetime.datetime(2026, 8, 23, 12)
    headings = [
        'WSNT36 YUSO 231200',   # issued today, counted
        'WSNT36 YUSO 221200',   # issued yesterday, ignored
        'WSNT36 YUSO 230000',   # issued at 0000, ignored
        'WSNT36 YUSO',          # no issue time, counted
    ]

    assert nextSequence(headings, today) == 3
    assert nextSequence([], today) == 1


def test_valid_period_wc_uses_next_full_hour():
    now = datetime.datetime(2026, 8, 23, 12, 3)

    start, end = validPeriod('WC', 6, now)

    assert start == datetime.datetime(2026, 8, 23, 13, 0)
    assert end == datetime.datetime(2026, 8, 23, 19, 0)


def test_valid_period_others_ceil_to_ten_minutes():
    now = datetime.datetime(2026, 8, 23, 12, 3)

    start, end = validPeriod('WS', 4, now)

    assert start == datetime.datetime(2026, 8, 23, 12, 10)
    assert end == datetime.datetime(2026, 8, 23, 16, 10)


def test_adjust_cancel_beginning_uses_later_input_within_12h():
    beginning = adjustCancelBeginning('231300', PERIOD_START, '231600', NOW)

    assert beginning == datetime.datetime(2026, 8, 23, 13, 0)


def test_adjust_cancel_beginning_backs_off_from_ending():
    beginning = adjustCancelBeginning('231300', PERIOD_START, '231300', NOW)

    assert beginning == datetime.datetime(2026, 8, 23, 12, 50)


def test_adjust_cancel_beginning_keeps_period_start_beyond_12h():
    beginning = adjustCancelBeginning('240100', PERIOD_START, '231600', NOW)

    assert beginning == PERIOD_START


def test_adjust_cancel_beginning_keeps_period_start_when_input_earlier():
    beginning = adjustCancelBeginning('231205', PERIOD_START, '231600', NOW)

    assert beginning == PERIOD_START


def test_compose_module_has_no_qt_dependency():
    assert 'PyQt5' not in inspect.getsource(compose_module)


def test_polygon_text_lists_points_then_prepends_wi_when_done():
    sketch = PolygonSketch('initial')
    assert formatLocation(sketch, None) == ''

    sketch.addPoint((110.0, 20.0))
    sketch.addPoint((111.0, 21.0))
    assert formatLocation(sketch, None) == 'N2000 E11000 - N2100 E11100'

    sketch.restore(coordinates=[(110.0, 20.0), (111.0, 21.0), (112.0, 20.0)])
    assert formatLocation(sketch, None) == 'WI N2000 E11000 - N2100 E11100 - N2000 E11200'


def test_line_text_reports_boundary_parallel_lines():
    sketch = LineSketch('initial')
    sketch.restore(coordinates=[(0.0, 0.0), (10.0, 0.0), (10.0, 5.0), (0.0, 5.0)])
    fir = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]

    assert formatLocation(sketch, fir) == 'S OF LINE N0500 E01000 - N0500 E00000'


def test_line_text_in_progress_lists_points():
    sketch = LineSketch('initial')
    sketch.addPoint((110.0, 20.0))
    sketch.addPoint((111.0, 21.0))

    assert formatLocation(sketch, None) == 'N2000 E11000 - N2100 E11100'


def test_circle_text_rounds_radius_to_deviation():
    sketch = CircleSketch('initial')
    sketch.addPoint((110.0, 20.0))
    sketch.addPoint((110.0, 20.05))

    assert formatLocation(sketch, None) == 'PSN N2000 E11000 / WI 5KM OF CENTRE'


def test_circle_text_omits_radius_when_with_radius_is_false():
    sketch = CircleSketch('final', withRadius=False)
    sketch.restore(center=(110.0, 20.0), radius=30)

    assert formatLocation(sketch, None) == 'PSN N2000 E11000'


def test_corridor_text_reports_width_between_points():
    sketch = CorridorSketch('initial')
    sketch.restore(coordinates=[(110.0, 20.0), (111.0, 21.0)], radius=25)

    assert formatLocation(sketch, None) == 'APRX 25KM WID LINE BTN N2000 E11000 - N2100 E11100'


def test_rectangular_text_reports_shared_coordinates():
    # a band spanning the whole FIR width: its E/W edges lie on the FIR
    # boundary, so only the two boundary-parallel lines are reported
    sketch = RectangularSketch('initial')
    sketch.restore(coordinates=[(100.0, 3.0), (110.0, 3.0), (110.0, 6.0), (100.0, 6.0)])
    boundaries = [(100.0, 0.0), (110.0, 0.0), (110.0, 10.0), (100.0, 10.0)]

    text = formatLocation(sketch, boundaries)

    assert set(text.split(' AND ')) == {'N OF N0300', 'S OF N0600'}


def test_rectangular_text_is_empty_before_the_area_is_clipped():
    sketch = RectangularSketch('initial')
    sketch.addPoint((110.0, 20.0))
    sketch.addPoint((111.0, 21.0))

    assert formatLocation(sketch, None) == ''


def test_entire_text():
    sketch = EntireSketch('initial')
    assert formatLocation(sketch, None) == ''

    sketch.restore(boundaries=[(110.0, 20.0), (111.0, 21.0), (112.0, 20.0)])
    assert formatLocation(sketch, None) == 'ENTIRE FIR'


class FakePrevParser:

    def __init__(self, sequence, validTime):
        self._sequence = sequence
        self._validTime = validTime

    def sequence(self):
        return self._sequence

    def validTime(self):
        return self._validTime


class FakeSig:

    def __init__(self, cancelSequence=None):
        self._cancelSequence = cancelSequence

    def cancelSequence(self):
        return self._cancelSequence


class FakeMessage:

    def __init__(self, uuid='u1', isCnl=False, expired=None, parser=None):
        self.uuid = uuid
        self._isCnl = isCnl
        self._expired = expired or datetime.datetime(2026, 8, 23, 16, 0)
        self._parser = parser if parser is not None else 'SIGMET TEXT'

    def isCnl(self):
        return self._isCnl

    def expired(self):
        return self._expired

    def parser(self):
        return self._parser


def makeMonitor():
    return SigmetMonitorService(SigmetMonitorState(), None)


def test_sync_sigmet_reminder_adds_entry_on_send():
    monitor = makeMonitor()
    expired = datetime.datetime(2026, 8, 23, 16, 0)
    message = FakeMessage(uuid='u1', expired=expired)

    monitor.updateReminders(message)

    assert monitor.entries == {'u1': {'text': 'SIGMET TEXT', 'time': expired}}


def test_sync_sigmet_reminder_cancel_drops_matching_entry():
    monitor = makeMonitor()
    monitor.add('u1', FakePrevParser('A3', '231200/231600'),
                datetime.datetime(2026, 8, 23, 16, 0))
    monitor.add('u2', FakePrevParser('A4', '231200/231600'),
                datetime.datetime(2026, 8, 23, 16, 0))
    cancelSig = FakeSig(cancelSequence=('A3', '231200/231600'))
    message = FakeMessage(uuid='u3', isCnl=True, parser=cancelSig)

    monitor.updateReminders(message)

    assert 'u1' not in monitor.entries
    assert 'u2' in monitor.entries
