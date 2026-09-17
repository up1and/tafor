import datetime

from tafor.core.utils.time import isOverlap, parseDayHour, parseTime, utcnow

def parseTemperature(value):
    return -int(value[1:]) if 'M' in value else int(value)


def parseTemperatureTime(text, durations):
    """A temperature's day-hour as a datetime, or None if it does not parse.

    None is the answer for both callers, but they read it differently: for the
    temperature being checked an unparsable time is the error, for one of its
    siblings it just means "not in the comparison". That is the old behaviour
    kept as is -- the checked time failed the rule, a sibling's was skipped.
    """
    try:
        return parseDayHour(text[:2], text[2:], durations[0], delta='month')
    except (ValueError, IndexError):
        pass

class TafFormValidator:
    WEATHER_CONFLICT = 'weather_conflict'
    GUST_SPEED_INSUFFICIENT = 'gust_speed_insufficient'
    CLOUD_HEIGHT_CONFLICT = 'cloud_height_conflict'
    CLOUD_OKTAS_EXCEED = 'cloud_oktas_exceed'
    CLOUD_ABOVE_OVC = 'cloud_above_ovc'
    GROUP_PERIOD_EXCEED = 'group_period_exceed'
    GROUP_START_INVALID = 'group_start_invalid'
    GROUP_END_INVALID = 'group_end_invalid'
    GROUP_OVERLAP = 'group_overlap'
    FM_TIME_INVALID = 'fm_time_invalid'
    TEMP_TIME_INVALID = 'temp_time_invalid'
    TEMP_MAX_LESS_MIN = 'temp_max_less_min'
    TEMP_MIN_GREATER_MAX = 'temp_min_greater_max'

    @staticmethod
    def checkWeather(state):
        weather = state.weather
        weatherWithIntensity = state.weatherWithIntensity
        if not weather or not weatherWithIntensity:
            return None

        if 'TS' in weather and ('TS' in weatherWithIntensity or 'RA' in weatherWithIntensity):
            return TafFormValidator.WEATHER_CONFLICT

        return None

    @staticmethod
    def checkGust(state):
        wind = state.wind
        gust = state.gust
        if not wind or not gust or gust == 'P49':
            return None

        windSpeed = wind[-2:]
        if int(windSpeed) == 0 or int(gust) - int(windSpeed) < 5:
            return TafFormValidator.GUST_SPEED_INSUFFICIENT

        return None

    @staticmethod
    def checkCloud(state, lineValue):
        if not lineValue:
            return None

        clouds = [cloud for cloud in state.clouds if cloud]
        cb = next((cloud for cloud in clouds if cloud.endswith('CB')), '')

        # A CB layer is an independent phenomena layer and may share the
        # height of an ordinary layer; duplicate heights are only checked
        # between the ordinary cloud rows
        heights = [cloud[3:6] for cloud in clouds if not cloud.endswith('CB')]
        if len(heights) != len(set(heights)):
            return TafFormValidator.CLOUD_HEIGHT_CONFLICT

        cloudCover = {'FEW': 1, 'SCT': 3, 'BKN': 5, 'OVC': 8}
        if cb:
            cbCover = cloudCover.get(cb[:3], 0)
            cbHeight = cb[3:6]
            for cloud in clouds:
                if cloud == cb:
                    continue
                cover = cloudCover.get(cloud[:3], 0)
                if cbHeight == cloud[3:6] and cbCover + cover > 8:
                    return TafFormValidator.CLOUD_OKTAS_EXCEED

        orderedClouds = sorted(clouds, key=lambda cloud: int(cloud[3:6]) if cloud[3:6].isdigit() else 0)
        covers = [cloud[:3] for cloud in orderedClouds]
        if 'OVC' in covers:
            index = covers.index('OVC')
            if index + 1 < len(covers):
                return TafFormValidator.CLOUD_ABOVE_OVC

        return None

    @staticmethod
    def checkGroupPeriod(groupState, primaryState, span):
        if not groupState.period or not primaryState.period:
            return None

        # The indicator is the group's own, so no caller can hand in a flag that
        # disagrees with the state it is asking about. `span` stays an argument:
        # the UI also needs it for the wording of the error.
        isBecmg = groupState.indicator == 'BECMG'

        start, end = groupState.durations
        primaryStart, primaryEnd = primaryState.durations

        if end - start > datetime.timedelta(hours=span):
            return TafFormValidator.GROUP_PERIOD_EXCEED

        if start < primaryStart or primaryEnd < start:
            return TafFormValidator.GROUP_START_INVALID

        if end < primaryStart or primaryEnd < end or (isBecmg and end == primaryEnd):
            return TafFormValidator.GROUP_END_INVALID

        return None

    @staticmethod
    def checkGroupOverlap(groupState, siblings):
        if groupState.durations is None:
            return None

        for sibling in siblings:
            if sibling.durations and isOverlap(groupState.durations, sibling.durations):
                return TafFormValidator.GROUP_OVERLAP

        return None

    @staticmethod
    def checkFmPeriod(groupState, primaryState):
        if groupState.durations is None or primaryState.durations is None:
            return None

        start, _ = groupState.durations
        primaryStart, primaryEnd = primaryState.durations

        if start < primaryStart or primaryEnd <= start:
            return TafFormValidator.FM_TIME_INVALID

        return None

    @staticmethod
    def checkFmOverlap(groupState, siblings):
        if groupState.durations is None:
            return None

        time = groupState.durations[0]
        for sibling in siblings:
            if sibling.durations and sibling.durations[0] <= time <= sibling.durations[1]:
                return TafFormValidator.GROUP_OVERLAP

        return None

    @staticmethod
    def checkTemperatureTime(tempState, temperatures, durations):
        """One temperature's time: inside the validity period, and clear of the rest.

        Three rules, and the third is the one that is easy to miss:

        - inside `[durations[0], durations[1]]`
        - no two temperatures share an instant -- a TX and a TN never coincide
        - two temperatures of the *same* mode never share a day -- FT30 is
          TX TN TX, and its two TX have to fall on different days
        """
        if not tempState.time:
            return None

        if durations is None or durations[0] is None:
            return TafFormValidator.TEMP_TIME_INVALID

        time = parseTemperatureTime(tempState.time, durations)
        if time is None or not durations[0] <= time <= durations[1]:
            return TafFormValidator.TEMP_TIME_INVALID

        for other in temperatures:
            if other is tempState or not other.time:
                continue

            otherTime = parseTemperatureTime(other.time, durations)
            if otherTime is None:
                continue

            if otherTime == time:
                return TafFormValidator.TEMP_TIME_INVALID

            if other.mode == tempState.mode and otherTime.day == time.day:
                return TafFormValidator.TEMP_TIME_INVALID

        return None

    @staticmethod
    def checkTemperature(tempState, temperatures):
        """The value has to clear the others: a max above the lowest of them, a
        min below the highest.
        """
        if not tempState.value:
            return None

        others = [parseTemperature(t.value) for t in temperatures
                  if t is not tempState and t.value]
        if not others:
            return None

        temperature = parseTemperature(tempState.value)
        if tempState.mode == 'max':
            if temperature <= min(others):
                return TafFormValidator.TEMP_MAX_LESS_MIN
        elif tempState.mode == 'min':
            if max(others) <= temperature:
                return TafFormValidator.TEMP_MIN_GREATER_MAX

        return None


class TrendFormValidator:
    TREND_TIME_INVALID = 'trend_time_invalid'

    @staticmethod
    def checkPeriod(value, now=None):
        if not value:
            return None

        if now is None:
            now = utcnow()

        delta = datetime.timedelta(hours=2, minutes=30)
        periods = [parseTime(text, basetime=now) for text in value.split('/')]

        if len(periods) == 2:
            if periods[1] <= periods[0]:
                periods[1] = periods[1] + datetime.timedelta(days=1)

            if periods[1] - periods[0] > datetime.timedelta(hours=2):
                return TrendFormValidator.TREND_TIME_INVALID

        for time in periods:
            if (time - delta) > now:
                return TrendFormValidator.TREND_TIME_INVALID

        return None
