"""Users blueprint."""

from flask import (Blueprint, flash, redirect, render_template, request,
                   session, url_for)
from flask_wtf import FlaskForm
from markupsafe import escape
from sqlalchemy import select
from sqlalchemy.orm import joinedload, raiseload
from wtforms import PasswordField, StringField, BooleanField, SubmitField, TextAreaField, IntegerField
from wtforms.validators import EqualTo, InputRequired, Length, Regexp, Optional

from database import User, Product, dbSession
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


# TODO: refactor with render_kw and other details
class CreateUserForm(FlaskForm):
    """Create user form."""
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
                message=("Password must have 1 big letter, " +
                         "1 number, 1 special char (!@#$%^&*_=+)!"))])
    admin = BooleanField(label="Admin")
    details = TextAreaField(label="Details")
    submit = SubmitField(label="Create user")


class EditUserForm(FlaskForm):
    """Edit user form."""
    name = StringField(
        label="Username",
        validators=[
            InputRequired("Username is required!"),
            Length(
                min=3,
                max=15,
                message="Username must be between 3 and 15 characters!")],
        render_kw={
            "class": "form-control",
            "placeholder": "Username",
            "autocomplete": "off",
            })
    password = PasswordField(
        label="Password",
        validators=[
            Optional(),
            Length(
                min=8,
                message="Password should have at least 8 characters!"),
            Regexp(
                r"(?=.*\d)(?=.*[A-Z])(?=.*[!@#$%^&*_=+]).{8,}",
                message=("Password must have 1 big letter, " +
                         "1 number, 1 special char (!@#$%^&*_=+)!"))],
        render_kw={
            "class": "form-control",
            "placeholder": "Password",
            })
    all_products = IntegerField()
    in_use_products = IntegerField()
    admin = BooleanField(
        label="Admin",
        render_kw={
                "class": "form-check-input",
                "role": "switch",
                })
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
    details = TextAreaField(
        label="Details",
        render_kw={
                "class": "form-control",
                "placeholder": "Details",
                "style": "height: 5rem",
                })
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
        user = db_session.scalar(select(User).filter_by(name=escape(username)))
        if user:
            user.reg_req = False
            db_session.commit()
            flash(f"{username} has been approved")
        else:
            flash(f"{username} does not exist!", "error")

    return redirect(url_for("main.index"))

@users_bp.route("/<username>/approve-inventory-check")
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

# TODO redesign
@users_bp.route("/user/new", methods=["GET", "POST"])
def new_user():
    """Create a new user."""
    new_user_form: CreateUserForm = CreateUserForm()
    if new_user_form.validate_on_submit():
        with dbSession() as db_session:
            # check if user exists
            user = db_session.scalar(
                select(User).filter_by(name=new_user_form.name.data))
            if not user:
                user = User(
                    name=new_user_form.name.data,
                    password=new_user_form.password.data,
                    admin=new_user_form.admin.data,
                    reg_req=False,
                    details=new_user_form.details.data
                )
                db_session.add(user)
                db_session.commit()
                flash(f"User {user.name} created")
                return redirect(url_for("main.index"))
            else:
                flash("Username allready exists...", "warning")
    elif new_user_form.errors:
        flash_errors(new_user_form.errors)

    return render_template("users/new_user.html", form=new_user_form)

# TODO
@users_bp.route("/<username>/edit", methods=["GET", "POST"])
def edit_user(username):
    """Edit user."""
    edit_user_form: EditUserForm = EditUserForm()
    
    if edit_user_form.validate_on_submit():
        # TODO
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
                try:
                    user.in_use = edit_user_form.in_use.data
                except ValueError as error:
                    flash(str(error), "warning")
                if db_session.is_modified(user):
                    flash("User updated")
                    db_session.commit()
                    if (session.get("user_id") == user.id and 
                        not user.admin):
                        return redirect(url_for("auth.logout"))
                    return redirect(
                        url_for("users.edit_user", username=user.name))
    elif edit_user_form.errors:
        flash_errors(edit_user_form.errors)

    with dbSession() as db_session:
        user = db_session.scalar(
            select(User).
            filter_by(name=escape(username)))
    if user:
        edit_user_form = EditUserForm(obj=user)
        # on 'POST' WTForms defaults to blank input if values were not posted
        edit_user_form.reg_req.data = user.reg_req
        edit_user_form.req_inv.data = user.req_inv
        edit_user_form.check_inv.data = user.check_inv
        edit_user_form.admin.data = user.admin
        edit_user_form.in_use.data = user.in_use
    else:
        flash(f"User '{username}' does not exist!", "error")
        return redirect(url_for("main.index"))

    return render_template("users/edit_user.html", form=edit_user_form)

