import os

from PyQt5.QtCore import QUrl
from PyQt5.QtMultimedia import QSoundEffect

from tafor import root, conf


class Sound(object):

    def __init__(self, filename, config=None):
        super(Sound, self).__init__()
        file = os.path.join(root, 'sounds', filename)
        self.config = config
        self.effect = QSoundEffect()
        self.effect.setSource(QUrl.fromLocalFile(file))

    def play(self, volume=None, loop=True):
        volume = volume if volume else self.volume()
        self.effect.setVolume(int(volume) / 100)

        if loop:
            self.effect.setLoopCount(QSoundEffect.Infinite)
        else:
            self.effect.setLoopCount(1)

        if not self.effect.isPlaying():
            self.effect.play()

    def stop(self):
        self.effect.stop()

    def volume(self):
        if self.config:
            volume = conf.value(self.config) or 100
        else:
            volume = 100

        return volume

