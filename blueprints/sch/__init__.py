"""Schedules informations.

No imputs from other user modules as this could raise circular import errors.
This is accesed by database.py, daily_task, tests and other modules.
All schedules info should come from here.
"""

from typing import NamedTuple

from flask_babel import lazy_gettext


# region: schedule names and details
class ScheduleInfo(NamedTuple):
    """Centralized app schedules information.

    - `*_en` versions should be used in app logic; they are not translatable
    - versions without `*_en` are translatable (lazy_gettext) and should be used
        in the web interface
    :param type: type of the schedule (group | individual)
    :param name_en: schedule name
    :param name: translatable name
    :param positive_en: message if next scheduled day is this week
    :param positive: translatable positive message
    :param negative_en: message if next scheduled day is not this week
    :param negative: translatable negative message
    :param sch_day: day of the week when the schedule starts
    :param sch_day_update: day of the week when the schedule updates
    :param switch_interval: switching time interval (weeks)
    """
    type: str
    name_en: str
    name: str
    positive_en: str
    positive: str
    negative_en: str
    negative: str
    sch_day: int
    sch_day_update: int
    switch_interval: int


sat_sch_info = ScheduleInfo(
    type="group",
    name_en="Saturday movie",
    name=lazy_gettext("Saturday movie"),
    positive_en="You're choosing the movie this saturday",
    positive=lazy_gettext("You're choosing the movie this saturday"),
    negative_en="You're not choosing the movie this saturday",
    negative=lazy_gettext("You're not choosing the movie this saturday"),
    sch_day=6,
    sch_day_update=7,
    switch_interval=1
)

clean_sch_info = ScheduleInfo(
    type="individual",
    name_en="Cleaning schedule",
    name=lazy_gettext("Cleaning schedule"),
    positive_en="You're scheduled for cleaning this week",
    positive=lazy_gettext("You're scheduled for cleaning this week"),
    negative_en="You're not scheduled for cleaning this week",
    negative=lazy_gettext("You're not scheduled for cleaning this week"),
    sch_day=1,
    sch_day_update=6,
    switch_interval=1
)
# endregion
