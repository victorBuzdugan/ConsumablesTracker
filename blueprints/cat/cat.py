"""Categories blueprint."""

from flask import Blueprint, flash, redirect, render_template, url_for
from flask_wtf import FlaskForm
from markupsafe import escape
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload, raiseload
from wtforms import (BooleanField, IntegerField, StringField, SubmitField,
                     TextAreaField)
from wtforms.validators import InputRequired, Length

from database import Category, dbSession
from helpers import admin_required, flash_errors

cat_bp = Blueprint(
    "cat",
    __name__,
    url_prefix="/category",
    template_folder="templates")

# require admin logged in for all routes
@cat_bp.before_request
@admin_required
def admin_logged_in():
    pass


class CreateCatForm(FlaskForm):
    """Create category form."""
    name = StringField(
        label="Name",
        validators=[
            InputRequired("Category name is required"),
            Length(
                min=3,
                message="Category name must have at least 3 characters")],
        render_kw={
            "class": "form-control",
            "placeholder": "Username",
            "autocomplete": "off",
            })
    description = TextAreaField(
        label="Description",
        render_kw={
                "class": "form-control",
                "placeholder": "Details",
                "style": "height: 5rem",
                })
    submit = SubmitField(
        label="Create category",
        render_kw={"class": "btn btn-primary px-4"})
    

class EditCatForm(CreateCatForm):
    """Edit user form."""
    all_products = IntegerField()
    in_use_products = IntegerField()
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

@cat_bp.route("/categories")
def categories():
    """All categories page."""
    with dbSession() as db_session:
        categories = db_session.scalars(
                select(Category).
                order_by(Category.in_use.desc(), func.lower(Category.name)).
                options(joinedload(Category.products), raiseload("*"))
                ).unique().all()
        stats = {
                "all_categories": db_session.\
                        scalar(select(func.count(Category.id))),
                "in_use_categories": db_session.\
                        scalar(select(func.count(Category.id)).\
                        filter_by(in_use=True)),
        }
    return render_template(
        "cat/categories.html",
        categories=categories,
        stats=stats)

@cat_bp.route("/new", methods=["GET", "POST"])
def new_category():
    """Create a new category."""
    new_cat_form: CreateCatForm = CreateCatForm()
    if new_cat_form.validate_on_submit():
        with dbSession() as db_session:
            try:
                category = Category(new_cat_form.name.data)
                new_cat_form.populate_obj(category)
                db_session.add(category)
                db_session.commit()
                flash(f"Category '{category.name}' created")
                return redirect(url_for("cat.categories"))
            except ValueError as error:
                flash(str(error), "error")
    elif new_cat_form.errors:
        flash_errors(new_cat_form.errors)

    return render_template("cat/new_category.html", form=new_cat_form)

@cat_bp.route("/<category>/edit", methods=["GET", "POST"])
def edit_category(category):
    """Edit category."""
    edit_cat_form: EditCatForm = EditCatForm()

    if edit_cat_form.validate_on_submit():
        with dbSession().no_autoflush as db_session:
            cat = db_session.scalar(select(Category).
                filter_by(name=escape(category)))
            if edit_cat_form.delete.data:
                if cat.all_products:
                    flash("Can't delete category! " +
                        "There are still products attached!",
                        "error")
                else:
                    db_session.delete(cat)
                    db_session.commit()
                    flash(f"Category '{cat.name}' has been deleted")
                    return redirect(url_for("cat.categories"))
            else:
                try:
                    cat.name = edit_cat_form.name.data
                except ValueError as error:
                    flash(str(error), "error")
                cat.description = edit_cat_form.description.data
                try:
                    cat.in_use = edit_cat_form.in_use.data
                except ValueError as error:
                    flash(str(error), "warning")
                if db_session.is_modified(cat, include_collections=False):
                    flash("Category updated")
                    db_session.commit()
                return redirect(
                    url_for("cat.edit_category", category=cat.name))
    elif edit_cat_form.errors:
        flash_errors(edit_cat_form.errors)
    
    with dbSession() as db_session:
        if (cat:= db_session.scalar(select(Category).
                filter_by(name=escape(category)))):
            edit_cat_form = EditCatForm(obj=cat)
        else:
            flash(f"{category} does not exist!", "error")
            return redirect(url_for("cat.categories"))

    return render_template("cat/edit_category.html", form=edit_cat_form)
