import os

from PyQt5.QtCore import QUrl
from PyQt5.QtMultimedia import QSoundEffect

from tafor import root


class Sound(object):

    def __init__(self, filename, volume):
        super(Sound, self).__init__()
        file = os.path.join(root, 'sounds', filename)
        self.volume = volume or 0
        self.effect = QSoundEffect()
        self.effect.setSource(QUrl.fromLocalFile(file))

    def play(self, volume=None, loop=True):
        volume = self.volume if volume is None else volume
        self.effect.setVolume(int(volume)/100)

        if loop:
            self.effect.setLoopCount(QSoundEffect.Infinite)
        else:
            self.effect.setLoopCount(1)

        if not self.effect.isPlaying():
            self.effect.play()

    def stop(self):
        self.effect.stop()

    def setVolume(self, volume):
        self.volume = volume
        