"""Tests for the application entry point.

tafor/ui/app.py is the composition root: it builds the runtime, hands each
presenter its collaborators and drives one lifecycle. Everything downstream of
the QApplication -- the window, the presenters, the worker pool, the event loop
-- is replaced with recording doubles, so the wiring and the ordering are
asserted directly instead of through a real GUI.
"""
import os
import sys
import json
import logging

from types import SimpleNamespace

import pytest

from tafor.core.config import createConfig
from tafor.core.repositories import Repositories
from tafor.ui import app as app_module
from tafor.ui.app import (
    Application,
    Runtime,
    SingleInstance,
    WorkerPool,
    applyStyle,
    configureHighDpi,
    createRuntime,
    installTranslations,
    main,
    run,
)
from tafor.ui.workers import ContextBridge, threadManager
from tests.mocks import MockConfig


# The presenters Application builds, in the order it builds them.
PRESENTERS = [
    'ReminderPresenter',
    'MessagePresenter',
    'NotificationPresenter',
    'BoardPresenter',
    'SoundPresenter',
    'LayerPresenter',
    'LicensePresenter',
    'UpgradePresenter',
]


@pytest.fixture
def conf():
    """A private config: these tests flip rpc/debug and must not leak into the
    session-scoped one the rest of the suite shares."""
    return createConfig(settings=MockConfig())


class PresenterDouble:
    """A presenter stand-in: records how it was built and when it was started."""

    def __init__(self, role, args, kwargs, order):
        self.role = role
        self.args = args
        self.kwargs = kwargs
        self.initialized = 0
        self.order = order

    def initialize(self):
        self.initialized += 1
        self.order.append(self.role)


class FakeWindow:
    """The MainWindow, reduced to the three methods Application calls."""

    def __init__(self, *args):
        self.args = args
        self.shown = 0
        self.trayHidden = 0
        self.dialogsClosed = 0

    def show(self):
        self.shown += 1

    def hideTray(self):
        self.trayHidden += 1

    def closeDialogs(self):
        self.dialogsClosed += 1


class FakeSignal:
    """A pyqtSignal reduced to connect()"""

    def __init__(self):
        self.targets = []

    def connect(self, target):
        self.targets.append(target)


class FakeWorker:
    """Worker double with the members the transmission assembly touches."""

    error = ''

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.done = FakeSignal()
        self.stopped = 0

    def transmit(self, *args):
        pass

    def prepare(self):
        pass

    def stop(self):
        self.stopped += 1


class FakeThread:
    def __init__(self):
        self.started = 0
        self.running = False

    def isRunning(self):
        return self.running

    def start(self):
        self.started += 1
        self.running = True


class FakePool:
    """A WorkerPool that hands back inert workers and records the request."""

    def __init__(self):
        self.created = []
        self.cleaned = 0

    def create(self, workerClass, *args, **kwargs):
        worker, thread = FakeWorker(*args, **kwargs), FakeThread()
        self.created.append(SimpleNamespace(
            workerClass=workerClass, args=args, kwargs=kwargs,
            worker=worker, thread=thread))
        return worker, thread

    def cleanup(self):
        self.cleaned += 1


class FakeGuard:
    """The SingleInstance context manager, with the answer handed in."""

    def __init__(self, name, acquired=True):
        self.name = name
        self.acquired = acquired

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeQApplication:
    """The QApplication, reduced to what main() touches."""

    instances = []
    execResult = 0

    def __init__(self, argv):
        self.argv = argv
        self.font = None
        self.style = None
        self.executed = 0
        FakeQApplication.instances.append(self)

    def setFont(self, font):
        self.font = font

    def installTranslator(self, translator):
        pass

    def setStyle(self, style):
        self.style = style

    def exec(self):
        self.executed += 1
        return FakeQApplication.execResult


class FakeRunningApplication:
    """The Application, reduced to start()/shutdown()."""

    instances = []

    def __init__(self, runtime, app):
        self.runtime = runtime
        self.app = app
        self.started = 0
        self.shutdowns = 0
        FakeRunningApplication.instances.append(self)

    def start(self):
        self.started += 1

    def shutdown(self):
        self.shutdowns += 1


def installPresenters(monkeypatch, roles):
    """Replace every presenter class in app's namespace with a factory that
    records what it was handed and the order it was initialized in."""
    byRole = {}
    order = []

    for role in roles:
        byRole[role] = []

        def factory(*args, _role=role, _bucket=byRole[role], **kwargs):
            instance = PresenterDouble(_role, args, kwargs, order)
            _bucket.append(instance)
            return instance

        monkeypatch.setattr(app_module, role, factory)

    return SimpleNamespace(byRole=byRole, order=order)


class TestCreateRuntime:
    """createRuntime() is Qt-light on purpose: it can be exercised headless."""

    @pytest.fixture
    def stubs(self, monkeypatch, conf, database):
        calls = {'logging': []}
        monkeypatch.setattr(app_module, 'createConfig', lambda: conf)
        monkeypatch.setattr(app_module, 'createDatabase', lambda: database)
        monkeypatch.setattr(app_module, 'setupLogging',
                            lambda debug=False: calls['logging'].append(debug))
        return calls

    def test_builds_every_collaborator(self, stubs, conf, database):
        runtime = createRuntime()

        assert isinstance(runtime, Runtime)
        assert runtime.conf is conf
        assert runtime.database is database
        assert isinstance(runtime.repositories, Repositories)
        assert isinstance(runtime.bridge, ContextBridge)
        assert runtime.bridge.context is runtime.context

    def test_the_repositories_share_the_one_database(self, stubs, database):
        """No second set appears by accident."""
        runtime = createRuntime()

        assert runtime.repositories.taf.database is database
        assert runtime.repositories.metar.database is database
        assert runtime.repositories.sigmet.database is database
        assert runtime.repositories.message.database is database

    def test_logging_follows_the_debug_flag(self, stubs, conf):
        createRuntime()

        assert stubs['logging'] == [conf.debugMode]


class TestSingleInstance:

    @pytest.fixture
    def name(self, request):
        # One socket name per test, so a leaked server cannot leak across them
        return 'TaforTest-{}'.format(request.node.name)

    def test_a_free_name_is_acquired(self, name):
        with SingleInstance(name) as guard:
            assert guard.acquired is True

    def test_a_second_copy_does_not_acquire(self, name):
        with SingleInstance(name) as first:
            assert first.acquired is True

            with SingleInstance(name) as second:
                assert second.acquired is False

    def test_the_name_is_released_on_exit(self, name):
        with SingleInstance(name) as first:
            assert first.acquired is True

        with SingleInstance(name) as again:
            assert again.acquired is True

    def test_a_dead_listen_raises_instead_of_running_twice(self, name):
        guard = SingleInstance(name)
        guard.server.listen = lambda name: False
        guard.server.errorString = lambda: 'name in use'

        with pytest.raises(RuntimeError, match='Cannot listen on'):
            guard.__enter__()

    def test_exit_closes_the_server(self, name):
        guard = SingleInstance(name)
        guard.__enter__()

        guard.__exit__(None, None, None)

        assert guard.server.isListening() is False


class TestWorkerPool:

    def test_defaults_to_the_shared_thread_manager(self):
        assert WorkerPool().manager is threadManager

    def test_create_delegates_to_the_manager(self):
        calls = []
        manager = SimpleNamespace(
            createWorker=lambda *args, **kwargs: calls.append((args, kwargs)) or ('w', 't'))
        pool = WorkerPool(manager)

        result = pool.create('Worker', 1, 2, workerId='x', reusable=True, extra=3)

        assert result == ('w', 't')
        assert calls == [(('Worker', 1, 2), {'workerId': 'x', 'reusable': True, 'extra': 3})]

    def test_cleanup_delegates_to_the_manager(self):
        cleaned = []
        pool = WorkerPool(SimpleNamespace(cleanup=lambda: cleaned.append(True)))

        pool.cleanup()

        assert cleaned == [True]


class TestApplication:

    @pytest.fixture
    def doubles(self, monkeypatch):
        windows = []
        pools = []

        def buildWindow(*args):
            windows.append(FakeWindow(*args))
            return windows[-1]

        def buildPool(*args, **kwargs):
            pools.append(FakePool())
            return pools[-1]

        monkeypatch.setattr(app_module, 'MainWindow', buildWindow)
        monkeypatch.setattr(app_module, 'WorkerPool', buildPool)
        presenters = installPresenters(monkeypatch, PRESENTERS)

        return SimpleNamespace(windows=windows, pools=pools,
                               byRole=presenters.byRole, order=presenters.order)

    @pytest.fixture
    def runtime(self, conf, context, database):
        return SimpleNamespace(
            conf=conf,
            context=context,
            database=database,
            repositories=Repositories(database),
            bridge=ContextBridge(context),
        )

    @pytest.fixture
    def application(self, runtime, doubles):
        return Application(runtime, 'app')

    def test_the_window_gets_the_shared_collaborators(self, application, runtime):
        assert application.window.args == (runtime.conf, runtime.context, runtime.repositories)

    def test_one_presenter_per_concern(self, application):
        assert [p.role for p in application.presenters] == PRESENTERS

    def test_presenters_get_their_collaborators(self, application, runtime, doubles):
        window, workers = application.window, application.workers

        assert doubles.byRole['ReminderPresenter'][0].args == (window, runtime.context, runtime.conf)
        assert doubles.byRole['MessagePresenter'][0].args == (
            window, runtime.context, runtime.conf, runtime.repositories, workers, runtime.bridge)
        assert doubles.byRole['NotificationPresenter'][0].args == (
            window, runtime.context, runtime.repositories)
        assert doubles.byRole['BoardPresenter'][0].args == (
            window, runtime.context, runtime.conf, runtime.repositories)
        assert doubles.byRole['SoundPresenter'][0].args == (window, runtime.context, runtime.conf)
        assert doubles.byRole['LayerPresenter'][0].args == (
            window, runtime.context, runtime.conf, workers, runtime.bridge)
        assert doubles.byRole['LicensePresenter'][0].args == (window, runtime.context)
        assert doubles.byRole['UpgradePresenter'][0].args == (window, workers)

    def test_start_shows_the_window_then_initializes_every_presenter(self, application, doubles):
        application.start()

        assert application.window.shown == 1
        assert [p.initialized for p in application.presenters] == [1] * len(PRESENTERS)

    def test_start_initializes_in_the_declared_order(self, application, doubles):
        application.start()

        assert doubles.order == PRESENTERS

    def test_shutdown_releases_the_two_real_resources(self, application):
        application.shutdown()

        assert application.window.trayHidden == 1
        assert application.window.dialogsClosed == 1
        assert application.workers.cleaned == 1

    def test_start_creates_the_transmission_line_first(self, application, runtime):
        application.start()

        request = application.workers.created[0]
        assert request.workerClass is app_module.TransmissionWorker
        assert request.kwargs == {'workerId': 'transmission', 'reusable': True}
        assert isinstance(runtime.context.transmission, app_module.TransmissionQueue)
        assert request.thread.started == 1

    def test_shutdown_stops_the_transmission_before_cleanup(self, application, runtime):
        application.start()
        application.shutdown()

        request = application.workers.created[0]
        assert request.worker.stopped == 1
        assert application.workers.cleaned == 1

    def test_start_rpc_does_nothing_when_disabled(self, application, runtime, monkeypatch):
        runtime.conf.rpc = False
        monkeypatch.setattr('tafor.core.rpc.create_app', pytest.fail)

        application.startRpc()

        assert application.rpc is None
        assert application.workers.created == []

    def test_start_rpc_serves_the_bridge_on_a_reusable_worker(self, application, runtime, monkeypatch):
        runtime.conf.rpc = True
        server = object()
        captured = {}
        monkeypatch.setattr('tafor.core.rpc.create_app',
                            lambda **kwargs: captured.update(kwargs) or server)

        application.startRpc()

        assert captured == {
            'context': runtime.bridge,
            'engine': runtime.database.engine,
            'conf': runtime.conf,
        }

        request = application.workers.created[0]
        assert request.workerClass is app_module.RpcWorker
        assert request.args == (server,)
        assert request.kwargs == {'workerId': 'rpc', 'reusable': True}
        assert application.rpc is request.worker
        assert request.thread.started == 1


class TestConfigureHighDpi:

    def test_enables_high_dpi_scaling(self, conf, monkeypatch):
        monkeypatch.delenv('QT_SCALE_FACTOR', raising=False)
        monkeypatch.setenv('QT_ENABLE_HIGHDPI_SCALING', 'old')
        monkeypatch.setenv('QT_SCALE_FACTOR_ROUNDING_POLICY', 'old')
        conf.interfaceScaling = 0

        configureHighDpi(conf)

        assert os.environ['QT_ENABLE_HIGHDPI_SCALING'] == '1'
        assert os.environ['QT_SCALE_FACTOR_ROUNDING_POLICY'] == 'PassThrough'
        # No scaling chosen, so Qt's own default factor is left alone
        assert 'QT_SCALE_FACTOR' not in os.environ

    def test_a_chosen_scale_sets_the_factor(self, conf, monkeypatch):
        monkeypatch.delenv('QT_SCALE_FACTOR', raising=False)
        conf.interfaceScaling = 4

        configureHighDpi(conf)

        assert os.environ['QT_SCALE_FACTOR'] == '2.0'


class FakeTranslator:

    def __init__(self, found=True):
        self.found = found
        self.loaded = None

    def load(self, path):
        self.loaded = path
        return self.found


class TestInstallTranslations:

    @pytest.fixture
    def locale(self, monkeypatch):
        monkeypatch.setattr(app_module, 'QLocale', SimpleNamespace(
            system=lambda: SimpleNamespace(name=lambda: 'en_US')))
        monkeypatch.setattr(app_module, 'root', '/root')

    def test_a_shipped_translation_is_installed(self, locale, monkeypatch):
        translator = FakeTranslator()
        monkeypatch.setattr(app_module, 'QTranslator', lambda app: translator)
        installed = []
        app = SimpleNamespace(installTranslator=installed.append)

        installTranslations(app)

        assert translator.loaded == os.path.join('/root', 'resources', 'i18n', 'en_US.qm')
        assert installed == [translator]

    def test_a_missing_translation_is_not_installed(self, locale, monkeypatch):
        monkeypatch.setattr(app_module, 'QTranslator', lambda app: FakeTranslator(found=False))
        installed = []
        app = SimpleNamespace(installTranslator=installed.append)

        installTranslations(app)

        assert installed == []


class FakeStyledApplication:

    def __init__(self):
        self.style = None

    def setStyle(self, style):
        self.style = style


class TestApplyStyle:

    @pytest.fixture
    def app(self):
        return FakeStyledApplication()

    def test_fusion_is_applied(self, conf, app, monkeypatch):
        conf.windowsStyle = 'Fusion'
        monkeypatch.setattr(app_module, 'QStyleFactory',
                            SimpleNamespace(create=lambda name: 'style:{}'.format(name)))

        applyStyle(app, conf)

        assert app.style == 'style:Fusion'

    def test_any_other_style_is_left_to_qt(self, conf, app):
        conf.windowsStyle = 'System'

        applyStyle(app, conf)

        assert app.style is None


class TestMain:

    @pytest.fixture
    def env(self, monkeypatch, conf):
        """Everything main() reaches for, replaced with recording doubles."""
        conf.rpc = False
        runtime = SimpleNamespace(conf=conf)
        calls = SimpleNamespace(highDpi=[], translations=[], styles=[], fonts=[])

        monkeypatch.setattr(app_module, 'createRuntime', lambda: runtime)
        monkeypatch.setattr(app_module, 'configureHighDpi', calls.highDpi.append)
        monkeypatch.setattr(app_module, 'installTranslations', calls.translations.append)
        monkeypatch.setattr(app_module, 'applyStyle', lambda app, c: calls.styles.append((app, c)))
        monkeypatch.setattr(app_module, 'uiFont', lambda **kw: calls.fonts.append(kw) or 'FONT')
        monkeypatch.setattr(app_module, 'appInfo', lambda **kw: {
            'version': '9.9', 'python': '3.11', 'machine': 'x86_64',
            'qt': kw.get('qt'), 'system': 'Windows', 'release': '10', 'revision': 'abc'})
        monkeypatch.setattr(app_module, 'QApplication', FakeQApplication)
        monkeypatch.delenv('TAFOR_ARGS', raising=False)

        FakeQApplication.instances.clear()
        FakeQApplication.execResult = 0
        FakeRunningApplication.instances.clear()

        return SimpleNamespace(runtime=runtime, calls=calls, conf=conf)

    @pytest.fixture
    def guard(self, monkeypatch):
        def build(name, acquired=True):
            monkeypatch.setattr(app_module, 'SingleInstance',
                                lambda n: FakeGuard(n, acquired=acquired))
            return name
        return build

    @pytest.fixture
    def application(self, monkeypatch):
        monkeypatch.setattr(app_module, 'Application', FakeRunningApplication)
        return FakeRunningApplication

    def test_a_second_copy_exits_zero_without_building_the_app(self, env, guard, application):
        guard('Tafor', acquired=False)

        assert main([]) == 0
        assert application.instances == []

    def test_a_normal_run_returns_the_event_loop_code(self, env, guard, application):
        guard('Tafor')

        assert main(['tafor']) == 0

        assert len(application.instances) == 1
        instance = application.instances[0]
        assert instance.runtime is env.runtime
        assert instance.started == 1
        assert instance.shutdowns == 1

    def test_the_event_loop_result_is_returned(self, env, guard, application):
        guard('Tafor')
        FakeQApplication.execResult = 7

        assert main(['tafor']) == 7

    def test_the_application_is_configured_before_it_runs(self, env, guard, application):
        guard('Tafor')

        main(['tafor'])

        app = FakeQApplication.instances[0]
        assert app.argv == ['tafor']
        assert app.font == 'FONT'
        assert env.calls.highDpi == [env.conf]
        assert env.calls.translations == [app]
        assert env.calls.styles == [(app, env.conf)]
        assert env.calls.fonts == [{'pointSize': 9}]

    def test_argv_defaults_to_sys_argv(self, env, guard, application, monkeypatch):
        guard('Tafor')
        monkeypatch.setattr(sys, 'argv', ['tafor', '--debug'])

        main()

        assert FakeQApplication.instances[0].argv == ['tafor', '--debug']

    def test_the_restart_arguments_are_recorded_for_the_child(self, env, guard, application, monkeypatch):
        guard('Tafor')
        monkeypatch.delenv('TAFOR_ARGS', raising=False)

        main(['tafor', '--debug', '--port', '1'])

        assert json.loads(os.environ['TAFOR_ARGS']) == ['--debug', '--port', '1']

    def test_shutdown_runs_even_when_the_loop_raises(self, env, guard, application, monkeypatch):
        guard('Tafor')
        monkeypatch.setattr(FakeQApplication, 'exec',
                            lambda self: (_ for _ in ()).throw(RuntimeError('boom')))

        with pytest.raises(RuntimeError):
            main(['tafor'])

        assert application.instances[0].shutdowns == 1

    def test_the_version_is_logged(self, env, guard, application, caplog):
        guard('Tafor')

        with caplog.at_level(logging.INFO, logger='tafor.main'):
            main(['tafor'])

        assert 'Version 9.9+abc' in caplog.text


class TestRun:
    """run() is the one broad catch, and it sits at the very top."""

    def test_the_exit_code_passes_through(self, monkeypatch):
        monkeypatch.setattr(app_module, 'main', lambda argv: 5)

        assert run([]) == 5

    def test_a_startup_failure_becomes_exit_code_one(self, monkeypatch, caplog):
        def boom(argv):
            raise RuntimeError('no display')

        monkeypatch.setattr(app_module, 'main', boom)

        with caplog.at_level(logging.ERROR, logger='tafor.main'):
            assert run([]) == 1

        assert 'On startup failed' in caplog.text


if __name__ == '__main__':
    pytest.main([__file__])
