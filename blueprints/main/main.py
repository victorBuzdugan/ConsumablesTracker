"""Main blueprint."""

from typing import Callable

from flask import Blueprint, render_template, session
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload, raiseload

from blueprints.sch import SAT_GROUP_SCH
from database import Category, Product, Supplier, User, dbSession
from helpers import logger, login_required

func: Callable

main_bp = Blueprint("main",
                    __name__,
                    template_folder="templates")


@main_bp.route("/")
@login_required
def index():
    """Index page."""
    logger.info("Index page")
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
                "products_in_use": db_session.scalar(
                        select(func.count(Product.id))
                        .filter_by(in_use=True)),
                "critical_products": db_session.scalar(
                        select(func.count(Product.id))
                        .filter_by(in_use=True, critical=True)),
                "users_in_use": db_session.scalar(
                        select(func.count(User.id))
                        .filter_by(in_use=True)),
                "categories_in_use": db_session.scalar(
                        select(func.count(Category.id))
                        .filter_by(in_use=True)),
                "suppliers_in_use": db_session.scalar(
                        select(func.count(Supplier.id))
                        .filter_by(in_use=True)),
            }

            return render_template(
                "main/index.html",
                user=user,
                users=users,
                stats=stats,
                sat_group_sch=SAT_GROUP_SCH)

    return render_template("main/index.html",
                           user=user,
                           sat_group_sch=SAT_GROUP_SCH)
