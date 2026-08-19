import os

import pytest


root = os.path.dirname(__file__)


@pytest.fixture(scope='session', autouse=True)
def initialize():
    print('start')
    yield
    print('end')


@pytest.fixture(scope='session', autouse=True)
def configure_database():
    from tafor.core.models import createDatabase

    createDatabase(uri='sqlite:///:memory:')
    yield
