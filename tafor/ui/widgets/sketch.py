from tafor.core.geometry.sketch import (
    CircleSketch, CorridorSketch, EntireSketch, LineSketch, PolygonSketch,
    RectangularSketch, Sketch, mergeGeometries
)
from tafor.ui.widgets.geometry import SketchGraphic, StickerGraphic


class SketchManager:

    sketchTypes = {
        'polygon': PolygonSketch,
        'line': LineSketch,
        'circle': CircleSketch,
        'corridor': CorridorSketch,
        'rectangular': RectangularSketch,
        'entire': EntireSketch,
    }

    def __init__(self, canvas, sketchNames=None):
        super().__init__()
        self.mode = 'polygon'
        self.canvas = canvas
        self.graphics = []
        self.sketchNames = sketchNames if sketchNames else []
        self.index = 0

        self.sketchCache = {}
        for mode, cls in self.sketchTypes.items():
            sketches = [cls(name) for name in self.sketchNames]
            for sketch in sketches:
                sketch.changed.connect(self.update)
            self.sketchCache[mode] = sketches

    @property
    def sketches(self):
        return self.sketchCache[self.mode]

    def __iter__(self):
        for sketches in self.sketchCache.values():
            for sketch in sketches:
                yield sketch

    def get(self, name):
        for sketch in self.sketches:
            if name == sketch.name:
                return sketch

    def currentSketch(self):
        return self.sketches[self.index]

    def next(self):
        self.index += 1
        if self.index >= len(self.sketches):
            self.index = 0
            self.last().clear()

    def first(self):
        return self.sketches[0]

    def last(self):
        return self.sketches[1]

    def clear(self):
        for s in self.sketches:
            s.empty()
        self.index = 0

    def setMode(self, mode):
        self.clear()
        self.mode = mode
        self.update()

    def update(self):
        if self.graphics:
            self.graphics = []
            self.canvas.scene.removeItem(self.graphicsGroup)

        sketchGeometries = []
        stickerGeometries = []
        for sketch in self.sketches:
            collections = sketch.geometry()
            sketchGeometries += collections['geometries']
            stickerGeometries += sketch.stickers

        sketchCollections = mergeGeometries(sketchGeometries)
        stickerCollections = mergeGeometries(stickerGeometries)

        graphic = SketchGraphic()
        graphic.updateGeometry(sketchCollections, self.canvas)
        self.graphics.append(graphic)

        sticker = StickerGraphic()
        sticker.updateGeometry(stickerCollections, self.canvas)
        self.graphics.append(sticker)

        self.graphicsGroup = self.canvas.scene.createItemGroup(self.graphics)
        self.graphicsGroup.setZValue(3)
