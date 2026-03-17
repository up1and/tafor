import os
import sys
import platform
import datetime


class AppInfoService:
    def environment(self):
        from PyQt5.QtCore import QT_VERSION_STR
        from tafor import __version__
        return {
            'version': __version__,
            'python': platform.python_version(),
            'machine': platform.machine(),
            'qt': QT_VERSION_STR,
            'system': platform.system(),
            'release': platform.release(),
            'revision': self.ghash(),
        }

    def ghash(self):
        if hasattr(sys, '_MEIPASS'):
            from tafor._environ import ghash

            return ghash

        from tafor.utils import gitRevisionHash

        return gitRevisionHash()


class LicenseService:
    key = (
        '-----BEGIN PUBLIC KEY-----\n'
        'MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA2AZZfefXdgpvnWcV9xMf\n'
        'qlBqTS/8XZXq9BwFRpe0thoS3fER8s5fGKDWiOzO2I2PEwvahXyPny4hxHll7vF+\n'
        'lgd3dl0Z5BRslDGzSUe3/S2vqu4jAiyFmF3z8HZ9Jcr7BXi8yYUOr/LUfOP2gWK3\n'
        'GnORnWhBTb/llaGjN72yoJKJpKEbJYlrBJdsOyBrAeXbg1QNktOuqPf5toP/72qU\n'
        '2a/RRvpK9koSHMvhqd6ex5h+MHvcQZ759Fi1wxj5ChkB6BGgsHGR+7f49c92Gd4o\n'
        '2TKLicLL6vcidL4QkXdhRaZTJyd8pYI6Su+FUK7mcaBDpEaUl9xWupJnjsfKx1bf\n'
        'WQIDAQAB\n'
        '-----END PUBLIC KEY-----'
    )

    def __init__(self):
        self.exp = 0

    def license(self, token=None):
        from tafor import conf
        from tafor.utils import verifyToken

        token = token or conf.license
        if not token:
            return {}

        payload = verifyToken(token, self.key)
        if payload is None:
            return {}

        if 'exp' in payload:
            exp = datetime.datetime.fromtimestamp(payload['exp'])
            now = datetime.datetime.utcnow()
            self.exp = (exp - now).days

        data = {}
        for key, info in self.register().items():
            if key in payload and info == payload[key]:
                data[key] = info

        return data

    def register(self):
        from tafor import conf

        infos = {}
        if conf.airport:
            infos['airport'] = conf.airport
        if conf.firName:
            infos['fir'] = conf.firName[:4]
        return infos

    def hasPermission(self, reportType):
        if reportType == 'Trend':
            return True
        if reportType in ['TAF', 'Custom']:
            return 'airport' in self.license()
        if reportType in ['SIGMET', 'AIRMET']:
            return 'fir' in self.license()
        return False


class ResourceService:
    def bundlePath(self, relativePath):
        from tafor import root

        if hasattr(sys, '_MEIPASS'):
            base = sys._MEIPASS
        else:
            base = root
        return os.path.join(base, relativePath)

    def fixedFont(self):
        from PyQt5.QtGui import QFontDatabase

        return QFontDatabase.systemFont(QFontDatabase.FixedFont)

class SerialLock:
    def __init__(self):
        self._locked = False

    @property
    def isBusy(self):
        return self._locked

    def lock(self):
        self._locked = True

    def release(self):
        self._locked = False
