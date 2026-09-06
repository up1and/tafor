import pytest

from tafor.core.utils.units import UnitSystem, KM_PER_NM, toKmh, toKt, toKm


class TestUnitSystem:

    def test_metric_units(self):
        units = UnitSystem.METRIC
        assert units.tafSpeed == 'MPS'
        assert units.sigmetSpeed == 'KMH'
        assert units.length == 'KM'

    def test_imperial_units(self):
        units = UnitSystem.IMPERIAL
        assert units.tafSpeed == 'KT'
        assert units.sigmetSpeed == 'KT'
        assert units.length == 'NM'

    @pytest.mark.parametrize('value', ['metric', None, '', 'imperal'])
    def test_invalid_config_falls_back_to_metric(self, value):
        assert UnitSystem.fromConfig(value) is UnitSystem.METRIC

    def test_valid_config_round_trip(self):
        assert UnitSystem.fromConfig('imperial') is UnitSystem.IMPERIAL
        assert UnitSystem.fromConfig('metric') is UnitSystem.METRIC

    def test_conf_accessor(self, conf):
        assert conf.unit in [u.value for u in UnitSystem]
        assert conf.units is UnitSystem.fromConfig(conf.unit)


class TestSpeedConversion:

    def test_kt_to_kmh(self):
        assert toKmh(65, 'KT') == 65 * KM_PER_NM

    def test_kmh_passthrough(self):
        assert toKmh(10, 'KMH') == 10

    def test_kmh_to_kt(self):
        assert toKt(200, 'KMH') == pytest.approx(200 / KM_PER_NM)

    def test_kt_passthrough(self):
        assert toKt(15, 'KT') == 15


class TestLengthConversion:

    def test_nm_to_km(self):
        assert toKm(30, 'NM') == 30 * KM_PER_NM
        assert toKm(1, 'NM') == KM_PER_NM

    def test_km_passthrough(self):
        assert toKm(5, 'KM') == 5

    def test_constant_value(self):
        assert KM_PER_NM == 1.852
