"""Inventory blueprint."""

from flask import (Blueprint, flash, redirect, render_template, request,
                   session, url_for)
from flask_wtf import FlaskForm
from markupsafe import escape
from sqlalchemy import select

from database import Product, User, dbSession
from helpers import admin_required, login_required

inv_bp = Blueprint(
    "inv",
    __name__,
    template_folder="templates")


class InventoryForm(FlaskForm):
    """Flask-WTF form used just for csrf token."""


@inv_bp.route("/inventory", methods=["GET", "POST"])
@login_required
def inventory():
    """Inventory check page."""
    inv_form: InventoryForm = InventoryForm()
    with dbSession() as db_session:
        user = db_session.get(User, session.get("user_id"))
    if inv_form.validate_on_submit() and not user.done_inv:
        with dbSession() as db_session:
            products = db_session.scalars(
                select(Product)
                .filter_by(responsable_id=user.id, in_use=True)
                ).all()
            for product in products:
                if str(product.id) in request.form:
                    product.to_order = True
                else:
                    product.to_order = False
            db_session.get(User, user.id).done_inv = True
            db_session.commit()
        flash("Inventory has been submitted")
        return redirect(url_for("main.index"))
    elif inv_form.errors:
        flash_errors = [error for errors in inv_form.errors.values()
                        for error in errors]
        for error in flash_errors:
            flash(error, "error")
    elif user.done_inv:
        flash("Inventory check not required", "info")

    with dbSession() as db_session:
        products = db_session.scalars(
            select(Product)
            .filter_by(responsable_id=user.id, in_use=True)
            .order_by(Product.category_id, Product.name)
            ).all()

    return render_template(
        "inv/inventory.html",
        products=products, form=inv_form, user=user)


@inv_bp.route("/<username>_inventory", methods=["GET", "POST"])
@admin_required
def inventory_user(username):
    """Inventory check page for other users."""
    inv_form: InventoryForm = InventoryForm()
    with dbSession() as db_session:
        user = db_session.scalar(select(User).filter_by(name=escape(username)))

    if not user or not user.in_use or user.reg_req:
        if not user:
            flash(f"User {username} does not exist!", "error")
        elif not user.in_use:
            flash(f"User {username} is not in use anymore!", "warning")
        else:
            flash(f"User {username} awaits registration aproval!", "warning")
        return redirect(url_for("main.index"))

    if inv_form.validate_on_submit() and not user.done_inv:
        with dbSession() as db_session:
            products = db_session.scalars(
                select(Product)
                .filter_by(responsable_id=user.id, in_use=True)
                ).all()
            for product in products:
                if str(product.id) in request.form:
                    product.to_order = True
                else:
                    product.to_order = False
            db_session.get(User, user.id).done_inv = True
            db_session.commit()
        flash("Inventory has been submitted")
        return redirect(url_for("main.index"))
    elif inv_form.errors:
        flash_errors = [error for errors in inv_form.errors.values()
                        for error in errors]
        for error in flash_errors:
            flash(error, "error")
    elif user.done_inv:
        flash("Inventory check not required", "info")

    with dbSession() as db_session:
        products = db_session.scalars(
            select(Product)
            .filter_by(responsable_id=user.id, in_use=True)
            .order_by(Product.category_id, Product.name)
            ).all()

    return render_template(
        "inv/inventory.html",
        products=products, form=inv_form, user=user)


@inv_bp.route("/inventory_request")
@login_required
def inventory_request():
    """Inventory request action."""
    if session.get("admin"):
        flash("You are an admin! You don't need to request inventory checks",
              "warning")
    else:
        with dbSession() as db_session:
            user = db_session.get(User, session.get("user_id"))
            if user.done_inv:
                user.req_inv = True
                db_session.commit()
                flash("Inventory check request sent")
            else:
                flash("You allready can check the inventory!", "warning")
                return redirect(url_for("inv.inventory"))

    return redirect(url_for("main.index"))
