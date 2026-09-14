"""Tests for tafor/ui/widgets/misc.py."""

import datetime
import re

import pytest

from PyQt5.QtCore import QSize
from PyQt5.QtGui import QFont, QImage

from tafor.core.models import Taf
from tafor.ui.widgets.misc import Clock, LicenseEditor, OutlinedLabel, RemindMessageBox, TafBoard


@pytest.fixture
def container(qtbot):
    from PyQt5.QtWidgets import QVBoxLayout, QWidget
    widget = QWidget()
    qtbot.addWidget(widget)
    layout = QVBoxLayout(widget)
    widget.setLayout(layout)
    return widget, layout


@pytest.fixture
def license_conf(conf):
    """conf is session-scoped: reset the stored license after each test."""
    yield conf
    conf.license = ''


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

    @pytest.fixture
    def board(self, qtbot, conf, context, container):
        widget, layout = container
        board = TafBoard(widget, layout, conf=conf, context=context)
        qtbot.addWidget(board)
        return board

    def test_current_shows_the_expected_period(self, board):
        assert re.match(r'^FT\d{4}$', board.current())

    def test_current_is_empty_with_a_message(self, board, context):
        context.taf.setState({'message': Taf(type='FT', text='TAF YUSO=')})

        assert board.current() == ''

    def test_update_gui_renders_current(self, board):
        board.updateGui()

        assert board.board.text() == board.current()


class TestClock:

    def test_update_gui_formats_utc(self, qtbot, container, context):
        widget, layout = container
        clock = Clock(widget, layout, context=context)
        qtbot.addWidget(clock)
        try:
            clock.updateGui()
            assert re.match(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$', clock.label.text())
        finally:
            clock.timer.stop()


class TestLicenseEditor:

    @pytest.fixture
    def editor(self, qtbot, license_conf, context):
        editor = LicenseEditor(conf=license_conf, context=context)
        qtbot.addWidget(editor)
        return editor

    def test_set_license_emits_once_on_change(self, editor, license_conf):
        changes = []
        editor.licenseChanged.connect(lambda: changes.append(1))

        editor.setLicense('TOKEN')
        assert license_conf.license == 'TOKEN'

        editor.setLicense('TOKEN')
        assert changes == [1]

    def test_remove_license_clears_config(self, editor, license_conf):
        editor.setLicense('TOKEN')
        editor.removeLicense()

        assert license_conf.license == ''

    def test_save_stores_normalized_token(self, editor, license_conf, context, monkeypatch):
        monkeypatch.setattr(context.license, 'license', lambda token=None: {'airport': 'YUSO'} if token else {})
        editor.textarea.setPlainText('  my token\n')

        editor.save()

        assert license_conf.license == 'mytoken'
        assert editor.textarea.toPlainText() == ''

    def test_save_rejects_invalid_token(self, editor, license_conf, context, monkeypatch):
        monkeypatch.setattr(context.license, 'license', lambda token=None: {})
        criticals = []
        monkeypatch.setattr('tafor.ui.widgets.misc.QMessageBox.critical',
                            lambda *args, **kwargs: criticals.append(args))
        editor.textarea.setPlainText('BAD TOKEN')

        editor.save()

        assert criticals
        assert license_conf.license == ''
        assert editor.textarea.toPlainText() == 'BAD TOKEN'


class TestRemindMessageBox:

    def test_offers_dismiss_and_snooze(self, qtbot):
        box = RemindMessageBox()
        qtbot.addWidget(box)

        texts = sorted(button.text() for button in box.buttons())

        assert texts == ['Dismiss', 'Snooze']


if __name__ == '__main__':
    pytest.main([__file__])
