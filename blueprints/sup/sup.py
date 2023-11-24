"""Suppliers blueprint."""

from typing import Callable

from flask import Blueprint, flash, redirect, render_template, session, url_for
from flask_babel import lazy_gettext
from flask_wtf import FlaskForm
from markupsafe import escape
from sqlalchemy import func, select
from sqlalchemy.orm import defer, joinedload, raiseload
from wtforms import (BooleanField, IntegerField, SelectField, StringField,
                     SubmitField, TextAreaField)
from wtforms.validators import InputRequired, Length

from constants import Constant
from database import Category, Product, Supplier, User, dbSession
from helpers import admin_required, flash_errors, logger
from messages import Message

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
            InputRequired(Message.Supplier.Name.Required()),
            Length(
                min=Constant.Supplier.Name.min_length,
                message=Message.Supplier.Name.LenLimit())],
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
                "autocomplete": "off",
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
        false_values = ("False", False, "false", ""),
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
    reassign = SubmitField(
        label=lazy_gettext("Reassign all products"),
        render_kw={"class": "btn btn-warning"})


class ReassignSupForm(FlaskForm):
    """Reassign supplier products form."""
    reassign = SubmitField(
        label=lazy_gettext("Reassign all products"),
        render_kw={"class": "btn btn-warning"})
    responsible_id = SelectField(
        label=lazy_gettext("New responsible"),
        coerce=int,
        render_kw={
                "class": "form-select",
                })


@sup_bp.route("/suppliers")
def suppliers():
    """All suppliers page."""
    logger.info("Suppliers page")
    session["last_url"] = url_for(".suppliers")
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
    logger.info("New supplier page")
    new_sup_form: CreateSupForm = CreateSupForm()
    if new_sup_form.validate_on_submit():
        with dbSession() as db_session:
            try:
                supplier = Supplier(name=new_sup_form.name.data)
                new_sup_form.populate_obj(supplier)
                db_session.add(supplier)
                db_session.commit()
                logger.debug("Supplier '%s' created", supplier.name)
                flash(**Message.Supplier.Created.flash(supplier.name))
                return redirect(url_for(".suppliers"))
            except ValueError as error:
                logger.warning("Supplier creation error(s)")
                flash(str(error), "error")
    elif new_sup_form.errors:
        logger.warning("Supplier creation error(s)")
        flash_errors(new_sup_form.errors)

    return render_template("sup/new_supplier.html", form=new_sup_form)


@sup_bp.route("/edit/<path:supplier>", methods=["GET", "POST"])
def edit_supplier(supplier):
    """Edit supplier."""
    logger.info("Edit supplier %s", supplier)
    edit_sup_form: EditSupForm = EditSupForm()

    if edit_sup_form.validate_on_submit():
        with dbSession() as db_session:
            sup = db_session.scalar(
                select(Supplier)
                .filter_by(name=escape(supplier)))
            if edit_sup_form.delete.data:
                if sup.all_products:
                    flash(**Message.Supplier.NoDelete.flash())
                else:
                    db_session.delete(sup)
                    db_session.commit()
                    logger.debug("Supplier '%s' has been deleted", sup.name)
                    flash(**Message.Supplier.Deleted.flash(sup.name))
                    return redirect(session["last_url"])
            elif edit_sup_form.reassign.data:
                return redirect(url_for(".reassign_supplier",
                                        supplier=sup.name))
            else:
                try:
                    sup.name = edit_sup_form.name.data
                    sup.details = edit_sup_form.details.data
                    sup.in_use = edit_sup_form.in_use.data
                except ValueError as error:
                    flash(str(error), "error")
                else:
                    if db_session.is_modified(sup, include_collections=False):
                        logger.debug("Supplier updated")
                        flash(**Message.Supplier.Updated.flash(sup.name))
                        db_session.commit()
                        return redirect(session["last_url"])
    elif edit_sup_form.errors:
        logger.warning("Supplier editing error(s)")
        flash_errors(edit_sup_form.errors)

    with dbSession() as db_session:
        if (sup := db_session.scalar(
                select(Supplier)
                .filter_by(name=escape(supplier)))):
            edit_sup_form = EditSupForm(obj=sup)
        else:
            logger.debug("Supplier '%s' does not exist", supplier)
            flash(**Message.Supplier.NotExists.flash(supplier))
            return redirect(url_for(".suppliers"))

    return render_template("sup/edit_supplier.html", form=edit_sup_form)


@sup_bp.route("/reassign/<path:supplier>", methods=["GET", "POST"])
def reassign_supplier(supplier):
    """Reassign all products from supplier."""
    logger.info("Reassign products supplier '%s' page", supplier)
    reassign_sup_form: ReassignSupForm = ReassignSupForm()

    with dbSession() as db_session:
        users = db_session.execute(
            select(User.id, User.name)
            .filter_by(in_use=True, reg_req=False)
            .order_by(func.lower(User.name))
            ).all()
    reassign_sup_form.responsible_id.choices = [
        (0, Message.Supplier.Responsible.Default())]
    reassign_sup_form.responsible_id.choices.extend(
        [(user.id, user.name) for user in users])

    if reassign_sup_form.validate_on_submit():
        if reassign_sup_form.responsible_id.data:
            with dbSession() as db_session:
                sup = db_session.scalar(
                    select(Supplier)
                    .filter_by(name=escape(supplier)))
                products = db_session.scalars(
                    select(Product)
                    .filter_by(supplier_id=sup.id)
                    ).all()
                for product in products:
                    product.responsible_id = (reassign_sup_form
                                              .responsible_id.data)
                db_session.commit()
                logger.debug("Supplier '%s' responsible updated", sup.name)
                flash(**Message.Supplier.Responsible.Updated.flash(sup.name))
        else:
            flash(**Message.Supplier.Responsible.Invalid.flash())
        return redirect(url_for(".reassign_supplier", supplier=supplier))

    elif reassign_sup_form.errors:
        logger.warning("Supplier reassign error(s)")
        flash_errors(reassign_sup_form.errors)

    with dbSession() as db_session:
        if (sup := db_session.scalar(
                select(Supplier)
                .filter_by(name=escape(supplier)))):
            products = db_session.scalars(
                select(Product)
                .join(Product.supplier)
                .filter_by(name=sup.name)
                .options(
                    defer(Product.to_order, raiseload=True),
                    joinedload(Product.responsible).load_only(User.name),
                    joinedload(Product.category).load_only(Category.name),
                    joinedload(Product.supplier).load_only(Supplier.name),
                    raiseload("*"))
                .order_by(func.lower(Product.responsible_id),
                          func.lower(Product.name))
            ).unique().all()
        else:
            logger.debug("Supplier '%s' does not exist", supplier)
            flash(**Message.Supplier.NotExists.flash(supplier))
            return redirect(url_for(".suppliers"))

    return render_template("sup/reassign_supplier.html",
                           form=reassign_sup_form,
                           products=products)
