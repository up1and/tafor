import logging

from PyQt5 import QtCore

from models import Session

__version__ = "1.0.0"

db = Session()
setting = QtCore.QSettings('Up1and', 'Tafor')