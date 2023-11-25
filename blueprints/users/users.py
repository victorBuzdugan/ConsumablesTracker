"""Users blueprint."""

from typing import Callable

from flask import Blueprint, flash, redirect, render_template, session, url_for
from flask_babel import gettext, lazy_gettext, ngettext
from flask_wtf import FlaskForm
from markupsafe import escape
from sqlalchemy import func, select
from wtforms import (BooleanField, EmailField, IntegerField, PasswordField,
                     SelectField, StringField, SubmitField, TextAreaField)
from wtforms.validators import (Email, InputRequired, Length, NumberRange,
                                Optional, Regexp)

from blueprints.sch import clean_sch_info, sat_sch_info
from blueprints.sch.sch import cleaning_sch
from constants import Constant
from database import User, dbSession
from helpers import admin_required, flash_errors, logger
from messages import Message

func: Callable

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
            InputRequired(Message.User.Name.Required()),
            Length(
                min=Constant.User.Name.min_length,
                max=Constant.User.Name.max_length,
                message=Message.User.Name.LenLimit())],
        render_kw={
            "class": "form-control",
            "placeholder": lazy_gettext("Username"),
            "autocomplete": "off",
            })
    password = PasswordField(
        label=lazy_gettext("Password"),
        validators=[
            InputRequired(Message.User.Password.Required()),
            Length(
                min=Constant.User.Password.min_length,
                message=Message.User.Password.LenLimit()),
            Regexp(
                Constant.User.Password.regex,
                message=Message.User.Password.Rules())],
        render_kw={
            "class": "form-control",
            "placeholder": lazy_gettext("Password"),
            "autocomplete": "new-password",
            })
    email = EmailField(
        label="Email",
        validators=[
            Optional(),
            Email(Message.User.Email.Invalid())],
        default="",
        render_kw={
            "class": "form-control",
            "placeholder": "Email",
            "autocomplete": "off",
            })
    sat_group = SelectField(
        label=sat_sch_info.name,
        validators=[
            NumberRange(
                min=1,
                max=2,
                message=Message.User.SatGroup.Invalid())],
        choices=[(1, lazy_gettext("Group 1")), (2, lazy_gettext("Group 2"))],
        coerce=int,
        default="1",
        render_kw={
                "class": "form-select",
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
        false_values = ("False", False, "false", ""),
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
                min=Constant.User.Password.min_length,
                message=Message.User.Password.LenLimit()),
            Regexp(
                Constant.User.Password.regex,
                message=Message.User.Password.Rules())],
        render_kw={
            "class": "form-control",
            "placeholder": lazy_gettext("Password"),
            "autocomplete": "new-password",
            })
    clean_order = SelectField(
        label=clean_sch_info.name,
        validators=[Optional()],
        coerce=int,
        default=None,
        render_kw={
                "class": "form-select",
                })
    all_products = IntegerField()
    in_use_products = IntegerField()
    in_use = BooleanField(
        label=lazy_gettext("In use"),
        false_values = ("False", False, "false", ""),
        render_kw={
                "class": "form-check-input",
                "role": "switch",
                })
    check_inv = BooleanField(
        label=lazy_gettext("Inventory check"),
        false_values = ("False", False, "false", ""),
        render_kw={
                "class": "form-check-input",
                "role": "switch",
                })
    reg_req = BooleanField(
        false_values = ("False", False, "false", ""),
        validators=[Optional()])
    req_inv = BooleanField(
        false_values = ("False", False, "false", ""),
        validators=[Optional()])
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
            cleaning_sch.add_user(user.id)
            flash(**Message.User.Approved.flash(username))
            flash(**Message.Schedule.Review.flash())
        else:
            logger.warning("User %s does not exist", username)
            flash(**Message.User.NotExists.flash(username))

    return redirect(session["last_url"])


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
            flash(**Message.User.NotExists.flash(username))

    return redirect(session["last_url"])


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
                    name=new_user_form.name.data,
                    password=new_user_form.password.data,
                    reg_req=False)
                new_user_form.populate_obj(user)
                db_session.add(user)
                db_session.commit()
                logger.debug("User '%s' created", user.name)
                cleaning_sch.add_user(user.id)
                flash(**Message.User.Created.flash(user.name))
                flash(**Message.Schedule.Review.flash())
                return redirect(url_for("main.index"))
            except ValueError as error:
                logger.warning("User creation error(s)")
                flash(str(error), "error")
    elif new_user_form.errors:
        logger.warning("User creation error(s)")
        flash_errors(new_user_form.errors)

    return render_template("users/new_user.html",
                           form=new_user_form,
                           Message=Message)


@users_bp.route("/edit/<path:username>", methods=["GET", "POST"])
def edit_user(username):
    """Edit user."""
    logger.info("Edit user '%s' page", username)
    edit_user_form: EditUserForm = EditUserForm()

    with dbSession() as db_session:
        user_len = db_session.scalar(
            select(func.count(User.id))
            .filter_by(reg_req=False, in_use=True))
    clean_order_choices = (
        [(0, gettext("This week"))] +
        [(ind, gettext("In") + f" {ind} " + ngettext("week", "weeks", ind))
            for ind in range(1, user_len)])
    edit_user_form.clean_order.choices = clean_order_choices

    if edit_user_form.validate_on_submit():
        with dbSession() as db_session:
            user = db_session.scalar(
                select(User)
                .filter_by(name=escape(username)))
            if edit_user_form.delete.data:
                if user.all_products:
                    flash(**Message.User.NoDelete.flash())
                else:
                    db_session.delete(user)
                    db_session.commit()
                    logger.debug("User '%s' has been deleted", username)
                    cleaning_sch.remove_user(user.id)
                    flash(**Message.User.Deleted.flash(user.name))
                    if user.id == session.get("user_id"):
                        return redirect(url_for("auth.logout"))
                    return redirect(session["last_url"])
            else:
                initial_in_use = user.in_use
                schedule_updated_flag = False
                try:
                    user.name = edit_user_form.name.data
                    if edit_user_form.password.data:
                        user.password = edit_user_form.password.data
                    user.email = edit_user_form.email.data
                    user.sat_group = edit_user_form.sat_group.data
                    # cleaning schedule
                    if user.in_use and not user.reg_req:
                        curr_pos = cleaning_sch.current_order()\
                                                .index(user.id)
                        if int(edit_user_form.clean_order.data) != curr_pos:
                            cleaning_sch.change_user_pos(
                                user.id,
                                edit_user_form.clean_order.data)
                            flash(**Message.Schedule.Updated.flash())
                            schedule_updated_flag = True
                    user.details = edit_user_form.details.data
                    user.admin = edit_user_form.admin.data
                    user.done_inv = not edit_user_form.check_inv.data
                    user.in_use = edit_user_form.in_use.data
                except TypeError:
                    flash(**Message.Schedule.InvalidChoice.flash())
                except ValueError as error:
                    flash(str(error), "error")
                else:
                    if db_session.is_modified(user, include_collections=False):
                        logger.debug("User updated")
                        flash(**Message.User.Updated.flash(user.name))
                        db_session.commit()
                        if  user.in_use is not initial_in_use:
                            # add or remove from schedule
                            if user.in_use:
                                cleaning_sch.add_user(user.id)
                            else:
                                cleaning_sch.remove_user(user.id)
                        if user.id == session.get("user_id"):
                            session["user_name"] = user.name
                            if not user.admin:
                                session["admin"] = False
                                return redirect(url_for("main.index"))
                        return redirect(session["last_url"])
                    if schedule_updated_flag:
                        return redirect(session["last_url"])
    elif edit_user_form.errors:
        logger.warning("User editing error(s)")
        flash_errors(edit_user_form.errors)

    with dbSession() as db_session:
        if (user := db_session.scalar(
                select(User)
                .filter(User.name==escape(username),
                        User.name!="Admin"))):
            edit_user_form = EditUserForm(obj=user)
            if user.in_use and not user.reg_req:
                edit_user_form.clean_order.choices = clean_order_choices
                edit_user_form.clean_order.data = \
                    cleaning_sch.current_order().index(user.id)
        else:
            flash(**Message.User.NotExists.flash(username))
            return redirect(url_for("main.index"))

    return render_template("users/edit_user.html",
                           form=edit_user_form,
                           Message=Message)
