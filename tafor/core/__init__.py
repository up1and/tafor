import os
import sys

def basedir():
    if hasattr(sys, '_MEIPASS'):
        return os.path.abspath(os.path.dirname(sys.argv[0]))

    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

root = basedir()
