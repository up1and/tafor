import csv
import datetime
import logging

import requests

from PyQt5.QtCore import QThread, QObject, pyqtSignal

from tafor import conf
from tafor.rpc import server
from tafor.states import context
from tafor.utils import serialComm, ftpComm
from tafor.utils.baudot import encode, ITA2_STANDARD

logger = logging.getLogger('tafor.thread')


_headers = {
    'User-Agent': 'Tafor/{version}+{revision} ({system} {release}; {bitness})'.format(**context.environ.environment())
}


class ThreadManager:
    """Simple thread manager for managing worker threads"""

    def __init__(self):
        self._threads = {}
        self._workers = {}

    def createWorker(self, workerClass, workerId=None, *args, **kwargs):
        """Create a worker and move it to a new thread"""
        if workerId is None:
            workerId = f"{workerClass.__name__}_{id(workerClass)}"

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

        return worker, thread

    def startWorker(self, workerId):
        """Start a worker thread"""
        if workerId in self._threads:
            thread = self._threads[workerId]
            if not thread.isRunning():
                thread.start()

    def stopWorker(self, workerId):
        """Stop a worker thread immediately"""
        if workerId in self._threads:
            thread = self._threads[workerId]
            if thread.isRunning():
                # Special handling for RpcWorker
                if workerId == 'rpc' and workerId in self._workers:
                    worker = self._workers[workerId]
                    if hasattr(worker, 'stop'):
                        worker.stop()

                thread.terminate()
                thread.wait(500)  # Brief wait to ensure termination

    def isWorkerRunning(self, workerId):
        """Check if worker thread is currently running"""
        if workerId in self._threads:
            return self._threads[workerId].isRunning()
        return False

    def cleanup(self):
        """Clean up all threads immediately or gracefully"""
        for workerId in list(self._threads.keys()):
            self.stopWorker(workerId)
        self._threads.clear()
        self._workers.clear()


# Global thread manager instance
threadManager = ThreadManager()


def fetchMessage(url):
    try:
        r = requests.get(url, headers=_headers, timeout=30)
        if r.status_code == 200:
            data = r.json()
            if not isinstance(data, dict):
                raise ValueError('The message data type is incorrect, please pass in data of dictionary type')

            messages = {}
            for key, value in data.items():
                if key in ['WS', 'WC', 'WV', 'WA'] and isinstance(value, list):
                    messages[key] = value
                if key in ['SA', 'SP', 'FC', 'FT'] and isinstance(value, str):
                    messages[key] = value

            return messages
        else:
            logger.warn('GET {} 404 Not Found'.format(url))

    except requests.exceptions.ConnectionError:
        logger.warn('GET {} 408 Request Timeout'.format(url))

    except Exception as e:
        logger.error('Failed to fetch message from {}, {}'.format(url, e))

    return {}

def layerInfo(url):
    try:
        r = requests.get(url, headers=_headers, timeout=30)
        if r.status_code == 200:
            data = r.json()
            if not isinstance(data, list):
                raise ValueError('The layer data type is incorrect, please pass in data of list type')

            for layer in data:
                try:
                    imageUrl = layer['image']
                    req = requests.get(imageUrl)
                    layer['image'] = req.content
                except Exception as e:
                    layer['image'] = None
            return data
        else:
            logger.warn('GET {} 404 Not Found'.format(url))

    except requests.exceptions.ConnectionError:
        logger.warn('GET {} 408 Request Timeout'.format(url))

    except Exception as e:
        logger.error('Failed to fetch cloud layer from {}, {}'.format(url, e))

    return []

def repoRelease(url):
    try:
        r = requests.get(url, headers=_headers, timeout=30)
        return r.json()

    except requests.exceptions.ConnectionError:
            logger.info('GET {} 408 Request Timeout'.format(url))

    except Exception as e:
        logger.error('Failed to get the latest version information from {}, {}'.format(url, e))

    return {}


class MessageWorker(QObject):
    """Worker for fetching message data"""
    finished = pyqtSignal()

    def run(self):
        try:
            if conf.messageUrl:
                url = conf.messageUrl or 'http://127.0.0.1:6575'
                context.message.setMessage(fetchMessage(url))
        finally:
            self.finished.emit()


class LayerWorker(QObject):
    """Worker for fetching layer information"""
    finished = pyqtSignal()

    def run(self):
        try:
            url = conf.layerUrl
            context.layer.setLayer(layerInfo(url))
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

    def __init__(self, message):
        super(SerialWorker, self).__init__()
        self.message = message

    def run(self):
        port = conf.port
        baudrate = int(conf.baudrate)
        bytesize = conf.bytesize
        parity = conf.parity
        stopbits = conf.stopbits
        codec = conf['Communication/Codec']

        try:
            context.serial.lock()
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
            context.serial.release()
            self.done.emit(error)
            self.finished.emit()


class FtpWorker(QObject):
    """Worker for FTP communication"""
    done = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, message, valids=None):
        super(FtpWorker, self).__init__()
        self.message = message
        if valids is None:
            valids = (datetime.datetime.utcnow(), datetime.datetime.utcnow())
        self.valids = valids

    def run(self):
        url = conf.ftpHost
        number = conf['Communication/FileSequenceNumber'] or 1
        format = '%Y%m%d%H%M%S'
        time = datetime.datetime.utcnow()
        filename = '9_OTHE_C_{airport}_{created}_STUB-WTMG-MULT-{validfrom}-{validto}-XXX-1,{number}.txt'.format(
            airport = conf.airport,
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

    def __init__(self, port=9407):
        super(RpcWorker, self).__init__()
        self.app = server
        self.port = port
        self._server = None

    def run(self):
        try:
            from waitress import serve
            # Store server reference for potential shutdown
            self._server = serve(self.app, port=self.port, _quiet=True)
        except Exception as e:
            logger.error(f"RPC server failed to start: {e}")
        finally:
            self.finished.emit()

    def stop(self):
        """Stop the RPC server"""
        if self._server:
            try:
                self._server.close()
            except:
                pass



