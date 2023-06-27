"""Authentification module."""

from flask import Blueprint, flash, redirect, render_template, session, url_for
from flask_wtf import FlaskForm
from sqlalchemy import select
from werkzeug.security import check_password_hash, generate_password_hash
from wtforms import PasswordField, StringField
from wtforms.validators import EqualTo, InputRequired, Length, Regexp

from database import User, dbSession
from helpers import login_required

auth_bp = Blueprint("auth",
                    __name__,
                    url_prefix="/auth",
                    template_folder="templates",
                    static_folder="static")


class LoginForm(FlaskForm):
    """Login form."""
    name = StringField(
        label="Username",
        validators=[InputRequired("Username is required!")])
    password = PasswordField(
        label="Password",
        validators=[InputRequired("Password is required!")])


class RegisterForm(FlaskForm):
    """Registration form."""
    name = StringField(
        label="Username",
        validators=[
            InputRequired("Username is required!"),
            Length(
                min=3,
                max=15,
                message="Username must be between 3 and 15 characters!")])
    password = PasswordField(
        label="Password",
        validators=[
            InputRequired("Password is required!"),
            Length(
                min=8,
                message="Password should have at least 8 characters!"),
            Regexp(
                r"(?=.*\d)(?=.*[A-Z])(?=.*[!@#$%^&*_=+]).{8,}",
                message="Check password rules!")])
    confirm = PasswordField(
        label="Retype password",
        validators=[
            InputRequired("Confirmation password is required!"),
            Length(
                min=8,
                message="Password should have at least 8 characters!"),
            EqualTo("password", "Passwords don't match!")])


class ChgPasswForm(FlaskForm):
    """Change password form."""
    old_password = PasswordField(
        label="Old password",
        validators=[
            InputRequired("Old password is required!"),
            Length(
                min=8,
                message="Password should have at least 8 characters!")])
    password = PasswordField(
        label="New password",
        validators=[
            InputRequired("New password is required!"),
            Length(
                min=8,
                message="Password should have at least 8 characters!"),
            Regexp(
                r"(?=.*\d)(?=.*[A-Z])(?=.*[!@#$%^&*_=+]).{8,}",
                message="Check password rules!")])
    confirm = PasswordField(
        label="Retype password",
        validators=[
            InputRequired("Confirmation password is required!"),
            Length(
                min=8,
                message="Password should have at least 8 characters!"),
            EqualTo("password", "Passwords don't match!")])


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Login user if conditions are met."""
    login_form: LoginForm = LoginForm()
    if login_form.validate_on_submit():
        with dbSession() as db_session:
            user = db_session.scalar(
                select(User).filter_by(name=login_form.name.data))
        if user and check_password_hash(
                user.password, login_form.password.data):
            if user.in_use:
                if not user.reg_req:
                    session.clear()
                    session["user_id"] = user.id
                    session["admin"] = user.admin
                    session["user_name"] = user.name
                    flash(f"Welcome {user.name}")
                    return redirect(url_for("index"))
                else:
                    flash("Your registration is pending. Contact an admin.",
                          "warning")
            else:
                flash("This user is not in use anymore!", "warning")
        else:
            flash("Wrong username or password!", "warning")
    elif login_form.errors:
        flash_errors = [error for errors in login_form.errors.values()
                        for error in errors]
        for error in flash_errors:
            flash(error, "error")

    return render_template("auth/login.html", form=login_form)


@auth_bp.route("/logout")
@login_required
def logout():
    """Logout and clear session."""
    session.clear()
    flash("Succesfully logged out...")
    return redirect(url_for("auth.login"))


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """Register user if conditions are met."""
    # if user is logged in
    if session.get("user_id"):
        session.clear()
        print("flash")
        flash("You have been logged out...", "info")

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
        flash_errors = [error for errors in reg_form.errors.values()
                        for error in errors]
        for error in flash_errors:
            flash(error, "error")

    return render_template("auth/register.html", form=reg_form)

@auth_bp.route("/change_password", methods=["GET", "POST"])
@login_required
def change_password():
    """Change current user password."""
    
    chg_pass: ChgPasswForm = ChgPasswForm()

    if chg_pass.validate_on_submit():
        with dbSession() as db_session:
            user = db_session.get(User, session["user_id"])

            if check_password_hash(user.password, chg_pass.old_password.data):
                user.password = generate_password_hash(chg_pass.password.data)
                db_session.commit()
                session.clear()
                flash("Password changed.")
                return redirect(url_for("auth.login"))
            else:
                flash("Wrong old password!", "error")
    elif chg_pass.errors:
        flash_errors = [error for errors in chg_pass.errors.values()
                        for error in errors]
        for error in flash_errors:
            flash(error, "error")

    return render_template("auth/change_password.html", form=chg_pass)
