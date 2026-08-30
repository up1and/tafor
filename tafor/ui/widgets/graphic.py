import os
import math
import logging

import shapefile
import shapely.geometry

from itertools import cycle

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGraphicsView, QGraphicsScene, QRubberBand,
    QStyleOptionGraphicsItem, QPushButton, QToolButton, QLabel, QMenu, QActionGroup, QAction, QWidgetAction, QSlider, QSpacerItem, QSizePolicy)
from PyQt5.QtGui import QIcon, QPainter
from PyQt5.QtCore import QCoreApplication, Qt, QRect, QRectF, QSize, pyqtSignal

from tafor.core.geometry.coordinate import degTodms
from tafor.core.utils.common import iconPath, resourcePath
from tafor.ui.fonts import fixedFont
from tafor.ui.widgets.sketch import SketchManager
from tafor.ui.widgets.geometry import BackgroundImage, Coastline, Fir, Sigmet
from tafor.ui.widgets.misc import OutlinedLabel

logger = logging.getLogger('tafor.sigmet.graphic')


class SketchTool:

    def __init__(self, canvas, manager):
        self.canvas = canvas
        self.manager = manager

    @property
    def sketch(self):
        return self.manager.currentSketch()

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

    def toLonLat(self, point):
        pos = self.canvas.mapToScene(point)
        return self.canvas.toGeographicalCoordinates(pos.x(), pos.y())


class PolygonTool(SketchTool):

    def mousePress(self, event):
        if event.button() == Qt.LeftButton:
            if len(self.sketch.coordinates) > 2:
                deviation = 12
                canvasPoint = self.canvas.toCanvasCoordinates(*self.sketch.coordinates[0])
                initPoint = self.canvas.mapFromScene(*canvasPoint)
                dx = abs(event.pos().x() - initPoint.x())
                dy = abs(event.pos().y() - initPoint.y())
                if dx < deviation and dy < deviation:
                    self.sketch.clip(self.canvas.context.layer.boundaries())
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
        self.sketch.clip(self.canvas.context.layer.boundaries())
        self.sketch.resize(ratio)


class RectangularTool(SketchTool):

    def __init__(self, canvas, manager):
        super().__init__(canvas, manager)
        self.origin = None

    def mousePress(self, event):
        if event.button() == Qt.LeftButton:
            self.origin = event.pos()
            if not self.sketch:
                self.canvas.rubberBand.setGeometry(QRect(self.origin, QSize()))
                self.canvas.rubberBand.show()
                self.sketch.addPoint(self.toLonLat(event.pos()))
        if event.button() == Qt.RightButton:
            self.sketch.removePoint()

    def mouseMove(self, event):
        if event.buttons() == Qt.LeftButton and self.origin:
            self.canvas.rubberBand.setGeometry(QRect(self.origin, event.pos()).normalized())

    def mouseRelease(self, event):
        if event.button() == Qt.LeftButton and self.origin:
            self.canvas.rubberBand.hide()
            self.sketch.addPoint(self.toLonLat(event.pos()))
            self.sketch.clip(self.canvas.context.layer.boundaries())
            self.origin = None


class EntireTool(SketchTool):

    def mousePress(self, event):
        boundaries = list(self.canvas.context.layer.boundaries())
        self.sketch.restore(boundaries=boundaries)


class BaseCanvas(QGraphicsView):

    def __init__(self, context):
        super().__init__()
        self.context = context
        self.extent = []

        self.coastlines = []
        self.firs = []
        self.sigmets = []

        self.projection = self.context.layer.projection()
        if self.projection.crs.is_geographic:
            self.ratio = 100
        else:
            self.ratio = 1 / 1000

        self.offset = (0, 0)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setTransformationAnchor(QGraphicsView.AnchorViewCenter)
        self.setRenderHint(QPainter.Antialiasing)
        self.setFocusPolicy(Qt.StrongFocus)

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

    def setExtent(self, extent):
        self.extent = extent

    def bbox(self):
        if self.extent:
            bound = shapely.geometry.box(*self.extent)
        else:
            bound = None

        return bound

    def drawCoastline(self):
        if self.coastlines:
            self.coastlines = []
            self.scene.removeItem(self.coastlinesGroup)

        filename = os.path.join(resourcePath('shapes'), 'coastline.shp')
        sf = shapefile.Reader(filename)
        shapes = sf.shapes()

        if not self.extent:
            self.setExtent(self.context.layer.maxExtent())

        bound = self.bbox()
        for polygons in shapes:
            polygons = shapely.geometry.shape(polygons)
            if bound:
                polygons = bound.intersection(polygons)

            if polygons.geom_type == 'MultiPolygon':
                polygons = polygons.geoms
            elif polygons.geom_type == 'Polygon':
                polygons = [polygons]

            for shape in polygons:
                if not shape.is_empty:
                    geometry = {
                        'type': 'Polygon',
                        'coordinates': shape.exterior.coords
                    }
                    p = Coastline(geometry)
                    p.addTo(self, self.coastlines)

        self.coastlinesGroup = self.scene.createItemGroup(self.coastlines)
        self.setSceneRect(self.scene.itemsBoundingRect())

    def drawBoundaries(self):
        geometry = {
            'type': 'Polygon',
            'coordinates': self.context.layer.boundaries()
        }
        p = Fir(geometry)
        p.addTo(self, self.firs)

        self.firsGroup = self.scene.createItemGroup(self.firs)
        self.firsGroup.setZValue(1)
        self.centerOn(self.firsGroup.boundingRect().center())

    def drawSigmets(self, geos):
        if self.sigmets:
            self.sigmets = []
            self.scene.removeItem(self.sigmetsGroup)
        
        for geo in geos:
            p = Sigmet(geo=geo)
            p.addTo(self, self.sigmets)
        
        self.sigmetsGroup = self.scene.createItemGroup(self.sigmets)
        self.sigmetsGroup.setZValue(2)

        if not self.context.layer.boundaries():
            self.centerOn(self.sigmetsGroup.boundingRect().center())

    def toGeographicalCoordinates(self, x, y):
        px, py = (x - self.offset[0]) / self.ratio, (self.offset[1] - y) / self.ratio
        return self.projection(px, py, inverse=True)
        
    def toCanvasCoordinates(self, longitude, latitude):
        px, py = self.projection(longitude, latitude)
        return px * self.ratio + self.offset[0], -py * self.ratio + self.offset[1]

    def redraw(self):
        self.drawCoastline()
        self.drawBoundaries()


class Viewer(BaseCanvas):

    def __init__(self, context):
        super().__init__(context)
        self.scale(0.4096, 0.4096)

    def mousePressEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.setDragMode(QGraphicsView.ScrollHandDrag)
            self.pos = event.pos()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            offset = self.pos - event.pos()
            self.pos = event.pos()
            x = self.horizontalScrollBar().value() + offset.x()
            y = self.verticalScrollBar().value() + offset.y()
            self.horizontalScrollBar().setValue(x)
            self.verticalScrollBar().setValue(y)

    def mouseReleaseEvent(self, event):
        self.setDragMode(QGraphicsView.NoDrag)

    def mouseDoubleClickEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.zoomIn()

    def zoomIn(self):
        zoom = QStyleOptionGraphicsItem.levelOfDetailFromTransform(self.transform())
        if zoom < 1:
            self.scale(1.25, 1.25)

    def zoomOut(self):
        zoom = QStyleOptionGraphicsItem.levelOfDetailFromTransform(self.transform())
        if zoom > 0.4:
            self.scale(0.8, 0.8)

    def wheelEvent(self, event):
        if event.angleDelta().y() > 0:
            self.zoomIn()
        else:
            self.zoomOut()


class Canvas(BaseCanvas):

    mouseMoved = pyqtSignal(tuple)

    def __init__(self, context):
        super().__init__(context)
        self.backgrounds = []

        self.mode = 'polygon'
        self.lock = False
        self.maxPoint = 7

        self.backgroundOpacity = 0.5
        self.maxLayerExtent = self.context.layer.maxExtent()

        self.setMouseTracking(True)

        self.rubberBand = QRubberBand(QRubberBand.Rectangle, self)
        self.sketchManager = SketchManager(self, sketchNames=['initial', 'final'])
        self.tools = {
            'polygon': PolygonTool(self, self.sketchManager),
            'line': LineTool(self, self.sketchManager),
            'circle': CircleTool(self, self.sketchManager),
            'corridor': CorridorTool(self, self.sketchManager),
            'rectangular': RectangularTool(self, self.sketchManager),
            'entire': EntireTool(self, self.sketchManager)
        }

    @property
    def sketch(self):
        return self.sketchManager.currentSketch()

    def currentTool(self):
        return self.tools.get(self.mode)

    def extentBound(self, extent):
        minlon, minlat, maxlon, maxlat = extent
        minx, miny = self.toCanvasCoordinates(minlon, minlat)
        maxx, maxy = self.toCanvasCoordinates(maxlon, maxlat)
        return minx, miny, maxx, maxy

    def maxZoomFactor(self):
        extent = self.context.layer.maxExtent()
        if not extent:
            return 0

        minx, miny, maxx, maxy = self.extentBound(extent)
        rect = QRectF(0, 0, abs(maxx - minx), abs(maxy - miny))
        viewrect = self.viewport().rect()
        scenerect = self.transform().mapRect(rect)
        factor = max(viewrect.width() / scenerect.width(),
                             viewrect.height() / scenerect.height())

        return factor

    def zoomIn(self):
        zoom = QStyleOptionGraphicsItem.levelOfDetailFromTransform(self.transform())
        if zoom < 5:
            self.scale(1.25, 1.25)

    def zoomOut(self):
        zoom = QStyleOptionGraphicsItem.levelOfDetailFromTransform(self.transform())
        factor = self.maxZoomFactor()

        if factor < 0.8 and zoom > 0.15:
            self.scale(0.8, 0.8)

    def leaveEvent(self, event):
        self.mouseMoved.emit(())

    def mouseDoubleClickEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.zoomIn()

    def mousePressEvent(self, event):
        if not self.lock and event.buttons() == Qt.LeftButton:
            self.setDragMode(QGraphicsView.ScrollHandDrag)
            self.pos = event.pos()

        if self.lock and self.currentTool():
            self.currentTool().mousePress(event)

    def mouseMoveEvent(self, event):
        self.emitMouseMoved(event)

        if not self.lock and event.buttons() == Qt.LeftButton:
            offset = self.pos - event.pos()
            self.pos = event.pos()
            x = self.horizontalScrollBar().value() + offset.x()
            y = self.verticalScrollBar().value() + offset.y()
            self.horizontalScrollBar().setValue(x)
            self.verticalScrollBar().setValue(y)

        if self.lock and self.currentTool():
            self.currentTool().mouseMove(event)

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.setDragMode(QGraphicsView.NoDrag)

        if self.lock and self.currentTool():
            self.currentTool().mouseRelease(event)

        if not self.lock and self.rubberBand.isVisible():
            self.rubberBand.hide()
            self.sketchManager.currentSketch().clear()

        super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        if self.lock and self.currentTool():
            self.currentTool().wheelEvent(event)
        else:
            if event.angleDelta().y() > 0:
                self.zoomIn()
            else:
                self.zoomOut()

        self.emitMouseMoved(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Control:
            self.lock = True
        if self.lock and self.currentTool():
            self.currentTool().keyPress(event)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_Control:
            self.lock = False
        if self.lock and self.currentTool():
            self.currentTool().keyRelease(event)

    def emitMouseMoved(self, event):
        pos = self.mapToScene(event.pos())
        self.mouseMoved.emit(self.toGeographicalCoordinates(pos.x(), pos.y()))

    def groundResolution(self, latitude):
        resolution = math.cos(latitude * math.pi / 180) * 2 * math.pi * 6378137 / self.scene.width()
        return resolution

    def setMode(self, mode):
        self.mode = mode
        self.sketchManager.setMode(mode)

        if mode == 'entire' and self.currentTool():
            self.currentTool().mousePress(None)

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
        if layers:
            if self.backgrounds:
                self.backgrounds = []
                self.scene.removeItem(self.backgroundsGroup)

            for layer in layers:
                opacity = self.backgroundOpacity if layer.overlay == 'mixed' else 1                
                background = BackgroundImage(layer, opacity)
                background.addTo(self, self.backgrounds)

            self.backgroundsGroup = self.scene.createItemGroup(self.backgrounds)
            self.backgroundsGroup.setZValue(-1)

    def clear(self):
        self.sketchManager.clear()

    def showEvent(self, event):
        extent = self.context.layer.maxExtent()
        if extent != self.maxLayerExtent:
            self.maxLayerExtent = extent
            self.drawCoastline()


class LocationWidget(QWidget):

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


class LayerInfoWidget(QWidget):

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


class GraphicsViewer(QWidget):

    def __init__(self, parent=None, context=None):
        super().__init__(parent)
        self.context = context
        self.canvas = Viewer(self.context)
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
        bbox = shapely.affinity.scale(bbox, xfact=4, yfact=2)
        return list(bbox.bounds)

    def setSigmet(self, geo):
        self.geometries = [geo]
        self.updateSigmetGraphic()

    def updateSigmetGraphic(self):
        self.canvas.drawSigmets(self.geometries)

    def clear(self):
        self.geometries = []
        self.updateSigmetGraphic()


class GraphicsWindow(QWidget):

    sketchChanged = pyqtSignal(list)
    circleChanged = pyqtSignal(dict)
    overlapChanged = pyqtSignal(str)
    modeChanged = pyqtSignal(str)

    def __init__(self, parent=None, context=None):
        super().__init__(parent)
        self.context = context
        self.type = ''
        self.quietly = False
        self.canvas = Canvas(self.context)
        self.verticalLayout = QVBoxLayout(self)
        self.verticalLayout.setContentsMargins(0, 8, 0, 0)
        self.verticalLayout.addWidget(self.canvas)
        self.setMaximumSize(960, 620)

        self.cachedSigmets = []

        self.zoomInButton = QPushButton(self)
        self.zoomInButton.setText('+')
        self.zoomOutButton = QPushButton(self)
        self.zoomOutButton.setText('-')
        self.zoomLayout = QVBoxLayout()
        self.zoomLayout.addWidget(self.zoomInButton)
        self.zoomLayout.addWidget(self.zoomOutButton)
        self.zoomLayout.setGeometry(QRect(20, 20, 24, 48))

        self.refreshButton = QToolButton(self)
        self.refreshButton.setText('Refresh')
        self.refreshButton.setIcon(QIcon(iconPath('synchronize.png')))

        self.layerButton = QToolButton(self)
        self.layerButton.setText('Layer')
        self.layerButton.setPopupMode(QToolButton.InstantPopup)
        self.layerButton.setIcon(QIcon(iconPath('layers.png')))

        self.overlapButton = QToolButton(self)
        self.overlapButton.setEnabled(False)
        self.overlapButton.setText('Overlap')
        self.overlapButton.setCheckable(True)
        self.overlapButton.setIcon(QIcon(iconPath('overlap.png')))

        self.modeButton = QToolButton(self)
        self.modeButton.setText('Mode')

        for button in [self.refreshButton, self.layerButton, self.overlapButton, self.modeButton]:
            button.setFixedSize(26, 26)
            button.setAutoRaise(True)

        self.operationWidget = QWidget(self)
        self.operationWidget.setMinimumSize(140, 44)
        self.operationLayout = QHBoxLayout(self.operationWidget)
        self.operationLayout.setSpacing(0)
        self.operationLayout.addItem(QSpacerItem(0, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        self.operationLayout.addWidget(self.refreshButton)
        self.operationLayout.addWidget(self.layerButton)
        self.operationLayout.addWidget(self.overlapButton)
        self.operationLayout.addWidget(self.modeButton)

        self.opacitySlider = QSlider(Qt.Horizontal, self)
        self.opacitySlider.setMinimum(0)
        self.opacitySlider.setMaximum(10)
        self.opacitySlider.setValue(5)
        self.opacitySlider.hide()

        self.positionLabel = OutlinedLabel(self)
        self.positionLabel.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.positionLabel.setMinimumWidth(200)
        self.positionLabel.setAlignment(Qt.AlignRight | Qt.AlignBottom)

        self.layerInfoWidget = LayerInfoWidget(self)
        self.locationWidget = LocationWidget(self.context, self)

        self.setLayerMenu()
        self.setButton()
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
        for sketch in self.canvas.sketchManager:
            sketch.changed.connect(self.handleSketchChange)
            sketch.finished.connect(self.updateOverlapButton)

        self.sketchChanged.connect(self.updateLocationLabel)

        self.trimShapesAction.toggled.connect(lambda: self.changeSigmetDisplayMode(self.trimShapesAction, 'trimShapes'))
        self.showSigmetAction.toggled.connect(lambda: self.changeSigmetDisplayMode(self.showSigmetAction, 'showSigmet'))
        self.backgroundLayerActionGroup.triggered.connect(self.changeLayer)
        self.mixedBackgroundLayerActionGroup.triggered.connect(self.changeLayer)
        self.opacitySlider.valueChanged.connect(self.updateMixedBackgroundOpacity)
        self.context.event.layerChanged.connect(self.setLayerSelectMenu)
        self.context.event.layerChanged.connect(self.updateLayer)

    def handleSketchChange(self):
        self.sketchChanged.emit(self.formattedCoordinates())
        
        if not self.quietly and self.canvas.mode == 'circle':
            self.circleChanged.emit(self.circleCoordinates())

    def formattedCoordinates(self):
        messages = []
        for s in self.canvas.sketchManager.sketches:
            messages.append(s.text(self.context.layer.boundaries()))
        return messages

    def circleCoordinates(self):
        collections = {
            'type': 'FeatureCollection',
            'features': []
        }
        for sketch in self.canvas.sketchManager:
            collections['features'].append(sketch.feature())

        return collections

    def location(self):
        locations = {}
        names = ['location', 'forecastLocation']

        for i, sketch in enumerate(self.canvas.sketchManager.sketches):
            if sketch.done:
                locations[names[i]] = sketch.text(self.context.layer.boundaries())

        return locations

    def hasAcceptableGraphic(self):
        initial = self.canvas.sketchManager.first()
        final = self.canvas.sketchManager.last()

        boundaries = self.context.layer.boundaries()
        sketchs = [initial.done and initial.text(boundaries)]
        if self.canvas.sketchManager.currentSketch() == final:
            sketchs.append(final.done and final.text(boundaries))

        return all(sketchs)

    def setButton(self, tt='WS', category='template'):
        if tt == 'WC':
            icons = [
                {'icon': iconPath('circle.png'), 'mode': 'circle'},
                {'icon': iconPath('polygon.png'), 'mode': 'polygon'}
            ]
        else:
            icons = [
                {'icon': iconPath('polygon.png'), 'mode': 'polygon'},
                {'icon': iconPath('line.png'), 'mode': 'line'},
                {'icon': iconPath('rectangular.png'), 'mode': 'rectangular'},
                {'icon': iconPath('corridor.png'), 'mode': 'corridor'},
                {'icon': iconPath('filled-polygon.png'), 'mode': 'entire'}
            ]

        self.type = tt
        self.icons = cycle(icons)
        self.nextMode()

        if category == 'cancel':
            self.overlapButton.hide()
            self.modeButton.hide()
        else:
            self.overlapButton.show()
            self.modeButton.show()

    def updateOverlapButton(self):
        initial = self.canvas.sketchManager.first()
        enabled = initial.done
        if self.type == 'WC' and self.canvas.mode == 'polygon' or self.canvas.mode == 'entire':
            enabled = False
        self.overlapButton.setEnabled(enabled)
        
        if enabled:
            final = self.canvas.sketchManager.last()
            checked = bool(final)
            self.overlapButton.setChecked(checked)

    def nextMode(self):
        self.clear()
        mode = next(self.icons)
        self.canvas.setMode(mode['mode'])
        self.modeButton.setIcon(QIcon(mode['icon']))
        self.modeChanged.emit(mode['mode'])

    def handleOverlap(self, checked):
        if checked:
            self.canvas.setSketch('final')
            self.modeButton.setEnabled(False)
            self.overlapChanged.emit('final')
        else:
            self.canvas.setSketch('initial')
            self.modeButton.setEnabled(True)
            self.overlapChanged.emit('initial')

    def switchLock(self):
        self.canvas.lock = not self.canvas.lock

    def setCachedSigmet(self, sigmets):
        self.cachedSigmets = sigmets
        self.updateSigmetGraphic()

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
        self.layerButton.setStyleSheet('QToolButton::menu-indicator {image: none;}')

    def setLayerSelectMenu(self):
        layers = self.context.layer.groupLayers()
        if not layers or self.backgroundLayerActionGroup.actions() or self.mixedBackgroundLayerActionGroup.actions():
            return

        for key, groups in layers.items():
            actionGroup = self.backgroundLayerActionGroup if key == 'standalone' else self.mixedBackgroundLayerActionGroup
            for layer in groups:
                action = QAction(layer.name, self)
                action.setCheckable(True)
                actionGroup.addAction(action)
                self.layerMenu.addAction(action)

            self.layerMenu.addSeparator()

        if 'mixed' in layers and layers['mixed']:
            self.opacitySlider.show()
            slider = QWidgetAction(self)
            slider.setDefaultWidget(self.opacitySlider)
            self.layerMenu.addAction(Slider)

        default = self.backgroundLayerActionGroup.actions()[0] or self.mixedBackgroundLayerActionGroup.actions()[0]
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

        self.layerInfoWidget.setLabel(words)

    def updateLocationLabel(self, messages):
        titles = ['INITIAL', 'FINAL']
        words = []
        for i, text in enumerate(messages):
            label = '<span style="color: lightgray">{}</span>'.format(titles[i])
            if text:
                text = label + '<br>' + text
                words.append(text)

        html = '<br><br>'.join(words)
        self.locationWidget.setText(html)

    def setTyphoonGraphic(self, collections):
        # quietly update sketches while not sending back circle changed signal.
        self.quietly = True
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

        self.quietly = False

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

        geos = []
        for sig in sigmets:
            parser = sig.parser()

            try:
                geo = parser.geo(self.context.layer.boundaries(), self.context.layer.trimShapes)
                geos.append(geo)
            except Exception as e:
                logger.error('Decode SIGMET graphic area error, {}, {}'.format(sig.text, e))

        self.canvas.drawSigmets(geos)

    def updateMixedBackgroundOpacity(self, value):
        value = value / 10
        self.canvas.setMixedBackgroundOpacity(value)

    def updateLayer(self):
        self.canvas.drawLayer()
        self.updateLayerInfoLabel()

    def updateCoastline(self):
        self.canvas.drawCoastline()

    def resizeEvent(self, event):
        self.operationWidget.move(self.width() - self.operationWidget.width() - 4, 10)
        self.positionLabel.move(self.width() - self.positionLabel.width() - 18, self.height() - self.positionLabel.height() - 15)
        self.layerInfoWidget.move(18, self.height() - self.layerInfoWidget.height() - 15)
        self.locationWidget.move(int(self.width() / 2 - self.locationWidget.width() / 2), self.height() - self.locationWidget.height() - 75)
        super().resizeEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Control:
            self.canvas.lock = True

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_Control:
            self.canvas.lock = False

    def load(self):
        self.canvas.redraw()

    def clear(self):
        self.canvas.clear()
        self.overlapButton.setEnabled(False)
        self.overlapButton.setChecked(False)
