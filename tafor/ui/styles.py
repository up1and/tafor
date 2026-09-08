
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

tabStyle = """
    QTabBar::tab {
        height: 22px;
    }
"""
