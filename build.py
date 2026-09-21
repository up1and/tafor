"""Build tafor into tafor.exe and a release archive.

The packaging rules -- what is pruned, what is kept -- live in build.spec, which
is checked in and edited by hand. This script produces the two inputs
PyInstaller cannot derive on its own (tafor/revision.py and .version), turns the
command line into the environment variable build.spec reads back, and runs
PyInstaller on it.
"""
import os
import sys
import datetime
import platform
import subprocess

from tafor import __version__
from tafor.core.utils.common import gitRevisionHash


def writeRevision(filedir):
    hash = gitRevisionHash()
    text = 'hash = "{}"'.format(hash)
    filepath = os.path.join(filedir, 'revision.py')
    with open(filepath, encoding='utf-8', mode='w') as f:
        f.write(text)

def writeVersionInfo(filedir):
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
            StringStruct(u'ProductVersion', u'{version}+{hash}'),
            StringStruct(u'OriginalFilename', u'tafor.exe'), 
            StringStruct(u'FileVersion', u'{version}'), 
            StringStruct(u'FileDescription', u'A Terminal Aerodrome Forecast Encoding Software'), 
            StringStruct(u'LegalCopyright', u'Copyright (C) {year}, up1and'),])
          ]), 
        VarFileInfo([VarStruct(u'Translation', [2052, 1200])])
      ]
    )"""
    hash = gitRevisionHash()
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
        version=__version__, hash=hash, year=year)

    filepath = os.path.join(filedir, '.version')
    with open(filepath, encoding='utf-8', mode='w') as f:
        f.write(text)


def main():
    # The one switch is `--keep-opengl32sw`. It is matched by name rather than
    # as a literal argv entry so that the dashes and the underscore spelling
    # cannot diverge, which is a mistake with no symptom: the build runs to
    # completion and quietly produces the default bundle.
    args = [a.lstrip('-').replace('_', '-') for a in sys.argv[1:]]
    opengl32sw = 'keep-opengl32sw' in args

    source = os.path.abspath(os.path.dirname(__file__))
    writeRevision(os.path.join(source, 'tafor'))
    writeVersionInfo(source)

    # PyInstaller runs the spec in a process of its own, so the environment is
    # the only channel that reaches it. The name is the contract with
    # build.spec, and the value is written either way, so that a build never
    # depends on what the caller's shell happened to have exported.
    env = os.environ.copy()
    env['KEEP_OPENGL32SW'] = '1' if opengl32sw else '0'
    print('KEEP_OPENGL32SW =', env['KEEP_OPENGL32SW'], '(argv: %r)' % args)

    # Resolve PyInstaller from the running interpreter rather than PATH: the
    # build is started by whichever python is active, and `pyinstaller` is only
    # on PATH by accident (uv run, an activated venv), not by contract.
    pyinstaller = os.path.join(os.path.dirname(sys.executable), 'pyinstaller.exe')
    if not os.path.exists(pyinstaller):
        pyinstaller = 'pyinstaller'

    command = [pyinstaller, os.path.join(source, 'build.spec'), '-y',
               '--distpath', os.path.join(source, 'dist'),
               '--workpath', os.path.join(source, 'build')]
    proc = subprocess.Popen(command, cwd=source, env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    for line in iter(proc.stdout.readline, b''):
        print(line.decode('utf-8', errors='replace').rstrip())

    proc.wait()

    if os.path.exists(os.path.join(source, 'dist', 'tafor.exe')):
        package()

def package():
    import zipfile

    source = os.path.abspath(os.path.dirname(__file__))
    machine = platform.machine().lower()
    filename = 'tafor-{version}-{machine}.zip'.format(version=__version__, machine=machine)
    output = os.path.abspath(os.path.join(source, 'dist', filename))

    def zipdir(path, package, extension=None):
        for root, dirs, files in os.walk(path):
            for file in files:
                _, ext = os.path.splitext(file)
                if extension and extension != ext:
                        continue

                filename = os.path.join(root, file)
                arcname = os.path.relpath(os.path.join(root, file), os.path.join(path, '..'))
                package.write(filename, arcname)

    with zipfile.ZipFile(output, 'w') as package:
        package.write(os.path.join(source, 'dist', 'tafor.exe'), 'tafor.exe')
        zipdir(os.path.join(source, 'tafor', 'resources', 'sounds'), package)
        zipdir(os.path.join(source, 'tafor', 'resources', 'i18n'), package, extension='.qm')

    print('Output', output)


if __name__ == '__main__':
    main()
