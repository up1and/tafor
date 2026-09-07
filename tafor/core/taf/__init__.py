from tafor.core.taf.spec import CurrentTaf, SpecFC, SpecFT24, SpecFT30
from tafor.core.taf.states import GroupState, PrimaryState, SegmentState, TemperatureState, TrendState
from tafor.core.taf.validator import TafValidator, TrendValidator, parseTemperature
from tafor.core.taf.compose import (
    completeGroupPeriod,
    composeHeading,
    formatValidityEnd,
    groupSpan,
    isGroupStartAcceptable,
    normalizeTemperatureTime,
    segmentOrderKey,
)
