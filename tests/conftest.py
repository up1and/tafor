import os

import pytest

from tafor.app import MainWindow
from tafor.components.setting import loadConf, saveConf

root = os.path.dirname(__file__)


@pytest.fixture
def window():
    widget = MainWindow()
    return widget

@pytest.fixture
def mock():
    # tmpfile = tmpdir.join('config.json')
    tmpfile = os.path.join(root, 'fixtures', 'default.json')
    saveConf(tmpfile)
    yield
    loadConf(tmpfile)