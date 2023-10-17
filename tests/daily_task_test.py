"""Daily task tests."""

from datetime import date, timedelta
from os import path, remove, rename
from shutil import copyfile

import pytest
from freezegun import freeze_time
from pytest import LogCaptureFixture
from sqlalchemy import select

from daily_task import db_backup, db_reinit, main, update_schedules
from database import Schedule, User, dbSession
from helpers import CURR_DIR
from tests.conftest import TEST_DB_NAME

pytestmark = pytest.mark.daily

prod_db = path.join(CURR_DIR, TEST_DB_NAME)
backup_db = path.join(CURR_DIR, path.splitext(TEST_DB_NAME)[0] + "_backup.db")
orig_db = path.join(CURR_DIR, path.splitext(TEST_DB_NAME)[0] + "_orig.db")
temp_db = path.join(CURR_DIR, path.splitext(TEST_DB_NAME)[0] + "_temp.db")

def test_main(caplog: LogCaptureFixture):
    """test_main"""
    assert path.isfile(prod_db)
    assert not path.isfile(backup_db)
    assert not path.isfile(orig_db)
    main(TEST_DB_NAME)
    assert path.isfile(prod_db)
    assert path.isfile(backup_db)
    assert not path.isfile(orig_db)
    assert "Starting first-time backup" in caplog.messages
    assert "Database backed up" in caplog.messages
    assert "Production database vacuumed" in caplog.messages
    assert "This app doesn't need database reinit" in caplog.messages
    assert "No need to update schedules" in caplog.messages
    # teardown
    remove(backup_db)

# region: backup/reinit
# region: backup and vacuum
def test_db_backup_update_file(caplog: LogCaptureFixture):
    """test_db_backup_update_file"""
    assert not path.isfile(backup_db)
    db_backup(TEST_DB_NAME)
    assert path.isfile(backup_db)
    assert "Starting first-time backup" in caplog.messages
    assert "Database backed up" in caplog.messages
    caplog.clear()
    first_backup_time = path.getmtime(backup_db)
    db_backup(TEST_DB_NAME)
    assert "Starting first-time backup" not in caplog.messages
    assert "Database backed up" in caplog.messages
    assert path.getmtime(backup_db) > first_backup_time
    # teardown
    remove(backup_db)


def test_db_backup_not_needed(caplog: LogCaptureFixture):
    """test_db_backup_not_needed"""
    copyfile(prod_db, orig_db)
    db_backup(TEST_DB_NAME)
    assert "No need to backup database as it will be reinitialised" \
        in caplog.messages
    remove(orig_db)


def test_failed_db_backup(caplog: LogCaptureFixture):
    """test_failed_db_backup"""
    rename(prod_db, temp_db)
    db_backup(TEST_DB_NAME)
    assert "Database could not be backed up" in caplog.messages
    assert "Database could not be vacuumed" in caplog.messages
    # teardown
    rename(temp_db, prod_db)
# endregion


# region: reinit
def test_db_reinit(caplog: LogCaptureFixture):
    """test_db_reinit"""
    user_id = 7
    sch_id = 1
    copyfile(prod_db, orig_db)
    with dbSession() as db_session:
        user = db_session.get(User, user_id)
        assert user
        db_session.delete(user)
        db_session.commit()
        assert not db_session.get(User, user_id)
    db_reinit(TEST_DB_NAME)
    with dbSession() as db_session:
        assert db_session.get(User, user_id)
        assert db_session.get(Schedule, sch_id).next_date == date.today()
    assert "Database reinitialised" in caplog.messages
    caplog.clear()
    # test remember schedules dates
    with freeze_time(date.today() + timedelta(days=1)):
        update_schedules(TEST_DB_NAME, date.today())
    assert "Group 1 'Saturday movie' schedule will be updated" \
        in caplog.messages
    assert "1 schedule(s) updated" in caplog.messages
    assert "No need to update schedules" not in caplog.messages
    caplog.clear()
    with dbSession() as db_session:
        assert db_session.get(Schedule, sch_id).next_date \
            == date.today() + timedelta(weeks=2)
    db_reinit(TEST_DB_NAME)
    assert "Database reinitialised" in caplog.messages
    update_schedules(TEST_DB_NAME, date.today())
    assert "Group 1 'Saturday movie' schedule will be updated" \
        not in caplog.messages
    assert "1 schedule(s) updated" not in caplog.messages
    assert "No need to update schedules" in caplog.messages
    with dbSession() as db_session:
        assert db_session.get(Schedule, sch_id).next_date \
            == date.today() + timedelta(weeks=2)
    # teardown
    copyfile(orig_db, prod_db)
    remove(orig_db)


def test_failed_db_reinit(caplog: LogCaptureFixture):
    """test_failed_db_reinit"""
    copyfile(prod_db, orig_db)
    rename(prod_db, temp_db)
    db_reinit(TEST_DB_NAME)
    assert "Database could not be reinitialised" in caplog.messages
    # teardown
    rename(temp_db, prod_db)
    remove(orig_db)
# endregion
# endregion


# region: schedules
@freeze_time("2023-05-06")
def test_update_schedules_1(caplog: LogCaptureFixture):
    """Explicit date checking 2 groups 2 weeks interval"""
    name = "test_saturday_working"
    assert date.today() == date(2023, 5, 6)
    assert date.today().isoweekday() == 6
    schedules = [
        Schedule(
            name=name,
            type="group",
            elem_id=1,
            next_date=date.today(),
            update_date=date.today() + timedelta(days=2),
            update_interval=28),
        Schedule(
            name=name,
            type="group",
            elem_id=2,
            next_date=date.today() + timedelta(days=14),
            update_date=date.today() + timedelta(days=16),
            update_interval=28),
        ]
    with dbSession() as db_session:
        db_session.add_all(schedules)
        db_session.commit()
    update_schedules(TEST_DB_NAME, date.today())
    assert "No need to update schedules" in caplog.messages
    caplog.clear()
    with freeze_time(date.today() + timedelta(days=1)):
        update_schedules(TEST_DB_NAME, date.today())
        assert "No need to update schedules" in caplog.messages
        assert f"Group 1 '{name}' schedule will be updated" \
            not in caplog.messages
        assert f"Group 2 '{name}' schedule will be updated" \
            not in caplog.messages
        assert "schedule(s) updated" not in caplog.messages
        caplog.clear()
    with freeze_time(date.today() + timedelta(days=2)):
        update_schedules(TEST_DB_NAME, date.today())
        assert "No need to update schedules" not in caplog.messages
        assert f"Group 1 '{name}' schedule will be updated" \
            in caplog.messages
        assert f"Group 2 '{name}' schedule will be updated" \
            not in caplog.messages
        assert "1 schedule(s) updated" in caplog.messages
        caplog.clear()
    with freeze_time(date.today() + timedelta(days=15)):
        update_schedules(TEST_DB_NAME, date.today())
        assert "No need to update schedules" in caplog.messages
        assert f"Group 1 '{name}' schedule will be updated" \
            not in caplog.messages
        assert f"Group 2 '{name}' schedule will be updated" \
            not in caplog.messages
        assert "schedule(s) updated" not in caplog.messages
        caplog.clear()
    with freeze_time(date.today() + timedelta(days=16)):
        update_schedules(TEST_DB_NAME, date.today())
        assert "No need to update schedules" not in caplog.messages
        assert f"Group 1 '{name}' schedule will be updated" \
            not in caplog.messages
        assert f"Group 2 '{name}' schedule will be updated" \
            in caplog.messages
        assert "1 schedule(s) updated" in caplog.messages
        caplog.clear()
    with freeze_time(date(2023, 10, 9)):
        update_schedules(TEST_DB_NAME, date.today())
        assert "No need to update schedules" not in caplog.messages
        assert f"Group 1 '{name}' schedule will be updated" \
            in caplog.messages
        assert f"Group 2 '{name}' schedule will be updated" \
            in caplog.messages
        assert "2 schedule(s) updated" in caplog.messages
        caplog.clear()
    with dbSession() as db_session:
        schedules: list[Schedule] = db_session.scalars(
            select(Schedule)
            .filter_by(name=name)).all()
        assert schedules[0].elem_id == 1
        assert schedules[0].next_date == date(2023, 10, 21)
        assert schedules[0].update_date == date(2023, 10, 23)
        assert schedules[0].update_interval == 28
        assert schedules[1].elem_id == 2
        assert schedules[1].next_date == date(2023, 11, 4)
        assert schedules[1].update_date == date(2023, 11, 6)
        assert schedules[1].update_interval == 28
        # teardown
        for schedule in schedules:
            db_session.delete(schedule)
        db_session.commit()


@freeze_time("2023-09-01")
def test_update_schedules_2(caplog: LogCaptureFixture):
    """Explicit date checking 2 groups 1 weeks interval"""
    name = "test_sunday_movie"
    assert date.today() == date(2023, 9, 1)
    assert date.today().isoweekday() == 5
    schedules = [
        Schedule(
            name=name,
            type="group",
            elem_id=1,
            next_date=date(2023, 9, 3),
            update_date=date(2023, 9, 4),
            update_interval=14),
        Schedule(
            name=name,
            type="group",
            elem_id=2,
            next_date=date(2023, 9, 10),
            update_date=date(2023, 9, 11),
            update_interval=14),
        ]
    with dbSession() as db_session:
        db_session.add_all(schedules)
        db_session.commit()
    update_schedules(TEST_DB_NAME, date.today())
    assert "No need to update schedules" in caplog.messages
    caplog.clear()
    with freeze_time(date.today() + timedelta(days=2)):
        update_schedules(TEST_DB_NAME, date.today())
        assert date.today().isoweekday() == 7
        assert "No need to update schedules" in caplog.messages
        assert f"Group 1 '{name}' schedule will be updated" \
            not in caplog.messages
        assert f"Group 2 '{name}' schedule will be updated" \
            not in caplog.messages
        assert "schedule(s) updated" not in caplog.messages
        caplog.clear()
    with freeze_time(date.today() + timedelta(days=3)):
        update_schedules(TEST_DB_NAME, date.today())
        assert date.today().isoweekday() == 1
        assert "No need to update schedules" not in caplog.messages
        assert f"Group 1 '{name}' schedule will be updated" \
            in caplog.messages
        assert f"Group 2 '{name}' schedule will be updated" \
            not in caplog.messages
        assert "1 schedule(s) updated" in caplog.messages
        caplog.clear()
    with freeze_time(date.today() + timedelta(days=9)):
        update_schedules(TEST_DB_NAME, date.today())
        assert date.today().isoweekday() == 7
        assert "No need to update schedules" in caplog.messages
        assert f"Group 1 '{name}' schedule will be updated" \
            not in caplog.messages
        assert f"Group 2 '{name}' schedule will be updated" \
            not in caplog.messages
        assert "schedule(s) updated" not in caplog.messages
        caplog.clear()
    with freeze_time(date.today() + timedelta(days=10)):
        update_schedules(TEST_DB_NAME, date.today())
        assert date.today().isoweekday() == 1
        assert "No need to update schedules" not in caplog.messages
        assert f"Group 1 '{name}' schedule will be updated" \
            not in caplog.messages
        assert f"Group 2 '{name}' schedule will be updated" in caplog.messages
        assert "1 schedule(s) updated" in caplog.messages
        caplog.clear()
    with freeze_time(date(2023, 10, 6)):
        update_schedules(TEST_DB_NAME, date.today())
        assert date.today().isoweekday() == 5
        assert "No need to update schedules" not in caplog.messages
        assert f"Group 1 '{name}' schedule will be updated" in caplog.messages
        assert f"Group 2 '{name}' schedule will be updated" in caplog.messages
        assert "2 schedule(s) updated" in caplog.messages
        caplog.clear()
    with dbSession() as db_session:
        schedules: list[Schedule] = db_session.scalars(
            select(Schedule)
            .filter_by(name=name)).all()
        assert schedules[0].elem_id == 1
        assert schedules[0].next_date == date(2023, 10, 15)
        assert schedules[0].update_date == date(2023, 10, 16)
        assert schedules[0].update_interval == 14
        assert schedules[1].elem_id == 2
        assert schedules[1].next_date == date(2023, 10, 8)
        assert schedules[1].update_date == date(2023, 10, 9)
        assert schedules[1].update_interval == 14
        # teardown
        for schedule in schedules:
            db_session.delete(schedule)
        db_session.commit()
# endregion
