"""Products blueprint."""

from typing import Callable

from flask import (Blueprint, flash, redirect, render_template, request,
                   session, url_for)
from flask_babel import gettext, lazy_gettext
from flask_wtf import FlaskForm
from markupsafe import escape
from sqlalchemy import func, select
from sqlalchemy.orm import defer, joinedload, raiseload
from wtforms import (BooleanField, IntegerField, SelectField, StringField,
                     SubmitField)
from wtforms.validators import InputRequired, Length, NumberRange

from database import Category, Product, Supplier, User, dbSession
from helpers import Constants, admin_required, flash_errors, logger

func: Callable

prod_bp = Blueprint(
    "prod",
    __name__,
    url_prefix="/product",
    template_folder="templates")


@prod_bp.before_request
@admin_required
def admin_logged_in():
    """Require admin logged in for all routes."""


class CreateProdForm(FlaskForm):
    """Create product form."""
    name = StringField(
        label=lazy_gettext("Code"),
        validators=[
            InputRequired(gettext("Product name is required")),
            Length(
                min=Constants.Product.Name.min_length,
                max=Constants.Product.Name.max_length,
                message=gettext("Product name must be between " +
                                f"{Constants.Product.Name.min_length} and " +
                                f"{Constants.Product.Name.max_length} " +
                                "characters"))],
        render_kw={
            "class": "form-control",
            "placeholder": lazy_gettext("Code"),
            "autocomplete": "off",
            })
    description = StringField(
        label=lazy_gettext("Description"),
        validators=[
            InputRequired(gettext("Product description is required")),
            Length(
                min=Constants.Product.Description.min_length,
                max=Constants.Product.Description.max_length,
                message=gettext("Product description must be between " +
                                f"{Constants.Product.Description.min_length} " +
                                "and " +
                                f"{Constants.Product.Description.max_length} " +
                                "characters"))],
        render_kw={
                "class": "form-control",
                "placeholder": lazy_gettext("Description"),
                "style": "height: 5rem",
                "autocomplete": "off",
                })
    responsable_id = SelectField(
        label=lazy_gettext("Responsable"),
        coerce=int,
        render_kw={
                "class": "form-select",
                })
    category_id = SelectField(
        label=lazy_gettext("Category"),
        coerce=int,
        render_kw={
                "class": "form-select",
                })
    supplier_id = SelectField(
        label=lazy_gettext("Supplier"),
        coerce=int,
        render_kw={
                "class": "form-select",
                })
    meas_unit = StringField(
        label=lazy_gettext("Measuring unit"),
        validators=[InputRequired(gettext("Measuring unit is required"))],
        render_kw={
            "class": "form-control",
            "placeholder": lazy_gettext("Measuring unit"),
            "autocomplete": "off",
            })
    min_stock = IntegerField(
        label=lazy_gettext("Minimum stock"),
        validators=[
            InputRequired(gettext("Minimum stock is required")),
            NumberRange(
                min=Constants.Product.MinStock.min_value,
                message=gettext("Minimum stock must be at least " +
                                f"{Constants.Product.MinStock.min_value}"))],
        render_kw={
            "class": "form-control",
            "placeholder": lazy_gettext("Minimum stock"),
            "autocomplete": "off",
            })
    ord_qty = IntegerField(
        label=lazy_gettext("Order quantity"),
        validators=[
            InputRequired(gettext("Order quantity is required")),
            NumberRange(
                min=Constants.Product.OrdQty.min_value,
                message=gettext("Order quantity must be at least " +
                                f"{Constants.Product.OrdQty.min_value}"))],
        render_kw={
            "class": "form-control",
            "placeholder": lazy_gettext("Order quantity"),
            "autocomplete": "off",
            })
    critical = BooleanField(
        label=lazy_gettext("Critical product"),
        false_values = ("False", False, "false", ""),
        render_kw={
                "class": "form-check-input",
                "role": "switch",
                })
    submit = SubmitField(
        label=lazy_gettext("Create product"),
        render_kw={"class": "btn btn-primary px-4"})


class EditProdForm(CreateProdForm):
    """Edit product form."""
    to_order = BooleanField(
        label=lazy_gettext("To order"),
        false_values = ("False", False, "false", ""),
        render_kw={
                "class": "form-check-input",
                "role": "switch",
                })
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


class ProdToOrderForm(FlaskForm):
    """Flask-WTF form used just for csrf token."""


@prod_bp.route("/products-sorted-by-<ordered_by>")
def products(ordered_by):
    """All products page."""
    logger.info("All products page")
    session["last_url"] = url_for(".products", ordered_by=ordered_by)
    with dbSession() as db_session:
        if ordered_by == "code":
            prods = db_session.scalars(
                select(Product)
                .options(
                    defer(Product.to_order, raiseload=True),
                    joinedload(Product.responsable).load_only(User.name),
                    joinedload(Product.category).load_only(Category.name),
                    joinedload(Product.supplier).load_only(Supplier.name),
                    raiseload("*"))
                .order_by(func.lower(Product.name))
            ).unique().all()
        elif ordered_by == "responsable":
            prods = db_session.scalars(
                select(Product)
                .join(Product.responsable)
                .options(
                    defer(Product.to_order, raiseload=True),
                    joinedload(Product.responsable).load_only(User.name),
                    joinedload(Product.category).load_only(Category.name),
                    joinedload(Product.supplier).load_only(Supplier.name),
                    raiseload("*"))
                .order_by(func.lower(User.name), func.lower(Product.name))
            ).unique().all()
        elif ordered_by == "category":
            prods = db_session.scalars(
                select(Product)
                .join(Product.category)
                .options(
                    defer(Product.to_order, raiseload=True),
                    joinedload(Product.responsable).load_only(User.name),
                    joinedload(Product.category).load_only(Category.name),
                    joinedload(Product.supplier).load_only(Supplier.name),
                    raiseload("*"))
                .order_by(func.lower(Category.name), func.lower(Product.name))
            ).unique().all()
        elif ordered_by == "supplier":
            prods = db_session.scalars(
                select(Product)
                .join(Product.supplier)
                .options(
                    defer(Product.to_order, raiseload=True),
                    joinedload(Product.responsable).load_only(User.name),
                    joinedload(Product.category).load_only(Category.name),
                    joinedload(Product.supplier).load_only(Supplier.name),
                    raiseload("*"))
                .order_by(func.lower(Supplier.name), func.lower(Product.name))
            ).unique().all()
        else:
            logger.warning("Products sorting error(s)")
            flash(gettext("Cannot sort products by %(ordered_by)s",
                          ordered_by=ordered_by), "warning")
            return redirect(url_for(".products", ordered_by="code"))
        stats = {
                "all_products": db_session.scalar(
                    select(func.count(Product.id))),
                "in_use_products": db_session.scalar(
                    select(func.count(Product.id))
                    .filter_by(in_use=True)),
                "critical_products": db_session.scalar(
                    select(func.count(Product.id))
                    .filter_by(critical=True)),
                "in_use_critical_products": db_session.scalar(
                    select(func.count(Product.id))
                    .filter_by(in_use=True, critical=True)),
        }
    return render_template(
        "prod/products.html",
        products=prods,
        stats=stats)


@prod_bp.route("/new", methods=["GET", "POST"])
def new_product():
    """Create a new product."""
    logger.info("New product page")
    new_prod_form: CreateProdForm = CreateProdForm()

    with dbSession() as db_session:
        users = db_session.execute(
            select(User.id, User.name)
            .filter_by(in_use=True, reg_req=False)
            .order_by(func.lower(User.name))
            ).all()
        categories = db_session.execute(
            select(Category.id, Category.name)
            .filter_by(in_use=True)
            .order_by(func.lower(Category.name))
            ).all()
        suppliers = db_session.execute(
            select(Supplier.id, Supplier.name)
            .filter_by(in_use=True)
            .order_by(func.lower(Supplier.name))
            ).all()
    new_prod_form.responsable_id.choices = [
        (user.id, user.name) for user in users]
    new_prod_form.category_id.choices = [
        (category.id, category.name) for category in categories]
    new_prod_form.supplier_id.choices = [
        (supplier.id, supplier.name) for supplier in suppliers]

    if new_prod_form.validate_on_submit():
        with dbSession() as db_session:
            try:
                new_prod = Product(
                    name=new_prod_form.name.data,
                    description=new_prod_form.description.data,
                    responsable=db_session.get(
                        User, new_prod_form.responsable_id.data),
                    category=db_session.get(
                        Category, new_prod_form.category_id.data),
                    supplier=db_session.get(
                        Supplier, new_prod_form.supplier_id.data),
                    meas_unit=new_prod_form.meas_unit.data,
                    min_stock=new_prod_form.min_stock.data,
                    ord_qty=new_prod_form.ord_qty.data)
                new_prod_form.populate_obj(new_prod)
                db_session.add(new_prod)
                db_session.commit()
                logger.debug("Product '%s' created", new_prod.name)
                flash(gettext("Product '%(new_prod_name)s' created",
                              new_prod_name=new_prod.name))
                return redirect(url_for(".products", ordered_by="code"))
            except ValueError as error:
                logger.warning("Product creation error(s)")
                flash(str(error), "error")
    elif new_prod_form.errors:
        logger.warning("Product creation error(s)")
        flash_errors(new_prod_form.errors)

    return render_template("prod/new_product.html", form=new_prod_form)


@prod_bp.route("/edit/<path:product>", methods=["GET", "POST"])
def edit_product(product):
    """Edit product."""
    logger.info("Edit product '%s' page", product)
    edit_prod_form: EditProdForm = EditProdForm()

    with dbSession() as db_session:
        users = db_session.execute(
            select(User.id, User.name)
            .filter_by(in_use=True, reg_req=False)
            .order_by(func.lower(User.name))
            ).all()
        categories = db_session.execute(
            select(Category.id, Category.name)
            .filter_by(in_use=True)
            .order_by(func.lower(Category.name))
            ).all()
        suppliers = db_session.execute(
            select(Supplier.id, Supplier.name)
            .filter_by(in_use=True)
            .order_by(func.lower(Supplier.name))
            ).all()
    edit_prod_form.responsable_id.choices = [
        (user.id, user.name) for user in users]
    edit_prod_form.category_id.choices = [
        (category.id, category.name) for category in categories]
    edit_prod_form.supplier_id.choices = [
        (supplier.id, supplier.name) for supplier in suppliers]

    if edit_prod_form.validate_on_submit():
        with dbSession().no_autoflush as db_session:
            prod = db_session.scalar(
                select(Product)
                .filter_by(name=escape(product)))
            if edit_prod_form.delete.data:
                db_session.delete(prod)
                db_session.commit()
                logger.debug("Product '%s' has been deleted", prod.name)
                flash(gettext("Product '%(prod_name)s' has been deleted",
                              prod_name=prod.name))
                return redirect(session["last_url"])
            else:
                try:
                    prod.name = edit_prod_form.name.data
                except ValueError as error:
                    flash(str(error), "error")
                prod.description = edit_prod_form.description.data
                prod.responsable = db_session.get(
                    User, edit_prod_form.responsable_id.data)
                prod.category = db_session.get(
                    Category, edit_prod_form.category_id.data)
                prod.supplier = db_session.get(
                    Supplier, edit_prod_form.supplier_id.data)
                prod.meas_unit = edit_prod_form.meas_unit.data
                prod.min_stock = edit_prod_form.min_stock.data
                prod.ord_qty = edit_prod_form.ord_qty.data
                try:
                    prod.to_order = edit_prod_form.to_order.data
                except ValueError as error:
                    flash(str(error), "warning")
                prod.critical = edit_prod_form.critical.data
                try:
                    prod.in_use = edit_prod_form.in_use.data
                except ValueError as error:
                    flash(str(error), "warning")
                if db_session.is_modified(prod, include_collections=False):
                    logger.debug("Product updated")
                    flash(gettext("Product updated"))
                    db_session.commit()
                return redirect(session["last_url"])

    elif edit_prod_form.errors:
        logger.warning("Product editing error(s)")
        flash_errors(edit_prod_form.errors)

    with dbSession() as db_session:
        if (prod := db_session.scalar(
                select(Product)
                .filter_by(name=escape(product)))):
            edit_prod_form = EditProdForm(obj=prod)
            edit_prod_form.responsable_id.choices = [
                (user.id, user.name) for user in users]
            edit_prod_form.category_id.choices = [
                (category.id, category.name) for category in categories]
            edit_prod_form.supplier_id.choices = [
                (supplier.id, supplier.name) for supplier in suppliers]
        else:
            flash(gettext("%(product)s does not exist!",
                          product=product), "error")
            return redirect(url_for(".products", ordered_by="code"))

    return render_template("prod/edit_product.html", form=edit_prod_form)


@prod_bp.route("/products-to-order", methods=["GET", "POST"])
def products_to_order():
    """Products to order page."""
    logger.info("Order page")
    prod_to_order_form: ProdToOrderForm = ProdToOrderForm()
    if prod_to_order_form.validate_on_submit():
        with dbSession() as db_session:
            prods = db_session.scalars(
                select(Product)
                .join(Product.supplier)
                .options(
                    defer(Product.min_stock, raiseload=True),
                    joinedload(Product.responsable).load_only(User.name),
                    joinedload(Product.category).load_only(Category.name),
                    joinedload(Product.supplier).load_only(Supplier.name),
                    raiseload("*"))
                .filter(Product.to_order)
                .order_by(func.lower(Supplier.name))
            ).unique().all()
            for product in prods:
                if str(product.id) in request.form:
                    product.to_order = False
                else:
                    product.to_order = True
            db_session.commit()
        logger.debug("Product(s) ordered")
        flash(gettext("Products updated"))
        session["last_url"] = url_for("main.index")
    elif prod_to_order_form.errors:
        logger.warning("Product order error(s)")
        flash_errors(prod_to_order_form.errors)

    with dbSession() as db_session:
        prods = db_session.scalars(
            select(Product)
            .join(Product.supplier)
            .options(
                defer(Product.min_stock, raiseload=True),
                joinedload(Product.responsable).load_only(User.name),
                joinedload(Product.category).load_only(Category.name),
                joinedload(Product.supplier).load_only(Supplier.name),
                raiseload("*"))
            .filter(Product.to_order)
            .order_by(func.lower(Supplier.name))
        ).unique().all()
    if prods:
        session["last_url"] = url_for(".products_to_order")
        return render_template(
            "prod/products_to_oder.html",
            products=prods,
            form=prod_to_order_form)
    else:
        logger.debug("There are no products that need to be ordered")
        flash(gettext("There are no products that need to be ordered"),
              "warning")
        return redirect(session["last_url"])


@prod_bp.route("/products-ordered")
def all_products_ordered():
    """All products ordered flag."""
    with dbSession() as db_session:
        prods = db_session.scalars(
            select(Product).filter_by(to_order=True)
            ).all()
        for product in prods:
            product.to_order = False
        db_session.commit()
    logger.debug("All products ordered")
    flash(gettext("All products ordered"))
    return redirect(url_for("main.index"))
