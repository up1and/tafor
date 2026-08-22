import pytest

from PyQt5.QtCore import QSettings

from tafor.core.config import createConfig
from tafor.core.models import createDatabase
from tafor.core.states import createContext


@pytest.fixture(scope='session')
def conf():
    settings = QSettings(QSettings.InMemoryFormat, QSettings.UserScope, 'Up1and', 'Tafor')
    return createConfig(settings=settings)


@pytest.fixture(scope='session')
def context(conf):
    return createContext(conf)


@pytest.fixture
def database():
    database = createDatabase(uri='sqlite:///:memory:')
    yield database
    database.engine.dispose()
