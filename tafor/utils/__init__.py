from tafor.utils.check import CheckTAF, Listen
from tafor.utils.validator import Validator, Grammar, Pattern, Parser


def checkVersion(releaseVersion, currentVersion):
    def versionNum(version):
        version = version.replace('v', '')
        if 'beta' in version:
            version, betaNum = version.split('-beta')
        else:
            betaNum = None

        nums = version.split('.')
        stableNum = 0
        multiple = 100

        for n in nums:
            stableNum += int(n) * multiple
            multiple = multiple / 10

        return {
            'stable': stableNum,
            'beta':  betaNum
        }

    current = versionNum(currentVersion)
    release = versionNum(releaseVersion)
    hasNewVersion = False

    if release['stable'] > current['stable']:
        hasNewVersion = True

    if release['stable'] == current['stable']:
        if release['beta'] is None and current['beta']:
            hasNewVersion = True

        if release['beta'] and current['beta'] and release['beta'] > current['beta']:
            hasNewVersion = True

    return hasNewVersion


def formatTimeInterval(interval, time=None):
    import datetime
    time = time if time else datetime.datetime.utcnow()
    startHour = int(interval[:2])
    endHour = 0 if interval[2:] in ['24', ''] else int(interval[2:])

    base = datetime.datetime(time.year, time.month, time.day)
    delta = datetime.timedelta(hours=endHour) if startHour < endHour else datetime.timedelta(days=1, hours=endHour)
    start = base + datetime.timedelta(hours=startHour)
    end = base + delta

    return start, end
