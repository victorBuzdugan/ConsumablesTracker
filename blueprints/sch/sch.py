"""Schedules blueprint."""

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Callable
# from sqlite3 import IntegrityError

from flask import Blueprint
from sqlalchemy import select

from database import Schedule, dbSession
from helpers import login_required, logger

func: Callable

sch_bp = Blueprint(
    "sch",
    __name__,
    url_prefix="/schedule",
    template_folder="templates")


@sch_bp.before_request
@login_required
def user_logged_in():
    """Require user logged in for all routes."""


@dataclass
class GroupSchedule():
    """Schedule for groups of users.

    :param name: schedule name
    :param sch_day: weekday for the schedule (1-monday : 7-sunday)
    :param sch_day_update: weekday when schedule updates (1-monday : 7-sunday)
    :param groups_switch: groups switch time interval
    :param num_groups: number of groups (defaults to 2 groups)
    :param first_group: first group to be scheduled (defaults to group 1)
    :param start_date: the date when the schedule starts (defaults to today)
    """
    name: str
    sch_day: int
    sch_day_update: int
    groups_switch: timedelta
    num_groups: int = 2
    first_group: int = 1
    start_date: date = date.today()

    def __post_init__(self):
        """Validate class data."""
        with dbSession() as db_session:
            if db_session.scalar(select(Schedule).filter_by(name=self.name)):
                raise AssertionError(f"Schedule '{self.name}' allready exists")
        if self.sch_day not in range(1, 8):
            raise ValueError("Schedule day attribute is not valid")
        if (self.sch_day_update not in range(1, 8)
                or self.sch_day_update == self.sch_day):
            raise ValueError("Schedule day change attribute is not valid")
        if self.groups_switch < timedelta(days=1):
            raise ValueError("Schedule groups switch attribute is not valid")
        if self.num_groups < 2:
            raise ValueError("You must have at least two groups")
        if self.first_group not in range(1, self.num_groups + 1):
            raise ValueError("First group attribute is not valid")
        if self.start_date < date.today():
            raise ValueError("Schedule start date cannot be in the past")
        self._register_schedule()

    def _group_order(self) -> list[int]:
        """Order groups based on first group."""
        group_order = list(range(1, self.num_groups + 1))
        if self.first_group != 1:
            while group_order[0] != self.first_group:
                group_order.append(group_order.pop(0))
        return group_order

    def _first_date(self) -> date:
        """Return first group start date."""
        first_date = self.start_date
        while first_date.isoweekday() != self.sch_day:
            first_date += timedelta(days=1)
        return first_date

    def _first_update_date(self, ref_date: date) -> date:
        """Return first group update date."""
        update_date = ref_date
        while update_date.isoweekday() != self.sch_day_update:
            update_date += timedelta(days=1)
        return update_date

    def _register_schedule(self):
        """Register the schedule in the database."""
        schedule_records = []
        next_date = self._first_date()
        update_date = self._first_update_date(next_date)
        for group_no in self._group_order():
            try:
                schedule_records.append(
                    Schedule(
                        name=self.name,
                        type="group",
                        elem_id=group_no,
                        next_date=next_date,
                        update_date=update_date,
                        update_interval=(self.groups_switch
                                         * self.num_groups)
                                         .days))
            except ValueError as sch_err:
                logger.warning(str(sch_err))
            next_date += self.groups_switch
            update_date += self.groups_switch
        if schedule_records:
            with dbSession() as db_session:
                db_session.add_all(schedule_records)
                db_session.commit()
                logger.info("Group schedule '%s' created", self.name)


# sample group schedule creation
# try:
#     GroupSchedule(
#         name="Saturday movie",
#         num_groups=2,
#         first_group=1,
#         sch_day=6,
#         sch_day_update=1,
#         groups_switch=timedelta(weeks=1),
#         start_date=date.today())
# except AssertionError as err:
#     logger.info(str(err))
# except ValueError as err:
#     logger.warning(str(err))
# except IntegrityError as err:
#     logger.critical(str(err))
