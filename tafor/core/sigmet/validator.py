import datetime


class SigmetValidator:
    START_TOO_FAR = 'start_too_far'
    END_NOT_GREATER = 'end_not_greater'
    PERIOD_TOO_LONG = 'period_too_long'
    FLIGHT_LEVEL_INVALID = 'flight_level_invalid'

    @staticmethod
    def validatePeriod(durations, span, now=None):
        if durations is None:
            return None

        if now is None:
            now = datetime.datetime.utcnow()

        start, end = durations

        if start - now > datetime.timedelta(hours=24):
            return SigmetValidator.START_TOO_FAR

        if end <= start:
            return SigmetValidator.END_NOT_GREATER

        if end - start > datetime.timedelta(hours=span):
            return (SigmetValidator.PERIOD_TOO_LONG, {'hours': span})

        return None

    @staticmethod
    def validateFlightLevel(base, top):
        if not (base and top):
            return None

        if int(top) <= int(base):
            return SigmetValidator.FLIGHT_LEVEL_INVALID

        return None
