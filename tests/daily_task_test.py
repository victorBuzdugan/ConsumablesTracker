"""Daily task tests."""

from datetime import date, timedelta
from os import environ, getenv, path, remove, rename
from shutil import copyfile

import pytest
from freezegun import freeze_time
from pytest import LogCaptureFixture
from sqlalchemy import select

from app import mail
from blueprints.sch import clean_sch_info, sat_sch_info
from blueprints.sch.sch import IndivSchedule
from daily_task import (db_backup, db_reinit, main, send_admins_notif,
                        send_log, send_users_notif, update_schedules)
from database import Product, Schedule, User, dbSession
from helpers import logger
from tests.conftest import BACKUP_DB, ORIG_DB, PROD_DB, TEMP_DB

pytestmark = pytest.mark.daily


# region: main
def test_main(caplog: LogCaptureFixture):
    """test_main"""
    assert path.isfile(PROD_DB)
    assert not path.isfile(BACKUP_DB)
    assert not path.isfile(ORIG_DB)
    main()
    assert path.isfile(PROD_DB)
    assert path.isfile(BACKUP_DB)
    assert not path.isfile(ORIG_DB)
    assert "Starting first-time backup" in caplog.messages
    assert "Database backed up" in caplog.messages
    assert "Production database vacuumed" in caplog.messages
    assert "This app doesn't need database reinit" in caplog.messages
    assert "No need to update schedules" in caplog.messages
    assert "No recipient or no log file to send" in caplog.messages
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

    main()
    assert path.isfile(backup_db_daily)
    assert not path.isfile(backup_db_weekly)
    assert not path.isfile(backup_db_monthly)
    assert "Starting first-time backup" in caplog.messages
    assert "Database backed up" in caplog.messages
    assert "Weekly backup" not in caplog.messages
    assert "Monthly backup" not in caplog.messages
    assert "No user notifications will be sent (weekend)" \
        in caplog.messages
    assert "No admin notifications will be sent (weekend)" \
        in caplog.messages
    caplog.clear()

    with freeze_time("2023-04-03"):
        assert date.today().isoweekday() == 1
        record_daily_time = path.getmtime(backup_db_daily)
        main()
        assert path.getmtime(backup_db_daily) == record_daily_time
        assert path.isfile(backup_db_weekly)
        assert not path.isfile(backup_db_monthly)
        assert "Starting first-time backup" in caplog.messages
        assert "Database backed up" in caplog.messages
        assert "Weekly backup" in caplog.messages
        assert "Monthly backup" not in caplog.messages
        assert "No eligible user found to send notification" \
            in caplog.messages
        assert "Sent admin email notification to 'user1'" \
            in caplog.messages
        assert "Sent admin email notification to 'user2'" \
            in caplog.messages
        caplog.clear()

    with freeze_time("2023-04-09"):
        assert date.today().isoweekday() == 7
        record_daily_time = path.getmtime(backup_db_daily)
        record_weekly_time = path.getmtime(backup_db_weekly)
        main()
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
        main()
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
        main()
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
        main()
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
        main()
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
    db_backup()
    assert path.isfile(BACKUP_DB)
    assert "Starting first-time backup" in caplog.messages
    assert "Database backed up" in caplog.messages
    caplog.clear()
    first_backup_time = path.getmtime(BACKUP_DB)
    db_backup()
    assert "Starting first-time backup" not in caplog.messages
    assert "Database backed up" in caplog.messages
    assert path.getmtime(BACKUP_DB) > first_backup_time
    # teardown
    remove(BACKUP_DB)


def test_db_backup_not_needed(caplog: LogCaptureFixture):
    """test_db_backup_not_needed"""
    copyfile(PROD_DB, ORIG_DB)
    db_backup()
    assert "No need to backup database as it will be reinitialised" \
        in caplog.messages
    remove(ORIG_DB)


def test_failed_db_backup(caplog: LogCaptureFixture):
    """test_failed_db_backup"""
    rename(PROD_DB, TEMP_DB)
    db_backup()
    assert "Database could not be backed up" in caplog.messages
    assert "Database could not be vacuumed" in caplog.messages
    # teardown
    rename(TEMP_DB, PROD_DB)
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
    db_reinit()
    with dbSession() as db_session:
        assert db_session.get(User, user_id)
        assert db_session.get(Schedule, sch_id).next_date == date.today()
    assert "Database reinitialised" in caplog.messages
    caplog.clear()
    # test DON'T remember schedules dates
    with freeze_time(date.today() + timedelta(days=1)):
        update_schedules()
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
    db_reinit()
    assert "Database reinitialised" in caplog.messages
    with freeze_time(date.today() + timedelta(days=1)):
        update_schedules()
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
    db_reinit()
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
    update_schedules()
    assert "No need to update schedules" in caplog.messages
    caplog.clear()
    with freeze_time(date.today() + timedelta(days=1)):
        update_schedules()
        assert "No need to update schedules" in caplog.messages
        assert f"Schedule '{name}' group '1' will be updated" \
            not in caplog.messages
        assert f"Schedule '{name}' group '2' will be updated" \
            not in caplog.messages
        assert "updated" not in caplog.messages
        caplog.clear()
    with freeze_time(date.today() + timedelta(days=2)):
        update_schedules()
        assert "No need to update schedules" not in caplog.messages
        assert f"Schedule '{name}' group '1' will be updated" \
            in caplog.messages
        assert f"Schedule '{name}' group '2' will be updated" \
            not in caplog.messages
        assert "1 schedule updated" in caplog.messages
        caplog.clear()
    with freeze_time(date.today() + timedelta(days=15)):
        update_schedules()
        assert "No need to update schedules" in caplog.messages
        assert f"Schedule '{name}' group '1' will be updated" \
            not in caplog.messages
        assert f"Schedule '{name}' group '2' will be updated" \
            not in caplog.messages
        assert "updated" not in caplog.messages
        caplog.clear()
    with freeze_time(date.today() + timedelta(days=16)):
        update_schedules()
        assert "No need to update schedules" not in caplog.messages
        assert f"Schedule '{name}' group '1' will be updated" \
            not in caplog.messages
        assert f"Schedule '{name}' group '2' will be updated" \
            in caplog.messages
        assert "1 schedule updated" in caplog.messages
        caplog.clear()
    with freeze_time(date(2023, 10, 9)):
        update_schedules()
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
    update_schedules()
    assert "No need to update schedules" in caplog.messages
    caplog.clear()
    with freeze_time(date.today() + timedelta(days=2)):
        update_schedules()
        assert date.today().isoweekday() == 7
        assert "No need to update schedules" in caplog.messages
        assert f"Schedule '{name}' group '1' will be updated" \
            not in caplog.messages
        assert f"Schedule '{name}' group '2' will be updated" \
            not in caplog.messages
        assert "updated" not in caplog.messages
        caplog.clear()
    with freeze_time(date.today() + timedelta(days=3)):
        update_schedules()
        assert date.today().isoweekday() == 1
        assert "No need to update schedules" not in caplog.messages
        assert f"Schedule '{name}' group '1' will be updated" \
            in caplog.messages
        assert f"Schedule '{name}' group '2' will be updated" \
            not in caplog.messages
        assert "1 schedule updated" in caplog.messages
        caplog.clear()
    with freeze_time(date.today() + timedelta(days=9)):
        update_schedules()
        assert date.today().isoweekday() == 7
        assert "No need to update schedules" in caplog.messages
        assert f"Schedule '{name}' group '1' will be updated" \
            not in caplog.messages
        assert f"Schedule '{name}' group '2' will be updated" \
            not in caplog.messages
        assert "updated" not in caplog.messages
        caplog.clear()
    with freeze_time(date.today() + timedelta(days=10)):
        update_schedules()
        assert date.today().isoweekday() == 1
        assert "No need to update schedules" not in caplog.messages
        assert f"Schedule '{name}' group '1' will be updated" \
            not in caplog.messages
        assert f"Schedule '{name}' group '2' will be updated" \
            in caplog.messages
        assert "1 schedule updated" in caplog.messages
        caplog.clear()
    with freeze_time(date(2023, 10, 6)):
        update_schedules()
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

    update_schedules()
    assert "No need to update schedules" in caplog.messages
    caplog.clear()
    assert test_sch.current_order() == [1, 2, 3, 4, 7]

    with freeze_time(date.today() + timedelta(days=2)):
        update_schedules()
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
        update_schedules()
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
        update_schedules()
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
        update_schedules()
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
        update_schedules()
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
        update_schedules()
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
        update_schedules()
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

    update_schedules()
    assert "No need to update schedules" in caplog.messages
    caplog.clear()
    assert test_sch.current_order() == [1, 2, 3, 4, 7]

    with freeze_time(date.today() + timedelta(weeks=0, days=2)):
        update_schedules()
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
        update_schedules()
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
        update_schedules()
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
        update_schedules()
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
        update_schedules()
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
        update_schedules()
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


# region: email notifications
@freeze_time("2023-11-03")
def test_send_user_notifications_email(caplog: LogCaptureFixture):
    """test_send_user_notifications_email"""
    assert date.today().isocalendar().weekday not in {6, 7}
    with mail.record_messages() as outbox:
        send_users_notif()
        assert len(outbox) == 0
        assert "No eligible user found to send notification" in caplog.messages
        caplog.clear()
    with dbSession() as db_session:
        user1 = db_session.get(User, 1)
        user4 = db_session.get(User, 4)
        user1.done_inv = False
        user4.done_inv = False
        db_session.commit()
        with mail.record_messages() as outbox:
            send_users_notif()
            assert len(outbox) == 2
            assert outbox[0].subject == "ConsumablesTracker - Reminder"
            assert 'ConsumablesTracker' in outbox[0].sender
            assert user1.email in outbox[0].recipients
            assert user1.email in outbox[0].send_to
            assert "Don't forget to check the inventory!" in outbox[0].body
            assert f"Hi <b>{user1.name}</b>" in outbox[0].html
            assert "Don't forget to <b>check the inventory</b>!" \
                in outbox[0].html
            assert outbox[1].subject == "ConsumablesTracker - Reminder"
            assert 'ConsumablesTracker' in outbox[1].sender
            assert user4.email in outbox[1].recipients
            assert user4.email in outbox[1].send_to
            assert "Don't forget to check the inventory!" in outbox[1].body
            assert f"Hi <b>{user4.name}</b>" in outbox[1].html
            assert "Don't forget to <b>check the inventory</b>!" \
                in outbox[1].html
        assert "No eligible user found to send notification" \
            not in caplog.messages
        assert f"Sent user email notification to '{user1.name}'" \
            in caplog.messages
        assert f"Sent user email notification to '{user4.name}'" \
            in caplog.messages
        caplog.clear()
        user4_email = user4.email
        user4.email = ""
        db_session.commit()
        with mail.record_messages() as outbox:
            send_users_notif()
            assert len(outbox) == 1
            assert user1.email in outbox[0].send_to
        assert "No eligible user found to send notification" \
            not in caplog.messages
        assert f"Sent user email notification to '{user1.name}'" \
            in caplog.messages
        assert f"Sent user email notification to '{user4.name}'" \
            not in caplog.messages
        caplog.clear()
        # teardown
        user1.done_inv = True
        user4.done_inv = True
        user4.email = user4_email
        db_session.commit()
    with freeze_time("2023-11-04"):
        send_users_notif()
        assert "No user notifications will be sent (weekend)" \
            in caplog.messages
        caplog.clear()
    with freeze_time("2023-11-05"):
        send_users_notif()
        assert "No user notifications will be sent (weekend)" \
            in caplog.messages


@freeze_time("2023-11-03")
def test_failed_send_user_notifications_email(caplog: LogCaptureFixture):
    """test_failed_send_user_notifications_email"""
    assert date.today().isocalendar().weekday not in {6, 7}
    with dbSession() as db_session:
        user1 = db_session.get(User, 1)
        user1.done_inv = False
        db_session.commit()
        mail_username = mail.state.username
        mail.state.suppress = False
        mail.state.username = "wrong_username"
        with mail.record_messages() as outbox:
            send_users_notif()
            assert len(outbox) == 0
        assert "No eligible user found to send notification" \
            not in caplog.messages
        assert f"Sent user email notification to '{user1.name}'" \
            not in caplog.messages
        assert "Failed email SMTP authentication" in caplog.messages
        caplog.clear()
        mail.state.username = mail_username
        user1_email = user1.email
        user1.email = "wrong_email"
        db_session.commit()
        with mail.record_messages() as outbox:
            send_users_notif()
            assert len(outbox) == 0
        assert "No eligible user found to send notification" \
            not in caplog.messages
        assert f"Sent user email notification to '{user1.name}'" \
            not in caplog.messages
        assert "not a valid RFC 5321 address" in caplog.text
        # teardown
        user1.done_inv = True
        user1.email = user1_email
        db_session.commit()
        mail.state.suppress = True


@freeze_time("2023-11-03")
def test_send_admin_notifications_email(caplog: LogCaptureFixture):
    """test_send_admin_notifications_email"""
    assert date.today().isocalendar().weekday not in {6, 7}
    with dbSession() as db_session:
        user1 = db_session.get(User, 1)
        user2 = db_session.get(User, 2)
        user3 = db_session.get(User, 3)
        user4 = db_session.get(User, 4)
        user5 = db_session.get(User, 5)
        product = db_session.get(Product, 1)
        # No eligible admin found to send notification
        user1_email = user1.email
        user2_email = user2.email
        user1.email = ""
        user2.email = ""
        db_session.commit()
        with mail.record_messages() as outbox:
            send_admins_notif()
            assert len(outbox) == 0
        assert "No eligible admin found to send notification" \
            in caplog.messages
        assert "No admin notifications need to be sent" \
            not in caplog.messages
        assert f"Sent admin email notification to '{user1.name}'" \
            not in caplog.messages
        assert f"Sent admin email notification to '{user2.name}'" \
            not in caplog.messages
        caplog.clear()
        user1.email = user1_email
        # No admin notifications need to be sent
        user5.reg_req = False
        db_session.commit()
        with mail.record_messages() as outbox:
            send_admins_notif()
        assert "No eligible admin found to send notification" \
            not in caplog.messages
        assert "No admin notifications need to be sent" \
            in caplog.messages
        assert f"Sent admin email notification to '{user1.name}'" \
            not in caplog.messages
        assert f"Sent admin email notification to '{user2.name}'" \
            not in caplog.messages
        caplog.clear()
        user5.reg_req = True
        db_session.commit()
        # there are users that need registration approval
        with mail.record_messages() as outbox:
            send_admins_notif()
            assert len(outbox) == 1
            assert outbox[0].subject == "ConsumablesTracker - Notifications"
            assert 'ConsumablesTracker' in outbox[0].sender
            assert user1.email in outbox[0].recipients
            assert user1.email in outbox[0].send_to
            assert "there are users that need registration approval" \
                in outbox[0].body
            assert "there are users that requested inventorying" \
                not in outbox[0].body
            assert "there are users that have to check the inventory" \
                not in outbox[0].body
            assert "there are products that need to be ordered" \
                not in outbox[0].body
            assert f"Hi <b>{user1.name}</b>" in outbox[0].html
            assert "These are the <b>daily notifications</b>:" \
                in outbox[0].html
            assert "there are users that need registration approval</li>" \
                in outbox[0].html
        assert "No eligible admin found to send notification" \
            not in caplog.messages
        assert "No admin notifications need to be sent" \
            not in caplog.messages
        assert f"Sent admin email notification to '{user1.name}'" \
            in caplog.messages
        assert f"Sent admin email notification to '{user2.name}'" \
            not in caplog.messages
        caplog.clear()
        # there are users that requested inventorying
        user2.email = user2_email
        user3.req_inv = True
        db_session.commit()
        with mail.record_messages() as outbox:
            send_admins_notif()
            assert len(outbox) == 2
            assert user1.email in outbox[0].send_to
            assert "there are users that need registration approval" \
                in outbox[0].body
            assert "there are users that requested inventorying" \
                in outbox[0].body
            assert "there are users that have to check the inventory" \
                not in outbox[0].body
            assert "there are products that need to be ordered" \
                not in outbox[0].body
            assert outbox[1].subject == "ConsumablesTracker - Notifications"
            assert 'ConsumablesTracker' in outbox[1].sender
            assert user2.email in outbox[1].recipients
            assert user2.email in outbox[1].send_to
            assert "there are users that need registration approval" \
                in outbox[1].body
            assert "there are users that requested inventorying" \
                in outbox[1].body
            assert f"Hi <b>{user2.name}</b>" in outbox[1].html
            assert "These are the <b>daily notifications</b>:" \
                in outbox[1].html
            assert "there are users that need registration approval</li>" \
                in outbox[1].html
            assert "there are users that requested inventorying</li>" \
                in outbox[1].html
            assert "there are users that have to check the inventory" \
                not in outbox[1].body
            assert "there are products that need to be ordered" \
                not in outbox[1].body
        assert "No eligible admin found to send notification" \
            not in caplog.messages
        assert "No admin notifications need to be sent" \
            not in caplog.messages
        assert f"Sent admin email notification to '{user1.name}'" \
            in caplog.messages
        assert f"Sent admin email notification to '{user2.name}'" \
            in caplog.messages
        # there are users that have to check the inventory
        user4.done_inv = False
        db_session.commit()
        with mail.record_messages() as outbox:
            send_admins_notif()
            assert len(outbox) == 2
            assert user1.email in outbox[0].send_to
            assert "there are users that need registration approval" \
                in outbox[0].body
            assert "there are users that requested inventorying" \
                in outbox[0].body
            assert "there are users that have to check the inventory" \
                in outbox[0].body
            assert "there are products that need to be ordered" \
                not in outbox[0].body
            assert user2.email in outbox[1].send_to
            assert "there are users that have to check the inventory" \
                in outbox[1].body
        # there are products that need to be ordered
        product.to_order = True
        db_session.commit()
        with mail.record_messages() as outbox:
            send_admins_notif()
            assert len(outbox) == 2
            assert user1.email in outbox[0].send_to
            assert "there are users that need registration approval" \
                in outbox[0].body
            assert "there are users that requested inventorying" \
                in outbox[0].body
            assert "there are users that have to check the inventory" \
                in outbox[0].body
            assert "there are products that need to be ordered" \
                in outbox[0].body
            assert user2.email in outbox[1].send_to
            assert "there are products that need to be ordered" \
                in outbox[1].body
        # teardown
        user3.req_inv = False
        user4.done_inv = True
        product.to_order = False
        db_session.commit()
    with freeze_time("2023-11-04"):
        send_admins_notif()
        assert "No admin notifications will be sent (weekend)" \
            in caplog.messages
        caplog.clear()
    with freeze_time("2023-11-05"):
        send_admins_notif()
        assert "No admin notifications will be sent (weekend)" \
            in caplog.messages


@freeze_time("2023-11-03")
def test_failed_send_admin_notifications_email(caplog: LogCaptureFixture):
    """test_failed_send_admin_notifications_email"""
    assert date.today().isocalendar().weekday not in {6, 7}
    with dbSession() as db_session:
        user1 = db_session.get(User, 1)
        mail_username = mail.state.username
        mail.state.suppress = False
        mail.state.username = "wrong_username"
        with mail.record_messages() as outbox:
            send_admins_notif()
            assert len(outbox) == 0
        assert "No eligible admin found to send notification" \
            not in caplog.messages
        assert "No admin notifications need to be sent" \
            not in caplog.messages
        assert f"Sent admin email notification to '{user1.name}'" \
            not in caplog.messages
        assert "Failed email SMTP authentication" in caplog.messages
        caplog.clear()
        mail.state.username = mail_username
        user1_email = user1.email
        user1.email = "wrong_email"
        db_session.commit()
        with mail.record_messages() as outbox:
            send_admins_notif()
            assert len(outbox) == 0
        assert "No eligible admin found to send notification" \
            not in caplog.messages
        assert "No admin notifications need to be sent" \
            not in caplog.messages
        assert f"Sent admin email notification to '{user1.name}'" \
            not in caplog.messages
        assert "not a valid RFC 5321 address" in caplog.text
        # teardown
        user1.email = user1_email
        db_session.commit()
        mail.state.suppress = True
# endregion


# region: send log
def test_send_log(caplog: LogCaptureFixture):
    """test_send_log"""
    log_file = logger.handlers[0].baseFilename
    assert not path.isfile(log_file)
    send_log()
    assert "No recipient or no log file to send" in caplog.messages
    assert "Sent log file to" not in caplog.text
    caplog.clear()
    # write a log message
    with open(file=log_file, mode="w", encoding="UTF-8") as file:
        file.write("Some log message")
    assert path.isfile(log_file)
    recipient = getenv("ADMIN_EMAIL")
    assert recipient
    with mail.record_messages() as outbox:
        send_log()
        assert len(outbox) == 1
        assert "ConsumablesTracker - LogFile - " in outbox[0].subject
        assert 'ConsumablesTracker' in outbox[0].sender
        assert recipient in outbox[0].recipients
        assert recipient in outbox[0].send_to
        assert "Log file attached" in outbox[0].body
        assert "<p>Log file attached.</p>" in outbox[0].html
        assert "No recipient or no log file to send" not in caplog.messages
        assert "Sent log file to" in caplog.text
        caplog.clear()
    environ["ADMIN_EMAIL"] = ""
    assert path.isfile(log_file)
    assert not getenv("ADMIN_EMAIL")
    send_log()
    assert "No recipient or no log file to send" in caplog.messages
    assert "Sent log file to" not in caplog.text
    # teardown
    environ["ADMIN_EMAIL"] = recipient


def test_failed_send_log(caplog: LogCaptureFixture):
    """test_failed_send_log"""
    log_file = logger.handlers[0].baseFilename
    # write a log message
    with open(file=log_file, mode="w", encoding="UTF-8") as file:
        file.write("Some log message")
    assert path.isfile(log_file)
    recipient = getenv("ADMIN_EMAIL")
    assert recipient
    mail_username = mail.state.username
    mail.state.suppress = False
    mail.state.username = "wrong_username"
    with mail.record_messages() as outbox:
        send_log()
        assert len(outbox) == 0
    assert "Failed email SMTP authentication" in caplog.messages
    mail.state.username = mail_username
    caplog.clear()
    environ["ADMIN_EMAIL"] = "wrong_email"
    with mail.record_messages() as outbox:
        send_log()
        assert len(outbox) == 0
    assert "not a valid RFC 5321 address" in caplog.text
    # teardown
    environ["ADMIN_EMAIL"] = recipient
    mail.state.suppress = True
# endregion
