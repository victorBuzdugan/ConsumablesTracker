from functools import wraps
from flask import session, redirect, url_for


def login_required(f):
    """Decorate routes to require login."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorate routes to require admin login."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None or not session.get("admin"):
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated_function