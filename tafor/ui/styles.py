
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QTextCharFormat


calendarStyle = """
    QCalendarWidget QAbstractItemView:enabled /* date of actual month */{
        color: #191919;
        /* Explicit highlight color keeps the selected day solid when the
           window is inactive (Windows fades the palette highlight color) */
        selection-background-color: #0078d7;
        selection-color: #fff;
        outline: 0px;
        background: #fff;
        alternate-background-color: #fff; /* week and day frame */
    }

    QCalendarWidget QAbstractItemView:disabled /* date previous/next month */ {
        color: #a6a6a6;
    }

    QCalendarWidget #qt_calendar_navigationbar {
        padding: 4px 6px;
        background: #fff;
        font-weight: bold;
    }

    /* year and month */
    QCalendarWidget QToolButton {
        color: #191919;
        padding: 2px;
        margin: 2px;
        border: 0;
        background: transparent;
    }

    QCalendarWidget QToolButton:hover {
        color: #0078d7;
        background-color: #f5f5f5;
    }

    QCalendarWidget QToolButton:pressed {
        background-color: #ebebeb;
    }

    /* oppress hook icon */
    QCalendarWidget QToolButton::menu-indicator {
        image: none;
    }

    QCalendarWidget #qt_calendar_prevmonth,
    QCalendarWidget #qt_calendar_nextmonth {
        color: #5d5d5d;
        qproperty-icon: none;
    }

    QCalendarWidget #qt_calendar_nextmonth {
        qproperty-text: ">";
    }

    QCalendarWidget #qt_calendar_prevmonth {
        qproperty-text: "<";
    }

    QCalendarWidget #qt_calendar_prevmonth:hover, QCalendarWidget #qt_calendar_nextmonth:hover {
        color: #0078d7;
    }

    /* weekday header */
    QCalendarWidget QHeaderView::section {
        background: #fff;
        color: #707070;
        border: 0;
        font-weight: normal;
    }
"""


def applyCalendarStyle(calendar):
    """Apply QSS styling and reset weekend colors for QCalendarWidget."""
    calendar.setStyleSheet(calendarStyle)

    muted = QTextCharFormat()
    muted.setForeground(QColor('#707070'))
    calendar.setWeekdayTextFormat(Qt.Saturday, muted)
    calendar.setWeekdayTextFormat(Qt.Sunday, muted)

