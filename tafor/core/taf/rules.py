from tafor.core.taf.compose import completeGroupPeriod, formatValidityEnd, isGroupStartAcceptable


def separatePeriod(text, previous):
    """Append the '/' separator after the four-digit day while typing.

    ``previous`` is the text from the last keystroke; the caller keeps that
    snapshot on its own instance.
    """
    if len(text) > len(previous) and len(text) == 4:
        return text + '/'
    return text


def normalizePeriod(text, previous, window):
    """Spell the typed period the one way the field accepts.

    Two respellings, both of the same instant: the separator after a
    four-digit day, and an end at midnight 00 written as 24 of the day
    before, the spelling that fits the validity window. Completion is not
    here: that adds what the operator has not typed, not how it is written.

    ``window`` is the (start, end) the text spells, as read from the state,
    or None when the field cannot read it yet.
    """
    text = separatePeriod(text, previous)

    if window is not None:
        start, end = window
        if end.hour == 0 and not text.endswith('24'):
            return '{:02d}{:02d}/{}'.format(start.day, start.hour, formatValidityEnd(end))

    return text


def groupPeriodRules(
    text,
    previous,
    *,
    window=None,
    primaryDurations=None,
    indicator='',
    spec=None,
    autoComplete=False,
    parseWindow=None,
):
    """Derive the formatted period text for a BECMG/TEMPO change group."""
    if autoComplete:
        if primaryDurations is None:
            return text

        refused = (
            len(text) == len(previous) == 4
            and (
                not isGroupStartAcceptable(previous, primaryDurations)
                or (
                    indicator in ('TEMPO', 'BECMG')
                    and completeGroupPeriod(previous, primaryDurations, indicator, spec) is None
                )
            )
        )
        growing = len(text) > len(previous) or refused
        if growing and len(text) == 4:
            if not isGroupStartAcceptable(text, primaryDurations):
                return text

            if indicator in ('TEMPO', 'BECMG'):
                completed = completeGroupPeriod(text, primaryDurations, indicator, spec)
                if completed is None:
                    return text

                text = completed
                window = parseWindow(text) if parseWindow else window

        return normalizePeriod(text, text, window)

    return normalizePeriod(text, previous, window)


def formatTrendPeriod(text, *, atChecked=False, fmChecked=False, tlChecked=False):
    """Normalize midnight spellings between 0000 and 2400 according to trend prefix."""
    if (atChecked or (fmChecked and not tlChecked)) and text == '2400':
        return '0000'
    if tlChecked and not fmChecked and text == '0000':
        return '2400'
    return text


def segmentRules(raw, previous, changed, source):
    """Apply cross-field derivation rules for a standard TAF/Trend segment."""
    if raw.get('isCavok') and raw.get('isNsc'):
        if not previous.get('isCavok'):
            raw['isNsc'] = False
        else:
            raw['isCavok'] = False

    if raw.get('isCavok'):
        for key in ('vis', 'weather', 'weatherWithIntensity', 'cloud1', 'cloud2', 'cloud3', 'cb'):
            raw[key] = ''
    elif raw.get('isNsc'):
        for key in ('cloud1', 'cloud2', 'cloud3', 'cb'):
            raw[key] = ''

    if raw.get('wind', '') == '00000':
        raw['gust'] = ''

    if (raw.get('weather') or '').upper() == 'NSW':
        raw['weatherWithIntensity'] = ''

    if (raw.get('cloud1') or '').upper().startswith('V'):
        for key in ('cloud2', 'cloud3', 'cb'):
            raw[key] = ''


def trendRules(raw, previous, changed, source):
    """Apply cross-field derivation rules for a METAR Trend forecast segment."""
    segmentRules(raw, previous, changed, source)

    if raw.get('indicator', 'BECMG') == 'TEMPO' and raw.get('atChecked'):
        raw['atChecked'] = False

    atChecked = bool(raw.get('atChecked'))
    fmChecked = bool(raw.get('fmChecked'))
    tlChecked = bool(raw.get('tlChecked'))

    atChanged = atChecked != bool(previous.get('atChecked'))
    fmChanged = fmChecked != bool(previous.get('fmChecked'))
    tlChanged = tlChecked != bool(previous.get('tlChecked'))

    if atChecked and (fmChecked or tlChecked):
        if atChanged:
            fmChecked = False
            tlChecked = False
            raw['fmChecked'] = False
            raw['tlChecked'] = False
        else:
            atChecked = False
            raw['atChecked'] = False

    if atChanged or fmChanged or tlChanged or not (atChecked or fmChecked or tlChecked):
        raw['period'] = ''

    if source == 'user' and 'period' in changed and fmChecked and tlChecked:
        raw['period'] = separatePeriod(raw.get('period', ''), previous.get('period', ''))
