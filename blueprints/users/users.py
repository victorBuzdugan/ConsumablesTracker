"""Users blueprint."""

from flask import Blueprint, flash, redirect, render_template, session, url_for
from flask_wtf import FlaskForm
from markupsafe import escape
from sqlalchemy import select
from wtforms import (BooleanField, IntegerField, PasswordField, StringField,
                     SubmitField, TextAreaField)
from wtforms.validators import InputRequired, Length, Optional, Regexp

from blueprints.auth.auth import (PASSW_MIN_LENGTH, PASSW_REGEX, PASSW_SYMB,
                                  USER_MAX_LENGTH, USER_MIN_LENGTH, msg)
from database import User, dbSession
from helpers import admin_required, flash_errors

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


class CreateUserForm(FlaskForm):
    """Create user form."""
    name = StringField(
        label="Username",
        validators=[
            InputRequired(msg["usr_req"]),
            Length(
                min=USER_MIN_LENGTH,
                max=USER_MAX_LENGTH,
                message=msg["usr_len"])],
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
            Regexp(PASSW_REGEX, message=("Password must have 1 big letter, " +
                         f"1 number, 1 special char ({PASSW_SYMB})!"))],
        render_kw={
            "class": "form-control",
            "placeholder": "Password",
            })
    details = TextAreaField(
        label="Details",
        render_kw={
                "class": "form-control",
                "placeholder": "Details",
                "style": "height: 5rem",
                })
    admin = BooleanField(
        label="Admin",
        render_kw={
                "class": "form-check-input",
                "role": "switch",
                })
    submit = SubmitField(
        label="Create user",
        render_kw={"class": "btn btn-primary px-4"})


class EditUserForm(CreateUserForm):
    """Edit user form."""
    password = PasswordField(
        label="Password",
        validators=[
            Optional(),
            Length(
                min=PASSW_MIN_LENGTH,
                message=msg["psw_len"]),
            Regexp(PASSW_REGEX, message=("Password must have 1 big letter, " +
                         f"1 number, 1 special char ({PASSW_SYMB})!"))],
        render_kw={
            "class": "form-control",
            "placeholder": "Password",
            })
    all_products = IntegerField()
    in_use_products = IntegerField()
    in_use = BooleanField(
        label="In use",
        render_kw={
                "class": "form-check-input",
                "role": "switch",
                })
    check_inv = BooleanField(
        label="Inventory check",
        render_kw={
                "class": "form-check-input",
                "role": "switch",
                })
    reg_req = BooleanField(validators=[Optional()])
    req_inv = BooleanField(validators=[Optional()])
    submit = SubmitField(
        label="Update",
        render_kw={"class": "btn btn-primary px-4"})
    delete = SubmitField(
        label="Delete",
        render_kw={"class": "btn btn-danger"})


@users_bp.route("/<username>/approve-registration")
def approve_reg(username):
    """Approve registration of user `username`."""
    with dbSession() as db_session:
        if (user:= db_session.scalar(
                        select(User).filter_by(name=escape(username)))):
            try:
                user.reg_req = False
                db_session.commit()
                flash(f"{username} has been approved")
            except ValueError as error:
                flash(str(error))
        else:
            flash(f"{username} does not exist!", "error")

    return redirect(url_for("main.index"))

@users_bp.route("/<username>/approve-inventory-check")
def approve_check_inv(username):
    """Approve inventory check for user `username`."""
    with dbSession() as db_session:
        if (user:= db_session.scalar(
                        select(User).filter_by(name=escape(username)))):
            try:
                user.done_inv = False
                db_session.commit()
            except ValueError as error:
                flash(str(error))
        else:
            flash(f"{username} does not exist!", "error")

    return redirect(url_for("main.index"))

@users_bp.route("/approve-all-inventory-check")
def approve_check_inv_all():
    """Approve inventory check for all eligible users."""
    with dbSession() as db_session:
        users = db_session.scalars(
            select(User).filter_by(in_use=True, reg_req=False)).all()
        for user in users:
            if user.in_use_products:
                user.done_inv = False
        db_session.commit()

    return redirect(url_for("main.index"))

@users_bp.route("/user/new", methods=["GET", "POST"])
def new_user():
    """Create a new user."""
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
                flash(f"User '{user.name}' created")
                return redirect(url_for("main.index"))
            except ValueError as error:
                flash(str(error), "error")
    elif new_user_form.errors:
        flash_errors(new_user_form.errors)

    return render_template("users/new_user.html", form=new_user_form)
# TESTME
@users_bp.route("/<username>/edit", methods=["GET", "POST"])
def edit_user(username):
    """Edit user."""
    edit_user_form: EditUserForm = EditUserForm()
    
    if edit_user_form.validate_on_submit():
        with dbSession().no_autoflush as db_session:
            user = db_session.scalar(
                select(User).
                filter_by(name=escape(username)))
            if edit_user_form.delete.data:
                if user.all_products:
                    flash("Can't delete user! " +
                        "He is still responsible for some products!",
                        "error")
                else:
                    db_session.delete(user)
                    db_session.commit()
                    flash(f"User '{user.name}' has been deleted")
                    if user.id == session.get("user_id"):
                        return redirect(url_for("auth.logout"))
                    return redirect(url_for("main.index"))
            else:
                # parse first in_use
                try:
                    user.in_use = edit_user_form.in_use.data
                except ValueError as error:
                    flash(str(error), "warning")
                try:
                    user.name = edit_user_form.name.data
                    if session.get("user_id") == user.id:
                        session["user_name"] = edit_user_form.name.data
                except ValueError as error:
                    flash(str(error), "error")
                if edit_user_form.password.data:
                    user.password = edit_user_form.password.data
                user.details = edit_user_form.details.data
                try:
                    user.admin = edit_user_form.admin.data
                except ValueError as error:
                    flash(str(error), "warning")
                try:
                    user.done_inv = not edit_user_form.check_inv.data
                except ValueError as error:
                    flash(str(error), "warning")
                if db_session.is_modified(user):
                    flash("User updated")
                    db_session.commit()
                    if (session.get("user_id") == user.id and 
                        not user.admin):
                        return redirect(url_for("auth.logout"))
                return redirect(url_for("users.edit_user", username=user.name))
    elif edit_user_form.errors:
        flash_errors(edit_user_form.errors)

    with dbSession() as db_session:
        user = db_session.scalar(
            select(User).
            filter_by(name=escape(username)))
    if user:
        edit_user_form = EditUserForm(obj=user)
    else:
        flash(f"User '{username}' does not exist!", "error")
        return redirect(url_for("main.index"))

    return render_template("users/edit_user.html", form=edit_user_form)
