import os
import sys
import datetime

from setuptools import setup, Command
from setuptools.command.test import test as TestCommand

from tafor import __version__
from tafor.utils import gitRevisionHash


def fread(filepath):
    with open(filepath, encoding='utf-8', mode='r') as f:
        return f.read()

def createEnviron(filedir):
    ghash = gitRevisionHash()
    text = 'ghash = "{}"'.format(ghash)
    filepath = os.path.join(filedir, '_environ.py')
    with open(filepath, encoding='utf-8', mode='w') as f:
        f.write(text)

def createVersion(filedir):
    templates = """VSVersionInfo(
      ffi=FixedFileInfo(
        filevers=({filevers}), 
        prodvers=({prodvers}),
        mask=0x3f, 
        flags=0x0,
        OS=0x4,
        fileType=0x1,
        subtype=0x0,
        date=(0, 0)
        ),
      kids=[
        StringFileInfo(
          [
          StringTable(
            u'040904b0', 
            [StringStruct(u'CompanyName', u'up1and'), 
            StringStruct(u'ProductName', u'Tafor'), 
            StringStruct(u'ProductVersion', u'{version}+{ghash}'),
            StringStruct(u'OriginalFilename', u'tafor.exe'), 
            StringStruct(u'FileVersion', u'{version}'), 
            StringStruct(u'FileDescription', u'A Terminal Aerodrome Forecast Encoding Software'), 
            StringStruct(u'LegalCopyright', u'Copyright (C) {year}, up1and'),])
          ]), 
        VarFileInfo([VarStruct(u'Translation', [2052, 1200])])
      ]
    )"""
    ghash = gitRevisionHash()
    versions = __version__.split('.')
    infos = []
    for i in range(4):
        if i < len(versions) and versions[i].isdigit():
            infos.append(versions[i])
        else:
            infos.append('0')

    prodvers = filevers = ', '.join(infos)
    year = datetime.datetime.now().year
    text = templates.format(filevers=filevers, prodvers=prodvers, 
        version=__version__, ghash=ghash, year=year)

    filepath = os.path.join(filedir, '.version')
    with open(filepath, encoding='utf-8', mode='w') as f:
        f.write(text)


class PyTest(TestCommand):

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = ['--cov=tafor', '--cov-report=term', '--cov-report=html']

    def run_tests(self):
        import pytest
        os.environ['TAFOR_ENV'] = 'TEST'
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
        createEnviron(cwddir)
        createVersion(cwddir)
        proc = subprocess.Popen(r'pyinstaller __main__.py -w -F -i icons\icon.ico -n tafor --version-file .version', cwd=cwddir, 
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
        while True:
            line = proc.stdout.readline()
            if not line:
                break
            print(line.decode('utf-8').strip())


class ZipCommand(Command):
    user_options = []
    description = 'Packaged zip files'

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        import zipfile

        bitness = 'amd64' if sys.maxsize > 2**32 else 'win32'
        filename = 'tafor-{version}-{bitness}.zip'.format(version=__version__, bitness=bitness)
        output = os.path.abspath(os.path.join('tafor/dist', filename))

        def zipdir(path, pack, extension=None):
            for root, dirs, files in os.walk(path):
                for file in files:
                    _, ext = os.path.splitext(file)
                    if extension and extension != ext:
                            continue

                    filename = os.path.join(root, file)
                    arcname = os.path.relpath(os.path.join(root, file), os.path.join(path, '..'))
                    pack.write(filename, arcname)

        with zipfile.ZipFile(output, 'w') as pack:
            pack.write(os.path.join('tafor/dist', 'tafor.exe'), 'tafor.exe')
            zipdir('tafor/sounds', pack)
            zipdir('tafor/i18n', pack, extension='.qm')

        print('Output', output)


setup(
    name='tafor',
    version=__version__,
    url='https://github.com/up1and/tafor',
    author='up1and',
    author_email='piratecb@gmail.com',
    description='A Terminal Aerodrome Forecast Encoding Software',
    long_description=fread('README.md'),
    license='GPLv2',
    keywords = 'aviation taf sigmet',
    tests_require=['pytest'],
    cmdclass ={'test': PyTest, 'docs': SphinxCommand, 'build_exe': PyInstallerCommand, 'zip': ZipCommand},
    platforms=['Windows', 'Linux', 'Mac OS-X'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Intended Audience :: Other Audience',
        'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
        'Operating System :: MacOS',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: Scientific/Engineering',
      ],
    entry_points={
        'gui_scripts': [
            'tafor = tafor.app:main',
        ],
    },
)