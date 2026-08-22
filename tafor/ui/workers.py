import csv
import datetime
import logging

from uuid import uuid4

from PyQt5.QtCore import QThread, QObject, pyqtSignal

from tafor.core.telegram.encoder import ITA2_STANDARD, encode
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

    def __init__(self, conf, context):
        super(MessageWorker, self).__init__()
        self.conf = conf
        self.context = context

    def run(self):
        try:
            if self.conf.messageUrl:
                url = self.conf.messageUrl or 'http://127.0.0.1:6575'
                self.context.message.setState(fetchMessage(url))
        finally:
            self.finished.emit()


class LayerWorker(QObject):
    """Worker for fetching layer information"""
    finished = pyqtSignal()

    def __init__(self, conf, context):
        super(LayerWorker, self).__init__()
        self.conf = conf
        self.context = context

    def run(self):
        try:
            url = self.conf.layerUrl
            self.context.layer.setLayer(layerInfo(url))
        finally:
            self.finished.emit()


class ExportRecordWorker(QObject):
    """Worker for exporting records to CSV"""
    finished = pyqtSignal()

    def __init__(self, filename, data, headers=None):
        super(ExportRecordWorker, self).__init__()
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
        super(SerialWorker, self).__init__()
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
            if codec == 'ITA2':
                message = encode(self.message, ITA2_STANDARD)
            else:
                message = self.message.encode()
            serialComm(message, port, baudrate=baudrate, bytesize=bytesize, parity=parity, stopbits=stopbits)
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

    def __init__(self, message, conf, valids=None):
        super(FtpWorker, self).__init__()
        self.message = message
        self.conf = conf
        if valids is None:
            valids = (datetime.datetime.utcnow(), datetime.datetime.utcnow())
        self.valids = valids

    def run(self):
        url = self.conf.ftpHost
        number = self.conf.fileSequenceNumber
        format = '%Y%m%d%H%M%S'
        time = datetime.datetime.utcnow()
        filename = '9_OTHE_C_{airport}_{created}_STUB-WTMG-MULT-{validfrom}-{validto}-XXX-1,{number}.txt'.format(
            airport = self.conf.airport,
            created = time.strftime(format),
            validfrom = self.valids[0].strftime(format),
            validto = self.valids[1].strftime(format),
            number = str(number).zfill(5)
        )

        try:
            ftpComm(self.message, url, filename)
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
        super(RpcWorker, self).__init__()
        self.app = app
        self.port = port
        self.server = None

    def run(self):
        try:
            from waitress import serve
            # Store server reference for potential shutdown
            self.server = serve(self.app, port=self.port, _quiet=True)
        except Exception as e:
            logger.error(f"RPC server failed to start: {e}")
        finally:
            self.finished.emit()

    def stop(self):
        """Stop the RPC server"""
        if self.server:
            try:
                self.server.close()
            except:
                pass