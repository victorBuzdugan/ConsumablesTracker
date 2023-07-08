"""Users blueprint."""

from flask import (Blueprint, flash, redirect, render_template, request,
                   session, url_for)
from flask_wtf import FlaskForm
from markupsafe import escape
from sqlalchemy import select
from sqlalchemy.orm import joinedload, raiseload

from database import User, dbSession
from helpers import admin_required

# TESTME
users_bp = Blueprint(
    "users",
    __name__,
    template_folder="templates")

# require admin logged in for all routes
@users_bp.before_request
@admin_required
def admin_logged_in():
    pass

@users_bp.route("/approve_<username>_registration")
def approve_reg(username):
    """Approve registration of user `username`."""
    with dbSession() as db_session:
        user = db_session.scalar(select(User).filter_by(name=escape(username)))
        if user:
            user.reg_req = False
            db_session.commit()
            flash(f"{username} has been approved")
        else:
            flash(f"{username} does not exist!", "error")

    return redirect(url_for("main.index"))

@users_bp.route("/approve_<username>_check_inventory")
def approve_check_inv(username):
    """Approve inventory check for user `username`."""
    with dbSession() as db_session:
        user = db_session.scalar(select(User).filter_by(name=escape(username)))
        if (user and
                user.in_use and
                not user.reg_req
                and len(user.products) > 0):
            user.done_inv = False
            # TESTME db rules auto-sets req_inv = False
            db_session.commit()
            flash(f"{username} inventory check has been approved")
        elif not user:
            flash(f"{username} does not exist!", "error")
        elif not user.in_use:
            flash(f"{username} is 'retired'", "warning")
        elif user.reg_req:
            flash(f"{username} is awaiting registration approval", "warning")
        else:
            flash(f"{username} has no products attached", "warning")

    return redirect(url_for("main.index"))

# TODO
@users_bp.route("/new_user")
def new_user():
    """Create a new user."""


    return render_template("users/new_user.html")
