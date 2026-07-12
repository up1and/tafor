import os
import platform
import datetime

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


def run():
    import subprocess
    source = os.path.abspath(os.path.dirname(__file__))
    src = os.path.join(source, 'tafor')
    writeRevision(src)
    writeVersionInfo(source)
    command = (
        r'pyinstaller {src}//__main__.py -w -F'
        r' -i {src}//resources//icons//icon.ico --add-data {src}//resources//shapes;shapes -n tafor --version-file {source}//.version'
        r' --specpath {source} --distpath {source}//dist --workpath {source}//build'
        ).format(src=src, source=source)
    proc = subprocess.Popen(command, cwd=src, 
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
    while True:
        line = proc.stdout.readline()
        if not line:
            break
        print(line.decode('utf-8').strip())

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
    run()
