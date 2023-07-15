"""Main blueprint."""

from flask import Blueprint, render_template, session
from sqlalchemy import select
from sqlalchemy.orm import joinedload, raiseload

from database import dbSession, User, Category, Supplier, Product
from helpers import login_required


main_bp = Blueprint("main",
                    __name__,
                    template_folder="templates")


@main_bp.route("/")
@login_required
def index():
    """Index page."""
    with dbSession() as db_session:
        user = db_session.scalar(
            select(User).
            filter_by(id=session.get("user_id")).
            options(joinedload(User.products), raiseload("*")))

        if session.get("admin"):
            with dbSession() as db_session:
                users = db_session.scalars(
                    select(User).
                    order_by(User.reg_req.desc(), User.in_use.desc(), User.admin.desc(), User.name).
                    options(joinedload(User.products), raiseload("*"))
                    ).unique().all()

            stats = {
                "products_to_order": db_session.query(Product).
                        filter_by(in_use=True, to_order=True).count(),
                "users_in_use": db_session.query(User).
                        filter_by(in_use=True).count(),
                "categories_in_use": db_session.query(Category).
                        filter_by(in_use=True).count(),
                "suppliers_in_use": db_session.query(Supplier).
                        filter_by(in_use=True).count(),
                "products_in_use": db_session.query(Product).
                        filter_by(in_use=True).count(),
                "critical_products": db_session.query(Product).
                        filter_by(in_use=True, critical=True).count()
            }

            return render_template("main/index.html", user=user, users=users, stats=stats)

    return render_template("main/index.html", user=user)
