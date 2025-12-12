import os
import sys
import logging

from logging.handlers import RotatingFileHandler

from tafor.config import ConfigManager, ConfigRegistry

def setupLogging(debug=False, name='tafor'):
    logLevel = logging.DEBUG if debug else logging.INFO
    _format = '[%(asctime)s] %(levelname)s [%(name)s] %(message)s'
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

def basedir():
    sysdir = os.path.abspath(os.path.dirname(sys.argv[0]))
    filedir = os.path.abspath(os.path.dirname(__file__))

    if os.path.exists(os.path.join(filedir, 'sounds')):
        return filedir

    return sysdir

root = basedir()
manager = ConfigManager('Up1and', 'Tafor')
conf = ConfigRegistry(manager)

setupLogging(debug=conf.debugMode)
