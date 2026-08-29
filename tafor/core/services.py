import datetime

from tafor.core.utils.common import verifyToken


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

    def __init__(self, conf):
        self.conf = conf
        self.exp = 0

    def license(self, token=None):
        token = token or self.conf.license
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
        infos = {}
        if self.conf.airport:
            infos['airport'] = self.conf.airport
        if self.conf.firName:
            infos['fir'] = self.conf.firName[:4]
        return infos

    def hasPermission(self, reportType):
        if reportType == 'trend':
            return True
        if reportType in ['taf', 'custom']:
            return 'airport' in self.license()
        if reportType in ['sigmet', 'airmet']:
            return 'fir' in self.license()
        return False


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