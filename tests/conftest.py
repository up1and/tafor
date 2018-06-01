import os

import pytest

from tafor.app import MainWindow
from tafor.components.setting import loadConf, saveConf

root = os.path.dirname(__file__)


@pytest.fixture(scope='session')
def window():
    widget = MainWindow()
    return widget

@pytest.fixture(scope='session', autouse=True)
def load_conf():
    fixture = os.path.join(root, 'fixtures', 'config.json')
    backup = os.path.join(root, 'fixtures', 'backup.json')
    saveConf(backup)
    loadConf(fixture)
    yield 
    loadConf(backup)