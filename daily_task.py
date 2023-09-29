import sqlite3
from os import path
from shutil import copyfile

from database import DB_NAME
from helpers import CURR_DIR, logger


def db_backup() -> None:
    """Backup and vacuum the database."""
    prod_db = path.join(CURR_DIR, DB_NAME)
    backup_db = path.join(CURR_DIR, path.splitext(DB_NAME)[0] + "_backup.db")
    source = sqlite3.connect(prod_db)
    if path.isfile(backup_db):
        dest = sqlite3.connect(backup_db)
        with source, dest:
            try:
                source.backup(dest)
                logger.info("Database backed up")
            except Exception as err:
                logger.warning("Database could not be backed up")
                logger.debug(err)
        dest.close()
    else:
        copyfile(prod_db, backup_db)
        logger.info("Database backed up. Creted a new backup file")
    try:
        source.execute("VACUUM")
        logger.info("Production database vacuumed")
    except Exception as err:
        logger.warning("Database could not be vacuumed")
        logger.debug(err)
    source.close()

def db_reinit() -> None:
    """Reinitialise the database from original if it exists."""
    prod_db = path.join(CURR_DIR, DB_NAME)
    orig_db = path.join(CURR_DIR, path.splitext(DB_NAME)[0] + "_orig.db")
    if path.isfile(orig_db):
        source = sqlite3.connect(orig_db)
        dest = sqlite3.connect(prod_db)
        with source, dest:
            try:
                source.backup(dest)
                logger.info("Database reinitialised")
            except Exception as err:
                logger.warning("Database could not be reinitialised")
                logger.debug(err)
        source.close()
        dest.close()
    else:
        logger.debug("No need to reinitialise the database")

if __name__== "__main__":
    db_backup()
    db_reinit()