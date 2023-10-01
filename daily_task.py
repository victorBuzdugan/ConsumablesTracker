"""Daily tasks."""

import sqlite3
from os import path
from shutil import copyfile

from helpers import CURR_DIR, DB_NAME, logger


def main(db_name: str = DB_NAME) -> None:
    """Run daily tasks."""
    db_backup(db_name)
    db_reinit(db_name)

def db_backup(db_name: str) -> None:
    """Backup and vacuum the database."""
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

if __name__== "__main__":
    main()
