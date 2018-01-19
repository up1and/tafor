from tafor.utils.check import CheckTAF, Listen, remoteMessage, callService, callUp
from tafor.utils.validator import Validator, Grammar, Pattern, Parser


def checkUpgrade(releaseURL, currentVersion, callback=None):
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

    def versionDetect(data):
        releaseVersion = data['tag_name']
        current = versionNum(currentVersion)
        release = versionNum(releaseVersion)
        hasNewVersion = False

        if release['stable'] > current['stable']:
            hasNewVersion = True

        if release['stable'] == current['stable']:
            if release['beta'] is None and current['beta']:
                hasNewVersion = True

            if release['beta'] > current['beta']:
                hasNewVersion = True

        if callback:
            callback(data, hasNewVersion)


    try:
        resp = requests.get(releaseURL, timeout=5)
        data = resp.json()
        versionDetect(data)
    except Exception as e:
        pass

# checkUpgrade('https://api.github.com/repos/up1and/tafor/releases/latest', __version__)