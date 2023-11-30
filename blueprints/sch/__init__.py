"""Schedules informations.

No inputs from other user modules as this could raise circular import errors.
This is accessed by database.py, daily_task, tests and other modules.
All schedules info should come from here.
"""

from typing import NamedTuple

from flask_babel import lazy_gettext


# region: schedule names and details
class ScheduleInfo(NamedTuple):
    """Centralized app schedules information.

    :param type: type of the schedule (group | individual)
    :param name: schedule name
    :param positive: schedule positive message
    :param negative: schedule negative message
    :param sch_day: day of the week when the schedule starts
    :param sch_day_update: day of the week when the schedule updates
    :param switch_interval: switching time interval (weeks)
    """
    type: str
    name: str
    positive: str
    negative: str
    sch_day: int
    sch_day_update: int
    switch_interval: int


sat_sch_info = ScheduleInfo(
    type="group",
    name=lazy_gettext("Saturday movie"),
    positive=lazy_gettext("You're choosing the movie this saturday"),
    negative=lazy_gettext("You're not choosing the movie this saturday"),
    sch_day=6,
    sch_day_update=7,
    switch_interval=1
)

clean_sch_info = ScheduleInfo(
    type="individual",
    name=lazy_gettext("Cleaning schedule"),
    positive=lazy_gettext("You're scheduled for cleaning this week"),
    negative=lazy_gettext("You're not scheduled for cleaning this week"),
    sch_day=1,
    sch_day_update=6,
    switch_interval=1
)
# endregion
