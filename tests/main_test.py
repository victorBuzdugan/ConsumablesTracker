"""Main blueprint tests."""

import pytest
from flask import session, url_for
from flask.testing import FlaskClient
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from database import User, dbSession, Category, Supplier, Product
from tests import (admin_logged_in, client, create_test_categories,
                   create_test_db, create_test_suppliers, create_test_users,
                   user_logged_in, create_test_products)

pytestmark = pytest.mark.main


def test_index_user_not_logged_in(client: FlaskClient):
    with client:
        response = client.get("/", follow_redirects=True)
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("auth.login")
        assert b'type="submit" value="Log In"' in response.data
        assert b"You have to be logged in..." in response.data

        assert f'href={url_for("auth.register")}>Register' in response.text
        assert f'href={url_for("auth.login")}>Log In' in response.text

        assert f'href={url_for("inv.inventory")}>Inventory' not in response.text
        assert f'href={url_for("auth.change_password")}>Change password' not in response.text
        assert f'href={url_for("auth.logout")}>Log Out' not in response.text

        assert f'href={url_for("users.new_user")}>User' not in response.text
        assert f'href={url_for("cat.new_category")}>Category' not in response.text
        assert f'href={url_for("sup.new_supplier")}>Supplier' not in response.text
        assert f'href={url_for("prod.new_product")}>Product' not in response.text
        assert f'href={url_for("cat.categories")}>Categories' not in response.text
        assert f'href={url_for("sup.suppliers")}>Suppliers' not in response.text
        assert f'href={url_for("prod.products", ordered_by="code")}>Products' not in response.text
        assert f'href={url_for("prod.products_to_order")}>Order' not in response.text


def test_index_user_logged_in(client: FlaskClient, user_logged_in):
    with client:
        response = client.get("/")
        with dbSession() as db_session:
            user = db_session.get(User, session["user_id"])
            assert response.status_code == 200
            assert user
            # user dashboard
            assert ('Logged in as <span class="text-secondary">' +
                    f'{session["user_name"]}') in response.text
            assert ('You have <span class="text-secondary">' +
                    f'{len(user.products)} products') in response.text
            assert b"Inventory check not required" in response.data
            assert f'href="{url_for("inv.inventory_request")}">Request inventory' in response.text
            user.done_inv = False
            db_session.commit()
            response = client.get("/")
            assert "Check inventory" in response.text
            assert f'href={url_for("inv.inventory_request")}>Request inventory' not in response.text
            user.done_inv = True
            user.req_inv = True
            db_session.commit()
            response = client.get("/")
            assert "You requested a inventory check" in response.text
            assert f'href={url_for("inv.inventory_request")}>Request inventory' not in response.text
            user.req_inv = False
            db_session.commit()
        assert "Admin dashboard" not in response.text
        assert "Statistics" not in response.text

        assert f'href={url_for("auth.register")}>Register' not in response.text
        assert f'href={url_for("auth.login")}>Log In' not in response.text

        assert f'href={url_for("inv.inventory")}>Inventory' in response.text
        assert f'href={url_for("auth.change_password")}>Change password' in response.text
        assert f'href={url_for("auth.logout")}>Log Out' in response.text

        assert f'href={url_for("users.new_user")}>User' not in response.text
        assert f'href={url_for("cat.new_category")}>Category' not in response.text
        assert f'href={url_for("sup.new_supplier")}>Supplier' not in response.text
        assert f'href={url_for("prod.new_product")}>Product' not in response.text
        assert f'href={url_for("cat.categories")}>Categories' not in response.text
        assert f'href={url_for("sup.suppliers")}>Suppliers' not in response.text
        assert f'href={url_for("prod.products", ordered_by="code")}>Products' not in response.text
        assert f'href={url_for("prod.products_to_order")}>Order' not in response.text


def test_index_admin_logged_in_user_dashboard(client: FlaskClient, admin_logged_in):
    with client:
        response = client.get("/")
        assert response.status_code == 200
        with dbSession() as db_session:
            user = db_session.scalar(select(User).options(
                joinedload(User.products)).filter_by(id=session["user_id"]))
            # user dashboard
            assert response.status_code == 200
            assert ('Logged in as <span class="text-secondary">' +
                    f'{session["user_name"]}') in response.text
            assert ('You have <span class="text-secondary">' +
                    f'{user.in_use_products} products') in response.text
            assert "Inventory check not required" in response.text
            assert f'href="{url_for("inv.inventory_request")}">Request inventory' not in response.text
            user.done_inv = False
            db_session.commit()
            response = client.get("/")
            assert "Check inventory" in response.text
            assert f'href={url_for("inv.inventory_request")}>Request inventory' not in response.text
            user.done_inv = True
            db_session.commit()
        assert b"Admin dashboard" in response.data
        assert b"Panou de bord utilizator" not in response.data
        assert b"Statistics" in response.data
        assert b"Statistici" not in response.data

        assert f'href={url_for("auth.register")}>Register' not in response.text
        assert f'href={url_for("auth.login")}>Log In' not in response.text
        
        assert f'href={url_for("inv.inventory")}>Inventory' in response.text
        assert f'href={url_for("auth.change_password")}>Change password' in response.text
        assert f'href={url_for("auth.logout")}>Log Out' in response.text

        assert f'href={url_for("users.new_user")}>User' in response.text
        assert f'href={url_for("cat.new_category")}>Category' in response.text
        assert f'href={url_for("sup.new_supplier")}>Supplier' in response.text
        assert f'href={url_for("prod.new_product")}>Product' in response.text
        assert f'href={url_for("cat.categories")}>Categories' in response.text
        assert f'href={url_for("sup.suppliers")}>Suppliers' in response.text
        assert f'href={url_for("prod.products", ordered_by="code")}>Products' in response.text
        assert f'href={url_for("prod.products_to_order")}>Order' in response.text

        client.get(url_for("set_language", language="ro"))
        response = client.get(url_for("main.index"))
        assert b'Language changed' not in response.data
        assert b"Admin dashboard" not in response.data
        assert b"Statistics" not in response.data
        assert u'Limba a fost schimbată' in response.text
        assert b"Panou de bord utilizator" in response.data
        assert b"Statistici" in response.data
        client.get(url_for("set_language", language="en"))
        response = client.get(url_for("main.index"))
        assert b'Language changed' in response.data
        assert b"Admin dashboard" in response.data
        assert b"Statistics" in response.data
        assert u'Limba a fost schimbată' not in response.text
        assert b"Panou de bord utilizator" not in response.data
        assert b"Statistici" not in response.data


def test_index_admin_logged_in_admin_dashboard_table(client: FlaskClient, admin_logged_in):
    with client:
        response = client.get("/")
        assert response.status_code == 200
        assert b"Bolded users have administrative privileges" in response.data
        assert b"Strikethrough users are no longer in use" in response.data
        # name
        assert b'<span class=" fw-bolder"><a class="link-dark link-offset-2 link-underline-opacity-50 link-underline-opacity-100-hover" href="/user/user1/edit">user1</a>' in response.data
        assert b'<span class=" fw-bolder"><a class="link-dark link-offset-2 link-underline-opacity-50 link-underline-opacity-100-hover" href="/user/user2/edit">user2</a>' in response.data
        assert b'<span class=""><a class="link-dark link-offset-2 link-underline-opacity-50 link-underline-opacity-100-hover" href="/user/user3/edit">user3</a>' in response.data
        assert b'<span class=""><a class="link-dark link-offset-2 link-underline-opacity-50 link-underline-opacity-100-hover" href="/user/user4/edit">user4</a>' in response.data
        assert b'<span class=""><a class="link-dark link-offset-2 link-underline-opacity-50 link-underline-opacity-100-hover" href="/user/user5/edit">user5</a>' in response.data
        assert b'<span class="text-decoration-line-through"><a class="link-dark link-offset-2 link-underline-opacity-50 link-underline-opacity-100-hover" href="/user/user6/edit">user6</a>' in response.data
        with dbSession() as db_session:
            db_session.get(User, 6).admin = True
            db_session.commit()
            response = client.get("/")
            assert b'<span class="text-decoration-line-through fw-bolder"><a class="link-dark link-offset-2 link-underline-opacity-50 link-underline-opacity-100-hover" href="/user/user6/edit">user6</a>' in response.data
            db_session.get(User, 6).admin = False
            db_session.commit()
        # assigned products
        assert b"<td>13</td>" in response.data
        assert b"<td>16</td>" in response.data
        assert b"<td>9</td>" in response.data
        assert b"<td>4</td>" in response.data
        assert b"<td>0</td>" in response.data
        # status
        assert b"check inventory" not in response.data
        assert b"requested inventory" not in response.data
        assert f'href="{url_for("users.approve_reg", username="user5")}">requested registration' in response.text
        with dbSession() as db_session:
            db_session.get(User, 3).done_inv = False
            db_session.get(User, 4).req_inv = True
            db_session.get(User, 5).reg_req = False
            db_session.commit()
            response = client.get("/")
            assert f'href="{url_for("inv.inventory_user", username="user3")}">check inventory' in response.text
            assert f'href="{url_for("users.approve_check_inv", username="user4")}">requested inventory' in response.text
            assert b"requested registration" not in response.data
            db_session.get(User, 3).done_inv = True
            db_session.get(User, 4).req_inv = False
            db_session.get(User, 5).reg_req = True
            db_session.commit()

        client.get(url_for("set_language", language="ro"))
        response = client.get(url_for("main.index"))
        assert b'Language changed' not in response.data
        assert b'Admin dashboard' not in response.data
        assert b"Bolded users have administrative privileges" not in response.data
        assert b"Strikethrough users are no longer in use" not in response.data
        assert u'Limba a fost schimbată' in response.text
        assert b'Panou de bord administrator' in response.data
        assert u'Utilizatorii cu text îngroșat sunt administratori' in response.text
        assert u'Utilizatorii cu text tăiat sunt scoși din uz' in response.text
        client.get(url_for("set_language", language="en"))
        response = client.get(url_for("main.index"))
        assert b'Language changed' in response.data
        assert b'Admin dashboard' in response.data
        assert b"Bolded users have administrative privileges" in response.data
        assert b"Strikethrough users are no longer in use" in response.data
        assert u'Limba a fost schimbată' not in response.text
        assert b'Panou de bord administrator' not in response.data
        assert u'Utilizatorii cu text îngroșat sunt administratori' not in response.text
        assert u'Utilizatorii cu text tăiat sunt scoși din uz' not in response.text


def test_index_admin_logged_in_admin_dashboard_product_need_to_be_ordered(client: FlaskClient, admin_logged_in):
    with client:
        response = client.get("/")
        assert response.status_code == 200
        assert b"There are no products that need to be ordered" in response.data
        with dbSession() as db_session:
            db_session.get(Product, 1).to_order = True
            db_session.get(Product, 2).to_order = True
            db_session.get(Product, 3).to_order = True
            db_session.commit()
            response = client.get("/")
            assert f'<span class="text-danger">There are <a class="link-danger link-offset-2 link-underline-opacity-25 link-underline-opacity-100-hover" href="{url_for("prod.products_to_order")}">3 products</a> that need to be ordered' in response.text

            db_session.get(Product, 2).to_order = False
            db_session.commit()
            response = client.get("/")
            assert f'<span class="text-danger">There are <a class="link-danger link-offset-2 link-underline-opacity-25 link-underline-opacity-100-hover" href="{url_for("prod.products_to_order")}">2 products</a> that need to be ordered' in response.text

            db_session.get(Product, 1).to_order = False
            db_session.get(Product, 3).to_order = False
            db_session.commit()
            response = client.get("/")
            assert "There are no products that need to be ordered" in response.text


def test_index_admin_logged_in_statistics(client: FlaskClient, admin_logged_in):
    with client:
        response = client.get("/")
        with dbSession() as db_session:
            assert "Statistics" in response.text
            in_use_users = db_session.scalar(select(func.count(User.id)).
                filter_by(in_use=True))
            in_use_categories = db_session.scalar(select(func.count(Category.id)).
                filter_by(in_use=True))
            in_use_suppliers = db_session.scalar(select(func.count(Supplier.id)).
                filter_by(in_use=True))
            in_use_products = db_session.scalar(select(func.count(Product.id)).
                filter_by(in_use=True))
            critical_products = db_session.scalar(select(func.count(Product.id)).
                filter_by(in_use=True, critical=True))
            assert ('There are <span class="text-secondary">' +
                    f"{in_use_users}" +
                    " users</span> in use") in response.text
            assert ('href="/category/categories">' +
                    f"{in_use_categories}" +
                    " categories</a> in use") in response.text
            assert ('href="/supplier/suppliers">' +
                    f"{in_use_suppliers}" +
                    " suppliers</a> in use") in response.text
            assert ('href="/product/products-sorted-by-code">' +
                    f"{in_use_products}" +
                    " products</a> in use, of which " +
                    '<span class="text-secondary">' +
                    f"{critical_products}" +
                    "</span> are critical.") in response.text
