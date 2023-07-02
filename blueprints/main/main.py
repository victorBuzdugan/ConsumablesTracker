"""Main blueprint."""

from flask import Blueprint, render_template, session
from sqlalchemy import select

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
        user = db_session.get(User, session["user_id"])
        stats = {
            "products": len(user.products),
            "done_inv": user.done_inv,
            "req_inv": user.req_inv,
        }
        admin = {}
        if user.admin:
            req_inv_users = db_session.scalars(
                select(User.name).filter_by(req_inv=True)).all()
            admin["req_inv_users"] = ", ".join(req_inv_users)

            done_inv_users = db_session.scalars(
                select(User.name).filter_by(done_inv=False)).all()
            admin["done_inv_users"] = ", ".join(done_inv_users)

            reg_req_users = db_session.scalars(
                select(User.name).filter_by(reg_req=True)).all()
            admin["reg_req_users"] = ", ".join(reg_req_users)

            admin["in_use_users"] = (
                db_session.query(User).filter_by(in_use=True).count())
            admin["in_use_categories"] = (
                db_session.query(Category).filter_by(in_use=True).count())
            admin["in_use_suppliers"] = (
                db_session.query(Supplier).filter_by(in_use=True).count())
            admin["in_use_products"] = (
                db_session.query(Product).filter_by(in_use=True).count())
            admin["critical_products"] = (
                db_session.query(Product).filter_by(
                    in_use=True, critical=True).count())

    return render_template("main/index.html", stats=stats, admin=admin)
