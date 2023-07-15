from functools import wraps
from flask import session, redirect, url_for, flash


def login_required(f):
    """Decorate routes to require login."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("user_id"):
            flash("You have to be logged in...", "warning")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorate routes to require admin login."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("user_id") or not session.get("admin"):
            flash("You have to be an admin...", "warning")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated_function

def flash_errors(form_errors: dict) -> None:
    flash_errors = [error for errors in form_errors.values()
                    for error in errors]
    for error in flash_errors:
        flash(error, "error")