"""Tests for tafor/core/services.py."""

import datetime

import pytest

from tafor.core.services import LicenseService, SerialLock


@pytest.fixture
def service(conf):
    return LicenseService(conf)


@pytest.fixture
def license_conf(conf):
    """conf is session-scoped: restore the license key after each test."""
    yield conf
    conf.license = ''


class TestRegister:

    def test_claims_from_config(self, service):
        assert service.register() == {'airport': 'YUSO', 'fir': 'YUDD'}

    def test_fir_claim_is_truncated_to_four_characters(self, conf):
        conf_copy = LicenseService(conf)
        assert conf_copy.register()['fir'] == conf.firName[:4]


class TestLicense:

    def test_no_token_returns_empty(self, license_conf, service):
        assert license_conf.license == ''
        assert service.license() == {}

    def test_failed_verification_returns_empty(self, conf, service, monkeypatch):
        monkeypatch.setattr('tafor.core.services.verifyToken', lambda token, key: None)
        assert service.license('token') == {}

    def test_matching_claims_are_kept(self, conf, service, monkeypatch):
        monkeypatch.setattr(
            'tafor.core.services.verifyToken',
            lambda token, key: {'airport': 'YUSO', 'fir': 'YUDD', 'extra': 'ignored'})
        assert service.license('token') == {'airport': 'YUSO', 'fir': 'YUDD'}

    def test_mismatched_claim_is_dropped_per_key(self, service, monkeypatch):
        # The claims are filtered key by key: a license whose airport does
        # not match still keeps the fir permission
        monkeypatch.setattr(
            'tafor.core.services.verifyToken',
            lambda token, key: {'airport': 'ZZZZ', 'fir': 'YUDD'})
        assert service.license('token') == {'fir': 'YUDD'}

    def test_exp_days_uses_utc_for_the_token_expiry(self, service, monkeypatch):
        # 'exp' is a Unix timestamp and must be interpreted as UTC; comparing
        # it against a local-time fromtimestamp() result would shift the
        # remaining days by the machine's UTC offset
        exp = datetime.datetime(2026, 6, 13, 12, 0, tzinfo=datetime.timezone.utc).timestamp()
        monkeypatch.setattr('tafor.core.services.verifyToken', lambda token, key: {'exp': exp})

        now = datetime.datetime(2026, 6, 10, 8, 0)
        assert service.license('token', now=now) == {}
        assert service.exp == 3

    def test_exp_days_side_effect(self, service, monkeypatch):
        # license() stores the remaining validity in self.exp even though
        # it returns only the verified claims
        exp = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=3, hours=4)).timestamp()
        monkeypatch.setattr('tafor.core.services.verifyToken', lambda token, key: {'exp': exp})
        service.license('token')
        expected = (datetime.datetime.fromtimestamp(exp, tz=datetime.timezone.utc).replace(tzinfo=None)
                    - datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)).days
        assert service.exp == expected

    def test_payload_without_exp_keeps_zero(self, service, monkeypatch):
        monkeypatch.setattr('tafor.core.services.verifyToken', lambda token, key: {'airport': 'YUSO'})
        service.license('token')
        assert service.exp == 0

    def test_token_from_config_is_used(self, license_conf, service, monkeypatch):
        license_conf.license = 'CONF-TOKEN'
        captured = {}

        def fakeVerify(token, key):
            captured['token'] = token
            return {'airport': 'YUSO'}

        monkeypatch.setattr('tafor.core.services.verifyToken', fakeVerify)
        assert service.license() == {'airport': 'YUSO'}
        assert captured['token'] == 'CONF-TOKEN'


class TestHasPermission:

    def test_trend_is_always_allowed(self, service, monkeypatch):
        monkeypatch.setattr(LicenseService, 'license', lambda self: {})
        assert service.hasPermission('TREND') is True

    def test_taf_needs_airport_claim(self, service, monkeypatch):
        monkeypatch.setattr(LicenseService, 'license', lambda self: {'airport': 'YUSO'})
        assert service.hasPermission('TAF') is True
        assert service.hasPermission('CUSTOM') is True

    def test_taf_without_airport_claim_rejected(self, service, monkeypatch):
        monkeypatch.setattr(LicenseService, 'license', lambda self: {'fir': 'YUDD'})
        assert service.hasPermission('TAF') is False

    def test_sigmet_needs_fir_claim(self, service, monkeypatch):
        monkeypatch.setattr(LicenseService, 'license', lambda self: {'fir': 'YUDD'})
        assert service.hasPermission('SIGMET') is True
        assert service.hasPermission('AIRMET') is True

    def test_sigmet_without_fir_claim_rejected(self, service, monkeypatch):
        monkeypatch.setattr(LicenseService, 'license', lambda self: {'airport': 'YUSO'})
        assert service.hasPermission('SIGMET') is False

    def test_unknown_category_rejected(self, service, monkeypatch):
        monkeypatch.setattr(LicenseService, 'license', lambda self: {'airport': 'YUSO', 'fir': 'YUDD'})
        assert service.hasPermission('OTHER') is False


class TestSerialLock:

    def test_initially_not_busy(self):
        lock = SerialLock()
        assert lock.isBusy is False

    def test_lock_and_release(self):
        lock = SerialLock()
        lock.lock()
        assert lock.isBusy is True
        lock.release()
        assert lock.isBusy is False

    def test_release_without_lock_is_harmless(self):
        lock = SerialLock()
        lock.release()
        assert lock.isBusy is False


if __name__ == '__main__':
    pytest.main([__file__])
