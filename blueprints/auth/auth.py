"""Authentification module."""

from flask import Blueprint, flash, redirect, render_template, session, url_for

from helpers import login_required

auth_bp = Blueprint('auth', __name__, template_folder='templates')

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Login page."""
    return render_template("auth/login.html")

@auth_bp.route("/logout")
@login_required
def logout():
    session.pop("username", None)
    flash("Succesfully logged out")
    return redirect(url_for("index"))