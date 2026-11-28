import re


def flightLevelFormats(phenomenon):
    """Return available flight level format options for ``phenomenon``."""
    if phenomenon in ('CB', 'TCU', 'TS', 'TSGR'):
        return ('', 'TOP', 'ABV', 'SFC', 'TOP ABV')
    return ('', 'ABV', 'BLW', 'SFC')


def flightLevelRules(raw, previous, changed, source):
    """Clear masked flight level inputs based on the selected format."""
    fmt = raw.get('flightLevelFormat', '')
    if fmt in ('TOP', 'TOP ABV', 'SFC', 'BLW'):
        raw['flightLevelBase'] = ''
    elif fmt == 'ABV':
        raw['flightLevelTop'] = ''


def movementRules(raw, previous, changed, source):
    """Clear movement speed when direction is stationary (STNR)."""
    if raw.get('direction', '') == 'STNR':
        raw['speed'] = ''


def observationRules(raw, previous, changed, source):
    """Synchronize observed/forecast time against validity beginning time."""
    if source == 'collect' or 'observedTime' in changed:
        return

    if 'comeFrom' not in changed and 'beginningTime' not in changed:
        return

    comeFrom = raw.get('comeFrom', '')
    beginSuffix = raw.get('beginningTime', '')[2:]
    if comeFrom == 'OBS':
        raw['observedTime'] = beginSuffix
        return

    prevSuffix = previous.get('beginningTime', '')[2:]
    if raw.get('observedTime', '') in (beginSuffix, prevSuffix):
        raw['observedTime'] = ''


def forecastRules(raw, previous, changed, source, *, hasDurations=True):
    """Synchronize forecast time against overlap mode and validity ending time."""
    if not raw.get('hasForecast'):
        raw['forecastTime'] = ''
        return

    if source == 'collect' or 'forecastTime' in changed:
        return

    if 'hasForecast' in changed or 'endingTime' in changed:
        ending = raw.get('endingTime', '')
        if hasDurations and ending:
            raw['forecastTime'] = ending[2:]


def generalRules(
    raw,
    previous,
    changed,
    source,
    *,
    phenomenaMap,
    defaultPhenomena,
    hasDurations=True,
):
    """Apply cross-field derivation rules for General/AIRMET SIGMET forms."""
    phenomena = phenomenaMap.get(raw.get('description', ''), defaultPhenomena)
    if raw.get('phenomenon', '') not in phenomena:
        raw['phenomenon'] = phenomena[0]

    formats = flightLevelFormats(raw.get('phenomenon', ''))
    phenomenonChanged = raw.get('phenomenon') != previous.get('phenomenon')
    if raw.get('flightLevelFormat', '') not in formats or (
        source == 'user'
        and ('phenomenon' in changed or phenomenonChanged)
        and 'flightLevelFormat' not in changed
    ):
        raw['flightLevelFormat'] = 'TOP' if raw.get('phenomenon', '') in ('CB', 'TCU', 'TS', 'TSGR') else ''

    flightLevelRules(raw, previous, changed, source)
    movementRules(raw, previous, changed, source)
    observationRules(raw, previous, changed, source)
    forecastRules(raw, previous, changed, source, hasDurations=hasDurations)


def ashRules(raw, previous, changed, source, *, hasDurations=True):
    """Apply cross-field derivation rules for Volcanic Ash SIGMET forms."""
    raw['isEruption'] = raw.get('phenomenon', 'ERUPTION') == 'ERUPTION'
    flightLevelRules(raw, previous, changed, source)
    movementRules(raw, previous, changed, source)
    observationRules(raw, previous, changed, source)
    forecastRules(raw, previous, changed, source, hasDurations=hasDurations)


def typhoonRules(raw, previous, changed, source, *, hasDurations=True, calcForecast=None):
    """Apply cross-field derivation rules for Tropical Cyclone SIGMET forms."""
    movementRules(raw, previous, changed, source)
    observationRules(raw, previous, changed, source)
    forecastRules(raw, previous, changed, source, hasDurations=hasDurations)

    triggerKeys = {
        'currentLatitude',
        'currentLongitude',
        'speed',
        'direction',
        'forecastTime',
        'beginningTime',
        'observedTime',
        'endingTime',
        'hasForecast',
    }
    if (
        source == 'user'
        and calcForecast is not None
        and not (changed & {'forecastLatitude', 'forecastLongitude'})
        and (changed & triggerKeys)
    ):
        positions = calcForecast()
        if positions:
            raw['forecastLatitude'], raw['forecastLongitude'] = positions
        else:
            raw['forecastLatitude'] = ''
            raw['forecastLongitude'] = ''


def filterCustomText(text):
    """Strip disallowed characters and uppercase free-form SIGMET text."""
    return re.sub(r'[^A-Za-z0-9)(\/\.\s,-]+', '', text).upper()


def customRules(raw, previous, changed, source):
    """Apply character filtering to custom SIGMET text."""
    raw['text'] = filterCustomText(raw.get('text', ''))


def cancelRules(raw, previous, changed, source, *, resolveValid, adjustBeginning):
    """Derive cancelled period and adjusted header validity times."""
    if source == 'collect':
        return

    if ('cancelIndex' in changed or 'cancelSequence' in changed) and not (
        'cancelBeginningTime' in changed or 'cancelEndingTime' in changed
    ):
        key = raw.get('cancelIndex')
        valid = resolveValid(key if key is not None else raw.get('cancelSequence', ''))
        if valid:
            begin, end = valid.split('/')
            raw['cancelBeginningTime'] = begin
            raw['cancelEndingTime'] = end
        else:
            raw['cancelBeginningTime'] = ''
            raw['cancelEndingTime'] = ''

    if changed & {'cancelIndex', 'cancelSequence', 'cancelBeginningTime', 'cancelEndingTime'}:
        cancelBegin = raw.get('cancelBeginningTime', '')
        cancelEnd = raw.get('cancelEndingTime', '')
        adjustBeginning(raw, cancelBegin, cancelEnd)
