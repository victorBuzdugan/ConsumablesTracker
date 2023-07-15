"""Authentification blueprint."""

from flask import Blueprint, flash, redirect, render_template, session, url_for
from flask_wtf import FlaskForm
from sqlalchemy import select
from werkzeug.security import check_password_hash
from wtforms import PasswordField, StringField, SubmitField
from wtforms.validators import EqualTo, InputRequired, Length, NoneOf, Regexp

from database import User, dbSession
from helpers import flash_errors, login_required

USER_MIN_LENGTH = 3
USER_MAX_LENGTH = 15
PASSW_MIN_LENGTH = 8
PASSW_REGEX = r"(?=.*\d)(?=.*[A-Z])(?=.*[!@#$%^&*_=+]).{8,}"
PASSW_SYMB = "!@#$%^&*_=+"
msg = {
    "usr_req": "Username is required!",
    "usr_len": (f"Username must be between {USER_MIN_LENGTH} and " +
                    f"{USER_MAX_LENGTH} characters!"),
    "usr_res": "Username is reserved!",
    "psw_req": "Password is required!",
    "psw_len": ("Password should have at least "
                            f"{PASSW_MIN_LENGTH} characters!"),
    "psw_rules": "Check password rules!",
    "psw_eq": "Passwords don't match!",
}

auth_bp = Blueprint("auth",
                    __name__,
                    url_prefix="/auth",
                    template_folder="templates",
                    static_folder="static")


class LoginForm(FlaskForm):
    """Login form."""
    name = StringField(
        label="Username",
        validators=[InputRequired(msg["usr_req"])],
        render_kw={
            "class": "form-control",
            "placeholder": "Username",
            "autocomplete": "off",
            })
    password = PasswordField(
        label="Password",
        validators=[InputRequired(msg["psw_req"])],
        render_kw={
            "class": "form-control",
            "placeholder": "Password",
            })
    submit = SubmitField(
        label="Log In",
        render_kw={
            "class": "btn btn-primary px-4",
            "disabled": ""})


class RegisterForm(FlaskForm):
    """Registration form."""
    name = StringField(
        label="Username",
        validators=[
            InputRequired(msg["usr_req"]),
            Length(
                min=USER_MIN_LENGTH,
                max=USER_MAX_LENGTH,
                message=msg["usr_len"]),
            NoneOf(("new_user", ), msg["usr_res"])],
        render_kw={
            "class": "form-control",
            "placeholder": "Username",
            "autocomplete": "off",
            })
    password = PasswordField(
        label="Password",
        validators=[
            InputRequired(msg["psw_req"]),
            Length(
                min=PASSW_MIN_LENGTH,
                message=msg["psw_len"]),
            Regexp(
                PASSW_REGEX,
                message=msg["psw_rules"])],
        render_kw={
            "class": "form-control",
            "placeholder": "Password",
            })
    confirm = PasswordField(
        label="Retype password",
        validators=[
            InputRequired(msg["psw_req"]),
            Length(
                min=PASSW_MIN_LENGTH,
                message=msg["psw_len"]),
            EqualTo("password", msg["psw_eq"])],
        render_kw={
            "class": "form-control",
            "placeholder": "Retype password",
            })
    submit = SubmitField(
        label="Request registration",
        render_kw={
            "class": "btn btn-primary px-4",
            "disabled": ""})


class ChgPasswForm(FlaskForm):
    """Change password form."""
    old_password = PasswordField(
        label="Old password",
        validators=[
            InputRequired(msg["psw_req"]),
            Length(
                min=PASSW_MIN_LENGTH,
                message=msg["psw_len"])],
        render_kw={
            "class": "form-control",
            "placeholder": "Old password",
            })
    password = PasswordField(
        label="New password",
        validators=[
            InputRequired(msg["psw_req"]),
            Length(
                min=PASSW_MIN_LENGTH,
                message=msg["psw_len"]),
            Regexp(
                PASSW_REGEX,
                message=msg["psw_rules"])],
        render_kw={
            "class": "form-control",
            "placeholder": "New password",
            })
    confirm = PasswordField(
        label="Retype password",
        validators=[
            InputRequired(msg["psw_req"]),
            Length(
                min=PASSW_MIN_LENGTH,
                message=msg["psw_len"]),
            EqualTo("password", msg["psw_eq"])],
        render_kw={
            "class": "form-control",
            "placeholder": "Retype password",
            })
    submit = SubmitField(
        label="Change password",
        render_kw={
            "class": "btn btn-primary px-4",
            "disabled": ""})


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
                    return redirect(url_for("main.index"))
                else:
                    flash("Your registration is pending. Contact an admin.",
                          "warning")
            else:
                flash("This user is not in use anymore!", "warning")
        else:
            flash("Wrong username or password!", "warning")
    elif login_form.errors:
        flash_errors(login_form.errors)

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
            user = User("new_user", "password")
            try:
                reg_form.populate_obj(user)
                db_session.add(user)
                db_session.commit()
                flash("Registration request sent. Please contact an admin.")
                return redirect(url_for("auth.login"))
            except ValueError as error:
                flash(str(error), "error")
    elif reg_form.errors:
        flash_errors(reg_form.errors)

    return render_template("auth/register.html", form=reg_form)


@auth_bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    """Change current user password."""
    
    chg_pass_form: ChgPasswForm = ChgPasswForm()

    if chg_pass_form.validate_on_submit():
        with dbSession() as db_session:
            user = db_session.get(User, session["user_id"])

            if check_password_hash(user.password, chg_pass_form.old_password.data):
                chg_pass_form.populate_obj(user)
                db_session.commit()
                session.clear()
                flash("Password changed.")
                return redirect(url_for("auth.login"))
            else:
                flash("Wrong old password!", "error")
    elif chg_pass_form.errors:
        flash_errors(chg_pass_form.errors)

    return render_template("auth/change_password.html", form=chg_pass_form)
