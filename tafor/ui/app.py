"""Application entry point and composition root.

This is the only module that knows how the pieces fit together. It builds the
runtime, creates the window, hands each presenter the collaborators it needs,
and drives the app through one lifecycle: initialize() every presenter in
order, then run.

Nothing here holds a business rule, and nothing here reaches into anything.
The window is a passive view, the presenters own the behaviour, the core owns
the rules.
"""

import json
import logging
import os
import sys

from PyQt5.QtCore import QLocale, QT_VERSION_STR, Qt, QTranslator
from PyQt5.QtGui import QGuiApplication
from PyQt5.QtNetwork import QLocalServer, QLocalSocket
from PyQt5.QtWidgets import QApplication, QStyleFactory

from tafor import root
from tafor.core.config import createConfig
from tafor.core.models import createDatabase
from tafor.core.repositories import Repositories
from tafor.core.states import createContext
from tafor.core.utils.common import appInfo, setupLogging
from tafor.ui.fonts import uiFont
from tafor.ui.main import (MainWindow, BoardPresenter, LayerPresenter, LicensePresenter,
    MessagePresenter, NotificationPresenter, ReminderPresenter, SoundPresenter, UpgradePresenter)
from tafor.ui.workers import ContextBridge, RpcWorker, threadManager

logger = logging.getLogger('tafor.main')


class Runtime:
    """Everything main() needs before a QApplication exists.

    Deliberately Qt-light: createRuntime() can be exercised without a display,
    which is not true of anything downstream of it.
    """

    def __init__(self, conf, context, database, repositories, bridge):
        self.conf = conf
        self.context = context
        self.database = database
        self.repositories = repositories
        self.bridge = bridge


def createRuntime():
    """Build the config, the context, the database and the bridge.

    The repositories are built here and shared, so the window and the
    presenters query the same set -- no second set appears by accident.
    """
    conf = createConfig()
    setupLogging(debug=conf.debugMode)

    context = createContext(conf)
    database = createDatabase()

    return Runtime(
        conf=conf,
        context=context,
        database=database,
        repositories=Repositories(database),
        bridge=ContextBridge(context),
    )


class SingleInstance:
    """Guards a single running copy through a named local socket.

    A context manager, so the socket is released on every exit path including
    the ones that raise. A copy that crashed leaves its socket file behind on
    Unix, so listen() is retried once after clearing it. The previous
    implementation ignored listen()'s return value and tried to refuse the
    second copy with quit() before exec(), which does nothing.
    """

    def __init__(self, name):
        self.name = name
        self.socket = QLocalSocket()
        self.server = QLocalServer()
        self.acquired = False

    def __enter__(self):
        self.socket.connectToServer(self.name)
        if self.socket.waitForConnected(500):
            return self                                 # another copy is up

        if not self.server.listen(self.name):
            self.server.removeServer(self.name)
            if not self.server.listen(self.name):
                raise RuntimeError('Cannot listen on {}, {}'.format(
                    self.name, self.server.errorString()))

        self.acquired = True
        return self

    def __exit__(self, *exc):
        self.socket.close()
        self.server.close()
        return False


class WorkerPool:
    """Thin wrapper over the shared thread manager.

    Wrapping it keeps the module-level singleton out of the presenters, so a
    test can hand in a pool that runs everything inline.
    """

    def __init__(self, manager=None):
        self.manager = manager or threadManager

    def create(self, workerClass, *args, workerId=None, reusable=False, **kwargs):
        return self.manager.createWorker(
            workerClass, *args, workerId=workerId, reusable=reusable, **kwargs
        )

    def cleanup(self):
        self.manager.cleanup()


class Application:
    """The running app: one window, one worker pool, a set of presenters.

    One initialize() call per presenter, then the event loop. There is no
    matching stop() pass: nothing a presenter acquires outlives the process,
    so shutdown only releases the two things that own real resources -- the
    windows and the worker threads.
    """

    def __init__(self, runtime, app):
        self.runtime = runtime
        self.app = app
        self.rpc = None
        self.workers = WorkerPool()
        self.window = MainWindow(runtime.conf, runtime.context, runtime.repositories)
        self.presenters = [
            ReminderPresenter(self.window, self.runtime.context, self.runtime.conf),
            MessagePresenter(self.window, self.runtime.context, self.runtime.conf, self.runtime.repositories, self.workers, self.runtime.bridge),
            NotificationPresenter(self.window, self.runtime.context, self.runtime.repositories),
            BoardPresenter(self.window, self.runtime.context, self.runtime.conf, self.runtime.repositories),
            SoundPresenter(self.window, self.runtime.context, self.runtime.conf),
            LayerPresenter(self.window, self.runtime.context, self.runtime.conf, self.workers, self.runtime.bridge),
            LicensePresenter(self.window, self.runtime.context),
            UpgradePresenter(self.window, self.workers)
        ]

    def start(self):
        self.window.show()
        for presenter in self.presenters:
            presenter.initialize()
        self.startRpc()

    def shutdown(self):
        """Deliberately small. Timers and subscriptions die with the process,
        so the only things worth doing by hand are the two that own real
        resources: the windows and the worker threads."""
        self.window.hideTray()
        self.window.closeDialogs()
        self.workers.cleanup()

    def startRpc(self):
        """The optional HTTP entry point, sharing the same bridge."""
        if not self.runtime.conf.rpc:
            return

        from tafor.core.rpc import create_app

        server = create_app(
            context=self.runtime.bridge,
            engine=self.runtime.database.engine,
            conf=self.runtime.conf,
        )
        self.rpc, thread = self.workers.create(
            RpcWorker, server, workerId='rpc', reusable=True
        )
        thread.start()


def configureHighDpi(conf):
    """High-DPI policy has to be set before the QApplication exists."""
    os.environ['QT_ENABLE_HIGHDPI_SCALING'] = '1'
    os.environ['QT_SCALE_FACTOR_ROUNDING_POLICY'] = 'PassThrough'

    scale = int(conf.interfaceScaling or 0)
    if scale:
        os.environ['QT_SCALE_FACTOR'] = str(scale * 0.25 + 1)

    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )


def installTranslations(app):
    """Load the .qm for the system locale, when one ships with the build."""
    translator = QTranslator(app)
    locale = QLocale.system().name()
    path = os.path.join(root, 'resources', 'i18n', '{}.qm'.format(locale))
    if translator.load(path):
        app.installTranslator(translator)


def applyStyle(app, conf):
    if conf.windowsStyle == 'Fusion':
        app.setStyle(QStyleFactory.create('Fusion'))


def main(argv=None):
    """Run the app and return its exit code."""
    argv = list(sys.argv if argv is None else argv)

    runtime = createRuntime()
    configureHighDpi(runtime.conf)

    # The child process re-reads these when it restarts itself
    os.environ['TAFOR_ARGS'] = json.dumps(argv[1:])

    app = QApplication(argv)
    app.setFont(uiFont(pointSize=9))
    installTranslations(app)
    applyStyle(app, runtime.conf)

    versions = appInfo(qt=QT_VERSION_STR)
    logger.info(
        'Version {version}+{revision}, Python {python} {machine}, '
        'Qt {qt} on {system} {release}'.format(**versions)
    )

    with SingleInstance('Tafor') as guard:
        if not guard.acquired:
            logger.info('Another instance is already running, exiting.')
            return 0

        application = Application(runtime, app)
        application.start()
        try:
            return app.exec()
        finally:
            application.shutdown()


def run(argv=None):
    """Entry point for tafor/__main__.py.

    The one broad catch in the program, and it sits at the very top on
    purpose: a startup failure becomes exit code 1 plus a traceback in the
    log, instead of the old behaviour where a failed start still exited 0 and
    looked like success to whatever launched it.
    """
    try:
        return main(argv)
    except Exception:
        logger.exception('On startup failed')
        return 1


if __name__ == '__main__':
    sys.exit(run())
