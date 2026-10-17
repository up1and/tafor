"""Tests for the log window and the presenter that owns it."""

import datetime
import logging

from collections import deque

import pytest

from PyQt5.QtCore import Qt

from tafor.core.utils import log as log_module
from tafor.core.utils.log import logBuffer
from tafor.ui.main import LogPresenter
from tafor.ui.widgets.logpanel import LogPanel


@pytest.fixture
def panel(qtbot):
    """A panel over an empty ring.

    The ring is process-wide and other tests log into it, so it is emptied
    here; the panel reads it by identity, not by copy.
    """
    logBuffer.clear()
    widget = LogPanel()
    qtbot.addWidget(widget)
    yield widget
    logBuffer.clear()


#: A two-line traceback for the tests that need one.
TEARDOWN = 'Traceback (most recent call last):' + chr(10) + 'KeyError: k'


def written(level=logging.INFO, message='a line', name='tafor.test', traceback=''):
    return logBuffer.append(level, name, 1000.0, message, traceback)


class TestLogPanelReading:

    def test_a_record_written_after_a_poll_appears_on_the_next_one(self, panel):
        written(message='first')
        panel.poll()
        written(message='second')
        panel.poll()

        assert 'first' in panel.text.toPlainText()
        assert 'second' in panel.text.toPlainText()

    def test_records_from_two_polls_are_separate_lines(self, panel):
        # A run of records appended in one poll and a second run appended
        # later must not end up in the same block, which would read as a
        # single line with the timestamps run together.
        written(message='from the first poll')
        panel.poll()
        written(message='from the second')
        panel.poll()

        lines = panel.text.toPlainText().splitlines()
        assert len(lines) == 2
        assert lines[0].endswith('from the first poll')
        assert lines[1].endswith('from the second')

    def test_every_record_gets_its_own_line(self, panel):
        for index in range(5):
            written(message='line {}'.format(index))
        panel.poll()

        assert panel.text.document().blockCount() == 5

    def test_a_poll_does_not_repeat_what_it_already_read(self, panel):
        written(message='only once')
        panel.poll()
        panel.poll()

        assert panel.text.toPlainText().count('only once') == 1

    def test_a_poll_with_nothing_new_changes_nothing(self, panel):
        written(message='before')
        panel.poll()
        before = panel.text.toPlainText()

        panel.poll()

        assert panel.text.toPlainText() == before

    def test_opening_the_panel_shows_what_was_logged_while_it_was_closed(self, panel):
        # Records logged before the window is ever shown are what the
        # operator opens it to find.
        written(message='from before it opened')

        panel.show()

        assert 'from before it opened' in panel.text.toPlainText()

    def test_a_line_carries_its_time_level_logger_and_message(self, panel):
        record = written(level=logging.WARNING, message='careful', name='tafor.channel')
        line = panel.format(record)
        stamp = datetime.datetime.fromtimestamp(1000.0).strftime('%b %d %H:%M:%S')

        assert 'WARNING' in line
        assert 'tafor.channel' in line
        assert 'careful' in line
        assert line.startswith('{} WARNING'.format(stamp))   # 1000.0 epoch, local

    def test_a_traceback_keeps_its_own_lines(self, panel):
        record = written(message='it broke', traceback=TEARDOWN)

        line = panel.format(record)

        assert line.splitlines()[0].endswith('it broke')
        assert 'KeyError: k' in line

    def test_the_ring_filling_up_does_not_clear_the_window(self, panel):
        # The window keeps what it drew; the ring dropping old records is
        # not the same thing as the operator losing them from view. The
        # capacity is traded down to five so the fill is real: while the
        # second batch is written and before the next poll, m4..m14 fall
        # off the ring. Nobody polled in between, so they were never drawn
        # precisely because they were evicted, and the panel has no copy
        # of its own to resurrect them with.
        was = logBuffer.records
        try:
            logBuffer.records = deque(maxlen=5)
            for index in range(5):
                written(message='m{}'.format(index))
            panel.poll()

            for index in range(5, 20):
                written(message='m{}'.format(index))
            panel.poll()

            assert len(logBuffer.records) == 5
            assert 'm0' in panel.text.toPlainText()
            assert 'm19' in panel.text.toPlainText()
            assert 'm10' not in panel.text.toPlainText()
        finally:
            logBuffer.records = was


class TestLogPanelFiltering:

    def test_the_level_box_offers_only_what_can_be_recorded(self, panel):
        offered = [panel.levelBox.itemText(i) for i in range(panel.levelBox.count())]

        assert offered == ['INFO', 'WARNING', 'ERROR', 'CRITICAL']
        assert 'DEBUG' not in offered          # the ring is filled at INFO

    def test_the_box_follows_the_logger_rather_than_an_imported_copy(self, panel, qtbot):
        # A number imported with ``from ... import logLevel`` is bound at
        # import time, so this module would go on reporting the release
        # default even after setupLogging turned debug on. Asking the logger
        # is what keeps the two in step.
        logger = logging.getLogger('tafor')
        was = logger.level
        try:
            logger.setLevel(logging.DEBUG)

            fresh = LogPanel()
            qtbot.addWidget(fresh)
            offered = [fresh.levelBox.itemText(i) for i in range(fresh.levelBox.count())]
            assert offered[0] == 'DEBUG'
        finally:
            logger.setLevel(was)

    def test_each_level_entry_carries_its_own_number(self, panel):
        # The filter compares numbers; the box shows names. The number has
        # to travel with the entry rather than be looked up in a table that
        # would then have to be kept in step with the box.
        data = [panel.levelBox.itemData(i) for i in range(panel.levelBox.count())]

        assert data == [logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL]

    def test_the_level_filter_hides_what_is_below_it(self, panel):
        written(level=logging.INFO, message='routine')
        written(level=logging.ERROR, message='urgent')
        panel.poll()

        panel.levelBox.setCurrentText('ERROR')

        text = panel.text.toPlainText()
        assert 'urgent' in text
        assert 'routine' not in text

    def test_lowering_the_level_brings_the_lines_back(self, panel):
        written(level=logging.INFO, message='routine')
        panel.poll()
        panel.levelBox.setCurrentText('ERROR')
        assert 'routine' not in panel.text.toPlainText()

        panel.levelBox.setCurrentText('INFO')

        assert 'routine' in panel.text.toPlainText()

    def test_the_keyword_filter_matches_the_message(self, panel):
        written(message='connection is down')
        written(message='message sent')
        panel.poll()

        panel.filterEdit.setText('down')

        text = panel.text.toPlainText()
        assert 'connection is down' in text
        assert 'message sent' not in text

    def test_the_keyword_filter_matches_the_logger_name(self, panel):
        written(message='anything', name='tafor.rpc')
        written(message='anything', name='tafor.layer')
        panel.poll()

        panel.filterEdit.setText('rpc')

        assert 'tafor.rpc' in panel.text.toPlainText()
        assert 'tafor.layer' not in panel.text.toPlainText()

    def test_the_keyword_filter_ignores_case(self, panel):
        written(message='Connection Error')
        panel.poll()

        panel.filterEdit.setText('connection error')

        assert 'Connection Error' in panel.text.toPlainText()

    def test_clearing_the_keyword_filter_brings_the_lines_back(self, panel):
        written(message='connection is down')
        panel.poll()
        panel.filterEdit.setText('nothing matches')
        assert 'connection is down' not in panel.text.toPlainText()

        panel.filterEdit.setText('')

        assert 'connection is down' in panel.text.toPlainText()

    def test_a_new_record_is_filtered_as_it_arrives(self, panel):
        panel.filterEdit.setText('keep me')
        written(message='keep me')
        written(message='drop me')
        panel.poll()

        text = panel.text.toPlainText()
        assert 'keep me' in text
        assert 'drop me' not in text


class TestLogPanelScrolling:

    def test_following_scrolls_to_the_newest_line(self, panel):
        panel.followBox.setChecked(True)
        for index in range(60):
            written(message='line {}'.format(index))
            panel.poll()

        bar = panel.text.verticalScrollBar()
        assert bar.value() == bar.maximum()

    def test_not_following_leaves_the_reading_position_where_it_was(self, panel):
        for index in range(60):
            written(message='line {}'.format(index))
        panel.poll()

        bar = panel.text.verticalScrollBar()
        bar.setValue(0)                       # the operator scrolled to the top
        panel.followBox.setChecked(False)

        for index in range(60, 80):
            written(message='line {}'.format(index))
        panel.poll()

        assert bar.value() == 0


class TestLogPresenter:

    def makeView(self, qtbot):
        from PyQt5.QtWidgets import QAction, QMainWindow

        class FakeView(QMainWindow):
            pass

        view = FakeView()
        view.viewLogsAction = QAction(view)
        qtbot.addWidget(view)
        return view

    def test_the_action_shows_the_window_and_starts_reading(self, qtbot):
        view = self.makeView(qtbot)
        presenter = LogPresenter(view)
        presenter.initialize()

        view.viewLogsAction.trigger()

        assert presenter.logPanel.isVisible()
        assert presenter.timer.isActive()

    def test_the_window_starts_hidden(self, qtbot):
        view = self.makeView(qtbot)
        presenter = LogPresenter(view)

        assert not presenter.logPanel.isVisible()
        assert not presenter.timer.isActive()

    def test_closing_the_window_stops_reading(self, qtbot):
        view = self.makeView(qtbot)
        presenter = LogPresenter(view)
        presenter.initialize()
        view.viewLogsAction.trigger()

        presenter.logPanel.close()

        assert not presenter.timer.isActive()

    def test_pressing_escape_stops_reading(self, qtbot):
        view = self.makeView(qtbot)
        presenter = LogPresenter(view)
        presenter.initialize()
        view.viewLogsAction.trigger()

        # ESC rides QDialog's reject, which by default hides without a
        # closeEvent; the panel routes it through close so the X button and
        # the keyboard reach the same stop.
        presenter.logPanel.reject()

        assert not presenter.logPanel.isVisible()
        assert not presenter.timer.isActive()

    def test_the_window_is_shown_again_rather_than_rebuilt(self, qtbot):
        view = self.makeView(qtbot)
        presenter = LogPresenter(view)
        presenter.initialize()

        view.viewLogsAction.trigger()
        first = presenter.logPanel
        presenter.logPanel.close()
        view.viewLogsAction.trigger()

        assert presenter.logPanel is first
        assert presenter.logPanel.isVisible()
