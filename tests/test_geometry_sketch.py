import inspect

import tafor.core.geometry.sketch as sketch_module
from tafor.core.geometry.sketch import (
    CircleSketch, CorridorSketch, EntireSketch, LineSketch, PolygonSketch,
    RectangularSketch, Sketch, mergeGeometries,
)


def log_signals(sketch):
    events = []
    sketch.changed.connect(lambda: events.append('changed'))
    sketch.finished.connect(lambda: events.append('finished'))
    return events


def test_module_has_no_qt_dependency():
    assert 'PyQt5' not in inspect.getsource(sketch_module)


def test_polygon_sketch_text_and_geometry():
    sketch = PolygonSketch('initial')
    assert not sketch
    assert sketch.text(None) == ''

    sketch.addPoint((110.0, 20.0))
    sketch.addPoint((111.0, 21.0))

    assert sketch
    assert not sketch.done
    assert sketch.text(None) == 'N2000 E11000 - N2100 E11100'
    assert sketch.geometry()['geometries'] == [
        {'type': 'LineString', 'coordinates': [(110.0, 20.0), (111.0, 21.0)]}
    ]

    sketch.restore(coordinates=[(110.0, 20.0), (111.0, 21.0), (112.0, 20.0)])

    assert sketch.done
    assert sketch.text(None) == 'WI N2000 E11000 - N2100 E11100 - N2000 E11200'
    assert sketch.geometry()['geometries'][0]['type'] == 'Polygon'


def test_line_sketch_restore_geometry():
    sketch = LineSketch('initial')
    sketch.restore(coordinates=[(110.0, 20.0), (111.0, 21.0), (112.0, 20.0)])

    assert sketch.done
    assert sketch.geometry()['geometries'] == [
        {'type': 'Polygon', 'coordinates': [(110.0, 20.0), (111.0, 21.0), (112.0, 20.0)]}
    ]


def test_circle_sketch_rounds_radius_to_deviation():
    sketch = CircleSketch('initial')
    sketch.addPoint((110.0, 20.0))
    sketch.addPoint((110.0, 20.05))

    assert sketch.done
    assert sketch.radius == 5000
    assert sketch.text(None) == 'PSN N2000 E11000 / WI 5KM OF CENTRE'

    geometries = sketch.geometry()['geometries']
    assert geometries[0]['type'] == 'Polygon'
    assert geometries[1] == {'type': 'Point', 'coordinates': (110.0, 20.0)}


def test_circle_sketch_restore_and_feature():
    sketch = CircleSketch('initial')
    sketch.restore(center=(110.0, 20.0), radius=30)

    assert sketch.done
    assert sketch.radius == 30000
    assert sketch.feature()['properties'] == {'radius': 30, 'location': 'initial'}


def test_circle_sketch_radius_text_omitted_for_final():
    sketch = CircleSketch('final')
    sketch.restore(center=(110.0, 20.0), radius=30)

    assert sketch.text(None) == 'PSN N2000 E11000'


def test_corridor_sketch_text():
    sketch = CorridorSketch('initial')
    sketch.restore(coordinates=[(110.0, 20.0), (111.0, 21.0)], radius=25)

    assert sketch.done
    assert sketch.radius == 12500
    assert sketch.text(None) == 'APRX 25KM WID LINE BTN N2000 E11000 - N2100 E11100'


def test_rectangular_sketch_restore_geometry():
    sketch = RectangularSketch('initial')
    assert sketch.geometry()['geometries'] == []

    sketch.restore(coordinates=[(110.0, 20.0), (111.0, 21.0), (112.0, 20.0)])

    assert sketch.done
    assert sketch.geometry()['geometries'][0]['type'] == 'Polygon'


def test_entire_sketch_text():
    sketch = EntireSketch('initial')
    assert sketch.text(None) == ''

    sketch.restore(boundaries=[(110.0, 20.0), (111.0, 21.0), (112.0, 20.0)])

    assert sketch.done
    assert sketch.text(None) == 'ENTIRE FIR'
    assert sketch.geometry()['geometries'][0]['type'] == 'Polygon'


def test_signal_order_on_lifecycle():
    sketch = PolygonSketch('initial')
    events = log_signals(sketch)

    sketch.addPoint((110.0, 20.0))
    assert events == ['changed']

    events.clear()
    sketch.restore(coordinates=[(110.0, 20.0), (111.0, 21.0), (112.0, 20.0)])
    assert events == ['finished', 'changed']

    events.clear()
    sketch.clear()
    assert events == ['finished', 'changed']
    assert not sketch


def test_sketches_do_not_share_signals():
    a = PolygonSketch('initial')
    b = PolygonSketch('final')
    events = log_signals(a)

    b.addPoint((110.0, 20.0))
    assert events == []

    a.addPoint((110.0, 20.0))
    assert events == ['changed']


def test_merge_geometries_skips_empty():
    collections = mergeGeometries([None, '', {'type': 'Point', 'coordinates': (1, 2)}])

    assert collections == {
        'type': 'GeometryCollection',
        'geometries': [{'type': 'Point', 'coordinates': (1, 2)}],
    }
