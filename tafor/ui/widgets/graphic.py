import os
import logging

import shapefile
import shapely.geometry
from shapely.affinity import scale

from itertools import cycle

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGraphicsView, QGraphicsScene, QRubberBand,
    QStyleOptionGraphicsItem, QPushButton, QLabel, QMenu, QActionGroup, QAction, QWidgetAction, QSlider, QSpacerItem, QSizePolicy)
from PyQt5.QtGui import QFontMetrics, QPainter
from PyQt5.QtCore import QCoreApplication, Qt, QRect, QRectF, QSize, pyqtSignal

from tafor.core.geometry.coordinate import degTodms
from tafor.core.geometry import geojson
from tafor.core.sigmet.compose import formatLocation
from tafor.core.utils.common import resourcePath
from tafor.ui.fonts import fixedFont
from tafor.ui.widgets.sketch import SketchManager
from tafor.ui.widgets.geometry import BackgroundImage, Coastline, Fir, Sigmet
from tafor.ui.widgets.misc import OutlinedLabel

logger = logging.getLogger(__name__)


class ToolContext:
    """Everything a drawing tool is allowed to reach.

    Deliberately narrow: a tool never sees the view, the scene or the panel, so
    the six tools can be exercised with plain Python objects and no Qt at all.

    ``boundary`` and ``band`` are callables rather than values because both
    change under the tool's feet -- the FIR boundary follows the selected layer,
    and the rubber band is swapped out by tests.
    """

    def __init__(self, registry, toGeo, toView, boundary, band):
        self.registry = registry
        self.toGeo = toGeo
        self.toView = toView
        self.boundary = boundary
        self.band = band


class SketchTool:
    """What a mouse or key event means in one drawing mode."""

    def __init__(self, context):
        self.context = context

    @property
    def sketch(self):
        return self.context.registry.currentSketch()

    def toLonLat(self, point):
        return self.context.toGeo(point)

    def mousePress(self, event):
        pass

    def mouseMove(self, event):
        pass

    def mouseRelease(self, event):
        pass

    def wheelEvent(self, event):
        pass

    def keyPress(self, event):
        pass

    def keyRelease(self, event):
        pass


class PolygonTool(SketchTool):

    def mousePress(self, event):
        if event.button() == Qt.LeftButton:
            if len(self.sketch.coordinates) > 2:
                deviation = 12
                firstPoint = self.context.toView(self.sketch.coordinates[0])
                dx = abs(event.pos().x() - firstPoint.x())
                dy = abs(event.pos().y() - firstPoint.y())
                if dx < deviation and dy < deviation:
                    self.sketch.clip(self.context.boundary())
                    return

            if not self.sketch.done and len(self.sketch.coordinates) < self.sketch.maxPoint:
                self.sketch.addPoint(self.toLonLat(event.pos()))

        if event.button() == Qt.RightButton:
            self.sketch.removePoint()


class LineTool(PolygonTool):
    pass


class CircleTool(SketchTool):

    def mousePress(self, event):
        if event.button() == Qt.LeftButton:
            self.sketch.addPoint(self.toLonLat(event.pos()))
        if event.button() == Qt.RightButton:
            self.sketch.removePoint()

    def wheelEvent(self, event):
        ratio = 1 if event.angleDelta().y() > 0 else -1
        self.sketch.resize(ratio)


class CorridorTool(SketchTool):

    def mousePress(self, event):
        if event.button() == Qt.LeftButton:
            self.sketch.addPoint(self.toLonLat(event.pos()))
        if event.button() == Qt.RightButton:
            self.sketch.removePoint()

    def wheelEvent(self, event):
        ratio = 1 if event.angleDelta().y() > 0 else -1
        self.sketch.clip(self.context.boundary())
        self.sketch.resize(ratio)


class RectangularTool(SketchTool):

    def __init__(self, context):
        super().__init__(context)
        self.origin = None

    def mousePress(self, event):
        if event.button() == Qt.LeftButton:
            self.origin = event.pos()
            if not self.sketch:
                band = self.context.band()
                band.setGeometry(QRect(self.origin, QSize()))
                band.show()
                self.sketch.addPoint(self.toLonLat(event.pos()))
        if event.button() == Qt.RightButton:
            self.sketch.removePoint()

    def mouseMove(self, event):
        if event.buttons() & Qt.LeftButton and self.origin:
            self.context.band().setGeometry(QRect(self.origin, event.pos()).normalized())

    def mouseRelease(self, event):
        if event.button() == Qt.LeftButton and self.origin:
            self.context.band().hide()
            self.sketch.addPoint(self.toLonLat(event.pos()))
            self.sketch.clip(self.context.boundary())
            self.origin = None


class EntireTool(SketchTool):
    """The whole FIR is the area, so there is nothing to draw."""

    def mousePress(self, event):
        self.restore()

    def restore(self):
        self.sketch.restore(boundaries=list(self.context.boundary()))


class SceneLayer:
    """One group of graphics items, replaceable as a unit.

    Every rebuild in this module used to hand-roll its own "drop the old items,
    then make a group" dance, and one of them forgot the first half -- which is
    why the FIR boundary accumulated another group on every redraw. There is now
    a single place that can get it wrong.
    """

    def __init__(self, view, z=0):
        self.view = view
        self.z = z
        self.items = []
        self.group = None

    def replace(self, items):
        self.clear()
        self.items = list(items)

        if self.items:
            self.group = self.view.scene.createItemGroup(self.items)
            self.group.setZValue(self.z)

    def clear(self):
        if self.group is not None:
            self.view.scene.removeItem(self.group)
            self.group = None

        self.items = []

    def boundingRect(self):
        if self.group is not None:
            return self.group.boundingRect()


class MapView(QGraphicsView):
    """Shared map view: projection, the item layers, pan and zoom.

    Panning and zooming used to be copy-pasted into both concrete views; the
    only thing that actually differed was the zoom policy, so that is now the
    only thing a subclass overrides.
    """

    #: zoom policy -- subclasses narrow it
    initialScale = 1.0
    maxZoom = 5
    minZoom = 0.15

    mouseMoved = pyqtSignal(tuple)

    def __init__(self, context):
        super().__init__()
        self.context = context
        self.extent = []

        self.coastlines = SceneLayer(self)
        self.firs = SceneLayer(self, z=1)
        self.sigmets = SceneLayer(self, z=2)

        self.projection = self.context.layer.projection()
        if self.projection.crs.is_geographic:
            self.ratio = 100
        else:
            self.ratio = 1 / 1000

        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setTransformationAnchor(QGraphicsView.AnchorViewCenter)
        self.setRenderHint(QPainter.Antialiasing)
        self.setFocusPolicy(Qt.StrongFocus)

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        if self.initialScale != 1.0:
            self.scale(self.initialScale, self.initialScale)

    def setExtent(self, extent):
        self.extent = extent

    def bbox(self):
        if self.extent:
            bound = shapely.geometry.box(*self.extent)
        else:
            bound = None

        return bound

    def drawCoastline(self):
        filename = os.path.join(resourcePath('shapes'), 'coastline.shp')
        shapes = shapefile.Reader(filename).shapes()

        if not self.extent:
            self.setExtent(self.context.layer.maxExtent())

        bound = self.bbox()
        items = []
        for shape in shapes:
            polygon = shapely.geometry.shape(shape)
            if bound:
                polygon = bound.intersection(polygon)

            if polygon.geom_type == 'MultiPolygon':
                polygons = polygon.geoms
            else:
                polygons = [polygon]

            for part in polygons:
                if not part.is_empty:
                    Coastline(geojson.polygon(part.exterior.coords)).addTo(self, items)

        self.coastlines.replace(items)
        self.setSceneRect(self.scene.itemsBoundingRect())

    def drawBoundaries(self):
        boundaries = self.context.layer.boundaries()
        if not boundaries:
            self.firs.clear()
            return

        items = []
        Fir(geojson.polygon(boundaries)).addTo(self, items)
        self.firs.replace(items)

    def drawSigmets(self, geometries):
        items = []
        for geometry in geometries:
            Sigmet(geo=geometry).addTo(self, items)
        self.sigmets.replace(items)

        if not self.context.layer.boundaries():
            self.centerOnLayer(self.sigmets)

    def centerOnLayer(self, layer):
        rect = layer.boundingRect()
        if rect is not None:
            self.centerOn(rect.center())

    def currentZoom(self):
        return QStyleOptionGraphicsItem.levelOfDetailFromTransform(self.transform())

    def zoomIn(self):
        if self.currentZoom() < self.maxZoom:
            self.scale(1.25, 1.25)

    def zoomOut(self):
        if self.currentZoom() > self.minZoom:
            self.scale(0.8, 0.8)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.setDragMode(QGraphicsView.ScrollHandDrag)
            self.pos = event.pos()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            delta = self.pos - event.pos()
            self.pos = event.pos()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() + delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() + delta.y())

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.setDragMode(QGraphicsView.NoDrag)
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.zoomIn()

    def wheelEvent(self, event):
        if event.angleDelta().y() > 0:
            self.zoomIn()
        else:
            self.zoomOut()

    def emitMouseMoved(self, event):
        pos = self.mapToScene(event.pos())
        self.mouseMoved.emit(self.toGeographicalCoordinates(pos.x(), pos.y()))

    def toGeographicalCoordinates(self, x, y):
        return self.projection(x / self.ratio, -y / self.ratio, inverse=True)

    def toCanvasCoordinates(self, longitude, latitude):
        px, py = self.projection(longitude, latitude)
        return px * self.ratio, -py * self.ratio

    def redraw(self):
        self.drawCoastline()
        self.drawBoundaries()
        self.centerOnLayer(self.firs)


class StaticView(MapView):
    """Read-only map: the same pan and zoom, no drawing state at all."""

    initialScale = 0.4096
    maxZoom = 1.0
    minZoom = 0.4


class SketchView(MapView):
    """The editable map: a MapView plus one pluggable drawing tool."""

    #: the user handed an event to the current tool, so the drawing moved.
    #: Programmatic writes to a sketch do not come through here.
    interacted = pyqtSignal()

    maxZoom = 5
    minZoom = 0.15

    def __init__(self, context):
        super().__init__(context)
        self.backgrounds = []
        self.backgroundOpacity = 0.5
        self.maxLayerExtent = self.context.layer.maxExtent()
        self.backgroundLayer = SceneLayer(self, z=-1)

        self.setMouseTracking(True)

        self.rubberBand = QRubberBand(QRubberBand.Rectangle, self)
        self.sketchManager = SketchManager(self, sketchNames=['initial', 'final'])
        self.toolContext = ToolContext(
            registry=self.sketchManager,
            toGeo=self.toGeographicalPoint,
            toView=self.toViewPoint,
            boundary=self.context.layer.boundaries,
            band=lambda: self.rubberBand,
        )
        self.tools = {
            'polygon': PolygonTool(self.toolContext),
            'line': LineTool(self.toolContext),
            'circle': CircleTool(self.toolContext),
            'corridor': CorridorTool(self.toolContext),
            'rectangular': RectangularTool(self.toolContext),
            'entire': EntireTool(self.toolContext)
        }

    @property
    def sketch(self):
        return self.sketchManager.currentSketch()

    @property
    def mode(self):
        """The drawing mode. It lives on the registry, not on the view."""
        return self.sketchManager.mode

    @property
    def tool(self):
        """The tool the current mode draws with."""
        return self.tools[self.mode]

    def toGeographicalPoint(self, point):
        """Widget position -> (longitude, latitude)."""
        pos = self.mapToScene(point)
        return self.toGeographicalCoordinates(pos.x(), pos.y())

    def toViewPoint(self, lonlat):
        """(longitude, latitude) -> widget position."""
        return self.mapFromScene(*self.toCanvasCoordinates(*lonlat))

    def extentToCanvasCoordinates(self, extent):
        minlon, minlat, maxlon, maxlat = extent
        minx, miny = self.toCanvasCoordinates(minlon, minlat)
        maxx, maxy = self.toCanvasCoordinates(maxlon, maxlat)
        return minx, miny, maxx, maxy

    def maxZoomFactor(self):
        extent = self.context.layer.maxExtent()
        if not extent:
            return 0

        minx, miny, maxx, maxy = self.extentToCanvasCoordinates(extent)
        rect = QRectF(0, 0, abs(maxx - minx), abs(maxy - miny))
        viewrect = self.viewport().rect()
        scenerect = self.transform().mapRect(rect)
        factor = max(viewrect.width() / scenerect.width(),
                             viewrect.height() / scenerect.height())

        return factor

    def zoomOut(self):
        # unlike the static view, how far you may zoom out is also limited by
        # how much of the layer extent is still on screen
        if self.maxZoomFactor() < 0.8 and self.currentZoom() > self.minZoom:
            self.scale(0.8, 0.8)

    def leaveEvent(self, event):
        self.mouseMoved.emit(())

    def isDrawing(self, event):
        """Whether this event belongs to a drawing gesture.

        Drawing is a live property of the event, not a latched flag. The old
        ``lock`` was set on Ctrl-press and cleared on Ctrl-release, so a double
        click during a gesture still zoomed the map, and losing focus while Ctrl
        was held left it stuck on for good.
        """
        return bool(event.modifiers() & Qt.ControlModifier)

    def handleDrawing(self, event, handler):
        """Hand a drawing event to the tool, and say that the user drew.

        Only user drawings pass through here, so the panel's ``circleChanged``
        reaches the typhoon form without echoing programmatic restores. 
        Mouse moves stay out: they only preview the rubber band.
        """
        handler(event)
        self.interacted.emit()

    def mousePressEvent(self, event):
        if self.isDrawing(event):
            self.handleDrawing(event, self.tool.mousePress)
            return

        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        # a double click during a drawing gesture is two clicks of that
        # gesture, not a request to zoom
        if self.isDrawing(event):
            return

        super().mouseDoubleClickEvent(event)

    def mouseMoveEvent(self, event):
        self.emitMouseMoved(event)

        if self.isDrawing(event):
            self.tool.mouseMove(event)
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.isDrawing(event):
            self.handleDrawing(event, self.tool.mouseRelease)
        elif self.rubberBand.isVisible():
            self.rubberBand.hide()
            self.sketchManager.currentSketch().clear()

        super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        if self.isDrawing(event):
            self.handleDrawing(event, self.tool.wheelEvent)
        else:
            super().wheelEvent(event)

        self.emitMouseMoved(event)

    def keyPressEvent(self, event):
        if self.isDrawing(event):
            self.handleDrawing(event, self.tool.keyPress)

    def keyReleaseEvent(self, event):
        if self.isDrawing(event):
            self.handleDrawing(event, self.tool.keyRelease)

    def setMode(self, mode):
        self.sketchManager.setMode(mode)

        if mode == 'entire':
            # The whole FIR is the area, so entering the mode *is* the
            # drawing. This used to be a fake ``mousePress(None)`` handed to
            # whichever tool happened to be current; now the view says what
            # it means, and the tools stay event translators.
            self.tool.restore()

    def setSketch(self, name):
        sketch = self.sketchManager.currentSketch()
        if sketch.name != name:
            self.sketchManager.next()

    def setMixedBackgroundOpacity(self, opacity):
        self.backgroundOpacity = opacity
        for bg in self.backgrounds:
            if bg.layer.overlay == 'mixed': 
                bg.setOpacity(opacity)

    def drawLayer(self):
        layers = [layer for layer in self.context.layer.currentLayers() if layer]
        if not layers:
            return

        items = []
        for layer in layers:
            opacity = self.backgroundOpacity if layer.overlay == 'mixed' else 1                
            background = BackgroundImage(layer, opacity)
            background.addTo(self, items)

        self.backgrounds = items
        self.backgroundLayer.replace(items)

    def clear(self):
        self.sketchManager.clear()

    def showEvent(self, event):
        extent = self.context.layer.maxExtent()
        if extent != self.maxLayerExtent:
            self.maxLayerExtent = extent
            self.redraw()


class LocationBanner(QWidget):

    def __init__(self, context, parent=None):
        super().__init__(parent)
        self.context = context
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setFixedSize(600, 200)

        self.location = QLabel(self)
        self.location.setWordWrap(True)
        self.location.setStyleSheet('QLabel { color: #fff; background-color: rgba(0, 0, 0, 0.35); border-radius: 3px; padding: 5px; }')

        font = fixedFont()
        font.setPointSize(10)
        self.location.setFont(font)

        self.verticalLayout = QVBoxLayout(self)
        self.verticalLayout.addItem(QSpacerItem(20, 0, QSizePolicy.Minimum, QSizePolicy.Expanding))
        self.verticalLayout.addWidget(self.location)

        self.hide()

    def setText(self, text):
        self.location.setText(text)
        if text:
            self.show()
        else:
            self.hide()


class LayerInfoOverlay(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setFixedSize(350, 80)

        self.verticalLayout = QVBoxLayout(self)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.addItem(QSpacerItem(20, 0, QSizePolicy.Minimum, QSizePolicy.Expanding))

    def setLabel(self, words):
        if not words:
            return

        for i in range(self.verticalLayout.count()):
            if i > 0:
                widget = self.verticalLayout.itemAt(i).widget()
                if widget:
                    widget.deleteLater()

        for text in words:
            label = OutlinedLabel(self)
            label.setText(text)
            self.verticalLayout.addWidget(label)


class PreviewPanel(QWidget):

    def __init__(self, parent=None, context=None):
        super().__init__(parent)
        self.context = context
        self.canvas = StaticView(self.context)
        self.verticalLayout = QVBoxLayout(self)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.addWidget(self.canvas)
        self.setMaximumSize(812, 300)

        self.geometries = []
        self.canvas.setExtent(self.extent())
        self.canvas.redraw()

    def extent(self):
        boundary = shapely.geometry.Polygon(self.context.layer.boundaries())
        bbox = boundary.envelope
        bbox = scale(bbox, xfact=4, yfact=2)
        return list(bbox.bounds)

    def setSigmet(self, geo):
        self.geometries = [geo]
        self.updateSigmetGraphic()

    def updateSigmetGraphic(self):
        self.canvas.drawSigmets(self.geometries)

    def clear(self):
        self.geometries = []
        self.updateSigmetGraphic()


class SketchPanel(QWidget):

    sketchChanged = pyqtSignal(list)
    circleChanged = pyqtSignal(dict)
    overlapChanged = pyqtSignal(str)
    modeChanged = pyqtSignal(str)

    def __init__(self, parent=None, context=None):
        super().__init__(parent)
        self.context = context
        self.designator = ''
        self.cachedSigmets = []

        self.canvas = SketchView(self.context)
        self.setMaximumSize(960, 620)
        self.canvasLayout = QVBoxLayout(self)
        self.canvasLayout.setContentsMargins(0, 8, 0, 0)
        self.canvasLayout.addWidget(self.canvas)

        self.zoomInButton = QPushButton(self)
        self.zoomInButton.setText('+')
        self.zoomOutButton = QPushButton(self)
        self.zoomOutButton.setText('-')

        # compact square zoom buttons inside the top-left overlay
        for button in (self.zoomInButton, self.zoomOutButton):
            button.setFixedSize(24, 24)

        self.zoomControl = QWidget(self)
        self.zoomControlLayout = QVBoxLayout(self.zoomControl)
        self.zoomControlLayout.setSpacing(0)
        self.zoomControlLayout.setContentsMargins(0, 0, 0, 0)
        self.zoomControlLayout.addWidget(self.zoomInButton)
        self.zoomControlLayout.addWidget(self.zoomOutButton)

        self.refreshButton = QPushButton(self)
        self.refreshButton.setText(QCoreApplication.translate('Editor', 'Refresh'))

        self.layerButton = QPushButton(self)
        self.layerButton.setText(QCoreApplication.translate('Editor', 'Layer'))

        self.overlapButton = QPushButton(self)
        self.overlapButton.setEnabled(False)
        self.overlapButton.setText(QCoreApplication.translate('Editor', 'Overlap'))
        self.overlapButton.setCheckable(True)

        self.modeButton = QPushButton(self)
        self.modeButton.setText(QCoreApplication.translate('Editor', 'Polygon'))

        for button in [self.refreshButton, self.layerButton, self.overlapButton]:
            button.setFixedHeight(24)

        self.toolbar = QWidget(self)
        self.toolbarLayout = QHBoxLayout(self.toolbar)
        self.toolbarLayout.setSpacing(0)
        self.toolbarLayout.setContentsMargins(0, 0, 0, 0)
        self.toolbarLayout.addWidget(self.refreshButton)
        self.toolbarLayout.addWidget(self.layerButton)
        self.toolbarLayout.addWidget(self.overlapButton)
        self.toolbarLayout.addWidget(self.modeButton)

        self.opacitySlider = QSlider(Qt.Horizontal, self)
        self.opacitySlider.setMinimum(0)
        self.opacitySlider.setMaximum(10)
        self.opacitySlider.setValue(5)
        self.opacitySlider.hide()

        self.positionLabel = OutlinedLabel(self)
        self.positionLabel.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.positionLabel.setMinimumWidth(200)
        self.positionLabel.setAlignment(Qt.AlignRight | Qt.AlignBottom)

        self.layerInfoOverlay = LayerInfoOverlay(self)
        self.locationBanner = LocationBanner(self.context, self)

        self.setLayerMenu()
        self.configureMode()
        self.load()
        self.bindSignal()

    def bindSignal(self):
        self.zoomOutButton.clicked.connect(self.canvas.zoomOut)
        self.zoomInButton.clicked.connect(self.canvas.zoomIn)
        self.modeButton.clicked.connect(self.nextMode)
        self.modeButton.clicked.connect(self.updateOverlapButton)
        self.overlapButton.toggled.connect(self.handleOverlap)
        self.refreshButton.clicked.connect(self.context.layer.refreshLayers)
        self.canvas.mouseMoved.connect(self.updatePositionLabel)
        self.canvas.interacted.connect(self.handleInteraction)
        for sketch in self.canvas.sketchManager:
            sketch.changed.connect(self.handleSketchChange)
            sketch.finished.connect(self.updateOverlapButton)

        self.sketchChanged.connect(self.updateLocationLabel)

        self.trimShapesAction.toggled.connect(lambda: self.changeSigmetDisplayMode(self.trimShapesAction, 'trimShapes'))
        self.showSigmetAction.toggled.connect(lambda: self.changeSigmetDisplayMode(self.showSigmetAction, 'showSigmet'))
        self.backgroundLayerActionGroup.triggered.connect(self.changeLayer)
        self.mixedBackgroundLayerActionGroup.triggered.connect(self.changeLayer)
        self.opacitySlider.valueChanged.connect(self.updateMixedBackgroundOpacity)
        self.context.event.layerChanged.connect(self.handleLayerChanged)

    def handleSketchChange(self):
        self.sketchChanged.emit(self.formattedCoordinates())

        # a sketch change can roll back ``done`` (e.g. removePoint cancels an
        # area), so recompute whether the overlap switch stays available;
        self.updateOverlapButton()

    def handleInteraction(self):
        """Mirror what the user drew here back into the form that owns it.

        Only the interactive path emits ``circleChanged``: the same circles
        reach this panel through ``setTyphoonGraphic`` when the typhoon form
        publishes an edit of its own, and echoing those straight back would
        close a signal loop between the map and the form.
        """
        if self.canvas.mode == 'circle':
            self.circleChanged.emit(self.circleCoordinates())

    def formattedCoordinates(self):
        messages = []
        for s in self.canvas.sketchManager.sketches:
            messages.append(formatLocation(s, self.context.layer.boundaries()))
        return messages

    def circleCoordinates(self):
        return geojson.featureCollection(
            [sketch.feature() for sketch in self.canvas.sketchManager.sketches])

    def location(self):
        """Area text keyed the way the message body reads it.

        The keys are the ``location`` / ``forecastLocation`` entries consumed
        by ``composeMessage(fir, locations)`` in ``tafor/core/sigmet/states.py``
        and are frozen by the message format, so they are written out as a
        mapping from key to area name. A sketch only contributes its key once
        it is done, so an unfinished area is absent rather than empty. The old
        ``names = ['location', 'forecastLocation']`` list said the same thing,
        but only by lining up with the order and the length of
        ``sketchManager.sketches`` -- a coupling that broke silently the
        moment either side gained a third entry.
        """
        manager = self.canvas.sketchManager
        boundaries = self.context.layer.boundaries()
        keys = {'location': 'initial', 'forecastLocation': 'final'}

        locations = {}
        for key, name in keys.items():
            sketch = manager.get(name)
            if sketch.done:
                locations[key] = formatLocation(sketch, boundaries)

        return locations

    def hasAcceptableGraphic(self):
        initial = self.canvas.sketchManager.first()
        final = self.canvas.sketchManager.last()

        boundaries = self.context.layer.boundaries()
        sketches = [initial.done and formatLocation(initial, boundaries)]
        if self.canvas.sketchManager.currentSketch() == final:
            sketches.append(final.done and formatLocation(final, boundaries))

        return all(sketches)

    def configureMode(self, designator='WS', mode='template'):
        if designator == 'WC':
            icons = [
                {'title': QCoreApplication.translate('Editor', 'Circle'), 'mode': 'circle'},
                {'title': QCoreApplication.translate('Editor', 'Polygon'), 'mode': 'polygon'}
            ]
        else:
            icons = [
                {'title': QCoreApplication.translate('Editor', 'Polygon'), 'mode': 'polygon'},
                {'title': QCoreApplication.translate('Editor', 'Line'), 'mode': 'line'},
                {'title': QCoreApplication.translate('Editor', 'Rectangular'), 'mode': 'rectangular'},
                {'title': QCoreApplication.translate('Editor', 'Corridor'), 'mode': 'corridor'},
                {'title': QCoreApplication.translate('Editor', 'Entire'), 'mode': 'entire'}
            ]

        self.designator = designator
        self.modes = cycle(icons)
        metrics = QFontMetrics(self.modeButton.font())
        width = max(metrics.horizontalAdvance(icon['title']) for icon in icons) + 20
        self.modeButton.setFixedSize(width, 24)
        self.nextMode()

        if mode == 'cancel':
            self.overlapButton.hide()
            self.modeButton.hide()
        else:
            self.overlapButton.show()
            self.modeButton.show()

    def updateOverlapButton(self):
        initial = self.canvas.sketchManager.first()
        enabled = initial.done
        if (self.designator == 'WC' and self.canvas.mode == 'polygon') or self.canvas.mode == 'entire':
            enabled = False
        self.overlapButton.setEnabled(enabled)
        
        if enabled:
            final = self.canvas.sketchManager.last()
            checked = bool(final)
            self.overlapButton.setChecked(checked)

    def nextMode(self):
        self.clear()
        mode = next(self.modes)
        self.canvas.setMode(mode['mode'])
        self.modeButton.setText(mode['title'])
        self.modeChanged.emit(mode['mode'])
        # ``SketchManager.clear`` empties the areas without notifying, so
        # republish the coordinates through the same signal sketch changes
        # flow through, which is what refreshes the location label
        self.sketchChanged.emit(self.formattedCoordinates())

    def handleOverlap(self, checked):
        if checked:
            self.canvas.setSketch('final')
            self.modeButton.setEnabled(False)
            self.overlapChanged.emit('final')
        else:
            self.canvas.setSketch('initial')
            self.modeButton.setEnabled(True)
            self.overlapChanged.emit('initial')

    def setSigmets(self, sigmets):
        self.cachedSigmets = sigmets
        self.updateSigmetGraphic()

    def handleLayerChanged(self):
        # pure notification: pull fresh data from the layer service,
        # keeping menu population before the canvas redraw
        self.setLayerSelectMenu()
        self.updateLayer()

    def setLayerMenu(self):
        self.layerMenu = QMenu(self)
        self.trimShapesAction = QAction(self)
        self.trimShapesAction.setText(QCoreApplication.translate('Editor', 'Trim Shapes'))
        self.trimShapesAction.setCheckable(True)
        self.trimShapesAction.setChecked(True)
        self.showSigmetAction = QAction(self)
        self.showSigmetAction.setText(QCoreApplication.translate('Editor', 'Latest SIGMET/AIRMET'))
        self.showSigmetAction.setCheckable(True)
        self.showSigmetAction.setChecked(True)
        self.backgroundLayerActionGroup = QActionGroup(self)
        self.mixedBackgroundLayerActionGroup = QActionGroup(self)
        self.mixedBackgroundLayerActionGroup.setExclusive(False)
        self.layerMenu.addAction(self.trimShapesAction)
        self.layerMenu.addAction(self.showSigmetAction)
        self.layerMenu.addSeparator()
        self.layerButton.setMenu(self.layerMenu)

        # The opacity slider reaches the menu through one reusable action:
        # building a fresh QWidgetAction per rebuild would hand the slider back
        # and forth between actions that are about to be discarded.
        self.opacitySliderAction = QWidgetAction(self)
        self.opacitySliderAction.setDefaultWidget(self.opacitySlider)
        # everything ``setLayerSelectMenu`` appends, so the next rebuild can
        # take it back out again
        self.layerItems = []

    def setLayerSelectMenu(self):
        layers = self.context.layer.groupLayers()
        if not layers:
            return

        # This runs again on every ``layerChanged``, so start from a clean slate.
        # Without it the menu was populated exactly once and then kept offering
        # layers that had since disappeared.
        for item in self.layerItems:
            self.layerMenu.removeAction(item)
        self.layerItems = []

        for actionGroup in (self.backgroundLayerActionGroup, self.mixedBackgroundLayerActionGroup):
            for action in actionGroup.actions():
                actionGroup.removeAction(action)

        for key, groups in layers.items():
            actionGroup = self.backgroundLayerActionGroup if key == 'standalone' else self.mixedBackgroundLayerActionGroup
            for layer in groups:
                action = QAction(layer.name, self)
                action.setCheckable(True)
                actionGroup.addAction(action)
                self.layerMenu.addAction(action)
                self.layerItems.append(action)

            self.layerItems.append(self.layerMenu.addSeparator())

        if 'mixed' in layers and layers['mixed']:
            self.opacitySlider.show()
            self.layerMenu.addAction(self.opacitySliderAction)
            self.layerItems.append(self.opacitySliderAction)
        else:
            self.opacitySlider.hide()

        # Either group may legitimately be empty, so take the first of whatever
        # actually survived. Subscripting both before the ``or`` raised
        # IndexError as soon as there were no standalone overlays.
        candidates = self.backgroundLayerActionGroup.actions() + self.mixedBackgroundLayerActionGroup.actions()
        if not candidates:
            return

        default = candidates[0]
        default.setChecked(True)
        self.context.layer.setState({'selected': [default.text()]})

    def changeSigmetDisplayMode(self, action, attr):
        checked = action.isChecked()
        self.context.layer.setState({attr: checked})
        self.updateSigmetGraphic()

    def changeLayer(self, action):
        stackable = self.context.layer.canStack(action.text())
        if stackable:
            selected = [action.text() for action in self.backgroundLayerActionGroup.actions() + self.mixedBackgroundLayerActionGroup.actions() if action.isChecked()]
            if selected != self.context.layer.selected:
                self.context.layer.setState({'selected': selected})
        else:
            action.setChecked(False)

    def updatePositionLabel(self, pos):
        if pos:
            lon, lat = pos
            text = '{}, {}'.format(degTodms(lat, pretty='lat'), degTodms(lon, pretty='lon'))
            self.positionLabel.setText(text)
        else:
            self.positionLabel.clear()

    def updateLayerInfoLabel(self):
        layers = self.context.layer.currentLayers()
        words = []
        for layer in layers:
            updated = layer.updatedTime()
            if updated:
                text = updated.strftime('%Y-%m-%d %H:%M')
            else:
                text = 'N/A'
            text = '{} - {}'.format(text, layer.name)
            words.append(text)

        self.layerInfoOverlay.setLabel(words)

    def updateLocationLabel(self, messages):
        # ``messages`` is built from the sketch list, so the headings are read
        # off that same list instead of being a second hand-written pair that
        # has to be kept in step with it.
        titles = [sketch.name.upper() for sketch in self.canvas.sketchManager.sketches]

        words = []
        for title, text in zip(titles, messages):
            if text:
                label = '<span style="color: lightgray">{}</span>'.format(title)
                words.append(label + '<br>' + text)

        html = '<br><br>'.join(words)
        self.locationBanner.setText(html)

    def setTyphoonGraphic(self, collections):
        """Apply the circles the typhoon form publishes.

        Nothing needs suppressing around this any more: the map only sends
        ``circleChanged`` for edits made on the map so the circles written
        here are not echoed back to the form they came from.
        """
        names = []
        for feature in collections['features']:
            name = feature['properties']['location']
            names.append(name)
            sketch = self.canvas.sketchManager.get(name)
            sketch.restore(
                center=feature['geometry']['coordinates'], radius=feature['properties']['radius'])

        for sketch in self.canvas.sketchManager:
            if sketch.name not in names:
                sketch.clear()

    def setAdvisoryGraphic(self, collections):
        self.overlapButton.setChecked(False)
        self.overlapButton.setEnabled(False)

        initial = self.canvas.sketchManager.first()
        final = self.canvas.sketchManager.last()

        def restore(sketch, feature):
            boundaries = self.context.layer.boundaries()
            if feature['geometry']['type'] == 'Polygon':
                sketch.restore(coordinates=feature['geometry']['coordinates'])
                sketch.clip(boundaries)
            if feature['geometry']['type'] == 'Point':
                sketch.restore(center=feature['geometry']['coordinates'],
                               radius=feature['properties']['radius'])

        locations = []
        for feature in collections['features']:
            type = feature['properties']['type']
            location = feature['properties']['location']
            locations.append(location)
            if type == 'sketch':
                if location == 'initial':
                    restore(initial, feature)
                if location == 'final':
                    if initial.done:
                        restore(final, feature)
                        if final.done:
                            self.overlapButton.setChecked(True)
                            self.overlapButton.setEnabled(True)
                feature['properties']['type'] = 'exterior'

        stickers = {'initial': [], 'final': []}
        for feature in collections['features']:
            location = feature['properties']['location']
            if location in stickers:
                stickers[location].append(feature['geometry'])

        for key, geometries in stickers.items():
            if geometries:
                sketch = initial if key == 'initial' else final
                sketch.stickers = geometries

        if 'initial' not in locations:
            initial.clear()
        if 'final' not in locations:
            final.clear()

        self.updateOverlapButton()

    def updateSigmetGraphic(self):
        if not self.context.layer.boundaries():
            return

        sigmets = []
        if self.context.layer.showSigmet:
            sigmets = self.cachedSigmets

        geometries = []
        for sig in sigmets:
            parser = sig.parser()

            try:
                geometry = parser.geo(self.context.layer.boundaries(), self.context.layer.trimShapes)
                geometries.append(geometry)
            except Exception as e:
                logger.error('Decode SIGMET graphic area error, {}, {}'.format(sig.text, e))

        self.canvas.drawSigmets(geometries)

    def updateMixedBackgroundOpacity(self, value):
        value = value / 10
        self.canvas.setMixedBackgroundOpacity(value)

    def updateLayer(self):
        # the FIR boundary belongs to the same rebuild as the backgrounds; it
        # used to be drawn once at load time and never revisited
        self.canvas.drawLayer()
        self.canvas.drawBoundaries()
        self.updateLayerInfoLabel()

    def updateCoastline(self):
        self.canvas.drawCoastline()

    def resizeEvent(self, event):
        # float the overlays over the corners, inset from the window edges;
        # raise them above the canvas so they receive mouse events.
        inset = 10
        self.zoomControl.adjustSize()
        self.toolbar.adjustSize()
        self.positionLabel.adjustSize()
        self.layerInfoOverlay.adjustSize()

        self.zoomControl.move(inset, inset + 8)
        self.toolbar.move(self.width() - self.toolbar.width() - inset, inset + 8)
        self.layerInfoOverlay.move(inset, self.height() - self.layerInfoOverlay.height() - inset)
        self.positionLabel.move(self.width() - self.positionLabel.width() - inset,
                                self.height() - self.positionLabel.height() - inset)

        # location banner centered, deliberately floated above the bottom edge
        self.locationBanner.move((self.width() - self.locationBanner.width()) // 2,
                                  self.height() - self.locationBanner.height() - 75)

        super().resizeEvent(event)

    def load(self):
        self.canvas.redraw()

    def clear(self):
        self.canvas.clear()
        self.overlapButton.setEnabled(False)
        self.overlapButton.setChecked(False)
