"""Products blueprint tests."""

from html import unescape
from urllib.parse import quote

import pytest
from flask import g, session, url_for
from flask.testing import FlaskClient
from sqlalchemy import select
from werkzeug.security import check_password_hash

from blueprints.auth.auth import PASSW_SYMB, msg
from database import Category, Product, Supplier, User, dbSession
from tests import (admin_logged_in, client, create_test_categories,
                   create_test_db, create_test_products, create_test_suppliers,
                   create_test_users, user_logged_in)

pytestmark = pytest.mark.prod


# region: products page
def test_products_page_user_logged_in(client: FlaskClient, user_logged_in):
    with client:
        client.get("/")
        response = client.get(url_for("prod.products", ordered_by="code"), follow_redirects=True)
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("auth.login")
        assert b"You have to be an admin..." in response.data


def test_products_page_admin_logged_in(client: FlaskClient, admin_logged_in):
    with client:
        client.get("/")
        response = client.get(url_for("prod.products", ordered_by="code"), follow_redirects=True)
        assert len(response.history) == 0
        assert response.status_code == 200
        assert b"You have to be an admin..." not in response.data
        assert b"Products" in response.data
        assert b"Strikethrough products are no longer in use" in response.data
        assert b"AAA Batteries" in response.data
        assert b"Cleaning Cloth" in response.data
        assert b"user1" in response.data
        assert b"user3" in response.data
        assert b"Electronics" in response.data
        assert b"Groceries" in response.data
        assert b"Carrefour" in response.data
        assert b"Amazon" in response.data
        assert b'<span class="text-secondary">Code</span>' in response.data
        assert f'<a class="link-dark link-offset-2 link-underline-opacity-50 link-underline-opacity-100-hover" href="{url_for("prod.products", ordered_by="code")}">Code</a>' not in response.text
        assert b"link-dark link-offset-2 link-underline-opacity-50 link-underline-opacity-100-hover" in response.data
        assert b"text-decoration-line-through" in response.data
        with dbSession() as db_session:
            db_session.get(Product, 43).in_use = True
            db_session.commit()
            response = client.get(url_for("prod.products", ordered_by="code"))
            assert b"text-decoration-line-through" not in response.data
            db_session.get(Product, 43).in_use = False
            db_session.commit()
        response = client.get(url_for("prod.products", ordered_by="responsable"), follow_redirects=True)
        assert len(response.history) == 0
        assert response.status_code == 200
        assert b'<span class="text-secondary">Responsable</span>' in response.data
        response = client.get(url_for("prod.products", ordered_by="category"), follow_redirects=True)
        assert len(response.history) == 0
        assert response.status_code == 200
        assert b'<span class="text-secondary">Category</span>' in response.data
        response = client.get(url_for("prod.products", ordered_by="supplier"), follow_redirects=True)
        assert len(response.history) == 0
        assert response.status_code == 200
        assert b'<span class="text-secondary">Supplier</span>' in response.data
        response = client.get(url_for("prod.products", ordered_by="not_existing"), follow_redirects=True)
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert quote(response.request.path) == url_for("prod.products", ordered_by="code")
        assert b"Cannot sort products by not_existing" in response.data
# endregion


# region: new product
@pytest.mark.parametrize(("name", "description", "responsable_id", "category_id", "supplier_id", "meas_unit", "min_stock", "ord_qty", "critical"), (
    ("new", "some description", 1, 1, 1, "pc", 0, 1, ""),
    ("new product", "some very long description", 2, 1, 3, "meas", 10, 100, "on"),
    ("new", "some description", 7, 7, 4, "pc", 2, 8, ""),
))
def test_new_product(client: FlaskClient, admin_logged_in,
        name, description, responsable_id, category_id, supplier_id, meas_unit, min_stock, ord_qty, critical):
    with client:
        client.get("/")
        response = client.get(url_for("prod.new_product"))
        assert b"Create product" in response.data
        data = {
            "csrf_token": g.csrf_token,
            "name": name,
            "description": description,
            "responsable_id": responsable_id,
            "category_id": category_id,
            "supplier_id": supplier_id,
            "meas_unit": meas_unit,
            "min_stock": min_stock,
            "ord_qty": ord_qty,
            "critical": critical,
            }
        response = client.post(
            url_for("prod.new_product"), data=data, follow_redirects=True)
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("prod.products", ordered_by="code")
        assert f"Product '{name}' created" in unescape(response.text)
        assert bytes(name, "UTF-8") in response.data
    with dbSession() as db_session:
        prod = db_session.scalar(select(Product).filter_by(name=name))
        assert prod.description == description
        assert prod.responsable == db_session.get(User, responsable_id)
        assert prod.category == db_session.get(Category, category_id)
        assert prod.supplier == db_session.get(Supplier, supplier_id)
        assert prod.meas_unit == meas_unit
        assert prod.min_stock == min_stock
        assert prod.ord_qty == ord_qty
        assert prod.critical == bool(critical)
        assert not prod.to_order
        assert prod.in_use
        db_session.delete(prod)
        db_session.commit()


@pytest.mark.parametrize(("name", "description", "responsable_id", "category_id", "supplier_id", "meas_unit", "min_stock", "ord_qty", "flash_message"), (
    ("", "some description", 1, 1, 1, "pc", 0, 1, "Product name is required"),
    ("pr", "some description", 1, 1, 1, "pc", 0, 1, "Product name must be between 3 and 15 characters"),
    ("prod_prod_prod_p", "some description", 1, 1, 1, "pc", 0, 1, "Product name must be between 3 and 15 characters"),
    ("AA Batteries", "some description", 1, 1, 1, "pc", 0, 1, "The product AA Batteries allready exists"),
    ("new_product", "", 1, 1, 1, "pc", 0, 1, "Product description is required"),
    ("new_product", "de", 1, 1, 1, "pc", 0, 1, "Product description must be between 3 and 50 characters"),
    ("new_product", "desc-desc-desc-desc-desc-desc-desc-desc-desc-desc-desc", 1, 1, 1, "pc", 0, 1, "Product description must be between 3 and 50 characters"),
    ("new_product", "some description", None, 1, 1, "pc", 0, 1, "Not a valid choice"),
    ("new_product", "some description", "", 1, 1, "pc", 0, 1, "Not a valid choice"),
    ("new_product", "some description", " ", 1, 1, "pc", 0, 1, "Not a valid choice"),
    ("new_product", "some description", 5, 1, 1, "pc", 0, 1, "Not a valid choice"),
    ("new_product", "some description", 6, 1, 1, "pc", 0, 1, "Not a valid choice"),
    ("new_product", "some description", 1, None, 1, "pc", 0, 1, "Not a valid choice"),
    ("new_product", "some description", 1, "", 1, "pc", 0, 1, "Not a valid choice"),
    ("new_product", "some description", 1, " ", 1, "pc", 0, 1, "Not a valid choice"),
    ("new_product", "some description", 1, 8, 1, "pc", 0, 1, "Not a valid choice"),
    ("new_product", "some description", 1, 1, None, "pc", 0, 1, "Not a valid choice"),
    ("new_product", "some description", 1, 1, "", "pc", 0, 1, "Not a valid choice"),
    ("new_product", "some description", 1, 1, " ", "pc", 0, 1, "Not a valid choice"),
    ("new_product", "some description", 1, 1, 5, "pc", 0, 1, "Not a valid choice"),
    ("new_product", "some description", 1, 1, 1, "", 0, 1, "Measuring unit is required"),
    ("new_product", "some description", 1, 1, 1, "pc", "", 1, "Minimum stock is required"),
    ("new_product", "some description", 1, 1, 1, "pc", -1, 1, "Minimum stock must be at least 0"),
    ("new_product", "some description", 1, 1, 1, "pc", "a", 1, "Not a valid integer value"),
    ("new_product", "some description", 1, 1, 1, "pc", 0, "", "Order quantity is required"),
    ("new_product", "some description", 1, 1, 1, "pc", 0, 0, "Order quantity must be at least 1"),
    ("new_product", "some description", 1, 1, 1, "pc", 0, -1, "Order quantity must be at least 1"),
    ("new_product", "some description", 1, 1, 1, "pc", 0, "a", "Not a valid integer value"),
))
def test_failed_new_product(client: FlaskClient, admin_logged_in,
        name, description, responsable_id, category_id, supplier_id, meas_unit, min_stock, ord_qty, flash_message):
    with client:
        client.get("/")
        response = client.get(url_for("prod.new_product"))
        assert b"Create product" in response.data
        data = {
            "csrf_token": g.csrf_token,
            "name": name,
            "description": description,
            "responsable_id": responsable_id,
            "category_id": category_id,
            "supplier_id": supplier_id,
            "meas_unit": meas_unit,
            "min_stock": min_stock,
            "ord_qty": ord_qty,
            "critical": "",
            }
        response = client.post(
            url_for("prod.new_product"), data=data, follow_redirects=True)
        assert len(response.history) == 0
        assert response.status_code == 200
        assert b"Create product" in response.data
        assert f"Product '{name}' created" not in unescape(response.text)
        assert flash_message in unescape(response.text)
    with dbSession() as db_session:
        if name != "AA Batteries":
            assert not db_session.scalar(select(Product).filter_by(name=name))
# endregion


# region: edit product
@pytest.mark.parametrize(
    ("id", "new_name", "new_description", "new_responsable_id", "new_category_id", "new_supplier_id",
        "new_meas_unit", "new_min_stock", "new_ord_qty", "new_critical", "new_to_order", "new_in_use"), (
    ("1", "new name", "new description", 1, 2, 1, "new_meas_unit", 100, 100, "", "on", "on"),
    ("2", "new name", "new description", 1, 2, 1, "new_meas_unit", 100, 100, "on", "on", "on"),
    ("22", "new name", "new description", 2, 2, 1, "new_meas_unit", 100, 100, "on", "on", "on"),
    ("6", "new name", "new description", 1, 2, 4, "new_meas_unit", 100, 100, "on", "", ""),
    ("10", "new name", "new description", 7, 4, 2, "new_meas_unit", 100, 100, "on", "", ""),
    ("32", "new name", "new description", 2, 7, 3, "new_meas_unit", 100, 100, "on", "", ""),
))
def test_edit_product(client: FlaskClient, admin_logged_in,
        id, new_name, new_description, new_responsable_id, new_category_id, new_supplier_id,
            new_meas_unit, new_min_stock, new_ord_qty, new_critical, new_to_order, new_in_use):
    with dbSession() as db_session:
        prod = db_session.get(Product, id)
        orig_prod = {key: value for key, value in prod.__dict__.items()
            if key in {"name", "description", "responsable_id", "category_id",
                       "supplier_id", "meas_unit", "min_stock", "ord_qty",
                       "critical", "to_order", "in_use"}}
        with client:
            client.get("/")
            response = client.get(url_for("prod.edit_product", product=prod.name))
            assert len(response.history) == 0
            assert response.status_code == 200
            assert bytes(orig_prod["name"], "UTF-8") in response.data
            data = {
                "csrf_token": g.csrf_token,
                "name": new_name,
                "description": new_description,
                "responsable_id": new_responsable_id,
                "category_id": new_category_id,
                "supplier_id": new_supplier_id,
                "meas_unit": new_meas_unit,
                "min_stock": new_min_stock,
                "ord_qty": new_ord_qty,
                "critical": new_critical,
                "to_order": new_to_order,
                "in_use": new_in_use,
                "submit": True,
            }
            response = client.post(url_for("prod.edit_product", product=orig_prod["name"]),
                data=data, follow_redirects=True)
            assert len(response.history) == 1
            assert response.history[0].status_code == 302
            assert response.status_code == 200
            assert quote(response.request.path) == url_for("prod.edit_product", product=new_name)
            assert b"Product updated" in response.data
            assert bytes(new_name, "UTF-8") in response.data
            assert bytes(new_description, "UTF-8") in response.data
        db_session.refresh(prod)
        assert prod.name == new_name
        assert prod.description == new_description
        assert prod.responsable_id == new_responsable_id
        assert prod.category_id == new_category_id
        assert prod.supplier_id == new_supplier_id
        assert prod.meas_unit == new_meas_unit
        assert prod.min_stock == new_min_stock
        assert prod.ord_qty == new_ord_qty
        assert prod.critical == bool(new_critical)
        assert prod.to_order == bool(new_to_order)
        assert prod.in_use == bool(new_in_use)

        # teardown
        for key, value in orig_prod.items():
            setattr(prod, key, value)
        db_session.commit()


@pytest.mark.parametrize(
    ("id", "new_name", "new_description", "new_responsable_id", "new_category_id", "new_supplier_id",
        "new_meas_unit", "new_min_stock", "new_ord_qty", "flash_message"), (
    ("2", "", "new description", 1, 1, 1, "new_meas_unit", 100, 100, "Product name is required"),
    ("4", "pr", "new description", 1, 1, 1, "new_meas_unit", 100, 100, "Product name must be between 3 and 15 characters"),
    ("5", "prod_prod_prod_p", "new description", 1, 1, 1, "new_meas_unit", 100, 100, "Product name must be between 3 and 15 characters"),
    ("6", "new_product", "", 1, 1, 1, "new_meas_unit", 100, 100, "Product description is required"),
    ("3", "new_product", "de", 1, 1, 1, "new_meas_unit", 100, 100, "Product description must be between 3 and 50 characters"),
    ("7", "new_product", "desc-desc-desc-desc-desc-desc-desc-desc-desc-desc-desc", 1, 1, 1, "new_meas_unit", 100, 100, "Product description must be between 3 and 50 characters"),
    ("8", "new_product", "new description", None, 1, 1, "new_meas_unit", 100, 100, "Not a valid choice"),
    ("9", "new_product", "new description", "", 1, 1, "new_meas_unit", 100, 100, "Not a valid choice"),
    ("10", "new_product", "new description", " ", 1, 1, "new_meas_unit", 100, 100, "Not a valid choice"),
    ("10", "new_product", "new description", 5, 1, 1, "new_meas_unit", 100, 100, "Not a valid choice"),
    ("11", "new_product", "new description", 6, 1, 1, "new_meas_unit", 100, 100, "Not a valid choice"),
    ("12", "new_product", "new description", 8, 1, 1, "new_meas_unit", 100, 100, "Not a valid choice"),
    ("13", "new_product", "new description", 1, None, 1, "new_meas_unit", 100, 100, "Not a valid choice"),
    ("14", "new_product", "new description", 1, "", 1, "new_meas_unit", 100, 100, "Not a valid choice"),
    ("15", "new_product", "new description", 1, " ", 1, "new_meas_unit", 100, 100, "Not a valid choice"),
    ("16", "new_product", "new description", 1, 8, 1, "new_meas_unit", 100, 100, "Not a valid choice"),
    ("17", "new_product", "new description", 1, 9, 1, "new_meas_unit", 100, 100, "Not a valid choice"),
    ("18", "new_product", "new description", 1, 1, None, "new_meas_unit", 100, 100, "Not a valid choice"),
    ("19", "new_product", "new description", 1, 1, "", "new_meas_unit", 100, 100, "Not a valid choice"),
    ("20", "new_product", "new description", 1, 1, " ", "new_meas_unit", 100, 100, "Not a valid choice"),
    ("21", "new_product", "new description", 1, 1, 5, "new_meas_unit", 100, 100, "Not a valid choice"),
    ("22", "new_product", "new description", 1, 1, 6, "new_meas_unit", 100, 100, "Not a valid choice"),
    ("23", "new_product", "new description", 1, 1, 1, "", 100, 100, "Measuring unit is required"),
    ("24", "new_product", "new description", 1, 1, 1, "new_meas_unit", "", 100, "Minimum stock is required"),
    ("25", "new_product", "new description", 1, 1, 1, "new_meas_unit", -1, 100, "Minimum stock must be at least 0"),
    ("26", "new_product", "new description", 1, 1, 1, "new_meas_unit", "a", 100, "Not a valid integer value"),
    ("27", "new_product", "new description", 1, 1, 1, "new_meas_unit", 100, "", "Order quantity is required"),
    ("28", "new_product", "new description", 1, 1, 1, "new_meas_unit", 100, 0, "Order quantity must be at least 1"),
    ("29", "new_product", "new description", 1, 1, 1, "new_meas_unit", 100, -1, "Order quantity must be at least 1"),
    ("30", "new_product", "new description", 1, 1, 1, "new_meas_unit", 100, "a", "Not a valid integer value"),
))
def test_failed_edit_product_form_validators(client: FlaskClient, admin_logged_in,
        id, new_name, new_description, new_responsable_id, new_category_id, new_supplier_id,
            new_meas_unit, new_min_stock, new_ord_qty, flash_message):
    with dbSession() as db_session:
        prod = db_session.get(Product, id)
        orig_prod = {key: value for key, value in prod.__dict__.items()
            if key in {"name", "description", "responsable_id", "category_id",
                       "supplier_id", "meas_unit", "min_stock", "ord_qty",
                       "critical", "to_order", "in_use"}}
        with client:
            client.get("/")
            response = client.get(url_for("prod.edit_product", product=prod.name))
            assert len(response.history) == 0
            assert response.status_code == 200
            assert bytes(orig_prod["name"], "UTF-8") in response.data
            data = {
                "csrf_token": g.csrf_token,
                "name": new_name,
                "description": new_description,
                "responsable_id": new_responsable_id,
                "category_id": new_category_id,
                "supplier_id": new_supplier_id,
                "meas_unit": new_meas_unit,
                "min_stock": new_min_stock,
                "ord_qty": new_ord_qty,
                "critical": "",
                "to_order": "",
                "in_use": "on",
                "submit": True,
            }
            response = client.post(url_for("prod.edit_product", product=orig_prod["name"]),
                data=data, follow_redirects=True)
            assert len(response.history) == 0
            assert response.status_code == 200
            assert b"Product updated" not in response.data
            assert bytes(orig_prod["name"], "UTF-8") in response.data
            assert flash_message in unescape(response.text)
        db_session.refresh(prod)
        for key, value in orig_prod.items():
            assert getattr(prod, key) == value


def test_failed_edit_product_name_duplicate(client: FlaskClient, admin_logged_in):
    with dbSession() as db_session:
        prod = db_session.get(Product, 2)
        orig_name = prod.name
        new_name = db_session.get(Product, 1).name
        with client:
            client.get("/")
            response = client.get(url_for("prod.edit_product", product=orig_name))
            assert bytes(prod.name, "UTF-8") in response.data
            data = {
                "csrf_token": g.csrf_token,
                "name": new_name,
                "description": prod.description,
                "responsable_id": prod.responsable_id,
                "category_id": prod.category_id,
                "supplier_id": prod.supplier_id,
                "meas_unit": prod.meas_unit,
                "min_stock": prod.min_stock,
                "ord_qty": prod.ord_qty,
                "critical": "",
                "to_order": "",
                "in_use": "on",
                "submit": True,
            }
            response = client.post(url_for("prod.edit_product", product=orig_name),
                                   data=data, follow_redirects=True)
            assert len(response.history) == 1
            assert response.history[0].status_code == 302
            assert response.status_code == 200
            assert quote(response.request.path) == url_for("prod.edit_product", product=orig_name)
            assert b"Product updated" not in response.data
            assert bytes(orig_name, "UTF-8") in response.data
            assert f"The product {new_name} allready exists" in response.text
        db_session.refresh(prod)
        assert prod.name != new_name


def test_failed_edit_product_to_order_in_use_validator(client: FlaskClient, admin_logged_in):
    with dbSession() as db_session:
        prod = db_session.get(Product, 3)
        prod.in_use = False
        db_session.commit()
        with client:
            client.get("/")
            response = client.get(url_for("prod.edit_product", product=prod.name))
            assert bytes(prod.name, "UTF-8") in response.data
            data = {
                "csrf_token": g.csrf_token,
                "name": prod.name,
                "description": prod.description,
                "responsable_id": prod.responsable_id,
                "category_id": prod.category_id,
                "supplier_id": prod.supplier_id,
                "meas_unit": prod.meas_unit,
                "min_stock": prod.min_stock,
                "ord_qty": prod.ord_qty,
                "critical": "on",
                "to_order": "on",
                "in_use": "",
                "submit": True,
            }
            response = client.post(url_for("prod.edit_product", product=prod.name),
                                   data=data, follow_redirects=True)
            assert len(response.history) == 1
            assert response.history[0].status_code == 302
            assert response.status_code == 200
            assert quote(response.request.path) == url_for("prod.edit_product", product=prod.name)
            assert b"Product updated" not in response.data
            assert bytes(prod.name, "UTF-8") in response.data
            assert f"Can't order not in use products" in unescape(response.text)
        db_session.refresh(prod)
        assert not prod.to_order

        prod.in_use = True
        prod.to_order = True
        db_session.commit()
        with client:
            client.get("/")
            response = client.get(url_for("prod.edit_product", product=prod.name))
            assert bytes(prod.name, "UTF-8") in response.data
            data = {
                "csrf_token": g.csrf_token,
                "name": prod.name,
                "description": prod.description,
                "responsable_id": prod.responsable_id,
                "category_id": prod.category_id,
                "supplier_id": prod.supplier_id,
                "meas_unit": prod.meas_unit,
                "min_stock": prod.min_stock,
                "ord_qty": prod.ord_qty,
                "critical": "on",
                "to_order": "on",
                "in_use": "",
                "submit": True,
            }
            response = client.post(url_for("prod.edit_product", product=prod.name),
                                   data=data, follow_redirects=True)
            assert len(response.history) == 1
            assert response.history[0].status_code == 302
            assert response.status_code == 200
            assert quote(response.request.path) == url_for("prod.edit_product", product=prod.name)
            assert b"Product updated" not in response.data
            assert bytes(prod.name, "UTF-8") in response.data
            assert f"Can't 'retire' a product that needs to be ordered" in unescape(response.text)
        db_session.refresh(prod)
        assert prod.in_use
        prod.to_order = False
        db_session.commit()


def test_failed_edit_product_bad_name(client: FlaskClient, admin_logged_in):
    with client:
        client.get("/")
        response = client.get(url_for("prod.edit_product", product="not_existing_product"), follow_redirects=True)
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("prod.products", ordered_by="code")
        assert b"not_existing_product does not exist!" in response.data
# endregion


# region: delete product
def test_delete_product(client: FlaskClient, admin_logged_in):
    with dbSession() as db_session:
        prod = Product(
            "new_product", "some description",
            db_session.get(User, 1),
            db_session.get(Category, 1),
            db_session.get(Supplier, 1),
            "pc", 0, 1)
        db_session.add(prod)
        db_session.commit()
        assert prod.id
    with client:
        client.get("/")
        response = client.get(url_for("prod.edit_product", product=prod.name))
        assert bytes(prod.name, "UTF-8") in response.data
        data = {
            "csrf_token": g.csrf_token,
            "name": prod.name,
            "description": prod.description,
            "responsable_id": prod.responsable_id,
            "category_id": prod.category_id,
            "supplier_id": prod.supplier_id,
            "meas_unit": prod.meas_unit,
            "min_stock": prod.min_stock,
            "ord_qty": prod.ord_qty,
            "critical": "",
            "to_order": "",
            "in_use": "on",
            "delete": True,
        }
        response = client.post(url_for("prod.edit_product", product=prod.name),
                            data=data, follow_redirects=True)
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("prod.products", ordered_by="code")
        assert f"Product '{prod.name}' has been deleted" in unescape(response.text)
    with dbSession() as db_session:
        assert not db_session.get(Product, prod.id)
# endregion


# region: order page
def test_order_page(client: FlaskClient, admin_logged_in):
    no_product = 10
    with client:
        client.get("/")
        response = client.get(url_for("prod.products_to_order"), follow_redirects=True)
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("main.index")
        assert b"Admin dashboard" in response.data
        assert b"There are no products that need to be ordered" in response.data
        with dbSession() as db_session:
            products = [db_session.get(Product, id) for id in range(1, no_product + 1)]
            for product in products:
                product.to_order = True
            db_session.commit()
            response = client.get(url_for("prod.products_to_order"), follow_redirects=True)
            assert len(response.history) == 0
            assert response.status_code == 200
            assert b"Products to order" in response.data
            assert b"Update" in response.data
            assert b"All ordered" in response.data
            for product in products:
                assert bytes(product.name, "UTF-8") in response.data
            assert f'There are <span class="text-secondary">{len(products)} products</span> that need to be orderer'
            for _ in range(no_product-1):
                prod = products.pop()
                client.get(url_for("prod.products_to_order"))
                data = {
                    "csrf_token": g.csrf_token,
                    str(prod.id): "on"
                }
                response = client.post(url_for("prod.products_to_order"), data=data)
                assert b"Products to order" in response.data
                assert b"Products updated" in response.data
                for product in products:
                    assert bytes(product.name, "UTF-8") in response.data
            assert len(products) == 1
            client.get(url_for("prod.products_to_order"))
            data = {
                "csrf_token": g.csrf_token,
                str(products[0].id): "on"
            }
            response = client.post(url_for("prod.products_to_order"), data=data, follow_redirects=True)
            assert len(response.history) == 1
            assert response.history[0].status_code == 302
            assert response.status_code == 200
            assert response.request.path == url_for("main.index")
            assert b"Products to order" not in response.data
            assert b"Admin dashboard" in response.data
            assert b"Products updated" in response.data
            assert b"There are no products that need to be ordered" in response.data


def test_order_page_all_ordered(client: FlaskClient, admin_logged_in):
    no_product = 10
    with client:
        client.get("/")
        with dbSession() as db_session:
            products = [db_session.get(Product, id) for id in range(1, no_product + 1)]
            for product in products:
                product.to_order = True
            db_session.commit()
            response = client.get(url_for("prod.products_to_order"), follow_redirects=True)
            assert len(response.history) == 0
            assert response.status_code == 200
            assert b"Products to order" in response.data
            assert b"Update" in response.data
            assert b"All ordered" in response.data
            for product in products:
                assert bytes(product.name, "UTF-8") in response.data
            assert f'There are <span class="text-secondary">{len(products)} products</span> that need to be orderer'
            response = client.get(url_for("prod.all_products_ordered"), follow_redirects=True)
            assert len(response.history) == 1
            assert response.history[0].status_code == 302
            assert response.status_code == 200
            assert response.request.path == url_for("main.index")
            assert b"All products ordered" in response.data
            for product in products:
                db_session.refresh(product)
                assert not product.to_order
        response = client.get(url_for("prod.products_to_order"), follow_redirects=True)
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("main.index")
        assert b"Admin dashboard" in response.data
        assert b"There are no products that need to be ordered" in response.data


def test_order_page_no_csrf(client: FlaskClient, admin_logged_in):
    with client:
        with dbSession() as db_session:
            prod = db_session.get(Product, 1)
            prod.to_order = True
            db_session.commit()
        client.get("/")
        client.get(url_for("prod.products_to_order"))
        data = {
            "1": "on"
        }
        response = client.post(url_for("prod.products_to_order"), data=data, follow_redirects=True)
        assert len(response.history) == 0
        assert response.status_code == 200
        assert b"Products to order" in response.data
        assert b"The CSRF token is missing" in response.data
# endregion
