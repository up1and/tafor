import datetime

from tafor.core.utils.time import isOverlap, parseDayHour, parseTime

def parseTemperature(value):
    return -int(value[1:]) if 'M' in value else int(value)

class TafValidator:
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
            return TafValidator.WEATHER_CONFLICT

        return None

    @staticmethod
    def checkGust(state):
        wind = state.wind
        gust = state.gust
        if not wind or not gust or gust == 'P49':
            return None

        windSpeed = wind[-2:]
        if int(windSpeed) == 0 or int(gust) - int(windSpeed) < 5:
            return TafValidator.GUST_SPEED_INSUFFICIENT

        return None

    @staticmethod
    def checkCloud(state, lineValue):
        if not lineValue:
            return None

        height = lineValue[3:]
        allClouds = list(filter(None, state.clouds + ([state.cb] if state.cb else [])))
        otherClouds = [c for c in allClouds if c != lineValue]
        cloudHeights = [cloud[3:6] for cloud in otherClouds]

        if cloudHeights.count(height) > 0:
            return TafValidator.CLOUD_HEIGHT_CONFLICT

        cloudCover = {'FEW': 1, 'SCT': 3, 'BKN': 5, 'OVC': 8}
        if state.cb:
            cbCover = cloudCover.get(state.cb[:3], 0)
            cbHeight = state.cb[3:6]
            for cloud in otherClouds:
                cover = cloudCover.get(cloud[:3], 0)
                if cbHeight == cloud[3:6] and cbCover + cover > 8:
                    return TafValidator.CLOUD_OKTAS_EXCEED

        orderedClouds = sorted(allClouds, key=lambda cloud: int(cloud[3:6]) if cloud[3:6].isdigit() else 0)
        covers = [cloud[:3] for cloud in orderedClouds]
        if 'OVC' in covers:
            index = covers.index('OVC')
            if index + 1 < len(covers):
                return TafValidator.CLOUD_ABOVE_OVC

        return None

    @staticmethod
    def checkGroupPeriod(groupState, primaryState, span, isBecmg=False):
        if not groupState.period or not primaryState.period:
            return None

        start, end = groupState.durations
        primaryStart, primaryEnd = primaryState.durations

        if end - start > datetime.timedelta(hours=span):
            return TafValidator.GROUP_PERIOD_EXCEED

        if start < primaryStart or primaryEnd < start:
            return TafValidator.GROUP_START_INVALID

        if end < primaryStart or primaryEnd < end or (isBecmg and end == primaryEnd):
            return TafValidator.GROUP_END_INVALID

        return None

    @staticmethod
    def checkGroupOverlap(groupState, siblings):
        if groupState.durations is None:
            return None

        for sibling in siblings:
            if sibling.durations and isOverlap(groupState.durations, sibling.durations):
                return TafValidator.GROUP_OVERLAP

        return None

    @staticmethod
    def checkFmPeriod(groupState, primaryState):
        if groupState.durations is None or primaryState.durations is None:
            return None

        start, _ = groupState.durations
        primaryStart, primaryEnd = primaryState.durations

        if start < primaryStart or primaryEnd <= start:
            return TafValidator.FM_TIME_INVALID

        return None

    @staticmethod
    def checkFmOverlap(groupState, siblings):
        if groupState.durations is None:
            return None

        time = groupState.durations[0]
        for sibling in siblings:
            if sibling.durations and sibling.durations[0] <= time <= sibling.durations[1]:
                return TafValidator.GROUP_OVERLAP

        return None

    @staticmethod
    def checkTemperatureTime(tempState, primaryDurations, siblings=None, sameTypeSiblings=None):
        if not tempState.time:
            return None

        if primaryDurations is None:
            return TafValidator.TEMP_TIME_INVALID

        try:
            time = parseDayHour(tempState.time[:2], tempState.time[2:], primaryDurations[0], delta='month')
        except Exception:
            return TafValidator.TEMP_TIME_INVALID

        siblings = siblings or []
        sameTypeSiblings = sameTypeSiblings or []
        valid = primaryDurations[0] <= time <= primaryDurations[1] and time not in siblings

        for sibling in sameTypeSiblings:
            if sibling.day == time.day:
                valid = False

        if not valid:
            return TafValidator.TEMP_TIME_INVALID

        return None

    @staticmethod
    def checkTemperature(tempState, referenceValue):
        if not tempState.value:
            return None

        temperature = parseTemperature(tempState.value)
        if tempState.mode == 'max':
            if referenceValue is not None and temperature <= referenceValue:
                return TafValidator.TEMP_MAX_LESS_MIN
        elif tempState.mode == 'min':
            if referenceValue is not None and referenceValue <= temperature:
                return TafValidator.TEMP_MIN_GREATER_MAX

        return None


class TrendValidator:
    TREND_TIME_INVALID = 'trend_time_invalid'

    @staticmethod
    def checkPeriod(value, now=None):
        if not value:
            return None

        if now is None:
            now = datetime.datetime.utcnow()

        delta = datetime.timedelta(hours=2, minutes=30)
        periods = [parseTime(text) for text in value.split('/')]

        if len(periods) == 2:
            if periods[1] <= periods[0]:
                periods[1] = periods[1] + datetime.timedelta(days=1)

            if periods[1] - periods[0] > datetime.timedelta(hours=2):
                return TrendValidator.TREND_TIME_INVALID

        for time in periods:
            if (time - delta) > now:
                return TrendValidator.TREND_TIME_INVALID

        return None
