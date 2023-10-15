"""Schedules blueprint tests."""

from datetime import date, timedelta

import pytest
from freezegun import freeze_time
from flask import session, url_for
from flask.testing import FlaskClient
from pytest import LogCaptureFixture
from sqlalchemy import select

from blueprints.sch import SAT_GROUP_SCH
from blueprints.sch.sch import GroupSchedule
from database import Schedule, User, dbSession

pytestmark = pytest.mark.sch


# region: group schedule creation
@pytest.mark.parametrize(
    ("num_groups", "first_group", "sch_day", "sch_day_update",
     "groups_switch", "start_date"), (
        (2, 1, 6, 1,
         timedelta(weeks=2), date.today()),
        (3, 2, 1, 3,
         timedelta(weeks=1), date.today() + timedelta(weeks=1)),
        (4, 4, 5, 4,
         timedelta(weeks=2), date.today()),
))
def test_group_schedule_creation(
        num_groups, first_group, sch_day, sch_day_update,
        groups_switch, start_date):
    """test_group_schedule_creation"""
    sch_name = "test_sch"
    GroupSchedule(
        name=sch_name,
        user_attr=User.sat_group.name,
        num_groups=num_groups,
        first_group=first_group,
        sch_day=sch_day,
        sch_day_update=sch_day_update,
        groups_switch=groups_switch,
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
            next_date += groups_switch
            # check update_date
            assert schedule.update_date == update_date
            update_date += groups_switch
            # check update_interval
            assert schedule.update_interval \
                    == (groups_switch * num_groups).days
        # teardown
        for schedule in schedules:
            db_session.delete(schedule)
        db_session.commit()


@freeze_time("2023-10-05")
def test_explicit_group_schedule_creation_1(caplog: LogCaptureFixture):
    """Explicit date checking 2 groups 2 weeks interval"""
    name = "Test saturday working"
    num_groups = 2
    groups_switch = timedelta(weeks=2)
    assert date.today() == date(2023, 10, 5)
    assert date.today().isoweekday() == 4
    GroupSchedule(
        name=name,
        user_attr=User.sat_group.name,
        num_groups=num_groups,
        first_group=1,
        sch_day=6,
        sch_day_update=1,
        groups_switch=groups_switch,
        start_date=date.today()).register()
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
def test_explicit_group_schedule_creation_2(caplog: LogCaptureFixture):
    """Explicit date checking 2 groups 1 week interval"""
    name = "Test sunday movie"
    num_groups = 2
    groups_switch = timedelta(weeks=1)
    assert date.today() == date(2023, 10, 5)
    assert date.today().isoweekday() == 4
    GroupSchedule(
        name=name,
        user_attr=User.sat_group.name,
        num_groups=num_groups,
        first_group=2,
        sch_day=7,
        sch_day_update=1,
        groups_switch=groups_switch,
        start_date=date(2023, 10, 14)).register()
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
def test_explicit_group_schedule_creation_3(caplog: LogCaptureFixture):
    """Explicit date checking 3 groups 3 weeks interval"""
    name = "Test some other schedule"
    num_groups = 3
    groups_switch = timedelta(weeks=3)
    assert date.today() == date(2023, 10, 5)
    assert date.today().isoweekday() == 4
    GroupSchedule(
        name=name,
        user_attr=User.sat_group.name,
        num_groups=num_groups,
        first_group=2,
        sch_day=4,
        sch_day_update=6,
        groups_switch=groups_switch,
        start_date=date.today()).register()
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


def test_failed_group_schedule_creation_duplicate(caplog: LogCaptureFixture):
    """test_failed_group_schedule_creation_duplicate"""
    name = "Test some schedule"
    test_schedule = GroupSchedule(
        name=name,
        user_attr=User.sat_group.name,
        sch_day=6,
        sch_day_update=1,
        groups_switch=timedelta(weeks=1))
    test_schedule.register()
    assert f"Group schedule '{name}' created" in caplog.messages
    caplog.clear()
    test_schedule.register()
    assert f"Schedule '{name}' allready exists" in caplog.messages
    # teardown
    with dbSession() as db_session:
        schedules = db_session.scalars(
            select(Schedule)
            .filter_by(name=name)).all()
        for schedule in schedules:
            db_session.delete(schedule)
        db_session.commit()


@pytest.mark.parametrize(
    ("name", "user_attr", "num_groups", "first_group",
     "sch_day", "sch_day_update", "groups_switch", "start_date",
     "err_msg"), (
        # name
        ("", "sat_group", 2, 1,
         6, 1, timedelta(weeks=2), date.today(),
         "The schedule must have a name"),
        (" ", "sat_group", 2, 1,
         6, 1, timedelta(weeks=2), date.today(),
         "The schedule must have a name"),
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
        ("test_sch", "sat_group", 2, 1,
         6, 6, timedelta(weeks=2), date.today(),
         "Schedule day change attribute is not valid"),
        # group groups_switch
        ("test_sch", "sat_group", 2, 1,
         6, 1, timedelta(hours=23), date.today(),
         "Schedule groups switch attribute is not valid"),
        # start_date
        ("test_sch", "sat_group", 2, 1,
         6, 1, timedelta(weeks=2), date.today() - timedelta(days=1),
         "Schedule start date cannot be in the past"),
))
def test_failed_group_schedule_creation(
        name, user_attr, num_groups, first_group,
        sch_day, sch_day_update, groups_switch, start_date,
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
            groups_switch=groups_switch,
            start_date=start_date)
    assert "Group schedule 'test_sch' created" not in caplog.messages


def test_group_schedule_unregister(caplog: LogCaptureFixture):
    """test_group_schedule_unregister"""
    sch_name = "test_sch"
    test_schedule = GroupSchedule(sch_name, User.sat_group.name)
    # test auto-registering
    test_schedule.data()
    with dbSession() as db_session:
        assert db_session.scalar(select(Schedule).filter_by(name=sch_name))
        assert f"Group schedule '{sch_name}' created" in caplog.messages
        test_schedule.unregister()
        assert not db_session.scalar(select(Schedule).filter_by(name=sch_name))
        assert f"Group schedule '{sch_name}' deleted" in caplog.messages
# endregion


# region: schedule page
def test_schedule_page_group_schedule_user_logged_in(
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
        assert f"<b>{date.today().strftime('%d.%m.%Y')}</b>" in response.text
        for week in range(1, 6):
            assert (date.today() + timedelta(weeks=week)).strftime("%d.%m.%Y")\
                in response.text


def test_schedule_page_group_schedule_admin_logged_in(
        client: FlaskClient, admin_logged_in: User):
    """test_schedule_page_group_schedule_admin_logged_in"""
    with client:
        with freeze_time(date.today() + timedelta(weeks=1)):
            client.get("/")
            assert session["user_name"] == admin_logged_in.name
            assert session["admin"]
            response = client.get(url_for("sch.schedules"))
            assert response.status_code == 200
            assert "Schedules" in response.text
            assert SAT_GROUP_SCH["name_for_test"] in response.text
            assert "Group 1" in response.text
            assert "Group 2" in response.text
            assert f'<span class="fw-bolder">{session["user_name"]}</span>' \
                not in response.text
            assert url_for("users.edit_user", username=session["user_name"]) \
                in response.text
            assert f"<b>{date.today().strftime('%d.%m.%Y')}</b>" \
                in response.text
# endregion
