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
    """Run daily tasks."""
    db_backup(db_name)
    db_reinit(db_name)
    update_schedules(db_name)

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

def update_schedules(db_name: str, base_date: date = date.today()) -> None:
    """Check update_date in schedules and update if necessary.
    
    :param base_date: date to check against the update date; used for testing
    """
    prod_db = path.join(CURR_DIR, db_name)
    con = sqlite3.connect(prod_db)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    all_group_sch = cur.execute("""
        SELECT id, name, elem_id, next_date, update_date, update_interval
        FROM schedules
        WHERE type = 'group'
        """).fetchall()
    for group_sch in all_group_sch:
        update_date = date.fromisoformat(group_sch["update_date"])
        if update_date <= base_date:
            next_date = date.fromisoformat(group_sch["next_date"])
            sch_interval = timedelta(days=group_sch["update_interval"])
            diff = math.ceil((base_date - next_date).days
                             / group_sch["update_interval"])
            next_date += sch_interval * diff
            update_date += sch_interval * diff
            cur.execute("""
                UPDATE schedules
                SET next_date = ?, update_date = ?
                WHERE id = ?
                """,
                (next_date.isoformat(),
                 update_date.isoformat(),
                 group_sch["id"])
                 )
            logger.debug("Group %d '%s' schedule will be updated",
                         group_sch["elem_id"], group_sch["name"])
    if con.in_transaction:
        logger.info("%d schedule(s) updated", con.total_changes)
        con.commit()
    else:
        logger.info("No need to update schedules")
    con.close()

if __name__== "__main__":
    main()
