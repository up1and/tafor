import csv
import time
import logging

from uuid import uuid4
from collections import deque
from types import SimpleNamespace

from PyQt5.QtCore import QThread, QObject, pyqtSignal

from tafor.core.telegram.transport import ftpComm, serialComm
from tafor.core.utils.client import fetchMessage, layerInfo, repoRelease

logger = logging.getLogger('tafor.workers')


class ThreadManager:
    """Thread manager for managing worker threads"""

    def __init__(self):
        self._threads = {}
        self._workers = {}

    def createWorker(self, workerClass, *args, workerId=None, reusable=False, **kwargs):
        """Create a worker and move it to a new thread"""
        if workerId is None:
            workerId = str(uuid4())

        if workerId in self._threads and workerId in self._workers:
            return self._workers[workerId], self._threads[workerId]

        # Create thread and worker
        thread = QThread()
        worker = workerClass(*args, **kwargs)

        # Move worker to thread
        worker.moveToThread(thread)

        # Store references
        self._threads[workerId] = thread
        self._workers[workerId] = worker

        # Connect signals
        thread.started.connect(worker.run)
        worker.finished.connect(thread.quit)

        if not reusable:
            thread.finished.connect(worker.deleteLater)
            thread.finished.connect(thread.deleteLater)
            thread.finished.connect(lambda wid=workerId: self.unregister(wid))

        return worker, thread

    def unregister(self, workerId):
        """Unregister worker references."""
        self._threads.pop(workerId, None)
        self._workers.pop(workerId, None)

    def removeWorker(self, workerId):
        """Gracefully stops a worker, waits for the thread to exit, and clears all references."""
        thread = self._threads.get(workerId)
        worker = self._workers.get(workerId)

        if not thread and not worker:
            return

        if thread is not None:
            thread.finished.connect(thread.deleteLater)
            if worker is not None:
                thread.finished.connect(worker.deleteLater)

        if thread and thread.isRunning():
            if worker and hasattr(worker, 'stop'):
                worker.stop()

            # Signal the event loop to stop
            thread.quit()

            # Blocking wait to ensure thread resources are released before disposal
            thread.wait(1000)

        self.unregister(workerId)
    def cleanup(self):
        """
        Synchronously shuts down all managed threads. 
        Usually called when the main application is closing.
        """
        for workerId in list(self._threads.keys()):
            self.removeWorker(workerId)


# Global thread manager instance
threadManager = ThreadManager()


class MessageWorker(QObject):
    """Worker for fetching message data"""
    finished = pyqtSignal()
    fetched = pyqtSignal(dict)

    def __init__(self, conf):
        super().__init__()
        self.conf = conf

    def run(self):
        try:
            url = self.conf.messageUrl or 'http://127.0.0.1:6575'
            self.fetched.emit(fetchMessage(url))
        finally:
            self.finished.emit()


class LayerWorker(QObject):
    """Worker for fetching layer information"""
    finished = pyqtSignal()
    fetched = pyqtSignal(list)

    def __init__(self, conf):
        super().__init__()
        self.conf = conf

    def run(self):
        try:
            url = self.conf.layerUrl
            self.fetched.emit(layerInfo(url))
        finally:
            self.finished.emit()


class ExportRecordWorker(QObject):
    """Worker for exporting records to CSV"""
    finished = pyqtSignal()

    def __init__(self, filename, data, headers=None):
        super().__init__()
        self.data = data
        self.headers = headers
        self.filename = filename

    def run(self):
        try:
            with open(self.filename, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                if self.headers:
                    writer.writerow(self.headers)
                for row in self.data:
                    writer.writerow(row)
        finally:
            self.finished.emit()


class Job:
    """One queued transmission. Created and settled on the GUI thread; the
    worker thread never sees it, only the plain payload derived from it."""

    def __init__(self, message, line, parser=None, settle=None):
        self.message = message      # transient message instance, GUI thread only
        self.line = line            # protocol (aftn/ftp), channel + conf
        self.parser = parser        # composed.parser, only feeds the ftp filename's valids
        self.settle = settle        # callable(job, error), runs on the GUI thread
        self.telegraph = None       # filled in by the queue at dispatch


def payload(job):
    """Derive the worker's plain arguments from a job: protocol kind, the
    telegraph text and the channel parameters, read from conf at dispatch so
    the freshest sequence number and port settings are used"""
    line = job.line
    text = job.telegraph.toString()

    if line.protocol == 'ftp':
        params = line.channel.ftpParams(getattr(job.parser, 'valids', None))
    else:
        params = {
            'port': line.conf.port,
            'baudrate': int(line.conf.baudrate),
            'bytesize': line.conf.bytesize,
            'parity': line.conf.parity,
            'stopbits': line.conf.stopbits,
            'codec': line.conf.codec,
        }

    return line.protocol, text, params


def deliver(job, error):
    """Hand the outcome back to the job's owner, absorbing its failures.

    A presenter error must not wedge the queue, and finish() runs this from a
    Qt slot, where an unhandled exception aborts the process outright.
    """
    if job.settle is None:
        return
    try:
        job.settle(job, error)
    except Exception:
        logger.exception('Failed to settle the transmission')


class TransmissionQueue(QObject):
    """The process-wide single transmission line.

    Lives entirely on the GUI thread: submissions, telegraph generation
    (sequence number read) and settlement (archive + sequence write-back)
    happen here in strict FIFO order, lock-free. The resident worker on its
    own thread only runs the blocking IO. See docs/transmission-queue.md.
    """

    dispatch = pyqtSignal(str, str, dict)   # kind, text, params

    def __init__(self, worker, parent=None):
        super().__init__(parent)
        self.worker = worker
        self.jobs = deque()
        self.current = None

    @property
    def isBusy(self):
        return self.current is not None

    @property
    def pending(self):
        return len(self.jobs)

    def submit(self, job):
        self.jobs.append(job)
        self.pump()

    def pump(self):
        if self.current is not None or not self.jobs:
            return

        job = self.jobs.popleft()
        try:
            job.telegraph = job.line.generate(job.message)
            kind, text, params = payload(job)
        except Exception as e:
            logger.exception('Failed to generate the telegram')
            deliver(job, str(e))        # generation failure settles as a send failure
            self.pump()                 # recursion depth is bounded by the queue length
            return

        self.current = job
        self.worker.prepare()
        self.dispatch.emit(kind, text, params)

    def finish(self, error):
        """Back from worker.done over a queued connection, on the GUI thread"""
        job, self.current = self.current, None
        if job is not None:
            deliver(job, error)
        self.pump()

    def stop(self):
        """Shutdown path: block until the wire goes quiet, then settle the
        in-flight job synchronously — the worker's done signal is never
        delivered once the event loop has exited. Undispatched jobs are
        dropped by design.

        The outcome is trustworthy because worker.stop() returns only once
        busy is cleared, and busy is cleared in the same finally that writes
        the error.
        """
        self.jobs.clear()
        self.worker.stop()
        job, self.current = self.current, None
        if job is not None:
            deliver(job, self.worker.error)


class TransmissionWorker(QObject):
    """The resident transmission worker: one thread, blocking IO only.

    run() is a no-op; the thread's event loop dispatches the transmit slot.
    done() always carries the outcome, finished() exists only to satisfy the
    thread manager contract and is never emitted.
    """
    done = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.busy = False
        self.error = ''

    def run(self):
        pass

    def prepare(self):
        """Called on the GUI thread right before dispatch: close the window
        where stop() would see an idle worker while a transmit() call is
        still queued on the worker thread"""
        self.busy = True
        self.error = ''

    def transmit(self, kind, text, params):
        """Runs on the worker thread"""
        self.busy = True
        self.error = ''
        try:
            if kind == 'ftp':
                ftpComm(text, **params)
            else:
                serialComm(text, **params)
        except Exception as e:
            self.error = str(e)
            logger.error('Failed to send data over {}, {}'.format(kind, e))
        finally:
            self.busy = False
            self.done.emit(self.error)

    def stop(self):
        """Block the caller until the wire goes quiet.

        busy is cleared in transmit()'s finally, right after the outcome is
        written to error, so a False busy means this job's result is known.
        That is the whole contract — there is no deadline.
        """
        if self.busy:
            logger.info('Waiting for the transmission in flight to finish')
        while self.busy:
            time.sleep(0.05)


class CheckUpgradeWorker(QObject):
    """Worker for checking software updates"""
    done = pyqtSignal(dict)
    finished = pyqtSignal()

    def run(self):
        try:
            url = 'https://api.github.com/repos/up1and/tafor/releases/latest'
            data = repoRelease(url)
            self.done.emit(data)
        finally:
            self.finished.emit()


class RpcWorker(QObject):
    """Worker for RPC server"""
    finished = pyqtSignal()

    def __init__(self, app, port=9407):
        super().__init__()
        self.app = app
        self.port = port
        self.server = None

    def run(self):
        try:
            from waitress.server import create_server
            # create_server only binds the socket; run() pumps requests until
            # stop() closes it.
            self.server = create_server(self.app, port=self.port)
            self.server.run()
        except Exception as e:
            logger.error(f"RPC server failed to start: {e}")
        finally:
            self.finished.emit()

    def stop(self):
        """Stop the RPC server"""
        if self.server:
            try:
                self.server.close()
            except Exception:
                logger.exception('Failed to close the RPC server')


class ContextBridge(QObject):
    """The single door through which background threads update context state.

    Lives on the GUI thread. Workers connect their fetched signals to the
    update* slots; the RPC server calls the setState/submit entry points,
    which emit Qt signals queued back to the GUI thread. The real context
    services only ever run on the GUI thread.

    Submit payloads must be transient model instances (never bound to a
    session) and stay read-only on the emitting thread; the GUI side
    takes ownership once queued.
    """
    metarNotification = pyqtSignal(dict)
    sigmetNotification = pyqtSignal(dict)
    otherMessage = pyqtSignal(object)

    def __init__(self, context, parent=None):
        super().__init__(parent)
        self.context = context
        self.metarNotification.connect(self.updateMetar)
        self.sigmetNotification.connect(self.updateSigmet)
        self.otherMessage.connect(self.updateOther)
        self.notification = SimpleNamespace(
            metar=SimpleNamespace(setState=self.metarNotification.emit),
            sigmet=SimpleNamespace(setState=self.sigmetNotification.emit),
        )
        self.other = SimpleNamespace(submit=self.otherMessage.emit)

    @property
    def transmission(self):
        """Forwarded live: the queue is injected into the context by the
        application assembly after the bridge exists"""
        return self.context.transmission

    def updateMetar(self, values):
        self.context.notification.metar.setState(values)

    def updateSigmet(self, values):
        self.context.notification.sigmet.setState(values)

    def updateOther(self, message):
        self.context.event.otherMessageReceived.emit(message)

    def updateMessage(self, data):
        self.context.message.setState(data)

    def updateLayer(self, data):
        self.context.layer.setLayer(data)
