"""Daily tasks."""

import math
import sqlite3
from datetime import date, timedelta
from os import path
from sqlalchemy import select

from database import Schedule, dbSession
from helpers import CURR_DIR, DB_NAME, logger


def main(db_name: str = DB_NAME) -> None:
    """Run daily tasks."""
    db_backup(db_name)
    db_reinit(db_name)
    update_schedules()

def db_backup(db_name: str) -> None:
    """Backup and vacuum the database."""
    # pylint: disable=broad-exception-caught
    prod_db = path.join(CURR_DIR, db_name)
    backup_db = path.join(CURR_DIR, path.splitext(db_name)[0] + "_backup.db")
    try:
        if not path.isfile(prod_db):
            raise FileNotFoundError("Database doesn't exist")
        source = sqlite3.connect(prod_db)
        if not path.isfile(backup_db):
            logger.debug("Starting first-time backup")
        # sqlite3.connect creates the file if it doesn't exist
        dest = sqlite3.connect(backup_db)
        with source, dest:
            source.backup(dest)
            logger.info("Database backed up")
        dest.close()
    except Exception as err:
        logger.warning("Database could not be backed up")
        logger.debug(err)
    try:
        source.execute("VACUUM")
        logger.info("Production database vacuumed")
        source.close()
    except Exception as err:
        logger.warning("Database could not be vacuumed")
        logger.debug(err)

def db_reinit(db_name: str) -> None:
    """Reinitialise the database from original if it exists."""
    # pylint: disable=broad-exception-caught
    prod_db = path.join(CURR_DIR, db_name)
    orig_db = path.join(CURR_DIR, path.splitext(db_name)[0] + "_orig.db")
    if path.isfile(orig_db):
        try:
            source = sqlite3.connect(orig_db)
            if not path.isfile(prod_db):
                raise FileNotFoundError("Database doesn't exist")
            dest = sqlite3.connect(prod_db)
            with source, dest:
                source.backup(dest)
                logger.info("Database reinitialised")
            source.close()
            dest.close()
        except Exception as err:
            logger.warning("Database could not be reinitialised")
            logger.debug(err)
    else:
        logger.debug("This app doesn't need database reinit")

def update_schedules(base_date: date = date.today()) -> None:
    """Check update_date in schedules and update if necessary.
    
    :param base_date: date to check against the update date; used for testing
    """
    with dbSession() as db_session:
        all_group_sch = db_session.scalars(
            select(Schedule)
            .filter_by(type="group")).all()
        for group_sch in all_group_sch:
            if group_sch.update_date <= base_date:
                sch_interval = timedelta(days=group_sch.update_interval)
                diff = math.ceil((base_date - group_sch.next_date).days
                                 / group_sch.update_interval)
                group_sch.next_date += sch_interval * diff
                group_sch.update_date += sch_interval * diff
                logger.debug("Group %d '%s' schedule will be updated",
                            group_sch.elem_id, group_sch.name)
        if db_session.dirty:
            logger.info("Schedules updated")
        else:
            logger.info("No need to update schedules")
        db_session.commit()

if __name__== "__main__":
    main()
