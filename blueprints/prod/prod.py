"""Products blueprint."""

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_wtf import FlaskForm
from markupsafe import escape
from sqlalchemy import func, select, text
from sqlalchemy.orm import (defaultload, defer, joinedload, lazyload,
                            load_only, raiseload, selectinload)
from wtforms import (BooleanField, IntegerField, SelectField, StringField,
                     SubmitField, TextAreaField)
from wtforms.validators import InputRequired, Length, NumberRange

from database import Category, Product, Supplier, User, dbSession
from helpers import admin_required, flash_errors

prod_bp = Blueprint(
    "prod",
    __name__,
    url_prefix="/product",
    template_folder="templates")

# require admin logged in for all routes
@prod_bp.before_request
@admin_required
def admin_logged_in():
    pass


class CreateProdForm(FlaskForm):
    """Create product form."""
    name = StringField(
        label="Code",
        validators=[
            InputRequired("Product name is required"),
            Length(
                min=3,
                max=15,
                message="Product name must be between 3 and 15 characters")],
        render_kw={
            "class": "form-control",
            "placeholder": "Code",
            "autocomplete": "off",
            })
    description = StringField(
        label="Description",
        validators=[
            InputRequired("Product description is required"),
            Length(
                min=3,
                max=50,
                message="Product description must be " +
                    "between 3 and 50 characters")],
        render_kw={
                "class": "form-control",
                "placeholder": "Description",
                "style": "height: 5rem",
                "autocomplete": "off",
                })
    responsable_id = SelectField(
        label="Responsable",
        coerce=int,
        render_kw={
                "class": "form-select",
                })
    category_id = SelectField(
        label="Category",
        coerce=int,
        render_kw={
                "class": "form-select",
                })
    supplier_id = SelectField(
        label="Supplier",
        coerce=int,
        render_kw={
                "class": "form-select",
                })
    meas_unit = StringField(
        label="Measuring unit",
        validators=[InputRequired("Measuring unit is required")],
        render_kw={
            "class": "form-control",
            "placeholder": "Measuring unit",
            })
    min_stock = IntegerField(
        label="Minimum stock",
        validators=[
            InputRequired("Minimum stock is required"),
            NumberRange(
                min=0,
                message="Minimum stock must be at least 0")],
        render_kw={
            "class": "form-control",
            "placeholder": "Minimum stock",
            })
    ord_qty = IntegerField(
        label="Order quantity",
        validators=[
            InputRequired("Order quantity is required"),
            NumberRange(
                min=1,
                message="Order quantity must be at least 1")],
        render_kw={
            "class": "form-control",
            "placeholder": "Order quantity",
            })
    critical = BooleanField(
        label="Critical product",
        render_kw={
                "class": "form-check-input",
                "role": "switch",
                })
    submit = SubmitField(
        label="Create product",
        render_kw={"class": "btn btn-primary px-4"})


class EditProdForm(CreateProdForm):
    """Edit product form."""
    to_order = BooleanField(
        label="To order",
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
    submit = SubmitField(
        label="Update",
        render_kw={"class": "btn btn-primary px-4"})
    delete = SubmitField(
        label="Delete",
        render_kw={"class": "btn btn-danger"})


class ProdToOrderForm(FlaskForm):
    """Flask-WTF form used just for csrf token."""


@prod_bp.route("/products-sorted-by-<ordered_by>")
def products(ordered_by):
    """All products page."""
    with dbSession() as db_session:
        if ordered_by == "code":
            products = db_session.scalars(
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
            products = db_session.scalars(
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
            products = db_session.scalars(
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
            products = db_session.scalars(
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
            flash(f"Cannot sort products by {ordered_by}", "warning")
            return redirect(url_for("prod.products", ordered_by="code"))
        stats = {
                "all_products": db_session.\
                        scalar(select(func.count(Product.id))),
                "in_use_products": db_session.\
                        scalar(select(func.count(Product.id)).\
                        filter_by(in_use=True)),
                "critical_products": db_session.\
                        scalar(select(func.count(Product.id)).\
                        filter_by(critical=True)),
                "in_use_critical_products": db_session.\
                        scalar(select(func.count(Product.id)).\
                        filter_by(in_use=True, critical=True)),
        }
    return render_template(
        "prod/products.html",
        products=products,
        stats=stats)

@prod_bp.route("/new", methods=["GET", "POST"])
def new_product():
    """Create a new product."""
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
                    new_prod_form.name.data,
                    new_prod_form.description.data,
                    db_session.get(User, new_prod_form.responsable_id.data),
                    db_session.get(Category, new_prod_form.category_id.data),
                    db_session.get(Supplier, new_prod_form.supplier_id.data),
                    new_prod_form.meas_unit.data,
                    new_prod_form.min_stock.data,
                    new_prod_form.ord_qty.data)
                new_prod_form.populate_obj(new_prod)
                db_session.add(new_prod)
                db_session.commit()
                flash(f"Product '{new_prod.name}' created")
                return redirect(url_for("prod.products", ordered_by="code"))
            except ValueError as error:
                flash(str(error), "error")
    elif new_prod_form.errors:
        flash_errors(new_prod_form.errors)

    return render_template("prod/new_product.html", form=new_prod_form)

@prod_bp.route("/<path:product>/edit", methods=["GET", "POST"])
def edit_product(product):
    """Edit product."""
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
            prod = db_session.scalar(select(Product).
                filter_by(name=escape(product)))
            if edit_prod_form.delete.data:
                db_session.delete(prod)
                db_session.commit()
                flash(f"Product '{prod.name}' has been deleted")
                return redirect(url_for("prod.products", ordered_by="code"))
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
                    flash("Product updated")
                    db_session.commit()
                return redirect(
                    url_for("prod.edit_product", product=prod.name))
                
    elif edit_prod_form.errors:
        flash_errors(edit_prod_form.errors)

    with dbSession() as db_session:
        if (prod:= db_session.scalar(select(Product).
                filter_by(name=escape(product)))):
            edit_prod_form = EditProdForm(obj=prod)
            edit_prod_form.responsable_id.choices = [
                (user.id, user.name) for user in users]
            edit_prod_form.category_id.choices = [
                (category.id, category.name) for category in categories]
            edit_prod_form.supplier_id.choices = [
                (supplier.id, supplier.name) for supplier in suppliers]
        else:
            flash(f"{product} does not exist!", "error")
            return redirect(url_for("prod.products", ordered_by="code"))

    return render_template("prod/edit_product.html", form=edit_prod_form)

@prod_bp.route("/products-to-order", methods=["GET", "POST"])
def products_to_order():
    """Products to order page."""
    prod_to_order_form: ProdToOrderForm = ProdToOrderForm()

    if prod_to_order_form.validate_on_submit():
        with dbSession() as db_session:
            products = db_session.scalars(
                select(Product)
                .join(Product.supplier)
                .options(
                    defer(Product.min_stock, raiseload=True),
                    joinedload(Product.responsable).load_only(User.name),
                    joinedload(Product.category).load_only(Category.name),
                    joinedload(Product.supplier).load_only(Supplier.name),
                    raiseload("*"))
                .filter(Product.to_order == True)
                .order_by(func.lower(Supplier.name))
            ).unique().all()
            for product in products:
                if str(product.id) in request.form:
                    product.to_order = False
                else:
                    product.to_order = True
            db_session.commit()
        flash("Products updated")
    elif prod_to_order_form.errors:
        flash_errors(prod_to_order_form.errors)

    with dbSession() as db_session:
        products = db_session.scalars(
            select(Product)
            .join(Product.supplier)
            .options(
                defer(Product.min_stock, raiseload=True),
                joinedload(Product.responsable).load_only(User.name),
                joinedload(Product.category).load_only(Category.name),
                joinedload(Product.supplier).load_only(Supplier.name),
                raiseload("*"))
            .filter(Product.to_order == True)
            .order_by(func.lower(Supplier.name))
        ).unique().all()
    if products:
        return render_template(
            "prod/products_to_oder.html",
            products=products,
            form=prod_to_order_form)
    else:
        flash("There are no products that need to be ordered", "warning")
        return redirect(url_for("main.index"))

@prod_bp.route("/products-ordered")
def all_products_ordered():
    """All products ordered flag."""
    with dbSession() as db_session:
        products = db_session.scalars(
            select(Product).filter_by(to_order=True)
            ).all()
        for product in products:
            product.to_order = False
        db_session.commit()
    flash("All products ordered")
    return redirect(url_for("main.index"))
