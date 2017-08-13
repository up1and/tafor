import os
import sys
import logging

from PyQt5 import QtCore
from tafor.models import Session


__version__ = "1.0.0"

BASEDIR = os.path.abspath(os.path.dirname(__file__))

def setup_log(debug=False):
    log_level = logging.DEBUG if debug else logging.INFO

    _format = '[%(asctime)s] %(levelname)s %(message)s'
    formatter = logging.Formatter(_format)

    # set stdout
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(formatter)

    # set log file
    fh = logging.FileHandler('log.log')
    fh.setLevel(log_level)
    fh.setFormatter(formatter)

    # log
    log = logging.getLogger(__name__)
    log.setLevel(log_level)
    log.addHandler(ch)
    log.addHandler(fh)

    return log

setting = QtCore.QSettings('Up1and', 'Tafor')

debug = setting.value('convention/debug')

log = setup_log(debug=debug)
