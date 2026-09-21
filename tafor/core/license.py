"""License verification.

Licenses are Ed25519-signed tokens in JWT compact serialization:

    <base64url({"alg":"EdDSA","typ":"JWT"})>.<base64url(json payload)>.<base64url(64-byte signature)>

The payload is plaintext JSON -- signing proves integrity, not secrecy, so
never put secrets in it. Recognized claims: 'airport' (ICAO code), 'fir'
(ICAO code) and 'exp' (integer Unix timestamp).
"""
import json
import base64
import datetime
import logging

from ecdsa import Ed25519, VerifyingKey

from tafor.core.utils.time import utcnow

logger = logging.getLogger(__name__)


def b64decode(segment):
    return base64.urlsafe_b64decode(segment + '=' * (-len(segment) % 4))


def verifyToken(token, pubkey):
    """Return the payload of a license token whose Ed25519 signature
    verifies against the base64url-encoded public key, or None."""
    try:
        header, payload, signature = token.split('.')

        # The header is checked against the one algorithm this verifier
        # supports; it never selects one
        params = json.loads(b64decode(header))
        if not isinstance(params, dict) or params.get('alg') != 'EdDSA':
            raise ValueError('unexpected token header')

        checker = VerifyingKey.from_string(b64decode(pubkey), curve=Ed25519)
        checker.verify(b64decode(signature), '{}.{}'.format(header, payload).encode('ascii'))

        claims = json.loads(b64decode(payload))
        if not isinstance(claims, dict):
            raise ValueError('payload is not a JSON object')

        return claims
    except Exception as e:
        logger.error('Failed to verify token, {}'.format(e))


class License:
    """A verified license: the claims that match this machine's
    configuration, and the remaining validity in days.

    Falsy when no claim matches, so `if service.license():` keeps its
    old meaning of "this copy is registered".
    """

    def __init__(self, claims, remaining):
        self.claims = claims
        self.remaining = remaining

    def __bool__(self):
        return bool(self.claims)


class LicenseService:
    # base64url-encoded Ed25519 public key
    key = 'pVUxLzkeh5GG7hsSV1upi7ZgJj3F9jJHM2oBJDd2cOI'

    requirements = {
        'TAF': 'airport',
        'CUSTOM': 'airport',
        'SIGMET': 'fir',
        'AIRMET': 'fir',
    }

    def __init__(self, conf):
        self.conf = conf
        self.payloads = {}

    def license(self, token=None, now=None):
        """Return the License for the token, or None when there is no
        token, the signature does not verify, or the token has expired."""
        token = token or self.conf.license
        if not token:
            return None

        # Verification is cached per token: a signature does not change,
        # and an invalid token would otherwise log on every call
        if token not in self.payloads:
            self.payloads[token] = verifyToken(token, self.key)

        payload = self.payloads[token]
        if payload is None:
            return None

        if now is None:
            now = utcnow()

        remaining = None
        if 'exp' in payload:
            # exp is a Unix timestamp: interpret it as UTC, otherwise the
            # naive result shifts by the machine's UTC offset
            exp = datetime.datetime.fromtimestamp(payload['exp'], tz=datetime.timezone.utc).replace(tzinfo=None)
            if exp <= now:
                return None
            remaining = (exp - now).days

        claims = {}
        for name, info in self.register().items():
            if name in payload and info == payload[name]:
                claims[name] = info

        return License(claims, remaining)

    def register(self):
        infos = {}
        if self.conf.airport:
            infos['airport'] = self.conf.airport
        if self.conf.firName:
            infos['fir'] = self.conf.firName[:4]
        return infos

    def hasPermission(self, category):
        if category == 'TREND':
            return True

        required = self.requirements.get(category)
        if required is None:
            return False

        license = self.license()
        return license is not None and required in license.claims
