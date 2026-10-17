"""Where the application's log records go.

Two sinks, one source. The rotating file next to the application is the
durable record; the ring in memory is the volatile copy the log panel reads,
so the panel never has to open, follow or parse a file that is rotating
underneath it -- and keeps working when that file cannot be written at all.
"""

import sys
import logging

from collections import deque
from logging import Formatter
from logging.handlers import RotatingFileHandler


class LogRecord:
    """One line, flattened to what the panel draws."""

    __slots__ = ('seq', 'level', 'levelname', 'name', 'created', 'message', 'traceback')

    def __init__(self, seq, level, name, created, message, traceback='', levelname=None):
        self.seq = seq              # monotonic: the panel asks for what is newer
        self.level = level          # logging.WARNING and friends
        self.name = name            # the logger it came from
        self.created = created      # epoch seconds, as logging stamped them
        self.message = message
        self.traceback = traceback  # formatted exception, when there was one
        # The name is carried rather than looked up: every logging record
        # already computed it, so deriving it again per line would be work
        # the standard library has done once already.
        self.levelname = levelname if levelname is not None else logging.getLevelName(level)

    def __repr__(self):
        return '<LogRecord {} {} {}>'.format(self.seq, self.levelname, self.message)


class LogBuffer:
    """A ring of the last ``capacity`` records.

    Old records fall off the front once it is full. That is the point: the
    panel shows what just happened, and a shift's worth of records is all it
    ever needs to hold.
    """

    def __init__(self, capacity=500):
        self.records = deque(maxlen=capacity)
        self.seq = 0

    def append(self, level, name, created, message, traceback='', levelname=None):
        self.seq += 1
        record = LogRecord(self.seq, level, name, created, message, traceback, levelname)
        self.records.append(record)
        return record

    def since(self, seq=0):
        """Every record appended after ``seq``, oldest first.

        A seq the ring has already dropped simply yields the whole ring:
        the caller asked for 'everything newer than X' and the honest answer
        is everything still held.
        """
        return [record for record in self.records if record.seq > seq]

    def clear(self):
        self.records.clear()

    def __len__(self):
        return len(self.records)


class BufferHandler(logging.Handler):
    """Feeds a LogBuffer from the logging call.

    emit() must never raise: logging calls fail-safe by contract, and a
    handler that throws would turn the act of logging into the failure.
    Whatever cannot be read off a record is dropped, not propagated.
    """

    def __init__(self, buffer, level=logging.NOTSET):
        super().__init__(level)
        self.buffer = buffer

    def emit(self, record):
        try:
            traceback = ''
            if record.exc_info:
                # The formatted exception only; the message itself is already
                # on the record, so formatting the whole line would repeat it.
                traceback = Formatter().formatException(record.exc_info)

            self.buffer.append(
                level=record.levelno,
                name=record.name,
                created=record.created,
                message=record.getMessage(),
                traceback=traceback,
                levelname=record.levelname,
            )
        except Exception:
            self.handleError(record)


# The ring the panel reads. Filled by setupLogging, drained by the panel.
logBuffer = LogBuffer()


def setupLogging(debug=False, name='tafor'):
    logLevel = logging.DEBUG if debug else logging.INFO
    _format = '[%(asctime)s] %(levelname)s [%(name)s] %(message)s'
    formatter = logging.Formatter(_format)

    logger = logging.getLogger(name)
    if logger.handlers:
        return

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(formatter)

    fh = RotatingFileHandler('{}.log'.format(name), maxBytes=1024*1024, backupCount=5)
    fh.setLevel(logLevel)
    fh.setFormatter(formatter)

    # The panel reads records, not the file: one more sink on the same
    # logger, at the same level, so what it shows is what was written.
    bh = BufferHandler(logBuffer)
    bh.setLevel(logLevel)

    logger.setLevel(logLevel)
    logger.addHandler(ch)
    logger.addHandler(fh)
    logger.addHandler(bh)
