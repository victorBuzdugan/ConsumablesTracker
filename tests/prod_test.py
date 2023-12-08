"""Products blueprint tests."""

import random
import re
import string
from html import unescape

import pytest
from flask import g, session, url_for
from flask.testing import FlaskClient
from hypothesis import assume, example, given
from hypothesis import strategies as st
from sqlalchemy import select

from constants import Constant
from database import Category, Product, Supplier, User, dbSession
from messages import Message
from tests import (InvalidProduct, ValidProduct, redirected_to,
                   test_categories, test_products, test_suppliers, test_users)

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
        assert redirected_to(url_for("auth.login"), response)
        assert str(Message.UI.Auth.AdminReq()) in response.text


def test_products_page_admin_logged_in(
        client: FlaskClient, admin_logged_in: User):
    """test_products_page_admin_logged_in"""
    products_in_use = [prod for prod in test_products if prod["in_use"]]
    crit_products = [prod for prod in test_products if prod["critical"]]
    crit_products_in_use = [prod for prod in test_products
                            if prod["critical"] and prod["in_use"]]
    with client:
        client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        response = client.get(
            url_for("prod.products", ordered_by="code"))
        assert response.status_code == 200
        # html elements
        assert str(Message.UI.Auth.AdminReq()) not in response.text
        assert str(Message.UI.Captions.Strikethrough("products")) \
            in response.text
        assert str(Message.UI.Captions.CriticalProducts()) in response.text
        assert str(Message.UI.Stats.Global("products",
                                           len(test_products),
                                           len(products_in_use))) \
            in response.text
        assert str(Message.UI.Stats.Global("critical_products",
                                           len(crit_products),
                                           len(crit_products_in_use))) \
            in response.text
        # links
        crit_prod_edit_link = re.compile(
            r'<a.*link-danger.*href="/product/edit/.*</a>', re.S)
        assert crit_prod_edit_link.search(response.text)
        sort_by_link = re.compile(
            r'<a.*link-dark.*href="/product/products-sorted-by.*</a>', re.S)
        assert sort_by_link.search(response.text)
        # products and description
        for product in test_products:
            assert product["name"] in response.text
            assert product["description"] in response.text
        disabled_product = re.compile(
            r'<span.*text-decoration-line-through.*<a.*href=".*</a>', re.S)
        assert disabled_product.search(response.text)
        # users
        for user in test_users:
            if user["has_products"]:
                assert user["name"] in response.text
            else:
                assert user["name"] not in response.text
        # categories
        for cat in test_categories:
            if cat["has_products"]:
                assert cat["name"] in response.text
            else:
                assert cat["name"] not in response.text
        # suppliers
        for sup in test_suppliers:
            if sup["has_products"]:
                assert sup["name"] in response.text
            else:
                assert sup["name"] not in response.text
        # add a product
        with dbSession() as db_session:
            new_product = Product(
                name=ValidProduct.name,
                description=ValidProduct.description,
                responsible=db_session.get(User, ValidProduct.responsible_id),
                category=db_session.get(Category, ValidProduct.category_id),
                supplier=db_session.get(Supplier, ValidProduct.supplier_id),
                meas_unit=ValidProduct.meas_unit,
                min_stock=ValidProduct.min_stock,
                ord_qty=ValidProduct.ord_qty)
            db_session.add(new_product)
            db_session.commit()
            response = client.get(
                url_for("prod.products", ordered_by="code"))
            assert re.search(
                r'<a.*link-dark.*href="' +
                url_for("prod.edit_product", product=ValidProduct.name),
                response.text, re.S)
            # make the product critical
            db_session.get(Product, new_product.id).critical = True
            db_session.commit()
            response = client.get(
                url_for("prod.products", ordered_by="code"))
            assert re.search(
                r'<a.*link-danger.*href="' +
                url_for("prod.edit_product", product=ValidProduct.name),
                response.text, re.S)
            # disable the product
            db_session.get(Product, new_product.id).in_use = False
            db_session.commit()
            response = client.get(
                url_for("prod.products", ordered_by="code"))
            assert re.search(
                r'span.*text-decoration-line-through.*<a.*link-danger.*href="' +
                url_for("prod.edit_product", product=ValidProduct.name),
                response.text, re.S)
            # delete the product
            db_session.delete(new_product)
            db_session.commit()
            response = client.get(
                url_for("prod.products", ordered_by="code"))
            assert url_for("prod.edit_product", product=ValidProduct.name) \
                not in response.text
        # sorting by
        response = client.get(
            url_for("prod.products", ordered_by="responsible"))
        assert response.status_code == 200
        assert re.search(r'<span.*text-secondary.*Responsible', response.text)
        response = client.get(
            url_for("prod.products", ordered_by="category"))
        assert response.status_code == 200
        assert re.search(r'<span.*text-secondary.*Category', response.text)
        response = client.get(
            url_for("prod.products", ordered_by="supplier"))
        assert response.status_code == 200
        assert re.search(r'<span.*text-secondary.*Supplier', response.text)
        # incorrect sorting
        response = client.get(
            url_for("prod.products", ordered_by="not_existing"),
            follow_redirects=True)
        assert redirected_to(url_for("prod.products", ordered_by="code"),
                             response)
        assert str(Message.Product.NoSort("not_existing")) in response.text
# endregion


# region: new product
create_prod_button = re.compile(r'input.*type="submit".*value="Create product"')


@given(name = st.text(min_size=Constant.Product.Name.min_length,
                      max_size=Constant.Product.Name.max_length)
           .map(lambda x: x.strip())
           .filter(lambda x: len(x) > Constant.Product.Name.min_length)
           .filter(lambda x: x not in [prod["name"] for prod in test_products]),
       description = st.text(min_size=Constant.Product.Description.min_length,
                             max_size=Constant.Product.Description.max_length)
           .map(lambda x: x.strip())
           .filter(lambda x: len(x) > Constant.Product.Description.min_length),
       responsible_id = st.sampled_from(
           [user["id"] for user in test_users
                if user["in_use"] and not user["reg_req"]]),
       category_id = st.sampled_from(
           [cat["id"] for cat in test_categories if cat["in_use"]]),
       supplier_id = st.sampled_from(
           [sup["id"] for sup in test_suppliers if sup["in_use"]]),
       meas_unit = st.text(min_size=1)
           .map(lambda x: x.strip())
           .filter(lambda x: len(x)>1),
       min_stock = st.integers(
           min_value=Constant.Product.MinStock.min_value,
           max_value=Constant.SQLite.Int.max_value),
       ord_qty = st.integers(
           min_value=Constant.Product.OrdQty.min_value,
           max_value=Constant.SQLite.Int.max_value),
       critical = st.sampled_from(["on", ""])
)
@example(name = ValidProduct.name,
         description = ValidProduct.description,
         responsible_id = ValidProduct.responsible_id,
         category_id = ValidProduct.category_id,
         supplier_id = ValidProduct.supplier_id,
         meas_unit = ValidProduct.meas_unit,
         min_stock = ValidProduct.min_stock,
         ord_qty = ValidProduct.ord_qty,
         critical = ValidProduct.critical
)
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
        assert create_prod_button.search(response.text)
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
        assert redirected_to(url_for("prod.products", ordered_by="code"),
                             response)
        assert str(Message.Product.Created(name)) in response.text
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


# region: failed product creation
def _test_failed_new_product(
        request: pytest.FixtureRequest,
        flash_message: str,
        name: str = ValidProduct.name,
        description: str = ValidProduct.description,
        responsible_id: int = ValidProduct.responsible_id,
        category_id: int = ValidProduct.category_id,
        supplier_id: int = ValidProduct.supplier_id,
        meas_unit: str = ValidProduct.meas_unit,
        min_stock: int = ValidProduct.min_stock,
        ord_qty: int = ValidProduct.ord_qty,
        check_db: bool = True):
    """Common logic for failed product creation"""
    client: FlaskClient = request.getfixturevalue("client")
    admin_logged_in: User = request.getfixturevalue("admin_logged_in")
    with client:
        client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        response = client.get(url_for("prod.new_product"))
        assert create_prod_button.search(response.text)
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
        response = client.post(url_for("prod.new_product"), data=data)
        assert response.status_code == 200
        assert create_prod_button.search(response.text)
        assert str(Message.Product.Created(name)) not in response.text
        assert flash_message in unescape(response.text)
    if check_db:
        with dbSession() as db_session:
            assert not db_session.scalar(select(Product).filter_by(name=name))


@given(name = st.one_of(
        # short name
        st.text(max_size=Constant.Product.Name.min_length - 1)
            .map(lambda x: x.strip()),
        # long name
        st.text(min_size=Constant.Product.Name.max_length + 1)
            .map(lambda x: x.strip())
            .filter(lambda x: len(x) > Constant.Product.Name.max_length)))
@example(name = None)
@example(name = InvalidProduct.short_name)
@example(name = InvalidProduct.long_name)
def test_failed_new_product_invalid_name(
        request: pytest.FixtureRequest, name: str):
    """Short, long or no name"""
    if name:
        flash_message = str(Message.Product.Name.LenLimit())
    else:
        flash_message = str(Message.Product.Name.Required())
    _test_failed_new_product(
        request=request,
        flash_message=flash_message,
        name=name
    )


@given(name = st.sampled_from([prod["name"] for prod in test_products]))
def test_failed_new_product_duplicate_name(
        request: pytest.FixtureRequest, name: str):
    """test_failed_new_product_duplicate_name"""
    flash_message = str(Message.Product.Name.Exists(name))
    _test_failed_new_product(
        request=request,
        flash_message=flash_message,
        name=name,
        check_db=False
    )


@given(description = st.one_of(
    # short description
    st.text(max_size=Constant.Product.Description.min_length - 1)
        .map(lambda x: x.strip()),
    # long description
    st.text(min_size=Constant.Product.Description.max_length + 1)
        .map(lambda x: x.strip())
        .filter(lambda x: len(x) > Constant.Product.Description.max_length)))
@example(description = None)
@example(description = InvalidProduct.short_description)
@example(description = InvalidProduct.long_description)
def test_failed_new_product_invalid_description(
        request: pytest.FixtureRequest, description: str):
    """Short, long or no description"""
    if description:
        flash_message = str(Message.Product.Description.LenLimit())
    else:
        flash_message = str(Message.Product.Description.Required())
    _test_failed_new_product(
        request=request,
        flash_message=flash_message,
        description=description
    )


@given(responsible_id = st.one_of(
        st.none(),
        st.text(alphabet=string.ascii_letters),
        st.integers()
        .filter(lambda x: x not in [user["id"] for user in test_users
                                    if user["in_use"] and not user["reg_req"]])
))
@example(responsible_id = InvalidProduct.responsible_id)
@example(responsible_id = [user["id"] for user in test_users
                           if not user["in_use"]][0])
@example(responsible_id = [user["id"] for user in test_users
                           if user["reg_req"]][0])
def test_failed_new_product_invalid_responsible_id(
        request: pytest.FixtureRequest, responsible_id):
    """test_failed_new_product_invalid_responsible_id"""
    flash_message = "Not a valid choice"
    _test_failed_new_product(
        request=request,
        flash_message=flash_message,
        responsible_id=responsible_id
    )


@given(category_id = st.one_of(
        st.none(),
        st.text(alphabet=string.ascii_letters),
        st.integers()
        .filter(lambda x: x not in [cat["id"] for cat in test_categories
                                    if cat["in_use"]])
))
@example(category_id = InvalidProduct.category_id)
@example(category_id = [cat["id"] for cat in test_categories
                           if not cat["in_use"]][0])
def test_failed_new_product_invalid_category_id(
        request: pytest.FixtureRequest, category_id):
    """test_failed_new_product_invalid_category_id"""
    flash_message = "Not a valid choice"
    _test_failed_new_product(
        request=request,
        flash_message=flash_message,
        category_id=category_id
    )


@given(supplier_id = st.one_of(
        st.none(),
        st.text(alphabet=string.ascii_letters),
        st.integers()
        .filter(lambda x: x not in [sup["id"] for sup in test_suppliers
                                    if sup["in_use"]])
))
@example(supplier_id = InvalidProduct.supplier_id)
@example(supplier_id = [sup["id"] for sup in test_suppliers
                           if not sup["in_use"]][0])
def test_failed_new_product_invalid_supplier_id(
        request: pytest.FixtureRequest, supplier_id):
    """test_failed_new_product_invalid_supplier_id"""
    flash_message = "Not a valid choice"
    _test_failed_new_product(
        request=request,
        flash_message=flash_message,
        supplier_id=supplier_id
    )


@pytest.mark.parametrize("meas_unit", [
    pytest.param("", id="Empty meas_unit"),
    pytest.param(" ", id="Empty meas_unit after strip"),
    pytest.param(None, id="None meas_unit"),
])
def test_failed_new_product_invalid_meas_unit(
        request: pytest.FixtureRequest, meas_unit):
    """test_failed_new_product_invalid_meas_unit"""
    flash_message = str(Message.Product.MeasUnit.Required())
    _test_failed_new_product(
        request=request,
        flash_message=flash_message,
        meas_unit=meas_unit
    )


@given(min_stock = st.one_of(
        st.none(),
        st.text(alphabet=string.ascii_letters),
        st.integers(max_value=Constant.Product.MinStock.min_value - 1),
        st.integers(min_value=Constant.SQLite.Int.max_value + 1)))
@example(min_stock = "")
@example(min_stock = " ")
@example(min_stock = InvalidProduct.small_min_stock)
def test_failed_new_product_invalid_min_stock(
        request: pytest.FixtureRequest, min_stock):
    """test_failed_new_product_invalid_min_stock"""
    if isinstance(min_stock, int):
        flash_message = str(Message.Product.MinStock.Invalid())
    elif not min_stock:
        flash_message = str(Message.Product.MinStock.Required())
    else:
        flash_message = "Not a valid integer value"
    _test_failed_new_product(
        request=request,
        flash_message=flash_message,
        min_stock=min_stock
    )


@given(ord_qty = st.one_of(
        st.none(),
        st.text(alphabet=string.ascii_letters),
        st.integers(max_value=Constant.Product.OrdQty.min_value - 1),
        st.integers(min_value=Constant.SQLite.Int.max_value + 1)))
@example(ord_qty = "")
@example(ord_qty = " ")
@example(ord_qty = InvalidProduct.small_ord_qty)
def test_failed_new_product_invalid_ord_qty(
        request: pytest.FixtureRequest, ord_qty):
    """test_failed_new_product_invalid_ord_qty"""
    if isinstance(ord_qty, int):
        flash_message = str(Message.Product.OrdQty.Invalid())
    elif not ord_qty:
        flash_message = str(Message.Product.OrdQty.Required())
    else:
        flash_message = "Not a valid integer value"
    _test_failed_new_product(
        request=request,
        flash_message=flash_message,
        ord_qty=ord_qty
    )
# endregion
# endregion


# region: edit product
update_prod_button = re.compile(r'input.*type="submit".*value="Update"')
delete_prod_button = re.compile(r'input.*type="submit".*value="Delete"')


@given(prod = st.sampled_from(test_products),
       new_name = st.text(
                min_size=Constant.Product.Name.min_length,
                max_size=Constant.Product.Name.max_length)
           .map(lambda x: x.strip())
           .filter(lambda x: len(x) > Constant.Product.Name.min_length)
           .filter(lambda x: x not in [prod["name"] for prod in test_products]),
       new_description = st.text(
                min_size=Constant.Product.Description.min_length,
                max_size=Constant.Product.Description.max_length)
           .map(lambda x: x.strip())
           .filter(lambda x: len(x) > Constant.Product.Description.min_length),
       new_responsible_id = st.sampled_from(
           [user["id"] for user in test_users
                if user["in_use"] and not user["reg_req"]]),
       new_category_id = st.sampled_from(
           [cat["id"] for cat in test_categories if cat["in_use"]]),
       new_supplier_id = st.sampled_from(
           [sup["id"] for sup in test_suppliers if sup["in_use"]]),
       new_meas_unit = st.text(min_size=1)
           .map(lambda x: x.strip())
           .filter(lambda x: len(x)>1),
       new_min_stock = st.integers(
           min_value=Constant.Product.MinStock.min_value,
           max_value=Constant.SQLite.Int.max_value),
       new_ord_qty = st.integers(
           min_value=Constant.Product.OrdQty.min_value,
           max_value=Constant.SQLite.Int.max_value),
       new_critical = st.sampled_from(["on", ""]),
       new_to_order = st.sampled_from(["on", ""]),
       new_in_use = st.sampled_from(["on", ""]),
)
def test_edit_product(
        client: FlaskClient,
        admin_logged_in: User,
        prod: dict[str],
        new_name: str,
        new_description: str,
        new_responsible_id: int,
        new_category_id: int,
        new_supplier_id: int,
        new_meas_unit: str,
        new_min_stock: int,
        new_ord_qty: int,
        new_critical: str,
        new_to_order: str,
        new_in_use: str):
    """test_edit_product"""
    if new_to_order:
        assume(new_in_use)
        assume(prod["in_use"])
    data = {
        "csrf_token": None,
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
    }
    with client:
        client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        # get products page for last url testing
        client.get(url_for("prod.products", ordered_by="code"))
        response = client.get(
            url_for("prod.edit_product", product=prod["name"]))
        assert response.status_code == 200
        assert prod["name"] in response.text
        assert update_prod_button.search(response.text)
        assert delete_prod_button.search(response.text)
        data["csrf_token"] = g.csrf_token
        response = client.post(
            url_for("prod.edit_product", product=prod["name"]),
            data=data,
            follow_redirects=True)
        # test last url
        assert redirected_to(url_for("prod.products", ordered_by="code"),
                             response)
    assert str(Message.Product.Updated(new_name)) in unescape(response.text)
    assert new_name in unescape(response.text)
    assert new_description in unescape(response.text)
    # db check and teardown
    with dbSession() as db_session:
        db_prod = db_session.get(Product, prod["id"])
        del data["csrf_token"]
        for attr, value in data.items():
            if attr in {"critical", "to_order", "in_use"}:
                assert getattr(db_prod, attr) == bool(value)
            else:
                assert getattr(db_prod, attr) == value
            setattr(db_prod, attr, prod[attr])
        db_session.commit()


@pytest.mark.parametrize(("attr", "value"), [
    pytest.param("done_inv", False,
                 id="Autoreset inventorying"),
    pytest.param("req_inv", True,
                 id="Autoreset inventorying request"),
])
def test_edit_product_last_responsible_product(
        client: FlaskClient, admin_logged_in: User, attr: str, value: bool):
    """Test autoreset values of done_inv and req_inv."""
    random_user = random.choice([user for user in test_users
                                 if user["has_products"] and not user["admin"]])
    with dbSession() as db_session:
        user = db_session.get(User, random_user["id"])
        initial_total_products = user.all_products
        setattr(user, attr, value)
        db_session.commit()
        db_session.refresh(user)
        assert getattr(user, attr) is value
        # change responsible for all products
        products = db_session.scalars(
            select(Product)
            .filter_by(responsible_id=user.id)).all()
        with client:
            client.get("/")
            for product in products:
                client.get(url_for("prod.edit_product", product=product.name))
                data = {
                    "csrf_token": g.csrf_token,
                    "name": product.name,
                    "description": product.description,
                    "responsible_id": admin_logged_in.id,
                    "category_id": product.category_id,
                    "supplier_id": product.supplier_id,
                    "meas_unit": product.meas_unit,
                    "min_stock": str(product.min_stock),
                    "ord_qty": str(product.ord_qty),
                    "critical": product.critical,
                    "to_order": product.to_order,
                    "in_use": product.in_use,
                }
                response = client.post(
                    url_for("prod.edit_product", product=product.name),
                    data=data,
                    follow_redirects=True)
                assert str(Message.Product.Updated(product.name)) \
                    in unescape(response.text)
                db_session.refresh(product)
                assert product.responsible_id == admin_logged_in.id
        # check value
        db_session.refresh(user)
        assert not user.all_products
        assert getattr(user, attr) is not value
        # teardown
        for product in products:
            db_session.get(
                Product, product.id).responsible_id = random_user["id"]
        db_session.commit()
        db_session.refresh(user)
        assert user.all_products == initial_total_products


# region: failed product edit
def _test_failed_edit_product(
        request: pytest.FixtureRequest,
        flash_message: str,
        new_name: str = ValidProduct.name,
        new_description: str = ValidProduct.description,
        new_responsible_id: int = ValidProduct.responsible_id,
        new_category_id: int = ValidProduct.category_id,
        new_supplier_id: int = ValidProduct.supplier_id,
        new_meas_unit: str = ValidProduct.meas_unit,
        new_min_stock: int = ValidProduct.min_stock,
        new_ord_qty: int = ValidProduct.ord_qty,
        new_critical: str = ValidProduct.critical,
        new_to_order: str = ValidProduct.to_order,
        new_in_use: str = ValidProduct.in_use):
    """Common logic for failed product edit"""
    client: FlaskClient = request.getfixturevalue("client")
    admin_logged_in: User = request.getfixturevalue("admin_logged_in")
    while True:
        prod = random.choice([prod for prod in test_products if prod["in_use"]])
        if prod["name"] != new_name:
            break
    data = {
        "csrf_token": None,
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
    }
    with client:
        client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        response = client.get(
            url_for("prod.edit_product", product=prod["name"]))
        assert response.status_code == 200
        assert prod["name"] in response.text
        assert update_prod_button.search(response.text)
        data["csrf_token"] = g.csrf_token
        response = client.post(
            url_for("prod.edit_product", product=prod["name"]),
            data=data)
        assert response.status_code == 200
    assert str(Message.Product.Updated(new_name)) not in unescape(response.text)
    assert prod["name"] in unescape(response.text)
    assert flash_message in unescape(response.text)
    # db check
    with dbSession() as db_session:
        db_prod = db_session.get(Product, prod["id"])
        del data["csrf_token"]
        for attr in data:
            assert getattr(db_prod, attr) == prod[attr]


@pytest.mark.parametrize("name", [
    pytest.param("",
                 id="Empty name"),
    pytest.param(None,
                 id="None name"),
    pytest.param(InvalidProduct.short_name,
                 id="Short name"),
    pytest.param(InvalidProduct.long_name,
                 id="Long name"),
    pytest.param(random.choice([prod["name"] for prod in test_products]),
                 id="Duplicate name"),
])
def test_failed_edit_product_invalid_name(
        request: pytest.FixtureRequest, name):
    """test_failed_edit_product_invalid_name"""
    if name in {prod["name"] for prod in test_products}:
        flash_message = str(Message.Product.Name.Exists(name))
    elif name:
        flash_message = str(Message.Product.Name.LenLimit())
    else:
        flash_message = str(Message.Product.Name.Required())
    _test_failed_edit_product(
        request=request,
        flash_message=flash_message,
        new_name=name
    )


@pytest.mark.parametrize("description", [
    pytest.param("",
                 id="Empty description"),
    pytest.param(None,
                 id="None description"),
    pytest.param(InvalidProduct.short_description,
                 id="Short description"),
    pytest.param(InvalidProduct.long_description,
                 id="Long description"),
])
def test_failed_edit_product_invalid_description(
        request: pytest.FixtureRequest, description):
    """test_failed_edit_product_invalid_description"""
    if description:
        flash_message = str(Message.Product.Description.LenLimit())
    else:
        flash_message = str(Message.Product.Description.Required())
    _test_failed_edit_product(
        request=request,
        flash_message=flash_message,
        new_description=description
    )


@pytest.mark.parametrize("responsible_id", [
    pytest.param("",
                 id="Empty responsible_id"),
    pytest.param(None,
                 id="None responsible_id"),
    pytest.param(InvalidProduct.responsible_id,
                 id="Not existing responsible_id"),
    pytest.param([user["id"] for user in test_users if not user["in_use"]][0],
                 id="Retired responsible"),
    pytest.param([user["id"] for user in test_users if user["reg_req"]][0],
                 id="Responsible with pending registration"),
])
def test_failed_edit_product_invalid_responsible(
        request: pytest.FixtureRequest, responsible_id):
    """test_failed_edit_product_invalid_responsible"""
    flash_message = "Not a valid choice"
    _test_failed_edit_product(
        request=request,
        flash_message=flash_message,
        new_responsible_id=responsible_id
    )


@pytest.mark.parametrize("category_id", [
    pytest.param("",
                 id="Empty category_id"),
    pytest.param(None,
                 id="None category_id"),
    pytest.param(InvalidProduct.category_id,
                 id="Not existing category"),
    pytest.param([cat["id"] for cat in test_categories if not cat["in_use"]][0],
                 id="Disabled category"),
])
def test_failed_edit_product_invalid_category(
        request: pytest.FixtureRequest, category_id):
    """test_failed_edit_product_invalid_category"""
    flash_message = "Not a valid choice"
    _test_failed_edit_product(
        request=request,
        flash_message=flash_message,
        new_category_id=category_id
    )


@pytest.mark.parametrize("supplier_id", [
    pytest.param("",
                 id="Empty supplier_id"),
    pytest.param(None,
                 id="None supplier_id"),
    pytest.param(InvalidProduct.supplier_id,
                 id="Not existing supplier"),
    pytest.param([sup["id"] for sup in test_suppliers if not sup["in_use"]][0],
                 id="Disabled supplier"),
])
def test_failed_edit_product_invalid_supplier(
        request: pytest.FixtureRequest, supplier_id):
    """test_failed_edit_product_invalid_supplier"""
    flash_message = "Not a valid choice"
    _test_failed_edit_product(
        request=request,
        flash_message=flash_message,
        new_supplier_id=supplier_id
    )


@pytest.mark.parametrize("meas_unit", [
    pytest.param("",
                 id="Empty meas_unit"),
    pytest.param(" ",
                 id="Empty meas_unit after strip"),
    pytest.param(None,
                 id="None meas_unit"),
])
def test_failed_edit_product_invalid_meas_unit(
        request: pytest.FixtureRequest, meas_unit):
    """test_failed_edit_product_invalid_meas_unit"""
    flash_message = str(Message.Product.MeasUnit.Required())
    _test_failed_edit_product(
        request=request,
        flash_message=flash_message,
        new_meas_unit=meas_unit
    )


@pytest.mark.parametrize("min_stock", [
    pytest.param("",
                 id="Empty min_stock"),
    pytest.param(" ",
                 id="Empty min_stock after strip"),
    pytest.param(None,
                 id="None min_stock"),
    pytest.param("a",
                 id="Not an integer"),
    pytest.param(InvalidProduct.small_min_stock,
                 id="Small min_stock"),
    pytest.param(Constant.SQLite.Int.max_value + 1,
                 id="Big min_stock"),
])
def test_failed_edit_product_invalid_min_stock(
        request: pytest.FixtureRequest, min_stock):
    """test_failed_edit_product_invalid_min_stock"""
    if isinstance(min_stock, int):
        flash_message = str(Message.Product.MinStock.Invalid())
    elif not min_stock:
        flash_message = str(Message.Product.MinStock.Required())
    else:
        flash_message = "Not a valid integer value"
    _test_failed_edit_product(
        request=request,
        flash_message=flash_message,
        new_min_stock=min_stock
    )


@pytest.mark.parametrize("ord_qty", [
    pytest.param("",
                 id="Empty ord_qty"),
    pytest.param(" ",
                 id="Empty ord_qty after strip"),
    pytest.param(None,
                 id="None ord_qty"),
    pytest.param("a",
                 id="Not an integer"),
    pytest.param(InvalidProduct.small_ord_qty,
                 id="Small ord_qty"),
    pytest.param(Constant.SQLite.Int.max_value + 1,
                 id="Big ord_qty"),
])
def test_failed_edit_product_invalid_ord_qty(
        request: pytest.FixtureRequest, ord_qty):
    """test_failed_edit_product_invalid_ord_qty"""
    if isinstance(ord_qty, int):
        flash_message = str(Message.Product.OrdQty.Invalid())
    elif not ord_qty:
        flash_message = str(Message.Product.OrdQty.Required())
    else:
        flash_message = "Not a valid integer value"
    _test_failed_edit_product(
        request=request,
        flash_message=flash_message,
        new_ord_qty=ord_qty
    )


@given(prod = st.sampled_from(
        [prod for prod in test_products if prod["in_use"]]))
def test_failed_edit_product_to_order_in_use_relation(
        client: FlaskClient, admin_logged_in: User, prod: dict[str]):
    """Test interlock of to_order and in_use"""
    data = {
        "csrf_token": None,
        "name": prod["name"],
        "description": prod["description"],
        "responsible_id": prod["responsible_id"],
        "category_id": prod["category_id"],
        "supplier_id": prod["supplier_id"],
        "meas_unit": prod["meas_unit"],
        "min_stock": prod["min_stock"],
        "ord_qty": prod["ord_qty"],
        "critical": prod["critical"],
        "to_order": True,
        "in_use": False,
    }
    # set product to_order
    with dbSession() as db_session:
        db_prod = db_session.get(Product, prod["id"])
        assert db_prod.in_use
        db_prod.to_order = True
        db_session.commit()
    # try to disable product
    with client:
        client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        response = client.get(
            url_for("prod.edit_product", product=prod["name"]))
        data["csrf_token"] = g.csrf_token
        response = client.post(
            url_for("prod.edit_product", product=prod["name"]),
            data=data)
    assert response.status_code == 200
    assert prod["name"] in unescape(response.text)
    assert str(Message.Product.Updated(prod["name"])) \
        not in unescape(response.text)
    assert str(Message.Product.InUse.ToOrder()) in unescape(response.text)
    # check db and set in_use
    with dbSession() as db_session:
        db_prod = db_session.get(Product, prod["id"])
        assert db_prod.in_use
        db_prod.to_order = False
        db_prod.in_use = False
        db_session.commit()
    # try to set to_order
    with client:
        client.get("/")
        response = client.get(
            url_for("prod.edit_product", product=prod["name"]))
        data["csrf_token"] = g.csrf_token
        response = client.post(
            url_for("prod.edit_product", product=prod["name"]),
            data=data)
    assert response.status_code == 200
    assert prod["name"] in unescape(response.text)
    assert str(Message.Product.Updated(prod["name"])) \
        not in unescape(response.text)
    assert str(Message.Product.ToOrder.Retired()) in unescape(response.text)
    # check db and teardown
    with dbSession() as db_session:
        db_prod = db_session.get(Product, prod["id"])
        assert not db_prod.to_order
        db_prod.in_use = True
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
        assert redirected_to(
            url_for("prod.products", ordered_by="code"),
                    response)
        assert str(Message.Product.NotExists("not_existing_product")) \
            in response.text
# endregion
# endregion


# region: delete product
def test_delete_product(
        client: FlaskClient, admin_logged_in: User):
    """test_delete_product"""
    with dbSession() as db_session:
        db_session.add(Product(
            name=ValidProduct.name,
            description=ValidProduct.description,
            responsible=db_session.get(User, ValidProduct.responsible_id),
            category=db_session.get(Category, ValidProduct.category_id),
            supplier=db_session.get(Supplier, ValidProduct.supplier_id),
            meas_unit=ValidProduct.meas_unit,
            min_stock=ValidProduct.min_stock,
            ord_qty=ValidProduct.ord_qty))
        db_session.commit()
    with client:
        client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        response = client.get(url_for("prod.edit_product",
                                      product=ValidProduct.name))
        assert ValidProduct.name in response.text
        data = {
            "csrf_token": g.csrf_token,
            "name": ValidProduct.name,
            "description": ValidProduct.description,
            "responsible_id": ValidProduct.responsible_id,
            "category_id": ValidProduct.category_id,
            "supplier_id": ValidProduct.supplier_id,
            "meas_unit": ValidProduct.meas_unit,
            "min_stock": ValidProduct.min_stock,
            "ord_qty": ValidProduct.ord_qty,
            "critical": "",
            "to_order": "",
            "in_use": "on",
            "delete": True,
        }
        response = client.post(
            url_for("prod.edit_product", product=ValidProduct.name),
            data=data,
            follow_redirects=True)
        assert redirected_to(url_for("main.index"), response)
        assert str(Message.Product.Deleted(ValidProduct.name)) \
            in unescape(response.text)
    with dbSession() as db_session:
        assert not db_session.scalar(select(Product)
                                     .filter_by(name=ValidProduct.name))
# endregion


# region: order page
update_order_button = re.compile(r'<input.*type="submit".*value="Update">')
all_ordered_button = re.compile(r'<a.*href=".*">All products ordered</a>')


@given(products_to_order = st.lists(
        elements=st.sampled_from(
            [product for product in test_products if product["in_use"]]),
        unique_by=lambda x: x["name"],
        min_size=5))
def test_order_page(client: FlaskClient, admin_logged_in: User,
                    products_to_order: list[dict[str]]):
    """test_order_page"""
    # check no products need to be ordered
    with client:
        response = client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        assert str(Message.UI.Main.ProdToOrder(0)) in response.text
        response = client.get(
            url_for("prod.products_to_order"), follow_redirects=True)
        assert redirected_to(url_for("main.index"), response)
        assert str(Message.Product.NoOrder()) in response.text
    # add some products to order list
    with dbSession() as db_session:
        for product in products_to_order:
            db_session.get(Product, product["id"]).to_order = True
        db_session.commit()
        db_products_to_order = db_session.scalars(
            select(Product).filter_by(to_order=True)).all()
        assert len(db_products_to_order) == len(products_to_order)
    # check new status and remove products from order list
    with client:
        client.get("/")
        response = client.get(url_for("prod.products_to_order"))
        assert response.status_code == 200
        assert update_order_button.search(response.text)
        assert all_ordered_button.search(response.text)
        for product in products_to_order:
            assert product["name"] in response.text
        assert str(Message.UI.Main.ProdToOrder(len(products_to_order))) \
            in response.text
        for _ in range(len(products_to_order)-1):
            prod = products_to_order.pop()
            client.get(url_for("prod.products_to_order"))
            data = {
                "csrf_token": g.csrf_token,
                str(prod["id"]): "on"
            }
            response = client.post(
                url_for("prod.products_to_order"), data=data)
            assert response.status_code == 200
            assert all_ordered_button.search(response.text)
            assert str(Message.Product.Ordered(1)) in response.text
            for product in products_to_order:
                assert product["name"] in response.text
        assert len(products_to_order) == 1
        client.get(url_for("prod.products_to_order"))
        data = {
            "csrf_token": g.csrf_token,
            str(products_to_order[0]["id"]): "on"
        }
        response = client.post(
            url_for("prod.products_to_order"),
            data=data,
            follow_redirects=True)
        assert redirected_to(url_for("main.index"), response)
    assert not all_ordered_button.search(response.text)
    assert str(Message.Product.Ordered(1)) in response.text
    assert str(Message.Product.NoOrder()) in response.text
    assert str(Message.UI.Main.ProdToOrder(0)) in response.text
    # check db
    with dbSession() as db_session:
        assert not db_session.scalars(
            select(Product).filter_by(to_order=True)).all()


@given(products_to_order = st.lists(
        elements=st.sampled_from(
            [product for product in test_products if product["in_use"]]),
        unique_by=lambda x: x["name"],
        min_size=5))
def test_order_page_all_ordered(client: FlaskClient, admin_logged_in: User,
                                products_to_order: list[dict[str]]):
    """test_order_page_all_ordered"""
    # add some products to order list
    with dbSession() as db_session:
        for product in products_to_order:
            db_session.get(Product, product["id"]).to_order = True
        db_session.commit()
        db_products_to_order = db_session.scalars(
            select(Product).filter_by(to_order=True)).all()
        assert len(db_products_to_order) == len(products_to_order)
    # all_ordered
    with client:
        response = client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        assert str(Message.UI.Main.ProdToOrder(len(products_to_order))) \
            in response.text
        response = client.get(url_for("prod.products_to_order"))
        assert response.status_code == 200
        assert update_order_button.search(response.text)
        assert all_ordered_button.search(response.text)
        for product in products_to_order:
            assert product["name"] in response.text
        response = client.get(
            url_for("prod.all_products_ordered"), follow_redirects=True)
        assert redirected_to(url_for("main.index"), response)
        assert str(Message.Product.AllOrdered()) in response.text
        assert str(Message.UI.Main.ProdToOrder(0)) in response.text
        # get redirected from order page
        response = client.get(
            url_for("prod.products_to_order"), follow_redirects=True)
        assert redirected_to(url_for("main.index"), response)
    assert str(Message.Product.NoOrder()) in response.text
    # check db
    with dbSession() as db_session:
        assert not db_session.scalars(
            select(Product).filter_by(to_order=True)).all()


def test_order_page_no_csrf(client: FlaskClient, admin_logged_in: User):
    """test_order_page_no_csrf"""
    # add a product to order list
    with dbSession() as db_session:
        db_session.get(Product, test_products[0]["id"]).to_order = True
        db_session.commit()
    # try to remove the product from order list
    with client:
        response = client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        assert str(Message.UI.Main.ProdToOrder(1)) in response.text
        data = {
            "csrf_token": None,
            str(test_products[0]["id"]): "on"
        }
        response = client.post(url_for("prod.products_to_order"), data=data)
        assert response.status_code == 200
        assert all_ordered_button.search(response.text)
        assert "The CSRF token is missing" in response.text
    # teardown
    with dbSession() as db_session:
        db_session.get(Product, test_products[0]["id"]).to_order = False
        db_session.commit()
# endregion
