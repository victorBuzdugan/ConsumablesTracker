"""Schedules init and constants.

No imputs from other user modules.
This is accesed by database.py and tests.
`name` is used for translation.
All schedule names should come from here.
"""

from flask_babel import lazy_gettext

# region: schedule names
SAT_GROUP_SCH_NAME: dict[str,str] = {
    "name": lazy_gettext("Saturday movie"),
    "db_name": "Saturday movie"}
# endregion
