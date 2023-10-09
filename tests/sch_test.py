"""Schedules blueprint tests."""

from datetime import date, timedelta

import pytest
from freezegun import freeze_time
from pytest import LogCaptureFixture
from sqlalchemy import select

from blueprints.sch.sch import GroupSchedule
from database import Schedule, dbSession
from tests import (admin_logged_in, client, create_test_categories,
                   create_test_db, create_test_products, create_test_suppliers,
                   create_test_users, user_logged_in)

pytestmark = pytest.mark.sch


@pytest.mark.parametrize(("num_groups", "first_group", "sch_day", "sch_day_update", "groups_switch", "start_date"), (
    (2, 1, 6, 1, timedelta(weeks=2), date.today()),
    (3, 2, 1, 3, timedelta(weeks=1), date.today() + timedelta(weeks=1)),
    (4, 4, 5, 4, timedelta(weeks=2), date.today()),
))
def test_group_schedule_creation(client, num_groups, first_group, sch_day, sch_day_update, groups_switch, start_date):
    GroupSchedule("test_sch", sch_day, sch_day_update, groups_switch, num_groups, first_group, start_date)
    with dbSession() as db_session:
        # check name
        schedules = db_session.scalars(
            select(Schedule)
            .filter_by(name="test_sch")).all()
        # check num_groups
        assert len(schedules) == num_groups

        elem_id = first_group
        next_date: date = start_date
        while next_date.isoweekday() != sch_day:
            next_date += timedelta(days=1)
        update_date = next_date
        while update_date.isoweekday() != sch_day_update:
            update_date += timedelta(days=1)
        for schedule in schedules:
            # check type
            assert schedule.type == "group"
            # check elem_id
            assert schedule.elem_id == elem_id
            if elem_id == num_groups:
                elem_id = 1
            else:
                elem_id += 1
            # check next_date
            assert schedule.next_date == next_date
            next_date += groups_switch
            # check update_date
            assert schedule.update_date == update_date
            update_date += groups_switch
            # check update_interval
            assert schedule.update_interval == (groups_switch * num_groups).days
        # teardown
        for schedule in schedules:
            db_session.delete(schedule)
        db_session.commit()

@freeze_time("2023-10-05")
def test_explicit_group_schedule_creation_1(client, caplog: LogCaptureFixture):
    """Explicit date checking 2 groups 2 weeks interval"""
    name = "Saturday working schedule"
    num_groups = 2
    groups_switch = timedelta(weeks=2)
    assert date.today() == date(2023, 10, 5)
    assert date.today().isoweekday() == 4
    GroupSchedule(
        name=name,
        num_groups=num_groups,
        first_group=1,
        sch_day=6,
        sch_day_update=1,
        groups_switch=groups_switch,
        start_date=date.today())
    assert f"Group schedule '{name}' created" in caplog.messages
    with dbSession() as db_session:
        schedules = db_session.scalars(
            select(Schedule)
            .filter_by(name=name)).all()
    # schedule group 1
    schedule = schedules[0]
    assert schedule.elem_id == 1
    assert schedule.next_date == date(2023, 10, 7)
    assert schedule.update_date == date(2023, 10, 9)
    assert schedule.update_interval == 28
    # schedule group 2
    schedule = schedules[1]
    assert schedule.elem_id == 2
    assert schedule.next_date == date(2023, 10, 21)
    assert schedule.update_date == date(2023, 10, 23)
    assert schedule.update_interval == 28
    # teardown
    with dbSession() as db_session:
        for schedule in schedules:
            db_session.delete(schedule)
        db_session.commit()


@freeze_time("2023-10-05")
def test_explicit_group_schedule_creation_2(client, caplog: LogCaptureFixture):
    """Explicit date checking 2 groups 1 week interval"""
    name = "Sunday movie"
    num_groups = 2
    groups_switch = timedelta(weeks=1)
    assert date.today() == date(2023, 10, 5)
    assert date.today().isoweekday() == 4
    GroupSchedule(
        name=name,
        num_groups=num_groups,
        first_group=2,
        sch_day=7,
        sch_day_update=1,
        groups_switch=groups_switch,
        start_date=date(2023, 10, 14))
    assert f"Group schedule '{name}' created" in caplog.messages
    with dbSession() as db_session:
        schedules = db_session.scalars(
            select(Schedule)
            .filter_by(name=name)).all()
    # schedule group 2
    schedule = schedules[0]
    assert schedule.elem_id == 2
    assert schedule.next_date == date(2023, 10, 15)
    assert schedule.update_date == date(2023, 10, 16)
    assert schedule.update_interval == 14
    # schedule group 1
    schedule = schedules[1]
    assert schedule.elem_id == 1
    assert schedule.next_date == date(2023, 10, 22)
    assert schedule.update_date == date(2023, 10, 23)
    assert schedule.update_interval == 14
    # teardown
    with dbSession() as db_session:
        for schedule in schedules:
            db_session.delete(schedule)
        db_session.commit()


@freeze_time("2023-10-05")
def test_explicit_group_schedule_creation_3(client, caplog: LogCaptureFixture):
    """Explicit date checking 3 groups 3 weeks interval"""
    name = "Some schedule"
    num_groups = 3
    groups_switch = timedelta(weeks=3)
    assert date.today() == date(2023, 10, 5)
    assert date.today().isoweekday() == 4
    GroupSchedule(
        name=name,
        num_groups=num_groups,
        first_group=2,
        sch_day=4,
        sch_day_update=6,
        groups_switch=groups_switch,
        start_date=date.today())
    assert f"Group schedule '{name}' created" in caplog.messages
    with dbSession() as db_session:
        schedules = db_session.scalars(
            select(Schedule)
            .filter_by(name=name)).all()
    # schedule group 2
    schedule = schedules[0]
    assert schedule.elem_id == 2
    assert schedule.next_date == date(2023, 10, 5)
    assert schedule.update_date == date(2023, 10, 7)
    assert schedule.update_interval == 63
    # schedule group 3
    schedule = schedules[1]
    assert schedule.elem_id == 3
    assert schedule.next_date == date(2023, 10, 26)
    assert schedule.update_date == date(2023, 10, 28)
    assert schedule.update_interval == 63
    # schedule group 1
    schedule = schedules[2]
    assert schedule.elem_id == 1
    assert schedule.next_date == date(2023, 11, 16)
    assert schedule.update_date == date(2023, 11, 18)
    assert schedule.update_interval == 63
    # teardown
    with dbSession() as db_session:
        for schedule in schedules:
            db_session.delete(schedule)
        db_session.commit()


def test_failed_group_schedule_creation_duplicate(client, caplog: LogCaptureFixture):
    name = "Some schedule"
    GroupSchedule(
        name=name,
        sch_day=6,
        sch_day_update=1,
        groups_switch=timedelta(weeks=1))
    assert f"Group schedule '{name}' created" in caplog.messages
    with pytest.raises(AssertionError, match="Schedule '(.)*' allready exists"):
        GroupSchedule(
            name=name,
            sch_day=6,
            sch_day_update=1,
            groups_switch=timedelta(weeks=1))
    # teardown
    with dbSession() as db_session:
        schedules = db_session.scalars(
            select(Schedule)
            .filter_by(name=name)).all()
        for schedule in schedules:
            db_session.delete(schedule)
        db_session.commit()

@pytest.mark.parametrize(("num_groups", "first_group", "sch_day", "sch_day_update", "groups_switch", "start_date", "err_msg"), (
    (1, 1, 6, 1, timedelta(weeks=2), date.today(), "You must have at least two groups"),
    (-2, 1, 6, 1, timedelta(weeks=2), date.today(), "You must have at least two groups"),
    (2, 0, 6, 1, timedelta(weeks=2), date.today(), "First group attribute is not valid"),
    (2, 3, 6, 1, timedelta(weeks=2), date.today(), "First group attribute is not valid"),
    (2, -2, 6, 1, timedelta(weeks=2), date.today(), "First group attribute is not valid"),
    (2, 1, 0, 1, timedelta(weeks=2), date.today(), "Schedule day attribute is not valid"),
    (2, 1, -2, 1, timedelta(weeks=2), date.today(), "Schedule day attribute is not valid"),
    (2, 1, 9, 1, timedelta(weeks=2), date.today(), "Schedule day attribute is not valid"),
    (2, 1, 6, 0, timedelta(weeks=2), date.today(), "Schedule day change attribute is not valid"),
    (2, 1, 6, -2, timedelta(weeks=2), date.today(), "Schedule day change attribute is not valid"),
    (2, 1, 6, 9, timedelta(weeks=2), date.today(), "Schedule day change attribute is not valid"),
    (2, 1, 6, 6, timedelta(weeks=2), date.today(), "Schedule day change attribute is not valid"),
    (2, 1, 6, 1, timedelta(hours=23), date.today(), "Schedule groups switch attribute is not valid"),
    (2, 1, 6, 1, timedelta(weeks=2), date.today() - timedelta(days=1), "Schedule start date cannot be in the past"),
))
def test_failed_group_schedule_creation(client, num_groups, first_group, sch_day, sch_day_update, groups_switch, start_date, err_msg, caplog: LogCaptureFixture):
    with pytest.raises(ValueError, match=err_msg):
        GroupSchedule("test_sch", sch_day, sch_day_update, groups_switch, num_groups, first_group, start_date)
    assert "Group schedule 'test_sch' created" not in caplog.messages


def test_failed_group_schedule_creation_db_fallback(client, caplog: LogCaptureFixture):
    GroupSchedule("", 1, 2, timedelta(weeks=2))
    assert "The schedule must have a name" in caplog.messages
