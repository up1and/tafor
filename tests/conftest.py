import os
import datetime

import pytest

from pathlib import Path

# Run Qt widgets headless so tests that show() top-level widgets do not
# flash windows on the desktop. Must be set before QApplication is created.
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from tafor.core.config import createConfig
from tafor.core.models import createDatabase
from tafor.core.states import createContext
from tests.mocks import MockConfig

root = Path(__file__).resolve().parent

# Canonical frozen instant for time-dependent tests: 2026-06-10 08:00 UTC.
FROZEN_MOMENT = datetime.datetime(2026, 6, 10, 8, 0)


@pytest.fixture
def frozen_time(time_machine):
    """Freeze the process-wide wall clock at FROZEN_MOMENT.

    time-machine replaces datetime.datetime.now/utcnow, time.time() etc.
    for every module, including datetime captured at import time (SQLAlchemy
    column defaults), so no per-module patch lists are needed. tick=False
    keeps the clock exactly at the frozen instant.
    """
    time_machine.move_to(FROZEN_MOMENT, tick=False)
    return FROZEN_MOMENT


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
