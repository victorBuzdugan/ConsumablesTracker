"""Schedules blueprint."""

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Callable

from flask import Blueprint, render_template
from sqlalchemy import func, select

from blueprints.sch import SAT_GROUP_SCH
from database import Schedule, User, dbSession
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
    :param user_attr: user class attribute corresponding to this group schedule
    :param sch_day: weekday for the schedule (1-monday : 7-sunday)
    :param sch_day_update: weekday when schedule updates (1-monday : 7-sunday)
    :param groups_switch: groups switch time interval
    :param num_groups: number of groups (defaults to 2 groups)
    :param first_group: first group to be scheduled (defaults to group 1)
    :param start_date: the date when the schedule starts (defaults to today)
    """
    name: str
    user_attr: str
    num_groups: int = 2
    first_group: int = 1
    sch_day: int = 6
    sch_day_update: int = 1
    groups_switch: timedelta = timedelta(weeks=1)
    start_date: date = date.today()

    def __post_init__(self):
        """Validate class data."""
        if not self.name.strip():
            raise ValueError("The schedule must have a name")
        if not hasattr(User, self.user_attr):
            raise AttributeError(f"User has no attribute '{self.user_attr}'")
        if self.num_groups < 2:
            raise ValueError("You must have at least two groups")
        if self.first_group not in range(1, self.num_groups + 1):
            raise ValueError("First group attribute is not valid")
        if self.sch_day not in range(1, 8):
            raise ValueError("Schedule day attribute is not valid")
        if (self.sch_day_update not in range(1, 8)
                or self.sch_day_update == self.sch_day):
            raise ValueError("Schedule day change attribute is not valid")
        if self.groups_switch < timedelta(days=1):
            raise ValueError("Schedule groups switch attribute is not valid")
        if self.start_date < date.today():
            raise ValueError("Schedule start date cannot be in the past")

    def _is_registered(self) -> bool:
        """Check if the schedule is registered."""
        with dbSession() as db_session:
            if db_session.scalar(select(Schedule).filter_by(name=self.name)):
                return True
        return False

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

    def register(self) -> None:
        """Register the schedule in the database."""
        if self._is_registered():
            logger.info("Schedule '%s' allready exists", self.name)
            return
        schedule_records = []
        next_date = self._first_date()
        update_date = self._first_update_date(next_date)
        for group_no in self._group_order():
            schedule_records.append(
                Schedule(
                    name=self.name,
                    type="group",
                    elem_id=group_no,
                    next_date=next_date,
                    update_date=update_date,
                    update_interval=(self.groups_switch * self.num_groups)
                                        .days))
            next_date += self.groups_switch
            update_date += self.groups_switch
        if schedule_records:
            with dbSession() as db_session:
                db_session.add_all(schedule_records)
                db_session.commit()
                logger.info("Group schedule '%s' created", self.name)

    def unregister(self) -> None:
        """Unregister/delete the schedule from the database."""
        with dbSession() as db_session:
            schedules = db_session.scalars(
                select(Schedule)
                .filter_by(name=self.name)).all()
            for sch in schedules:
                db_session.delete(sch)
            db_session.commit()
            logger.info("Group schedule '%s' deleted", self.name)

    def data(self) -> list[list[str]]:
        """Get group schedule data: groups, usernames and dates.
        
        Returns a list of groups; each group item contain a list of names,
        a list of dates and a flag if theschedule date is this week.
        """
        # pylint: disable=singleton-comparison
        if not self._is_registered():
            self.register()
        data = []
        for group in range(1, self.num_groups + 1):
            group_data = []
            with dbSession() as db_session:
                # index [0] - names
                group_names = db_session.scalars(
                    select(User.name)
                    .filter(
                        getattr(User, self.user_attr)==group,
                        User.in_use==True,
                        User.reg_req==False)
                    .order_by(func.lower(User.name))).all()
                group_data.append(group_names)
                # index [1] - dates
                group_dates = []
                group_next_date = db_session.scalar(
                    select(Schedule.next_date)
                    .filter_by(
                        name = self.name,
                        elem_id = group))
                group_interval = db_session.scalar(
                    select(Schedule.update_interval)
                    .filter_by(
                        name = self.name,
                        elem_id = group))
                next_date = group_next_date
                for _ in range(3):
                    group_dates.append(next_date.strftime("%d.%m.%Y"))
                    next_date += timedelta(days=group_interval)
                group_data.append(group_dates)
                # index [2] - flag if groups next date is this week
                if (group_next_date.isocalendar()[1] ==
                        date.today().isocalendar()[1]):
                    group_data.append(True)
                else:
                    group_data.append(False)
            data.append(group_data)
        return data


# region: group schedules init
sat_group_schedule = GroupSchedule(
    name=SAT_GROUP_SCH["db_name"],
    user_attr=User.sat_group.name,
    num_groups=2,
    first_group=1,
    sch_day=6,
    sch_day_update=1,
    groups_switch=timedelta(weeks=1),
    start_date=date.today())
# sat_group_schedule.register()
# endregion


@sch_bp.route("")
def schedules():
    """Schedules page."""
    logger.info("Schedules page")

    # schedule view registration
    group_schedules = []
    group_schedules.append(
        [SAT_GROUP_SCH["name"], sat_group_schedule.data()])

    return render_template("sch/schedules.html",
                           group_schedules=group_schedules)
