"""Suppliers blueprint tests."""

import re
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
from tests import (InvalidSupplier, ValidProduct, ValidSupplier, redirected_to,
                   test_products, test_suppliers, test_users)

pytestmark = pytest.mark.sup


# region: suppliers page
def test_suppliers_page_user_logged_in(
        client: FlaskClient, user_logged_in: User):
    """test_suppliers_page_user_logged_in"""
    with client:
        client.get("/")
        assert session["user_name"] == user_logged_in.name
        assert not session["admin"]
        response = client.get(url_for("sup.suppliers"), follow_redirects=True)
        assert redirected_to(url_for("auth.login"), response)
        assert str(Message.UI.Auth.AdminReq()) in response.text


def test_suppliers_page_admin_logged_in(
        client: FlaskClient, admin_logged_in: User):
    """test_suppliers_page_admin_logged_in"""
    strikethrough_decoration = re.compile(r'span.*text-decoration-line-through')
    with client:
        client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        response = client.get(url_for("sup.suppliers"))
        assert response.status_code == 200
        assert str(Message.UI.Auth.AdminReq()) not in response.text
        assert str(Message.UI.Captions.Strikethrough("suppliers")) \
            in response.text
        for supplier in test_suppliers:
            assert supplier["name"] in response.text
        # not in use supplier
        assert strikethrough_decoration.search(response.text)
        suppliers_not_in_use = [sup for sup in test_suppliers
                                if not sup["in_use"]]
        with dbSession() as db_session:
            for sup in suppliers_not_in_use:
                db_session.scalar(
                    select(Supplier)
                    .filter_by(name=sup["name"])
                    ).in_use = True
            db_session.commit()
            response = client.get(url_for("sup.suppliers"))
            assert not strikethrough_decoration.search(response.text)
            for sup in suppliers_not_in_use:
                db_session.scalar(
                    select(Supplier)
                    .filter_by(name=sup["name"])
                    ).in_use = False
            db_session.commit()
# endregion


# region: new supplier
@given(name=st.text(min_size=Constant.Supplier.Name.min_length)
            .map(lambda x: x.strip())
            .filter(lambda x: len(x) > Constant.Supplier.Name.min_length)
            .filter(lambda x: x not in [sup["name"] for sup in test_suppliers]),
       details=st.text())
@example(name=ValidSupplier.name,
         details=ValidSupplier.details)
def test_new_supplier(
        client: FlaskClient, admin_logged_in: User,
        name: str, details: str):
    """test_new_supplier"""
    create_sup_btn = re.compile(
        r'<input.*type="submit".*value="Create supplier">')
    with client:
        client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        response = client.get(url_for("sup.new_supplier"))
        assert create_sup_btn.search(response.text)
        data = {
            "csrf_token": g.csrf_token,
            "name": name,
            "details": details,
            }
        response = client.post(
            url_for("sup.new_supplier"), data=data, follow_redirects=True)
        assert redirected_to(url_for("sup.suppliers"), response)
        assert str(Message.Supplier.Created(name)) in response.text
        assert name in unescape(response.text)
    with dbSession() as db_session:
        sup = db_session.scalar(select(Supplier).filter_by(name=name))
        assert sup.in_use
        assert sup.details == details
        db_session.delete(sup)
        db_session.commit()
        assert not db_session.get(Supplier, sup.id)


def _test_failed_new_supplier(
        request: pytest.FixtureRequest,
        name: str, flash_message: str, check_db: bool = True):
    """Common logic for failed new supplier."""
    client: FlaskClient = request.getfixturevalue("client")
    admin_logged_in: User = request.getfixturevalue("admin_logged_in")
    create_sup_btn = re.compile(
        r'<input.*type="submit".*value="Create supplier">')
    with client:
        client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        response = client.get(url_for("sup.new_supplier"))
        assert "Create supplier" in response.text
        data = {
            "csrf_token": g.csrf_token,
            "name": name,
            "details": "",
            }
        response = client.post(
            url_for("sup.new_supplier"), data=data)
        assert response.status_code == 200
        assert create_sup_btn.search(response.text)
        assert flash_message in unescape(response.text)
        assert str(Message.Supplier.Created(name)) not in response.text
    if check_db:
        with dbSession() as db_session:
            assert not db_session.scalar(select(Supplier).filter_by(name=name))


@given(name=st.text(min_size=1,
                    max_size=Constant.Category.Name.min_length - 1))
@example("")
@example(InvalidSupplier.short_name)
def test_failed_new_supplier_invalid_name(request, name: str):
    """Invalid or no name"""
    name = name.strip()
    if name:
        flash_message = str(Message.Supplier.Name.LenLimit())
    else:
        flash_message = str(Message.Supplier.Name.Required())
    _test_failed_new_supplier(request=request,
                              name=name,
                              flash_message=flash_message)


@given(supplier=st.sampled_from(test_suppliers))
def test_failed_new_supplier_duplicate_name(request, supplier):
    """Duplicate supplier name."""
    flash_message = str(Message.Supplier.Name.Exists(supplier["name"]))
    _test_failed_new_supplier(request=request,
                              name=supplier['name'],
                              flash_message=flash_message,
                              check_db=False)
# endregion


# region: edit supplier
@given(supplier=st.sampled_from(test_suppliers),
       new_name=st.text(min_size=Constant.Supplier.Name.min_length)
            .map(lambda x: x.strip())
            .filter(lambda x: len(x) > Constant.Supplier.Name.min_length)
            .filter(lambda x: x not in [sup["name"] for sup in test_suppliers]),
       new_details=st.text())
@example(supplier=test_suppliers[0],
       new_name=ValidSupplier.name,
       new_details=ValidSupplier.details)
def test_edit_supplier(
        client: FlaskClient, admin_logged_in: User,
        supplier: dict, new_name: str, new_details: str):
    """Test successfully edit supplier"""
    with client:
        client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        client.get(url_for("sup.suppliers"))
        response = client.get(
            url_for("sup.edit_supplier", supplier=supplier["name"]))
        assert response.status_code == 200
        assert supplier["name"] in response.text
        data = {
            "csrf_token": g.csrf_token,
            "name": new_name,
            "details": new_details,
            "in_use": "on",
            "submit": True,
        }
        response = client.post(
            url_for("sup.edit_supplier", supplier=supplier["name"]),
            data=data,
            follow_redirects=True)
        assert redirected_to(url_for("sup.suppliers"), response)
        assert str(Message.Supplier.Updated(new_name)) \
            in unescape(response.text)
        assert new_name in unescape(response.text)
        assert new_details in unescape(response.text)
    with dbSession() as db_session:
        sup = db_session.get(Supplier, supplier["id"])
        assert sup.name == new_name
        assert sup.details == new_details
        assert sup.in_use
        # teardown
        sup.name = supplier["name"]
        sup.details = supplier["details"]
        sup.in_use = supplier["in_use"]
        db_session.commit()


# region: failed edit supplier
def _test_failed_edit_supplier(
        request: pytest.FixtureRequest,
        supplier: dict,
        flash_message: str,
        new_name: str = ValidSupplier.name,
        new_in_use: str = ValidSupplier.in_use):
    """Common logic for failed edit supplier"""
    client: FlaskClient = request.getfixturevalue("client")
    admin_logged_in: User = request.getfixturevalue("admin_logged_in")
    with client:
        client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        response = client.get(url_for("sup.edit_supplier",
                                        supplier=supplier["name"]))
        assert supplier["name"] in response.text
        data = {
            "csrf_token": g.csrf_token,
            "name": new_name,
            "details": supplier["details"],
            "in_use": new_in_use,
            "submit": True,
        }
        response = client.post(
            url_for("sup.edit_supplier", supplier=supplier["name"]),
            data=data)
        assert response.status_code == 200
        assert str(Message.Supplier.Updated(new_name)) \
            not in unescape(response.text)
        assert supplier["name"] in response.text
        assert flash_message in unescape(response.text)
    with dbSession() as db_session:
        sup = db_session.scalar(
            select(Supplier)
            .filter_by(name=supplier["name"]))
        assert sup.in_use == supplier["in_use"]


@given(supplier=st.sampled_from(test_suppliers),
       new_name=st.text(min_size=1,
                        max_size=Constant.Supplier.Name.min_length - 1))
@example(supplier=test_suppliers[0],
         new_name="")
@example(supplier=test_suppliers[0],
         new_name=InvalidSupplier.short_name)
def test_failed_edit_supplier_invalid_name(
        request, supplier: dict, new_name: str):
    """Invalid or no name"""
    new_name = new_name.strip()
    if new_name:
        flash_message = str(Message.Supplier.Name.LenLimit())
    else:
        flash_message = str(Message.Supplier.Name.Required())
    _test_failed_edit_supplier(request=request,
                               supplier=supplier,
                               new_name=new_name,
                               flash_message=flash_message)


@given(supplier=st.sampled_from(test_suppliers),
       name=st.sampled_from([supplier["name"] for supplier in test_suppliers]))
def test_failed_edit_supplier_duplicate_name(
        request, supplier: dict, name: str):
    """Duplicate name"""
    assume(supplier["name"] != name)
    flash_message = str(Message.Supplier.Name.Exists(name))
    _test_failed_edit_supplier(request=request,
                               supplier=supplier,
                               new_name=name,
                               flash_message=flash_message)


@given(supplier=st.sampled_from([supplier for supplier in test_suppliers
                                 if supplier["has_products"]]))
def test_failed_edit_supplier_with_products_not_in_use(
        request, supplier: dict):
    """Retire a category that still has products attached"""
    flash_message = str(Message.Supplier.InUse.StillProd())
    _test_failed_edit_supplier(request=request,
                               supplier=supplier,
                               new_in_use="",
                               flash_message=flash_message)


def test_failed_edit_supplier_not_existing_supplier(
        client: FlaskClient, admin_logged_in: User):
    """test_failed_edit_supplier_not_existing_supplier"""
    sup_name = "not_existing_supplier"
    with client:
        client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        response = client.get(
            url_for("sup.edit_supplier", supplier=sup_name),
            follow_redirects=True)
        assert redirected_to(url_for("sup.suppliers"), response)
        assert str(Message.Supplier.NotExists(sup_name)) in response.text
# endregion
# endregion


# region: delete supplier
def test_delete_supplier(client: FlaskClient, admin_logged_in: User):
    """Test successfully delete supplier"""
    # setup
    with dbSession() as db_session:
        sup = Supplier(name=ValidSupplier.name)
        db_session.add(sup)
        db_session.commit()
        assert sup.id
    # delete cat
    with client:
        client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        response = client.get(url_for("sup.edit_supplier", supplier=sup.name))
        assert sup.name in response.text
        data = {
            "csrf_token": g.csrf_token,
            "name": sup.name,
            "delete": True,
        }
        response = client.post(
            url_for("sup.edit_supplier", supplier=sup.name),
            data=data,
            follow_redirects=True)
        assert redirected_to(url_for("main.index"), response)
        assert response.request.path == url_for("main.index")
        assert str(Message.Supplier.Deleted(sup.name)) in response.text
    # db check
    with dbSession() as db_session:
        assert not db_session.get(Supplier, sup.id)


@given(supplier=st.sampled_from([supplier for supplier in test_suppliers
                                 if supplier["has_products"]]))
def test_failed_delete_supplier_with_products(
        client: FlaskClient, admin_logged_in: User,
        supplier: dict):
    """Failed delete suppliers that still have products attached"""
    with client:
        client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        response = client.get(url_for("sup.edit_supplier",
                                      supplier=supplier["name"]))
        assert supplier["name"] in response.text
        data = {
            "csrf_token": g.csrf_token,
            "name": supplier["name"],
            "delete": True,
        }
        response = client.post(
            url_for("sup.edit_supplier", supplier=supplier["name"]),
            data=data)
        assert response.status_code == 200
        assert str(Message.Supplier.NoDelete()) in response.text
    with dbSession() as db_session:
        assert db_session.get(Supplier, supplier["id"])
# endregion


# region: reassign supplier
@given(sup = st.sampled_from(test_suppliers))
def test_landing_page_from_category_edit(
        client: FlaskClient, admin_logged_in: User, sup: dict[str]):
    """test_landing_page_from_supplier_edit"""
    with client:
        client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        response = client.get(url_for("sup.edit_supplier",
                                      supplier=sup["name"]))
        assert sup["name"] in response.text
        data = {
            "csrf_token": g.csrf_token,
            "name": sup["name"],
            "reassign": True,
        }
        response = client.post(
            url_for("sup.edit_supplier", supplier=sup["name"]),
            data=data,
            follow_redirects=True)
        assert redirected_to(
            url_for("sup.reassign_supplier", supplier=sup["name"]),
            response)
        assert "Reassign all products for supplier" in response.text
        assert sup["name"] in response.text


def test_reassign_supplier(client: FlaskClient, admin_logged_in: User):
    """test_reassign_supplier"""
    resp_id = [user["id"] for user in test_users if user["active"]][0]
    new_resp_id = [user["id"] for user in test_users if user["active"]][1]
    with dbSession() as db_session:
        # create supplier
        new_sup = Supplier(name=ValidSupplier.name)
        db_session.add(new_sup)
        db_session.commit()
        # create 5 products for to this supplier
        for ind in range(5):
            new_product = Product(
                name="_".join([ValidProduct.name, str(ind)]),
                description=ValidProduct.description,
                responsible=db_session.get(User, resp_id),
                category=db_session.get(Category, ValidProduct.category_id),
                supplier=new_sup,
                meas_unit=ValidProduct.meas_unit,
                min_stock=ValidProduct.min_stock,
                ord_qty=ValidProduct.ord_qty)
            db_session.add(new_product)
        db_session.commit()
        products = db_session.scalars(
            select(Product)
            .filter_by(supplier_id=new_sup.id)).all()
        assert products
        # reassign all products
        with client:
            client.get("/")
            assert session["user_name"] == admin_logged_in.name
            assert session["admin"]
            response = client.get(
                url_for("sup.reassign_supplier", supplier=new_sup.name))
            assert response.status_code == 200
            assert new_sup.name in response.text
            data = {
                "csrf_token": g.csrf_token,
                "responsible_id": str(new_resp_id),
                "submit": True,
                }
            response = client.post(
                url_for("sup.reassign_supplier", supplier=new_sup.name),
                data=data,
                follow_redirects=True)
            assert redirected_to(
                url_for("sup.reassign_supplier", supplier=new_sup.name),
                response)
            assert str(Message.Supplier.Responsible.Updated(new_sup.name)) \
                in unescape(response.text)
            assert str(Message.Supplier.Responsible.Invalid()) \
                not in response.text
        # check and teardown
        for product in products:
            db_session.refresh(product)
            assert product.responsible_id == new_resp_id
            db_session.delete(product)
        db_session.delete(new_sup)
        db_session.commit()


@given(supplier_id = st.sampled_from(
            [sup["id"] for sup in test_suppliers if sup["has_products"]]),
       new_responsible_id=st.integers(min_value=len(test_users)))
@example(supplier_id=ValidProduct.supplier_id,
         new_responsible_id=0)
@example(supplier_id=ValidProduct.supplier_id,
         new_responsible_id=test_users.index(
             [user for user in test_users if not user["in_use"]][1]))
@example(supplier_id=ValidProduct.supplier_id,
         new_responsible_id=test_users.index(
             [user for user in test_users if user["reg_req"]][0]))
def test_failed_reassign_supplier(
        client: FlaskClient, admin_logged_in, supplier_id, new_responsible_id):
    """Test failed reassign supplier invalid new_responsible"""
    with dbSession() as db_session:
        sup = db_session.get(Supplier, supplier_id)
        with client:
            client.get("/")
            assert session["user_name"] == admin_logged_in.name
            assert session["admin"]
            response = client.get(
                url_for("sup.reassign_supplier", supplier=sup.name))
            assert response.status_code == 200
            assert sup.name in response.text
            # try to reassign
            data = {
                "csrf_token": g.csrf_token,
                "responsible_id": str(new_responsible_id),
                "submit": True,
                }
            response = client.post(
                url_for("sup.reassign_supplier", supplier=sup.name),
                data=data,
                follow_redirects=True)
            assert str(Message.Supplier.Responsible.Updated(sup.name)) \
                not in unescape(response.text)
            if new_responsible_id == 0:
                assert redirected_to(
                    url_for("sup.reassign_supplier", supplier=sup.name),
                    response)
                assert str(Message.Supplier.Responsible.Invalid()) \
                    in response.text
            else:
                assert len(response.history) == 0
                assert response.status_code == 200
                assert "Not a valid choice." in response.text
        # database check
        products = db_session.scalars(select(Product)
                                      .filter_by(supplier_id=supplier_id)).all()
        for product in products:
            assert product.responsible_id == \
                [prod["responsible_id"] for prod in test_products
                 if prod["name"] == product.name][0]


def test_failed_reassign_supplier_bad_name(
        client: FlaskClient, admin_logged_in: User):
    """test_failed_reassign_supplier_bad_name"""
    sup_name = "not_existing_supplier"
    with client:
        client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        response = client.get(
            url_for("sup.reassign_supplier", supplier=sup_name),
            follow_redirects=True)
        assert redirected_to(url_for("sup.suppliers"), response)
        assert str(Message.Supplier.NotExists(sup_name)) in response.text
# endregion
