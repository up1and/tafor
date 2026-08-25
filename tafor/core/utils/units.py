from enum import Enum


class UnitSystem(Enum):
    """Measurement system resolved from conf.unit, mapping each quantity
    to the unit string used when composing reports."""

    METRIC = 'metric'
    IMPERIAL = 'imperial'

    @classmethod
    def fromConfig(cls, value):
        try:
            return cls(value)
        except ValueError:
            return cls.METRIC

    @property
    def tafSpeed(self):
        """Speed unit in TAF messages: KT or MPS"""
        return 'KT' if self is UnitSystem.IMPERIAL else 'MPS'

    @property
    def sigmetSpeed(self):
        """Speed unit in SIGMET messages: KT or KMH"""
        return 'KT' if self is UnitSystem.IMPERIAL else 'KMH'

    @property
    def length(self):
        """Distance unit in SIGMET messages: NM or KM"""
        return 'NM' if self is UnitSystem.IMPERIAL else 'KM'


KM_PER_NM = 1.852   # 1 nautical mile = 1.852 km; 1 knot = 1.852 km/h


def toKmh(value, unit):
    """Convert a numeric speed from 'KT' or 'KMH' to km/h."""
    if unit == 'KT':
        return value * KM_PER_NM
    return value


def toKt(value, unit):
    """Convert a numeric speed from 'KMH' or 'KT' to knots."""
    if unit == 'KMH':
        return value / KM_PER_NM
    return value


def toKm(value, unit):
    """Convert a numeric distance from 'NM' or 'KM' to kilometres."""
    if unit == 'NM':
        return value * KM_PER_NM
    return value
