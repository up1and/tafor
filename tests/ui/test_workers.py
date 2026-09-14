"""Tests for tafor/ui/workers.py.

Covers the thread manager lifecycle, the CSV export worker, the context
bridge and the run() methods of the network workers with a patched client.
Serial, FTP and RPC workers need hardware, a server or a bound port and are
not covered here.
"""

import csv

import pytest

from PyQt5.QtCore import QObject, pyqtSignal

from tafor.ui.workers import (
    CheckUpgradeWorker, ContextBridge, ExportRecordWorker, LayerWorker,
    MessageWorker, ThreadManager)


METAR = 'METAR ZJHK 210900Z 14004MPS 4500 -RA BKN030='


class DummyWorker(QObject):
    """Minimal worker for exercising the thread manager lifecycle."""
    finished = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.ran = False

    def run(self):
        self.ran = True
        self.finished.emit()


@pytest.fixture
def manager():
    manager = ThreadManager()
    yield manager
    manager.cleanup()


class TestExportRecordWorker:

    def test_run_writes_csv_with_headers(self, qtbot, tmp_path):
        filename = str(tmp_path / 'records.csv')
        worker = ExportRecordWorker(filename, [('FT', 'TAF YUSO='), ('SA', METAR)],
                                    headers=('type', 'text'))

        with qtbot.waitSignal(worker.finished):
            worker.run()

        with open(filename, newline='') as file:
            rows = list(csv.reader(file))

        assert rows == [['type', 'text'], ['FT', 'TAF YUSO='], ['SA', METAR]]

    def test_run_without_headers_skips_header_row(self, qtbot, tmp_path):
        filename = str(tmp_path / 'records.csv')
        worker = ExportRecordWorker(filename, [['a', 1]])

        with qtbot.waitSignal(worker.finished):
            worker.run()

        with open(filename, newline='') as file:
            rows = list(csv.reader(file))

        assert rows == [['a', '1']]


class TestThreadManager:

    def test_create_registers_worker(self, manager):
        worker, thread = manager.createWorker(DummyWorker, workerId='x', reusable=True)

        assert manager._workers['x'] is worker
        assert manager._threads['x'] is thread

    def test_same_id_returns_same_pair(self, manager):
        first = manager.createWorker(DummyWorker, workerId='x', reusable=True)
        second = manager.createWorker(DummyWorker, workerId='x', reusable=True)

        assert first == second

    def test_reusable_worker_survives_finish(self, manager, qtbot):
        worker, thread = manager.createWorker(DummyWorker, workerId='x', reusable=True)

        with qtbot.waitSignal(worker.finished):
            thread.start()

        assert worker.ran is True
        assert manager._workers['x'] is worker

    def test_non_reusable_worker_unregisters_on_finish(self, manager, qtbot):
        worker, thread = manager.createWorker(DummyWorker, workerId='x')

        with qtbot.waitSignal(worker.finished):
            thread.start()

        qtbot.waitUntil(lambda: 'x' not in manager._threads)
        replacement = manager.createWorker(DummyWorker, workerId='x')
        assert replacement[0] is not worker

    def test_remove_worker_stops_and_unregisters(self, manager, qtbot):
        worker, thread = manager.createWorker(DummyWorker, workerId='x', reusable=True)
        thread.start()
        qtbot.waitUntil(thread.isRunning)

        manager.removeWorker('x')

        assert 'x' not in manager._threads
        replacement = manager.createWorker(DummyWorker, workerId='x', reusable=True)
        assert replacement[0] is not worker

    def test_remove_unknown_worker_is_harmless(self, manager):
        manager.removeWorker('missing')

    def test_cleanup_removes_everything(self, manager, qtbot):
        manager.createWorker(DummyWorker, workerId='a', reusable=True)
        manager.createWorker(DummyWorker, workerId='b', reusable=True)

        manager.cleanup()

        assert manager._threads == {}
        assert manager._workers == {}


class TestContextBridge:

    def test_metar_notification_updates_context(self, qtbot, context):
        bridge = ContextBridge(context)

        bridge.notification.metar.setState({'message': METAR, 'validation': True})

        assert context.notification.metar.message() == METAR

    def test_sigmet_notification_updates_context(self, qtbot, context):
        message = 'ZJSA SIGMET 2 VALID 100730/101430 ZJHK-\nZJSA SANYA FIR OBSC TS='
        bridge = ContextBridge(context)

        bridge.notification.sigmet.setState({'message': message, 'validation': False})

        assert context.notification.sigmet.message() == message

    def test_other_message_reaches_event_bus(self, qtbot, context):
        received = []
        context.event.otherMessageReceived.connect(received.append)
        bridge = ContextBridge(context)

        bridge.other.submit('transient message')

        assert received == ['transient message']

    def test_update_message_sets_remote_state(self, qtbot, context):
        bridge = ContextBridge(context)

        bridge.updateMessage({'SA': METAR})

        assert context.message.message() == {'SA': METAR}

    def test_exposes_serial_lock(self, qtbot, context):
        bridge = ContextBridge(context)

        assert bridge.serial is context.serial


class TestNetworkWorkers:
    """run() is called directly; the client functions are patched so no
    network is touched."""

    def test_message_worker_emits_fetched(self, qtbot, conf, monkeypatch):
        monkeypatch.setattr('tafor.ui.workers.fetchMessage', lambda url: {'SA': METAR})
        worker = MessageWorker(conf)

        with qtbot.waitSignal(worker.fetched) as blocker:
            worker.run()

        assert blocker.args == [{'SA': METAR}]

    def test_message_worker_emits_empty_dict_on_failure(self, qtbot, conf, monkeypatch):
        # fetchMessage swallows every error and returns {}; the UI cannot
        # tell "no data" from "connection failed". The signal is typed as
        # dict, so a client ever returning None would crash right here.
        monkeypatch.setattr('tafor.ui.workers.fetchMessage', lambda url: {})
        worker = MessageWorker(conf)

        with qtbot.waitSignal(worker.fetched) as blocker:
            worker.run()

        assert blocker.args == [{}]

    def test_layer_worker_emits_fetched(self, qtbot, conf, monkeypatch):
        layers = [{'image': b'bytes', 'name': 'cloud'}]
        monkeypatch.setattr('tafor.ui.workers.layerInfo', lambda url: layers)
        worker = LayerWorker(conf)

        with qtbot.waitSignal(worker.fetched) as blocker:
            worker.run()

        assert blocker.args == [layers]

    def test_check_upgrade_worker_emits_release(self, qtbot, monkeypatch):
        release = {'tag_name': 'v3.0.1'}
        monkeypatch.setattr('tafor.ui.workers.repoRelease', lambda url: release)
        worker = CheckUpgradeWorker()

        with qtbot.waitSignal(worker.done) as blocker:
            worker.run()

        assert blocker.args == [release]


if __name__ == '__main__':
    pytest.main([__file__])
