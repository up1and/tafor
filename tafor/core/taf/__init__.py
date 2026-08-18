import datetime

from tafor.core.taf.spec import CurrentTaf, SpecFC, SpecFT24, SpecFT30
from tafor.core.taf.states import GroupState, PrimaryState, SegmentState, TemperatureState, TrendState
from tafor.core.taf.validator import TafValidator, TrendValidator, parseTemperature


def normalizeTemperatureTime(time, primary):
    if time.hour != 0:
        return None

    if time == primary[1]:
        normalizedTime = time - datetime.timedelta(hours=1)
        return '{}24'.format(str(normalizedTime.day).zfill(2))

    return '{}{}'.format(str(time.day).zfill(2), str(time.hour).zfill(2))
