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

            in_use_users = db_session.scalars(
                select(User.name).filter_by(in_use=True)).all()
            in_use_categories = db_session.scalars(
                select(Category.name).filter_by(in_use=True)).all()
            in_use_suppliers = db_session.scalars(
                select(Supplier.name).filter_by(in_use=True)).all()
            in_use_products = db_session.scalars(
                select(Product.name).filter_by(in_use=True)).all()
            
            admin["in_use_users"] = len(in_use_users)
            admin["in_use_categories"] = len(in_use_categories)
            admin["in_use_suppliers"] = len(in_use_suppliers)
            admin["in_use_products"] = len(in_use_products)


    return render_template("main/index.html", stats=stats, admin=admin)
