import pytest

import falcon
import falcon.testing
from sqlalchemy import create_engine

from tafor.core.models import Base
from tafor.core.rpc.api import create_app


class FakeConf(object):

    channel = 'YMC'
    channelSequenceNumber = '1'
    channelSequenceLength = '4'
    fileSequenceNumber = '1'
    maxSendAddress = '21'
    originatorAddress = 'YUSOYMYX'
    tafAddress = 'YUSOYMYX'
    trendAddress = 'YUSOYMYX'
    sigmetAddress = 'YUSOYMYX'
    airmetAddress = 'YUSOYMYX'
    license = 'test-token'
    visHas5000 = False
    cloudHeightHas450 = True
    weakPrecipitationVerification = False

    def get(self, name):
        return getattr(self, name)


class FakeContext(object):

    class _Serial(object):
        isBusy = False

    class _Metar(object):
        def setState(self, values):
            self.values = values

    class _Sigmet(object):
        def setState(self, values):
            self.values = values

    class _Other(object):
        def setState(self, values):
            self.__dict__.update(values)

    def __init__(self):
        self.serial = self._Serial()
        self.notification = type('Notification', (), {
            'metar': self._Metar(),
            'sigmet': self._Sigmet(),
        })()
        self.other = self._Other()


@pytest.fixture
def engine():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def client(engine):
    app = create_app(engine=engine, conf=FakeConf(), context=FakeContext())
    return falcon.testing.TestClient(app)


def _auth(token='test-token'):
    return {'Authorization': 'Bearer ' + token}


def test_create_app_exposes_routes(client):
    assert client.simulate_get('/').status == falcon.HTTP_200


def test_state_resource(client):
    resp = client.simulate_get('/api/state', headers=_auth())
    assert resp.status == falcon.HTTP_200
    data = resp.json
    assert data['busy'] is False
    assert data['aftn']['channel'] == 'YMC'
    assert data['address']['taf'] == 'YUSOYMYX'


def test_authorize_required(client):
    resp = client.simulate_get('/api/state')
    assert resp.status == falcon.HTTP_401


def test_authorize_invalid_token(client):
    resp = client.simulate_get('/api/state', headers=_auth('wrong-token'))
    assert resp.status == falcon.HTTP_401


def test_metars_resource(client):
    resp = client.simulate_get('/api/metars', headers=_auth())
    assert resp.status == falcon.HTTP_200
    assert resp.json['metars'] == []


def test_others_resource(client, engine):
    body = {
        'priority': 'UR',
        'address': 'YUSOYMYX',
        'message': 'TEST MESSAGE',
    }
    resp = client.simulate_post('/api/others', headers=_auth(), json=body)
    assert resp.status == falcon.HTTP_CREATED
    assert resp.json['type'] == 'other'
    assert resp.json['message']
    assert client.simulate_get('/api/others', headers=_auth()).status == falcon.HTTP_200


def test_notification_metar(client):
    resp = client.simulate_post(
        '/api/notifications',
        headers=_auth(),
        json={'message': 'METAR ZJHK 210900Z 14004MPS 4500 -RA BKN030=', 'validation': True},
    )
    assert resp.status == falcon.HTTP_CREATED
    assert 'validations' in resp.json


SIGMET_MESSAGE = (
    'ZJSA SIGMET 1 VALID 300855/301255 ZJHK-\n'
    'ZJSA SANYA FIR TC YAGI OBS AT 1400Z N2300 E11304 CB TOP FL420 WI 300KM OF CENTER MOV NE 30KMH INTSF\n'
    'FCST 1925Z TC CENTER N2401 E11411='
)


def test_notification_sigmet(client):
    resp = client.simulate_post(
        '/api/notifications',
        headers=_auth(),
        json={'message': SIGMET_MESSAGE},
    )
    assert resp.status == falcon.HTTP_CREATED


def test_notification_requires_message(client):
    resp = client.simulate_post('/api/notifications', headers=_auth(), json={})
    assert resp.status == falcon.HTTP_400


def test_parse_taf():
    from tafor.core.rpc.api import parse_taf

    data = parse_taf('TAF ZJHK 211338Z 211524 14004MPS 4500 -RA BKN030=', {})
    assert data['pass'] is True
    assert data['html']


def test_parse_metar():
    from tafor.core.rpc.api import parse_metar

    data = parse_metar('METAR ZJHK 210900Z 14004MPS 4500 -RA BKN030=', {})
    assert data['pass'] is True
    assert data['html']


def test_parse_sigmet():
    from tafor.core.rpc.api import parse_sigmet

    data = parse_sigmet(SIGMET_MESSAGE, {})
    assert data['pass'] is True
    assert data['html']