"""Daily task tests."""

from os import path, remove, rename
from shutil import copyfile

import pytest
from pytest import LogCaptureFixture

from daily_task import db_backup, db_reinit, main
from database import User, dbSession
from helpers import CURR_DIR
from tests import TEST_DB_NAME, create_test_db, create_test_users

pytestmark = pytest.mark.daily


# region: backup/reinit
prod_db = path.join(CURR_DIR, TEST_DB_NAME)
backup_db = path.join(CURR_DIR, path.splitext(TEST_DB_NAME)[0] + "_backup.db")
orig_db = path.join(CURR_DIR, path.splitext(TEST_DB_NAME)[0] + "_orig.db")
temp_db = path.join(CURR_DIR, path.splitext(TEST_DB_NAME)[0] + "_temp.db")


# region: backup and vacuum
def test_main(create_test_db, caplog: LogCaptureFixture):
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
    # teardown
    remove(backup_db)


def test_db_backup_update_file(create_test_db, caplog: LogCaptureFixture):
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


def test_failed_db_backup(create_test_db, caplog: LogCaptureFixture):
    rename(prod_db, temp_db)
    db_backup(TEST_DB_NAME)
    assert "Database could not be backed up" in caplog.messages
    assert "Database could not be vacuumed" in caplog.messages
    # teardown
    rename(temp_db, prod_db)
# endregion


# region: reinit
def test_db_reinit(create_test_db, create_test_users, caplog: LogCaptureFixture):
    USER_ID = 7
    copyfile(prod_db, orig_db)
    with dbSession() as db_session:
        user = db_session.get(User, USER_ID)
        assert user
        db_session.delete(user)
        db_session.commit()
        assert not db_session.get(User, USER_ID)
    db_reinit(TEST_DB_NAME)
    with dbSession() as db_session:
        assert db_session.get(User, USER_ID)
    assert "Database reinitialised" in caplog.messages
    # teardown
    remove(orig_db)


def test_failed_db_reinit(create_test_db, caplog: LogCaptureFixture):
    copyfile(prod_db, orig_db)
    rename(prod_db, temp_db)
    db_reinit(TEST_DB_NAME)
    assert "Database could not be reinitialised" in caplog.messages
    # teardown
    rename(temp_db, prod_db)
    remove(orig_db)
# endregion
# endregion
