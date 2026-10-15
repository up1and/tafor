"""Widget styling, written so that the platform theme is what decides colour.

Nothing here hardcodes a text or surface colour. The sheets name a palette
role instead -- ``palette(text)``, ``palette(base)`` -- and Qt resolves the
role when the sheet is applied. A literal such as ``color: black`` cannot
follow the platform into dark mode, which is what used to leave white cards
and black editor text on a dark desktop.

The one thing Qt does not do for us: ``palette()`` is resolved once, at
apply time, and cached in the compiled sheet. Changing the platform theme
therefore does not restyle anything by itself, so ``applyCalendarStyle``
listens for the palette change and re-applies the same sheet, which is
enough to make Qt resolve the roles again.

Every colour here is now a role, including the selection and the hover
accent: ``palette(highlight)`` and ``palette(highlightedtext)`` cover both,
and Qt keeps the selection solid when the window is inactive because a sheet
is not re-resolved against the inactive group.
"""

from PyQt5.QtCore import QEvent, QObject, Qt
from PyQt5.QtGui import QPalette, QTextCharFormat


#: The calendar sheet. Roles, not literals: a literal cannot follow the
#: platform into dark mode, which is what used to leave white cards and black
#: text on a dark desktop.
calendarSheet = """
    QCalendarWidget QAbstractItemView:enabled /* date of actual month */{
        color: palette(text);
        selection-background-color: palette(highlight);
        selection-color: palette(highlightedtext);
        outline: 0px;
        background: palette(base);
        alternate-background-color: palette(base); /* week and day frame */
    }

    QCalendarWidget QAbstractItemView:disabled /* date previous/next month */ {
        color: palette(placeholdertext);
    }

    QCalendarWidget #qt_calendar_navigationbar {
        padding: 4px 6px;
        background: palette(base);
        font-weight: bold;
    }

    /* year and month */
    QCalendarWidget QToolButton {
        color: palette(text);
        padding: 2px;
        margin: 2px;
        border: 0;
        background: transparent;
    }

    QCalendarWidget QToolButton:hover {
        color: palette(highlight);
        background-color: palette(midlight);
    }

    QCalendarWidget QToolButton:pressed {
        background-color: palette(mid);
    }

    /* oppress hook icon */
    QCalendarWidget QToolButton::menu-indicator {
        image: none;
    }

    QCalendarWidget #qt_calendar_prevmonth,
    QCalendarWidget #qt_calendar_nextmonth {
        color: palette(dark);
        qproperty-icon: none;
    }

    QCalendarWidget #qt_calendar_nextmonth {
        qproperty-text: ">";
    }

    QCalendarWidget #qt_calendar_prevmonth {
        qproperty-text: "<";
    }

    QCalendarWidget #qt_calendar_prevmonth:hover, QCalendarWidget #qt_calendar_nextmonth:hover {
        color: palette(highlight);
    }

    /* weekday header */
    QCalendarWidget QHeaderView::section {
        background: palette(base);
        color: palette(placeholdertext);
        border: 0;
        font-weight: normal;
    }
    """


def applyCalendarStyle(calendar):
    """Style a QCalendarWidget so it follows the platform theme.

    Applies the sheet, sets the weekend colour, and keeps both in step with
    the palette from then on: a sheet is resolved when it is applied and then
    cached, so a theme switch does not restyle anything by itself.
    """

    class Watcher(QObject):
        """Re-applies the sheet when the platform palette moves.

        setStyleSheet() emits a PaletteChange of its own, so the base colour
        is compared against the one the last apply saw: only a real move
        restyles, and an apply cannot trigger itself.
        """

        def __init__(self, calendar):
            super().__init__(calendar)
            self.calendar = calendar
            self.base = None
            calendar.installEventFilter(self)

        def apply(self):
            # The sheet goes on first: it writes its own colours back into the
            # widget's palette, and the base recorded below must be the one a
            # re-apply would see, or the comparison would never settle.
            self.calendar.setStyleSheet(calendarSheet)

            # The weekend colour is code, not stylesheet, so it has to be
            # reset here too or it stays on the theme it was set under.
            muted = QTextCharFormat()
            muted.setForeground(self.calendar.palette().brush(QPalette.PlaceholderText))
            for day in (Qt.Saturday, Qt.Sunday):
                self.calendar.setWeekdayTextFormat(day, muted)

            self.base = self.calendar.palette().color(QPalette.Base).name()

        def eventFilter(self, obj, event):
            if event.type() == QEvent.PaletteChange:
                if self.calendar.palette().color(QPalette.Base).name() != self.base:
                    self.apply()

            return False

    watcher = Watcher(calendar)
    watcher.apply()
    # Reachable from the widget it styles, so callers and tests can see what
    # is driving it rather than having to hold the return value.
    calendar.calendarStyler = watcher
    return watcher


#: Secondary text: hints, counts and other labels that should recede.
mutedStyle = 'QLabel {color: palette(placeholdertext);}'

#: An input whose contents are complete and acceptable.
validTextStyle = 'color: palette(text);'

#: An input whose contents are still missing something.
invalidTextStyle = 'color: palette(placeholdertext);'
