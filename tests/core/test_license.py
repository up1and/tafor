"""Tests for tafor/core/license.py."""

import base64
import datetime
import json

import pytest

from ecdsa import Ed25519, SigningKey

from tafor.core.license import License, LicenseService, verifyToken


def b64encode(data):
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode()


def issue_token(signing_key, payload, header=None):
    """The signing side of the license format: JWS compact serialization,
    signed over the encoded header.payload segments."""
    if header is None:
        header = {'typ': 'JWT', 'alg': 'EdDSA'}
    segments = [b64encode(json.dumps(item, separators=(',', ':')).encode('utf-8'))
                for item in (header, payload)]
    signing_input = '.'.join(segments).encode('ascii')
    return signing_input.decode('ascii') + '.' + b64encode(signing_key.sign(signing_input))


@pytest.fixture(scope='module')
def signing_key():
    return SigningKey.generate(curve=Ed25519)


@pytest.fixture(scope='module')
def public_key(signing_key):
    return b64encode(signing_key.get_verifying_key().to_string())


@pytest.fixture
def service(conf, public_key):
    service = LicenseService(conf)
    service.key = public_key
    return service


@pytest.fixture
def license_conf(conf):
    """conf is session-scoped: restore the license key after each test."""
    yield conf
    conf.license = ''


class TestVerifyToken:
    """Signature verification with real Ed25519 keys."""

    def test_valid_token_returns_payload(self, signing_key, public_key):
        payload = {'airport': 'YUSO', 'fir': 'YUDD', 'exp': 1893456000}
        assert verifyToken(issue_token(signing_key, payload), public_key) == payload

    def test_tampered_payload_is_rejected(self, signing_key, public_key):
        token = issue_token(signing_key, {'airport': 'YUSO'})
        header, _, signature = token.split('.')
        forged = header + '.' + b64encode(b'{"airport":"ZZZZ"}') + '.' + signature
        assert verifyToken(forged, public_key) is None

    def test_tampered_header_is_rejected(self, signing_key, public_key):
        # The JWS signing input covers the encoded header.payload, so a
        # re-encoded header no longer matches the original signature
        token = issue_token(signing_key, {'airport': 'YUSO'})
        _, payload, signature = token.split('.')
        header = b64encode(b'{"alg":"EdDSA","typ":"XXX"}')
        assert verifyToken(header + '.' + payload + '.' + signature, public_key) is None

    def test_tampered_signature_is_rejected(self, signing_key, public_key):
        token = issue_token(signing_key, {'airport': 'YUSO'})
        header, payload, signature = token.split('.')
        # Flip a character in the middle of the signature: the last one may
        # only carry padding bits, which the decoder discards
        replacement = 'A' if signature[10] != 'A' else 'B'
        forged = '.'.join([header, payload, signature[:10] + replacement + signature[11:]])
        assert verifyToken(forged, public_key) is None

    def test_wrong_public_key_is_rejected(self, signing_key):
        other = SigningKey.generate(curve=Ed25519)
        token = issue_token(signing_key, {'airport': 'YUSO'})
        assert verifyToken(token, b64encode(other.get_verifying_key().to_string())) is None

    def test_header_alg_is_pinned(self, signing_key, public_key):
        # The header never selects the algorithm: anything but EdDSA is
        # rejected even though the Ed25519 signature itself is valid
        for header in [{'alg': 'none'}, {'alg': 'HS256'}, {'typ': 'JWT'}, ['EdDSA']]:
            token = issue_token(signing_key, {'airport': 'YUSO'}, header=header)
            assert verifyToken(token, public_key) is None

    def test_header_without_typ_is_accepted(self, signing_key, public_key):
        token = issue_token(signing_key, {'airport': 'YUSO'}, header={'alg': 'EdDSA'})
        assert verifyToken(token, public_key) == {'airport': 'YUSO'}

    def test_two_segment_token_is_rejected(self, signing_key, public_key):
        token = issue_token(signing_key, {'airport': 'YUSO'})
        _, payload, signature = token.split('.')
        assert verifyToken(payload + '.' + signature, public_key) is None

    def test_malformed_tokens_return_none(self, public_key):
        for token in ['', 'onlyonesegment', 'four.a.b.c', '!!!.@@@.###']:
            assert verifyToken(token, public_key) is None

    def test_non_dict_payload_is_rejected(self, signing_key, public_key):
        token = issue_token(signing_key, ['airport', 'YUSO'])
        assert verifyToken(token, public_key) is None

    def test_invalid_public_key_returns_none(self, signing_key):
        token = issue_token(signing_key, {'airport': 'YUSO'})
        assert verifyToken(token, 'not-a-key') is None


class TestRegister:

    def test_claims_from_config(self, service):
        assert service.register() == {'airport': 'YUSO', 'fir': 'YUDD'}

    def test_fir_claim_is_truncated_to_four_characters(self, conf):
        service = LicenseService(conf)
        assert service.register()['fir'] == conf.firName[:4]


class TestLicense:

    def test_no_token_returns_none(self, license_conf, service):
        assert license_conf.license == ''
        assert service.license() is None

    def test_failed_verification_returns_none(self, service, monkeypatch):
        monkeypatch.setattr('tafor.core.license.verifyToken', lambda token, key: None)
        assert service.license('token') is None

    def test_matching_claims_are_kept(self, service, monkeypatch):
        monkeypatch.setattr(
            'tafor.core.license.verifyToken',
            lambda token, key: {'airport': 'YUSO', 'fir': 'YUDD', 'extra': 'ignored'})
        license = service.license('token')
        assert license.claims == {'airport': 'YUSO', 'fir': 'YUDD'}
        assert license

    def test_mismatched_claim_is_dropped_per_key(self, service, monkeypatch):
        # The claims are filtered key by key: a license whose airport does
        # not match still keeps the fir permission
        monkeypatch.setattr(
            'tafor.core.license.verifyToken',
            lambda token, key: {'airport': 'ZZZZ', 'fir': 'YUDD'})
        assert service.license('token').claims == {'fir': 'YUDD'}

    def test_no_matching_claims_is_falsy(self, service, monkeypatch):
        # A valid signature alone does not register the copy: the claims
        # must also match this machine's configuration
        monkeypatch.setattr(
            'tafor.core.license.verifyToken',
            lambda token, key: {'airport': 'ZZZZ'})
        license = service.license('token')
        assert license.claims == {}
        assert not license

    def test_exp_days_uses_utc_for_the_token_expiry(self, service, monkeypatch):
        # 'exp' is a Unix timestamp and must be interpreted as UTC; comparing
        # it against a local-time fromtimestamp() result would shift the
        # remaining days by the machine's UTC offset
        exp = datetime.datetime(2026, 6, 13, 12, 0, tzinfo=datetime.timezone.utc).timestamp()
        monkeypatch.setattr('tafor.core.license.verifyToken', lambda token, key: {'exp': exp})

        now = datetime.datetime(2026, 6, 10, 8, 0)
        license = service.license('token', now=now)
        assert license.claims == {}
        assert license.remaining == 3

    def test_expired_token_returns_none(self, service, signing_key):
        expired = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1)).timestamp()
        token = issue_token(signing_key, {'airport': 'YUSO', 'exp': expired})
        assert service.license(token) is None

    def test_payload_without_exp_has_no_days_remaining(self, service, monkeypatch):
        monkeypatch.setattr('tafor.core.license.verifyToken', lambda token, key: {'airport': 'YUSO'})
        assert service.license('token').remaining is None

    def test_token_from_config_is_used(self, license_conf, service, monkeypatch):
        license_conf.license = 'CONF-TOKEN'
        captured = {}

        def fakeVerify(token, key):
            captured['token'] = token
            return {'airport': 'YUSO'}

        monkeypatch.setattr('tafor.core.license.verifyToken', fakeVerify)
        assert service.license().claims == {'airport': 'YUSO'}
        assert captured['token'] == 'CONF-TOKEN'

    def test_verification_is_cached_per_token(self, service, monkeypatch):
        calls = []

        def fakeVerify(token, key):
            calls.append(token)
            return {'airport': 'YUSO'}

        monkeypatch.setattr('tafor.core.license.verifyToken', fakeVerify)
        service.license('token')
        service.license('token')
        service.license('other')
        assert calls == ['token', 'other']


class TestHasPermission:

    def test_trend_is_always_allowed(self, service, monkeypatch):
        monkeypatch.setattr(LicenseService, 'license', lambda self: None)
        assert service.hasPermission('TREND') is True

    def test_taf_needs_airport_claim(self, service, monkeypatch):
        monkeypatch.setattr(LicenseService, 'license', lambda self: License({'airport': 'YUSO'}, None))
        assert service.hasPermission('TAF') is True
        assert service.hasPermission('CUSTOM') is True

    def test_taf_without_airport_claim_rejected(self, service, monkeypatch):
        monkeypatch.setattr(LicenseService, 'license', lambda self: License({'fir': 'YUDD'}, None))
        assert service.hasPermission('TAF') is False

    def test_sigmet_needs_fir_claim(self, service, monkeypatch):
        monkeypatch.setattr(LicenseService, 'license', lambda self: License({'fir': 'YUDD'}, None))
        assert service.hasPermission('SIGMET') is True
        assert service.hasPermission('AIRMET') is True

    def test_sigmet_without_fir_claim_rejected(self, service, monkeypatch):
        monkeypatch.setattr(LicenseService, 'license', lambda self: License({'airport': 'YUSO'}, None))
        assert service.hasPermission('SIGMET') is False

    def test_unknown_category_rejected(self, service, monkeypatch):
        monkeypatch.setattr(LicenseService, 'license', lambda self: License({'airport': 'YUSO', 'fir': 'YUDD'}, None))
        assert service.hasPermission('OTHER') is False

    def test_no_license_rejected(self, service, monkeypatch):
        monkeypatch.setattr(LicenseService, 'license', lambda self: None)
        assert service.hasPermission('TAF') is False


class TestEndToEnd:
    """Real Ed25519 signatures through the whole service."""

    def test_signed_token_grants_matching_permissions(self, license_conf, service, signing_key):
        license_conf.license = issue_token(signing_key, {'airport': 'YUSO', 'fir': 'YUDD', 'exp': 1893456000})
        assert service.hasPermission('TAF') is True
        assert service.hasPermission('SIGMET') is True
        assert service.license().remaining is not None

    def test_signed_token_for_another_airport_denies_taf(self, license_conf, service, signing_key):
        license_conf.license = issue_token(signing_key, {'airport': 'ZZZZ', 'fir': 'YUDD', 'exp': 1893456000})
        assert service.hasPermission('TAF') is False
        assert service.hasPermission('SIGMET') is True


if __name__ == '__main__':
    pytest.main([__file__])
