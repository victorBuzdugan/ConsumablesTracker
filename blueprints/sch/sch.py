"""Schedules blueprint."""

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Callable

from flask import Blueprint, render_template, session, url_for
from sqlalchemy import func, select

from blueprints.sch import clean_sch_info, sat_sch_info
from database import Schedule, User, dbSession
from helpers import logger, login_required

func: Callable

sch_bp = Blueprint(
    "sch",
    __name__,
    url_prefix="/schedule",
    template_folder="templates")


def update_schedules() -> None:
    """Check update_date in schedules and update if necessary."""
    with dbSession() as db_session:
        all_schedules = db_session.scalars(
            select(Schedule)
            .filter(Schedule.update_date <= date.today())
        ).all()
        if not all_schedules:
            logger.info("No need to update schedules")
            return
        for schedule in all_schedules:
            # count all the schedules with this name and type
            sch_count = db_session.scalar(
                select(func.count(Schedule.id))
                .filter_by(type=schedule.type, name=schedule.name))
            sch_increment = timedelta(
                days=schedule.update_interval * sch_count)
            # increment dates until update date is in the future
            next_date = schedule.next_date
            update_date = schedule.update_date
            while update_date <= date.today():
                next_date += sch_increment
                update_date += sch_increment
            schedule.next_date = next_date
            schedule.update_date = update_date
            if schedule.type == "group":
                logger.debug("Schedule '%s' group '%d' will be updated",
                            schedule.name, schedule.elem_id)
            else:
                logger.debug("Schedule '%s' user '%s' will be updated",
                            schedule.name,
                            db_session.get(User, schedule.elem_id).name)
        db_session.commit()
        if len(all_schedules) == 1:
            logger.info("1 schedule updated")
        else:
            logger.info("%d schedules updated", len(all_schedules))


@sch_bp.before_request
@login_required
def user_logged_in():
    """Require user logged in for all routes."""


@dataclass
class BaseSchedule():
    """Base for group and individual schedule.
    
    :param name: schedule name
    :param sch_day: weekday for the schedule (1-monday : 7-sunday)
    :param sch_day_update: weekday when schedule updates (1-monday : 7-sunday)
    :param switch_interval: switch time interval
    :param start_date: the date when the schedule starts
    """

    name: str
    sch_day: int
    sch_day_update: int
    switch_interval: timedelta
    start_date: date

    def __post_init__(self):
        """Validate class data."""
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("The schedule must have a valid name")
        if (not isinstance(self.sch_day, int) or
                self.sch_day not in range(1, 8)):
            raise ValueError("Schedule day attribute is not valid")
        if (not isinstance(self.sch_day_update, int)
                or self.sch_day_update not in range(1, 8)):
            raise ValueError("Schedule day change attribute is not valid")
        if (not isinstance(self.switch_interval, timedelta) or
                self.switch_interval < timedelta(days=7)):
            raise ValueError("Schedule switch interval is not valid")
        if (not isinstance(self.start_date, date) or
                self.start_date < date.today()):
            raise ValueError("Schedule start date is not valid")

    def _is_registered(self) -> bool:
        """Check if the schedule is registered."""
        with dbSession() as db_session:
            if db_session.scalar(select(Schedule).filter_by(name=self.name)):
                return True
        return False

    def _determine_first_date(self) -> date:
        """Figure out schedule's first start date
        based on `start_date` and `sch_day`."""
        first_date = self.start_date
        while first_date.isoweekday() != self.sch_day:
            first_date += timedelta(days=1)
        return first_date

    def _determine_update_date(self, ref_date: date) -> date:
        """Return schedule specific update date based on a reference date."""
        # make sure update date is not the same day as next date
        update_date = ref_date + timedelta(days=1)
        while update_date.isoweekday() != self.sch_day_update:
            update_date += timedelta(days=1)
        return update_date

    def _registered_first_date(self) -> date:
        """Get schedule's registered first next date"""
        with dbSession() as db_session:
            return db_session.scalar(
                select(Schedule.next_date)
                .filter_by(name=self.name)
                .order_by(Schedule.next_date))

    def _registered_last_date(self) -> date:
        """Get schedule's registered last next date"""
        with dbSession() as db_session:
            return db_session.scalar(
                select(Schedule.next_date)
                .filter_by(name=self.name)
                .order_by(Schedule.next_date.desc()))

    def _registered_first_update_date(self) -> date:
        """Get schedule's registered first update date"""
        with dbSession() as db_session:
            return db_session.scalar(
                select(Schedule.update_date)
                .filter_by(name=self.name)
                .order_by(Schedule.update_date))

    def _registered_last_update_date(self) -> date:
        """Get schedule's registered last update date"""
        with dbSession() as db_session:
            return db_session.scalar(
                select(Schedule.update_date)
                .filter_by(name=self.name)
                .order_by(Schedule.update_date.desc()))

    def register(self) -> None:
        """Register the schedule in the database."""
        raise NotImplementedError

    def unregister(self) -> None:
        """Unregister/delete the schedule from the database."""
        with dbSession() as db_session:
            db_schedules = db_session.scalars(
                select(Schedule)
                .filter_by(name=self.name)).all()
            if db_schedules:
                for db_schedule in db_schedules:
                    db_session.delete(db_schedule)
                db_session.commit()
                logger.info("Schedule '%s' deleted", self.name)
            else:
                logger.warning("Cannot unregister schedule '%s' " +
                               "as it was not found in the database",
                               self.name)

    def data(self) -> None:
        """Get schedule data for displaying on the schedules page."""
        raise NotImplementedError


@dataclass
class GroupSchedule(BaseSchedule):
    """Schedule for groups of users.

    :param user_attr: user class attribute corresponding to this group schedule
    :param num_groups: number of groups (defaults to 2 groups)
    :param first_group: first group to be scheduled (defaults to group 1)
    """

    user_attr: str
    num_groups: int = 2
    first_group: int = 1

    def __post_init__(self):
        """Validate class data."""
        super().__post_init__()
        if (not isinstance(self.user_attr, str) or
                not hasattr(User, self.user_attr)):
            raise AttributeError(f"Invalid user attribute '{self.user_attr}'")
        if not isinstance(self.num_groups, int) or self.num_groups < 2:
            raise ValueError("You must have at least two groups")
        if (not isinstance(self.first_group, int) or
                self.first_group not in range(1, self.num_groups + 1)):
            raise ValueError("First group attribute is not valid")

    def _group_order(self) -> list[int]:
        """Order groups based on first group."""
        group_order = list(range(1, self.num_groups + 1))
        if self.first_group != 1:
            while group_order[0] != self.first_group:
                group_order.append(group_order.pop(0))
        return group_order

    def register(self) -> None:
        """Register the schedule in the database."""
        if self._is_registered():
            logger.warning("Schedule '%s' (register): already exists",
                        self.name)
            return
        schedule_records = []
        next_date = self._determine_first_date()
        update_date = self._determine_update_date(next_date)
        for group_no in self._group_order():
            schedule_records.append(
                Schedule(
                    name=self.name,
                    type="group",
                    elem_id=group_no,
                    next_date=next_date,
                    update_date=update_date,
                    update_interval=self.switch_interval.days))
            next_date += self.switch_interval
            update_date += self.switch_interval
        if schedule_records:
            with dbSession() as db_session:
                db_session.add_all(schedule_records)
                db_session.commit()
                logger.info("Schedule '%s' created", self.name)

    def data(self) -> list[list[str]]:
        """Get group schedule data: groups, usernames and dates.

        Returns a list of groups; each group item contain a list of names,
        a list of dates and a flag if the schedule date is this week.
        [
            [#group1
                0: [group1_name1, group1_name2, ...]
                1: [group1_date1, group1_date2, group1_date3]
                2: True | False
            ]
            [#group2
                0: [group2_name1, group2_name2, ...]
                1: [group1_date2, group2_date2, group2_date3]
                2: True | False
            ]
            ...
        ]
        """
        if not self._is_registered():
            self.register()
        data = []
        for group in range(1, self.num_groups + 1):
            group_data = []
            with dbSession() as db_session:
                # index [0] - names
                group_names = db_session.scalars(
                    select(User.name)
                    .filter_by(in_use=True, reg_req=False)
                    .filter(getattr(User, self.user_attr)==group)
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
                        elem_id = group)) * self.num_groups
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


@dataclass
class IndivSchedule(BaseSchedule):
    """Individual schedule for users."""

    def current_order(self) -> list[int]:
        """Schedule user id's current order."""
        with dbSession() as db_session:
            return db_session.scalars(
                select(Schedule.elem_id)
                .filter_by(name=self.name)
                .order_by(Schedule.next_date)).all()

    def _valid_user_id(self, user_id: int) -> bool:
        """Validate user id argument."""
        with dbSession() as db_session:
            if not db_session.scalar(
                    select(User.id)
                    .filter_by(in_use=True,
                                reg_req=False,
                                id=user_id)):
                return False
        return True

    def _valid_pos(self, pos: int) -> bool:
        """Validate a new position in the list of id's"""
        if 0 <= pos < len(self.current_order()):
            return True
        return False

    def _reg_mod(self,
                 user_ids_order: list[int] = None,
                 start_date: date = None,
                 operation: str = "modify"
                 ) -> bool:
        """Register or modify the schedule in the database.
        
        :param user_ids_order: optional order in which to create or modify the
            schedule (list of user id's)
        :param start_date: optional first next_date; can be in the past but
            has to be this week
        :param operation: register or modify
        """
        if self._is_registered():
            logger.warning("Schedule '%s' (%s): already exists",
                           self.name, operation)
            return False

        # if provided validate user_ids_order
        with dbSession() as db_session:
            db_user_ids = db_session.scalars(
                select(User.id)
                .filter_by(in_use=True, reg_req=False)).all()
        if user_ids_order:
            if not sorted(user_ids_order) == sorted(db_user_ids):
                logger.error("Schedule '%s' (%s): list of id's " +
                             "provided is invalid",
                             self.name, operation)
                return False
        else:
            user_ids_order = db_user_ids

        if start_date:
            # validate start date is on the correct day
            if start_date.isoweekday() != self.sch_day:
                logger.error("Schedule '%s' (%s): start date '%s' " +
                             "provided is invalid",
                             self.name, operation, start_date.isoformat())
                return False
            next_date = start_date
        else:
            next_date = self._determine_first_date()

        # register schedule
        update_date = self._determine_update_date(next_date)
        schedule_records = []
        for user_id in user_ids_order:
            schedule_records.append(
                Schedule(
                    name=self.name,
                    type="individual",
                    elem_id=user_id,
                    next_date=next_date,
                    update_date=update_date,
                    update_interval=self.switch_interval.days))
            next_date += self.switch_interval
            update_date += self.switch_interval
        with dbSession() as db_session:
            db_session.add_all(schedule_records)
            db_session.commit()
            return True

    def _modify(self,
                 user_ids_order: list[int] = None,
                 start_date: date = None
                 ) -> None:
        """Modify the schedule in the database.

        :param user_ids_order: modification user order (list of user id's)
        :param start_date: first next_date;
            can be in the past but has to be this week
        """
        if self._reg_mod(user_ids_order, start_date, "modify"):
            logger.info("Schedule '%s' modified",
                        self.name)

    def register(self,
                 user_ids_order: list[int] = None,
                 start_date: date = None
                 ) -> None:
        """Register the schedule in the database.
        
        :param user_ids_order: optional order in which to create the schedule
            (list of user id's)
        :param start_date: optional first next_date; can be in the past but
            has to be this week
        """
        if self._reg_mod(user_ids_order, start_date, "register"):
            logger.info("Schedule '%s' registered",
                        self.name)

    def data(self):
        """Get individual schedule data: usernames and dates.
        
        Returns a list of names, dates and a flag if the schedule date
        is this week.
        [
            [user1_name, user1_date]
            [user2_name, user2_date]
            ...
        ]
        """
        data = []
        if not self._is_registered():
            logger.warning("Schedule '%s' (data): is not registered",
                           self.name)
            return data
        with dbSession() as db_session:
            schedule_records = db_session.execute(
                select(Schedule.elem_id, Schedule.next_date)
                .filter_by(name=self.name)
                .order_by(Schedule.next_date)).unique().all()
        for record in schedule_records:
            record_data=[]
            # index [0] - name
            with dbSession() as db_session:
                record_data.append(db_session.get(User, record.elem_id).name)
            # index [1] - date
            record_data.append(record.next_date.strftime("%d.%m.%Y"))
            data.append(record_data)
        return data

    def add_user(self, user_id: int) -> None:
        """Add a new user to the schedule.
        
        :param user_id: id of the user that will be added"""
        # prechecks
        if not self._is_registered():
            logger.warning("Schedule '%s' (add_user): is not registered",
                           self.name)
            return
        if self._registered_first_update_date() <= date.today():
            update_schedules()
        if not isinstance(user_id, int) or not self._valid_user_id(user_id):
            logger.warning("Schedule '%s' (add_user): invalid user_id '%s'",
                           self.name, user_id)
            return
        if user_id in self.current_order():
            logger.warning("Schedule '%s' (add_user): user with id '%d' " +
                           "is already scheduled",
                           self.name, user_id)
            return

        next_date = self._registered_last_date() + self.switch_interval
        update_date = self._registered_last_update_date() + self.switch_interval
        with dbSession() as db_session:
            db_session.add(
                Schedule(
                    name=self.name,
                    type="individual",
                    elem_id=user_id,
                    next_date=next_date,
                    update_date=update_date,
                    update_interval=self.switch_interval.days))
            db_session.commit()
            logger.debug("Schedule '%s' added '%s'",
                         self.name,
                         db_session.get(User, user_id).name)

    def remove_user(self, user_id: int) -> None:
        """Remove a user from the schedule.
        
        :param user_id: id of the user that will be removed"""
        # prechecks
        if not self._is_registered():
            logger.warning("Schedule '%s' (remove_user): is not registered",
                           self.name)
            return
        if self._registered_first_update_date() <= date.today():
            update_schedules()
        if not isinstance(user_id, int):
            logger.warning("Schedule '%s' (remove_user): invalid user_id '%s'",
                           self.name, user_id)
            return
        users_order = self.current_order()
        if user_id not in users_order:
            logger.warning("Schedule '%s' (remove_user): " +
                        "user with id '%d' is not in the schedule",
                        self.name, user_id)
            return

        # remove the user
        users_order.pop(users_order.index(user_id))
        # register the new order
        first_date = self._registered_first_date()
        self.unregister()
        self._modify(
            user_ids_order=users_order,
            start_date=first_date)
        logger.debug("Schedule '%s' removed user with id '%d'",
                    self.name, user_id)

    def change_user_pos(self, user_id: int, new_pos: int) -> None:
        """Change a user position in the schedule.
        
        :param user_id: id of the user that will change position
        :param new_pos: the new user's position (0 indexed)
        """
        # prechecks
        if not self._is_registered():
            logger.warning("Schedule '%s' (change_user_pos): is not registered",
                           self.name)
            return
        if self._registered_first_update_date() <= date.today():
            update_schedules()
        if not isinstance(user_id, int) or not self._valid_user_id(user_id):
            logger.warning("Schedule '%s' (change_user_pos): " +
                           "invalid user_id '%s'", self.name, user_id)
            return
        if not isinstance(new_pos, int) or not self._valid_pos(new_pos):
            logger.warning("Schedule '%s' (change_user_pos): " +
                           "invalid new position '%s'", self.name, new_pos)
            return
        users_order = self.current_order()
        if user_id not in users_order:
            logger.warning("Schedule '%s' (change_user_pos): " +
                           "user with id '%d' is not in the schedule",
                           self.name, user_id)
            return
        if users_order[new_pos] == user_id:
            logger.warning("Schedule '%s' (change_user_pos): " +
                           "user with id '%d' is already at position %d",
                           self.name, user_id, new_pos)
            return

        # reorder the list of user id's
        users_order.pop(users_order.index(user_id))
        users_order.insert(new_pos, user_id)
        # register the new order
        first_date = self._registered_first_date()
        self.unregister()
        self._modify(
            user_ids_order=users_order,
            start_date=first_date)
        logger.debug("Schedule '%s' changed user with id '%d' position to '%d'",
                    self.name, user_id, new_pos)


# region: group schedules init
saturday_sch = GroupSchedule(
    name=sat_sch_info.en_name,
    user_attr=User.sat_group.name,
    num_groups=2,
    first_group=1,
    sch_day=sat_sch_info.sch_day,
    sch_day_update=sat_sch_info.sch_day_update,
    switch_interval=timedelta(weeks=sat_sch_info.switch_interval),
    start_date=date.today())
# saturday_sch.register()
# endregion

# region: individual schedules init
cleaning_sch = IndivSchedule(
    name=clean_sch_info.en_name,
    sch_day=clean_sch_info.sch_day,
    sch_day_update=clean_sch_info.sch_day_update,
    switch_interval=timedelta(weeks=clean_sch_info.switch_interval),
    start_date=date.today())
# cleaning_sch.register()
# endregion


@sch_bp.route("")
def schedules():
    """Schedules page."""
    logger.info("Schedules page")
    session["last_url"] = url_for(".schedules")

    # schedule view registration
    group_schedules = []
    group_schedules.append(
        [sat_sch_info.name, saturday_sch.data()])

    indiv_schedules = []
    indiv_schedules.append(
        [clean_sch_info.name, cleaning_sch.data()])

    return render_template("sch/schedules.html",
                           group_schedules=group_schedules,
                           indiv_schedules=indiv_schedules)
