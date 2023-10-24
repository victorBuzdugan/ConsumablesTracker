"""
Daily tasks.
Note: use only modules from the standard library
"""

import math
import sqlite3
from datetime import date, timedelta
from os import path

from helpers import CURR_DIR, DB_NAME, logger


def main(db_name: str = DB_NAME) -> None:
    """Run tasks."""
    # daily tasks
    if date.today().day == 1:
        db_backup(db_name, "monthly")
    elif date.today().isoweekday() == 1:
        db_backup(db_name, "weekly")
    else:
        db_backup(db_name, "daily")
    db_reinit(db_name)
    update_schedules(db_name)

def db_backup(db_name: str, task: str = "daily") -> None:
    """Backup and vacuum the database."""
    # pylint: disable=broad-exception-caught
    prod_db = path.join(CURR_DIR, db_name)
    orig_db = path.join(CURR_DIR, path.splitext(db_name)[0] + "_orig.db")
    backup_db = path.join(CURR_DIR, path.splitext(db_name)[0] + "_backup")
    match task:
        case "daily":
            backup_db = backup_db + "_daily.db"
        case "weekly":
            backup_db = backup_db + "_weekly.db"
            logger.debug("Weekly backup")
        case "monthly":
            backup_db = backup_db + "_monthly.db"
            logger.debug("Monthly backup")
        case other:
            logger.error("Backup task argument '%s' invalid", str(other))
            backup_db = backup_db + "_daily.db"
    if path.isfile(orig_db):
        logger.info("No need to backup database as it will be reinitialised")
    else:
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
            # reinit db
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


def update_schedules(db_name: str, base_date: date = date.today()) -> None:
    """Check update_date in schedules and update if necessary.
    
    :param base_date: date to check against the update date; used for testing
    """
    prod_db = path.join(CURR_DIR, db_name)
    con = sqlite3.connect(prod_db)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    schedules = cur.execute("""
        SELECT *
        FROM schedules
        """).fetchall()
    for schedule in schedules:
        update_date = date.fromisoformat(schedule["update_date"])
        if update_date <= base_date:
            # count all the schedules with this name and type
            sch_count = cur.execute("""
                SELECT COUNT(id)
                FROM schedules
                WHERE type = ? AND name = ?
                """, (schedule["type"], schedule["name"])
                ).fetchone()[0]
            next_date = date.fromisoformat(schedule["next_date"])
            sch_interval = (
                timedelta(days=schedule["update_interval"]) * sch_count)
            diff = math.ceil((base_date - next_date).days
                             / sch_interval.days)
            next_date += sch_interval * diff
            update_date += sch_interval * diff
            cur.execute("""
                UPDATE schedules
                SET next_date = ?, update_date = ?
                WHERE id = ?
                """,
                (next_date.isoformat(),
                 update_date.isoformat(),
                 schedule["id"])
                 )
            logger.debug("Schedule '%s' element '%d' will be updated",
                         schedule["name"], schedule["elem_id"])
    if con.in_transaction:
        logger.info("%d schedule(s) updated", con.total_changes)
        con.commit()
    else:
        logger.info("No need to update schedules")
    con.close()

if __name__== "__main__":   # pragma: no cover
    main()
