import pytest

from tafor.core.config import createConfig
from tafor.core.models import createDatabase
from tafor.core.states import createContext
from tests.mocks import MockConfig


@pytest.fixture(scope='session')
def conf():
    return createConfig(settings=MockConfig())


@pytest.fixture
def context(conf):
    # Function-scoped: UI widgets connect to context events, so the context
    # must not outlive a test's widgets (handlers would fire on dead objects)
    return createContext(conf)


@pytest.fixture
def database():
    database = createDatabase(uri='sqlite:///:memory:')
    yield database
    database.engine.dispose()
