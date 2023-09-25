"""Inventory blueprint."""

from flask import (Blueprint, flash, redirect, render_template, request,
                   session, url_for)
from flask_babel import gettext
from flask_wtf import FlaskForm
from markupsafe import escape
from sqlalchemy import select

from database import Product, User, dbSession
from helpers import admin_required, flash_errors, logger, login_required

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
    logger.info("Inventory check page")
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
        logger.debug("Inventory submitted")
        flash(gettext("Inventory has been submitted"))
        return redirect(url_for("main.index"))
    elif inv_form.errors:
        logger.warning("Inventory submitting error(s)")
        flash_errors(inv_form.errors)
    elif user.done_inv:
        logger.warning("Inventory check not required")
        flash(gettext("Inventory check not required"), "info")

    with dbSession() as db_session:
        products = db_session.scalars(
            select(Product)
            .filter_by(responsable_id=user.id, in_use=True)
            .order_by(Product.category_id, Product.name)
            ).all()

    return render_template(
        "inv/inventory.html",
        products=products, form=inv_form, user=user)


@inv_bp.route("/<path:username>/inventory", methods=["GET", "POST"])
@admin_required
def inventory_user(username):
    """Inventory check page for other users."""
    logger.info("Inventory check page for user '%s'", username)
    inv_form: InventoryForm = InventoryForm()
    with dbSession() as db_session:
        user = db_session.scalar(select(User).filter_by(name=escape(username)))

    if not user or not user.in_use or user.reg_req:
        if not user:
            flash(gettext("User %(username)s does not exist!",
                          username=username), "error")
        elif not user.in_use:
            flash(gettext("User %(username)s is not in use anymore!",
                          username=username), "warning")
        else:
            flash(gettext("User %(username)s awaits registration aproval!",
                          username=username), "warning")
        logger.warning("Inventory check page for user '%s' error(s)", username)
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
        logger.debug("Inventory has been submitted for user '%s'", username)
        flash(gettext("Inventory has been submitted"))
        return redirect(url_for("main.index"))
    elif inv_form.errors:
        logger.warning("Inventory check page for user '%s' error(s)", username)
        flash_errors(inv_form.errors)
    elif user.done_inv:
        logger.debug("Inventory check not required for user '%s' error(s)",
                     username)
        flash(gettext("Inventory check not required"), "info")

    with dbSession() as db_session:
        products = db_session.scalars(
            select(Product)
            .filter_by(responsable_id=user.id, in_use=True)
            .order_by(Product.category_id, Product.name)
            ).all()

    return render_template(
        "inv/inventory.html",
        products=products, form=inv_form, user=user)


@inv_bp.route("/inventory/request")
@login_required
def inventory_request():
    """Inventory request action."""
    if session.get("admin"):
        flash(gettext("You are an admin! You don't need to request " +
                      "inventory checks"), "warning")
    else:
        with dbSession() as db_session:
            user = db_session.get(User, session.get("user_id"))
            try:
                user.req_inv = True
                logger.info("Inventory check request sent")
                flash(gettext("Inventory check request sent"))
                db_session.commit()
            except ValueError as error:
                flash(str(error), "warning")
                return redirect(url_for("inv.inventory"))

    return redirect(url_for("main.index"))
