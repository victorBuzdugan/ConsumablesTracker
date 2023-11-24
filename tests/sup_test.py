"""Suppliers blueprint tests."""

from html import unescape
from urllib.parse import quote

import pytest
from flask import g, session, url_for
from flask.testing import FlaskClient
from sqlalchemy import select

from database import Category, Product, Supplier, User, dbSession
from messages import Message

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
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("auth.login")
        assert str(Message.UI.Auth.AdminReq()) in response.text


def test_suppliers_page_admin_logged_in(
        client: FlaskClient, admin_logged_in: User):
    """test_suppliers_page_admin_logged_in"""
    with client:
        client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        response = client.get(url_for("sup.suppliers"), follow_redirects=True)
        assert len(response.history) == 0
        assert response.status_code == 200
        assert str(Message.UI.Auth.AdminReq()) not in response.text
        assert "Suppliers" in response.text
        assert "Strikethrough suppliers are no longer in use" in response.text
        assert "Amazon" in response.text
        assert "Carrefour" in response.text
        assert ("link-dark link-offset-2 link-underline-opacity-50 " +
                "link-underline-opacity-100-hover") in response.text
        assert "text-decoration-line-through" in response.text
        with dbSession() as db_session:
            db_session.get(Supplier, 5).in_use = True
            db_session.commit()
            response = client.get(url_for("sup.suppliers"))
            assert "text-decoration-line-through" not in response.text
            db_session.get(Supplier, 5).in_use = False
            db_session.commit()
# endregion


# region: new supplier
@pytest.mark.parametrize(("name", "details"), (
    ("new", ""),
    ("new_supplier", "some details"),
    ("a_long_long_long_new_supplier",
     "some really long long long details, even a double long long details"),
))
def test_new_supplier(
    client: FlaskClient, admin_logged_in: User,
    name, details):
    """test_new_supplier"""
    with client:
        client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        response = client.get(url_for("sup.new_supplier"))
        assert "Create supplier" in response.text
        data = {
            "csrf_token": g.csrf_token,
            "name": name,
            "details": details,
            }
        response = client.post(
            url_for("sup.new_supplier"), data=data, follow_redirects=True)
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("sup.suppliers")
        assert str(Message.Supplier.Created(name)) in unescape(response.text)
        assert name in response.text
    with dbSession() as db_session:
        sup = db_session.scalar(select(Supplier).filter_by(name=name))
        assert sup.in_use
        assert sup.details == details
        db_session.delete(sup)
        db_session.commit()


@pytest.mark.parametrize(("name", "flash_message"), (
    ("", str(Message.Supplier.Name.Required())),
    ("su", str(Message.Supplier.Name.LenLimit())),
    ("Amazon", str(Message.Supplier.Name.Exists("Amazon"))),
))
def test_failed_new_supplier(
        client: FlaskClient, admin_logged_in: User,
        name, flash_message):
    """test_failed_new_supplier"""
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
            url_for("sup.new_supplier"), data=data, follow_redirects=True)
        assert len(response.history) == 0
        assert response.status_code == 200
        assert "Create supplier" in response.text
        assert flash_message in unescape(response.text)
        assert str(Message.Supplier.Created(name)) \
            not in unescape(response.text)
    with dbSession() as db_session:
        if name != "Amazon":
            assert not db_session.scalar(select(Supplier).filter_by(name=name))
# endregion


# region: edit supplier
@pytest.mark.parametrize(("sup_id", "new_name", "new_details", "new_in_use"), (
    ("1", "Amazon renamed", "", "on"),
    ("1", "Amazon", "Some details", "on"),
    ("2", "Other name", "Some details", "on"),
    ("4", "Other_name", "Some details", "on"),
    ("5", "Other_name", "Some details", "on"),
))
def test_edit_supplier(
        client: FlaskClient, admin_logged_in: User,
        sup_id, new_name, new_details, new_in_use):
    """test_edit_supplier"""
    with dbSession() as db_session:
        sup = db_session.get(Supplier, sup_id)
        orig_in_use = sup.in_use
        orig_name = sup.name
        orig_details = sup.details
        with client:
            client.get("/")
            assert session["user_name"] == admin_logged_in.name
            assert session["admin"]
            client.get(url_for("sup.suppliers"))
            response = client.get(
                url_for("sup.edit_supplier", supplier=sup.name))
            assert len(response.history) == 0
            assert response.status_code == 200
            assert orig_name in response.text
            data = {
                "csrf_token": g.csrf_token,
                "name": new_name,
                "details": new_details,
                "in_use": new_in_use,
                "submit": True,
            }
            response = client.post(
                url_for("sup.edit_supplier", supplier=orig_name),
                data=data,
                follow_redirects=True)
            assert len(response.history) == 1
            assert response.history[0].status_code == 302
            assert response.status_code == 200
            assert quote(response.request.path) == url_for("sup.suppliers")
            assert str(Message.Supplier.Updated(new_name)) \
                in unescape(response.text)
            assert new_name in response.text
            assert new_details in response.text

        db_session.refresh(sup)
        assert sup.name == new_name
        assert sup.details == new_details
        assert sup.in_use == bool(new_in_use)
        # teardown
        sup.name = orig_name
        sup.details = orig_details
        sup.in_use = orig_in_use
        db_session.commit()


@pytest.mark.parametrize(("sup_id", "new_name", "new_in_use", "flash_msg"), (
    ("1", "", "on", str(Message.Supplier.Name.Required())),
    ("4", "", "on", str(Message.Supplier.Name.Required())),
    ("3", "ca", "on", str(Message.Supplier.Name.LenLimit())),
    ("5", "ca", "", str(Message.Supplier.Name.LenLimit())),
))
def test_failed_edit_supplier_form_validators(
        client: FlaskClient, admin_logged_in,
        sup_id, new_name, new_in_use, flash_msg):
    """test_failed_edit_supplier_form_validators"""
    with dbSession() as db_session:
        sup = db_session.get(Supplier, sup_id)
        orig_name = sup.name
        orig_in_use = sup.in_use
        orig_details = sup.details
        with client:
            client.get("/")
            assert session["user_name"] == admin_logged_in.name
            assert session["admin"]
            response = client.get(
                url_for("sup.edit_supplier", supplier=sup.name))
            assert orig_name in response.text
            data = {
                "csrf_token": g.csrf_token,
                "name": new_name,
                "details": sup.details,
                "in_use": new_in_use,
                "submit": True,
            }
            response = client.post(
                url_for("sup.edit_supplier", supplier=orig_name),
                data=data,
                follow_redirects=True)
            assert len(response.history) == 0
            assert response.status_code == 200
            assert str(Message.Supplier.Updated(new_name)) \
                not in unescape(response.text)
            assert orig_name in response.text
            assert flash_msg in unescape(response.text)
        db_session.refresh(sup)
        assert sup.name == orig_name
        assert sup.in_use == orig_in_use
        assert sup.details == orig_details


def test_failed_edit_supplier_name_duplicate(
        client: FlaskClient, admin_logged_in: User):
    """test_failed_edit_supplier_name_duplicate"""
    with dbSession() as db_session:
        sup = db_session.get(Supplier, 2)
        orig_name = sup.name
        new_name = db_session.get(Supplier, 1).name
        with client:
            client.get("/")
            assert session["user_name"] == admin_logged_in.name
            assert session["admin"]
            client.get(url_for("sup.suppliers"))
            response = client.get(
                url_for("sup.edit_supplier", supplier=orig_name))
            assert sup.name in response.text
            data = {
                "csrf_token": g.csrf_token,
                "name": new_name,
                "details": sup.details,
                "in_use": "on",
                "submit": True,
            }
            response = client.post(
                url_for("sup.edit_supplier", supplier=orig_name),
                data=data,
                follow_redirects=True)
            assert len(response.history) == 0
            assert response.status_code == 200
            assert str(Message.Supplier.Updated(new_name)) \
                not in unescape(response.text)
            assert orig_name in response.text
            assert str(Message.Supplier.Name.Exists(new_name)) \
                in unescape(response.text)
        db_session.refresh(sup)
        assert sup.name != new_name


def test_failed_edit_supplier_in_use(
        client: FlaskClient, admin_logged_in: User):
    """test_failed_edit_supplier_in_use"""
    with dbSession() as db_session:
        sup = db_session.get(Supplier, 3)
        with client:
            client.get("/")
            assert session["user_name"] == admin_logged_in.name
            assert session["admin"]
            client.get(url_for("sup.suppliers"))
            response = client.get(
                url_for("sup.edit_supplier", supplier=sup.name))
            assert sup.name in response.text
            data = {
                "csrf_token": g.csrf_token,
                "name": sup.name,
                "details": sup.details,
                "in_use": "",
                "submit": True,
            }
            response = client.post(
                url_for("sup.edit_supplier", supplier=sup.name),
                data=data,
                follow_redirects=True)
            assert len(response.history) == 0
            assert response.status_code == 200
            assert str(Message.Supplier.Updated(sup.name)) \
                not in unescape(response.text)
            assert sup.name in response.text
            assert str(Message.Supplier.InUse.StillProd()) \
                in unescape(response.text)
        db_session.refresh(sup)
        assert sup.in_use


def test_failed_edit_supplier_bad_name(
        client: FlaskClient, admin_logged_in: User):
    """test_failed_edit_supplier_bad_name"""
    sup_name = "not_existing_supplier"
    with client:
        client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        response = client.get(
            url_for("sup.edit_supplier", supplier=sup_name),
            follow_redirects=True)
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("sup.suppliers")
        assert str(Message.Supplier.NotExists(sup_name)) \
            in unescape(response.text)
# endregion


# region: delete supplier
def test_delete_supplier(client: FlaskClient, admin_logged_in: User):
    """test_delete_supplier"""
    with dbSession() as db_session:
        sup = Supplier(name="new_supplier")
        db_session.add(sup)
        db_session.commit()
        assert sup.id
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
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("main.index")
        assert str(Message.Supplier.Deleted(sup.name)) \
            in unescape(response.text)
    with dbSession() as db_session:
        assert not db_session.get(Supplier, sup.id)


@pytest.mark.parametrize(("sup_id", ), (
    ("1",),
    ("2",),
    ("3",),
    ("4",),
))
def test_failed_delete_category(
        client: FlaskClient, admin_logged_in: User,
        sup_id):
    """test_failed_delete_category"""
    with dbSession() as db_session:
        sup = db_session.get(Supplier, sup_id)
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
        assert len(response.history) == 0
        assert response.status_code == 200
        assert str(Message.Supplier.NoDelete()) in unescape(response.text)
    with dbSession() as db_session:
        assert db_session.get(Supplier, sup.id)
# endregion


# region: reassign supplier
def test_landing_page_from_supplier_edit(
        client: FlaskClient, admin_logged_in: User):
    """test_landing_page_from_supplier_edit"""
    cat_id = 1
    with dbSession() as db_session:
        sup = db_session.get(Supplier, cat_id)
    with client:
        client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        response = client.get(url_for("sup.edit_supplier", supplier=sup.name))
        assert sup.name in response.text
        data = {
            "csrf_token": g.csrf_token,
            "name": sup.name,
            "reassign": True,
        }
        response = client.post(
            url_for("sup.edit_supplier", supplier=sup.name),
            data=data,
            follow_redirects=True)
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path \
            == url_for("sup.reassign_supplier", supplier=sup.name)
        assert "Reassign all products for supplier" in response.text
        assert sup.name in response.text


def test_reassign_supplier(client: FlaskClient, admin_logged_in: User):
    """For testing create a new supplier
    that has all products responsible_id to 1 - user1"""
    resp_id = 1
    new_resp_id = 2
    with dbSession() as db_session:
        new_sup = Supplier(name="new_supplier")
        db_session.add(new_sup)
        db_session.commit()
        for ind in range(5):
            new_product = Product(
                name=f"new_product_{ind}",
                description="Some description",
                responsible=db_session.get(User, resp_id),
                category=db_session.get(Category, resp_id),
                supplier=new_sup,
                meas_unit="pc",
                min_stock=0,
                ord_qty=1)
            db_session.add(new_product)
        db_session.commit()

        products = db_session.scalars(
            select(Product)
            .filter_by(supplier_id=new_sup.id)).all()
        for product in products:
            assert product.responsible_id == resp_id
        with client:
            client.get("/")
            assert session["user_name"] == admin_logged_in.name
            assert session["admin"]
            response = client.get(
                url_for("sup.reassign_supplier", supplier=new_sup.name))
            assert len(response.history) == 0
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
            assert len(response.history) == 1
            assert response.history[0].status_code == 302
            assert response.status_code == 200
            assert quote(response.request.path) \
                == url_for("sup.reassign_supplier", supplier=new_sup.name)
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


def test_failed_reassign_supplier(client: FlaskClient, admin_logged_in: User):
    """test_failed_reassign_supplier"""
    sup_id = 3
    new_resp_id = 0
    with dbSession() as db_session:
        sup = db_session.get(Supplier, sup_id)
        with client:
            client.get("/")
            assert session["user_name"] == admin_logged_in.name
            assert session["admin"]
            response = client.get(
                url_for("sup.reassign_supplier", supplier=sup.name))
            assert len(response.history) == 0
            assert response.status_code == 200
            assert sup.name in response.text
            data = {
                "csrf_token": g.csrf_token,
                "responsible_id": str(new_resp_id),
                "submit": True,
                }
            response = client.post(
                url_for("sup.reassign_supplier", supplier=sup.name),
                data=data,
                follow_redirects=True)
            assert len(response.history) == 1
            assert response.history[0].status_code == 302
            assert response.status_code == 200
            assert quote(response.request.path) \
                == url_for("sup.reassign_supplier", supplier=sup.name)
            assert str(Message.Supplier.Responsible.Updated(sup.name)) \
                not in unescape(response.text)
            assert str(Message.Supplier.Responsible.Invalid()) in response.text


def test_failed_reassign_supplier_bad_choice(
        client: FlaskClient, admin_logged_in: User):
    """test_failed_reassign_supplier_bad_choice"""
    sup_id = 2
    new_resp_id = 15
    with dbSession() as db_session:
        sup = db_session.get(Supplier, sup_id)
        with client:
            client.get("/")
            assert session["user_name"] == admin_logged_in.name
            assert session["admin"]
            response = client.get(
                url_for("sup.reassign_supplier", supplier=sup.name))
            assert len(response.history) == 0
            assert response.status_code == 200
            assert sup.name in response.text
            data = {
                "csrf_token": g.csrf_token,
                "responsible_id": str(new_resp_id),
                "submit": True,
                }
            response = client.post(
                url_for("sup.reassign_supplier", supplier=sup.name),
                data=data,
                follow_redirects=True)
            assert len(response.history) == 0
            assert response.status_code == 200
            assert str(Message.Supplier.Responsible.Updated(sup.name)) \
                not in response.text
            assert "Not a valid choice." in response.text


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
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("sup.suppliers")
        assert str(Message.Supplier.NotExists(sup_name)) \
            in unescape(response.text)
# endregion
