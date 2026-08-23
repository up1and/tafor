import pytest

from tafor.core.config import createConfig
from tafor.core.models import createDatabase
from tafor.core.states import createContext
from tests.mocks import MockConfig


@pytest.fixture(scope='session')
def conf():
    return createConfig(settings=MockConfig())


@pytest.fixture(scope='session')
def context(conf):
    return createContext(conf)


@pytest.fixture
def database():
    database = createDatabase(uri='sqlite:///:memory:')
    yield database
    database.engine.dispose()
