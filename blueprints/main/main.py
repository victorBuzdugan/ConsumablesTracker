"""Main blueprint."""

from typing import Callable

from flask import Blueprint, render_template, session, url_for
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload, raiseload

from blueprints.sch import clean_sch_info, sat_sch_info
from database import Category, Product, Supplier, User, dbSession
from helpers import logger, login_required
from messages import Message

func: Callable

main_bp = Blueprint("main",
                    __name__,
                    template_folder="templates")


@main_bp.route("/")
@login_required
def index():
    """Index page."""
    logger.info("Index page")
    session["last_url"] = url_for(".index")
    with dbSession() as db_session:
        user = db_session.scalar(
            select(User)
            .filter_by(id=session.get("user_id"))
            .options(joinedload(User.products), raiseload("*")))

        if session.get("admin"):
            with dbSession() as db_session:
                users = db_session.scalars(
                    select(User)
                    .filter(User.name!="Admin")
                    .order_by(
                        User.reg_req.desc(),
                        User.in_use.desc(),
                        User.admin.desc(),
                        func.lower(User.name))
                    .options(joinedload(User.products), raiseload("*"))
                    ).unique().all()

            stats = {
                "products_to_order": db_session.scalar(
                        select(func.count(Product.id))
                        .filter_by(in_use=True, to_order=True)),
                "users_in_use": db_session.scalar(
                        select(func.count(User.id))
                        .filter_by(in_use=True)),
                "categories_in_use": db_session.scalar(
                        select(func.count(Category.id))
                        .filter_by(in_use=True)),
                "suppliers_in_use": db_session.scalar(
                        select(func.count(Supplier.id))
                        .filter_by(in_use=True)),
                "products_in_use": db_session.scalar(
                        select(func.count(Product.id))
                        .filter_by(in_use=True)),
                "crit_products_in_use": db_session.scalar(
                        select(func.count(Product.id))
                        .filter_by(in_use=True, critical=True)),
            }

            return render_template(
                "main/index.html",
                user=user,
                users=users,
                stats=stats,
                saturday_sch=sat_sch_info,
                cleaning_sch=clean_sch_info,
                Message=Message)

    return render_template("main/index.html",
                           user=user,
                           saturday_sch=sat_sch_info,
                           cleaning_sch=clean_sch_info,
                           Message=Message)
