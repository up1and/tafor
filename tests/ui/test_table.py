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
from tafor.ui.widgets.table import MetarTable, TafTable
from tafor.ui.workers import threadManager


TAF_TEXT = 'TAF ZPPP 100800Z 1009/1018 32008G15MPS 9999 SCT020='
AMD_TEXT = 'TAF AMD ZPPP 100900Z 1009/1018 32012MPS 9999 SCT020='
METAR_TEXT = 'METAR ZJHK 210900Z 14004MPS 4500 -RA BKN030='


@pytest.fixture(autouse=True)
def clean_thread_manager():
    yield
    threadManager.cleanup()


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
def taf_table(qtbot, conf, context, database, repos, container):
    widget, layout = container
    table = TafTable(widget, layout, conf=conf, context=context, repository=repos.message.taf)
    qtbot.addWidget(table)
    return table


@pytest.fixture
def metar_table(qtbot, conf, context, database, repos, container):
    widget, layout = container
    table = MetarTable(widget, layout, conf=conf, context=context, repository=repos.message.metar)
    qtbot.addWidget(table)
    return table


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


if __name__ == '__main__':
    pytest.main([__file__])
