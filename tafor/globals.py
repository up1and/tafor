import os
import sys
import logging

from logging.handlers import RotatingFileHandler


def createLogger(debug=False, name=None):
    logLevel = logging.DEBUG if debug else logging.INFO
    name = name if name else __name__

    _format = '[%(asctime)s] %(levelname)s %(message)s'
    formatter = logging.Formatter(_format)

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(formatter)

    fh = RotatingFileHandler('{}.log'.format(name), maxBytes=1024*1024, backupCount=5)
    fh.setLevel(logLevel)
    fh.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(logLevel)
    logger.addHandler(ch)
    logger.addHandler(fh)

    return logger


class AppGlobals(object):

    def __init__(self):
        from PyQt5.QtCore import QSettings
        boolean = lambda value: value if isinstance(value, bool) else value == 'true'
        self._conf = QSettings('Up1and', 'Tafor')
        self._debug = boolean(self._conf.value('General/Debug'))
        self._logger = createLogger(self._debug, name='tafor')

    @property
    def basedir(self):
        sysdir = os.path.abspath(os.path.dirname(sys.argv[0]))
        filedir = os.path.abspath(os.path.dirname(__file__))

        if os.path.exists(os.path.join(filedir, 'sounds')):
            return filedir

        return sysdir

    @property
    def conf(self):
        return self._conf

    @property
    def logger(self):
        return self._logger


_globals = AppGlobals()

root = _globals.basedir
conf = _globals.conf
logger = _globals.logger
