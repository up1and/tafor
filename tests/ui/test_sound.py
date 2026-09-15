"""Tests for tafor/ui/widgets/sound.py."""

import logging

import pytest

from PyQt5.QtMultimedia import QSoundEffect

from tafor.ui.widgets import sound as sound_module
from tafor.ui.widgets.sound import Sound, toQtVolume


class FakeEffect:
    """A QSoundEffect that records what it was asked to do.

    Nothing here touches an audio device, so the playback policy can be
    asserted without depending on a backend.
    """

    def __init__(self):
        self._source = None
        self.playing = False
        self.volumes = []
        self.loopCounts = []
        self.plays = 0
        self.stops = 0

    def setSource(self, url):
        self._source = url

    def source(self):
        return self._source

    def setVolume(self, volume):
        self.volumes.append(volume)

    def setLoopCount(self, count):
        self.loopCounts.append(count)

    def play(self):
        self.plays += 1
        self.playing = True

    def stop(self):
        self.stops += 1
        self.playing = False

    def isPlaying(self):
        return self.playing


class FakeEffectFactory:
    """Stands in for the QSoundEffect class.

    It keeps the loop count member Sound reaches for, so patching the class
    does not break the loop mode it sets.
    """

    Infinite = QSoundEffect.Infinite

    def __init__(self):
        self.built = []

    def __call__(self):
        effect = FakeEffect()
        self.built.append(effect)
        return effect


@pytest.fixture
def effects(monkeypatch):
    """Every Sound built in the test gets a recording effect instead."""
    factory = FakeEffectFactory()
    monkeypatch.setattr(sound_module, 'QSoundEffect', factory)
    return factory.built


class TestToQtVolume:

    @pytest.mark.parametrize('percent, expected', [
        (0, 0.0),
        (30, 0.3),
        (99, 0.99),
        (100, 1.0),
    ])
    def test_percent_is_mapped_to_the_qt_range(self, percent, expected):
        assert toQtVolume(percent) == pytest.approx(expected)

    @pytest.mark.parametrize('percent', [150, 101, 1000])
    def test_a_volume_above_the_range_is_clamped(self, percent):
        assert toQtVolume(percent) == pytest.approx(1.0)

    def test_a_legacy_volume_of_100_still_reads_as_full(self):
        """The domain is 0-99, but this is the unit conversion and not the
        domain check: a value left over from an older install is converted
        rather than shaved, so it keeps playing at full volume."""
        assert toQtVolume(100) == pytest.approx(1.0)

    @pytest.mark.parametrize('percent', [-1, -100])
    def test_a_volume_below_the_range_is_clamped(self, percent):
        assert toQtVolume(percent) == pytest.approx(0.0)

    def test_a_numeric_string_is_accepted(self):
        assert toQtVolume('30') == pytest.approx(0.3)

    def test_a_fraction_is_truncated(self):
        assert toQtVolume(0.5) == pytest.approx(0.0)

    @pytest.mark.parametrize('percent', ['abc', None, [30], {}])
    def test_an_unusable_volume_falls_back_to_full_and_is_logged(self, percent, caplog):
        with caplog.at_level(logging.WARNING, logger='tafor.sound'):
            assert toQtVolume(percent) == pytest.approx(1.0)

        assert 'Unusable volume' in caplog.text


class TestSound:

    def test_the_source_points_at_the_resource_file(self, effects):
        Sound('alarm.wav')

        assert effects[0].source().fileName() == 'alarm.wav'
        assert 'sounds' in effects[0].source().toLocalFile()

    def test_the_default_volume_is_full(self, effects):
        Sound('alarm.wav').play()

        assert effects[0].volumes == [1.0]

    def test_a_plain_number_is_used_as_the_volume(self, effects):
        Sound('alarm.wav', volume=25).play()

        assert effects[0].volumes == [0.25]

    def test_a_volume_source_is_read_on_every_play(self, effects):
        level = [30]
        sound = Sound('alarm.wav', volume=lambda: level[0])

        sound.play()
        level[0] = 80
        sound.stop()
        sound.play()

        assert effects[0].volumes == [0.3, 0.8]

    def test_a_volume_source_that_raises_does_not_reach_the_caller(self, effects, caplog):
        """A stored value of the wrong type makes the config read raise, and
        play() is reached from a Qt slot, where an escaping exception is worse
        than a wrong volume."""
        def broken():
            raise ValueError("invalid literal for int() with base 10: 'abc'")

        sound = Sound('alarm.wav', volume=broken)

        with caplog.at_level(logging.WARNING, logger='tafor.sound'):
            sound.play()

        assert effects[0].volumes == [1.0]
        assert 'Unusable volume for alarm.wav' in caplog.text

    def test_a_volume_source_that_returns_nonsense_falls_back_to_full(self, effects, caplog):
        sound = Sound('alarm.wav', volume=lambda: 'abc')

        with caplog.at_level(logging.WARNING, logger='tafor.sound'):
            sound.play()

        assert effects[0].volumes == [1.0]
        assert 'Unusable volume' in caplog.text

    def test_a_looping_channel_loops_forever(self, effects):
        Sound('alarm.wav').play()

        assert effects[0].loopCounts == [QSoundEffect.Infinite]

    def test_a_one_shot_channel_plays_once(self, effects):
        Sound('notification.wav', loop=False).play()

        assert effects[0].loopCounts == [1]

    def test_a_looping_channel_is_started_only_once(self, effects):
        sound = Sound('alarm.wav')

        sound.play()
        sound.play()
        sound.play()

        assert effects[0].plays == 1

    def test_a_looping_channel_starts_again_after_it_stopped(self, effects):
        sound = Sound('alarm.wav')

        sound.play()
        sound.stop()
        sound.play()

        assert effects[0].plays == 2

    def test_a_one_shot_channel_fires_every_time(self, effects):
        sound = Sound('notification.wav', loop=False)

        sound.play()
        sound.play()

        assert effects[0].plays == 2

    def test_stop_stops_the_effect(self, effects):
        sound = Sound('alarm.wav')
        sound.play()

        sound.stop()

        assert effects[0].isPlaying() is False

    def test_play_restarts_from_the_beginning(self, effects):
        """stop() comes before play(), so a retrigger does not depend on what
        the backend does with play() on an effect that is already running."""
        Sound('alarm.wav', loop=False).play()

        assert effects[0].stops == 1

    def test_preview_plays_at_the_given_volume(self, effects):
        Sound('alarm.wav', volume=30).preview(70)

        assert effects[0].volumes == [0.7]

    def test_preview_at_zero_is_silent(self, effects):
        """The regression: 0 used to be read as 'no volume given' and was
        replaced by the configured volume, so the slider could not audition
        mute."""
        Sound('alarm.wav', volume=30).preview(0)

        assert effects[0].volumes == [0.0]

    def test_preview_is_always_a_one_shot(self, effects):
        Sound('alarm.wav').preview(70)

        assert effects[0].loopCounts == [1]

    def test_preview_is_not_blocked_by_the_loop_guard(self, effects):
        sound = Sound('alarm.wav')

        sound.play()
        sound.preview(0)

        assert effects[0].plays == 2

    def test_play_goes_back_to_the_configured_volume(self, effects):
        sound = Sound('alarm.wav', volume=30)

        sound.preview(0)
        sound.stop()
        sound.play()

        assert effects[0].volumes == [0.0, 0.3]

    def test_play_leaves_a_running_channel_alone(self, effects):
        """A preview that is still playing is not cut short by the tick."""
        sound = Sound('alarm.wav', volume=30)

        sound.preview(70)
        sound.play()

        assert effects[0].volumes == [0.7]


if __name__ == '__main__':
    pytest.main([__file__])
