
def boolean(value):
    return value if isinstance(value, bool) else value == 'true'

def checkVersion(releaseVersion, currentVersion):
    def versionNum(version):
        if version.startswith('v'):
            version = version[1:]

        dev = None
        nums = version.split('.')

        if 'dev' in nums:
            dev = nums.pop()

        number = 0
        multiple = 100

        for n in nums:
            number += int(n) * multiple
            multiple = multiple / 10

        return {
            'version': number,
            'dev': dev
        }

    current = versionNum(currentVersion)
    release = versionNum(releaseVersion)
    hasNewVersion = False

    if release['version'] > current['version']:
        hasNewVersion = True

    if release['version'] == current['version']:
        if release['dev'] and current['dev'] is None:
            hasNewVersion = True

    return hasNewVersion

def gitRevisionHash():
    import subprocess

    try:
        ghash = subprocess.check_output(['git', 'describe', '--always'])
        ghash = ghash.decode('utf-8').rstrip()
    except Exception:
        ghash = ''

    return ghash
