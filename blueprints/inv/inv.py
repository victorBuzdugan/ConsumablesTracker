"""Inventory blueprint."""

from flask import (Blueprint, flash, redirect, render_template, request,
                   session, url_for)
from flask_wtf import FlaskForm
from markupsafe import escape
from sqlalchemy import select

from database import Product, User, dbSession
from helpers import admin_required, flash_errors, logger, login_required
from messages import Message

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
    session["last_url"] = url_for(".inventory")
    inv_form: InventoryForm = InventoryForm()
    with dbSession() as db_session:
        user = db_session.get(User, session.get("user_id"))
    if inv_form.validate_on_submit() and not user.done_inv:
        with dbSession() as db_session:
            products = db_session.scalars(
                select(Product)
                .filter_by(responsible_id=user.id, in_use=True)
                ).all()
            for product in products:
                if str(product.id) in request.form:
                    product.to_order = True
                else:
                    product.to_order = False
            db_session.get(User, user.id).done_inv = True
            db_session.commit()
        logger.debug("Inventory submitted")
        flash(**Message.UI.Inv.Submitted.flash())
        return redirect(url_for("main.index"))
    elif inv_form.errors:
        logger.warning("Inventory submitting error(s)")
        flash_errors(inv_form.errors)
    elif user.done_inv:
        logger.info("Inventory check not required")
        flash(**Message.UI.Inv.NotReq.flash())

    with dbSession() as db_session:
        products = db_session.scalars(
            select(Product)
            .filter_by(responsible_id=user.id, in_use=True)
            .order_by(Product.category_id, Product.name)
            ).all()

    return render_template(
        "inv/inventory.html",
        products=products, form=inv_form, user=user)


@inv_bp.route("/inventory/<path:username>", methods=["GET", "POST"])
@admin_required
def inventory_user(username):
    """Inventory check page for other users."""
    logger.info("Inventory check page for user '%s'", username)
    session["last_url"] = url_for(".inventory_user", username=username)
    inv_form: InventoryForm = InventoryForm()
    with dbSession() as db_session:
        user = db_session.scalar(select(User).filter_by(name=escape(username)))

    if not user or not user.in_use or user.reg_req:
        if not user:
            flash(**Message.User.NotExists.flash(username))
        elif not user.in_use:
            flash(**Message.User.Retired.flash(username))
        else:
            flash(**Message.User.RegPending.flash(username))
        logger.warning("Inventory check page for user '%s' error(s)", username)
        return redirect(url_for("main.index"))

    if inv_form.validate_on_submit() and not user.done_inv:
        with dbSession() as db_session:
            products = db_session.scalars(
                select(Product)
                .filter_by(responsible_id=user.id, in_use=True)
                ).all()
            for product in products:
                if str(product.id) in request.form:
                    product.to_order = True
                else:
                    product.to_order = False
            db_session.get(User, user.id).done_inv = True
            db_session.commit()
        logger.debug("Inventory has been submitted for user '%s'", username)
        flash(**Message.UI.Inv.Submitted.flash())
        return redirect(url_for("main.index"))
    elif inv_form.errors:
        logger.warning("Inventory check page for user '%s' error(s)", username)
        flash_errors(inv_form.errors)
    elif user.done_inv:
        logger.info("Inventory check not required for user '%s' error(s)",
                     username)
        flash(**Message.UI.Inv.NotReq.flash())

    with dbSession() as db_session:
        products = db_session.scalars(
            select(Product)
            .filter_by(responsible_id=user.id, in_use=True)
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
        flash(**Message.User.ReqInv.Admin.flash())
    else:
        with dbSession() as db_session:
            user = db_session.get(User, session.get("user_id"))
            try:
                user.req_inv = True
                logger.info("Inventory check request sent")
                flash(**Message.User.ReqInv.Sent.flash())
                db_session.commit()
            except ValueError as error:
                flash(str(error), "warning")
                return redirect(url_for(".inventory"))

    return redirect(url_for("main.index"))
