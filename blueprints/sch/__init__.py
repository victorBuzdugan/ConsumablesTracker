"""Schedules init and constants.

No imputs from other user modules.
This is accesed by database.py, tests and other modules.
`name` is used for translation
`db_name` is used for database access and should be in english
`positive` interface message if next scheduled day is this week
`negative` interface message if next scheduled day is not this week
`*_for_test` variants are the same strings without lazy_gettext;
    used in tests for checking interface text
All schedule names should come from here.
"""

from flask_babel import lazy_gettext

# region: schedule names and details
SAT_GROUP_SCH: dict[str,str] = {
    "name": lazy_gettext("Saturday movie"),
    "name_for_test": "Saturday movie",
    "db_name": "Saturday movie",
    "positive": lazy_gettext("You're choosing the movie this saturday"),
    "positive_for_test": "You're choosing the movie this saturday",
    "negative": lazy_gettext("You're not choosing the movie this saturday"),
    "negative_for_test": "You're not choosing the movie this saturday"}
# endregion
