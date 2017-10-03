import os

from PyQt5.QtCore import QUrl
from PyQt5.QtMultimedia import QSoundEffect

from tafor import BASEDIR


class Sound(object):
    """docstring for ClassName"""
    def __init__(self, filename, volume):
        super(Sound, self).__init__()
        file = os.path.join(BASEDIR, 'sounds', filename)
        self.volume = volume or 0
        self.effect = QSoundEffect()
        self.effect.setSource(QUrl.fromLocalFile(file))

    def play(self, volume=None, loop=True):
        volume = self.volume if volume is None else volume
        self.effect.setLoopCount(0)
        self.effect.setVolume(int(volume)/100)

        if loop:
            self.effect.setLoopCount(QSoundEffect.Infinite)
        else:
            self.effect.setLoopCount(1)
        
        if not self.effect.isPlaying():
            self.effect.play()

    def stop(self):
        self.effect.stop()
        