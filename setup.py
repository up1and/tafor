import os
import sys

from setuptools import setup, Command
from setuptools.command.test import test as TestCommand

from tafor import __version__


def fread(filepath):
    with open(filepath, encoding='utf-8', mode='r') as f:
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


class SphinxCommand(Command):
    user_options = []
    description = 'Build docs using Sphinx'

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        import subprocess
        source = os.path.abspath(os.path.dirname(__file__))
        outdir = os.path.join(source, 'docs', '_build', 'html')
        res = subprocess.call('sphinx-build -b html docs docs/_build/html', shell=True)
        if res:
            print('ERROR: sphinx-build exited with code {}'.format(res))
        else:
            print('Documentation created at {}.'.format(outdir))


class PyInstallerCommand(Command):
    user_options = []
    description = 'Build exe using PyInstaller'

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        import subprocess
        source = os.path.abspath(os.path.dirname(__file__))
        cwddir = os.path.join(source, 'tafor')
        proc = subprocess.Popen(r'pyinstaller __main__.py -w -F -i icons\icon.ico', cwd=cwddir, 
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
        while True:
            line = proc.stdout.readline()
            if not line:
                break
            print(line.decode('utf-8').strip())


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
    cmdclass = {'test': PyTest, 'docs': SphinxCommand, 'build_exe': PyInstallerCommand},
    platforms='any',
    )