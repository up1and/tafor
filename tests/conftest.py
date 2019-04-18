import os

import pytest

from tafor.components.setting import loadConf, saveConf

root = os.path.dirname(__file__)


@pytest.fixture(scope='session', autouse=True)
def initialize():
    fixture = os.path.join(root, 'fixtures', 'config.json')
    backup = os.path.join(root, 'fixtures', 'backup.json')
    saveConf(backup)
    loadConf(fixture)
    yield
    loadConf(backup)

    # database = os.path.join(root, 'db.sqlite3')
    # if os.path.exists(database):
    #     os.remove(database)
