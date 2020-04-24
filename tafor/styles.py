from PyQt5.QtCore import QSysInfo

from tafor import conf


if QSysInfo.prettyProductName().startswith('Windows 10') and conf.value('General/WindowsStyle') == 'System':
    buttonHoverStyle = 'QToolButton:hover, QDateEdit:hover { background: #e5f3ff; border: 1px solid #cce8ff;}'
else:
    buttonHoverStyle = 'QToolButton:hover, QDateEdit:hover { background: #f0f0f0; border: 1px solid #999; border-radius: 3px;}'

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
        image: url(:/search.png);
        width: 16px;
        height: 16px;
    }

"""
