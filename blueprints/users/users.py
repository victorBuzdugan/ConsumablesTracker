"""Users blueprint."""

from flask import Blueprint, flash, redirect, render_template, session, url_for
from flask_babel import gettext, lazy_gettext
from flask_wtf import FlaskForm
from markupsafe import escape
from sqlalchemy import select
from wtforms import (BooleanField, EmailField, IntegerField, PasswordField,
                     StringField, SubmitField, TextAreaField)
from wtforms.validators import Email, InputRequired, Length, Optional, Regexp

from blueprints.auth.auth import (PASSW_MIN_LENGTH, PASSW_REGEX, PASSW_SYMB,
                                  USER_MAX_LENGTH, USER_MIN_LENGTH, msg)
from database import User, dbSession
from helpers import admin_required, flash_errors, logger

users_bp = Blueprint(
    "users",
    __name__,
    url_prefix="/user",
    template_folder="templates")


@users_bp.before_request
@admin_required
def admin_logged_in():
    """Require admin logged in for all routes."""


class CreateUserForm(FlaskForm):
    """Create user form."""
    name = StringField(
        label=lazy_gettext("Username"),
        validators=[
            InputRequired(msg["usr_req"]),
            Length(
                min=USER_MIN_LENGTH,
                max=USER_MAX_LENGTH,
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
                min=PASSW_MIN_LENGTH,
                message=msg["psw_len"]),
            Regexp(PASSW_REGEX, message=(
                gettext("Password must have 1 big letter, " +
                "1 number, 1 special char (%(passw_symb)s)!",
                passw_symb=PASSW_SYMB)))],
        render_kw={
            "class": "form-control",
            "placeholder": lazy_gettext("Password"),
            "autocomplete": "new-password",
            })
    email = EmailField(
        label="Email",
        validators=[
            Optional(),
            Email(gettext("Invalid email adress"))],
        default="",
        render_kw={
            "class": "form-control",
            "placeholder": "Email",
            "autocomplete": "off",
            })
    details = TextAreaField(
        label=lazy_gettext("Details"),
        render_kw={
                "class": "form-control",
                "placeholder": lazy_gettext("Details"),
                "style": "height: 5rem",
                "autocomplete": "off",
                })
    admin = BooleanField(
        label=lazy_gettext("Admin"),
        render_kw={
                "class": "form-check-input",
                "role": "switch",
                })
    submit = SubmitField(
        label=lazy_gettext("Create user"),
        render_kw={"class": "btn btn-primary px-4"})


class EditUserForm(CreateUserForm):
    """Edit user form."""
    password = PasswordField(
        label=lazy_gettext("Password"),
        validators=[
            Optional(),
            Length(
                min=PASSW_MIN_LENGTH,
                message=msg["psw_len"]),
            Regexp(PASSW_REGEX, message=(
                gettext("Password must have 1 big letter, " +
                "1 number, 1 special char (%(passw_symb)s)!",
                passw_symb=PASSW_SYMB)))],
        render_kw={
            "class": "form-control",
            "placeholder": lazy_gettext("Password"),
            "autocomplete": "new-password",
            })
    all_products = IntegerField()
    in_use_products = IntegerField()
    in_use = BooleanField(
        label=lazy_gettext("In use"),
        render_kw={
                "class": "form-check-input",
                "role": "switch",
                })
    check_inv = BooleanField(
        label=lazy_gettext("Inventory check"),
        render_kw={
                "class": "form-check-input",
                "role": "switch",
                })
    reg_req = BooleanField(validators=[Optional()])
    req_inv = BooleanField(validators=[Optional()])
    submit = SubmitField(
        label=lazy_gettext("Update"),
        render_kw={"class": "btn btn-primary px-4"})
    delete = SubmitField(
        label=lazy_gettext("Delete"),
        render_kw={"class": "btn btn-danger"})


@users_bp.route("/approve-registration/<path:username>")
def approve_reg(username):
    """Approve registration of user `username`."""
    with dbSession() as db_session:
        if (user := db_session.scalar(
                        select(User).filter_by(name=escape(username)))):
            user.reg_req = False
            db_session.commit()
            logger.debug("%s has been approved", username)
            flash(gettext("%(username)s has been approved",
                          username=username))
        else:
            logger.warning("%s does not exist", username)
            flash(gettext("%(username)s does not exist!",
                          username=username), "error")

    return redirect(url_for("main.index"))


@users_bp.route("/approve-inventory-check/<path:username>")
def approve_check_inv(username):
    """Approve inventory check for user `username`."""
    with dbSession() as db_session:
        if (user := db_session.scalar(
                        select(User).filter_by(name=escape(username)))):
            try:
                user.done_inv = False
                db_session.commit()
                logger.debug("Inventory check approved for %s", username)
            except ValueError as error:
                logger.warning("User inventory check approval error(s)")
                flash(str(error))
        else:
            logger.warning("User inventory check approval error(s)")
            flash(gettext("%(username)s does not exist!",
                          username=username), "error")

    return redirect(url_for("main.index"))


@users_bp.route("/all-approve-inventory-check")
def approve_check_inv_all():
    """Approve inventory check for all eligible users."""
    with dbSession() as db_session:
        users = db_session.scalars(
            select(User).filter_by(in_use=True, reg_req=False)).all()
        for user in users:
            if user.in_use_products:
                user.done_inv = False
        db_session.commit()
        logger.debug("Approved inventory check for all")

    return redirect(url_for("main.index"))


@users_bp.route("/new", methods=["GET", "POST"])
def new_user():
    """Create a new user."""
    logger.info("New user page")
    new_user_form: CreateUserForm = CreateUserForm()
    if new_user_form.validate_on_submit():
        with dbSession() as db_session:
            try:
                user = User(
                    new_user_form.name.data,
                    new_user_form.password.data,
                    reg_req=False)
                new_user_form.populate_obj(user)
                db_session.add(user)
                db_session.commit()
                logger.debug("User '%s' created", user.name)
                flash(gettext("User '%(username)s' created",
                              username=user.name))
                return redirect(url_for("main.index"))
            except ValueError as error:
                logger.warning("User creation error(s)")
                flash(str(error), "error")
    elif new_user_form.errors:
        logger.warning("User creation error(s)")
        flash_errors(new_user_form.errors)

    return render_template("users/new_user.html", form=new_user_form)


@users_bp.route("/edit/<path:username>", methods=["GET", "POST"])
def edit_user(username):
    """Edit user."""
    logger.info("Edit user '%s' page", username)
    edit_user_form: EditUserForm = EditUserForm()

    if edit_user_form.validate_on_submit():
        with dbSession().no_autoflush as db_session:
            user = db_session.scalar(
                select(User)
                .filter_by(name=escape(username)))
            if edit_user_form.delete.data:
                if user.all_products:
                    flash(gettext("Can't delete user! " +
                          "He is still responsible for some products!"),
                          "error")
                else:
                    db_session.delete(user)
                    db_session.commit()
                    logger.debug("User '%s' has been deleted", username)
                    flash(gettext("User '%(username)s' has been deleted",
                                  username=user.name))
                    if user.id == session.get("user_id"):
                        return redirect(url_for("auth.logout"))
                    return redirect(url_for("main.index"))
            else:
                try:
                    user.name = edit_user_form.name.data
                except ValueError as error:
                    flash(str(error), "error")
                if edit_user_form.password.data:
                    user.password = edit_user_form.password.data
                user.email = edit_user_form.email.data
                user.details = edit_user_form.details.data
                try:
                    user.admin = edit_user_form.admin.data
                except ValueError as error:
                    flash(str(error), "warning")
                try:
                    user.done_inv = not edit_user_form.check_inv.data
                except ValueError as error:
                    flash(str(error), "warning")
                try:
                    user.in_use = edit_user_form.in_use.data
                except ValueError as error:
                    flash(str(error), "warning")
                if db_session.is_modified(user, include_collections=False):
                    logger.debug("User updated")
                    flash(gettext("User updated"))
                    db_session.commit()
                    if user.id == session.get("user_id"):
                        session["user_name"] = user.name
                        if not user.admin:
                            session["admin"] = False
                            return redirect(url_for("main.index"))
                return redirect(url_for("users.edit_user", username=user.name))
    elif edit_user_form.errors:
        logger.warning("User editing error(s)")
        flash_errors(edit_user_form.errors)

    with dbSession() as db_session:
        if (user := db_session.scalar(
                select(User)
                .filter(User.name==escape(username),
                        User.name!="Admin"))):
            edit_user_form = EditUserForm(obj=user)
        else:
            flash(gettext("%(username)s does not exist!",
                          username=username), "error")
            return redirect(url_for("main.index"))

    return render_template("users/edit_user.html", form=edit_user_form)
