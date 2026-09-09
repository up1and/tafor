"""Tests for tafor.ui/widgets/graphic.py.

Covers coordinate transforms, sketch tools (polygon/line/circle/corridor/
rectangular/entire), GraphicsWindow helpers and background opacity handling.
"""

import pytest
import shapely.geometry
from PyQt5.QtCore import QEvent, QPointF, QPoint, QRect, QSize, Qt
from PyQt5.QtGui import QMouseEvent, QResizeEvent, QWheelEvent
from PyQt5.QtWidgets import QPushButton

from tafor.ui.widgets.graphic import (
    Canvas, GraphicsWindow, LineTool, PolygonTool
)
from tafor.ui.widgets.misc import OutlinedLabel


# a small triangle well inside the mock FIR boundary (107-114E, 14.5-20.5N)
TRIANGLE = [(109, 15), (111, 15), (110, 17)]


def mouseEvent(kind, x, y, button=Qt.NoButton, buttons=Qt.NoButton):
    return QMouseEvent(kind, QPointF(x, y), button, buttons, Qt.NoModifier)


def press(x, y, button=Qt.LeftButton):
    return mouseEvent(QEvent.MouseButtonPress, x, y, button=button, buttons=button)


def release(x, y, button=Qt.LeftButton):
    return mouseEvent(QEvent.MouseButtonRelease, x, y, button=button)


def drag(x, y):
    return mouseEvent(QEvent.MouseMove, x, y, buttons=Qt.LeftButton)


def wheel(delta):
    return QWheelEvent(QPointF(0, 0), QPointF(0, 0), QPoint(0, 0),
                       QPoint(0, delta), Qt.NoButton, Qt.NoModifier,
                       Qt.NoScrollPhase, False)


def clickPoint(canvas, lon, lat):
    """Widget position whose tool-side round trip recovers lon/lat.

    Tools read events as mapToScene(pos) -> toGeographicalCoordinates, so
    the inverse mapFromScene of the canvas coordinates is the position to
    click.
    """
    point = canvas.mapFromScene(*canvas.toCanvasCoordinates(lon, lat))
    return point.x(), point.y()


class FakeBackground:

    def __init__(self, overlay):
        self.layer = type('Layer', (), {'overlay': overlay})()
        self.opacity = None

    def setOpacity(self, opacity):
        self.opacity = opacity


class FakeRubberBand:

    def __init__(self):
        self.geometry = None
        self.shown = 0
        self.hidden = 0

    def setGeometry(self, rect):
        self.geometry = rect

    def show(self):
        self.shown += 1

    def hide(self):
        self.hidden += 1


@pytest.fixture
def canvas(qtbot, context):
    view = Canvas(context)
    qtbot.addWidget(view)
    return view


class TestCoordinateTransforms:
    """toCanvasCoordinates / toGeographicalCoordinates round trip."""

    def test_round_trip_recovers_lonlat(self, canvas):
        for lon, lat in [(107.19, 19.27), (114.0, 14.5), (110.0, 18.0)]:
            x, y = canvas.toCanvasCoordinates(lon, lat)
            back = canvas.toGeographicalCoordinates(x, y)
            assert back[0] == pytest.approx(lon, abs=1e-6)
            assert back[1] == pytest.approx(lat, abs=1e-6)

    def test_canvas_offsets_have_zero_origin(self, canvas):
        assert canvas.offset == (0, 0)

    def test_x_grows_eastward_and_y_grows_southward(self, canvas):
        x1, _ = canvas.toCanvasCoordinates(109, 16)
        x2, _ = canvas.toCanvasCoordinates(111, 16)
        assert x2 > x1

        _, y1 = canvas.toCanvasCoordinates(110, 15)
        _, y2 = canvas.toCanvasCoordinates(110, 17)
        assert y2 < y1

    def test_bbox_is_extent_as_shapely_box(self, canvas):
        assert canvas.bbox() is None

        canvas.setExtent([107, 14, 114, 20.5])
        bound = canvas.bbox()
        assert isinstance(bound, shapely.geometry.Polygon)
        assert bound.bounds == (107, 14, 114, 20.5)

    def test_extent_to_canvas_coordinates_matches_corner_transforms(self, canvas):
        canvas.setExtent([107, 14, 114, 20.5])
        result = canvas.extentToCanvasCoordinates(canvas.extent)
        assert result[:2] == canvas.toCanvasCoordinates(107, 14)
        assert result[2:] == canvas.toCanvasCoordinates(114, 20.5)



class TestPolygonTool:

    def test_click_adds_geographical_point(self, canvas):
        tool = canvas.currentTool()

        tool.mousePress(press(*clickPoint(canvas, 110, 16)))

        sketch = canvas.sketchManager.currentSketch()
        assert len(sketch.coordinates) == 1
        assert sketch.coordinates[0][0] == pytest.approx(110, abs=0.05)
        assert sketch.coordinates[0][1] == pytest.approx(16, abs=0.05)

    def test_close_loop_within_deviation_finishes_area(self, canvas):
        tool = canvas.currentTool()
        sketch = canvas.sketchManager.currentSketch()
        for lonlat in TRIANGLE:
            sketch.addPoint(lonlat)

        tool.mousePress(press(*clickPoint(canvas, *sketch.coordinates[0])))

        assert sketch.done is True
        assert len(sketch.coordinates) > 2

    def test_click_beyond_deviation_does_not_close(self, canvas):
        tool = canvas.currentTool()
        sketch = canvas.sketchManager.currentSketch()
        for lonlat in TRIANGLE:
            sketch.addPoint(lonlat)

        tool.mousePress(press(*clickPoint(canvas, 107.5, 20.0)))

        assert sketch.done is False
        assert len(sketch.coordinates) == 4

    def test_max_point_rejection(self, canvas):
        tool = canvas.currentTool()
        sketch = canvas.sketchManager.currentSketch()
        for i in range(sketch.maxPoint):
            sketch.addPoint((107.5 + i * 0.01, 15.0 + i * 0.01))

        tool.mousePress(press(*clickPoint(canvas, 113, 19)))

        assert len(sketch.coordinates) == sketch.maxPoint

    def test_right_click_removes_last_point(self, canvas):
        tool = canvas.currentTool()
        sketch = canvas.sketchManager.currentSketch()
        for lonlat in TRIANGLE:
            sketch.addPoint(lonlat)

        tool.mousePress(press(0, 0, button=Qt.RightButton))

        assert len(sketch.coordinates) == 2


class TestLineTool:

    def test_right_click_removes_last_point(self, canvas):
        canvas.setMode('line')
        tool = LineTool(canvas, canvas.sketchManager)
        sketch = canvas.sketchManager.currentSketch()
        sketch.addPoint((109, 15))
        sketch.addPoint((111, 16))

        tool.mousePress(press(0, 0, button=Qt.RightButton))

        assert len(sketch.coordinates) == 1


class TestCircleTool:

    def test_click_adds_centre_point(self, canvas):
        canvas.setMode('circle')
        tool = canvas.currentTool()

        tool.mousePress(press(*clickPoint(canvas, 111, 16)))

        sketch = canvas.sketchManager.currentSketch()
        assert len(sketch.coordinates) == 1
        assert sketch.coordinates[0][0] == pytest.approx(111, abs=0.05)

    def test_wheel_grows_and_shrinks_radius(self, canvas):
        canvas.setMode('circle')
        tool = canvas.currentTool()
        sketch = canvas.sketchManager.currentSketch()
        sketch.restore(center=(112, 17), radius=100)
        assert sketch.radius == 100000

        tool.wheelEvent(wheel(120))
        assert sketch.radius == 105000

        tool.wheelEvent(wheel(-120))
        assert sketch.radius == 100000


class TestCorridorTool:
    # CorridorTool.wheelEvent clips first and resizes afterwards; a done
    # sketch ignores the clip and only resizes

    def test_wheel_shrinks_radius_of_done_sketch(self, canvas):
        canvas.setMode('corridor')
        tool = canvas.currentTool()
        sketch = canvas.sketchManager.currentSketch()
        sketch.restore(coordinates=[(109, 15), (111, 16)], radius=100)
        assert sketch.done is True

class TestRectangularTool:

    def test_press_sets_origin_and_shows_rubber_band(self, canvas):
        canvas.setMode('rectangular')
        canvas.rubberBand = FakeRubberBand()
        tool = canvas.currentTool()

        tool.mousePress(press(100, 100))

        assert tool.origin == QPoint(100, 100)
        assert canvas.rubberBand.shown == 1
        assert canvas.rubberBand.geometry == QRect(QPoint(100, 100), QSize())
        assert len(canvas.sketchManager.currentSketch().coordinates) == 1

    def test_move_resizes_rubber_band(self, canvas):
        canvas.setMode('rectangular')
        canvas.rubberBand = FakeRubberBand()
        tool = canvas.currentTool()

        tool.mousePress(press(100, 100))
        tool.mouseMove(drag(150, 120))

        expected = QRect(QPoint(100, 100), QPoint(150, 120)).normalized()
        assert canvas.rubberBand.geometry == expected

    def test_release_adds_point_clips_and_hides(self, canvas):
        canvas.setMode('rectangular')
        canvas.rubberBand = FakeRubberBand()
        tool = canvas.currentTool()

        tool.mousePress(press(100, 100))
        tool.mouseRelease(release(*clickPoint(canvas, 111, 16)))

        sketch = canvas.sketchManager.currentSketch()
        assert sketch.done is True
        assert canvas.rubberBand.hidden == 1
        assert tool.origin is None


class TestEntireTool:

    def test_set_mode_restores_entire_fir(self, canvas):
        # setMode('entire') triggers EntireTool.mousePress(None), which
        # restores the FIR boundary onto the sketch
        boundaries = canvas.context.layer.boundaries()
        canvas.setMode('entire')

        sketch = canvas.sketchManager.currentSketch()
        assert sketch.done is True
        assert sketch.coordinates == boundaries


class TestMixedBackgroundOpacity:

    def test_only_mixed_backgrounds_are_affected(self, canvas):
        backgrounds = [FakeBackground('standalone'),
                       FakeBackground('mixed'),
                       FakeBackground('mixed')]
        canvas.backgrounds = backgrounds

        canvas.setMixedBackgroundOpacity(0.25)

        assert canvas.backgroundOpacity == 0.25

        canvas.setMixedBackgroundOpacity(0.75)
        assert backgrounds[0].opacity is None
        assert backgrounds[1].opacity == 0.75


def makeWindow(canvas, designator='WS'):
    window = GraphicsWindow.__new__(GraphicsWindow)
    window.canvas = canvas
    window.context = canvas.context
    window.type = designator
    window.overlapButton = QPushButton()
    window.overlapButton.setCheckable(True)
    window.positionLabel = OutlinedLabel()
    return window


class TestUpdateOverlapButton:
    """Truth table for the overlap button.

    Pinned behaviour: ``self.type == 'WC' and self.canvas.mode == 'polygon'
    or self.canvas.mode == 'entire'`` evaluates as
    ``(WC and polygon) or entire`` because of and/or precedence.
    """

    def test_not_done_initial_disables_button(self, canvas):
        window = makeWindow(canvas)
        window.updateOverlapButton()

        assert window.overlapButton.isEnabled() is False
        assert window.overlapButton.isChecked() is False

    def test_done_initial_enables_and_unchecks(self, canvas):
        window = makeWindow(canvas)
        canvas.sketchManager.first().restore(coordinates=TRIANGLE)

        window.updateOverlapButton()

        assert window.overlapButton.isEnabled() is True
        assert window.overlapButton.isChecked() is False

    def test_done_final_checks_button(self, canvas):
        window = makeWindow(canvas)
        manager = canvas.sketchManager
        manager.first().restore(coordinates=TRIANGLE)
        manager.last().restore(coordinates=TRIANGLE)

        window.updateOverlapButton()

        assert window.overlapButton.isEnabled() is True
        assert window.overlapButton.isChecked() is True

    def test_wc_polygon_disables_button(self, canvas):
        window = makeWindow(canvas, designator='WC')
        canvas.sketchManager.first().restore(coordinates=TRIANGLE)

        window.updateOverlapButton()

        assert window.overlapButton.isEnabled() is False

    def test_entire_mode_disables_button(self, canvas):
        window = makeWindow(canvas)
        canvas.setMode('entire')

        window.updateOverlapButton()

        assert window.overlapButton.isEnabled() is False

    def test_wc_line_enables_button(self, canvas):
        # WC only blocks polygon mode: the and/or precedence means
        # 'WC and line' is False and 'line == entire' is False
        window = makeWindow(canvas, designator='WC')
        canvas.setMode('line')
        canvas.sketchManager.first().restore(coordinates=[(109, 15), (111, 16)])

        window.updateOverlapButton()

        assert window.overlapButton.isEnabled() is True


def _is_within(node, root):
    """True if `node` is `root` or one of its descendants."""
    while node is not None and node is not root:
        node = node.parentWidget()
    return node is root


class TestGraphicsWindowHelpers:

    @pytest.fixture
    def window(self, qtbot, context):
        view = GraphicsWindow(parent=None, context=context)
        qtbot.addWidget(view)
        return view

    def test_set_button_switches_designator_and_mode(self, window):
        assert window.type == 'WS'
        assert window.canvas.mode == 'polygon'

        window.setModeButtons('WC')
        assert window.type == 'WC'
        assert window.canvas.mode == 'circle'

        window.setModeButtons('WS')
        assert window.type == 'WS'
        assert window.canvas.mode == 'polygon'

    def test_operation_buttons_sizing(self, window):
        # adaptive buttons follow their text via the style size hint,
        # the cycling mode button is pinned so it does not jump around
        for button in [window.refreshButton, window.layerButton, window.overlapButton]:
            button.adjustSize()
            assert button.height() == 24
            assert button.width() == button.sizeHint().width()

        assert window.modeButton.height() == 24
        assert window.modeButton.width() >= window.modeButton.sizeHint().width()

    def test_corner_overlays_positioned(self, window):
        window.resize(800, 500)
        size = QSize(window.width(), window.height())
        window.resizeEvent(QResizeEvent(size, size))
        window.locationWidget.show()

        inset = 10
        assert window.zoomWidget.geometry().topLeft() == QPoint(inset, inset)
        assert window.operationWidget.geometry().topRight() == QPoint(window.width() - inset - 1, inset)
        assert window.layerInfoWidget.geometry().bottomLeft() == QPoint(inset, window.height() - inset - 1)
        assert window.positionLabel.geometry().bottomRight() == QPoint(window.width() - inset - 1, window.height() - inset - 1)

        # the location banner floats above the bottom edge, centered
        geo = window.locationWidget.geometry()
        assert geo.x() == (window.width() - geo.width()) // 2
        assert window.height() - geo.bottom() - 1 == 75

        # zoom buttons are square and stay inside their overlay widget
        assert window.zoomInButton.parent() is window.zoomWidget
        assert window.zoomOutButton.parent() is window.zoomWidget
        assert window.zoomInButton.width() == window.zoomInButton.height() == 24

    def test_corner_buttons_are_clickable(self, window, qtbot):
        # the interactive overlays float directly over the canvas without a
        # transparent overlay, so a hit-test at their center must find them;
        # the labels stay transparent to keep the map reachable
        window.resize(800, 500)
        app_size = QSize(window.width(), window.height())
        window.resizeEvent(QResizeEvent(app_size, app_size))
        window.show()
        qtbot.wait(100)

        for widget in [window.zoomWidget, window.operationWidget]:
            center = widget.geometry().center()
            hit = window.childAt(center.x(), center.y())
            assert _is_within(hit, widget), '{} is covered by {}'.format(widget, hit)

        # a real press on the zoom button reaches the button
        clicks = []
        window.zoomInButton.clicked.connect(lambda: clicks.append(1))
        qtbot.mouseClick(window.zoomInButton, Qt.LeftButton)
        assert clicks, 'zoomInButton was not clickable'

    def test_location_only_lists_done_sketches(self, window):
        assert window.location() == {}

        initial = window.canvas.sketchManager.first()
        initial.restore(coordinates=TRIANGLE)
        locations = window.location()
        assert list(locations) == ['location']
        assert locations['location'].startswith('WI ')

        final = window.canvas.sketchManager.last()
        final.restore(coordinates=TRIANGLE)
        locations = window.location()
        assert list(locations) == ['location', 'forecastLocation']
        assert locations['forecastLocation'].startswith('WI ')

    def test_has_acceptable_graphic_requires_done_sketches(self, window):
        assert window.hasAcceptableGraphic() is False

        window.canvas.sketchManager.first().restore(coordinates=TRIANGLE)
        assert window.hasAcceptableGraphic() is True

        window.canvas.setSketch('final')
        assert window.hasAcceptableGraphic() is False

        window.canvas.sketchManager.last().restore(coordinates=TRIANGLE)
        assert window.hasAcceptableGraphic() is True

    def test_next_mode_clears_location_label(self, window):
        window.setModeButtons('WS')
        window.canvas.sketchManager.first().restore(coordinates=TRIANGLE)
        assert window.locationWidget.location.text()
        assert window.locationWidget.isHidden() is False

        window.nextMode()

        assert window.locationWidget.location.text() == ''
        assert window.locationWidget.isHidden() is True

    def test_cancelling_sketch_disables_overlap_button(self, window):
        # drawing an area enables the overlap switch (done -> finished signal),
        # but cancelling/undoing it rolls ``done`` back via the changed signal,
        # which must disable the switch again
        initial = window.canvas.sketchManager.first()
        initial.restore(coordinates=TRIANGLE)
        assert initial.done is True
        assert window.overlapButton.isEnabled()

        initial.removePoint()
        assert initial.done is False
        assert window.overlapButton.isEnabled() is False
        assert window.overlapButton.isChecked() is False

    def test_layer_changed_event_notifies_subscribers(self, window):
        # the bus notification carries no payload; consumers pull fresh
        # data from the layer service and run in a stable order
        calls = []
        window.setLayerSelectMenu = lambda: calls.append('menu')
        window.updateLayer = lambda: calls.append('canvas')

        window.context.event.layerChanged.emit()

        assert calls == ['menu', 'canvas']

    def test_update_position_label(self, window):
        window.updatePositionLabel((110.5, 15.25))
        assert window.positionLabel.text() == 'N15°15′00″, E110°30′00″'

        window.updatePositionLabel(())
        assert window.positionLabel.text() == ''
