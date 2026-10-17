"""Tests for tafor/ui/widgets/misc.py."""

import datetime
import re

import pytest

from PyQt5.QtCore import QSize
from PyQt5.QtGui import QFont, QImage

from tafor.ui.widgets.misc import Clock, LicenseEditor, OutlinedLabel, RemindMessageBox, TafBoard


@pytest.fixture
def container(qtbot):
    from PyQt5.QtWidgets import QVBoxLayout, QWidget
    widget = QWidget()
    qtbot.addWidget(widget)
    layout = QVBoxLayout(widget)
    widget.setLayout(layout)
    return widget, layout


class TestOutlinedLabel:

    @pytest.fixture
    def label(self, qtbot):
        label = OutlinedLabel('SIGMET')
        qtbot.addWidget(label)
        return label

    def test_scaled_thickness_follows_point_size(self, label):
        font = QFont()
        font.setPointSize(50)
        label.setFont(font)

        assert label.outlineThickness() == pytest.approx(50 / 25)

    def test_fixed_thickness(self, label):
        label.setScaledOutlineMode(False)
        label.setOutlineThickness(3)

        assert label.outlineThickness() == 3

    def test_thickness_is_clamped_to_one(self, label):
        label.setScaledOutlineMode(False)
        label.setOutlineThickness(0.1)

        assert label.outlineThickness() == 1

    def test_size_hint_grows_with_outline(self, label):
        from PyQt5.QtWidgets import QLabel
        base = QLabel('SIGMET')
        base.setFont(label.font())

        thickness = label.outlineThickness()
        grow = QSize(2 * round(thickness), 2 * round(thickness))

        assert label.sizeHint() == base.sizeHint() + grow

    def test_paint_with_text_does_not_crash(self, label):
        label.resize(200, 40)
        image = QImage(200, 40, QImage.Format_ARGB32)
        label.render(image)

        assert not image.isNull()

    # Note: painting an EMPTY OutlinedLabel raises IndexError inside
    # paintEvent (self.text()[0], misc.py:74). Qt swallows the exception and
    # pytest-qt reports it at teardown, so it cannot be pinned with
    # pytest.raises here; see the design notes.


class TestTafBoard:
    """The board is a passive view: the text is computed by BoardPresenter
    and pushed in through setText()."""

    @pytest.fixture
    def board(self, qtbot, container):
        widget, layout = container
        board = TafBoard(widget, layout)
        qtbot.addWidget(board)
        return board

    def test_set_text_renders_the_period_key(self, board):
        board.setText('FT1011')

        assert board.board.text() == 'FT1011'

    def test_set_text_to_empty_clears_the_board(self, board):
        board.setText('FT1011')
        board.setText('')

        assert board.board.text() == ''


class TestClock:

    def test_update_gui_formats_utc(self, qtbot, container):
        widget, layout = container
        clock = Clock(widget, layout)
        qtbot.addWidget(clock)
        try:
            clock.updateGui()
            assert re.match(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$', clock.label.text())
        finally:
            clock.timer.stop()


class TestLicenseEditor:
    """The editor normalises the typed key and reports it; verification and
    the conf write belong to the LicensePresenter (see test_main.py)."""

    @pytest.fixture
    def editor(self, qtbot):
        editor = LicenseEditor()
        qtbot.addWidget(editor)
        return editor

    def test_submit_emits_the_normalized_token(self, editor):
        seen = []
        editor.submitted.connect(seen.append)
        editor.textarea.setPlainText('  my token\n')

        editor.submit()

        assert seen == ['mytoken']

    def test_submit_emits_an_empty_key_when_nothing_is_typed(self, editor):
        seen = []
        editor.submitted.connect(seen.append)

        editor.submit()

        assert seen == ['']


class TestRemindMessageBox:

    def test_offers_dismiss_and_snooze(self, qtbot):
        box = RemindMessageBox()
        qtbot.addWidget(box)

        texts = sorted(button.text() for button in box.buttons())

        assert texts == ['Dismiss', 'Snooze']


if __name__ == '__main__':
    pytest.main([__file__])
