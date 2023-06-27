from functools import wraps
from flask import session, redirect, url_for, flash


def login_required(f):
    """Decorate routes to require login."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            flash("You have to be logged in...", "warning")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorate routes to require admin login."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None or not session.get("admin"):
            flash("You have to be an admin...", "warning")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated_function