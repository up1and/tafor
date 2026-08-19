import os
import sys

from tafor.core.config import ConfigManager, ConfigRegistry

def basedir():
    if hasattr(sys, '_MEIPASS'):
        return os.path.abspath(os.path.dirname(sys.argv[0]))

    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

root = basedir()
manager = ConfigManager('Up1and', 'Tafor')
conf = ConfigRegistry(manager)
