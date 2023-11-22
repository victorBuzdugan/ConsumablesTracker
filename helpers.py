"""Helpers module."""

import logging
from datetime import datetime
from functools import wraps
from logging.handlers import TimedRotatingFileHandler
from os import path
from zoneinfo import ZoneInfo

from flask import flash, redirect, session, url_for

from constants import Constant
from messages import Message

# region: logging configuration
log_formatter = logging.Formatter(
    fmt='%(tztime)s %(levelname)-8s %(user)-10s: %(message)s')

log_handler = TimedRotatingFileHandler(
    filename=path.join(Constant.Basic.current_dir, 'logger.log'),
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
        record.user = session.get("user_name", default="__x__")
    except RuntimeError:
        record.user = "_sys_"
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
        if session.get("user_id") is None:
            flash(**Message.UI.Auth.LoginReq.flash())
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorate routes to require admin login."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if (session.get("user_id") is None) or (not session.get("admin")):
            flash(**Message.UI.Auth.AdminReq.flash())
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated_function
# endregion


def flash_errors(form_errors: dict) -> None:
    """Flash all errors from form."""
    errors = [error for errors in form_errors.values() for error in errors]
    for error in errors:
        flash(error, "error")
