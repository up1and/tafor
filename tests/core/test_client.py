import logging

import pytest

import requests

from tafor.core.utils import client
from tafor.core.utils.client import fetchMessage, headers, layerInfo, repoRelease


class FakeResponse:

    def __init__(self, status_code=200, payload=None, content=b''):
        self.status_code = status_code
        self.content = content
        self._payload = payload

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload

    def raise_for_status(self):
        if self.status_code != 200:
            raise requests.exceptions.HTTPError(
                'unexpected status {}'.format(self.status_code))


class FakeGet:
    # Returns canned responses in order; an Exception item is raised instead
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, url, **kwargs):
        self.calls.append((url, kwargs))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def use_responses(monkeypatch, fake):
    monkeypatch.setattr(client.requests, 'get', fake)


def test_headers_builds_user_agent():
    agent = headers()['User-Agent']

    assert agent.startswith('Tafor/')
    assert '{' not in agent and '}' not in agent


def test_fetch_message_keeps_known_keys_only(monkeypatch):
    payload = {
        'WS': ['wx1', 'wx2'],
        'FC': 'TAF ZJHK=',
        'WC': 'not-a-list',
        'FT': 123,
        'XX': ['unknown'],
    }
    fake = FakeGet(FakeResponse(payload=payload))
    use_responses(monkeypatch, fake)

    assert fetchMessage('http://x/messages') == {'WS': ['wx1', 'wx2'], 'FC': 'TAF ZJHK='}


def test_fetch_message_sends_headers_and_timeout(monkeypatch):
    fake = FakeGet(FakeResponse(payload={}))
    use_responses(monkeypatch, fake)

    fetchMessage('http://x/messages')

    url, kwargs = fake.calls[0]
    assert url == 'http://x/messages'
    assert kwargs['timeout'] == 30
    assert 'User-Agent' in kwargs['headers']


def test_fetch_message_rejects_non_dict_payload(monkeypatch):
    use_responses(monkeypatch, FakeGet(FakeResponse(payload=['not', 'dict'])))

    with pytest.raises(ValueError, match='dictionary'):
        fetchMessage('http://x')


def test_fetch_message_unexpected_status(monkeypatch):
    use_responses(monkeypatch, FakeGet(FakeResponse(status_code=404)))

    with pytest.raises(requests.exceptions.HTTPError, match='404'):
        fetchMessage('http://x')


def test_fetch_message_timeout(monkeypatch):
    use_responses(monkeypatch, FakeGet(requests.exceptions.Timeout()))

    with pytest.raises(requests.exceptions.Timeout):
        fetchMessage('http://x')


def test_fetch_message_connection_error(monkeypatch):
    use_responses(monkeypatch, FakeGet(requests.exceptions.ConnectionError()))

    with pytest.raises(requests.exceptions.ConnectionError):
        fetchMessage('http://x')


def test_fetch_message_broken_json(monkeypatch):
    use_responses(monkeypatch, FakeGet(FakeResponse(payload=ValueError('invalid json'))))

    with pytest.raises(ValueError, match='invalid json'):
        fetchMessage('http://x')


def test_fetch_message_empty_payload_is_a_success(monkeypatch):
    # an honest empty response from the server is fresh silence
    use_responses(monkeypatch, FakeGet(FakeResponse(payload={})))

    assert fetchMessage('http://x') == {}


def test_fetch_message_unknown_keys_raise_and_log(monkeypatch, caplog):
    # the server answered, but nothing in the payload is a subscribed type;
    # raising stops it before it can wipe the cached messages as a payload
    # that simply looks empty
    use_responses(monkeypatch, FakeGet(FakeResponse(payload={'XX': ['unknown']})))

    with caplog.at_level(logging.ERROR):
        with pytest.raises(ValueError, match="'XX'"):
            fetchMessage('http://x')

    assert 'Unknown message keys' in caplog.text


def test_layer_info_downloads_layer_images(monkeypatch):
    fake = FakeGet(
        FakeResponse(payload=[{'image': 'http://img/1'}, {'image': 'http://img/2'}]),
        FakeResponse(content=b'first'),
        FakeResponse(content=b'second'),
    )
    use_responses(monkeypatch, fake)

    layers = layerInfo('http://x/layers')

    assert [layer['image'] for layer in layers] == [b'first', b'second']
    assert fake.calls[1][0] == 'http://img/1'
    assert fake.calls[2][0] == 'http://img/2'


def test_layer_info_failed_image_becomes_none(monkeypatch, caplog):
    fake = FakeGet(
        FakeResponse(payload=[{'image': 'http://img/bad'}, {'image': 'http://img/good'}]),
        requests.exceptions.ConnectionError(),
        FakeResponse(content=b'ok'),
    )
    use_responses(monkeypatch, fake)

    with caplog.at_level(logging.WARNING):
        layers = layerInfo('http://x/layers')

    # A failed image download only affects its own layer, and leaves a trace
    assert layers[0]['image'] is None
    assert layers[1]['image'] == b'ok'
    assert 'Failed to download layer image' in caplog.text


def test_layer_info_missing_image_field_becomes_none(monkeypatch, caplog):
    fake = FakeGet(FakeResponse(payload=[{'other': 1}]))
    use_responses(monkeypatch, fake)

    with caplog.at_level(logging.WARNING):
        assert layerInfo('http://x/layers') == [{'other': 1, 'image': None}]
    assert 'Failed to download layer image' in caplog.text


def test_layer_info_rejects_non_list_payload(monkeypatch):
    use_responses(monkeypatch, FakeGet(FakeResponse(payload={'a': 1})))

    with pytest.raises(ValueError, match='list'):
        layerInfo('http://x/layers')


def test_layer_info_unexpected_status(monkeypatch):
    use_responses(monkeypatch, FakeGet(FakeResponse(status_code=500)))

    with pytest.raises(requests.exceptions.HTTPError, match='500'):
        layerInfo('http://x/layers')


def test_layer_info_timeout(monkeypatch):
    use_responses(monkeypatch, FakeGet(requests.exceptions.Timeout()))

    with pytest.raises(requests.exceptions.Timeout):
        layerInfo('http://x/layers')


def test_repo_release_returns_payload(monkeypatch):
    release = {'tag_name': 'v3.0.1'}
    fake = FakeGet(FakeResponse(payload=release))
    use_responses(monkeypatch, fake)

    assert repoRelease('http://x/release') == release


def test_repo_release_timeout(monkeypatch):
    use_responses(monkeypatch, FakeGet(requests.exceptions.Timeout()))

    with pytest.raises(requests.exceptions.Timeout):
        repoRelease('http://x/release')


def test_repo_release_connection_error(monkeypatch):
    use_responses(monkeypatch, FakeGet(requests.exceptions.ConnectionError()))

    with pytest.raises(requests.exceptions.ConnectionError):
        repoRelease('http://x/release')


def test_repo_release_broken_json(monkeypatch):
    use_responses(monkeypatch, FakeGet(FakeResponse(payload=ValueError('expecting value'))))

    with pytest.raises(ValueError):
        repoRelease('http://x/release')


def test_repo_release_unexpected_status(monkeypatch):
    use_responses(monkeypatch, FakeGet(FakeResponse(status_code=404)))

    with pytest.raises(requests.exceptions.HTTPError):
        repoRelease('http://x/release')


def test_repo_release_wrong_payload_shape(monkeypatch):
    use_responses(monkeypatch, FakeGet(FakeResponse(payload=['not', 'an', 'object'])))

    with pytest.raises(ValueError):
        repoRelease('http://x/release')
