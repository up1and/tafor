"""Tests for the in-memory log ring the panel reads."""

import logging
import threading

import pytest

from tafor.core.utils import log as log_module
from tafor.core.utils.log import BufferHandler, LogBuffer, setupLogging


def emitting(buffer, level=logging.NOTSET):
    """A logger with only the buffer attached, so records do not leak into
    the real handlers' output."""
    logger = logging.getLogger('tafor.test.logbuffer.{}'.format(id(buffer)))
    logger.handlers = []
    logger.propagate = False
    logger.setLevel(logging.DEBUG)
    logger.addHandler(BufferHandler(buffer, level))
    return logger


class TestLogBuffer:

    def test_records_carry_the_seq_they_were_given(self):
        buffer = LogBuffer()

        buffer.append(logging.INFO, 'tafor', 1.0, 'first')
        buffer.append(logging.WARNING, 'tafor', 2.0, 'second')

        assert [r.seq for r in buffer.records] == [1, 2]

    def test_the_ring_drops_the_oldest_record(self):
        buffer = LogBuffer(capacity=2)

        for index in range(3):
            buffer.append(logging.INFO, 'tafor', 0.0, 'm{}'.format(index))

        assert [r.message for r in buffer.records] == ['m1', 'm2']

    def test_since_returns_only_what_is_newer(self):
        buffer = LogBuffer()
        for index in range(3):
            buffer.append(logging.INFO, 'tafor', 0.0, 'm{}'.format(index))

        assert [r.message for r in buffer.since(2)] == ['m2']

    def test_since_a_dropped_seq_returns_the_whole_ring(self):
        # The caller asked for everything newer than 1, but 1 has already
        # fallen off; what is still held is the honest answer.
        buffer = LogBuffer(capacity=2)
        for index in range(4):
            buffer.append(logging.INFO, 'tafor', 0.0, 'm{}'.format(index))

        assert [r.message for r in buffer.since(1)] == ['m2', 'm3']

    def test_clear_empties_the_ring_but_not_the_seq(self):
        buffer = LogBuffer()
        buffer.append(logging.INFO, 'tafor', 0.0, 'm0')

        buffer.clear()

        assert len(buffer) == 0
        assert buffer.seq == 1

    def test_since_returns_a_snapshot_list(self):
        buffer = LogBuffer()
        buffer.append(logging.INFO, 'tafor', 0.0, 'm0')

        snapshot = buffer.since()

        assert isinstance(snapshot, list)
        snapshot.clear()
        assert len(buffer) == 1

    def test_concurrent_reads_and_writes_stay_consistent(self):
        buffer = LogBuffer(capacity=20)
        stop = threading.Event()
        errors = []

        def write(worker):
            try:
                for index in range(250):
                    buffer.append(logging.INFO, 'tafor', float(index), 'w{}-{}'.format(worker, index))
            except Exception as exc:
                errors.append(exc)

        def read():
            try:
                last = 0
                while not stop.is_set():
                    snapshot = buffer.since()
                    seqs = [record.seq for record in snapshot]
                    assert seqs == sorted(seqs)
                    recent = buffer.since(last)
                    recent_seqs = [record.seq for record in recent]
                    assert recent_seqs == sorted(recent_seqs)
                    if recent_seqs:
                        assert recent_seqs[0] > last
                        last = recent_seqs[-1]
                    _ = len(buffer)
            except Exception as exc:
                errors.append(exc)

        readers = [threading.Thread(target=read) for _ in range(2)]
        writers = [threading.Thread(target=write, args=(n,)) for n in range(4)]
        for thread in readers + writers:
            thread.start()
        for thread in writers:
            thread.join()
        stop.set()
        for thread in readers:
            thread.join()

        assert errors == []
        assert buffer.seq == 1000
        assert len(buffer) == 20


class TestBufferHandler:

    def test_a_record_reaches_the_buffer(self):
        buffer = LogBuffer()
        logger = emitting(buffer)

        logger.warning('something %s', 'happened')

        assert buffer.records[0].message == 'something happened'
        assert buffer.records[0].level == logging.WARNING
        assert buffer.records[0].name == logger.name

    def test_arguments_are_interpolated(self):
        buffer = LogBuffer()
        logger = emitting(buffer)

        logger.info('a %s with %d parts', 'message', 3)

        assert buffer.records[0].message == 'a message with 3 parts'

    def test_the_record_keeps_the_name_the_standard_library_gave_it(self):
        # ``LogRecord`` computes levelname once; deriving it again per line
        # in the panel would be repeating work already done.
        buffer = LogBuffer()
        logger = emitting(buffer)

        logger.warning('careful')

        assert buffer.records[0].levelname == 'WARNING'

    def test_a_name_can_be_supplied_without_looking_it_up(self):
        buffer = LogBuffer()

        record = buffer.append(logging.INFO, 'tafor', 0.0, 'm', levelname='INFO')

        assert record.levelname == 'INFO'

    def test_an_exception_is_kept_as_a_traceback(self):
        buffer = LogBuffer()
        logger = emitting(buffer)

        try:
            {}['missing']
        except KeyError:
            logger.exception('lookup failed')

        record = buffer.records[0]
        assert record.message == 'lookup failed'
        assert record.traceback.startswith('Traceback (most recent call last):')
        assert 'KeyError' in record.traceback
        # The message is the message; the traceback must not repeat it
        assert record.message not in record.traceback

    def test_records_below_the_handler_level_are_ignored(self):
        buffer = LogBuffer()
        logger = emitting(buffer, level=logging.WARNING)

        logger.info('too quiet')
        logger.error('loud enough')

        assert [r.message for r in buffer.records] == ['loud enough']

    def test_emit_never_raises(self):
        # Logging is fail-safe: a broken sink must not become the failure it
        # was supposed to report. A ring that cannot be appended to stands in
        # for any such breakage.
        class Broken:
            def append(self, **kwargs):
                raise RuntimeError('ring is gone')

        handler = BufferHandler(Broken())
        record = logging.LogRecord('tafor', logging.ERROR, __file__, 1, 'x', None, None)

        handler.emit(record)        # no raise

    def test_records_from_several_threads_are_all_kept(self):
        buffer = LogBuffer(capacity=1000)
        logger = emitting(buffer)

        def write(start):
            for index in range(100):
                logger.info('t%d-%d', start, index)

        threads = [threading.Thread(target=write, args=(n,)) for n in range(4)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert len(buffer.records) == 400
        # Every seq handed out once: appends from four threads did not collide
        seqs = [r.seq for r in buffer.records]
        assert seqs == sorted(seqs)
        assert len(set(seqs)) == 400


class TestSetupLogging:

    def test_writes_utf8_logs_under_root_logs_directory_and_feeds_buffer(self, monkeypatch, tmp_path):
        fresh = LogBuffer()
        monkeypatch.setattr(log_module, 'root', str(tmp_path))
        monkeypatch.setattr(log_module, 'logBuffer', fresh)

        name = 'tafor.test.setup.returns'
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.propagate = False
        try:
            setupLogging(debug=True, name=name)
            logger.debug('setup works 中文日志')

            logFile = tmp_path / 'logs' / '{}.log'.format(name)
            assert logFile.is_file()
            assert 'setup works 中文日志' in logFile.read_text(encoding='utf-8')
            assert [r.message for r in fresh.records] == ['setup works 中文日志']

            fileHandlers = [
                h for h in logger.handlers if isinstance(h, logging.handlers.RotatingFileHandler)
            ]
            assert len(fileHandlers) == 1
            assert fileHandlers[0].encoding == 'utf-8'
        finally:
            for handler in list(logger.handlers):
                handler.close()
            logger.handlers.clear()

    def test_does_not_add_duplicate_handlers_when_already_configured(self, monkeypatch, tmp_path):
        fresh = LogBuffer()
        monkeypatch.setattr(log_module, 'root', str(tmp_path))
        monkeypatch.setattr(log_module, 'logBuffer', fresh)

        name = 'tafor.test.setup.idempotent'
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.propagate = False
        try:
            setupLogging(name=name)
            count = len(logger.handlers)
            setupLogging(name=name)

            assert len(logger.handlers) == count
        finally:
            for handler in list(logger.handlers):
                handler.close()
            logger.handlers.clear()
