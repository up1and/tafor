"""Tests for tafor/ui/widgets/table.py.

The data tables query the repository directly, so every test runs against
the in-memory database. CSV export patches the native file dialog.
"""

import csv
import datetime

import pytest

from PyQt5.QtCore import QDate
from PyQt5.QtGui import QColor

from tafor.core.models import Taf
from tafor.core.repositories import Repositories
from tafor.ui.widgets.table import ExportDialog, MetarTable, TafTable
from tafor.ui.workers import WorkerPool


TAF_TEXT = 'TAF ZPPP 100800Z 1009/1018 32008G15MPS 9999 SCT020='
AMD_TEXT = 'TAF AMD ZPPP 100900Z 1009/1018 32012MPS 9999 SCT020='
METAR_TEXT = 'METAR ZJHK 210900Z 14004MPS 4500 -RA BKN030='


@pytest.fixture
def container(qtbot):
    from PyQt5.QtWidgets import QVBoxLayout, QWidget
    widget = QWidget()
    qtbot.addWidget(widget)
    layout = QVBoxLayout(widget)
    widget.setLayout(layout)
    return widget, layout


@pytest.fixture
def repos(database):
    return Repositories(database)


@pytest.fixture
def pool():
    """A pool whose manager is cleaned up with the test.

    A table builds its own pool when none is passed, and that pool owns a
    ThreadManager: the CSV export test starts a real thread through it, so it
    has to be the fixture's to shut down.
    """
    pool = WorkerPool()
    yield pool
    pool.cleanup()


@pytest.fixture
def taf_table(qtbot, repos, container, pool):
    widget, layout = container
    table = TafTable(widget, layout, pool, repository=repos.message.taf)
    qtbot.addWidget(table)
    return table


@pytest.fixture
def metar_table(qtbot, repos, container, pool):
    widget, layout = container
    table = MetarTable(widget, layout, pool, repository=repos.message.metar)
    qtbot.addWidget(table)
    return table


class FakeSignal:
    """A pyqtSignal reduced to connect()"""

    def __init__(self):
        self.targets = []

    def connect(self, target):
        self.targets.append(target)


class InertWorker:
    """Enough of a worker for the dialog to connect and start it."""

    def __init__(self, *args, **kwargs):
        self.finished = FakeSignal()


class InertThread:
    """A thread that records the start and runs nothing."""

    def __init__(self):
        self.started = 0

    def start(self):
        self.started += 1


class RecordingPool:
    """A WorkerPool handed to the widgets instead of the shared manager."""

    def __init__(self):
        self.created = []

    def create(self, workerClass, *args, **kwargs):
        self.created.append((workerClass, args, kwargs))
        return InertWorker(), InertThread()


def seed_taf(database, text=TAF_TEXT, created=None, confirmed=None, type='FT'):
    taf = Taf(type=type, text=text, confirmed=confirmed,
              created=created or datetime.datetime.utcnow())
    with database.session() as session:
        session.add(taf)
    return taf


class TestTafTable:

    def test_update_table_renders_rows(self, taf_table, database):
        seed_taf(database, TAF_TEXT)
        seed_taf(database, AMD_TEXT, confirmed=datetime.datetime.utcnow())

        taf_table.updateGui()

        assert taf_table.table.rowCount() == 2
        assert taf_table.pagesLabel.text() == '1/1'
        # rows are ordered newest first
        texts = [taf_table.table.item(row, 1).text() for row in range(2)]
        assert texts == [AMD_TEXT, TAF_TEXT]
        created = taf_table.table.item(0, 2).text()
        assert datetime.datetime.strptime(created, '%Y-%m-%d %H:%M:%S')

    def test_checkmark_column(self, taf_table, database):
        seed_taf(database, TAF_TEXT)
        taf_table.updateGui()

        assert taf_table.table.cellWidget(0, 3) is not None

    def test_auto_search_uppercases_and_splits(self, taf_table):
        taf_table.search.setText('taf zppp')
        taf_table.autoSearch()

        assert taf_table.search.text() == 'TAF ZPPP'
        assert taf_table.keywords == ['TAF', 'ZPPP']

    def test_search_filters_rows(self, taf_table, database):
        seed_taf(database, TAF_TEXT)
        seed_taf(database, AMD_TEXT)
        taf_table.updateGui()
        assert taf_table.table.rowCount() == 2

        taf_table.search.setText('32012')
        taf_table.autoSearch()

        assert taf_table.table.rowCount() == 1
        assert taf_table.table.item(0, 1).text() == AMD_TEXT

    def test_pagination_walks_pages(self, taf_table, database):
        for index in range(13):
            seed_taf(database, '{} {}'.format(TAF_TEXT, index))

        taf_table.updateGui()
        assert taf_table.pagesLabel.text() == '1/2'

        taf_table.next()
        assert taf_table.page == 2
        assert taf_table.table.rowCount() == 1
        assert taf_table.pagesLabel.text() == '2/2'

        taf_table.prev()
        assert taf_table.page == 1
        assert taf_table.table.rowCount() == 12

    def test_a_new_record_recounts_the_pages_on_repaint(self, taf_table, database):
        for index in range(12):
            seed_taf(database, '{} {}'.format(TAF_TEXT, index))

        taf_table.updateGui()
        assert taf_table.pagesLabel.text() == '1/1'

        # a record stored after the last repaint must invalidate the old count
        seed_taf(database, '{} 13'.format(TAF_TEXT))
        taf_table.updateGui()

        assert taf_table.pagesLabel.text() == '1/2'
        taf_table.next()
        assert taf_table.page == 2
        assert taf_table.table.rowCount() == 1

    def test_next_at_last_page_steps_the_date(self, taf_table, database):
        seed_taf(database, TAF_TEXT)
        today = datetime.date.today()
        taf_table.setCalendar(QDate(today.year, today.month, today.day))
        assert taf_table.table.rowCount() == 1

        # a single row means no next page: the date advances instead
        taf_table.next()
        assert taf_table.date == today + datetime.timedelta(days=1)
        assert taf_table.table.rowCount() == 0

        taf_table.prev()
        assert taf_table.date == today
        assert taf_table.table.rowCount() == 1

    def test_set_calendar_filters_by_date(self, taf_table, database):
        yesterday = datetime.datetime.utcnow() - datetime.timedelta(days=1)
        seed_taf(database, TAF_TEXT, created=yesterday)
        seed_taf(database, AMD_TEXT)

        today = QDate.currentDate()
        taf_table.setCalendar(today)
        assert taf_table.date == datetime.date(today.year(), today.month(), today.day())
        assert taf_table.table.rowCount() == 1

        taf_table.setCalendar(None)
        assert taf_table.date is None
        assert taf_table.table.rowCount() == 2

    def test_update_info_button_follows_selection(self, taf_table, database):
        seed_taf(database, TAF_TEXT)
        taf_table.updateGui()

        # the button only appears when exactly one cell is selected
        taf_table.table.item(0, 1).setSelected(True)

        assert taf_table.infoButton.isVisibleTo(taf_table)
        assert taf_table.selected.text == TAF_TEXT

        taf_table.table.clearSelection()
        assert not taf_table.infoButton.isVisibleTo(taf_table)
        assert taf_table.selected is None

    def test_full_row_selection_keeps_info_button_hidden(self, taf_table, database):
        seed_taf(database, TAF_TEXT)
        taf_table.updateGui()

        taf_table.table.selectRow(0)

        assert not taf_table.infoButton.isVisibleTo(taf_table)

    def test_amended_row_is_decorated(self, taf_table, database):
        seed_taf(database, TAF_TEXT)
        seed_taf(database, AMD_TEXT)
        taf_table.updateGui()

        amended = taf_table.table.item(0, 0).foreground().color()
        normal = taf_table.table.item(1, 0).foreground().color()

        assert amended == QColor(200, 20, 40)
        assert normal != QColor(200, 20, 40)

    def test_double_click_copies_to_clipboard(self, taf_table, database):
        seed_taf(database, TAF_TEXT)
        taf_table.updateGui()

        from PyQt5.QtWidgets import QApplication
        taf_table.copySelected(taf_table.table.item(0, 1))

        assert QApplication.clipboard().text() == TAF_TEXT


class TestMetarTable:

    def test_checkmark_column_is_hidden(self, metar_table):
        assert metar_table.perPage == 24
        assert metar_table.table.isColumnHidden(3)

    def test_special_report_is_decorated(self, metar_table, database):
        from tafor.core.models import Metar
        now = datetime.datetime.utcnow()
        with database.session() as session:
            session.add(Metar(type='SA', text=METAR_TEXT, created=now))
            session.add(Metar(type='SP', text='SPECI ZJHK 211000Z 14004MPS 0800 TSRA=', created=now))

        metar_table.updateGui()

        special = metar_table.table.item(0, 0).foreground().color()
        routine = metar_table.table.item(1, 0).foreground().color()

        assert special == QColor(200, 20, 40)
        assert routine != QColor(200, 20, 40)

    def test_info_button_stays_hidden(self, metar_table, database):
        from tafor.core.models import Metar
        with database.session() as session:
            session.add(Metar(type='SA', text=METAR_TEXT, created=datetime.datetime.utcnow()))

        metar_table.updateGui()
        metar_table.table.item(0, 1).setSelected(True)

        assert not metar_table.infoButton.isVisibleTo(metar_table)


class TestExportDialog:

    def test_empty_report_disables_save(self, taf_table):
        dialog = taf_table.exportDialog
        dialog.updateExportStatus()

        assert not dialog.saveButton.isEnabled()
        assert dialog.countLabel.text() == ''

    def test_report_count_enables_save(self, taf_table, database):
        seed_taf(database, TAF_TEXT)
        dialog = taf_table.exportDialog

        today = QDate.currentDate()
        dialog.startDate.setDate(today)
        dialog.endDate.setDate(today)
        dialog.updateExportStatus()

        assert dialog.saveButton.isEnabled()
        assert '1' in dialog.countLabel.text()

    def test_export_writes_csv(self, taf_table, database, qtbot, tmp_path, monkeypatch):
        seed_taf(database, TAF_TEXT)
        dialog = taf_table.exportDialog
        today = QDate.currentDate()
        dialog.startDate.setDate(today)
        dialog.endDate.setDate(today)
        dialog.updateExportStatus()

        target = tmp_path / 'export.csv'
        monkeypatch.setattr(
            'tafor.ui.widgets.table.QFileDialog.getSaveFileName',
            lambda *args, **kwargs: (str(target), ''))

        dialog.saveButton.click()
        qtbot.waitUntil(lambda: target.exists())

        with open(target, newline='') as file:
            rows = list(csv.reader(file))

        assert rows[0] == ['type', 'text', 'created']
        assert rows[1][:2] == ['FT', TAF_TEXT]


class TestExportWorkers:
    """The export dialog borrows a pool instead of reaching for the shared
    thread manager, so it can be driven without starting a real thread."""

    def build(self, qtbot, workers, repository=None):
        from PyQt5.QtWidgets import QVBoxLayout, QWidget

        widget, layout = QWidget(), QVBoxLayout()
        widget.setLayout(layout)
        qtbot.addWidget(widget)
        table = TafTable(widget, layout, workers, repository=repository)
        # the caller keeps the container alive: the table is only a child of it
        self.container = widget
        self.table = table
        return table

    def test_the_table_hands_its_pool_to_the_export_dialog(self, qtbot):
        pool = RecordingPool()

        table = self.build(qtbot, pool)

        assert table.exportDialog.workers is pool

    def test_the_export_uses_the_injected_pool(self, qtbot, database, tmp_path, monkeypatch):
        pool = RecordingPool()
        table = self.build(qtbot, pool, repository=Repositories(database).message.taf)

        seed_taf(database, TAF_TEXT)

        dialog = table.exportDialog
        today = QDate.currentDate()
        dialog.startDate.setDate(today)
        dialog.endDate.setDate(today)
        dialog.updateExportStatus()

        monkeypatch.setattr(
            'tafor.ui.widgets.table.QFileDialog.getSaveFileName',
            lambda *args, **kwargs: (str(tmp_path / 'export.csv'), ''))
        dialog.saveButton.click()

        assert len(pool.created) == 1
        workerClass, args, kwargs = pool.created[0]
        assert workerClass.__name__ == 'ExportRecordWorker'
        assert kwargs == {'headers': ('type', 'text', 'created')}

    def test_the_pool_is_not_optional(self, qtbot):
        # a dialog that quietly built its own pool would leave a manager
        # nobody ever cleans up, so omitting it has to fail loudly
        with pytest.raises(TypeError):
            ExportDialog()


if __name__ == '__main__':
    pytest.main([__file__])
