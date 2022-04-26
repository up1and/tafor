import os

import pytest


root = os.path.dirname(__file__)


@pytest.fixture(scope='session', autouse=True)
def initialize():
    print('start')
    yield
    print('end')
