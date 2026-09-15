import logging
import os

from PyQt5.QtCore import QUrl
from PyQt5.QtMultimedia import QSoundEffect

from tafor import root

logger = logging.getLogger('tafor.sound')


def toQtVolume(percent):
    """Convert a percentage to the 0.0-1.0 QSoundEffect wants.
    """
    try:
        percent = int(percent)
    except (TypeError, ValueError):
        logger.warning('Unusable volume %r, falling back to 100', percent)
        return 1.0

    return max(0, min(100, percent)) / 100


class Sound:
    """One sound channel: a file, a volume source and a playback mode.

    The mode is fixed at construction because it belongs to the channel and
    not to a single call, and the volume is read through a callable so this
    class never has to know which config key feeds it.
    """

    def __init__(self, filename, volume=100, loop=True):
        super().__init__()
        self.filename = filename
        self._volume = volume if callable(volume) else (lambda: volume)
        self.loop = loop
        self.effect = QSoundEffect()
        self.effect.setSource(QUrl.fromLocalFile(
            os.path.join(root, 'resources', 'sounds', filename)))

    def volume(self):
        """The channel's volume, in 0-100.

        Reading the config can raise when a stored value does not match its
        declared type. That must not take the channel down with it: play() is
        reached from Qt slots, and an exception escaping a slot is worse than
        a wrong volume.
        """
        try:
            return self._volume()
        except (TypeError, ValueError) as error:
            logger.warning('Unusable volume for %s: %s', self.filename, error)
            return 100

    def play(self):
        """Start the channel.

        A looping channel is idempotent: the sound presenter ticks once a
        second, and restarting an alarm on every tick would stop it from ever
        finishing a cycle. A one-shot channel fires every time instead, or a
        burst of messages inside one wav would be heard as a single beep.
        """
        if self.loop and self.effect.isPlaying():
            return

        self.effect.stop()
        self.start(self.volume(), self.loop)

    def preview(self, volume):
        """Audition once at an explicit volume, for the settings sliders."""
        self.start(volume, loop=False)

    def stop(self):
        self.effect.stop()

    def start(self, volume, loop):
        self.effect.setVolume(toQtVolume(volume))
        self.effect.setLoopCount(QSoundEffect.Infinite if loop else 1)
        self.effect.play()
