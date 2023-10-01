import logging
from datetime import datetime
from functools import wraps
from logging.handlers import TimedRotatingFileHandler
from os import path
from zoneinfo import ZoneInfo

from flask import flash, redirect, session, url_for
from flask_babel import gettext

CURR_DIR = path.dirname(path.realpath(__file__))
DB_NAME = "inventory.db"

# region: logging configuration
log_formatter = logging.Formatter(
    fmt='%(tztime)s %(levelname)-8s %(user)-10s: %(message)s')

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
    # time with timezone
    record.tztime = datetime.now(
        tz=ZoneInfo("Europe/Bucharest")).strftime("%d.%m %H:%M")
    return record

logging.setLogRecordFactory(record_factory)
# endregion


# region: credentials required
def login_required(f):
    """Decorate routes to require login."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") == None:
            flash(gettext("You have to be logged in..."), "warning")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorate routes to require admin login."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if (session.get("user_id") == None) or (not session.get("admin")):
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
