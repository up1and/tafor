import sys

from setuptools import setup
from setuptools.command.test import test as TestCommand


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
    tests_require=['pytest'],
    cmdclass = {'test': PyTest},
    )