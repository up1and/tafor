import os

from PyQt5.QtCore import QSysInfo

from tafor.core.utils.common import iconPath


def flatButtonStyle():
    """Flat icon buttons over non-white surfaces: any stylesheet rule makes Qt
    draw the button box, so the resting state must say transparent explicitly."""
    hover = 'background: #f0f0f0; border: 1px solid #dcdcdc; border-radius: 2px;'
    return 'QToolButton {{ background: transparent; border: none; padding: 2px; }} ' \
           'QToolButton:hover, QToolButton:pressed {{ {} }}'.format(hover)

calendarStyle = """
    QCalendarWidget QAbstractItemView:enabled /* date of actual month */{
        color: #595959;
        selection-color: #fff;
        outline: 0px;
        alternate-background-color:#fff;/*  week and day frame */
    }

    QCalendarWidget QAbstractItemView:disabled /* date previous/next month */ {
        color:#b0b0b0;
    }

    QCalendarWidget #qt_calendar_navigationbar {
        padding: 2px;
        background:#fff;
        font-weight: bold;
    }
    /* year and month */
    QCalendarWidget QToolButton  {
        color: #262626;
        padding: 2px;
        margin: 2px;
        border: 0;
    }

    QCalendarWidget QToolButton:hover {
        color: #44a6f6;
    }

    /* oppress hook icon */
    QCalendarWidget QToolButton::menu-indicator {
        image: none;
    }
    QCalendarWidget #qt_calendar_nextmonth {
        color: #bfbfbf;
        qproperty-icon: none;
        qproperty-text: ">";
    }
    QCalendarWidget #qt_calendar_prevmonth {
        color: #bfbfbf;
        qproperty-icon: none;
        qproperty-text: "<"; 
    }

    QCalendarWidget #qt_calendar_prevmonth:hover, QCalendarWidget #qt_calendar_nextmonth:hover {
        color: black;
    }

"""

dateEditHiddenStyle = """
    QDateEdit {
        border: 1px solid transparent;
        padding: 2px; /* This (useless) line resolves a bug with the font color */
    }

    QDateEdit::drop-down
    {
        border: 0px; /* This seems to replace the whole arrow of the combo box */
    }

    /* Define a new custom arrow icon for the combo box */
    QDateEdit::down-arrow {
        image: url(%s);
        width: 16px;
        height: 16px;
    }

""" % iconPath('search.png').replace(os.sep, '/')

tabStyle = """
    QTabBar::tab {
        height: 22px;
    }
"""
