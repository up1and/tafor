"""Tests for tafor/ui/workers.py.

Covers the thread manager lifecycle, the CSV export worker, the context
bridge, the transmission queue and the run() methods of the network workers
with a patched client. The RPC worker needs a bound port and is covered in
tests/core/test_rpc.py.
"""

import csv
import threading
import time

from types import SimpleNamespace

import pytest

from PyQt5.QtCore import QObject, pyqtSignal

from tafor.ui.workers import (
    CheckUpgradeWorker, ContextBridge, ExportRecordWorker, Job, LayerWorker,
    MessageWorker, ThreadManager, TransmissionQueue, TransmissionWorker)


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

    def test_forwards_transmission(self, qtbot, context):
        context.transmission = object()
        bridge = ContextBridge(context)

        assert bridge.transmission is context.transmission


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


class TestTransmissionQueue:
    """The worker is stubbed: the queue generates and dispatches
    synchronously on submission, the test delivers results with finish()"""

    def makeQueue(self, conf):
        calls = []
        worker = SimpleNamespace(prepare=lambda: None, stop=lambda: None, error='')
        queue = TransmissionQueue(worker)
        queue.dispatch.connect(lambda kind, text, params: calls.append(
            {'kind': kind, 'text': text, 'params': params}))
        return queue, calls

    def makeJob(self, message=None, conf=None, **kwargs):
        from tafor.ui.components.send import Line

        message = message or SimpleNamespace(
            text='TEST=', priority='FF', address='YUSO YUSI',
            category='CUSTOM', heading=None)
        line = Line(conf, pinned=kwargs.pop('pinned', 'aftn'))
        return Job(message, line, settle=kwargs.pop('settle', None), **kwargs)

    def test_submit_generates_and_dispatches_when_idle(self, qtbot, conf):
        queue, calls = self.makeQueue(conf)
        settled = []
        job = self.makeJob(conf=conf, settle=lambda j, e: settled.append((j, e)))

        queue.submit(job)

        assert job.telegraph is not None
        assert calls[0]['kind'] == 'aftn'
        assert calls[0]['params']['port'] == conf.port
        assert queue.isBusy

        queue.finish('')
        assert settled == [(job, '')]
        assert not queue.isBusy

    def test_serializes_and_generates_at_dispatch_time(self, qtbot, conf):
        queue, calls = self.makeQueue(conf)
        conf.set('channelSequenceNumber', '1')

        # The settle callback mirrors the presenter: the sequence number is
        # written back before the queue generates the next telegraph
        first = self.makeJob(conf=conf, settle=lambda j, e: conf.set(
            'channelSequenceNumber', str(j.telegraph.number)))
        second = self.makeJob(conf=conf, settle=lambda j, e: None)
        queue.submit(first)
        queue.submit(second)

        # The second job waits untouched while the first is on the wire
        assert queue.pending == 1
        assert second.telegraph is None
        assert len(calls) == 1

        queue.finish('')

        assert second.telegraph.number == first.telegraph.number + 1
        assert len(calls) == 2
        queue.finish('')

    def test_generation_failure_settles_and_continues(self, qtbot, conf):
        queue, calls = self.makeQueue(conf)
        settled = []

        broken = self.makeJob(conf=conf, settle=lambda j, e: settled.append((j, e)))
        broken.line.generate = lambda message: 1 / 0
        following = self.makeJob(conf=conf, settle=lambda j, e: settled.append((j, e)))

        queue.submit(broken)
        queue.submit(following)

        # The broken job settled with the error, the queue moved on by itself
        assert settled[0][0] is broken and settled[0][1]
        assert queue.current is following
        assert len(calls) == 1

        queue.finish('')
        assert settled[1] == (following, '')

    def test_ftp_dispatch_carries_channel_params(self, qtbot, conf, monkeypatch):
        queue, calls = self.makeQueue(conf)
        monkeypatch.setattr(conf, 'communicationProtocol', 'ftp')
        conf.set('fileSequenceNumber', '1')

        message = SimpleNamespace(
            text='TAF YUSO=', category='TAF', heading='FTZJ41 ZJHK 211400',
            priority=None, address=None)
        job = self.makeJob(message=message, conf=conf, pinned=None, settle=lambda j, e: None)
        queue.submit(job)

        assert calls[0]['kind'] == 'ftp'
        assert 'url' in calls[0]['params'] and 'filename' in calls[0]['params']
        queue.finish('')

    def test_a_failing_settle_does_not_wedge_the_queue(self, qtbot, conf):
        """Regression: settle used to run bare inside finish(), a Qt slot —
        an exception there aborts the process with no traceback."""
        queue, calls = self.makeQueue(conf)

        def broken(job, error):
            raise RuntimeError('the presenter blew up')

        first = self.makeJob(conf=conf, settle=broken)
        following = self.makeJob(conf=conf)         # no settle callback at all
        queue.submit(first)
        queue.submit(following)

        assert len(calls) == 1
        queue.finish('')                            # must not raise

        assert len(calls) == 2                      # the queue moved on by itself
        queue.finish('')

    def test_a_failing_settle_does_not_stop_the_failure_path(self, qtbot, conf):
        queue, calls = self.makeQueue(conf)

        def broken(job, error):
            raise RuntimeError('the presenter blew up')

        bad = self.makeJob(conf=conf, settle=broken)
        bad.line.generate = lambda message: 1 / 0
        following = self.makeJob(conf=conf)
        queue.submit(bad)
        queue.submit(following)

        assert len(calls) == 1
        assert queue.isBusy
        queue.finish('')

    def test_stop_settles_with_the_outcome_of_the_real_worker(self, qtbot, conf):
        """The stub worker cannot catch a wrong outcome: stop() must not read
        error before the transmit still on the wire has written it."""
        worker = TransmissionWorker()
        queue = TransmissionQueue(worker)
        settled = []

        job = self.makeJob(conf=conf, settle=lambda j, e: settled.append((j, e)))
        queue.submit(job)                           # prepare() ran, the worker is idle

        def wire():
            time.sleep(0.2)
            worker.error = 'serial port offline'
            worker.busy = False

        threading.Thread(target=wire, daemon=True).start()
        queue.stop()

        assert settled == [(job, 'serial port offline')]
        assert not queue.isBusy


class TestTransmissionWorker:

    def test_transmit_serial_success(self, qtbot, monkeypatch):
        sent = []
        monkeypatch.setattr('tafor.ui.workers.serialComm', lambda text, **params: sent.append((text, params)))
        worker = TransmissionWorker()

        with qtbot.waitSignal(worker.done) as blocker:
            worker.transmit('aftn', 'TEST=', {'port': 'COM1', 'baudrate': 9600})

        assert blocker.args == ['']
        assert sent[0][0] == 'TEST='
        assert sent[0][1]['port'] == 'COM1'
        assert worker.busy is False

    def test_transmit_ftp_dispatch(self, qtbot, monkeypatch):
        sent = []
        monkeypatch.setattr('tafor.ui.workers.ftpComm', lambda text, **params: sent.append((text, params)))
        worker = TransmissionWorker()

        with qtbot.waitSignal(worker.done):
            worker.transmit('ftp', 'TEST=', {'url': 'ftp://x', 'filename': 'f'})

        assert sent[0][1] == {'url': 'ftp://x', 'filename': 'f'}

    def test_transmit_failure_reports_error(self, qtbot, monkeypatch):
        def broken(text, **params):
            raise OSError('port busy')

        monkeypatch.setattr('tafor.ui.workers.serialComm', broken)
        worker = TransmissionWorker()

        with qtbot.waitSignal(worker.done) as blocker:
            worker.transmit('aftn', 'TEST=', {})

        assert blocker.args == ['port busy']
        assert worker.error == 'port busy'
        assert worker.busy is False

    def test_stop_returns_immediately_when_idle(self, qtbot):
        worker = TransmissionWorker()
        start = time.time()
        worker.stop()
        assert time.time() - start < 1

    def test_stop_waits_for_the_transmission_in_flight(self, qtbot):
        """Regression: the wait broke out on its first pass, because error is
        '' both before and during a transmit — never None."""
        worker = TransmissionWorker()
        worker.prepare()

        def wire():
            time.sleep(0.2)
            worker.error = 'port busy'
            worker.busy = False

        threading.Thread(target=wire, daemon=True).start()

        start = time.time()
        worker.stop()

        assert time.time() - start >= 0.2
        assert worker.busy is False
        assert worker.error == 'port busy'


if __name__ == '__main__':
    pytest.main([__file__])
