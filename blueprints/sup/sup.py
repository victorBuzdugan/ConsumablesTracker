"""Suppliers blueprint."""

from typing import Callable

from flask import Blueprint, flash, redirect, render_template, url_for
from flask_babel import gettext, lazy_gettext
from flask_wtf import FlaskForm
from markupsafe import escape
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload, raiseload
from wtforms import (BooleanField, IntegerField, StringField, SubmitField,
                     TextAreaField)
from wtforms.validators import InputRequired, Length

from database import Supplier, dbSession
from helpers import admin_required, flash_errors

func: Callable

sup_bp = Blueprint(
    "sup",
    __name__,
    url_prefix="/supplier",
    template_folder="templates")


@sup_bp.before_request
@admin_required
def admin_logged_in():
    """Require admin logged in for all routes."""


class CreateSupForm(FlaskForm):
    """Create supplier form."""
    name = StringField(
        label=lazy_gettext("Name"),
        validators=[
            InputRequired(gettext("Supplier name is required")),
            Length(
                min=3,
                message=gettext("Supplier name must have at least 3 characters"))],
        render_kw={
            "class": "form-control",
            "placeholder": lazy_gettext("Username"),
            "autocomplete": "off",
            })
    details = TextAreaField(
        label=lazy_gettext("Details"),
        render_kw={
                "class": "form-control",
                "placeholder": lazy_gettext("Details"),
                "style": "height: 5rem",
                })
    submit = SubmitField(
        label=lazy_gettext("Create supplier"),
        render_kw={"class": "btn btn-primary px-4"})


class EditSupForm(CreateSupForm):
    """Edit supplier form."""
    all_products = IntegerField()
    in_use_products = IntegerField()
    in_use = BooleanField(
        label=lazy_gettext("In use"),
        render_kw={
                "class": "form-check-input",
                "role": "switch",
                })
    submit = SubmitField(
        label=lazy_gettext("Update"),
        render_kw={"class": "btn btn-primary px-4"})
    delete = SubmitField(
        label=lazy_gettext("Delete"),
        render_kw={"class": "btn btn-danger"})


@sup_bp.route("/suppliers")
def suppliers():
    """All suppliers page."""
    with dbSession() as db_session:
        supps = db_session.scalars(
                select(Supplier).
                order_by(Supplier.in_use.desc(), func.lower(Supplier.name)).
                options(joinedload(Supplier.products), raiseload("*"))
                ).unique().all()
        stats = {
            "all_suppliers": db_session.scalar(
                select(func.count(Supplier.id))),
            "in_use_suppliers": db_session.scalar(
                select(func.count(Supplier.id))
                .filter_by(in_use=True)),
        }
    return render_template(
        "sup/suppliers.html",
        suppliers=supps,
        stats=stats)


@sup_bp.route("/new", methods=["GET", "POST"])
def new_supplier():
    """Create a new supplier."""
    new_sup_form: CreateSupForm = CreateSupForm()
    if new_sup_form.validate_on_submit():
        with dbSession() as db_session:
            try:
                supplier = Supplier(new_sup_form.name.data)
                new_sup_form.populate_obj(supplier)
                db_session.add(supplier)
                db_session.commit()
                flash(gettext("Supplier '%(supplier_name)s' created",
                              supplier_name=supplier.name))
                return redirect(url_for("sup.suppliers"))
            except ValueError as error:
                flash(str(error), "error")
    elif new_sup_form.errors:
        flash_errors(new_sup_form.errors)

    return render_template("sup/new_supplier.html", form=new_sup_form)


@sup_bp.route("/<path:supplier>/edit", methods=["GET", "POST"])
def edit_supplier(supplier):
    """Edit supplier."""
    edit_sup_form: EditSupForm = EditSupForm()

    if edit_sup_form.validate_on_submit():
        with dbSession().no_autoflush as db_session:
            sup = db_session.scalar(
                select(Supplier)
                .filter_by(name=escape(supplier)))
            if edit_sup_form.delete.data:
                if sup.all_products:
                    flash(gettext("Can't delete supplier! " +
                          "There are still products attached!"),
                          "error")
                else:
                    db_session.delete(sup)
                    db_session.commit()
                    flash(gettext("Supplier '%(sup_name)s' has been deleted",
                                  sup_name=sup.name))
                    return redirect(url_for("sup.suppliers"))
            else:
                try:
                    sup.name = edit_sup_form.name.data
                except ValueError as error:
                    flash(str(error), "error")
                sup.details = edit_sup_form.details.data
                try:
                    sup.in_use = edit_sup_form.in_use.data
                except ValueError as error:
                    flash(str(error), "warning")
                if db_session.is_modified(sup, include_collections=False):
                    flash(gettext("Supplier updated"))
                    db_session.commit()
                return redirect(
                    url_for("sup.edit_supplier", supplier=sup.name))
    elif edit_sup_form.errors:
        flash_errors(edit_sup_form.errors)

    with dbSession() as db_session:
        if (sup := db_session.scalar(
                select(Supplier)
                .filter_by(name=escape(supplier)))):
            edit_sup_form = EditSupForm(obj=sup)
        else:
            # flash(f"{supplier} does not exist!", "error")
            flash(gettext("%(supplier)s does not exist!",
                          supplier=supplier), "error")
            return redirect(url_for("sup.suppliers"))

    return render_template("sup/edit_supplier.html", form=edit_sup_form)
