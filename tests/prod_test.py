"""Products blueprint tests."""

from html import unescape
from urllib.parse import quote

import pytest
from flask import g, session, url_for
from flask.testing import FlaskClient
from sqlalchemy import select

from database import Category, Product, Supplier, User, dbSession
from messages import Message

pytestmark = pytest.mark.prod


# region: products page
def test_products_page_user_logged_in(
        client: FlaskClient, user_logged_in: User):
    """test_products_page_user_logged_in"""
    with client:
        client.get("/")
        assert session["user_name"] == user_logged_in.name
        assert not session["admin"]
        response = client.get(
            url_for("prod.products", ordered_by="code"), follow_redirects=True)
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("auth.login")
        assert str(Message.UI.Auth.AdminReq()) in response.text


def test_products_page_admin_logged_in(
        client: FlaskClient, admin_logged_in: User):
    """test_products_page_admin_logged_in"""
    with client:
        client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        response = client.get(
            url_for("prod.products", ordered_by="code"), follow_redirects=True)
        assert len(response.history) == 0
        assert response.status_code == 200
        assert str(Message.UI.Auth.AdminReq()) not in response.text
        assert "Products" in response.text
        assert "Strikethrough products are no longer in use" in response.text
        assert "AAA Batteries" in response.text
        assert "Cleaning Cloth" in response.text
        assert "user1" in response.text
        assert "user3" in response.text
        assert "Electronics" in response.text
        assert "Groceries" in response.text
        assert "Carrefour" in response.text
        assert "Amazon" in response.text
        assert '<span class="text-secondary">Code</span>' in response.text
        assert ('<a class="link-dark link-offset-2 link-underline-opacity-50' +
            ' link-underline-opacity-100-hover" href="' +
            url_for("prod.products", ordered_by="code") +
            '">Code</a>') not in response.text
        assert ("link-dark link-offset-2 link-underline-opacity-50 " +
                "link-underline-opacity-100-hover") in response.text
        assert "text-decoration-line-through" in response.text
        with dbSession() as db_session:
            db_session.get(Product, 43).in_use = True
            db_session.commit()
            response = client.get(url_for("prod.products", ordered_by="code"))
            assert "text-decoration-line-through" not in response.text
            db_session.get(Product, 43).in_use = False
            db_session.commit()
        response = client.get(
            url_for("prod.products", ordered_by="responsible"),
            follow_redirects=True)
        assert len(response.history) == 0
        assert response.status_code == 200
        assert '<span class="text-secondary">Responsible</span>' \
            in response.text
        response = client.get(
            url_for("prod.products", ordered_by="category"),
            follow_redirects=True)
        assert len(response.history) == 0
        assert response.status_code == 200
        assert '<span class="text-secondary">Category</span>' in response.text
        response = client.get(
            url_for("prod.products", ordered_by="supplier"),
            follow_redirects=True)
        assert len(response.history) == 0
        assert response.status_code == 200
        assert '<span class="text-secondary">Supplier</span>' in response.text
        response = client.get(
            url_for("prod.products", ordered_by="not_existing"),
            follow_redirects=True)
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert quote(response.request.path) == url_for("prod.products",
                                                       ordered_by="code")
        assert str(Message.Product.NoSort("not_existing")) in response.text
# endregion


# region: new product
@pytest.mark.parametrize(
    ("name", "description", "responsible_id", "category_id", "supplier_id",
     "meas_unit", "min_stock", "ord_qty", "critical"), (
        ("new", "some description", 1, 1, 1,
         "pc", 0, 1, ""),
        ("new product", "some very long description", 2, 1, 3,
         "meas", 10, 100, "on"),
        ("new", "some description", 7, 7, 4,
         "pc", 2, 8, ""),
))
def test_new_product(
        client: FlaskClient, admin_logged_in: User,
        name, description, responsible_id, category_id, supplier_id,
        meas_unit, min_stock, ord_qty, critical):
    """test_new_product"""
    with client:
        client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        response = client.get(url_for("prod.new_product"))
        assert "Create product" in response.text
        data = {
            "csrf_token": g.csrf_token,
            "name": name,
            "description": description,
            "responsible_id": responsible_id,
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
        assert response.request.path == url_for("prod.products",
                                                ordered_by="code")
        assert str(Message.Product.Created(name)) in unescape(response.text)
        assert name in response.text
    with dbSession() as db_session:
        prod = db_session.scalar(select(Product).filter_by(name=name))
        assert prod.description == description
        assert prod.responsible == db_session.get(User, responsible_id)
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


@pytest.mark.parametrize(
    ("name", "description", "responsible_id", "category_id", "supplier_id",
     "meas_unit", "min_stock", "ord_qty", "flash_message"), (
        ("", "some description", 1, 1, 1,
         "pc", 0, 1, str(Message.Product.Name.Req())),
        ("pr", "some description", 1, 1, 1,
         "pc", 0, 1, str(Message.Product.Name.LenLimit())),
        ("prod_prod_prod_p", "some description", 1, 1, 1,
         "pc", 0, 1, str(Message.Product.Name.LenLimit())),
        ("AA Batteries", "some description", 1, 1, 1,
         "pc", 0, 1, str(Message.Product.Name.Exists("AA Batteries"))),
        ("new_product", "", 1, 1, 1,
         "pc", 0, 1, str(Message.Product.Description.Req())),
        ("new_product", "de", 1, 1, 1,
         "pc", 0, 1, str(Message.Product.Description.LenLimit())),
        ("new_product",
         "desc-desc-desc-desc-desc-desc-desc-desc-desc-desc-desc", 1, 1, 1,
         "pc", 0, 1, str(Message.Product.Description.LenLimit())),
        ("new_product", "some description", None, 1, 1,
         "pc", 0, 1, "Not a valid choice"),
        ("new_product", "some description", "", 1, 1,
         "pc", 0, 1, "Not a valid choice"),
        ("new_product", "some description", " ", 1, 1,
         "pc", 0, 1, "Not a valid choice"),
        ("new_product", "some description", 5, 1, 1,
         "pc", 0, 1, "Not a valid choice"),
        ("new_product", "some description", 6, 1, 1,
         "pc", 0, 1, "Not a valid choice"),
        ("new_product", "some description", 1, None, 1,
         "pc", 0, 1, "Not a valid choice"),
        ("new_product", "some description", 1, "", 1,
         "pc", 0, 1, "Not a valid choice"),
        ("new_product", "some description", 1, " ", 1,
         "pc", 0, 1, "Not a valid choice"),
        ("new_product", "some description", 1, 8, 1,
         "pc", 0, 1, "Not a valid choice"),
        ("new_product", "some description", 1, 1, None,
         "pc", 0, 1, "Not a valid choice"),
        ("new_product", "some description", 1, 1, "",
         "pc", 0, 1, "Not a valid choice"),
        ("new_product", "some description", 1, 1, " ",
         "pc", 0, 1, "Not a valid choice"),
        ("new_product", "some description", 1, 1, 5,
        "pc", 0, 1, "Not a valid choice"),
        ("new_product", "some description", 1, 1, 1,
        "", 0, 1, str(Message.Product.MeasUnit.Req())),
        ("new_product", "some description", 1, 1, 1,
        "pc", "", 1, str(Message.Product.MinStock.Req())),
        ("new_product", "some description", 1, 1, 1,
        "pc", -1, 1, str(Message.Product.MinStock.Invalid())),
        ("new_product", "some description", 1, 1, 1,
        "pc", "a", 1, "Not a valid integer value"),
        ("new_product", "some description", 1, 1, 1,
        "pc", 0, "", str(Message.Product.OrdQty.Req())),
        ("new_product", "some description", 1, 1, 1,
        "pc", 0, 0, str(Message.Product.OrdQty.Invalid())),
        ("new_product", "some description", 1, 1, 1,
        "pc", 0, -1, str(Message.Product.OrdQty.Invalid())),
        ("new_product", "some description", 1, 1, 1,
        "pc", 0, "a", "Not a valid integer value"),
))
def test_failed_new_product(
        client: FlaskClient, admin_logged_in: User,
        name, description, responsible_id, category_id, supplier_id,
        meas_unit, min_stock, ord_qty, flash_message):
    """test_failed_new_product"""
    with client:
        client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        response = client.get(url_for("prod.new_product"))
        assert "Create product" in response.text
        data = {
            "csrf_token": g.csrf_token,
            "name": name,
            "description": description,
            "responsible_id": responsible_id,
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
        assert "Create product" in response.text
        assert str(Message.Product.Created(name)) not in unescape(response.text)
        assert flash_message in unescape(response.text)
    with dbSession() as db_session:
        if name != "AA Batteries":
            assert not db_session.scalar(select(Product).filter_by(name=name))
# endregion


# region: edit product
@pytest.mark.parametrize(
    ("prod_id", "new_name", "new_description",
     "new_responsible_id", "new_category_id", "new_supplier_id",
     "new_meas_unit", "new_min_stock", "new_ord_qty",
     "new_critical", "new_to_order", "new_in_use"), (
        ("1", "new name", "new description",
        1, 2, 1,
        "new_meas_unit", 100, 100,
        "", "on", "on"),
        ("2", "new name", "new description",
        1, 2, 1,
        "new_meas_unit", 100, 100,
        "on", "on", "on"),
        ("22", "new name", "new description",
        2, 2, 1,
        "new_meas_unit", 100, 100,
        "on", "on", "on"),
        ("6", "new name", "new description",
        1, 2, 4,
        "new_meas_unit", 100, 100,
        "on", "", ""),
        ("10", "new name", "new description",
        7, 4, 2,
        "new_meas_unit", 100, 100,
        "on", "", ""),
        ("32", "new name", "new description",
        2, 7, 3,
        "new_meas_unit", 100, 100,
        "on", "", ""),
))
def test_edit_product(
        client: FlaskClient, admin_logged_in: User,
        prod_id, new_name, new_description,
        new_responsible_id, new_category_id, new_supplier_id,
        new_meas_unit, new_min_stock, new_ord_qty,
        new_critical, new_to_order, new_in_use):
    """test_edit_product"""
    with dbSession() as db_session:
        prod = db_session.get(Product, prod_id)
        orig_prod = {key: value for key, value in prod.__dict__.items()
            if key in {"name", "description", "responsible_id", "category_id",
                       "supplier_id", "meas_unit", "min_stock", "ord_qty",
                       "critical", "to_order", "in_use"}}
        with client:
            client.get("/")
            assert session["user_name"] == admin_logged_in.name
            assert session["admin"]
            client.get(url_for("prod.products", ordered_by="code"))
            response = client.get(url_for("prod.edit_product",
                                          product=prod.name))
            assert len(response.history) == 0
            assert response.status_code == 200
            assert orig_prod["name"] in response.text
            data = {
                "csrf_token": g.csrf_token,
                "name": new_name,
                "description": new_description,
                "responsible_id": new_responsible_id,
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
            response = client.post(
                url_for("prod.edit_product", product=orig_prod["name"]),
                data=data,
                follow_redirects=True)
            assert len(response.history) == 1
            assert response.history[0].status_code == 302
            assert response.status_code == 200
            assert quote(response.request.path) == url_for("prod.products",
                                                           ordered_by="code")
            assert str(Message.Product.Updated()) in response.text
            assert new_name in response.text
            assert new_description in response.text
        db_session.refresh(prod)
        assert prod.name == new_name
        assert prod.description == new_description
        assert prod.responsible_id == new_responsible_id
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
    ("attr", "value"), (
        ("done_inv", False),
        ("req_inv", True),
))
def test_edit_product_last_responsible_product(
        client: FlaskClient, admin_logged_in: User, attr: str, value: bool):
    """test_edit_product_last_responsible_product."""
    def formify_bool(value: bool) -> str:
        """Transform bool to form campatible ("on"/"")"""
        if value:
            return "on"
        return ""
    def change_responsible_data(
            csrf: str, product: Product, new_resp_id: int) -> dict:
        """Build change product responsible data for form posting."""
        return {
            "csrf_token": csrf,
            "name": product.name,
            "description": product.description,
            "responsible_id": new_resp_id,
            "category_id": product.category_id,
            "supplier_id": product.supplier_id,
            "meas_unit": product.meas_unit,
            "min_stock": str(product.min_stock),
            "ord_qty": str(product.ord_qty),
            "critical": formify_bool(product.critical),
            "to_order": formify_bool(product.to_order),
            "in_use": formify_bool(product.in_use),
            "submit": True,
        }
    with dbSession() as db_session:
        user = db_session.get(User, 4)
        initial_total_products = user.all_products
        setattr(user, attr, value)
        db_session.commit()
        db_session.refresh(user)
        assert getattr(user, attr) is value
        products = db_session.scalars(
            select(Product)
            .filter_by(responsible_id=user.id)).all()
        with client:
            client.get("/")
            for product in products:
                client.get(url_for("prod.edit_product", product=product.name))
                data = change_responsible_data(
                    g.csrf_token, product, admin_logged_in.id)
                response = client.post(
                    url_for("prod.edit_product", product=product.name),
                    data=data,
                    follow_redirects=True)
                assert str(Message.Product.Updated()) in response.text
                db_session.refresh(product)
                assert product.responsible_id == admin_logged_in.id
            db_session.refresh(user)
            assert not user.all_products
            assert getattr(user, attr) is not value
            # teardown
            for product in products:
                client.get(url_for("prod.edit_product", product=product.name))
                data = change_responsible_data(
                    g.csrf_token, product, user.id)
                response = client.post(
                    url_for("prod.edit_product", product=product.name),
                    data=data,
                    follow_redirects=True)
                assert str(Message.Product.Updated()) in response.text
                db_session.refresh(product)
                assert product.responsible_id == user.id
            db_session.refresh(user)
            assert user.all_products == initial_total_products





@pytest.mark.parametrize(
    ("prod_id", "new_name", "new_description",
     "new_responsible_id", "new_category_id", "new_supplier_id",
     "new_meas_unit", "new_min_stock", "new_ord_qty",
     "flash_message"), (
        # name
        ("2", "", "new description",
         1, 1, 1,
         "new_meas_unit", 100, 100,
         str(Message.Product.Name.Req())),
        ("4", "pr", "new description",
         1, 1, 1,
         "new_meas_unit", 100, 100,
         str(Message.Product.Name.LenLimit())),
        ("5", "prod_prod_prod_p", "new description",
         1, 1, 1,
         "new_meas_unit", 100, 100,
         str(Message.Product.Name.LenLimit())),
        # description
        ("6", "new_product", "",
         1, 1, 1,
         "new_meas_unit", 100, 100,
         str(Message.Product.Description.Req())),
        ("3", "new_product", "de",
         1, 1, 1,
         "new_meas_unit", 100, 100,
         str(Message.Product.Description.LenLimit())),
        ("7", "new_product",
         "desc-desc-desc-desc-desc-desc-desc-desc-desc-desc-desc",
         1, 1, 1,
         "new_meas_unit", 100, 100,
         str(Message.Product.Description.LenLimit())),
        # responsible
        ("8", "new_product", "new description",
         None, 1, 1,
         "new_meas_unit", 100, 100,
         "Not a valid choice"),
        ("9", "new_product", "new description",
         "", 1, 1,
         "new_meas_unit", 100, 100,
         "Not a valid choice"),
        ("10", "new_product", "new description",
         " ", 1, 1,
         "new_meas_unit", 100, 100,
         "Not a valid choice"),
        ("10", "new_product", "new description",
         5, 1, 1,
         "new_meas_unit", 100, 100,
         "Not a valid choice"),
        ("11", "new_product", "new description",
         6, 1, 1,
         "new_meas_unit", 100, 100,
         "Not a valid choice"),
        ("12", "new_product", "new description",
         8, 1, 1,
         "new_meas_unit", 100, 100,
         "Not a valid choice"),
        # category
        ("13", "new_product", "new description",
         1, None, 1,
         "new_meas_unit", 100, 100,
         "Not a valid choice"),
        ("14", "new_product", "new description",
         1, "", 1, "new_meas_unit", 100, 100,
         "Not a valid choice"),
        ("15", "new_product", "new description",
         1, " ", 1,
         "new_meas_unit", 100, 100,
         "Not a valid choice"),
        ("16", "new_product", "new description",
         1, 8, 1,
         "new_meas_unit", 100, 100,
         "Not a valid choice"),
        ("17", "new_product", "new description",
         1, 9, 1,
         "new_meas_unit", 100, 100,
         "Not a valid choice"),
        # supplier
        ("18", "new_product", "new description",
         1, 1, None,
         "new_meas_unit", 100, 100,
         "Not a valid choice"),
        ("19", "new_product", "new description",
         1, 1, "",
         "new_meas_unit", 100, 100,
         "Not a valid choice"),
        ("20", "new_product", "new description",
         1, 1, " ",
         "new_meas_unit", 100, 100,
         "Not a valid choice"),
        ("21", "new_product", "new description",
         1, 1, 5,
         "new_meas_unit", 100, 100,
         "Not a valid choice"),
        ("22", "new_product", "new description",
         1, 1, 6,
         "new_meas_unit", 100, 100,
         "Not a valid choice"),
        # meas_unit
        ("23", "new_product", "new description",
         1, 1, 1,
         "", 100, 100,
         str(Message.Product.MeasUnit.Req())),
        # min_stock
        ("24", "new_product", "new description",
         1, 1, 1,
         "new_meas_unit", "", 100,
         str(Message.Product.MinStock.Req())),
        ("25", "new_product", "new description",
         1, 1, 1,
         "new_meas_unit", -1, 100,
         str(Message.Product.MinStock.Invalid())),
        ("26", "new_product", "new description",
         1, 1, 1,
         "new_meas_unit", "a", 100,
         "Not a valid integer value"),
        # ord_qty
        ("27", "new_product", "new description",
        1, 1, 1,
        "new_meas_unit", 100, "",
        str(Message.Product.OrdQty.Req())),
        ("28", "new_product", "new description",
        1, 1, 1,
        "new_meas_unit", 100, 0,
        str(Message.Product.OrdQty.Invalid())),
        ("29", "new_product", "new description",
        1, 1, 1,
        "new_meas_unit", 100, -1,
        str(Message.Product.OrdQty.Invalid())),
        ("30", "new_product", "new description",
        1, 1, 1,
        "new_meas_unit", 100, "a",
        "Not a valid integer value"),
))
def test_failed_edit_product_form_validators(
        client: FlaskClient, admin_logged_in: User,
        prod_id, new_name, new_description,
        new_responsible_id, new_category_id, new_supplier_id,
        new_meas_unit, new_min_stock, new_ord_qty,
        flash_message):
    """test_failed_edit_product_form_validators"""
    with dbSession() as db_session:
        prod = db_session.get(Product, prod_id)
        orig_prod = {key: value for key, value in prod.__dict__.items()
            if key in {"name", "description", "responsible_id", "category_id",
                       "supplier_id", "meas_unit", "min_stock", "ord_qty",
                       "critical", "to_order", "in_use"}}
        with client:
            client.get("/")
            assert session["user_name"] == admin_logged_in.name
            assert session["admin"]
            response = client.get(
                url_for("prod.edit_product", product=prod.name))
            assert len(response.history) == 0
            assert response.status_code == 200
            assert orig_prod["name"] in response.text
            data = {
                "csrf_token": g.csrf_token,
                "name": new_name,
                "description": new_description,
                "responsible_id": new_responsible_id,
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
            response = client.post(url_for("prod.edit_product",
                                           product=orig_prod["name"]),
                data=data, follow_redirects=True)
            assert len(response.history) == 0
            assert response.status_code == 200
            assert str(Message.Product.Updated()) not in response.text
            assert orig_prod["name"] in response.text
            assert flash_message in unescape(response.text)
        db_session.refresh(prod)
        for key, value in orig_prod.items():
            assert getattr(prod, key) == value


def test_failed_edit_product_name_duplicate(
        client: FlaskClient, admin_logged_in: User):
    """test_failed_edit_product_name_duplicate"""
    with dbSession() as db_session:
        prod = db_session.get(Product, 2)
        orig_name = prod.name
        new_name = db_session.get(Product, 1).name
        with client:
            client.get("/")
            assert session["user_name"] == admin_logged_in.name
            assert session["admin"]
            client.get(url_for("prod.products", ordered_by="code"))
            response = client.get(url_for("prod.edit_product",
                                          product=orig_name))
            assert prod.name in response.text
            data = {
                "csrf_token": g.csrf_token,
                "name": new_name,
                "description": prod.description,
                "responsible_id": prod.responsible_id,
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
            response = client.post(
                url_for("prod.edit_product", product=orig_name),
                data=data,
                follow_redirects=True)
            assert len(response.history) == 0
            assert response.status_code == 200
            assert str(Message.Product.Updated()) not in response.text
            assert orig_name in response.text
            assert str(Message.Product.Name.Exists(new_name)) in response.text
        db_session.refresh(prod)
        assert prod.name != new_name


def test_failed_edit_product_to_order_in_use_validator(
        client: FlaskClient, admin_logged_in: User):
    """test_failed_edit_product_to_order_in_use_validator"""
    with dbSession() as db_session:
        prod = db_session.get(Product, 3)
        prod.in_use = False
        db_session.commit()
        with client:
            client.get("/")
            assert session["user_name"] == admin_logged_in.name
            assert session["admin"]
            client.get(url_for("prod.products", ordered_by="code"))
            response = client.get(url_for("prod.edit_product",
                                          product=prod.name))
            assert prod.name in response.text
            data = {
                "csrf_token": g.csrf_token,
                "name": prod.name,
                "description": prod.description,
                "responsible_id": prod.responsible_id,
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
            response = client.post(
                url_for("prod.edit_product", product=prod.name),
                data=data,
                follow_redirects=True)
            assert len(response.history) == 0
            assert response.status_code == 200
            assert str(Message.Product.Updated()) not in response.text
            assert prod.name in response.text
            assert str(Message.Product.ToOrder.Retired()) \
                in unescape(response.text)
        db_session.refresh(prod)
        assert not prod.to_order

        prod.in_use = True
        prod.to_order = True
        db_session.commit()
        with client:
            client.get("/")
            client.get(url_for("prod.products", ordered_by="code"))
            response = client.get(url_for("prod.edit_product",
                                          product=prod.name))
            assert prod.name in response.text
            data = {
                "csrf_token": g.csrf_token,
                "name": prod.name,
                "description": prod.description,
                "responsible_id": prod.responsible_id,
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
            response = client.post(
                url_for("prod.edit_product", product=prod.name),
                data=data,
                follow_redirects=True)
            assert len(response.history) == 0
            assert response.status_code == 200
            assert str(Message.Product.Updated()) not in response.text
            assert prod.name in response.text
            assert str(Message.Product.InUse.ToOrder()) \
                in unescape(response.text)
        db_session.refresh(prod)
        assert prod.in_use
        prod.to_order = False
        db_session.commit()


def test_failed_edit_product_bad_name(
        client: FlaskClient, admin_logged_in: User):
    """test_failed_edit_product_bad_name"""
    with client:
        client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        response = client.get(
            url_for("prod.edit_product", product="not_existing_product"),
            follow_redirects=True)
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("prod.products",
                                                ordered_by="code")
        assert str(Message.Product.NotExists("not_existing_product")) \
            in response.text
# endregion


# region: delete product
def test_delete_product(
        client: FlaskClient, admin_logged_in: User):
    """test_delete_product"""
    with dbSession() as db_session:
        prod = Product(
            name="new_product",
            description="some description",
            responsible=db_session.get(User, 1),
            category=db_session.get(Category, 1),
            supplier=db_session.get(Supplier, 1),
            meas_unit="pc",
            min_stock=0,
            ord_qty=1)
        db_session.add(prod)
        db_session.commit()
        assert prod.id
    with client:
        client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        response = client.get(url_for("prod.edit_product", product=prod.name))
        assert prod.name in response.text
        data = {
            "csrf_token": g.csrf_token,
            "name": prod.name,
            "description": prod.description,
            "responsible_id": prod.responsible_id,
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
        response = client.post(
            url_for("prod.edit_product", product=prod.name),
            data=data,
            follow_redirects=True)
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("main.index")
        assert str(Message.Product.Deleted(prod.name)) \
            in unescape(response.text)
    with dbSession() as db_session:
        assert not db_session.get(Product, prod.id)
# endregion


# region: order page
def test_order_page(client: FlaskClient, admin_logged_in: User):
    """test_order_page"""
    numb_products = 10
    with client:
        client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        response = client.get(
            url_for("prod.products_to_order"), follow_redirects=True)
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("main.index")
        assert "Admin dashboard" in response.text
        assert str(Message.Product.NoOrder()) in response.text
        with dbSession() as db_session:
            products = [db_session.get(Product, id)
                        for id in range(1, numb_products + 1)]
            for product in products:
                product.to_order = True
            db_session.commit()
            response = client.get(
                url_for("prod.products_to_order"), follow_redirects=True)
            assert len(response.history) == 0
            assert response.status_code == 200
            assert "Products to order" in response.text
            assert "Update" in response.text
            assert "All ordered" in response.text
            for product in products:
                assert product.name in response.text
            assert ('There are <span class="text-secondary">' +
                    f'{len(products)} products</span> ' +
                    'that need to be ordered') in response.text
            for _ in range(numb_products-1):
                prod = products.pop()
                client.get(url_for("prod.products_to_order"))
                data = {
                    "csrf_token": g.csrf_token,
                    str(prod.id): "on"
                }
                response = client.post(
                    url_for("prod.products_to_order"), data=data)
                assert "Products to order" in response.text
                assert str(Message.Product.Ordered()) in response.text
                for product in products:
                    assert product.name in response.text
            assert len(products) == 1
            client.get(url_for("prod.products_to_order"))
            data = {
                "csrf_token": g.csrf_token,
                str(products[0].id): "on"
            }
            response = client.post(
                url_for("prod.products_to_order"),
                data=data,
                follow_redirects=True)
            assert len(response.history) == 1
            assert response.history[0].status_code == 302
            assert response.status_code == 200
            assert response.request.path == url_for("main.index")
            assert "Products to order" not in response.text
            assert "Admin dashboard" in response.text
            assert str(Message.Product.Ordered()) in response.text
            assert str(Message.Product.NoOrder()) in response.text


def test_order_page_all_ordered(client: FlaskClient, admin_logged_in: User):
    """test_order_page_all_ordered"""
    numb_product = 10
    with client:
        client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        with dbSession() as db_session:
            products = [db_session.get(Product, id)
                        for id in range(1, numb_product + 1)]
            for product in products:
                product.to_order = True
            db_session.commit()
            response = client.get(
                url_for("prod.products_to_order"), follow_redirects=True)
            assert len(response.history) == 0
            assert response.status_code == 200
            assert "Products to order" in response.text
            assert "Update" in response.text
            assert "All ordered" in response.text
            for product in products:
                assert product.name in response.text
            assert ('There are <span class="text-secondary">' +
                    f'{len(products)} products</span> ' +
                    'that need to be ordered') in response.text
            response = client.get(
                url_for("prod.all_products_ordered"), follow_redirects=True)
            assert len(response.history) == 1
            assert response.history[0].status_code == 302
            assert response.status_code == 200
            assert response.request.path == url_for("main.index")
            assert str(Message.Product.AllOrdered()) in response.text
            for product in products:
                db_session.refresh(product)
                assert not product.to_order
        response = client.get(
            url_for("prod.products_to_order"), follow_redirects=True)
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("main.index")
        assert "Admin dashboard" in response.text
        assert str(Message.Product.NoOrder()) in response.text


def test_order_page_no_csrf(client: FlaskClient, admin_logged_in: User):
    """test_order_page_no_csrf"""
    with dbSession() as db_session:
        prod = db_session.get(Product, 1)
        assert not prod.to_order
        prod.to_order = True
        db_session.commit()
        with client:
            client.get("/")
            assert session["user_name"] == admin_logged_in.name
            assert session["admin"]
            client.get(url_for("prod.products_to_order"))
            data = {
                "1": "on"
            }
            response = client.post(
                url_for("prod.products_to_order"),
                data=data,
                follow_redirects=True)
            assert len(response.history) == 0
            assert response.status_code == 200
            assert "Products to order" in response.text
            assert "The CSRF token is missing" in response.text
        prod.to_order = False
        db_session.commit()
# endregion
