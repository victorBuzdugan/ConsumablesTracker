"""Schedules blueprint tests."""

from datetime import date, timedelta

import pytest
from flask import session, url_for
from flask.testing import FlaskClient
from freezegun import freeze_time
from pytest import LogCaptureFixture
from sqlalchemy import select

from blueprints.sch import CLEANING_SCH, SAT_GROUP_SCH
from blueprints.sch.sch import (BaseSchedule, GroupSchedule, IndivSchedule,
                                cleaning_schedule)
from database import Schedule, User, dbSession

pytestmark = pytest.mark.sch


# region: base schedule
def test_base_schedule():
    """Test base schedule not implemented"""
    test_sch = BaseSchedule(
        name="test_sch",
        sch_day=1,
        sch_day_update=1,
        switch_interval=timedelta(weeks=1),
        start_date=date.today())
    with pytest.raises(NotImplementedError):
        test_sch.register()
    with pytest.raises(NotImplementedError):
        test_sch.data()
# endregion


# region: group schedule
@pytest.mark.parametrize(
    ("num_groups", "first_group", "sch_day", "sch_day_update",
     "switch_interval", "start_date"), (
        (2, 1, 6, 1,
         timedelta(weeks=2), date.today()),
        (3, 2, 1, 3,
         timedelta(weeks=1), date.today() + timedelta(weeks=1)),
        (4, 4, 5, 4,
         timedelta(weeks=2), date.today()),
))
def test_group_schedule_creation(
        num_groups, first_group, sch_day, sch_day_update,
        switch_interval, start_date):
    """test_group_schedule_creation"""
    sch_name = "test_sch"
    GroupSchedule(
        name=sch_name,
        user_attr=User.sat_group.name,
        num_groups=num_groups,
        first_group=first_group,
        sch_day=sch_day,
        sch_day_update=sch_day_update,
        switch_interval=switch_interval,
        start_date=start_date).register()
    with dbSession() as db_session:
        # check name
        schedules = db_session.scalars(
            select(Schedule)
            .filter_by(name=sch_name)).all()
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
            next_date += switch_interval
            # check update_date
            assert schedule.update_date == update_date
            update_date += switch_interval
            # check update_interval
            assert schedule.update_interval == switch_interval.days
        # teardown
        for schedule in schedules:
            db_session.delete(schedule)
        db_session.commit()


@freeze_time("2023-10-05")
def test_explicit_group_schedule_creation_1(caplog: LogCaptureFixture):
    """Explicit date checking 2 groups 2 weeks interval"""
    name = "Test saturday working"
    num_groups = 2
    switch_interval = timedelta(weeks=2)
    assert date.today() == date(2023, 10, 5)
    assert date.today().isoweekday() == 4
    GroupSchedule(
        name=name,
        user_attr=User.sat_group.name,
        num_groups=num_groups,
        first_group=1,
        sch_day=6,
        sch_day_update=1,
        switch_interval=switch_interval,
        start_date=date.today()).register()
    assert f"Schedule '{name}' created" in caplog.messages
    with dbSession() as db_session:
        schedules = db_session.scalars(
            select(Schedule)
            .filter_by(name=name)).all()
    # schedule group 1
    schedule = schedules[0]
    assert schedule.elem_id == 1
    assert schedule.next_date == date(2023, 10, 7)
    assert schedule.update_date == date(2023, 10, 9)
    assert schedule.update_interval == 14
    # schedule group 2
    schedule = schedules[1]
    assert schedule.elem_id == 2
    assert schedule.next_date == date(2023, 10, 21)
    assert schedule.update_date == date(2023, 10, 23)
    assert schedule.update_interval == 14
    # teardown
    with dbSession() as db_session:
        for schedule in schedules:
            db_session.delete(schedule)
        db_session.commit()


@freeze_time("2023-10-05")
def test_explicit_group_schedule_creation_2(caplog: LogCaptureFixture):
    """Explicit date checking 2 groups 1 week interval"""
    name = "Test sunday movie"
    num_groups = 2
    switch_interval = timedelta(weeks=1)
    assert date.today() == date(2023, 10, 5)
    assert date.today().isoweekday() == 4
    GroupSchedule(
        name=name,
        user_attr=User.sat_group.name,
        num_groups=num_groups,
        first_group=2,
        sch_day=7,
        sch_day_update=1,
        switch_interval=switch_interval,
        start_date=date(2023, 10, 14)).register()
    assert f"Schedule '{name}' created" in caplog.messages
    with dbSession() as db_session:
        schedules = db_session.scalars(
            select(Schedule)
            .filter_by(name=name)).all()
    # schedule group 2
    schedule = schedules[0]
    assert schedule.elem_id == 2
    assert schedule.next_date == date(2023, 10, 15)
    assert schedule.update_date == date(2023, 10, 16)
    assert schedule.update_interval == 7
    # schedule group 1
    schedule = schedules[1]
    assert schedule.elem_id == 1
    assert schedule.next_date == date(2023, 10, 22)
    assert schedule.update_date == date(2023, 10, 23)
    assert schedule.update_interval == 7
    # teardown
    with dbSession() as db_session:
        for schedule in schedules:
            db_session.delete(schedule)
        db_session.commit()


@freeze_time("2023-10-05")
def test_explicit_group_schedule_creation_3(caplog: LogCaptureFixture):
    """Explicit date checking 3 groups 3 weeks interval"""
    name = "Test some other schedule"
    num_groups = 3
    switch_interval = timedelta(weeks=3)
    assert date.today() == date(2023, 10, 5)
    assert date.today().isoweekday() == 4
    GroupSchedule(
        name=name,
        user_attr=User.sat_group.name,
        num_groups=num_groups,
        first_group=2,
        sch_day=4,
        sch_day_update=6,
        switch_interval=switch_interval,
        start_date=date.today()).register()
    assert f"Schedule '{name}' created" in caplog.messages
    with dbSession() as db_session:
        schedules = db_session.scalars(
            select(Schedule)
            .filter_by(name=name)).all()
    # schedule group 2
    schedule = schedules[0]
    assert schedule.elem_id == 2
    assert schedule.next_date == date(2023, 10, 5)
    assert schedule.update_date == date(2023, 10, 7)
    assert schedule.update_interval == 21
    # schedule group 3
    schedule = schedules[1]
    assert schedule.elem_id == 3
    assert schedule.next_date == date(2023, 10, 26)
    assert schedule.update_date == date(2023, 10, 28)
    assert schedule.update_interval == 21
    # schedule group 1
    schedule = schedules[2]
    assert schedule.elem_id == 1
    assert schedule.next_date == date(2023, 11, 16)
    assert schedule.update_date == date(2023, 11, 18)
    assert schedule.update_interval == 21
    # teardown
    with dbSession() as db_session:
        for schedule in schedules:
            db_session.delete(schedule)
        db_session.commit()


def test_failed_group_schedule_creation_duplicate(caplog: LogCaptureFixture):
    """test_failed_group_schedule_creation_duplicate"""
    GroupSchedule(
        name=SAT_GROUP_SCH["db_name"],
        user_attr=User.sat_group.name,
        sch_day=6,
        sch_day_update=1,
        switch_interval=timedelta(weeks=1),
        start_date=date.today()).register()
    assert f"Schedule '{SAT_GROUP_SCH['db_name']}' (register): allready exists"\
        in caplog.messages


@pytest.mark.parametrize(
    ("name", "user_attr", "num_groups", "first_group",
     "sch_day", "sch_day_update", "switch_interval", "start_date",
     "err_msg"), (
        # name
        ("", "sat_group", 2, 1,
         6, 1, timedelta(weeks=2), date.today(),
         "The schedule must have a name"),
        (" ", "sat_group", 2, 1,
         6, 1, timedelta(weeks=2), date.today(),
         "The schedule must have a name"),
        (None, "sat_group", 2, 1,
         6, 1, timedelta(weeks=2), date.today(),
         "'NoneType' object has no attribute 'strip'"),
        # user_attr
        ("test_sch", "", 2, 1,
         6, 1, timedelta(weeks=2), date.today(),
         "User has no attribute"),
        ("test_sch", " ", 2, 1,
         6, 1, timedelta(weeks=2), date.today(),
         "User has no attribute"),
        ("test_sch", "wrong_attr", 2, 1,
         6, 1, timedelta(weeks=2), date.today(),
         "User has no attribute"),
        # num_groups
        ("test_sch", "sat_group", 1, 1,
         6, 1, timedelta(weeks=2), date.today(),
         "You must have at least two groups"),
        ("test_sch", "sat_group", -2, 1,
         6, 1, timedelta(weeks=2), date.today(),
         "You must have at least two groups"),
        # first_group
        ("test_sch", "sat_group", 2, 0,
         6, 1, timedelta(weeks=2), date.today(),
         "First group attribute is not valid"),
        ("test_sch", "sat_group", 2, 3,
         6, 1, timedelta(weeks=2), date.today(),
         "First group attribute is not valid"),
        ("test_sch", "sat_group", 2, -2,
         6, 1, timedelta(weeks=2), date.today(),
         "First group attribute is not valid"),
        # sch_day
        ("test_sch", "sat_group", 2, 1,
         0, 1, timedelta(weeks=2), date.today(),
         "Schedule day attribute is not valid"),
        ("test_sch", "sat_group", 2, 1,
         -2, 1, timedelta(weeks=2), date.today(),
         "Schedule day attribute is not valid"),
        ("test_sch", "sat_group", 2, 1,
         9, 1, timedelta(weeks=2), date.today(),
         "Schedule day attribute is not valid"),
        # sch_day_update
        ("test_sch", "sat_group", 2, 1,
         6, 0, timedelta(weeks=2), date.today(),
         "Schedule day change attribute is not valid"),
        ("test_sch", "sat_group", 2, 1,
         6, -2, timedelta(weeks=2), date.today(),
         "Schedule day change attribute is not valid"),
        ("test_sch", "sat_group", 2, 1,
         6, 9, timedelta(weeks=2), date.today(),
         "Schedule day change attribute is not valid"),
        # group switch_interval
        ("test_sch", "sat_group", 2, 1,
         6, 1, timedelta(hours=23), date.today(),
         "Schedule switch interval is not valid"),
        # start_date
        ("test_sch", "sat_group", 2, 1,
         6, 1, timedelta(weeks=2), date.today() - timedelta(days=1),
         "Schedule start date cannot be in the past"),
))
def test_failed_group_schedule_creation(
        name, user_attr, num_groups, first_group,
        sch_day, sch_day_update, switch_interval, start_date,
        err_msg, caplog: LogCaptureFixture):
    """test_failed_group_schedule_creation"""
    with pytest.raises((ValueError, AttributeError), match=err_msg):
        GroupSchedule(
            name=name,
            user_attr=user_attr,
            num_groups=num_groups,
            first_group=first_group,
            sch_day=sch_day,
            sch_day_update=sch_day_update,
            switch_interval=switch_interval,
            start_date=start_date).register()
    assert f"Schedule '{name}' created" not in caplog.messages


def test_group_schedule_unregister(caplog: LogCaptureFixture):
    """test_group_schedule_unregister"""
    sch_name = "test_sch"
    test_schedule = GroupSchedule(
        name=sch_name,
        user_attr=User.sat_group.name,
        sch_day=6,
        sch_day_update=1,
        switch_interval=timedelta(weeks=1),
        start_date=date.today())
    # test auto-registering
    test_schedule.data()
    with dbSession() as db_session:
        assert db_session.scalar(select(Schedule).filter_by(name=sch_name))
        assert f"Schedule '{sch_name}' created" in caplog.messages
        test_schedule.unregister()
        assert not db_session.scalar(select(Schedule).filter_by(name=sch_name))
        assert f"Schedule '{sch_name}' deleted" in caplog.messages
# endregion


# region: individual schedule
@pytest.mark.parametrize(
        ("sch_day", "sch_day_update", "switch_interval", "start_date"), (
            (1, 1, timedelta(weeks=1), date.today()),
            (7, 1, timedelta(weeks=2), date.today() + timedelta(weeks=1)),
            (2, 6, timedelta(weeks=3), date.today()),
))
def test_individual_schedule_creation(
        sch_day, sch_day_update, switch_interval, start_date):
    """Test individual schedule creation with different attributes."""
    sch_name = "test_sch"
    IndivSchedule(
        name=sch_name,
        sch_day=sch_day,
        sch_day_update=sch_day_update,
        switch_interval=switch_interval,
        start_date=start_date).register()
    next_date: date = start_date
    while next_date.isoweekday() != sch_day:
        next_date += timedelta(days=1)
    update_date = next_date + timedelta(days=1)
    while update_date.isoweekday() != sch_day_update:
        update_date += timedelta(days=1)
    with dbSession() as db_session:
        # check name
        schedules = db_session.scalars(
            select(Schedule)
            .filter_by(name=sch_name)).all()
        users_ids = db_session.scalars(
            select(User.id)
            .filter_by(in_use= True, reg_req=False)).all()
        assert len(schedules) == len(users_ids)
        for index, schedule in enumerate(schedules):
            # check type
            assert schedule.type == "individual"
            # check elem_id
            assert schedule.elem_id == users_ids[index]
            # check next_date
            assert schedule.next_date == next_date
            next_date += switch_interval
            # check update_date
            assert schedule.update_date == update_date
            update_date += switch_interval
            # check update_interval
            assert schedule.update_interval == switch_interval.days
        # teardown
        for schedule in schedules:
            db_session.delete(schedule)
        db_session.commit()


@freeze_time("2023-10-12")
def test_explicit_individual_schedule_creation_1(caplog: LogCaptureFixture):
    """Explicit date checking 1 week interval"""
    # pylint: disable=protected-access
    assert date.today() == date(2023, 10, 12)
    assert date.today().isoweekday() == 4
    indiv_schedule = IndivSchedule(
        name="Test cleaning schedule",
        sch_day=1,
        sch_day_update=1,
        switch_interval=timedelta(weeks=1),
        start_date=date.today())
    users_ids = [4, 2, 1, 7, 3]
    # test register in the past and order
    indiv_schedule.register(users_ids, date(2023, 10, 9))
    assert f"Schedule '{indiv_schedule.name}' registered" in caplog.text
    with dbSession() as db_session:
        schedules = db_session.scalars(
            select(Schedule)
            .filter_by(name=indiv_schedule.name)).all()
    # user 4
    schedule = schedules[0]
    assert schedule.elem_id == 4
    assert schedule.next_date == date(2023, 10, 9)
    assert schedule.update_date == date(2023, 10, 16)
    assert schedule.update_interval == 7
    # user 2
    schedule = schedules[1]
    assert schedule.elem_id == 2
    assert schedule.next_date == date(2023, 10, 16)
    assert schedule.update_date == date(2023, 10, 23)
    assert schedule.update_interval == 7
    # user 1
    schedule = schedules[2]
    assert schedule.elem_id == 1
    assert schedule.next_date == date(2023, 10, 23)
    assert schedule.update_date == date(2023, 10, 30)
    assert schedule.update_interval == 7
    # user 7
    schedule = schedules[3]
    assert schedule.elem_id == 7
    assert schedule.next_date == date(2023, 10, 30)
    assert schedule.update_date == date(2023, 11, 6)
    assert schedule.update_interval == 7
    # user 3
    schedule = schedules[4]
    assert schedule.elem_id == 3
    assert schedule.next_date == date(2023, 11, 6)
    assert schedule.update_date == date(2023, 11, 13)
    assert schedule.update_interval == 7
    # test data
    assert indiv_schedule.data() == [
        ["user4", date(2023, 10, 9).strftime("%d.%m.%Y")],
        ["user2", date(2023, 10, 16).strftime("%d.%m.%Y")],
        ["user1", date(2023, 10, 23).strftime("%d.%m.%Y")],
        ["user7", date(2023, 10, 30).strftime("%d.%m.%Y")],
        ["user3", date(2023, 11, 6).strftime("%d.%m.%Y")]
    ]
    # add user
    with dbSession() as db_session:
        db_session.get(User, 5).reg_req = False
        db_session.commit()
        indiv_schedule.add_user(5)
        schedules = db_session.scalars(
            select(Schedule)
            .filter_by(name=indiv_schedule.name)).all()
    assert f"Schedule '{indiv_schedule.name}' added 'user5'" in caplog.text
    schedule = schedules[-1]
    assert schedule.elem_id == 5
    assert schedule.next_date == date(2023, 11, 13)
    assert schedule.update_date == date(2023, 11, 20)
    assert schedule.update_interval == 7
    # remove user
    with dbSession() as db_session:
        db_session.get(User, 5).reg_req = True
        db_session.commit()
        indiv_schedule.remove_user(5)
        schedules = db_session.scalars(
            select(Schedule)
            .filter_by(name=indiv_schedule.name)).all()
        assert not db_session.scalar(
            select(Schedule)
            .filter_by(name=indiv_schedule.name, elem_id=5))
    assert (f"Schedule '{indiv_schedule.name}' " +
            "removed user with id '5'") in caplog.text
    schedule = schedules[0]
    assert schedule.elem_id == 4
    assert schedule.next_date == date(2023, 10, 9)
    assert schedule.update_date == date(2023, 10, 16)
    assert schedule.update_interval == 7
    schedule = schedules[-1]
    assert schedule.elem_id == 3
    assert schedule.next_date == date(2023, 11, 6)
    assert schedule.update_date == date(2023, 11, 13)
    assert schedule.update_interval == 7
    # change user position
    assert indiv_schedule.current_order() == [4, 2, 1, 7, 3]
    indiv_schedule.change_user_pos(7, 0)
    assert (f"Schedule '{indiv_schedule.name}' changed " +
            "user with id '7' position to '0'") in caplog.text
    assert indiv_schedule.current_order() == [7, 4, 2, 1, 3]
    with dbSession() as db_session:
        schedules = db_session.scalars(
            select(Schedule)
            .filter_by(name=indiv_schedule.name)).all()
    schedule = schedules[0]
    assert schedule.elem_id == 7
    assert schedule.next_date == date(2023, 10, 9)
    assert schedule.update_date == date(2023, 10, 16)
    schedule = schedules[2]
    assert schedule.elem_id == 2
    assert schedule.next_date == date(2023, 10, 23)
    assert schedule.update_date == date(2023, 10, 30)
    schedule = schedules[4]
    assert schedule.elem_id == 3
    assert schedule.next_date == date(2023, 11, 6)
    assert schedule.update_date == date(2023, 11, 13)
    indiv_schedule.change_user_pos(2, 4)
    assert (f"Schedule '{indiv_schedule.name}' changed " +
            "user with id '2' position to '4'") in caplog.text
    assert indiv_schedule.current_order() == [7, 4, 1, 3, 2]
    with dbSession() as db_session:
        schedules = db_session.scalars(
            select(Schedule)
            .filter_by(name=indiv_schedule.name)).all()
    schedule = schedules[0]
    assert schedule.elem_id == 7
    assert schedule.next_date == date(2023, 10, 9)
    assert schedule.update_date == date(2023, 10, 16)
    schedule = schedules[2]
    assert schedule.elem_id == 1
    assert schedule.next_date == date(2023, 10, 23)
    assert schedule.update_date == date(2023, 10, 30)
    schedule = schedules[4]
    assert schedule.elem_id == 2
    assert schedule.next_date == date(2023, 11, 6)
    assert schedule.update_date == date(2023, 11, 13)
    # teardown
    with dbSession() as db_session:
        for schedule in schedules:
            db_session.delete(schedule)
        db_session.commit()


@freeze_time("2023-10-04")
def test_explicit_individual_schedule_creation_2(caplog: LogCaptureFixture):
    """Explicit date checking 2 week interval"""
    # pylint: disable=protected-access
    assert date.today() == date(2023, 10, 4)
    assert date.today().isoweekday() == 3
    indiv_schedule = IndivSchedule(
        name="Test some schedule",
        sch_day=1,
        sch_day_update=6,
        switch_interval=timedelta(weeks=2),
        start_date=date.today())
    users_ids = [3, 7, 2, 4, 1]
    # test register order
    indiv_schedule.register(users_ids)
    assert f"Schedule '{indiv_schedule.name}' registered" in caplog.text
    with dbSession() as db_session:
        schedules = db_session.scalars(
            select(Schedule)
            .filter_by(name=indiv_schedule.name)).all()
    # user 3
    schedule = schedules[0]
    assert schedule.elem_id == 3
    assert schedule.next_date == date(2023, 10, 9)
    assert schedule.update_date == date(2023, 10, 14)
    assert schedule.update_interval == 14
    # user 7
    schedule = schedules[1]
    assert schedule.elem_id == 7
    assert schedule.next_date == date(2023, 10, 23)
    assert schedule.update_date == date(2023, 10, 28)
    assert schedule.update_interval == 14
    # user 2
    schedule = schedules[2]
    assert schedule.elem_id == 2
    assert schedule.next_date == date(2023, 11, 6)
    assert schedule.update_date == date(2023, 11, 11)
    assert schedule.update_interval == 14
    # user 4
    schedule = schedules[3]
    assert schedule.elem_id == 4
    assert schedule.next_date == date(2023, 11, 20)
    assert schedule.update_date == date(2023, 11, 25)
    assert schedule.update_interval == 14
    # user 1
    schedule = schedules[4]
    assert schedule.elem_id == 1
    assert schedule.next_date == date(2023, 12, 4)
    assert schedule.update_date == date(2023, 12, 9)
    assert schedule.update_interval == 14
    # test data
    assert indiv_schedule.data() == [
        ["user3", date(2023, 10, 9).strftime("%d.%m.%Y")],
        ["user7", date(2023, 10, 23).strftime("%d.%m.%Y")],
        ["user2", date(2023, 11, 6).strftime("%d.%m.%Y")],
        ["user4", date(2023, 11, 20).strftime("%d.%m.%Y")],
        ["user1", date(2023, 12, 4).strftime("%d.%m.%Y")]
    ]
    # add user
    with dbSession() as db_session:
        db_session.get(User, 5).reg_req = False
        db_session.commit()
        indiv_schedule.add_user(5)
        schedules = db_session.scalars(
            select(Schedule)
            .filter_by(name=indiv_schedule.name)).all()
    assert f"Schedule '{indiv_schedule.name}' added 'user5'" in caplog.text
    schedule = schedules[-1]
    assert schedule.elem_id == 5
    assert schedule.next_date == date(2023, 12, 18)
    assert schedule.update_date == date(2023, 12, 23)
    assert schedule.update_interval == 14
    # remove user
    with dbSession() as db_session:
        db_session.get(User, 5).reg_req = True
        db_session.commit()
        indiv_schedule.remove_user(5)
        schedules = db_session.scalars(
            select(Schedule)
            .filter_by(name=indiv_schedule.name)).all()
        assert not db_session.scalar(
            select(Schedule)
            .filter_by(name=indiv_schedule.name, elem_id=5))
    assert (f"Schedule '{indiv_schedule.name}' " +
            "removed user with id '5'") in caplog.text
    schedule = schedules[0]
    assert schedule.elem_id == 3
    assert schedule.next_date == date(2023, 10, 9)
    assert schedule.update_date == date(2023, 10, 14)
    assert schedule.update_interval == 14
    schedule = schedules[-1]
    assert schedule.elem_id == 1
    assert schedule.next_date == date(2023, 12, 4)
    assert schedule.update_date == date(2023, 12, 9)
    assert schedule.update_interval == 14
    # change user position
    assert indiv_schedule.current_order() == [3, 7, 2, 4, 1]
    indiv_schedule.change_user_pos(7, 4)
    assert (f"Schedule '{indiv_schedule.name}' changed " +
            "user with id '7' position to '4'") in caplog.text
    assert indiv_schedule.current_order() == [3, 2, 4, 1, 7]
    with dbSession() as db_session:
        schedules = db_session.scalars(
            select(Schedule)
            .filter_by(name=indiv_schedule.name)).all()
    schedule = schedules[0]
    assert schedule.elem_id == 3
    assert schedule.next_date == date(2023, 10, 9)
    assert schedule.update_date == date(2023, 10, 14)
    schedule = schedules[2]
    assert schedule.elem_id == 4
    assert schedule.next_date == date(2023, 11, 6)
    assert schedule.update_date == date(2023, 11, 11)
    schedule = schedules[4]
    assert schedule.elem_id == 7
    assert schedule.next_date == date(2023, 12, 4)
    assert schedule.update_date == date(2023, 12, 9)
    indiv_schedule.change_user_pos(4, 1)
    assert (f"Schedule '{indiv_schedule.name}' changed " +
            "user with id '4' position to '1'") in caplog.text
    assert indiv_schedule.current_order() == [3, 4, 2, 1, 7]
    with dbSession() as db_session:
        schedules = db_session.scalars(
            select(Schedule)
            .filter_by(name=indiv_schedule.name)).all()
    schedule = schedules[0]
    assert schedule.elem_id == 3
    assert schedule.next_date == date(2023, 10, 9)
    assert schedule.update_date == date(2023, 10, 14)
    schedule = schedules[2]
    assert schedule.elem_id == 2
    assert schedule.next_date == date(2023, 11, 6)
    assert schedule.update_date == date(2023, 11, 11)
    schedule = schedules[4]
    assert schedule.elem_id == 7
    assert schedule.next_date == date(2023, 12, 4)
    assert schedule.update_date == date(2023, 12, 9)
    # teardown
    with dbSession() as db_session:
        for schedule in schedules:
            db_session.delete(schedule)
        db_session.commit()


def test_failed_indiv_schedule_creation_duplicate(caplog: LogCaptureFixture):
    """test_failed_individual_schedule_creation_duplicate"""
    IndivSchedule(
        name=CLEANING_SCH["db_name"],
        sch_day=1,
        sch_day_update=1,
        switch_interval=timedelta(weeks=1),
        start_date=date.today()).register()
    assert f"Schedule '{CLEANING_SCH['db_name']}' (register): allready exists"\
        in caplog.messages


@pytest.mark.parametrize(
    ("name", "sch_day", "sch_day_update",
     "switch_interval", "start_date",
     "err_msg"), (
        # name
        ("", 1, 1,
         timedelta(weeks=1), date.today(),
         "The schedule must have a name"),
        (" ", 1, 1,
         timedelta(weeks=1), date.today(),
         "The schedule must have a name"),
        (None, 1, 1,
         timedelta(weeks=1), date.today(),
         "'NoneType' object has no attribute 'strip'"),
        # sch_day
        ("test_sch", 0, 1,
         timedelta(weeks=1), date.today(),
         "Schedule day attribute is not valid"),
        ("test_sch", -2, 1,
         timedelta(weeks=1), date.today(),
         "Schedule day attribute is not valid"),
        ("test_sch", 9, 1,
         timedelta(weeks=1), date.today(),
         "Schedule day attribute is not valid"),
        ("test_sch", None, 1,
         timedelta(weeks=1), date.today(),
         "Schedule day attribute is not valid"),
        ("test_sch", "", 1,
         timedelta(weeks=1), date.today(),
         "Schedule day attribute is not valid"),
        ("test_sch", " ", 1,
         timedelta(weeks=1), date.today(),
         "Schedule day attribute is not valid"),
        ("test_sch", "a", 1,
         timedelta(weeks=1), date.today(),
         "Schedule day attribute is not valid"),
        # sch_day_update
        ("test_sch", 1, 0,
         timedelta(weeks=1), date.today(),
         "Schedule day change attribute is not valid"),
        ("test_sch", 1, -1,
         timedelta(weeks=1), date.today(),
         "Schedule day change attribute is not valid"),
        ("test_sch", 1, 8,
         timedelta(weeks=1), date.today(),
         "Schedule day change attribute is not valid"),
        ("test_sch", 1, None,
         timedelta(weeks=1), date.today(),
         "Schedule day change attribute is not valid"),
        ("test_sch", 1, "",
         timedelta(weeks=1), date.today(),
         "Schedule day change attribute is not valid"),
        ("test_sch", 1, " ",
         timedelta(weeks=1), date.today(),
         "Schedule day change attribute is not valid"),
        ("test_sch", 1, "c",
         timedelta(weeks=1), date.today(),
         "Schedule day change attribute is not valid"),
        # group switch_interval
        ("test_sch", 1, 1,
         timedelta(hours=12), date.today(),
         "Schedule switch interval is not valid"),
        ("test_sch", 1, 1,
         None, date.today(),
         "'<' not supported between instances of 'NoneType' and"),
        ("test_sch", 1, 1,
         "", date.today(),
         "'<' not supported between instances of 'str' and"),
        ("test_sch", 1, 1,
         " ", date.today(),
         "'<' not supported between instances of 'str' and"),
        ("test_sch", 1, 1,
         "a", date.today(),
         "'<' not supported between instances of 'str' and"),
        ("test_sch", 1, 1,
         2, date.today(),
         "'<' not supported between instances of 'int' and"),
        # start_date
        ("test_sch", 1, 1,
         timedelta(weeks=1), date.today() - timedelta(days=1),
         "Schedule start date cannot be in the past"),
        ("test_sch", 1, 1,
         timedelta(weeks=1), None,
         "'<' not supported between instances of 'NoneType' and"),
        ("test_sch", 1, 1,
         timedelta(weeks=1), "",
         "'<' not supported between instances of 'str' and"),
        ("test_sch", 1, 1,
         timedelta(weeks=1), " ",
         "'<' not supported between instances of 'str' and"),
        ("test_sch", 1, 1,
         timedelta(weeks=1), "a",
         "'<' not supported between instances of 'str' and"),
        ("test_sch", 1, 1,
         timedelta(weeks=1), 3,
         "'<' not supported between instances of 'int' and"),
))
def test_failed_individual_schedule_creation(
    name, sch_day, sch_day_update, switch_interval, start_date, err_msg,
    caplog: LogCaptureFixture):
    """test_failed_individual_schedule_creation"""
    with pytest.raises((ValueError, AttributeError, TypeError), match=err_msg):
        IndivSchedule(
            name=name,
            sch_day=sch_day,
            sch_day_update=sch_day_update,
            switch_interval=switch_interval,
            start_date=start_date).register()
    assert f"Schedule '{name}' registered" not in caplog.messages


def test_individual_schedule_unregister(caplog: LogCaptureFixture):
    """test_individual_schedule_unregister"""
    sch_name = "test_sch"
    test_schedule = IndivSchedule(
        name=sch_name,
        sch_day=6,
        sch_day_update=1,
        switch_interval=timedelta(weeks=1),
        start_date=date.today())
    test_schedule.unregister()
    assert (f"Cannot unregister schedule '{test_schedule.name}' " +
        "as it was not found in the database") in caplog.text
    test_schedule.register()
    with dbSession() as db_session:
        assert db_session.scalar(select(Schedule).filter_by(name=sch_name))
        assert f"Schedule '{sch_name}' registered" in caplog.text
        test_schedule.unregister()
        assert not db_session.scalar(select(Schedule).filter_by(name=sch_name))
        assert f"Schedule '{sch_name}' deleted" in caplog.text


@pytest.mark.parametrize(
    ("name", "user_ids_order", "start_date",
     "err_msg"), (
        # name
        (CLEANING_SCH["db_name"], [1, 2, 3, 4, 7], date.today(),
         f"Schedule '{CLEANING_SCH['db_name']}' (register): allready exists"),
        # user_ids_order
        ("test_sch", [1, 2, 3, 7], date.today(),
         "Schedule 'test_sch' (register): list of id's provided is invalid"),
        ("test_sch", [1, 2, 3, 4, 5], date.today(),
         "Schedule 'test_sch' (register): list of id's provided is invalid"),
        # start_date
        ("test_sch", [1, 2, 3, 4, 7], date.today() - timedelta(weeks=1),
         "Schedule 'test_sch' (register): start date " +
         f"'{(date.today() - timedelta(weeks=1)).isoformat()}' " +
         "provided is invalid"),
        ("test_sch", [1, 2, 3, 4, 7], date.today() + timedelta(days=1),
         "Schedule 'test_sch' (register): start date " +
         f"'{(date.today() + timedelta(days=1)).isoformat()}' " +
         "provided is invalid"),
))
def test_failed_individual_schedule_registration(
        name, user_ids_order, start_date, err_msg,
        caplog: LogCaptureFixture):
    """failed_individual_schedule_registration"""
    IndivSchedule(
        name=name,
        sch_day=date.today().isocalendar()[2],
        sch_day_update=(date.today() + timedelta(days=1)).isocalendar()[2],
        switch_interval=timedelta(weeks=1),
        start_date=date.today()
    ).register(
        user_ids_order=user_ids_order,
        start_date=start_date)
    assert err_msg in caplog.messages
    assert f"Schedule '{name}' registered" not in caplog.messages


def test_failed_individual_schedule_data(caplog: LogCaptureFixture):
    """test_failed_individual_schedule_data"""
    IndivSchedule(
        name="test_sch",
        sch_day=date.today().isocalendar()[2],
        sch_day_update=(date.today() + timedelta(days=1)).isocalendar()[2],
        switch_interval=timedelta(weeks=1),
        start_date=date.today()
    ).data()
    assert "Schedule 'test_sch' (data): is not registered" in caplog.messages


@pytest.mark.parametrize(
    ("name", "user_id",
     "err_msg"), (
        # name
        ("test_sch", 1,
         "Schedule 'test_sch' (add_user): is not registered"),
        # user_id
        (CLEANING_SCH["db_name"], 5,
         f"Schedule '{CLEANING_SCH['db_name']}' (add_user): invalid user_id"),
        (CLEANING_SCH["db_name"], None,
         f"Schedule '{CLEANING_SCH['db_name']}' (add_user): invalid user_id"),
        (CLEANING_SCH["db_name"], "",
         f"Schedule '{CLEANING_SCH['db_name']}' (add_user): invalid user_id"),
        (CLEANING_SCH["db_name"], " ",
         f"Schedule '{CLEANING_SCH['db_name']}' (add_user): invalid user_id"),
        (CLEANING_SCH["db_name"], "a",
         f"Schedule '{CLEANING_SCH['db_name']}' (add_user): invalid user_id"),
        (CLEANING_SCH["db_name"], 22,
         f"Schedule '{CLEANING_SCH['db_name']}' (add_user): invalid user_id"),
        (CLEANING_SCH["db_name"], 0,
         f"Schedule '{CLEANING_SCH['db_name']}' (add_user): invalid user_id"),
        (CLEANING_SCH["db_name"], -6,
         f"Schedule '{CLEANING_SCH['db_name']}' (add_user): invalid user_id"),
        (CLEANING_SCH["db_name"], 1,
         f"Schedule '{CLEANING_SCH['db_name']}' (add_user): user with id " +
         "'1' is already scheduled"),
        (CLEANING_SCH["db_name"], 3,
         f"Schedule '{CLEANING_SCH['db_name']}' (add_user): user with id " +
         "'3' is already scheduled"),
))
def test_failed_individual_schedule_add_user(
        name, user_id, err_msg, caplog: LogCaptureFixture):
    """test_failed_add_user"""
    IndivSchedule(
        name=name,
        sch_day=date.today().isocalendar()[2],
        sch_day_update=(date.today() + timedelta(days=1)).isocalendar()[2],
        switch_interval=timedelta(weeks=1),
        start_date=date.today()
    ).add_user(user_id)
    assert err_msg in caplog.text


@pytest.mark.parametrize(
    ("name", "user_id",
     "err_msg"), (
        # name
        ("test_sch", 1,
         "Schedule 'test_sch' (remove_user): is not registered"),
        # user_id (tested thoroughly at failed add user)
        (CLEANING_SCH["db_name"], "a",
         f"Schedule '{CLEANING_SCH['db_name']}' (remove_user): " +
         "invalid user_id"),
         # not in schedule
        (CLEANING_SCH["db_name"], 5,
         f"Schedule '{CLEANING_SCH['db_name']}' (remove_user): " +
         "user with id '5' is not in the schedule"),
))
def test_failed_individual_schedule_remove_user(
        name, user_id, err_msg, caplog: LogCaptureFixture):
    """test_failed_individual_schedule_remove_user"""
    IndivSchedule(
        name=name,
        sch_day=date.today().isocalendar()[2],
        sch_day_update=(date.today() + timedelta(days=1)).isocalendar()[2],
        switch_interval=timedelta(weeks=1),
        start_date=date.today()
    ).remove_user(user_id)
    assert err_msg in caplog.text


@pytest.mark.parametrize(
    ("name", "user_id", "new_pos",
     "err_msg"), (
        # name
        ("test_sch", 1, 1,
         "Schedule 'test_sch' (change_user_pos): is not registered"),
        # user_id (tested thoroughly at failed add user)
        (CLEANING_SCH["db_name"], 6, 2,
         f"Schedule '{CLEANING_SCH['db_name']}' (change_user_pos): " +
         "invalid user_id"),
        # new_pos
        (CLEANING_SCH["db_name"], 1, None,
         f"Schedule '{CLEANING_SCH['db_name']}' (change_user_pos): " +
         "invalid new position"),
        (CLEANING_SCH["db_name"], 1, "",
         f"Schedule '{CLEANING_SCH['db_name']}' (change_user_pos): " +
         "invalid new position"),
        (CLEANING_SCH["db_name"], 1, " ",
         f"Schedule '{CLEANING_SCH['db_name']}' (change_user_pos): " +
         "invalid new position"),
        (CLEANING_SCH["db_name"], 1, "a",
         f"Schedule '{CLEANING_SCH['db_name']}' (change_user_pos): " +
         "invalid new position"),
        (CLEANING_SCH["db_name"], 1, 5,
         f"Schedule '{CLEANING_SCH['db_name']}' (change_user_pos): " +
         "invalid new position"),
        (CLEANING_SCH["db_name"], 1, -2,
         f"Schedule '{CLEANING_SCH['db_name']}' (change_user_pos): " +
         "invalid new position"),
        # not in schedule
        (CLEANING_SCH["db_name"], 5, 0,
         f"Schedule '{CLEANING_SCH['db_name']}' (change_user_pos): " +
         "user with id '5' is not in the schedule"),
        # already at position
        (CLEANING_SCH["db_name"], 1, 0,
         f"Schedule '{CLEANING_SCH['db_name']}' (change_user_pos): " +
         "user with id '1' is already at position"),
        (CLEANING_SCH["db_name"], 3, 2,
         f"Schedule '{CLEANING_SCH['db_name']}' (change_user_pos): " +
         "user with id '3' is already at position"),
        (CLEANING_SCH["db_name"], 7, 4,
         f"Schedule '{CLEANING_SCH['db_name']}' (change_user_pos): " +
         "user with id '7' is already at position"),
))
def test_failed_individual_schedule_change_user_position(
        name, user_id, new_pos, err_msg, caplog: LogCaptureFixture):
    """test_failed_individual_schedule_change_user_position"""
    with dbSession() as db_session:
        db_session.get(User, 5).reg_req = False
        db_session.commit()
        IndivSchedule(
            name=name,
            sch_day=date.today().isocalendar()[2],
            sch_day_update=(date.today() + timedelta(days=1)).isocalendar()[2],
            switch_interval=timedelta(weeks=1),
            start_date=date.today()
        ).change_user_pos(user_id, new_pos)
        # teardown
        db_session.get(User, 5).reg_req = True
        db_session.commit()
    assert err_msg in caplog.text
# endregion


# region: schedule page
def test_schedule_page_user_logged_in(
        client: FlaskClient, user_logged_in: User):
    """test_schedule_page_group_schedule_user_logged_in"""
    with client:
        client.get("/")
        assert session["user_name"] == user_logged_in.name
        assert not session["admin"]
        response = client.get(url_for("sch.schedules"))
        assert response.status_code == 200
        assert "Schedules" in response.text
        assert SAT_GROUP_SCH["name_for_test"] in response.text
        assert "Group 1" in response.text
        assert "Group 2" in response.text
        assert CLEANING_SCH["name_for_test"] in response.text
        assert f'<span class="fw-bolder">{session["user_name"]}</span>' \
            in response.text
        assert url_for("users.edit_user", username=session["user_name"]) \
            not in response.text
        with dbSession() as db_session:
            users_in_use = db_session.scalars(
                select(User.name)
                .filter_by(in_use=True, reg_req=False)).all()
            users_not_in_use = db_session.scalars(
                select(User.name)
                .filter_by(in_use=False)).all()
            users_reg_req = db_session.scalars(
                select(User.name)
                .filter_by(reg_req=True)).all()
        for username in users_in_use:
            assert username in response.text
        for username in users_not_in_use:
            assert username not in response.text
        for username in users_reg_req:
            assert username not in response.text
        # group schedule dates
        assert f"<b>{date.today().strftime('%d.%m.%Y')}</b>" in response.text
        for week in range(1, 6):
            assert (date.today() + timedelta(weeks=week)).strftime("%d.%m.%Y")\
                in response.text
        # individual schedule dates
        # pylint: disable=protected-access
        first_date = cleaning_schedule._first_date()
        assert f"<b>{first_date.strftime('%d.%m.%Y')}</b>" \
            not in response.text
        for week in range(len(users_in_use)):
            assert (first_date + timedelta(weeks=week)
                    ).strftime("%d.%m.%Y") in response.text


def test_schedule_page_group_schedule_admin_logged_in(
        client: FlaskClient, admin_logged_in: User):
    """test_schedule_page_group_schedule_admin_logged_in"""
    with client:
        client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        response = client.get(url_for("sch.schedules"))
        assert response.status_code == 200
        assert "Schedules" in response.text
        assert SAT_GROUP_SCH["name_for_test"] in response.text
        assert CLEANING_SCH["name_for_test"] in response.text
        assert "Group 1" in response.text
        assert "Group 2" in response.text
        assert f"<b>{date.today().strftime('%d.%m.%Y')}</b>" \
            in response.text
        with freeze_time(date.today() + timedelta(weeks=1)):
            response = client.get(url_for("sch.schedules"))
            assert f"<b>{date.today().strftime('%d.%m.%Y')}</b>" \
                in response.text
        assert f'<span class="fw-bolder">{session["user_name"]}</span>' \
            not in response.text
        assert url_for("users.edit_user", username=session["user_name"]) \
            in response.text
        # pylint: disable=protected-access
        first_date = cleaning_schedule._first_date()
        assert f"<b>{first_date.strftime('%d.%m.%Y')}</b>" \
            in response.text
# endregion
