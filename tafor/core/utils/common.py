import os
import sys
import logging
import platform

from logging.handlers import RotatingFileHandler

logger = logging.getLogger(__name__)


def setupLogging(debug=False, name='tafor'):
    logLevel = logging.DEBUG if debug else logging.INFO
    _format = '[%(asctime)s] %(levelname)s [%(name)s] %(message)s'
    formatter = logging.Formatter(_format)

    logger = logging.getLogger(name)
    if logger.handlers:
        return

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(formatter)

    fh = RotatingFileHandler('{}.log'.format(name), maxBytes=1024*1024, backupCount=5)
    fh.setLevel(logLevel)
    fh.setFormatter(formatter)

    logger.setLevel(logLevel)
    logger.addHandler(ch)
    logger.addHandler(fh)

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
        hash = subprocess.check_output(['git', 'describe', '--always'])
        hash = hash.decode('utf-8').rstrip()
    except Exception:
        hash = ''

    return hash

def verifyToken(token, key):
    import jwt
    try:
        data = jwt.decode(token, key, algorithms='RS256')
        return data
    except Exception as e:
        logger.error('Failed to verify token, {}'.format(e))

def appInfo(qt=''):
    from tafor import __version__

    return {
        'version': __version__,
        'python': platform.python_version(),
        'machine': platform.machine(),
        'qt': qt,
        'system': platform.system(),
        'release': platform.release(),
        'revision': revision(),
    }

def revision():
    if hasattr(sys, '_MEIPASS'):
        from tafor.revision import hash

        return hash

    return gitRevisionHash()

def bundlePath(relativePath):
    if hasattr(sys, '_MEIPASS'):
        base = sys._MEIPASS
    else:
        from tafor.core.globals import root

        base = root

    candidate = os.path.join(base, 'resources', relativePath)
    if os.path.exists(candidate):
        return candidate

    return os.path.join(base, relativePath)
