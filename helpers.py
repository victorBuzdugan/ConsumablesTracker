import logging
import sqlite3
from functools import wraps
from logging.handlers import TimedRotatingFileHandler
from os import path
from shutil import copyfile
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from flask import flash, redirect, session, url_for
from flask_babel import gettext

from database import DB_NAME, db_url

CURR_DIR = path.dirname(path.realpath(__file__))

# region: logging configuration
log_formatter = logging.Formatter(
    fmt='%(asctime)s %(levelname)-8s %(user)-10s: %(message)s',
    datefmt='%d.%m %H:%M'
)

log_handler = TimedRotatingFileHandler(
    filename=path.join(CURR_DIR, 'logger.log'),
    encoding='UTF-8',
    when="D",
    interval=30,
    backupCount=1
)
log_handler.setLevel(logging.DEBUG)
log_handler.setFormatter(log_formatter)

logger = logging.getLogger("app_logger")
logger.setLevel(logging.DEBUG)
logger.addHandler(log_handler)

old_factory = logging.getLogRecordFactory()
def record_factory(*args, **kwargs):
    """Add user name to all log records.
    
    I the user is not logged in log as `no_user`
    """
    record = old_factory(*args, **kwargs)
    # bypass flask no request context runtime error
    try:
        record.user = session.get("user_name", default="no_user")
    except RuntimeError:
        record.user = "no_user"
    return record

logging.setLogRecordFactory(record_factory)
# endregion


# region scheduler
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
    """Reinitialise the database from original if it exists.
    
    Make sure the scheduled jobs are in the original database
    """
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

# configure scheduler logging
sch_logger = logging.getLogger('apscheduler')
sch_logger.setLevel(logging.DEBUG)
sch_logger.addHandler(log_handler)
# configure and start scheduler
scheduler = BackgroundScheduler(timezone=ZoneInfo("Europe/Bucharest"))
scheduler.add_jobstore("sqlalchemy", url=str(db_url))
scheduler.start()
# add jobs
if not scheduler.get_job("db_reinit"):
    scheduler.add_job(
        db_reinit,
        'cron', hour=7, minute=00,
        id="db_reinit",
        name="Database reinitialisation",
        coalesce=True,
        max_instances=1,
        replace_existing=True,
        misfire_grace_time=1)
if not scheduler.get_job("db_backup"):
    scheduler.add_job(
        db_backup,
        'cron', hour=7, minute=30,
        id="db_backup",
        name="Database backup",
        coalesce=True,
        max_instances=1,
        replace_existing=True,
        misfire_grace_time=None)
# endregion


# region: credentials required
def login_required(f):
    """Decorate routes to require login."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("user_id"):
            flash(gettext("You have to be logged in..."), "warning")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorate routes to require admin login."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("user_id") or not session.get("admin"):
            flash(gettext("You have to be an admin..."), "warning")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated_function
# endregion


def flash_errors(form_errors: dict) -> None:
    flash_errors = [error for errors in form_errors.values()
                    for error in errors]
    for error in flash_errors:
        flash(error, "error")
