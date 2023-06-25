"""Authentification module."""

from flask import Blueprint, flash, redirect, render_template, session, url_for, request, get_flashed_messages
from flask_wtf import FlaskForm
from sqlalchemy import select
from wtforms import StringField, PasswordField
from wtforms.validators import InputRequired, Length, EqualTo, Regexp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import login_required
from database import dbSession, User

auth_bp = Blueprint("auth",
                    __name__,
                    url_prefix="/auth",
                    template_folder="templates",
                    static_folder="static")

class LoginForm(FlaskForm):
    name = StringField(
        label="Username",
        validators=[InputRequired()])
    password = PasswordField(
        label="Password",
        validators=[InputRequired()])

class RegisterForm(FlaskForm):
    name = StringField(
        label="Username",
        validators=[InputRequired(),
                    Length(min=3, max=15)])
    password = PasswordField(
        label="Password",
        validators=[InputRequired(),
                    Length(min=8)])
    confirm = PasswordField(
        label="Retype password",
        validators=[InputRequired(),
                    Length(min=8),
                    EqualTo("password", "Passwords don't match!"),
                    Regexp("(?=.*\d)(?=.*[A-Z])(?=.*[!@#$%^&*_=+]).{8,}",
                           message="Check password rules!")])


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    login_form: LoginForm = LoginForm()
    if login_form.validate_on_submit():
        with dbSession() as db_session:
            user = db_session.scalar(
                select(User).filter_by(name=login_form.name.data))
        if user and check_password_hash(
                user.password, login_form.password.data):
            if user.in_use:
                if not user.reg_req:
                    session["user_id"] = user.id
                    session["admin"] = user.admin
                    session["user_name"] = user.name
                    flash(f"Welcome {user.name}")
                    return redirect(url_for("index"))
                else:
                    flash("You're registration is pending. Contact an admin.",
                          "warning")
            else:
                flash("This user is not in use anymore!", "warning")
        else:
            flash("Incorrect username or password!", "warning")
    elif login_form.errors:
        flash_errors = [error for errors in login_form.errors.values() \
                        for error in errors]
        for error in flash_errors:
            flash(error, "error")

    return render_template("auth/login.html", form=login_form)


@auth_bp.route("/logout")
@login_required
def logout():
    session.clear()
    flash("Succesfully logged out...")
    return redirect(url_for("auth.login"))


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    # if user is logged in
    if session.get("user_id"):
        session.clear()
        flash("You have been logged out...", "info")
        return redirect(url_for("auth.register"))
    
    reg_form: RegisterForm = RegisterForm()
    
    if reg_form.validate_on_submit():
        with dbSession() as db_session:
            user = db_session.scalar(
                select(User).filter_by(name=reg_form.name.data))
            if not user:
                user = User(
                    name=reg_form.name.data,
                    password=generate_password_hash(reg_form.password.data)
                )
                db_session.add(user)
                db_session.commit()
                flash("Registration request sent. Please contact an admin.")
                return redirect(url_for("auth.login"))
            else:
                flash("Username allready exists...", "warning")
    elif reg_form.errors:
        flash_errors = [error for errors in reg_form.errors.values() \
                        for error in errors]
        for error in flash_errors:
            flash(error, "error")
    
    return render_template("auth/register.html", form=reg_form)
