import pytest

from tafor.core.config import Config, ConfigItem, ConfigManager, ConfigRegistry, createConfig
from tests.mocks import MockConfig


def makeSettings():
    settings = MockConfig()
    settings.config.clear()
    return settings


def makeConf():
    return createConfig(settings=makeSettings())


def test_defaults_when_unset():
    conf = makeConf()

    assert isinstance(conf, ConfigRegistry)
    assert conf.unit == 'metric'
    assert conf.airport == 'YUSO'
    assert conf.sigmetEnabled is False
    assert conf.interfaceScaling == 0


def test_schema_usable_without_registry():
    schema = Config(ConfigManager(makeSettings()))

    schema.codec = 'UTF-8'
    assert schema.codec == 'UTF-8'


def test_coerces_stored_value_to_default_type():
    conf = makeConf()

    conf.set('remindTaf', 'true')
    assert conf.get('remindTaf') is True

    conf.set('interfaceScaling', '2')
    assert conf.interfaceScaling == 2


def test_attribute_and_get_set_are_equivalent():
    conf = makeConf()

    conf.codec = 'UTF-8'
    assert conf.codec == 'UTF-8'
    assert conf.get('codec') == 'UTF-8'

    conf.set('codec', 'GB2312')
    assert conf.codec == 'GB2312'


def test_unknown_attribute_raises():
    conf = makeConf()

    with pytest.raises(AttributeError):
        conf.notExist

    with pytest.raises(AttributeError):
        conf.notExist = 1

    with pytest.raises(AttributeError):
        conf.set('notExist', 1)


def test_validator_rejects_invalid_value():
    conf = makeConf()

    with pytest.raises(ValueError):
        conf.firBoundary = 'not-a-json'

    conf.firBoundary = '[[0, 0], [1, 0], [1, 1], [0, 1]]'
    assert conf.firBoundary == [[0, 0], [1, 0], [1, 1], [0, 1]]


def test_set_json_string_broadcasts_typed_value():
    conf = makeConf()
    changes = []
    conf.manager.configChanged.connect(
        lambda key, value, scope: changes.append((key, value, scope)))

    conf.weatherList = '["FG", "FU"]'

    assert conf.weatherList == ['FG', 'FU']
    key, value, scope = changes[-1]
    assert key == 'Message/Weather'
    assert value == ['FG', 'FU']
    assert scope == 'restart'


def test_set_invalid_json_keeps_raw_value_without_raising():
    conf = makeConf()

    conf.weatherList = 'not-a-json'

    # the raw text is stored; read-back falls back to the default list
    assert conf.weatherList == []


def test_emit_fires_signals_for_pending_scopes():
    conf = makeConf()
    reloaded = []
    restarted = []

    conf.reloadRequired.connect(lambda: reloaded.append(True))
    conf.restartRequired.connect(lambda: restarted.append(True))

    conf.windowsStyle = 'Fusion'             # scope: restart
    conf.communicationProtocol = 'Serial'    # scope: reload
    conf.communicationProtocol = 'FTP'       # scope: reload, again
    conf.unit = 'imperial'                   # scope: immediate

    assert reloaded == []
    assert restarted == []

    conf.emit()
    assert len(reloaded) == 1
    assert len(restarted) == 1

    conf.emit()
    assert len(reloaded) == 1
    assert len(restarted) == 1


def test_check_completeness():
    conf = makeConf()

    assert conf.checkCompleteness('taf') is False

    conf.channel = 'AFTN'
    conf.originatorAddress = 'YUSOYYXX'
    conf.bulletinNumber = 'B001'
    conf.tafAddress = 'YUSO3001'

    assert conf.checkCompleteness('taf') is True
    assert conf.checkCompleteness('unknown') is True


def test_iter_yields_bound_items_only():
    conf = makeConf()
    items = dict(conf)

    assert 'windowsStyle' in items
    assert all(isinstance(item, ConfigItem) and item.bindProperty for item in items.values())
    assert 'license' not in items
    assert 'unit' not in items
    assert 'fileSequenceNumber' not in items


def test_iter_does_not_cache_values_on_descriptors():
    conf = makeConf()

    for attr, item in conf:
        assert 'value' not in vars(item)


def test_instances_do_not_share_state():
    a = makeConf()
    b = makeConf()

    a.codec = 'UTF-8'
    b.codec = 'GB2312'

    assert a.codec == 'UTF-8'
    assert b.codec == 'GB2312'


def test_mock_config_instances_do_not_share_state():
    a = MockConfig()
    b = MockConfig()

    a.setValue('General/WindowsStyle', 'Fusion')

    assert a.value('General/WindowsStyle') == 'Fusion'
    assert b.value('General/WindowsStyle') == 'System'
