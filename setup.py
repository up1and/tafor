import sys

from setuptools import setup
from setuptools.command.test import test as TestCommand

from tafor import __version__


def fread(filepath):
    with open(filepath, 'r') as f:
        return f.read()


class PyTest(TestCommand):

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = ['--cov=tafor']

    def run_tests(self):
        import pytest
        errno = pytest.main(self.test_args)
        if errno != 0:
            raise SystemExit(errno)


setup(
    name='tafor',
    version=__version__,
    url='https://github.com/up1and/tafor',
    author='up1and',
    author_email='piratecb@gmail.com',
    description='A Terminal Aerodrome Forecast Encoding Software',
    long_description=fread('README.md'),
    license='GPLv2',
    tests_require=['pytest'],
    cmdclass = {'test': PyTest},
    platforms='any',
    )