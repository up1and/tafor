import logging

logger = logging.getLogger(__name__)


def boolean(value):
    return value if isinstance(value, bool) else value == 'true'

def ipAddress():
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    
    return ip

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

def verifyToken(token, key):
    import jwt
    try:
        data = jwt.decode(token, key, algorithms='RS256')
        return data
    except Exception as e:
        logger.error('Failed to verify token, {}'.format(e))
