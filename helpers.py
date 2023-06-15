"""Helpers functions."""

from functools import wraps
from flask import redirect, url_for, session


def login_required(f):
    """Decorate routes to require login."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Decorate routes to require admin login."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None or session.get("admin") is None:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function