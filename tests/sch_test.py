"""Schedules blueprint tests."""

import re
import string
from datetime import date, timedelta

import pytest
from flask import session, url_for
from flask.testing import FlaskClient
from freezegun import freeze_time
from hypothesis import assume, example, given
from hypothesis import strategies as st
from pytest import LogCaptureFixture
from sqlalchemy import select

from blueprints.sch.sch import (BaseSchedule, GroupSchedule, IndivSchedule,
                                cleaning_sch, saturday_sch)
from constants import Constant
from database import Schedule, User, dbSession
from tests import ValidSchedule, test_schedules, test_users

pytestmark = pytest.mark.sch


# region: base schedule
def test_base_schedule():
    """Test base schedule not implemented methods"""
    test_sch = BaseSchedule(
        name=ValidSchedule.name,
        sch_day=ValidSchedule.sch_day,
        sch_day_update=ValidSchedule.sch_day_update,
        switch_interval=ValidSchedule.switch_interval,
        start_date=ValidSchedule.start_date)
    with pytest.raises(NotImplementedError):
        test_sch.register()
    with pytest.raises(NotImplementedError):
        test_sch.data()
# endregion


# region: group schedule
@given(name = st.text(min_size=1)
           .map(lambda x: x.strip())
           .filter(lambda x: len(x) > 1)
           .filter(lambda x: x not in [sch["name"] for sch in test_schedules]),
       num_groups = st.integers(min_value=2,
                                max_value=len([user for user in test_users
                                               if user["in_use"]])),
       first_group = st.integers(min_value=1,
                                 max_value=len([user for user in test_users
                                                if user["in_use"]])),
       sch_day = st.integers(min_value=1, max_value=7),
       sch_day_update = st.integers(min_value=1, max_value=7),
       switch_interval = st.timedeltas(min_value=timedelta(weeks=1),
                                       max_value=timedelta(weeks=8)),
       start_date = st.dates(min_value=date.today(),
                             max_value=date.today() + timedelta(days=365)))
@example(name = ValidSchedule.name,
         num_groups = ValidSchedule.num_groups,
         first_group = ValidSchedule.first_group,
         sch_day = ValidSchedule.sch_day,
         sch_day_update = ValidSchedule.sch_day_update,
         switch_interval = ValidSchedule.switch_interval,
         start_date = ValidSchedule.start_date)
def test_group_schedule_creation(
        name: str,
        num_groups: int,
        first_group: int,
        sch_day: int,
        sch_day_update: int,
        switch_interval: timedelta,
        start_date: date):
    """test_group_schedule_creation"""
    assume(first_group <= num_groups)
    elem_id = first_group
    next_date: date = start_date
    while next_date.isoweekday() != sch_day:
        next_date += timedelta(days=1)
    update_date = next_date + timedelta(days=1)
    while update_date.isoweekday() != sch_day_update:
        update_date += timedelta(days=1)
    GroupSchedule(
        name=name,
        user_attr=User.sat_group.name,
        num_groups=num_groups,
        first_group=first_group,
        sch_day=sch_day,
        sch_day_update=sch_day_update,
        switch_interval=switch_interval,
        start_date=start_date
    ).register()
    with dbSession() as db_session:
        # check name
        schedules = db_session.scalars(
            select(Schedule)
            .filter_by(name=name)).all()
        # check num_groups
        assert len(schedules) == num_groups
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
    assert date.today() == date(2023, 10, 5)
    assert date.today().isoweekday() == 4
    GroupSchedule(
        name=ValidSchedule.name,
        user_attr=ValidSchedule.user_attr,
        num_groups=2,
        first_group=1,
        sch_day=6,
        sch_day_update=1,
        switch_interval=timedelta(weeks=2),
        start_date=date.today()
    ).register()
    assert f"Schedule '{ValidSchedule.name}' created" in caplog.messages
    with dbSession() as db_session:
        schedules = db_session.scalars(
            select(Schedule)
            .filter_by(name=ValidSchedule.name)).all()
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
    assert date.today() == date(2023, 10, 5)
    assert date.today().isoweekday() == 4
    GroupSchedule(
        name=ValidSchedule.name,
        user_attr=User.sat_group.name,
        num_groups=2,
        first_group=2,
        sch_day=7,
        sch_day_update=1,
        switch_interval=timedelta(weeks=1),
        start_date=date(2023, 10, 14)).register()
    assert f"Schedule '{ValidSchedule.name}' created" in caplog.messages
    with dbSession() as db_session:
        schedules = db_session.scalars(
            select(Schedule)
            .filter_by(name=ValidSchedule.name)).all()
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
    assert date.today() == date(2023, 10, 5)
    assert date.today().isoweekday() == 4
    GroupSchedule(
        name=ValidSchedule.name,
        user_attr=User.sat_group.name,
        num_groups=3,
        first_group=2,
        sch_day=4,
        sch_day_update=6,
        switch_interval=timedelta(weeks=3),
        start_date=date.today()).register()
    assert f"Schedule '{ValidSchedule.name}' created" in caplog.messages
    with dbSession() as db_session:
        schedules = db_session.scalars(
            select(Schedule)
            .filter_by(name=ValidSchedule.name)).all()
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


# region: failed schedule creation
@given(name = st.sampled_from([sch["name"] for sch in test_schedules]))
def test_failed_group_schedule_creation_name_duplicate(
        caplog: LogCaptureFixture, name: str):
    """test_failed_group_schedule_creation_name_duplicate"""
    GroupSchedule(
        name=name,
        user_attr=ValidSchedule.user_attr,
        sch_day=ValidSchedule.sch_day,
        sch_day_update=ValidSchedule.sch_day_update,
        switch_interval=ValidSchedule.switch_interval,
        start_date=ValidSchedule.start_date
        ).register()
    assert f"Schedule '{name}' (register): already exists" in caplog.messages


def _test_failed_group_schedule_creation(
        caplog: LogCaptureFixture,
        err_msg: str,
        name = ValidSchedule.name,
        user_attr = ValidSchedule.user_attr,
        num_groups = ValidSchedule.num_groups,
        first_group = ValidSchedule.first_group,
        sch_day = ValidSchedule.sch_day,
        sch_day_update = ValidSchedule.sch_day_update,
        switch_interval = ValidSchedule.switch_interval,
        start_date = ValidSchedule.start_date):
    """Common logic for group schedule creation"""
    with pytest.raises((ValueError, AttributeError), match=err_msg):
        GroupSchedule(
            name=name,
            user_attr=user_attr,
            num_groups=num_groups,
            first_group=first_group,
            sch_day=sch_day,
            sch_day_update=sch_day_update,
            switch_interval=switch_interval,
            start_date=start_date
        ).register()
    assert f"Schedule '{name}' created" not in caplog.messages


@given(name = st.one_of(
    st.none(),
    st.booleans(),
    st.text(max_size=0),
    st.integers()
))
@example(name = " ")
def test_failed_group_schedule_creation_invalid_name(
        caplog: LogCaptureFixture, name):
    """test_failed_group_schedule_creation_invalid_name"""
    err_msg = "The schedule must have a valid name"
    _test_failed_group_schedule_creation(
        caplog=caplog,
        err_msg=err_msg,
        name=name
    )


@given(user_attr = st.one_of(
    st.none(),
    st.booleans(),
    st.text(alphabet=string.ascii_lowercase),
    st.integers()
))
def test_failed_group_schedule_creation_invalid_user_attr(
        caplog: LogCaptureFixture, user_attr):
    """test_failed_group_schedule_creation_invalid_user_attr"""
    if isinstance(user_attr, str):
        assume(not hasattr(User, user_attr))
    err_msg = f"Invalid user attribute '{user_attr}'"
    _test_failed_group_schedule_creation(
        caplog=caplog,
        err_msg=err_msg,
        user_attr=user_attr
    )


@given(num_groups = st.one_of(
    st.none(),
    st.booleans(),
    st.text(),
    st.integers(max_value=1)
))
def test_failed_group_schedule_creation_invalid_num_groups(
        caplog: LogCaptureFixture, num_groups):
    """test_failed_group_schedule_creation_invalid_num_groups"""
    err_msg = "You must have at least two groups"
    _test_failed_group_schedule_creation(
        caplog=caplog,
        err_msg=err_msg,
        num_groups=num_groups
    )


@given(first_group = st.one_of(
    st.none(),
    st.text(),
    st.integers(max_value=0),
    st.integers(min_value=ValidSchedule.num_groups + 1)
))
def test_failed_group_schedule_creation_invalid_first_group(
        caplog: LogCaptureFixture, first_group):
    """test_failed_group_schedule_creation_invalid_first_group"""
    err_msg = "First group attribute is not valid"
    _test_failed_group_schedule_creation(
        caplog=caplog,
        err_msg=err_msg,
        first_group=first_group
    )


@given(sch_day = st.one_of(
    st.none(),
    st.text(),
    st.integers(max_value=0),
    st.integers(min_value=8)
))
def test_failed_group_schedule_creation_invalid_sch_day(
        caplog: LogCaptureFixture, sch_day):
    """test_failed_group_schedule_creation_invalid_sch_day"""
    err_msg = "Schedule day attribute is not valid"
    _test_failed_group_schedule_creation(
        caplog=caplog,
        err_msg=err_msg,
        sch_day=sch_day
    )


@given(sch_day_update = st.one_of(
    st.none(),
    st.text(),
    st.integers(max_value=0),
    st.integers(min_value=8)
))
def test_failed_group_schedule_creation_invalid_sch_day_update(
        caplog: LogCaptureFixture, sch_day_update):
    """test_failed_group_schedule_creation_invalid_sch_day_update"""
    err_msg = "Schedule day change attribute is not valid"
    _test_failed_group_schedule_creation(
        caplog=caplog,
        err_msg=err_msg,
        sch_day_update=sch_day_update
    )


@given(switch_interval = st.one_of(
    st.none(),
    st.booleans(),
    st.text(),
    st.integers(),
    st.timedeltas(max_value=timedelta(days=7) - timedelta(microseconds=1))
))
def test_failed_group_schedule_creation_invalid_switch_interval(
        caplog: LogCaptureFixture, switch_interval):
    """test_failed_group_schedule_creation_invalid_switch_interval"""
    err_msg = "Schedule switch interval is not valid"
    _test_failed_group_schedule_creation(
        caplog=caplog,
        err_msg=err_msg,
        switch_interval=switch_interval
    )


@given(start_date = st.one_of(
    st.none(),
    st.booleans(),
    st.text(),
    st.integers(),
    st.dates(max_value=date.today() - timedelta(days=1))
))
def test_failed_group_schedule_creation_invalid_start_date(
        caplog: LogCaptureFixture, start_date):
    """test_failed_group_schedule_creation_invalid_start_date"""
    err_msg = "Schedule start date is not valid"
    _test_failed_group_schedule_creation(
        caplog=caplog,
        err_msg=err_msg,
        start_date=start_date
    )
# endregion


def test_group_schedule_auto_register_and_unregister(caplog: LogCaptureFixture):
    """Test auto-register when accessing data method and unregister"""
    sch_name = ValidSchedule.name
    test_schedule = GroupSchedule(
        name=sch_name,
        user_attr=ValidSchedule.user_attr,
        sch_day=ValidSchedule.sch_day,
        sch_day_update=ValidSchedule.sch_day_update,
        switch_interval=ValidSchedule.switch_interval,
        start_date=ValidSchedule.start_date)
    with dbSession() as db_session:
        assert not db_session.scalar(select(Schedule).filter_by(name=sch_name))
        # test auto-registering when accessing data method
        test_schedule.data()
        assert db_session.scalar(select(Schedule).filter_by(name=sch_name))
        assert f"Schedule '{sch_name}' created" in caplog.messages
        test_schedule.unregister()
        assert not db_session.scalar(select(Schedule).filter_by(name=sch_name))
        assert f"Schedule '{sch_name}' deleted" in caplog.messages
# endregion


# region: individual schedule
@given(name = st.text(min_size=1)
           .map(lambda x: x.strip())
           .filter(lambda x: len(x) > 1)
           .filter(lambda x: x not in [sch["name"] for sch in test_schedules]),
       sch_day = st.integers(min_value=1, max_value=7),
       sch_day_update = st.integers(min_value=1, max_value=7),
       switch_interval = st.timedeltas(min_value=timedelta(weeks=1),
                                       max_value=timedelta(weeks=8)),
       start_date = st.dates(min_value=date.today(),
                             max_value=date.today() + timedelta(days=365)))
@example(name = ValidSchedule.name,
         sch_day = ValidSchedule.sch_day,
         sch_day_update = ValidSchedule.sch_day_update,
         switch_interval = ValidSchedule.switch_interval,
         start_date = ValidSchedule.start_date)
def test_individual_schedule_creation(
        name: str,
        sch_day: int,
        sch_day_update: int,
        switch_interval: timedelta,
        start_date: date):
    """Test individual schedule creation"""
    IndivSchedule(
        name=name,
        sch_day=sch_day,
        sch_day_update=sch_day_update,
        switch_interval=switch_interval,
        start_date=start_date
    ).register()
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
            .filter_by(name=name)).all()
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
        name=ValidSchedule.name,
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
    user = [user for user in test_users if user["reg_req"]][0]
    with dbSession() as db_session:
        db_session.get(User, user["id"]).reg_req = False
        db_session.commit()
        indiv_schedule.add_user(user["id"])
        schedules = db_session.scalars(
            select(Schedule)
            .filter_by(name=indiv_schedule.name)).all()
    assert f"Schedule '{indiv_schedule.name}' added '{user['name']}'" \
        in caplog.text
    schedule = schedules[-1]
    assert schedule.elem_id == user["id"]
    assert schedule.next_date == date(2023, 11, 13)
    assert schedule.update_date == date(2023, 11, 20)
    assert schedule.update_interval == 7
    # remove user
    with dbSession() as db_session:
        db_session.get(User, user["id"]).reg_req = True
        db_session.commit()
        indiv_schedule.remove_user(user["id"])
        schedules = db_session.scalars(
            select(Schedule)
            .filter_by(name=indiv_schedule.name)).all()
        assert not db_session.scalar(
            select(Schedule)
            .filter_by(name=indiv_schedule.name, elem_id=user["id"]))
    assert (f"Schedule '{indiv_schedule.name}' " +
            f"removed user with id '{user['id']}'") in caplog.text
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
        name=ValidSchedule.name,
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
    user = [user for user in test_users if user["reg_req"]][0]
    with dbSession() as db_session:
        db_session.get(User, user["id"]).reg_req = False
        db_session.commit()
        indiv_schedule.add_user(user["id"])
        schedules = db_session.scalars(
            select(Schedule)
            .filter_by(name=indiv_schedule.name)).all()
    assert f"Schedule '{indiv_schedule.name}' added '{user['name']}'" \
        in caplog.text
    schedule = schedules[-1]
    assert schedule.elem_id == user["id"]
    assert schedule.next_date == date(2023, 12, 18)
    assert schedule.update_date == date(2023, 12, 23)
    assert schedule.update_interval == 14
    # remove user
    with dbSession() as db_session:
        db_session.get(User, user["id"]).reg_req = True
        db_session.commit()
        indiv_schedule.remove_user(user["id"])
        schedules = db_session.scalars(
            select(Schedule)
            .filter_by(name=indiv_schedule.name)).all()
        assert not db_session.scalar(
            select(Schedule)
            .filter_by(name=indiv_schedule.name, elem_id=user["id"]))
    assert (f"Schedule '{indiv_schedule.name}' " +
            f"removed user with id '{user['id']}'") in caplog.text
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


# region: failed schedule creation
@given(name = st.sampled_from([sch["name"] for sch in test_schedules]))
def test_failed_indiv_schedule_creation_duplicate(
        caplog: LogCaptureFixture, name: str):
    """test_failed_indiv_schedule_creation_duplicate"""
    IndivSchedule(
        name=name,
        sch_day=ValidSchedule.sch_day,
        sch_day_update=ValidSchedule.sch_day_update,
        switch_interval=ValidSchedule.switch_interval,
        start_date=ValidSchedule.start_date
    ).register()
    assert f"Schedule '{name}' (register): already exists" in caplog.messages


def _test_failed_individual_schedule_creation(
        caplog: LogCaptureFixture,
        err_msg: str,
        name = ValidSchedule.name,
        sch_day = ValidSchedule.sch_day,
        sch_day_update = ValidSchedule.sch_day_update,
        switch_interval = ValidSchedule.switch_interval,
        start_date = ValidSchedule.start_date):
    """Common logic for individual schedule creation"""
    with pytest.raises((ValueError, AttributeError, TypeError), match=err_msg):
        IndivSchedule(
            name=name,
            sch_day=sch_day,
            sch_day_update=sch_day_update,
            switch_interval=switch_interval,
            start_date=start_date
        ).register()
    assert f"Schedule '{name}' registered" not in caplog.messages


@given(name = st.one_of(
    st.none(),
    st.booleans(),
    st.text(max_size=0),
    st.integers()
))
@example(name = " ")
def test_failed_indiv_schedule_creation_invalid_name(
        caplog: LogCaptureFixture, name):
    """test_failed_indiv_schedule_creation_invalid_name"""
    err_msg = "The schedule must have a valid name"
    _test_failed_individual_schedule_creation(
        caplog=caplog,
        err_msg=err_msg,
        name=name
    )


@given(sch_day = st.one_of(
    st.none(),
    st.text(),
    st.integers(max_value=0),
    st.integers(min_value=8)
))
def test_failed_indiv_schedule_creation_invalid_sch_day(
        caplog: LogCaptureFixture, sch_day):
    """test_failed_indiv_schedule_creation_invalid_sch_day"""
    err_msg = "Schedule day attribute is not valid"
    _test_failed_individual_schedule_creation(
        caplog=caplog,
        err_msg=err_msg,
        sch_day=sch_day
    )


@given(sch_day_update = st.one_of(
    st.none(),
    st.text(),
    st.integers(max_value=0),
    st.integers(min_value=8)
))
def test_failed_indiv_schedule_creation_invalid_sch_day_update(
        caplog: LogCaptureFixture, sch_day_update):
    """test_failed_indiv_schedule_creation_invalid_sch_day_update"""
    err_msg = "Schedule day change attribute is not valid"
    _test_failed_individual_schedule_creation(
        caplog=caplog,
        err_msg=err_msg,
        sch_day_update=sch_day_update
    )


@given(switch_interval = st.one_of(
    st.none(),
    st.booleans(),
    st.text(),
    st.integers(),
    st.timedeltas(max_value=timedelta(days=7) - timedelta(microseconds=1))
))
def test_failed_indiv_schedule_creation_invalid_switch_interval(
        caplog: LogCaptureFixture, switch_interval):
    """test_failed_indiv_schedule_creation_invalid_switch_interval"""
    err_msg = "Schedule switch interval is not valid"
    _test_failed_individual_schedule_creation(
        caplog=caplog,
        err_msg=err_msg,
        switch_interval=switch_interval
    )


@given(start_date = st.one_of(
    st.none(),
    st.booleans(),
    st.text(),
    st.integers(),
    st.dates(max_value=date.today() - timedelta(days=1))
))
def test_failed_indiv_schedule_creation_invalid_start_date(
        caplog: LogCaptureFixture, start_date):
    """test_failed_indiv_schedule_creation_invalid_start_date"""
    err_msg = "Schedule start date is not valid"
    _test_failed_individual_schedule_creation(
        caplog=caplog,
        err_msg=err_msg,
        start_date=start_date
    )
# endregion


def test_individual_schedule_unregister(caplog: LogCaptureFixture):
    """test_individual_schedule_unregister"""
    test_schedule = IndivSchedule(
        name=ValidSchedule.name,
        sch_day=ValidSchedule.sch_day,
        sch_day_update=ValidSchedule.sch_day_update,
        switch_interval=ValidSchedule.switch_interval,
        start_date=ValidSchedule.start_date)
    test_schedule.unregister()
    assert (f"Cannot unregister schedule '{ValidSchedule.name}' " +
            "as it was not found in the database") in caplog.text
    test_schedule.register()
    assert f"Schedule '{ValidSchedule.name}' registered" in caplog.text
    with dbSession() as db_session:
        assert db_session.scalar(select(Schedule)
                                 .filter_by(name=ValidSchedule.name))
        test_schedule.unregister()
        assert not db_session.scalar(select(Schedule)
                                     .filter_by(name=ValidSchedule.name))
    assert f"Schedule '{ValidSchedule.name}' deleted" in caplog.text


def test_individual_schedule_update_date_in_the_past(caplog: LogCaptureFixture):
    """Test auto update schedule date on add_user, remove_user or change_pos"""
    # register a schedule in the past to force auto update
    with freeze_time(date.today() - timedelta(weeks=3)):
        indiv_schedule = IndivSchedule(
            name=ValidSchedule.name,
            sch_day=date.today().isoweekday(),
            sch_day_update=(date.today() + timedelta(days=1)).isoweekday(),
            switch_interval=timedelta(weeks=1),
            start_date=date.today())
        indiv_schedule.register()
        assert f"Schedule '{indiv_schedule.name}' registered" in caplog.text
        caplog.clear()
        current_order = [user["id"] for user in test_users if user["active"]]
        assert indiv_schedule.current_order() == current_order
     # advance 1 week - force 1 update - test add_user
    with freeze_time(date.today() - timedelta(weeks=2)):
        user = [user for user in test_users if user["reg_req"]][0]
        with dbSession() as db_session:
            db_session.get(User, user["id"]).reg_req = False
            db_session.commit()
        indiv_schedule.add_user(user["id"])
    assert re.search(fr"Schedule '{indiv_schedule.name}' user.*will be updated",
                     caplog.text)
    assert f"Schedule '{indiv_schedule.name}' added '{user['name']}'" \
        in caplog.text
    caplog.clear()
    # order rotation and add user to the end
    current_order.append(current_order.pop(0))
    current_order.append(user["id"])
    assert indiv_schedule.current_order() == current_order
    # advance 1 week - force 1 update - test remove_user
    with freeze_time(date.today() - timedelta(weeks=1)):
        with dbSession() as db_session:
            db_session.get(User, user["id"]).reg_req = True
            db_session.commit()
        indiv_schedule.remove_user(user["id"])
    assert re.search(fr"Schedule '{indiv_schedule.name}' user.*will be updated",
                     caplog.text)
    assert (f"Schedule '{indiv_schedule.name}' removed user " +
            f"with id '{user['id']}'") in caplog.text
    caplog.clear()
    # order rotation and remove user
    current_order.append(current_order.pop(0))
    current_order.pop(current_order.index(user["id"]))
    assert indiv_schedule.current_order() == current_order
    # advance to today - force 1 update - test change_user_pos
    user_id = current_order[0]
    new_pos = 1
    indiv_schedule.change_user_pos(user_id, new_pos)
    assert re.search(fr"Schedule '{indiv_schedule.name}' user.*will be updated",
                     caplog.text)
    assert (f"Schedule '{indiv_schedule.name}' changed user with id " +
            f"'{current_order[0]}' position to '1'") in caplog.text
    # order rotation and change user position
    current_order.append(current_order.pop(0))
    current_order.insert(new_pos,
                         current_order.pop(current_order.index(user_id)))
    caplog.clear()
    assert indiv_schedule.current_order() == current_order
    # teardown
    indiv_schedule.unregister()
    assert f"Schedule '{indiv_schedule.name}' deleted" in caplog.text


# region: failed individual schedule registration
def _test_failed_individual_schedule_registration(
        caplog: LogCaptureFixture,
        err_msg: str,
        user_ids_order: list[int] = [user["id"] for user in test_users
                                     if user["active"]],
        reg_start_date: date = ValidSchedule.start_date):
    """Common logic for individual schedule registration"""
    IndivSchedule(
        name=ValidSchedule.name,
        sch_day=ValidSchedule.sch_day,
        sch_day_update=ValidSchedule.sch_day_update,
        switch_interval=ValidSchedule.switch_interval,
        start_date=ValidSchedule.start_date
    ).register(
        user_ids_order=user_ids_order,
        start_date=reg_start_date)
    assert err_msg in caplog.messages
    assert f"Schedule '{ValidSchedule.name}' registered" not in caplog.messages


@given(user_ids_order = st.lists(st.integers(), min_size=1))
def test_failed_individual_schedule_registration_user_ids_order(
        caplog: LogCaptureFixture, user_ids_order: list[int]):
    """test_failed_individual_schedule_registration_user_ids_order"""
    err_msg = (f"Schedule '{ValidSchedule.name}' (register): " +
               "list of id's provided is invalid")
    _test_failed_individual_schedule_registration(
        caplog=caplog,
        err_msg=err_msg,
        user_ids_order=user_ids_order
    )


@given(reg_start_date = st.dates()
       .filter(lambda x: x.isoweekday() != ValidSchedule.sch_day))
def test_failed_individual_schedule_registration_start_date(
        caplog: LogCaptureFixture, reg_start_date: date):
    """test_failed_individual_schedule_registration_start_date"""
    err_msg = (f"Schedule '{ValidSchedule.name}' (register): " +
               f"start date '{reg_start_date.isoformat()}' " +
               "provided is invalid")
    _test_failed_individual_schedule_registration(
        caplog=caplog,
        err_msg=err_msg,
        reg_start_date=reg_start_date
    )
# endregion


def test_failed_individual_schedule_data(caplog: LogCaptureFixture):
    """test_failed_individual_schedule_data"""
    test_schedule = IndivSchedule(
        name=ValidSchedule.name,
        sch_day=ValidSchedule.sch_day,
        sch_day_update=ValidSchedule.sch_day_update,
        switch_interval=ValidSchedule.switch_interval,
        start_date=ValidSchedule.start_date)
    # failed add user to an unregistered schedule
    test_schedule.add_user(1)
    assert f"Schedule '{ValidSchedule.name}' (add_user): is not registered" \
        in caplog.messages
    # failed remove user from an unregistered schedule
    test_schedule.remove_user(1)
    assert (f"Schedule '{ValidSchedule.name}' (remove_user): "
            "is not registered") in caplog.messages
    # failed change user position in an unregistered schedule
    test_schedule.change_user_pos(1, 1)
    assert (f"Schedule '{ValidSchedule.name}' (change_user_pos): "
            "is not registered") in caplog.messages
    # failed get data of an unregistered schedule
    test_schedule.data()
    assert f"Schedule '{ValidSchedule.name}' (data): is not registered" \
        in caplog.messages


@given(sch_name = st.sampled_from([sch["name"] for sch in test_schedules
                                   if sch["type"] == "individual"]),
       user_id = st.one_of(st.integers(min_value=-100,
                                       max_value=Constant.SQLite.Int.max_value),
                           st.none(),
                           st.text()))
@example(sch_name = [sch["name"] for sch in test_schedules
                     if sch["type"] == "individual"][0],
         user_id = [user["id"] for user in test_users if user["active"]][0])
def test_failed_individual_schedule_add_user(
        caplog: LogCaptureFixture, sch_name, user_id):
    """test_failed_individual_schedule_add_user"""
    if user_id in [user["id"] for user in test_users if user["active"]]:
        err_msg = (f"Schedule '{sch_name}' (add_user): user with id " +
                        f"'{user_id}' is already scheduled")
    else:
        err_msg = f"Schedule '{sch_name}' (add_user): invalid user_id"
    IndivSchedule(
        name=sch_name,
        sch_day=ValidSchedule.sch_day,
        sch_day_update=ValidSchedule.sch_day_update,
        switch_interval=ValidSchedule.switch_interval,
        start_date=ValidSchedule.start_date
    ).add_user(user_id)
    assert err_msg in caplog.text


@given(sch_name = st.sampled_from([sch["name"] for sch in test_schedules
                                   if sch["type"] == "individual"]),
       user_id = st.one_of(
           st.integers(min_value=-100,
                       max_value=Constant.SQLite.Int.max_value)
            .filter(lambda x : x not in [user["id"] for user in test_users
                                         if user["active"]]),
           st.none(),
           st.text()))
@example(sch_name = [sch["name"] for sch in test_schedules
                     if sch["type"] == "individual"][0],
         user_id = [user["id"] for user in test_users if not user["in_use"]][0])
def test_failed_individual_schedule_remove_user(
        caplog: LogCaptureFixture, sch_name, user_id):
    """test_failed_individual_schedule_remove_user"""
    if isinstance(user_id, int):
        err_msg = (f"Schedule '{sch_name}' (remove_user): " +
                        f"user with id '{user_id}' is not in the schedule")
    else:
        err_msg = f"Schedule '{sch_name}' (remove_user): invalid user_id"
    IndivSchedule(
        name=sch_name,
        sch_day=ValidSchedule.sch_day,
        sch_day_update=ValidSchedule.sch_day_update,
        switch_interval=ValidSchedule.switch_interval,
        start_date=ValidSchedule.start_date
    ).remove_user(user_id)
    assert err_msg in caplog.text


# region: failed individual schedule change user position
def _test_failed_individual_schedule_change_user_position(
        caplog: LogCaptureFixture,
        err_msg: str,
        sch_name: str,
        user_id: int = [user["id"] for user in test_users if user["active"]][0],
        new_pos: int = 0):
    """Common logic for individual schedule change user position"""
    IndivSchedule(
        name=sch_name,
        sch_day=ValidSchedule.sch_day,
        sch_day_update=ValidSchedule.sch_day_update,
        switch_interval=ValidSchedule.switch_interval,
        start_date=ValidSchedule.start_date
    ).change_user_pos(user_id, new_pos)
    assert err_msg in caplog.text


@given(sch_name = st.sampled_from([sch["name"] for sch in test_schedules
                                   if sch["type"] == "individual"]),
       user_id = st.one_of(
           st.integers(min_value=-100,
                       max_value=Constant.SQLite.Int.max_value)
            .filter(lambda x : x not in [user["id"] for user in test_users
                                         if user["active"]]),
           st.none(),
           st.text()))
def test_failed_individual_schedule_change_user_position_user_id(
        caplog: LogCaptureFixture, sch_name, user_id):
    """test_failed_individual_schedule_change_user_position_user_id"""
    err_msg = (f"Schedule '{sch_name}' (change_user_pos): " +
                    f"invalid user_id '{user_id}'")
    _test_failed_individual_schedule_change_user_position(
        caplog=caplog,
        err_msg=err_msg,
        sch_name=sch_name,
        user_id=user_id
    )


@given(sch_name = st.sampled_from([sch["name"] for sch in test_schedules
                                   if sch["type"] == "individual"]))
def test_failed_individual_schedule_change_user_position_unregistered_user_id(
        caplog: LogCaptureFixture, sch_name):
    """Failed change pos of a user that is not registered in the schedule"""
    # make a user viable to be added to the schedule
    user = [user for user in test_users if user["reg_req"]][0]
    with dbSession() as db_session:
        db_session.get(User, user["id"]).reg_req = False
        db_session.commit()
    err_msg = (f"Schedule '{sch_name}' (change_user_pos): " +
                    f"user with id '{user['id']}' is not in the schedule")
    _test_failed_individual_schedule_change_user_position(
        caplog=caplog,
        err_msg=err_msg,
        sch_name=sch_name,
        user_id=user["id"]
    )
    with dbSession() as db_session:
        db_session.get(User, user["id"]).reg_req = True
        db_session.commit()


@given(sch_name = st.sampled_from([sch["name"] for sch in test_schedules
                                   if sch["type"] == "individual"]),
       new_pos = st.one_of(
           st.integers(min_value=-100,
                       max_value=Constant.SQLite.Int.max_value)
            .filter(lambda x : x not in range(len(
                [user["id"] for user in test_users if user["active"]]))),
           st.none(),
           st.text()))
def test_failed_individual_schedule_change_user_position_new_pos(
        caplog: LogCaptureFixture, sch_name, new_pos):
    """test_failed_individual_schedule_change_user_position_new_pos"""
    err_msg = (f"Schedule '{sch_name}' (change_user_pos): " +
                    f"invalid new position '{new_pos}'")
    _test_failed_individual_schedule_change_user_position(
        caplog=caplog,
        err_msg=err_msg,
        sch_name=sch_name,
        new_pos=new_pos
    )


@given(sch_name = st.sampled_from([sch["name"] for sch in test_schedules
                                   if sch["type"] == "individual"]))
def test_failed_individual_schedule_change_user_position_alr_at_pos(
        caplog: LogCaptureFixture, sch_name):
    """User already at position"""
    user_ids = [user["id"] for user in test_users if user["active"]]
    for pos, user_id in enumerate(user_ids):
        err_msg = (f"Schedule '{sch_name}' (change_user_pos): " +
                    f"user with id '{user_id}' is already at position {pos}")
        _test_failed_individual_schedule_change_user_position(
            caplog=caplog,
            err_msg=err_msg,
            sch_name=sch_name,
            user_id=user_id,
            new_pos=pos
        )
# endregion
# endregion


# region: schedule page
edit_user_link = re.compile(r'<a.*href="/user/edit/.*</a>')


def test_schedule_page_user_logged_in(
        client: FlaskClient, user_logged_in: User):
    """test_schedule_page_user_logged_in"""
    with client:
        client.get("/")
        assert session["user_name"] == user_logged_in.name
        assert not session["admin"]
        response = client.get(url_for("sch.schedules"))
        assert response.status_code == 200
        for schedule in test_schedules:
            assert schedule["name"] in response.text
        assert "Group 1" in response.text
        assert "Group 2" in response.text
        assert re.search(fr'<span.*fw-bolder.*{user_logged_in.name}</span>',
                         response.text)
        assert not edit_user_link.search(response.text)
        for user in test_users:
            if user["active"]:
                assert user["name"] in response.text
            else:
                assert user["name"] not in response.text
        # group schedule dates
        assert f"<b>{saturday_sch.start_date.strftime('%d.%m.%Y')}</b>" \
            in response.text
        for week in range(1, 6):
            assert (saturday_sch.start_date + timedelta(weeks=week)
                    ).strftime("%d.%m.%Y") in response.text
        # individual schedule dates
        # pylint: disable=protected-access
        first_date = cleaning_sch._determine_first_date()
        with dbSession() as db_session:
            this_user_date = db_session.scalar(
                select(Schedule.next_date)
                .filter_by(
                    name=cleaning_sch.name,
                    elem_id=user_logged_in.id))
        assert f"<b>{this_user_date.strftime('%d.%m.%Y')}</b>" \
            in response.text
        for week in range(len([user for user in test_users if user["active"]])):
            assert (first_date + timedelta(weeks=week)).strftime("%d.%m.%Y") \
                in response.text


def test_schedule_page_admin_logged_in(
        client: FlaskClient, admin_logged_in: User):
    """test_schedule_page_admin_logged_in"""
    with client:
        client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        response = client.get(url_for("sch.schedules"))
        assert response.status_code == 200
        for schedule in test_schedules:
            assert schedule["name"] in response.text
        assert "Group 1" in response.text
        assert "Group 2" in response.text
        assert re.search(fr'<span.*fw-bolder.*{admin_logged_in.name}</a>',
                         response.text, re.S)
        assert edit_user_link.search(response.text)
        for user in test_users:
            if user["active"]:
                assert user["name"] in response.text
            else:
                assert user["name"] not in response.text
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
        first_date = cleaning_sch._determine_first_date()
        assert f"<b>{first_date.strftime('%d.%m.%Y')}</b>" \
            in response.text


@given(user = st.sampled_from([user for user in test_users if user["reg_req"]]))
def test_schedule_page_group_schedule_add_and_remove_user(
        client: FlaskClient, admin_logged_in: User, user: dict[str]):
    """test_schedule_page_group_schedule_add_and_remove_user"""
    with client:
        # initial check
        client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        user_edit_link = re.compile(
            fr'<a.*href="{url_for("users.edit_user", username=user["name"])}"' +
            fr'>{user["name"]}</a>')
        response = client.get(url_for("sch.schedules"))
        assert response.status_code == 200
        assert not user_edit_link.search(response.text)
        # add a user to the group schedule
        with dbSession() as db_session:
            db_session.get(User, user["id"]).reg_req = False
            db_session.commit()
        # check the user in schedules page
        response = client.get(url_for("sch.schedules"))
        assert response.status_code == 200
        assert user_edit_link.search(response.text)
        # remove the user from the group schedule
        with dbSession() as db_session:
            db_session.get(User, user["id"]).reg_req = True
            db_session.commit()
        # check the user in schedules page
        response = client.get(url_for("sch.schedules"))
        assert response.status_code == 200
        assert not user_edit_link.search(response.text)


@given(user = st.sampled_from([user for user in test_users if user["reg_req"]]))
def test_schedule_page_individual_schedule_add_and_remove_user(
        client: FlaskClient, caplog: LogCaptureFixture,
        admin_logged_in: User, user: dict[str]):
    """test_schedule_page_individual_schedule_add_and_remove_user"""
    with client:
        # initial check
        client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        user_edit_link = re.compile(
            fr'<a.*href="{url_for("users.edit_user", username=user["name"])}"' +
            fr'>{user["name"]}</a>')
        response = client.get(url_for("sch.schedules"))
        assert response.status_code == 200
        assert not user_edit_link.search(response.text)
        # make user eligible to be added to the individual schedule
        with dbSession() as db_session:
            db_session.get(User, user["id"]).reg_req = False
            db_session.commit()
        # automatically gets added to the group schedule
        response = client.get(url_for("sch.schedules"))
        assert response.status_code == 200
        assert len(user_edit_link.findall(response.text)) == 1
        # add user to the individual schedule
        cleaning_sch.add_user(user["id"])
        assert f"Schedule '{cleaning_sch.name}' added '{user['name']}'" \
            in caplog.messages
        # check the user in schedules page
        response = client.get(url_for("sch.schedules"))
        assert response.status_code == 200
        assert len(user_edit_link.findall(response.text)) == 2
        # remove the user from the group schedule
        with dbSession() as db_session:
            db_session.get(User, user["id"]).reg_req = True
            db_session.commit()
        # check the user in schedules page
        response = client.get(url_for("sch.schedules"))
        assert response.status_code == 200
        assert len(user_edit_link.findall(response.text)) == 1
        # remove the user from the individual schedule
        cleaning_sch.remove_user(user["id"])
        assert (f"Schedule '{cleaning_sch.name}' removed user "
                f"with id '{user['id']}'") in caplog.messages
# endregion
