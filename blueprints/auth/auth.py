"""Authentification blueprint."""

from flask import (Blueprint, flash, redirect, render_template, request,
                   session, url_for)
from flask_babel import gettext, lazy_gettext
from flask_wtf import FlaskForm
from sqlalchemy import select
from werkzeug.security import check_password_hash
from wtforms import EmailField, PasswordField, StringField, SubmitField
from wtforms.validators import (Email, EqualTo, InputRequired, Length,
                                Optional, Regexp)

from constants import Constant
from database import User, dbSession
from helpers import flash_errors, logger, login_required

msg = {
    "usr_req": lazy_gettext("Username is required!"),
    "usr_len": lazy_gettext(
        "Username must be between %(m)i and %(M)i characters!",
        m=Constant.User.Name.min_length, M=Constant.User.Name.max_length),
    "psw_req": lazy_gettext("Password is required!"),
    "psw_len": lazy_gettext(
        "Password should have at least %(pmin)i characters!",
        pmin=Constant.User.Password.min_length),
    "psw_rules": lazy_gettext("Check password rules!"),
    "psw_eq": lazy_gettext("Passwords don't match!"),
}

auth_bp = Blueprint("auth",
                    __name__,
                    url_prefix="/auth",
                    template_folder="templates",
                    static_folder="static")


class LoginForm(FlaskForm):
    """Login form."""
    name = StringField(
        label=lazy_gettext("Username"),
        validators=[InputRequired(msg["usr_req"])],
        render_kw={
            "class": "form-control",
            "placeholder": lazy_gettext("Username"),
            })
    password = PasswordField(
        label=lazy_gettext("Password"),
        validators=[InputRequired(msg["psw_req"])],
        render_kw={
            "class": "form-control",
            "placeholder": lazy_gettext("Password"),
            })
    submit = SubmitField(
        label="Log In",
        render_kw={
            "class": "btn btn-primary px-4",
            "disabled": ""})


class RegisterForm(FlaskForm):
    """Registration form."""
    name = StringField(
        label=lazy_gettext("Username"),
        validators=[
            InputRequired(msg["usr_req"]),
            Length(
                min=Constant.User.Name.min_length,
                max=Constant.User.Name.max_length,
                message=msg["usr_len"])],
        render_kw={
            "class": "form-control",
            "placeholder": lazy_gettext("Username"),
            "autocomplete": "off",
            })
    password = PasswordField(
        label=lazy_gettext("Password"),
        validators=[
            InputRequired(msg["psw_req"]),
            Length(
                min=Constant.User.Password.min_length,
                message=msg["psw_len"]),
            Regexp(
                Constant.User.Password.regex,
                message=msg["psw_rules"])],
        render_kw={
            "class": "form-control",
            "placeholder": lazy_gettext("Password"),
            "autocomplete": "new-password",
            })
    confirm = PasswordField(
        label=lazy_gettext("Retype password"),
        validators=[
            InputRequired(msg["psw_req"]),
            Length(
                min=Constant.User.Password.min_length,
                message=msg["psw_len"]),
            EqualTo("password", msg["psw_eq"])],
        render_kw={
            "class": "form-control",
            "placeholder": lazy_gettext("Retype password"),
            "autocomplete": "new-password",
            })
    email = EmailField(
        label="Email",
        default=None,
        validators=[
            Optional(),
            Email(gettext("Invalid email adress"))],
        render_kw={
            "class": "form-control",
            "placeholder": "Email",
            "autocomplete": "off",
            })
    submit = SubmitField(
        label=lazy_gettext("Request registration"),
        render_kw={
            "class": "btn btn-primary px-4",
            "disabled": ""})


class ChgPasswForm(FlaskForm):
    """Change password form."""
    old_password = PasswordField(
        label=lazy_gettext("Old password"),
        validators=[
            InputRequired(msg["psw_req"]),
            Length(
                min=Constant.User.Password.min_length,
                message=msg["psw_len"])],
        render_kw={
            "class": "form-control",
            "placeholder": lazy_gettext("Old password"),
            "autocomplete": "current-password",
            })
    password = PasswordField(
        label=lazy_gettext("New password"),
        validators=[
            InputRequired(msg["psw_req"]),
            Length(
                min=Constant.User.Password.min_length,
                message=msg["psw_len"]),
            Regexp(
                Constant.User.Password.regex,
                message=msg["psw_rules"])],
        render_kw={
            "class": "form-control",
            "placeholder": lazy_gettext("New password"),
            "autocomplete": "new-password",
            })
    confirm = PasswordField(
        label=lazy_gettext("Retype password"),
        validators=[
            InputRequired(msg["psw_req"]),
            Length(
                min=Constant.User.Password.min_length,
                message=msg["psw_len"]),
            EqualTo("password", msg["psw_eq"])],
        render_kw={
            "class": "form-control",
            "placeholder": lazy_gettext("Retype password"),
            "autocomplete": "new-password",
            })
    submit = SubmitField(
        label=lazy_gettext("Change password"),
        render_kw={
            "class": "btn btn-primary px-4",
            "disabled": ""})


def clear_session():
    """Clear the session."""
    language = session.get("language")
    session.clear()
    if language:
        session["language"] = language


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Login user if conditions are met."""
    logger.info("Login page")
    login_form: LoginForm = LoginForm()
    if login_form.validate_on_submit():
        with dbSession() as db_session:
            user = db_session.scalar(
                select(User).filter_by(name=login_form.name.data))
        if user and check_password_hash(
                user.password, login_form.password.data):
            if user.in_use or user.name == "Admin":
                if not user.reg_req:
                    language = session.get("language")
                    session.clear()
                    session["user_id"] = user.id
                    session["admin"] = user.admin
                    session["user_name"] = user.name
                    if language:
                        session["language"] = language
                    flash(gettext("Welcome %(username)s", username=user.name))
                    return redirect(url_for("main.index"))
                else:
                    flash(gettext("Your registration is pending. " +
                                  "Contact an admin."), "warning")
            else:
                flash(gettext("This user is not in use anymore!"), "warning")
        else:
            logger.warning("Bad login credentials for user '%s'",
                           login_form.name.data)
            flash(gettext("Wrong username or password!"), "warning")
    elif login_form.errors:
        flash_errors(login_form.errors)

    # redirect instead of render to avoid javascript glitches
    if request.method == "POST":
        return redirect(url_for(".login", form=login_form))

    return render_template("auth/login.html", form=login_form)


@auth_bp.route("/logout")
@login_required
def logout():
    """Logout and clear session."""
    logger.info("Logging out")
    clear_session()
    flash(gettext("Succesfully logged out..."))
    return redirect(url_for(".login"))


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """Register user if conditions are met."""
    logger.info("Register page")
    # if user is logged in
    if session.get("user_id"):
        session.clear()
        flash(gettext("You have been logged out..."), "info")

    reg_form: RegisterForm = RegisterForm()

    if reg_form.validate_on_submit():
        with dbSession() as db_session:
            try:
                user = User(
                    name=reg_form.name.data,
                    password=reg_form.password.data)
                reg_form.populate_obj(user)
                db_session.add(user)
                db_session.commit()
                logger.debug("Registration requested")
                flash(gettext("Registration request sent. " +
                              "Please contact an admin."))
                return redirect(url_for(".login"))
            except ValueError as error:
                flash(str(error), "error")
    elif reg_form.errors:
        logger.warning("Bad registration data")
        flash_errors(reg_form.errors)

    return render_template("auth/register.html", form=reg_form)


@auth_bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    """Change current user password."""
    logger.info("Change password page")

    chg_pass_form: ChgPasswForm = ChgPasswForm()

    if chg_pass_form.validate_on_submit():
        with dbSession() as db_session:
            user = db_session.get(User, session["user_id"])

            if check_password_hash(
                    user.password, chg_pass_form.old_password.data):
                chg_pass_form.populate_obj(user)
                db_session.commit()
                clear_session()
                logger.debug("Password changed")
                flash(gettext("Password changed."))
                return redirect(url_for(".login"))
            else:
                logger.warning("Wrong old password")
                flash(gettext("Wrong old password!"), "error")
    elif chg_pass_form.errors:
        logger.warning("Change password error(s)")
        flash_errors(chg_pass_form.errors)

    return render_template("auth/change_password.html", form=chg_pass_form)
