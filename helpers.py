import logging
import os
from functools import wraps
from logging.handlers import TimedRotatingFileHandler

from flask import flash, redirect, session, url_for
from flask_babel import gettext


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

def flash_errors(form_errors: dict) -> None:
    flash_errors = [error for errors in form_errors.values()
                    for error in errors]
    for error in flash_errors:
        flash(error, "error")

# region: logging configuration
FILE_PATH = os.path.dirname(os.path.realpath(__file__))

log_formatter = logging.Formatter(
    fmt='%(asctime)s %(levelname)-8s %(user)-10s: %(message)s',
    datefmt='%d.%m %H:%M'
)

log_handler = TimedRotatingFileHandler(
    filename=os.path.join(FILE_PATH, 'logger.log'),
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
    record = old_factory(*args, **kwargs)
    # bypass flask no request context runtime error
    try:
        record.user = session.get("user_name", default="no_user")
    except RuntimeError:
        record.user = "no_user"
    return record

logging.setLogRecordFactory(record_factory)
# endregion
