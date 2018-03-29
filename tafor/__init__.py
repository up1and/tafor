import os
import sys
import logging

from PyQt5 import QtCore


__version__ = '1.0.1-beta'

BASEDIR = os.path.abspath(os.path.dirname(sys.argv[0]))
BASEDIR = os.path.abspath(os.path.dirname(__file__))


def boolean(value):
    return value if isinstance(value, bool) else value == 'true'

def setupLog(debug=False):
    logLevel = logging.DEBUG if debug else logging.INFO

    _format = '[%(asctime)s] %(levelname)s %(message)s'
    formatter = logging.Formatter(_format)

    # set stdout
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(formatter)

    # set log file
    fh = logging.FileHandler('log.log')
    fh.setLevel(logLevel)
    fh.setFormatter(formatter)

    # log
    log = logging.getLogger(__name__)
    log.setLevel(logLevel)
    log.addHandler(ch)
    log.addHandler(fh)

    return log

conf = QtCore.QSettings('Up1and', 'Tafor')
debug = boolean(conf.value('General/Debug'))
logger = setupLog(debug=debug)
