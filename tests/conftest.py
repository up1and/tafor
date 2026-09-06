import pytest

from pathlib import Path

from tafor.core.config import createConfig
from tafor.core.models import createDatabase
from tafor.core.states import createContext
from tests.mocks import MockConfig

root = Path(__file__).resolve().parent


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


@pytest.fixture(scope='session')
def fixtures_dir():
    return root / 'fixtures'


@pytest.fixture
def read_fixture(fixtures_dir):
    def read(folder, name):
        return (fixtures_dir / folder / f'{name}.text').read_text()
    return read
