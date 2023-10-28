"""Daily task tests."""

from datetime import date, timedelta
from os import path, remove, rename
from shutil import copyfile

import pytest
from freezegun import freeze_time
from pytest import LogCaptureFixture
from sqlalchemy import select

from blueprints.sch import clean_sch_info, sat_sch_info
from blueprints.sch.sch import IndivSchedule
from daily_task import db_backup, db_reinit, main, update_schedules
from database import Schedule, User, dbSession
from tests.conftest import (BACKUP_DB, ORIG_DB, PROD_DB, TASK, TEMP_DB,
                            TEST_DB_NAME)

pytestmark = pytest.mark.daily


# region: main
def test_main(caplog: LogCaptureFixture):
    """test_main"""
    assert path.isfile(PROD_DB)
    assert not path.isfile(BACKUP_DB)
    assert not path.isfile(ORIG_DB)
    main(TEST_DB_NAME)
    assert path.isfile(PROD_DB)
    assert path.isfile(BACKUP_DB)
    assert not path.isfile(ORIG_DB)
    assert "Starting first-time backup" in caplog.messages
    assert "Database backed up" in caplog.messages
    assert "Production database vacuumed" in caplog.messages
    assert "This app doesn't need database reinit" in caplog.messages
    assert "No need to update schedules" in caplog.messages
    # teardown
    remove(BACKUP_DB)


@freeze_time("2023-04-02")
def test_main_timeline(caplog: LogCaptureFixture):
    """Test db_backup in time."""
    assert path.isfile(PROD_DB)
    backup_file = BACKUP_DB.rsplit("_", 1)[0]
    backup_db_daily = backup_file + "_daily.db"
    backup_db_weekly = backup_file + "_weekly.db"
    backup_db_monthly = backup_file + "_monthly.db"

    assert not path.isfile(backup_db_daily)
    assert not path.isfile(backup_db_weekly)
    assert not path.isfile(backup_db_monthly)
    assert date.today() == date(2023, 4, 2)
    assert date.today().isoweekday() == 7

    main(TEST_DB_NAME)
    assert path.isfile(backup_db_daily)
    assert not path.isfile(backup_db_weekly)
    assert not path.isfile(backup_db_monthly)
    assert "Starting first-time backup" in caplog.messages
    assert "Database backed up" in caplog.messages
    assert "Weekly backup" not in caplog.messages
    assert "Monthly backup" not in caplog.messages
    caplog.clear()

    with freeze_time("2023-04-03"):
        assert date.today().isoweekday() == 1
        record_daily_time = path.getmtime(backup_db_daily)
        main(TEST_DB_NAME)
        assert path.getmtime(backup_db_daily) == record_daily_time
        assert path.isfile(backup_db_weekly)
        assert not path.isfile(backup_db_monthly)
        assert "Starting first-time backup" in caplog.messages
        assert "Database backed up" in caplog.messages
        assert "Weekly backup" in caplog.messages
        assert "Monthly backup" not in caplog.messages
        caplog.clear()

    with freeze_time("2023-04-09"):
        assert date.today().isoweekday() == 7
        record_daily_time = path.getmtime(backup_db_daily)
        record_weekly_time = path.getmtime(backup_db_weekly)
        main(TEST_DB_NAME)
        assert path.getmtime(backup_db_daily) > record_daily_time
        assert path.getmtime(backup_db_weekly) == record_weekly_time
        assert not path.isfile(backup_db_monthly)
        assert "Starting first-time backup" not in caplog.messages
        assert "Database backed up" in caplog.messages
        assert "Weekly backup" not in caplog.messages
        assert "Monthly backup" not in caplog.messages
        caplog.clear()

    with freeze_time("2023-04-10"):
        assert date.today().isoweekday() == 1
        record_daily_time = path.getmtime(backup_db_daily)
        record_weekly_time = path.getmtime(backup_db_weekly)
        main(TEST_DB_NAME)
        assert path.getmtime(backup_db_daily) == record_daily_time
        assert path.getmtime(backup_db_weekly) > record_weekly_time
        assert not path.isfile(backup_db_monthly)
        assert "Starting first-time backup" not in caplog.messages
        assert "Database backed up" in caplog.messages
        assert "Weekly backup" in caplog.messages
        assert "Monthly backup" not in caplog.messages
        caplog.clear()

    with freeze_time("2023-05-01"):
        assert date.today().isoweekday() == 1
        record_daily_time = path.getmtime(backup_db_daily)
        record_weekly_time = path.getmtime(backup_db_weekly)
        main(TEST_DB_NAME)
        assert path.getmtime(backup_db_daily) == record_daily_time
        assert path.getmtime(backup_db_weekly) == record_weekly_time
        assert path.isfile(backup_db_monthly)
        assert "Starting first-time backup" in caplog.messages
        assert "Database backed up" in caplog.messages
        assert "Weekly backup" not in caplog.messages
        assert "Monthly backup" in caplog.messages
        caplog.clear()

    with freeze_time("2023-05-07"):
        assert date.today().isoweekday() == 7
        record_daily_time = path.getmtime(backup_db_daily)
        record_weekly_time = path.getmtime(backup_db_weekly)
        record_monthly_time = path.getmtime(backup_db_monthly)
        main(TEST_DB_NAME)
        assert path.getmtime(backup_db_daily) > record_daily_time
        assert path.getmtime(backup_db_weekly) == record_weekly_time
        assert path.getmtime(backup_db_monthly) == record_monthly_time
        assert "Starting first-time backup" not in caplog.messages
        assert "Database backed up" in caplog.messages
        assert "Weekly backup" not in caplog.messages
        assert "Monthly backup" not in caplog.messages
        caplog.clear()

    with freeze_time("2023-06-01"):
        assert date.today().isoweekday() == 4
        record_daily_time = path.getmtime(backup_db_daily)
        record_weekly_time = path.getmtime(backup_db_weekly)
        record_monthly_time = path.getmtime(backup_db_monthly)
        main(TEST_DB_NAME)
        assert path.getmtime(backup_db_daily) == record_daily_time
        assert path.getmtime(backup_db_weekly) == record_weekly_time
        assert path.getmtime(backup_db_monthly) > record_monthly_time
        assert "Starting first-time backup" not in caplog.messages
        assert "Database backed up" in caplog.messages
        assert "Weekly backup" not in caplog.messages
        assert "Monthly backup" in caplog.messages
        caplog.clear()

    # teardown
    remove(backup_db_daily)
    remove(backup_db_weekly)
    remove(backup_db_monthly)
# endregion


# region: backup/reinit
# region: backup and vacuum
def test_db_backup_update_file(caplog: LogCaptureFixture):
    """test_db_backup_update_file"""
    assert not path.isfile(BACKUP_DB)
    db_backup(TEST_DB_NAME, TASK)
    assert path.isfile(BACKUP_DB)
    assert "Starting first-time backup" in caplog.messages
    assert "Database backed up" in caplog.messages
    caplog.clear()
    first_backup_time = path.getmtime(BACKUP_DB)
    db_backup(TEST_DB_NAME, TASK)
    assert "Starting first-time backup" not in caplog.messages
    assert "Database backed up" in caplog.messages
    assert path.getmtime(BACKUP_DB) > first_backup_time
    # teardown
    remove(BACKUP_DB)


def test_db_backup_not_needed(caplog: LogCaptureFixture):
    """test_db_backup_not_needed"""
    copyfile(PROD_DB, ORIG_DB)
    db_backup(TEST_DB_NAME)
    assert "No need to backup database as it will be reinitialised" \
        in caplog.messages
    remove(ORIG_DB)


def test_failed_db_backup(caplog: LogCaptureFixture):
    """test_failed_db_backup"""
    rename(PROD_DB, TEMP_DB)
    db_backup(TEST_DB_NAME)
    assert "Database could not be backed up" in caplog.messages
    assert "Database could not be vacuumed" in caplog.messages
    # teardown
    rename(TEMP_DB, PROD_DB)


def test_db_backup_task(caplog: LogCaptureFixture):
    """Test database backup task argument."""
    assert not path.isfile(BACKUP_DB)
    backup_file = BACKUP_DB.rsplit("_", 1)[0]
    backup_db_daily = backup_file + "_daily.db"
    backup_db_weekly = backup_file + "_weekly.db"
    backup_db_monthly = backup_file + "_monthly.db"

    db_backup(TEST_DB_NAME, "daily")
    assert path.isfile(backup_db_daily)
    assert not path.isfile(backup_db_weekly)
    assert not path.isfile(backup_db_monthly)
    assert "Starting first-time backup" in caplog.messages
    assert "Database backed up" in caplog.messages
    assert "Weekly backup" not in caplog.messages
    assert "Monthly backup" not in caplog.messages
    # teardown
    caplog.clear()
    remove(backup_db_daily)

    db_backup(TEST_DB_NAME, "weekly")
    assert not path.isfile(backup_db_daily)
    assert path.isfile(backup_db_weekly)
    assert not path.isfile(backup_db_monthly)
    assert "Starting first-time backup" in caplog.messages
    assert "Database backed up" in caplog.messages
    assert "Weekly backup" in caplog.messages
    assert "Monthly backup" not in caplog.messages
    # teardown
    caplog.clear()
    remove(backup_db_weekly)

    db_backup(TEST_DB_NAME, "monthly")
    assert not path.isfile(backup_db_daily)
    assert not path.isfile(backup_db_weekly)
    assert path.isfile(backup_db_monthly)
    assert "Starting first-time backup" in caplog.messages
    assert "Database backed up" in caplog.messages
    assert "Weekly backup" not in caplog.messages
    assert "Monthly backup" in caplog.messages
    # teardown
    caplog.clear()
    remove(backup_db_monthly)


@pytest.mark.parametrize("task", (
    "",
    " ",
    None,
    2,
    "some random text",
    True,
))
def test_db_backup_task_daily_fallback(task, caplog: LogCaptureFixture):
    """Test database backup task argument fallback to `daily`."""
    backup_file = BACKUP_DB.rsplit("_", 1)[0]
    backup_db_daily = backup_file + "_daily.db"
    assert not path.isfile(backup_db_daily)
    db_backup(TEST_DB_NAME, task)
    assert "Starting first-time backup" in caplog.messages
    assert "Database backed up" in caplog.messages
    assert "Weekly backup" not in caplog.messages
    assert "Monthly backup" not in caplog.messages
    assert f"Backup task argument '{task}' invalid" in caplog.messages
    assert path.isfile(backup_db_daily)
    # teardown
    caplog.clear()
    remove(backup_db_daily)
# endregion


# region: reinit
def test_db_reinit(caplog: LogCaptureFixture):
    """test_db_reinit"""
    user_id = 7
    sch_id = 1
    copyfile(PROD_DB, ORIG_DB)
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
    # test DON'T remember schedules dates
    with freeze_time(date.today() + timedelta(days=1)):
        update_schedules(TEST_DB_NAME, date.today())
    assert f"Schedule '{sat_sch_info.name_en}' group '1' will be updated"\
        in caplog.messages
    assert f"Schedule '{clean_sch_info.name_en}' user 'user1' will be updated"\
        in caplog.messages
    assert "2 schedules updated" in caplog.messages
    assert "No need to update schedules" not in caplog.messages
    caplog.clear()
    with dbSession() as db_session:
        assert db_session.get(Schedule, sch_id).next_date \
            == date.today() + timedelta(weeks=2)
    db_reinit(TEST_DB_NAME)
    assert "Database reinitialised" in caplog.messages
    with freeze_time(date.today() + timedelta(days=1)):
        update_schedules(TEST_DB_NAME, date.today())
    assert f"Schedule '{sat_sch_info.name_en}' group '1' will be updated"\
        in caplog.messages
    assert f"Schedule '{clean_sch_info.name_en}' user 'user1' will be updated"\
        in caplog.messages
    assert "2 schedules updated" in caplog.messages
    assert "No need to update schedules" not in caplog.messages
    with dbSession() as db_session:
        assert db_session.get(Schedule, sch_id).next_date \
            == date.today() + timedelta(weeks=2)
    # teardown
    copyfile(ORIG_DB, PROD_DB)
    remove(ORIG_DB)


def test_failed_db_reinit(caplog: LogCaptureFixture):
    """test_failed_db_reinit"""
    copyfile(PROD_DB, ORIG_DB)
    rename(PROD_DB, TEMP_DB)
    db_reinit(TEST_DB_NAME)
    assert "Database could not be reinitialised" in caplog.messages
    # teardown
    rename(TEMP_DB, PROD_DB)
    remove(ORIG_DB)
# endregion
# endregion


# region: schedules
@freeze_time("2023-05-06")
def test_update_group_schedules_1(caplog: LogCaptureFixture):
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
            update_interval=14),
        Schedule(
            name=name,
            type="group",
            elem_id=2,
            next_date=date.today() + timedelta(days=14),
            update_date=date.today() + timedelta(days=16),
            update_interval=14),
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
        assert f"Schedule '{name}' group '1' will be updated" \
            not in caplog.messages
        assert f"Schedule '{name}' group '2' will be updated" \
            not in caplog.messages
        assert "updated" not in caplog.messages
        caplog.clear()
    with freeze_time(date.today() + timedelta(days=2)):
        update_schedules(TEST_DB_NAME, date.today())
        assert "No need to update schedules" not in caplog.messages
        assert f"Schedule '{name}' group '1' will be updated" \
            in caplog.messages
        assert f"Schedule '{name}' group '2' will be updated" \
            not in caplog.messages
        assert "1 schedule updated" in caplog.messages
        caplog.clear()
    with freeze_time(date.today() + timedelta(days=15)):
        update_schedules(TEST_DB_NAME, date.today())
        assert "No need to update schedules" in caplog.messages
        assert f"Schedule '{name}' group '1' will be updated" \
            not in caplog.messages
        assert f"Schedule '{name}' group '2' will be updated" \
            not in caplog.messages
        assert "updated" not in caplog.messages
        caplog.clear()
    with freeze_time(date.today() + timedelta(days=16)):
        update_schedules(TEST_DB_NAME, date.today())
        assert "No need to update schedules" not in caplog.messages
        assert f"Schedule '{name}' group '1' will be updated" \
            not in caplog.messages
        assert f"Schedule '{name}' group '2' will be updated" \
            in caplog.messages
        assert "1 schedule updated" in caplog.messages
        caplog.clear()
    with freeze_time(date(2023, 10, 9)):
        update_schedules(TEST_DB_NAME, date.today())
        assert "No need to update schedules" not in caplog.messages
        assert f"Schedule '{name}' group '1' will be updated" \
            in caplog.messages
        assert f"Schedule '{name}' group '2' will be updated" \
            in caplog.messages
        assert "2 schedules updated" in caplog.messages
        caplog.clear()
    with dbSession() as db_session:
        schedules: list[Schedule] = db_session.scalars(
            select(Schedule)
            .filter_by(name=name)).all()
        assert schedules[0].elem_id == 1
        assert schedules[0].next_date == date(2023, 10, 21)
        assert schedules[0].update_date == date(2023, 10, 23)
        assert schedules[0].update_interval == 14
        assert schedules[1].elem_id == 2
        assert schedules[1].next_date == date(2023, 11, 4)
        assert schedules[1].update_date == date(2023, 11, 6)
        assert schedules[1].update_interval == 14
        # teardown
        for schedule in schedules:
            db_session.delete(schedule)
        db_session.commit()


@freeze_time("2023-09-01")
def test_update_group_schedules_2(caplog: LogCaptureFixture):
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
            update_interval=7),
        Schedule(
            name=name,
            type="group",
            elem_id=2,
            next_date=date(2023, 9, 10),
            update_date=date(2023, 9, 11),
            update_interval=7),
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
        assert f"Schedule '{name}' group '1' will be updated" \
            not in caplog.messages
        assert f"Schedule '{name}' group '2' will be updated" \
            not in caplog.messages
        assert "updated" not in caplog.messages
        caplog.clear()
    with freeze_time(date.today() + timedelta(days=3)):
        update_schedules(TEST_DB_NAME, date.today())
        assert date.today().isoweekday() == 1
        assert "No need to update schedules" not in caplog.messages
        assert f"Schedule '{name}' group '1' will be updated" \
            in caplog.messages
        assert f"Schedule '{name}' group '2' will be updated" \
            not in caplog.messages
        assert "1 schedule updated" in caplog.messages
        caplog.clear()
    with freeze_time(date.today() + timedelta(days=9)):
        update_schedules(TEST_DB_NAME, date.today())
        assert date.today().isoweekday() == 7
        assert "No need to update schedules" in caplog.messages
        assert f"Schedule '{name}' group '1' will be updated" \
            not in caplog.messages
        assert f"Schedule '{name}' group '2' will be updated" \
            not in caplog.messages
        assert "updated" not in caplog.messages
        caplog.clear()
    with freeze_time(date.today() + timedelta(days=10)):
        update_schedules(TEST_DB_NAME, date.today())
        assert date.today().isoweekday() == 1
        assert "No need to update schedules" not in caplog.messages
        assert f"Schedule '{name}' group '1' will be updated" \
            not in caplog.messages
        assert f"Schedule '{name}' group '2' will be updated" \
            in caplog.messages
        assert "1 schedule updated" in caplog.messages
        caplog.clear()
    with freeze_time(date(2023, 10, 6)):
        update_schedules(TEST_DB_NAME, date.today())
        assert date.today().isoweekday() == 5
        assert "No need to update schedules" not in caplog.messages
        assert f"Schedule '{name}' group '1' will be updated" \
            in caplog.messages
        assert f"Schedule '{name}' group '2' will be updated" \
            in caplog.messages
        assert "2 schedules updated" in caplog.messages
        caplog.clear()
    with dbSession() as db_session:
        schedules: list[Schedule] = db_session.scalars(
            select(Schedule)
            .filter_by(name=name)).all()
        assert schedules[0].elem_id == 1
        assert schedules[0].next_date == date(2023, 10, 15)
        assert schedules[0].update_date == date(2023, 10, 16)
        assert schedules[0].update_interval == 7
        assert schedules[1].elem_id == 2
        assert schedules[1].next_date == date(2023, 10, 8)
        assert schedules[1].update_date == date(2023, 10, 9)
        assert schedules[1].update_interval == 7
        # teardown
        for schedule in schedules:
            db_session.delete(schedule)
        db_session.commit()


@freeze_time("2023-08-04")
def test_update_indiv_schedule_1(caplog: LogCaptureFixture):
    """Explicit date checking 1 week interval"""
    name = "test_schedule"
    assert date.today() == date(2023, 8, 4)
    assert date.today().isoweekday() == 5
    test_sch = IndivSchedule(
        name=name,
        sch_day=1,
        sch_day_update=1,
        switch_interval=timedelta(weeks=1),
        start_date=date.today())
    test_sch.register(start_date=date(2023, 7, 31))
    assert test_sch.current_order() == [1, 2, 3, 4, 7]

    update_schedules(TEST_DB_NAME, date.today())
    assert "No need to update schedules" in caplog.messages
    caplog.clear()
    assert test_sch.current_order() == [1, 2, 3, 4, 7]

    with freeze_time(date.today() + timedelta(days=2)):
        update_schedules(TEST_DB_NAME, date.today())
        assert date.today().isoweekday() == 7
        assert "No need to update schedules" in caplog.messages
        assert f"Schedule '{name}' user 'user1' will be updated" \
            not in caplog.messages
        assert f"Schedule '{name}' user 'user2' will be updated" \
            not in caplog.messages
        assert f"Schedule '{name}' user 'user3' will be updated" \
            not in caplog.messages
        assert f"Schedule '{name}' user 'user4' will be updated" \
            not in caplog.messages
        assert f"Schedule '{name}' user 'user7' will be updated" \
            not in caplog.messages
        assert "updated" not in caplog.messages
        caplog.clear()
        assert test_sch.current_order() == [1, 2, 3, 4, 7]

    with freeze_time(date.today() + timedelta(days=3)):
        update_schedules(TEST_DB_NAME, date.today())
        assert date.today().isoweekday() == 1
        assert "No need to update schedules" not in caplog.messages
        assert f"Schedule '{name}' user 'user1' will be updated" \
            in caplog.messages
        assert f"Schedule '{name}' user 'user2' will be updated" \
            not in caplog.messages
        assert f"Schedule '{name}' user 'user3' will be updated" \
            not in caplog.messages
        assert f"Schedule '{name}' user 'user4' will be updated" \
            not in caplog.messages
        assert f"Schedule '{name}' user 'user7' will be updated" \
            not in caplog.messages
        assert "1 schedule updated" in caplog.messages
        caplog.clear()
        assert test_sch.current_order() == [2, 3, 4, 7, 1]

    with freeze_time(date.today() + timedelta(weeks=1, days=2)):
        update_schedules(TEST_DB_NAME, date.today())
        assert date.today().isoweekday() == 7
        assert "No need to update schedules" in caplog.messages
        assert f"Schedule '{name}' user 'user1' will be updated" \
            not in caplog.messages
        assert f"Schedule '{name}' user 'user2' will be updated" \
            not in caplog.messages
        assert f"Schedule '{name}' user 'user3' will be updated" \
            not in caplog.messages
        assert f"Schedule '{name}' user 'user4' will be updated" \
            not in caplog.messages
        assert f"Schedule '{name}' user 'user7' will be updated" \
            not in caplog.messages
        assert "updated" not in caplog.messages
        caplog.clear()
        assert test_sch.current_order() == [2, 3, 4, 7, 1]

    with freeze_time(date.today() + timedelta(weeks=1, days=3)):
        update_schedules(TEST_DB_NAME, date.today())
        assert date.today().isoweekday() == 1
        assert "No need to update schedules" not in caplog.messages
        assert f"Schedule '{name}' user 'user1' will be updated" \
            not in caplog.messages
        assert f"Schedule '{name}' user 'user2' will be updated" \
            in caplog.messages
        assert f"Schedule '{name}' user 'user3' will be updated" \
            not in caplog.messages
        assert f"Schedule '{name}' user 'user4' will be updated" \
            not in caplog.messages
        assert f"Schedule '{name}' user 'user7' will be updated" \
            not in caplog.messages
        assert "1 schedule updated" in caplog.messages
        caplog.clear()
        assert test_sch.current_order() == [3, 4, 7, 1, 2]

    with freeze_time(date.today() + timedelta(weeks=2, days=3)):
        update_schedules(TEST_DB_NAME, date.today())
        assert date.today().isoweekday() == 1
        assert "No need to update schedules" not in caplog.messages
        assert f"Schedule '{name}' user 'user1' will be updated" \
            not in caplog.messages
        assert f"Schedule '{name}' user 'user2' will be updated" \
            not in caplog.messages
        assert f"Schedule '{name}' user 'user3' will be updated" \
            in caplog.messages
        assert f"Schedule '{name}' user 'user4' will be updated" \
            not in caplog.messages
        assert f"Schedule '{name}' user 'user7' will be updated" \
            not in caplog.messages
        assert "1 schedule updated" in caplog.messages
        caplog.clear()
        assert test_sch.current_order() == [4, 7, 1, 2, 3]

    with freeze_time(date.today() + timedelta(weeks=4, days=3)):
        update_schedules(TEST_DB_NAME, date.today())
        assert date.today().isoweekday() == 1
        assert "No need to update schedules" not in caplog.messages
        assert f"Schedule '{name}' user 'user1' will be updated" \
            not in caplog.messages
        assert f"Schedule '{name}' user 'user2' will be updated" \
            not in caplog.messages
        assert f"Schedule '{name}' user 'user3' will be updated" \
            not in caplog.messages
        assert f"Schedule '{name}' user 'user4' will be updated" \
            in caplog.messages
        assert f"Schedule '{name}' user 'user7' will be updated" \
            in caplog.messages
        assert "2 schedules updated" in caplog.messages
        caplog.clear()
        assert test_sch.current_order() == [1, 2, 3, 4, 7]

    with freeze_time(date.today() + timedelta(weeks=8, days=3)):
        update_schedules(TEST_DB_NAME, date.today())
        assert date.today().isoweekday() == 1
        assert "No need to update schedules" not in caplog.messages
        assert f"Schedule '{name}' user 'user1' will be updated" \
            in caplog.messages
        assert f"Schedule '{name}' user 'user2' will be updated" \
            in caplog.messages
        assert f"Schedule '{name}' user 'user3' will be updated" \
            in caplog.messages
        assert f"Schedule '{name}' user 'user4' will be updated" \
            in caplog.messages
        assert f"Schedule '{name}' user 'user7' will be updated" \
            not in caplog.messages
        assert "4 schedules updated" in caplog.messages
        caplog.clear()
        assert test_sch.current_order() == [7, 1, 2, 3, 4]

    # teardown
    with dbSession() as db_session:
        schedules: list[Schedule] = db_session.scalars(
            select(Schedule)
            .filter_by(name=name)).all()
        for schedule in schedules:
            db_session.delete(schedule)
        db_session.commit()


@freeze_time("2023-08-04")
def test_update_indiv_schedule_2(caplog: LogCaptureFixture):
    """Explicit date checking 2 week interval"""
    name = "test_schedule"
    assert date.today() == date(2023, 8, 4)
    assert date.today().isoweekday() == 5
    test_sch = IndivSchedule(
        name=name,
        sch_day=5,
        sch_day_update=1,
        switch_interval=timedelta(weeks=2),
        start_date=date.today())
    test_sch.register()
    assert test_sch.current_order() == [1, 2, 3, 4, 7]

    update_schedules(TEST_DB_NAME, date.today())
    assert "No need to update schedules" in caplog.messages
    caplog.clear()
    assert test_sch.current_order() == [1, 2, 3, 4, 7]

    with freeze_time(date.today() + timedelta(weeks=0, days=2)):
        update_schedules(TEST_DB_NAME, date.today())
        assert date.today().isoweekday() == 7
        assert "No need to update schedules" in caplog.messages
        assert f"Schedule '{name}' user 'user1' will be updated" \
            not in caplog.messages
        assert f"Schedule '{name}' user 'user2' will be updated" \
            not in caplog.messages
        assert f"Schedule '{name}' user 'user3' will be updated" \
            not in caplog.messages
        assert f"Schedule '{name}' user 'user4' will be updated" \
            not in caplog.messages
        assert f"Schedule '{name}' user 'user7' will be updated" \
            not in caplog.messages
        assert "updated" not in caplog.messages
        caplog.clear()
        assert test_sch.current_order() == [1, 2, 3, 4, 7]

    with freeze_time(date.today() + timedelta(weeks=0, days=3)):
        update_schedules(TEST_DB_NAME, date.today())
        assert date.today().isoweekday() == 1
        assert "No need to update schedules" not in caplog.messages
        assert f"Schedule '{name}' user 'user1' will be updated" \
            in caplog.messages
        assert f"Schedule '{name}' user 'user2' will be updated" \
            not in caplog.messages
        assert f"Schedule '{name}' user 'user3' will be updated" \
            not in caplog.messages
        assert f"Schedule '{name}' user 'user4' will be updated" \
            not in caplog.messages
        assert f"Schedule '{name}' user 'user7' will be updated" \
            not in caplog.messages
        assert "1 schedule updated" in caplog.messages
        caplog.clear()
        assert test_sch.current_order() == [2, 3, 4, 7, 1]

    with freeze_time(date.today() + timedelta(weeks=1, days=3)):
        update_schedules(TEST_DB_NAME, date.today())
        assert date.today().isoweekday() == 1
        assert "No need to update schedules" in caplog.messages
        assert f"Schedule '{name}' user 'user1' will be updated" \
            not in caplog.messages
        assert f"Schedule '{name}' user 'user2' will be updated" \
            not in caplog.messages
        assert f"Schedule '{name}' user 'user3' will be updated" \
            not in caplog.messages
        assert f"Schedule '{name}' user 'user4' will be updated" \
            not in caplog.messages
        assert f"Schedule '{name}' user 'user7' will be updated" \
            not in caplog.messages
        assert "updated" not in caplog.messages
        caplog.clear()
        assert test_sch.current_order() == [2, 3, 4, 7, 1]

    with freeze_time(date.today() + timedelta(weeks=2, days=3)):
        update_schedules(TEST_DB_NAME, date.today())
        assert date.today().isoweekday() == 1
        assert "No need to update schedules" not in caplog.messages
        assert f"Schedule '{name}' user 'user1' will be updated" \
            not in caplog.messages
        assert f"Schedule '{name}' user 'user2' will be updated" \
            in caplog.messages
        assert f"Schedule '{name}' user 'user3' will be updated" \
            not in caplog.messages
        assert f"Schedule '{name}' user 'user4' will be updated" \
            not in caplog.messages
        assert f"Schedule '{name}' user 'user7' will be updated" \
            not in caplog.messages
        assert "1 schedule updated" in caplog.messages
        caplog.clear()
        assert test_sch.current_order() == [3, 4, 7, 1, 2]

    with freeze_time(date.today() + timedelta(weeks=3, days=3)):
        update_schedules(TEST_DB_NAME, date.today())
        assert date.today().isoweekday() == 1
        assert "No need to update schedules" in caplog.messages
        assert f"Schedule '{name}' user 'user1' will be updated" \
            not in caplog.messages
        assert f"Schedule '{name}' user 'user2' will be updated" \
            not in caplog.messages
        assert f"Schedule '{name}' user 'user3' will be updated" \
            not in caplog.messages
        assert f"Schedule '{name}' user 'user4' will be updated" \
            not in caplog.messages
        assert f"Schedule '{name}' user 'user7' will be updated" \
            not in caplog.messages
        assert "updated" not in caplog.messages
        caplog.clear()
        assert test_sch.current_order() == [3, 4, 7, 1, 2]

    with freeze_time(date.today() + timedelta(weeks=6, days=3)):
        update_schedules(TEST_DB_NAME, date.today())
        assert date.today().isoweekday() == 1
        assert "No need to update schedules" not in caplog.messages
        assert f"Schedule '{name}' user 'user1' will be updated" \
            not in caplog.messages
        assert f"Schedule '{name}' user 'user2' will be updated" \
            not in caplog.messages
        assert f"Schedule '{name}' user 'user3' will be updated" \
            in caplog.messages
        assert f"Schedule '{name}' user 'user4' will be updated" \
            in caplog.messages
        assert f"Schedule '{name}' user 'user7' will be updated" \
            not in caplog.messages
        assert "2 schedules updated" in caplog.messages
        caplog.clear()
        assert test_sch.current_order() == [7, 1, 2, 3, 4]

    # teardown
    with dbSession() as db_session:
        schedules: list[Schedule] = db_session.scalars(
            select(Schedule)
            .filter_by(name=name)).all()
        for schedule in schedules:
            db_session.delete(schedule)
        db_session.commit()
# endregion
