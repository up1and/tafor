# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build script for tafor.

This file is the build, not a build artefact: it is checked in and edited by
hand. build.py only produces the two inputs PyInstaller cannot derive on its
own -- tafor/revision.py and .version -- and then hands this file over, so
every rule about what ends up inside tafor.exe lives here.

Qt ships far more than a widgets application loads: a QML engine, ANGLE's
software rasteriser, a dozen image codecs and 47 translation catalogues.
PyInstaller's hooks collect them because the binaries sit next to the ones we
do need, not because anything imports them. Each table below is an explicit
allow-list or deny-list, so that a Qt upgrade shows up as a diff here rather
than as a silent size increase in the artefact.

A command line switch reaches this file as an environment variable: PyInstaller
executes the spec in a process of its own, so the environment is the only
channel that survives, and build.py writes the variables below from its own
command line. The names are the contract between the two files.
"""

import os

# PyInstaller defines SPECPATH as the directory holding this file.
SOURCE = SPECPATH

ENTRY = os.path.join(SOURCE, 'tafor', '__main__.py')
SHAPES = os.path.join(SOURCE, 'tafor', 'resources', 'shapes')
ICONS = os.path.join(SOURCE, 'tafor', 'resources', 'icons')
ICON = os.path.join(ICONS, 'icon.ico')
VERSION_INFO = os.path.join(SOURCE, '.version')

#: Qt DLLs nothing in tafor reaches. The ANGLE pair and d3dcompiler are the
#: shader compiler and ES runtime Qt would use to emulate OpenGL on top of
#: Direct3D; the QML engine is 8 MB of interpreter the project has no .qml
#: files for.
#:
#: The OpenSSL pair is Qt's own copy, 3.7 MB of it, collected only because it
#: sits in Qt's bin directory. Nothing links against it: pefile finds no import
#: of it in any bundled binary, and the name appears as a string in
#: Qt5Network.dll alone, which loads it with QLibrary the moment a QSslSocket
#: is created. tafor never creates one -- Qt networking here is QLocalServer
#: and QLocalSocket, and every URL goes to QDesktopServices -- while the HTTP
#: client is `requests`, whose TLS comes from Python's own OpenSSL 3
#: (libssl-3-x64.dll / libcrypto-3-x64.dll, both kept). Dropping the pair
#: costs Qt TLS and nothing else.
EXCLUDED_BINARIES = (
    'd3dcompiler_47.dll',       # 4.0 MB ANGLE shader compiler
    'libGLESv2.dll',            # 3.2 MB ANGLE ES runtime
    'libEGL.dll',               # 0.02 MB ANGLE entry point
    'Qt5Quick.dll',             # 4.0 MB QML -- the project has no .qml files
    'Qt5Qml.dll',               # 3.4 MB QML engine
    'Qt5QmlModels.dll',         # 0.4 MB QML models
    'Qt5DBus.dll',              # 0.4 MB unused on Windows
    'Qt5WebSockets.dll',        # 0.1 MB unused
    'libssl-1_1-x64.dll',       # 0.6 MB Qt's OpenSSL, TLS only
    'libcrypto-1_1-x64.dll',    # 3.1 MB
)

#: Binaries the default build drops but a build can ask back, paired with the
#: environment variable that asks. opengl32sw is the software rasteriser Qt
#: falls back to when no GPU driver is usable: MapView is a plain QGraphicsView
#: on the raster viewport, so it is never selected, but it is the one exclusion
#: a host without a working driver can feel, which is what the escape hatch is
#: for. Adding another is one entry here and one switch in build.py.
RESTORABLE_BINARIES = (
    ('opengl32sw.dll', 'KEEP_OPENGL32SW'),
)

#: Python-side counterpart of the two tables above: the bindings whose DLLs are
#: dropped. PyQt5's hooks drag in whatever a stray import reaches, so the pair
#: is kept in step -- if one of these ever becomes reachable, the build fails
#: on a missing module instead of shipping a half-pruned Qt.
EXCLUDED_MODULES = (
    'PyQt5.QtQml',
    'PyQt5.QtQuick',
    'PyQt5.QtQuickWidgets',
    'PyQt5.QtWebSockets',
    'PyQt5.QtDBus',
)

#: Qt plugins, keeping only the backends the application actually loads. Qt
#: picks these at runtime by scanning the plugin directory, so this list is the
#: whole contract -- anything missing here is missing from the built
#: application, with no import error to warn you.
#:
#: Two deliberate whole-group entries. The image codecs all stay because map
#: backgrounds arrive as raw bytes from the layer service, so the format is the
#: server's choice and not something this codebase can pin down. The audio pair
#: stays because which backend Qt prefers depends on the host.
#:
#: Note there is deliberately no sqldrivers entry: the database goes through
#: SQLAlchemy onto the standard library's sqlite3, so Qt's own SQL layer is
#: never loaded and its driver plugin is never collected either.
REQUIRED_PLUGIN_GROUPS = (
    'imageformats/',
)

REQUIRED_PLUGINS = (
    'platforms/qwindows.dll',               # without this nothing renders at all
    'styles/qwindowsvistastyle.dll',        # native widget style
    'iconengines/qsvgicon.dll',             # icons are PNG through QIcon
    'printsupport/windowsprintersupport.dll',  # QPrintDialog in the sender
    'mediaservice/qtmedia_audioengine.dll',    # QSoundEffect
    'audio/qtaudio_wasapi.dll',
    'audio/qtaudio_windows.dll',
)

#: Datas that the hooks over-collect. pyproj ships its Cython sources next to
#: the compiled modules and the hook copies the lot; none of it is read at
#: runtime, since only the compiled .pyd files are imported.
EXCLUDED_DATA_SUFFIXES = (
    '.c', '.pyx', '.pyi', '.pxd', '.pxi',
)

#: Directories whose entire contents are dropped, matched as path prefixes on
#: the archive-relative path so that a single entry cannot catch a sibling by
#: accident.
EXCLUDED_DATA_DIRS = ()

EXCLUDED_DATA_NAMES = (
    'translations',             # Qt's own catalogues; tafor has resources/i18n
    'qsci',                     # QScintilla, never imported
)


def requested(variable):
    """True when the build asked for this deviation from the default.

    build.py writes every switch it knows about, either way, so an empty or
    unset variable means the default build rather than an unmanaged shell.
    """
    return os.environ.get(variable, '').strip().lower() not in ('', '0', 'false', 'no')


a = Analysis(
    [ENTRY],
    pathex=[],
    binaries=[],
    datas=[(SHAPES, 'shapes'), (ICONS, 'resources/icons')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=list(EXCLUDED_MODULES),
    noarchive=False,
    optimize=0,
)

# `Analysis` gives no declarative way to say "collect these binaries except
# those", so the filtering happens here, in the spec's own namespace, on the
# lists it has just produced.


def prune_binaries(toc):
    dropped = set(EXCLUDED_BINARIES)
    dropped.update(name for name, variable in RESTORABLE_BINARIES
                   if not requested(variable))
    kept = []
    for dest, src, kind in toc:
        if os.path.basename(dest) in dropped:
            continue
        kept.append((dest, src, kind))
    return kept


def prune_plugins(toc):
    """Drop every Qt plugin except the ones Qt is told to load.

    Plugins are picked up by directory walk, and their dest path is always
    PyQt5/Qt5/plugins/<category>/<name>.dll, so the relative path is what the
    allow-list is expressed in. A group entry keeps a whole category.
    """
    kept = []
    for dest, src, kind in toc:
        parts = dest.replace('\\', '/').split('/')
        if 'plugins' not in parts:
            kept.append((dest, src, kind))
            continue
        index = parts.index('plugins')
        relative = '/'.join(parts[index + 1:])
        if relative in REQUIRED_PLUGINS:
            kept.append((dest, src, kind))
        elif any(relative.startswith(g) for g in REQUIRED_PLUGIN_GROUPS):
            kept.append((dest, src, kind))
    return kept


def prune_datas(toc):
    """Drop Qt's translation catalogues and the Cython sources pyproj ships.

    The matches are on the archive-relative path, so a name match is a whole
    path segment and cannot catch a file that merely contains the substring.
    """
    kept = []
    for dest, src, kind in toc:
        relative = dest.replace('\\', '/')
        parts = relative.split('/')
        if any(name in parts for name in EXCLUDED_DATA_NAMES):
            continue
        if any(relative.startswith(d + '/') for d in EXCLUDED_DATA_DIRS):
            continue
        if os.path.splitext(dest)[1].lower() in EXCLUDED_DATA_SUFFIXES:
            continue
        kept.append((dest, src, kind))
    return kept


a.binaries = prune_plugins(prune_binaries(a.binaries))
a.datas = prune_datas(a.datas)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='tafor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version=VERSION_INFO,
    icon=[ICON],
)
