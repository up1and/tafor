import csv
import logging

from uuid import uuid4

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


class SerialWorker(QObject):
    """Worker for serial communication"""
    done = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, message, conf, context):
        super().__init__()
        self.message = message
        self.conf = conf
        self.context = context

    def run(self):
        port = self.conf.port
        baudrate = int(self.conf.baudrate)
        bytesize = self.conf.bytesize
        parity = self.conf.parity
        stopbits = self.conf.stopbits
        codec = self.conf.codec

        try:
            self.context.serial.lock()
            serialComm(self.message, port, baudrate=baudrate, bytesize=bytesize,
                       parity=parity, stopbits=stopbits, codec=codec)
            error = ''
        except Exception as e:
            error = str(e)
            logger.error('Failed to send data through serial port, {}'.format(e))
        finally:
            self.context.serial.release()
            self.done.emit(error)
            self.finished.emit()


class FtpWorker(QObject):
    """Worker for FTP communication"""
    done = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, message, url, filename):
        super().__init__()
        self.message = message
        self.url = url
        self.filename = filename

    def run(self):
        try:
            ftpComm(self.message, self.url, self.filename)
            error = ''
        except Exception as e:
            error = str(e)
            logger.error('Failed to send data through FTP, {}'.format(e))
        finally:
            self.done.emit(error)
            self.finished.emit()


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
    update* slots; the RPC server calls the setState entry points, which
    emit Qt signals queued back to the GUI thread. The real context
    services only ever run on the GUI thread.
    """
    metarNotification = pyqtSignal(dict)
    sigmetNotification = pyqtSignal(dict)
    otherMessage = pyqtSignal(dict)

    def __init__(self, context, parent=None):
        super().__init__(parent)
        self.context = context
        self.serial = context.serial
        self.metarNotification.connect(self.updateMetar)
        self.sigmetNotification.connect(self.updateSigmet)
        self.otherMessage.connect(self.updateOther)
        self.notification = SimpleNamespace(
            metar=SimpleNamespace(setState=self.metarNotification.emit),
            sigmet=SimpleNamespace(setState=self.sigmetNotification.emit),
        )
        self.other = SimpleNamespace(setState=self.otherMessage.emit)

    def updateMetar(self, values):
        self.context.notification.metar.setState(values)

    def updateSigmet(self, values):
        self.context.notification.sigmet.setState(values)

    def updateOther(self, values):
        self.context.other.setState(values)

    def updateMessage(self, data):
        self.context.message.setState(data)

    def updateLayer(self, data):
        self.context.layer.setLayer(data)
