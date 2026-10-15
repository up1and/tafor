"""Tests for tafor/ui/styles.py.

The point of this module is that colour comes from the platform palette and
nothing else, so a dark desktop gets dark widgets. Two things can go wrong
quietly and are pinned here: a literal colour creeping back into a sheet
(which cannot follow the theme), and the theme switch not reaching the
widget (because Qt resolves palette() once, at apply time).
"""

import pytest

from PyQt5.QtCore import QObject, Qt
from PyQt5.QtGui import QColor, QPalette
from PyQt5.QtWidgets import QCalendarWidget, QLabel

from tafor.ui import styles
from tafor.ui.styles import (
    applyCalendarStyle,
    invalidTextStyle,
    mutedStyle,
    validTextStyle,
)


# Rules that describe the widget's shape rather than its colour. Rewriting a
# sheet for theming is exactly when these get dropped, and dropping one
# silently changes the widget, so they are listed and checked.
STRUCTURAL_RULES = [
    'padding: 4px 6px',                     # navigation bar padding
    'font-weight: bold',                    # navigation bar
    'QCalendarWidget QToolButton {',        # year/month buttons
    'margin: 2px',
    'border: 0',
    'QCalendarWidget QToolButton:hover',
    'QCalendarWidget QToolButton:pressed',
    'QCalendarWidget QToolButton::menu-indicator',
    'QHeaderView::section',                 # weekday header
    'qproperty-text: ">"',
    'qproperty-text: "<"',
    'qproperty-icon: none',
]

def light_palette():
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor('#efefef'))
    palette.setColor(QPalette.Base, QColor('#ffffff'))
    palette.setColor(QPalette.Text, QColor('#000000'))
    palette.setColor(QPalette.PlaceholderText, QColor('#8a8a8a'))
    palette.setColor(QPalette.Midlight, QColor('#e3e3e3'))
    palette.setColor(QPalette.Mid, QColor('#b8b8b8'))
    palette.setColor(QPalette.Dark, QColor('#9f9f9f'))
    return palette


def dark_palette():
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor('#1e1e1e'))
    palette.setColor(QPalette.Base, QColor('#252525'))
    palette.setColor(QPalette.Text, QColor('#ffffff'))
    palette.setColor(QPalette.PlaceholderText, QColor('#a0a0a0'))
    palette.setColor(QPalette.Midlight, QColor('#3a3a3a'))
    palette.setColor(QPalette.Mid, QColor('#4a4a4a'))
    palette.setColor(QPalette.Dark, QColor('#6a6a6a'))
    return palette


@pytest.fixture
def restore_palette(qapp):
    """Put the application palette back however the test leaves it."""
    original = QPalette(qapp.palette())
    yield
    qapp.setPalette(original)
    settle(qapp)


@pytest.fixture
def calendar(qtbot, restore_palette):
    widget = QCalendarWidget()
    qtbot.addWidget(widget)
    applyCalendarStyle(widget)
    return widget


def settle(qapp, rounds=10):
    """Let the queued palette-change round trip finish."""
    for _ in range(rounds):
        qapp.processEvents()


def switch_to(qapp, palette):
    qapp.setPalette(palette)
    settle(qapp)


class TestSheetsFollowThePalette:
    """No sheet may name a text or surface colour directly."""

    @pytest.mark.parametrize('sheet', [mutedStyle, validTextStyle, invalidTextStyle])
    def test_the_text_styles_ask_for_a_role(self, sheet):
        assert 'palette(' in sheet

    def test_the_text_styles_hold_no_colour_literal(self):
        for sheet in (mutedStyle, validTextStyle, invalidTextStyle):
            assert '#' not in sheet, sheet
            for named in ('black', 'white', 'grey', 'gray'):
                assert named not in sheet, sheet

    def test_the_calendar_sheet_keeps_its_structural_rules(self, calendar):
        for rule in STRUCTURAL_RULES:
            assert rule in calendar.styleSheet(), rule

    def test_the_calendar_sheet_has_no_literal_colours(self, calendar):
        # Every colour is a palette() role, so nothing here can pin the
        # calendar to the theme it happened to be applied under.
        import re
        colours = re.findall(r'#[0-9a-fA-F]{3,6}', calendar.styleSheet())
        assert colours == []

    def test_the_calendar_surface_comes_from_the_palette(self, calendar):
        sheet = calendar.styleSheet()
        assert 'background: palette(base)' in sheet
        assert 'color: palette(text)' in sheet


class TestThemeSwitchReachesTheWidget:
    """palette() is resolved once at apply time, so a switch needs a re-apply."""

    def test_a_dark_palette_rewrites_the_calendar(self, calendar, qapp):
        switch_to(qapp, light_palette())
        light = calendar.styleSheet()

        switch_to(qapp, dark_palette())

        assert calendar.calendarStyler.base \
            == dark_palette().color(QPalette.Base).name()
        # The sheet text is identical; what moves is what Qt resolved it to.
        assert calendar.styleSheet() == light

    def test_the_weekend_colour_moves_with_the_theme(self, calendar, qapp):
        switch_to(qapp, dark_palette())

        expected = calendar.palette().brush(QPalette.PlaceholderText).color().name()
        for day in (Qt.Saturday, Qt.Sunday):
            fmt = calendar.weekdayTextFormat(day)
            assert fmt.foreground().color().name() == expected

    def test_the_watcher_does_not_re_enter_itself_on_apply(self, calendar, qapp):
        # setStyleSheet() emits a PaletteChange of its own, and an unguarded
        # watcher answers it with another setStyleSheet() -- which recurses
        # inside Qt's dispatch until the interpreter stack goes. Applying and
        # then turning the event loop is what used to trip that, so this
        # simply has to come back with the widget still standing.
        calendar.calendarStyler.apply()

        settle(qapp, rounds=50)

        assert calendar.calendarStyler.base \
            == calendar.palette().color(QPalette.Base).name()

    def test_a_palette_change_that_leaves_the_base_alone_is_ignored(
            self, calendar, qapp, monkeypatch):
        # A palette change does not imply a colour change: moving Window alone
        # still emits PaletteChange. The base is what the sheet actually
        # paints with, so when it has not moved the rewrite is skipped --
        # which is also what keeps an apply from triggering the next one.
        styler = calendar.calendarStyler
        styler.apply()
        settle(qapp)

        applied = []
        monkeypatch.setattr(styler, 'apply', lambda: applied.append(1))

        moved = QPalette(qapp.palette())
        moved.setColor(QPalette.Window, QColor('#123456'))
        switch_to(qapp, moved)

        assert applied == []

    def test_a_real_theme_move_does_reach_apply(
            self, calendar, qapp, monkeypatch):
        # The counterpart: a base that really moved must get through the
        # guard, or the guard would have swallowed the very thing it exists
        # to let past.
        styler = calendar.calendarStyler
        apply = styler.apply
        applied = []

        def counting():
            applied.append(1)
            apply()

        monkeypatch.setattr(styler, 'apply', counting)

        switch_to(qapp, dark_palette())

        assert applied
        assert styler.base == dark_palette().color(QPalette.Base).name()

    def test_the_calendar_survives_a_round_trip(self, calendar, qapp):
        switch_to(qapp, light_palette())
        assert calendar.calendarStyler.base == '#ffffff'

        switch_to(qapp, dark_palette())
        assert calendar.calendarStyler.base == '#252525'

        switch_to(qapp, light_palette())
        assert calendar.calendarStyler.base == '#ffffff'


class TestTheWatcher:
    """The watcher is the piece that makes the switch arrive at all."""

    def test_apply_calendar_style_returns_a_watcher(self, qtbot, restore_palette):
        widget = QCalendarWidget()
        qtbot.addWidget(widget)

        watcher = applyCalendarStyle(widget)

        assert watcher is widget.calendarStyler
        assert isinstance(watcher, QObject)

    def test_the_watcher_is_parented_to_the_calendar(self, calendar):
        # Parenting is what keeps it alive; a bare reference would be
        # collected and the theme switch would silently stop arriving.
        assert calendar.calendarStyler.parent() is calendar

    def test_the_watcher_styles_the_widget_it_listens_on(self, calendar, qapp):
        # The watcher must be installed on the calendar, not on the app:
        # QApplication does not receive the palette change, widgets do.
        widget = calendar.calendarStyler.calendar

        assert widget is calendar
        assert widget.styleSheet() == calendar.styleSheet()

    def test_no_watcher_is_installed_twice(self, calendar, qapp):
        # applyCalendarStyle() is called once per calendar today, but a
        # second call must not leave a stale watcher behind.
        before = calendar.calendarStyler

        applyCalendarStyle(calendar)

        assert calendar.calendarStyler is not before

    def test_a_widget_stylesheet_pollution_is_not_read_as_the_theme(
            self, calendar, qapp):
        # A stylesheet writes its colours back into the widget's own palette,
        # so reading the widget would let the sheet decide the next theme.
        # The watcher reads the widget, which is why this is worth pinning:
        # what it compares is the base the last apply recorded, not a theme
        # guess, so a sheet's own pollution cannot flip it.
        before = calendar.calendarStyler.base

        calendar.setStyleSheet('QCalendarWidget { background: #abcdef; }')
        settle(qapp)

        assert calendar.calendarStyler.base == before


class TestEditorsUseTheStyles:
    """The three text styles reach the editors through the same names."""

    def test_a_valid_field_asks_for_the_text_role(self, qtbot):
        line = QLabel()
        qtbot.addWidget(line)
        line.setStyleSheet(validTextStyle)

        assert 'palette(text)' in line.styleSheet()

    def test_an_invalid_field_asks_for_the_muted_role(self, qtbot):
        line = QLabel()
        qtbot.addWidget(line)
        line.setStyleSheet(invalidTextStyle)

        assert 'palette(placeholdertext)' in line.styleSheet()

    def test_muted_labels_ask_for_the_muted_role(self, qtbot):
        label = QLabel('UTC')
        qtbot.addWidget(label)
        label.setStyleSheet(mutedStyle)

        assert 'palette(placeholdertext)' in label.styleSheet()


class TestModuleSurface:
    """The names callers import, and the literals that used to be here."""

    def test_the_module_no_longer_ships_colour_tables(self):
        for gone in ('LIGHT_CALENDAR', 'DARK_CALENDAR', 'calendarStyle',
                     'CALENDAR_SHEET', 'calendarColors', 'isdark_palette'):
            assert not hasattr(styles, gone), gone

    def test_apply_calendar_style_is_still_the_entry_point(self):
        assert callable(styles.applyCalendarStyle)
