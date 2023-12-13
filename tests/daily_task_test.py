"""Daily task tests."""

import re
from datetime import date, timedelta
from os import environ, getenv
from shutil import copyfile

import pytest
from freezegun import freeze_time
from hypothesis import given
from hypothesis import strategies as st
from pytest import LogCaptureFixture
from sqlalchemy import select

from app import mail
from blueprints.sch.sch import IndivSchedule, update_schedules
from daily_task import (db_backup, db_reinit, main, send_admins_notif,
                        send_log, send_users_notif)
from database import Product, Schedule, User, dbSession
from tests import BACKUP_DB, LOG_FILE, ORIG_DB, PROD_DB, TEMP_DB, test_users

pytestmark = pytest.mark.daily

admins_with_email = [user for user in test_users
                     if user["admin"] and user["email"]]

# region: main
@pytest.mark.mail
def test_main(caplog: LogCaptureFixture):
    """test_main"""
    # prechecks
    assert PROD_DB.exists()
    BACKUP_DB.unlink(missing_ok=True)
    ORIG_DB.unlink(missing_ok=True)
    LOG_FILE.unlink(missing_ok=True)

    main()
    assert PROD_DB.exists()
    assert BACKUP_DB.exists()
    assert not ORIG_DB.exists()
    assert "Starting first-time backup" in caplog.messages
    assert "Database backed up" in caplog.messages
    assert "Production database vacuumed" in caplog.messages
    assert "This app doesn't need database reinit" in caplog.messages
    assert "No need to update schedules" in caplog.messages
    assert "No recipient or no log file to send" in caplog.messages
    # teardown
    BACKUP_DB.unlink()


@pytest.mark.mail
def test_main_timeline(caplog: LogCaptureFixture):
    """Test backup and sending notifications in time."""
    # setup
    assert PROD_DB.exists()
    backup_db_daily = PROD_DB.with_stem(PROD_DB.stem + "_backup_daily")
    backup_db_weekly = PROD_DB.with_stem(PROD_DB.stem + "_backup_weekly")
    backup_db_monthly = PROD_DB.with_stem(PROD_DB.stem + "_backup_monthly")
    # prechecks
    assert not backup_db_daily.exists()
    assert not backup_db_weekly.exists()
    assert not backup_db_monthly.exists()

    # sunday - first daily backup
    # weekend - no notifications
    with freeze_time("2023-04-02"):
        assert date.today() == date(2023, 4, 2)
        assert date.today().isoweekday() == 7
        main()
        assert backup_db_daily.exists()
        assert not backup_db_weekly.exists()
        assert not backup_db_monthly.exists()
        assert "Starting first-time backup" in caplog.messages
        assert "Database backed up" in caplog.messages
        assert "Weekly backup" not in caplog.messages
        assert "Monthly backup" not in caplog.messages
        assert "No user notifications will be sent (weekend)" \
            in caplog.messages
        assert "No admin notifications will be sent (weekend)" \
            in caplog.messages
        caplog.clear()

    # monday - first weekly backup
    # not weekend - send notifications
    with freeze_time("2023-04-03"):
        assert date.today().isoweekday() == 1
        record_daily_time = backup_db_daily.stat().st_mtime
        main()
        assert backup_db_daily.stat().st_mtime == record_daily_time
        assert backup_db_weekly.exists()
        assert not backup_db_monthly.exists()
        assert "Starting first-time backup" in caplog.messages
        assert "Database backed up" in caplog.messages
        assert "Weekly backup" in caplog.messages
        assert "Monthly backup" not in caplog.messages
        assert "No eligible user found to send notification" \
            in caplog.messages
        assert admins_with_email
        for admin in admins_with_email:
            assert f"Sent admin email notification to '{admin['name']}'" \
                in caplog.messages
        caplog.clear()

    # sunday - second daily backup
    with freeze_time("2023-04-09"):
        assert date.today().isoweekday() == 7
        record_daily_time = backup_db_daily.stat().st_mtime
        record_weekly_time = backup_db_weekly.stat().st_mtime
        main()
        assert backup_db_daily.stat().st_mtime > record_daily_time
        assert backup_db_weekly.stat().st_mtime == record_weekly_time
        assert not backup_db_monthly.exists()
        assert "Starting first-time backup" not in caplog.messages
        assert "Database backed up" in caplog.messages
        assert "Weekly backup" not in caplog.messages
        assert "Monthly backup" not in caplog.messages
        caplog.clear()

    # monday - second weekly backup
    with freeze_time("2023-04-10"):
        assert date.today().isoweekday() == 1
        record_daily_time = backup_db_daily.stat().st_mtime
        record_weekly_time = backup_db_weekly.stat().st_mtime
        main()
        assert backup_db_daily.stat().st_mtime == record_daily_time
        assert backup_db_weekly.stat().st_mtime > record_weekly_time
        assert not backup_db_monthly.exists()
        assert "Starting first-time backup" not in caplog.messages
        assert "Database backed up" in caplog.messages
        assert "Weekly backup" in caplog.messages
        assert "Monthly backup" not in caplog.messages
        caplog.clear()

    # 1'st of the month - first monthly backup
    with freeze_time("2023-05-01"):
        assert date.today().isoweekday() == 1
        record_daily_time = backup_db_daily.stat().st_mtime
        record_weekly_time = backup_db_weekly.stat().st_mtime
        main()
        assert backup_db_daily.stat().st_mtime == record_daily_time
        assert backup_db_weekly.stat().st_mtime == record_weekly_time
        assert backup_db_monthly.exists()
        assert "Starting first-time backup" in caplog.messages
        assert "Database backed up" in caplog.messages
        assert "Weekly backup" not in caplog.messages
        assert "Monthly backup" in caplog.messages
        caplog.clear()

    # sunday - third daily backup
    with freeze_time("2023-05-07"):
        assert date.today().isoweekday() == 7
        record_daily_time = backup_db_daily.stat().st_mtime
        record_weekly_time = backup_db_weekly.stat().st_mtime
        record_monthly_time = backup_db_monthly.stat().st_mtime
        main()
        assert backup_db_daily.stat().st_mtime > record_daily_time
        assert backup_db_weekly.stat().st_mtime == record_weekly_time
        assert backup_db_monthly.stat().st_mtime == record_monthly_time
        assert "Starting first-time backup" not in caplog.messages
        assert "Database backed up" in caplog.messages
        assert "Weekly backup" not in caplog.messages
        assert "Monthly backup" not in caplog.messages
        caplog.clear()

    # 1'st of the month - second monthly backup
    with freeze_time("2023-06-01"):
        assert date.today().isoweekday() == 4
        record_daily_time = backup_db_daily.stat().st_mtime
        record_weekly_time = backup_db_weekly.stat().st_mtime
        record_monthly_time = backup_db_monthly.stat().st_mtime
        main()
        assert backup_db_daily.stat().st_mtime == record_daily_time
        assert backup_db_weekly.stat().st_mtime == record_weekly_time
        assert backup_db_monthly.stat().st_mtime > record_monthly_time
        assert "Starting first-time backup" not in caplog.messages
        assert "Database backed up" in caplog.messages
        assert "Weekly backup" not in caplog.messages
        assert "Monthly backup" in caplog.messages
        caplog.clear()

    # teardown
    backup_db_daily.unlink()
    backup_db_weekly.unlink()
    backup_db_monthly.unlink()
# endregion


# region: backup/reinit
# region: backup and vacuum
def test_db_backup_updates_file(caplog: LogCaptureFixture):
    """test_db_backup_updates_file"""
    # setup
    BACKUP_DB.unlink(missing_ok=True)
    # run test
    db_backup()
    assert BACKUP_DB.exists()
    assert "Starting first-time backup" in caplog.messages
    assert "Database backed up" in caplog.messages
    caplog.clear()
    first_backup_time = BACKUP_DB.stat().st_mtime
    db_backup()
    assert "Starting first-time backup" not in caplog.messages
    assert "Database backed up" in caplog.messages
    assert BACKUP_DB.stat().st_mtime > first_backup_time
    # teardown
    BACKUP_DB.unlink()


def test_db_backup_not_needed(caplog: LogCaptureFixture):
    """test_db_backup_not_needed"""
    # setup
    copyfile(PROD_DB, ORIG_DB)
    # run test
    db_backup()
    assert "No need to backup database as it will be reinitialised" \
        in caplog.messages
    # teardown
    ORIG_DB.unlink()


def test_failed_db_backup(caplog: LogCaptureFixture):
    """test_failed_db_backup"""
    # setup
    PROD_DB.rename(TEMP_DB)
    # run test
    db_backup()
    assert "Database could not be backed up" in caplog.messages
    assert "Database could not be vacuumed" in caplog.messages
    # teardown
    TEMP_DB.rename(PROD_DB)
# endregion


# region: reinit
@given(user = st.sampled_from([user for user in test_users
                               if not user["has_products"]]))
def test_db_reinit(caplog: LogCaptureFixture, user: dict):
    """Test successfully reinit the database"""
    # setup
    copyfile(PROD_DB, ORIG_DB)
    with dbSession() as db_session:
        db_session.delete(db_session.get(User, user["id"]))
        db_session.commit()
        assert not db_session.get(User, user["id"])
    # run test
    db_reinit()
    with dbSession() as db_session:
        assert db_session.get(User, user["id"])
    assert "Database reinitialised" in caplog.messages
    # teardown
    ORIG_DB.unlink()


def test_failed_db_reinit(caplog: LogCaptureFixture):
    """test_failed_db_reinit"""
    copyfile(PROD_DB, ORIG_DB)
    PROD_DB.rename(TEMP_DB)
    db_reinit()
    assert "Database could not be reinitialised" in caplog.messages
    # teardown
    TEMP_DB.rename(PROD_DB)
    ORIG_DB.unlink()
# endregion
# endregion


# region: schedules
@freeze_time("2023-05-06")
def test_update_group_schedules_1(caplog: LogCaptureFixture):
    """Explicit date checking 2 groups 2 weeks interval"""
    # constants
    name = "test_saturday_working"
    # setup
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
    # run test
    update_schedules()
    assert "No need to update schedules" in caplog.messages
    caplog.clear()
    # advance time to 1 day before group 1 update date
    with freeze_time(date.today() + timedelta(days=1)):
        update_schedules()
        assert "No need to update schedules" in caplog.messages
        assert f"Schedule '{name}' group '1' will be updated" \
            not in caplog.messages
        assert f"Schedule '{name}' group '2' will be updated" \
            not in caplog.messages
        assert "updated" not in caplog.messages
    with dbSession() as db_session:
        schedules: list[Schedule] = db_session.scalars(
            select(Schedule)
            .filter_by(name=name)).all()
        assert schedules[0].next_date == date(2023, 5, 6)
        assert schedules[0].update_date == date(2023, 5, 8)
        assert schedules[1].next_date == date(2023, 5, 20)
        assert schedules[1].update_date == date(2023, 5, 22)
    caplog.clear()
    # advance time to group 1 update date
    with freeze_time(date(2023, 5, 8)):
        update_schedules()
        assert "No need to update schedules" not in caplog.messages
        assert f"Schedule '{name}' group '1' will be updated" \
            in caplog.messages
        assert f"Schedule '{name}' group '2' will be updated" \
            not in caplog.messages
        assert "1 schedule updated" in caplog.messages
    with dbSession() as db_session:
        schedules: list[Schedule] = db_session.scalars(
            select(Schedule)
            .filter_by(name=name)).all()
        assert schedules[0].next_date == date(2023, 6, 3)
        assert schedules[0].update_date == date(2023, 6, 5)
        assert schedules[1].next_date == date(2023, 5, 20)
        assert schedules[1].update_date == date(2023, 5, 22)
    caplog.clear()
    # advance time to 1 day before group 2 update date
    with freeze_time(date(2023, 5, 21)):
        update_schedules()
        assert "No need to update schedules" in caplog.messages
        assert f"Schedule '{name}' group '1' will be updated" \
            not in caplog.messages
        assert f"Schedule '{name}' group '2' will be updated" \
            not in caplog.messages
        assert "updated" not in caplog.messages
    with dbSession() as db_session:
        schedules: list[Schedule] = db_session.scalars(
            select(Schedule)
            .filter_by(name=name)).all()
        assert schedules[0].next_date == date(2023, 6, 3)
        assert schedules[0].update_date == date(2023, 6, 5)
        assert schedules[1].next_date == date(2023, 5, 20)
        assert schedules[1].update_date == date(2023, 5, 22)
    caplog.clear()
    # advance time to 1 day past group 2 update date
    with freeze_time(date(2023, 5, 23)):
        update_schedules()
        assert "No need to update schedules" not in caplog.messages
        assert f"Schedule '{name}' group '1' will be updated" \
            not in caplog.messages
        assert f"Schedule '{name}' group '2' will be updated" \
            in caplog.messages
        assert "1 schedule updated" in caplog.messages
    with dbSession() as db_session:
        schedules: list[Schedule] = db_session.scalars(
            select(Schedule)
            .filter_by(name=name)).all()
        assert schedules[0].next_date == date(2023, 6, 3)
        assert schedules[0].update_date == date(2023, 6, 5)
        assert schedules[1].next_date == date(2023, 6, 17)
        assert schedules[1].update_date == date(2023, 6, 19)
    caplog.clear()
    # advance time past group 1 and group 2 update date
    with freeze_time(date(2023, 11, 9)):
        update_schedules()
        assert "No need to update schedules" not in caplog.messages
        assert f"Schedule '{name}' group '1' will be updated" \
            in caplog.messages
        assert f"Schedule '{name}' group '2' will be updated" \
            in caplog.messages
        assert "2 schedules updated" in caplog.messages
        caplog.clear()
    # final checks and teardown
    with dbSession() as db_session:
        schedules: list[Schedule] = db_session.scalars(
            select(Schedule)
            .filter_by(name=name)).all()
        assert schedules[0].elem_id == 1
        assert schedules[0].next_date == date(2023, 11, 18)
        assert schedules[0].update_date == date(2023, 11, 20)
        assert schedules[0].update_interval == 14
        assert schedules[1].elem_id == 2
        assert schedules[1].next_date == date(2023, 12, 2)
        assert schedules[1].update_date == date(2023, 12, 4)
        assert schedules[1].update_interval == 14
        # teardown
        for schedule in schedules:
            db_session.delete(schedule)
        db_session.commit()


@freeze_time("2023-09-01")
def test_update_group_schedules_2(caplog: LogCaptureFixture):
    """Explicit date checking 2 groups 1 weeks interval"""
    # constants
    name = "test_sunday_movie"
    # setup
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
    # run test
    update_schedules()
    assert "No need to update schedules" in caplog.messages
    caplog.clear()
    # advance time to 1 day before group 1 update date
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
    # advance time to group 1 update date
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
    # advance time to 1 day before group 2 update date
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
    # advance time to group 2 update date
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
    # advance time past group 1 and group 2 update date
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
    # final checks and teardown
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


@freeze_time("2023-03-03")
def test_update_indiv_schedule_1(caplog: LogCaptureFixture):
    """Explicit date checking 1 week interval"""
    # constants
    name = "test_schedule"
    # setup
    assert date.today() == date(2023, 3, 3)
    assert date.today().isoweekday() == 5
    test_sch = IndivSchedule(
        name=name,
        sch_day=1,
        sch_day_update=1,
        switch_interval=timedelta(weeks=1),
        start_date=date.today())
    test_sch.register(start_date=date(2023, 2, 27))
    assert test_sch.current_order() == [1, 2, 3, 4, 7]
    # run test
    update_schedules()
    assert "No need to update schedules" in caplog.messages
    with dbSession() as db_session:
        schedules: list[Schedule] = db_session.scalars(
            select(Schedule)
            .filter_by(name=name)).all()
        assert schedules[0].next_date == date(2023, 2, 27)
        assert schedules[0].update_date == date(2023, 3, 6)
        assert schedules[1].next_date == date(2023, 3, 6)
        assert schedules[1].update_date == date(2023, 3, 13)
        assert schedules[2].next_date == date(2023, 3, 13)
        assert schedules[2].update_date == date(2023, 3, 20)
        assert schedules[3].next_date == date(2023, 3, 20)
        assert schedules[3].update_date == date(2023, 3, 27)
        assert schedules[4].next_date == date(2023, 3, 27)
        assert schedules[4].update_date == date(2023, 4, 3)
    caplog.clear()
    assert test_sch.current_order() == [1, 2, 3, 4, 7]
    # advance time to 1 day before update
    with freeze_time(date(2023, 3, 5)):
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
        with dbSession() as db_session:
            schedules: list[Schedule] = db_session.scalars(
                select(Schedule)
                .filter_by(name=name)).all()
            assert schedules[0].next_date == date(2023, 2, 27)
            assert schedules[0].update_date == date(2023, 3, 6)
            assert schedules[1].next_date == date(2023, 3, 6)
            assert schedules[1].update_date == date(2023, 3, 13)
            assert schedules[2].next_date == date(2023, 3, 13)
            assert schedules[2].update_date == date(2023, 3, 20)
            assert schedules[3].next_date == date(2023, 3, 20)
            assert schedules[3].update_date == date(2023, 3, 27)
            assert schedules[4].next_date == date(2023, 3, 27)
            assert schedules[4].update_date == date(2023, 4, 3)
        caplog.clear()
        assert test_sch.current_order() == [1, 2, 3, 4, 7]
    # advance time to update day
    with freeze_time(date(2023, 3, 6)):
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
        with dbSession() as db_session:
            schedules: list[Schedule] = db_session.scalars(
                select(Schedule)
                .filter_by(name=name)).all()
            assert schedules[1].next_date == date(2023, 3, 6)
            assert schedules[1].update_date == date(2023, 3, 13)
            assert schedules[2].next_date == date(2023, 3, 13)
            assert schedules[2].update_date == date(2023, 3, 20)
            assert schedules[3].next_date == date(2023, 3, 20)
            assert schedules[3].update_date == date(2023, 3, 27)
            assert schedules[4].next_date == date(2023, 3, 27)
            assert schedules[4].update_date == date(2023, 4, 3)
            assert schedules[0].next_date == date(2023, 4, 3)
            assert schedules[0].update_date == date(2023, 4, 10)
        caplog.clear()
        assert test_sch.current_order() == [2, 3, 4, 7, 1]
    # advance time to 1 day before update
    with freeze_time(date(2023, 3, 12)):
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
        with dbSession() as db_session:
            schedules: list[Schedule] = db_session.scalars(
                select(Schedule)
                .filter_by(name=name)).all()
            assert schedules[1].next_date == date(2023, 3, 6)
            assert schedules[1].update_date == date(2023, 3, 13)
            assert schedules[2].next_date == date(2023, 3, 13)
            assert schedules[2].update_date == date(2023, 3, 20)
            assert schedules[3].next_date == date(2023, 3, 20)
            assert schedules[3].update_date == date(2023, 3, 27)
            assert schedules[4].next_date == date(2023, 3, 27)
            assert schedules[4].update_date == date(2023, 4, 3)
            assert schedules[0].next_date == date(2023, 4, 3)
            assert schedules[0].update_date == date(2023, 4, 10)
        caplog.clear()
        assert test_sch.current_order() == [2, 3, 4, 7, 1]
    # advance time 2 days past update day
    with freeze_time(date(2023, 3, 15)):
        update_schedules()
        assert date.today().isoweekday() == 3
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
        with dbSession() as db_session:
            schedules: list[Schedule] = db_session.scalars(
                select(Schedule)
                .filter_by(name=name)).all()
            assert schedules[2].next_date == date(2023, 3, 13)
            assert schedules[2].update_date == date(2023, 3, 20)
            assert schedules[3].next_date == date(2023, 3, 20)
            assert schedules[3].update_date == date(2023, 3, 27)
            assert schedules[4].next_date == date(2023, 3, 27)
            assert schedules[4].update_date == date(2023, 4, 3)
            assert schedules[0].next_date == date(2023, 4, 3)
            assert schedules[0].update_date == date(2023, 4, 10)
            assert schedules[1].next_date == date(2023, 4, 10)
            assert schedules[1].update_date == date(2023, 4, 17)
        caplog.clear()
        assert test_sch.current_order() == [3, 4, 7, 1, 2]
    # advance time to update day
    with freeze_time(date(2023, 3, 20)):
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
        with dbSession() as db_session:
            schedules: list[Schedule] = db_session.scalars(
                select(Schedule)
                .filter_by(name=name)).all()
            assert schedules[3].next_date == date(2023, 3, 20)
            assert schedules[3].update_date == date(2023, 3, 27)
            assert schedules[4].next_date == date(2023, 3, 27)
            assert schedules[4].update_date == date(2023, 4, 3)
            assert schedules[0].next_date == date(2023, 4, 3)
            assert schedules[0].update_date == date(2023, 4, 10)
            assert schedules[1].next_date == date(2023, 4, 10)
            assert schedules[1].update_date == date(2023, 4, 17)
            assert schedules[2].next_date == date(2023, 4, 17)
            assert schedules[2].update_date == date(2023, 4, 24)
        caplog.clear()
        assert test_sch.current_order() == [4, 7, 1, 2, 3]
    # advance time past two updates
    with freeze_time(date(2023, 4, 6)):
        update_schedules()
        assert date.today().isoweekday() == 4
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
        with dbSession() as db_session:
            schedules: list[Schedule] = db_session.scalars(
                select(Schedule)
                .filter_by(name=name)).all()
            assert schedules[0].next_date == date(2023, 4, 3)
            assert schedules[0].update_date == date(2023, 4, 10)
            assert schedules[1].next_date == date(2023, 4, 10)
            assert schedules[1].update_date == date(2023, 4, 17)
            assert schedules[2].next_date == date(2023, 4, 17)
            assert schedules[2].update_date == date(2023, 4, 24)
            assert schedules[3].next_date == date(2023, 4, 24)
            assert schedules[3].update_date == date(2023, 5, 1)
            assert schedules[4].next_date == date(2023, 5, 1)
            assert schedules[4].update_date == date(2023, 5, 8)
        caplog.clear()
        assert test_sch.current_order() == [1, 2, 3, 4, 7]
    # advance time past four updates
    with freeze_time(date(2023, 5, 1)):
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
        with dbSession() as db_session:
            schedules: list[Schedule] = db_session.scalars(
                select(Schedule)
                .filter_by(name=name)).all()
            assert schedules[4].next_date == date(2023, 5, 1)
            assert schedules[4].update_date == date(2023, 5, 8)
            assert schedules[0].next_date == date(2023, 5, 8)
            assert schedules[0].update_date == date(2023, 5, 15)
            assert schedules[1].next_date == date(2023, 5, 15)
            assert schedules[1].update_date == date(2023, 5, 22)
            assert schedules[2].next_date == date(2023, 5, 22)
            assert schedules[2].update_date == date(2023, 5, 29)
            assert schedules[3].next_date == date(2023, 5, 29)
            assert schedules[3].update_date == date(2023, 6, 5)
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
    # constants
    name = "test_schedule"
    # setup
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
    # run test
    update_schedules()
    assert "No need to update schedules" in caplog.messages
    caplog.clear()
    assert test_sch.current_order() == [1, 2, 3, 4, 7]
    # advance time to 1 day before update
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
    # advance time to update day
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
    # advance time to 1 week before update
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
    # advance time to update day
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
    # advance time to 1 week before update
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
    # advance time past two updates
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
@pytest.mark.mail
@freeze_time("2023-11-03")
@given(data = st.data())
def test_send_user_notifications_email(
        caplog: LogCaptureFixture, data: st.DataObject):
    """Test successfully send user notifications"""
    # setup
    users_with_prod = [user for user in test_users if user["has_products"]]
    users = []
    for _ in range(3):
        users.append(data.draw(st.sampled_from(users_with_prod)))
        users_with_prod.remove(users[-1])
    users.sort(key=lambda user: user["id"])
    assert date.today().isocalendar().weekday not in {6, 7}
    # run test
    with mail.record_messages() as outbox:
        send_users_notif()
        assert len(outbox) == 0
        assert "No eligible user found to send notification" in caplog.messages
        caplog.clear()
    with dbSession() as db_session:
        for user in users:
            db_session.get(User, user["id"]).done_inv = False
        db_session.commit()
    with mail.record_messages() as outbox:
        send_users_notif()
        assert len(outbox) == len(users)
        for ind, user in enumerate(users):
            assert outbox[ind].subject == "ConsumablesTracker - Reminder"
            assert 'ConsumablesTracker' in outbox[ind].sender
            assert user["email"] in outbox[ind].recipients
            assert user["email"] in outbox[ind].send_to
            assert "Don't forget to check the inventory!" in outbox[ind].body
            assert f"Hi <b>{user['name']}</b>" in outbox[ind].html
            assert "Don't forget to <b>check the inventory</b>!" \
                in outbox[ind].html
    assert "No eligible user found to send notification" not in caplog.messages
    for user in users:
        assert f"Sent user email notification to '{user['name']}'" \
            in caplog.messages
    caplog.clear()
    # remove email from a user
    removed_user = users.pop()
    with dbSession() as db_session:
        db_session.get(User, removed_user["id"]).email = ""
        db_session.commit()
    with mail.record_messages() as outbox:
        send_users_notif()
        assert len(outbox) == len(users)
        for ind, user in enumerate(users):
            assert user["email"] in outbox[ind].send_to
    assert "No eligible user found to send notification" not in caplog.messages
    for user in users:
        assert f"Sent user email notification to '{user['name']}'" \
            in caplog.messages
    assert f"Sent user email notification to '{removed_user['name']}'" \
        not in caplog.messages
    caplog.clear()
    # test weekend
    with freeze_time("2023-11-04"):
        assert date.today().isocalendar().weekday == 6
        send_users_notif()
        assert "No user notifications will be sent (weekend)" \
            in caplog.messages
        caplog.clear()
    with freeze_time("2023-11-05"):
        assert date.today().isocalendar().weekday == 7
        send_users_notif()
        assert "No user notifications will be sent (weekend)" \
            in caplog.messages
    # teardown
    with dbSession() as db_session:
        for user in users:
            db_session.get(User, user["id"]).done_inv = True
        db_session.get(User, removed_user["id"]).done_inv = True
        db_session.get(User, removed_user["id"]).email = removed_user["email"]
        db_session.commit()


@pytest.mark.mail
@freeze_time("2023-11-03")
def test_failed_send_user_notifications_email(caplog: LogCaptureFixture):
    """test_failed_send_user_notifications_email"""
    invalid_address = re.compile(
        r"The recipient address.*is not a valid RFC 5321.*address")
    # setup
    user = test_users[1]
    assert date.today().isocalendar().weekday not in {6, 7}
    with dbSession() as db_session:
        db_session.get(User, user["id"]).done_inv = False
        db_session.commit()
    mail_username = mail.state.username
    mail.state.suppress = False
    mail.state.username = "wrong_mail_username"
    # run test
    with mail.record_messages() as outbox:
        send_users_notif()
        assert len(outbox) == 0
    assert "No eligible user found to send notification" not in caplog.messages
    assert f"Sent user email notification to '{user['name']}'" \
        not in caplog.messages
    assert "Failed email SMTP authentication" in caplog.messages
    caplog.clear()
    # section setup
    mail.state.username = mail_username
    with dbSession() as db_session:
        db_session.get(User, user["id"]).email = "wrong_email_address"
        db_session.commit()
    # run test
    with mail.record_messages() as outbox:
        send_users_notif()
        assert len(outbox) == 0
    assert "No eligible user found to send notification" not in caplog.messages
    assert f"Sent user email notification to '{user['name']}'" \
        not in caplog.messages
    assert invalid_address.search(caplog.text)
    # teardown
    with dbSession() as db_session:
        db_session.get(User, user["id"]).done_inv = True
        db_session.get(User, user["id"]).email = user["email"]
        db_session.commit()
    mail.state.suppress = True


# region: send admin notifications
@pytest.fixture(name="admins")
def admins_fixture() -> list[dict]:
    """List of all in use admins."""
    return [user for user in test_users if user["admin"] and user["in_use"]]


@pytest.fixture(name="users_reg_req")
def users_reg_req_fixture() -> list[dict]:
    """List of users that requested registration."""
    return [user for user in test_users if user["reg_req"]]


@pytest.fixture(name="users")
def users_fixture() -> list[dict]:
    """List of users that requested registration."""
    return [user for user in test_users
                if not user["admin"] and user["has_products"]]


# region: no email sent
def _test_send_admin_notifications_no_email_sent(
        caplog: LogCaptureFixture, freeze_date: str, messages: list[str]):
    """Common logic for admin notifications no mail sent"""
    log_messages = {
        "weekend": "No admin notifications will be sent (weekend)",
        "no_admin_email": "No eligible admin found to send notification",
        "not_needed": "No admin notifications need to be sent",
    }
    with freeze_time(freeze_date):
        with mail.record_messages() as outbox:
            send_admins_notif()
            assert len(outbox) == 0
    assert len(caplog.messages) == len(messages)
    for message in messages:
        assert log_messages[message] in caplog.messages


@pytest.mark.parametrize("freeze_date", [
    pytest.param("2023-11-04", id="Saturday"),
    pytest.param("2023-11-04", id="Sunday"),
])
def test_send_admin_notifications_email_weekend(
        caplog: LogCaptureFixture, freeze_date: str):
    """test_send_admin_notifications_email_weekend"""
    assert date.fromisoformat(freeze_date).isocalendar().weekday in {6, 7}
    _test_send_admin_notifications_no_email_sent(
        caplog=caplog,
        freeze_date=freeze_date,
        messages=["weekend"]
    )


def test_send_admin_notifications_email_no_eligible_admin(
        caplog: LogCaptureFixture, admins: list[dict]):
    """test_send_admin_notifications_email_no_eligible_admin"""
    freeze_date = "2023-11-03"
    assert date.fromisoformat(freeze_date).isocalendar().weekday not in {6, 7}
    with dbSession() as db_session:
        for admin in admins:
            db_session.get(User, admin["id"]).email = ""
        db_session.commit()
    _test_send_admin_notifications_no_email_sent(
        caplog=caplog,
        freeze_date=freeze_date,
        messages=["no_admin_email"]
    )
    with dbSession() as db_session:
        for admin in admins:
            db_session.get(User, admin["id"]).email = admin["email"]
        db_session.commit()


def test_send_admin_notifications_email_not_needed(
        caplog: LogCaptureFixture, users_reg_req: list[dict]):
    """test_send_admin_notifications_email_not_needed"""
    freeze_date = "2023-11-03"
    assert date.fromisoformat(freeze_date).isocalendar().weekday not in {6, 7}
    with dbSession() as db_session:
        for user in users_reg_req:
            db_session.get(User, user["id"]).reg_req = False
        db_session.commit()
    _test_send_admin_notifications_no_email_sent(
        caplog=caplog,
        freeze_date=freeze_date,
        messages=["not_needed"]
    )
    with dbSession() as db_session:
        for user in users_reg_req:
            db_session.get(User, user["id"]).reg_req = True
        db_session.commit()
# endregion


# region: mail sent
def _test_send_admin_notifications_email_sent(
        caplog: LogCaptureFixture, admins: list[dict], messages: list[str]):
    """Common logic for admin notifications and mail sent"""
    log_messages = {
        "weekend": "No admin notifications will be sent (weekend)",
        "no_admin_email": "No eligible admin found to send notification",
        "not_needed": "No admin notifications need to be sent",
    }
    mail_messages = {
        "reg_req": "there are users that need registration approval",
        "req_inv": "there are users that requested inventorying",
        "check_inv": "there are users that have to check the inventory",
        "prod_ord": "there are products that need to be ordered",
    }
    with freeze_time("2023-11-03"):
        assert date.today().isocalendar().weekday not in {6, 7}
        with mail.record_messages() as outbox:
            send_admins_notif()
            assert len(outbox) == len(admins)
            for ind, admin in enumerate(admins):
                assert outbox[ind].subject == \
                    "ConsumablesTracker - Notifications"
                assert 'ConsumablesTracker' in outbox[ind].sender
                assert admin["email"] in outbox[ind].recipients
                assert admin["email"] in outbox[ind].send_to
                for message in messages:
                    assert mail_messages[message] in outbox[ind].body
                    assert mail_messages[message] in outbox[ind].html
                assert f"Hi <b>{admin['name']}</b>" in outbox[ind].html
                assert "These are the <b>daily notifications</b>:" \
                    in outbox[ind].html
    assert len(caplog.messages) == len(admins)
    for log_message in log_messages.values():
        assert log_message not in caplog.messages
    for admin in admins:
        assert f"Sent admin email notification to '{admin['name']}'" \
            in caplog.messages


@pytest.mark.mail
def test_send_admin_notifications_email_registration_requested(
        caplog: LogCaptureFixture,
        admins: list[dict], users_reg_req: list[dict]):
    """test_send_admin_notifications_email_registration_requested"""
    assert users_reg_req
    _test_send_admin_notifications_email_sent(
        caplog=caplog,
        admins=admins,
        messages=["reg_req"]
    )


@pytest.mark.mail
def test_send_admin_notifications_email_inventorying_requested(
        caplog: LogCaptureFixture,
        admins: list[dict], users_reg_req: list[dict], users: list[dict]):
    """test_send_admin_notifications_email_inventorying_requested"""
    assert users_reg_req
    with dbSession() as db_session:
        db_session.get(User, users[0]["id"]).req_inv = True
        db_session.commit()
    _test_send_admin_notifications_email_sent(
        caplog=caplog,
        admins=admins,
        messages=["reg_req", "req_inv"]
    )
    with dbSession() as db_session:
        db_session.get(User, users[0]["id"]).req_inv = False
        db_session.commit()


@pytest.mark.mail
def test_send_admin_notifications_email_inventorying_in_progress(
        caplog: LogCaptureFixture,
        admins: list[dict], users_reg_req: list[dict], users: list[dict]):
    """test_send_admin_notifications_email_inventorying_in_progress"""
    assert users_reg_req
    with dbSession() as db_session:
        db_session.get(User, users[0]["id"]).done_inv = False
        db_session.commit()
    _test_send_admin_notifications_email_sent(
        caplog=caplog,
        admins=admins,
        messages=["reg_req", "check_inv"]
    )
    with dbSession() as db_session:
        db_session.get(User, users[0]["id"]).done_inv = True
        db_session.commit()


@pytest.mark.mail
def test_send_admin_notifications_email_products_need_ordering(
        caplog: LogCaptureFixture,
        admins: list[dict], users_reg_req: list[dict]):
    """test_send_admin_notifications_email_products_need_ordering"""
    prod_id = 1
    assert users_reg_req
    with dbSession() as db_session:
        db_session.get(Product, prod_id).to_order = True
        db_session.commit()
    _test_send_admin_notifications_email_sent(
        caplog=caplog,
        admins=admins,
        messages=["reg_req", "prod_ord"]
    )
    with dbSession() as db_session:
        db_session.get(Product, prod_id).to_order = False
        db_session.commit()
# endregion


@pytest.mark.mail
@freeze_time("2023-11-03")
def test_failed_send_admin_notifications_email(
        caplog: LogCaptureFixture, admins: list[dict]):
    """test_failed_send_admin_notifications_email"""
    # setup
    invalid_address = re.compile(
        r"The recipient address.*is not a valid RFC 5321.*address")
    assert date.today().isocalendar().weekday not in {6, 7}
    mail_username = mail.state.username
    mail.state.suppress = False
    mail.state.username = "wrong_mail_username"
    # run test
    with mail.record_messages() as outbox:
        send_admins_notif()
        assert len(outbox) == 0
    assert "No eligible admin found to send notification" \
        not in caplog.messages
    assert "No admin notifications need to be sent" \
        not in caplog.messages
    for admin in admins:
        assert f"Sent admin email notification to '{admin['name']}'" \
            not in caplog.messages
    assert "Failed email SMTP authentication" in caplog.messages
    caplog.clear()
    # section setup
    mail.state.username = mail_username
    with dbSession() as db_session:
        db_session.get(User, admins[0]["id"]).email = "wrong_email_address"
        db_session.commit()
    # run test
    with mail.record_messages() as outbox:
        send_admins_notif()
        assert len(outbox) == 0
    assert "No eligible admin found to send notification" \
        not in caplog.messages
    assert "No admin notifications need to be sent" \
        not in caplog.messages
    for admin in admins:
        assert f"Sent admin email notification to '{admin['name']}'" \
            not in caplog.messages
    assert invalid_address.search(caplog.text)
    # teardown
    with dbSession() as db_session:
        db_session.get(User, admins[0]["id"]).email = admins[0]["email"]
        db_session.commit()
    mail.state.suppress = True
# endregion
# endregion


# region: send log
@pytest.mark.mail
def test_send_log(caplog: LogCaptureFixture):
    """test_send_log"""
    # setup
    LOG_FILE.unlink(missing_ok=True)
    # run test
    send_log()
    assert "No recipient or no log file to send" in caplog.messages
    assert "Sent log file to" not in caplog.text
    caplog.clear()
    # setup section
    LOG_FILE.write_text(
        f"{date.today().strftime('%d.%m')} Some log message",
        encoding="UTF-8")
    recipient = getenv("ADMIN_EMAIL")
    assert recipient
    # run test
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
    # setup section
    environ["ADMIN_EMAIL"] = ""
    assert LOG_FILE.exists()
    assert not getenv("ADMIN_EMAIL")
    # run test
    send_log()
    assert "No recipient or no log file to send" in caplog.messages
    assert "Sent log file to" not in caplog.text
    # teardown
    environ["ADMIN_EMAIL"] = recipient


@pytest.mark.mail
def test_failed_send_log(caplog: LogCaptureFixture):
    """test_failed_send_log"""
    # setup
    invalid_address = re.compile(
        r"The recipient address.*is not a valid RFC 5321.*address")
    LOG_FILE.write_text(
        f"{date.today().strftime('%d.%m')} Some log message",
        encoding="UTF-8")
    recipient = getenv("ADMIN_EMAIL")
    assert recipient
    mail_username = mail.state.username
    mail.state.suppress = False
    mail.state.username = "wrong_username"
    # run test
    with mail.record_messages() as outbox:
        send_log()
        assert len(outbox) == 0
    assert "Failed email SMTP authentication" in caplog.messages
    caplog.clear()
    # setup section
    mail.state.username = mail_username
    environ["ADMIN_EMAIL"] = "wrong_email"
    with mail.record_messages() as outbox:
        send_log()
        assert len(outbox) == 0
    assert invalid_address.search(caplog.text)
    # teardown
    environ["ADMIN_EMAIL"] = recipient
    mail.state.suppress = True
# endregion
