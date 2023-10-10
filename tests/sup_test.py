"""Suppliers blueprint tests."""

from html import unescape
from urllib.parse import quote

import pytest
from flask import g, url_for
from flask.testing import FlaskClient
from sqlalchemy import select

from database import Category, Product, Supplier, User, dbSession
from tests import (admin_logged_in, client, create_test_categories,
                   create_test_db, create_test_group_schedule,
                   create_test_products, create_test_suppliers,
                   create_test_users, user_logged_in)

pytestmark = pytest.mark.sup


# region: suppliers page
def test_suppliers_page_user_logged_in(client: FlaskClient, user_logged_in):
    with client:
        client.get("/")
        response = client.get(url_for("sup.suppliers"), follow_redirects=True)
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("auth.login")
        assert b"You have to be an admin..." in response.data


def test_suppliers_page_admin_logged_in(client: FlaskClient, admin_logged_in):
    with client:
        client.get("/")
        response = client.get(url_for("sup.suppliers"), follow_redirects=True)
        assert len(response.history) == 0
        assert response.status_code == 200
        assert b"You have to be an admin..." not in response.data
        assert b"Suppliers" in response.data
        assert b"Strikethrough suppliers are no longer in use" in response.data
        assert b"Amazon" in response.data
        assert b"Carrefour" in response.data
        assert b"link-dark link-offset-2 link-underline-opacity-50 link-underline-opacity-100-hover" in response.data
        assert b"text-decoration-line-through" in response.data
        with dbSession() as db_session:
            db_session.get(Supplier, 5).in_use = True
            db_session.commit()
            response = client.get(url_for("sup.suppliers"))
            assert b"text-decoration-line-through" not in response.data
            db_session.get(Supplier, 5).in_use = False
            db_session.commit()
# endregion


# region: new supplier
@pytest.mark.parametrize(("name", "details"), (
    ("new", ""),
    ("new_supplier", "some details"),
    ("a_long_long_long_new_supplier", "some really long long long details, even a double long long details"),
))
def test_new_supplier(client: FlaskClient, admin_logged_in, name, details):
    with client:
        client.get("/")
        response = client.get(url_for("sup.new_supplier"))
        assert b"Create supplier" in response.data
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
        assert f"Supplier '{name}' created" in unescape(response.text)
        assert bytes(name, "UTF-8") in response.data
    with dbSession() as db_session:
        sup = db_session.scalar(select(Supplier).filter_by(name=name))
        assert sup.in_use
        assert sup.details == details
        db_session.delete(sup)
        db_session.commit()


@pytest.mark.parametrize(("name", "flash_message"), (
    ("", "Supplier name is required"),
    ("su", "Supplier name must have at least 3 characters"),
    ("Amazon", "The supplier Amazon allready exists"),
))
def test_failed_new_supplier(client: FlaskClient, admin_logged_in, name, flash_message):
    with client:
        client.get("/")
        response = client.get(url_for("sup.new_supplier"))
        assert b"Create supplier" in response.data
        data = {
            "csrf_token": g.csrf_token,
            "name": name,
            "details": "",
            }
        response = client.post(
            url_for("sup.new_supplier"), data=data, follow_redirects=True)
        assert len(response.history) == 0
        assert response.status_code == 200
        assert b"Create supplier" in response.data
        assert flash_message in unescape(response.text)
        assert f"Supplier '{name}' created" not in unescape(response.text)
    with dbSession() as db_session:
        if name != "Amazon":
            assert not db_session.scalar(select(Supplier).filter_by(name=name))
# endregion


# region: edit supplier
@pytest.mark.parametrize(("id", "new_name", "new_details", "new_in_use"), (
    ("1", "Amazon renamed", "", "on"),
    ("1", "Amazon", "Some details", "on"),
    ("2", "Other name", "Some details", "on"),
    ("4", "Other_name", "Some details", "on"),
    ("5", "Other_name", "Some details", "on"),
))
def test_edit_supplier(client: FlaskClient, admin_logged_in,
        id, new_name, new_details, new_in_use):
    with dbSession() as db_session:
        sup = db_session.get(Supplier, id)
        orig_in_use = sup.in_use
        orig_name = sup.name
        orig_details = sup.details
        with client:
            client.get("/")
            response = client.get(url_for("sup.edit_supplier", supplier=sup.name))
            assert len(response.history) == 0
            assert response.status_code == 200
            assert bytes(orig_name, "UTF-8") in response.data
            data = {
                "csrf_token": g.csrf_token,
                "name": new_name,
                "details": new_details,
                "in_use": new_in_use,
                "submit": True,
            }
            response = client.post(url_for("sup.edit_supplier", supplier=orig_name),
                                   data=data, follow_redirects=True)
            assert len(response.history) == 1
            assert response.history[0].status_code == 302
            assert response.status_code == 200
            assert quote(response.request.path) == url_for("sup.edit_supplier", supplier=new_name)
            assert b"Supplier updated" in response.data
            assert bytes(new_name, "UTF-8") in response.data
            assert bytes(new_details, "UTF-8") in response.data

        db_session.refresh(sup)
        assert sup.name == new_name
        assert sup.details == new_details
        assert sup.in_use == bool(new_in_use)
        # teardown
        sup.name = orig_name
        sup.details = orig_details
        sup.in_use = orig_in_use
        db_session.commit()


@pytest.mark.parametrize(("id", "new_name", "new_in_use", "flash_message"), (
    ("1", "", "on", "Supplier name is required"),
    ("4", "", "on", "Supplier name is required"),
    ("3", "ca", "on", "Supplier name must have at least 3 characters"),
    ("5", "ca", "", "Supplier name must have at least 3 characters"),
))
def test_failed_edit_supplier_form_validators(client: FlaskClient, admin_logged_in,
        id, new_name, new_in_use, flash_message):
    with dbSession() as db_session:
        sup = db_session.get(Supplier, id)
        orig_name = sup.name
        orig_in_use = sup.in_use
        orig_details = sup.details
        with client:
            client.get("/")
            response = client.get(url_for("sup.edit_supplier", supplier=sup.name))
            assert bytes(orig_name, "UTF-8") in response.data
            data = {
                "csrf_token": g.csrf_token,
                "name": new_name,
                "details": sup.details,
                "in_use": new_in_use,
                "submit": True,
            }
            response = client.post(url_for("sup.edit_supplier", supplier=orig_name),
                                   data=data, follow_redirects=True)
            assert len(response.history) == 0
            assert response.status_code == 200
            assert b"Supplier updated" not in response.data
            assert bytes(orig_name, "UTF-8") in response.data
            assert flash_message in unescape(response.text)
        db_session.refresh(sup)
        assert sup.name == orig_name
        assert sup.in_use == orig_in_use
        assert sup.details == orig_details


def test_failed_edit_supplier_name_duplicate(client: FlaskClient, admin_logged_in):
    with dbSession() as db_session:
        sup = db_session.get(Supplier, 2)
        orig_name = sup.name
        new_name = db_session.get(Supplier, 1).name
        with client:
            client.get("/")
            response = client.get(url_for("sup.edit_supplier", supplier=orig_name))
            assert bytes(sup.name, "UTF-8") in response.data
            data = {
                "csrf_token": g.csrf_token,
                "name": new_name,
                "details": sup.details,
                "in_use": "on",
                "submit": True,
            }
            response = client.post(url_for("sup.edit_supplier", supplier=orig_name),
                                   data=data, follow_redirects=True)
            assert len(response.history) == 1
            assert response.history[0].status_code == 302
            assert response.status_code == 200
            assert response.request.path == url_for("sup.edit_supplier", supplier=orig_name)
            assert b"Supplier updated" not in response.data
            assert bytes(orig_name, "UTF-8") in response.data
            assert f"The supplier {new_name} allready exists" in response.text
        db_session.refresh(sup)
        assert sup.name != new_name


def test_failed_edit_supplier_in_use(client: FlaskClient, admin_logged_in):
    with dbSession() as db_session:
        sup = db_session.get(Supplier, 3)
        with client:
            client.get("/")
            response = client.get(url_for("sup.edit_supplier", supplier=sup.name))
            assert bytes(sup.name, "UTF-8") in response.data
            data = {
                "csrf_token": g.csrf_token,
                "name": sup.name,
                "details": sup.details,
                "in_use": "",
                "submit": True,
            }
            response = client.post(url_for("sup.edit_supplier", supplier=sup.name),
                                   data=data, follow_redirects=True)
            assert len(response.history) == 1
            assert response.history[0].status_code == 302
            assert response.status_code == 200
            assert response.request.path == url_for("sup.edit_supplier", supplier=sup.name)
            assert b"Supplier updated" not in response.data
            assert bytes(sup.name, "UTF-8") in response.data
            assert "Not in use supplier can't have products attached" in unescape(response.text)
        db_session.refresh(sup)
        assert sup.in_use


def test_failed_edit_supplier_bad_name(client: FlaskClient, admin_logged_in):
    with client:
        client.get("/")
        response = client.get(url_for("sup.edit_supplier", supplier="not_existing_supplier"), follow_redirects=True)
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("sup.suppliers")
        assert b"not_existing_supplier does not exist!" in response.data
# endregion


# region: delete supplier
def test_delete_supplier(client: FlaskClient, admin_logged_in):
    with dbSession() as db_session:
        sup = Supplier("new_supplier")
        db_session.add(sup)
        db_session.commit()
        assert sup.id
    with client:
        client.get("/")
        response = client.get(url_for("sup.edit_supplier", supplier=sup.name))
        assert bytes(sup.name, "UTF-8") in response.data
        data = {
            "csrf_token": g.csrf_token,
            "name": sup.name,
            "delete": True,
        }
        response = client.post(url_for("sup.edit_supplier", supplier=sup.name),
                            data=data, follow_redirects=True)
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("sup.suppliers")
        assert f"Supplier '{sup.name}' has been deleted" in unescape(response.text)
    with dbSession() as db_session:
        assert not db_session.get(Supplier, sup.id)


@pytest.mark.parametrize(("sup_id", ), (
    ("1",),
    ("2",),
    ("3",),
    ("4",),
))
def test_failed_delete_category(client: FlaskClient, admin_logged_in, sup_id):
    with dbSession() as db_session:
        sup = db_session.get(Supplier, sup_id)
    with client:
        client.get("/")
        response = client.get(url_for("sup.edit_supplier", supplier=sup.name))
        assert bytes(sup.name, "UTF-8") in response.data
        data = {
            "csrf_token": g.csrf_token,
            "name": sup.name,
            "delete": True,
        }
        response = client.post(url_for("sup.edit_supplier", supplier=sup.name),
                            data=data, follow_redirects=True)
        assert len(response.history) == 0
        assert response.status_code == 200
        assert f"Can't delete supplier! There are still products attached!" in unescape(response.text)
    with dbSession() as db_session:
        assert db_session.get(Supplier, sup.id)
# endregion


# region: reassign supplier
def test_landing_page_from_supplier_edit(client: FlaskClient, admin_logged_in):
    CAT_ID = 1
    with dbSession() as db_session:
        sup = db_session.get(Supplier, CAT_ID)
    with client:
        client.get("/")
        response = client.get(url_for("sup.edit_supplier", supplier=sup.name))
        assert bytes(sup.name, "UTF-8") in response.data
        data = {
            "csrf_token": g.csrf_token,
            "name": sup.name,
            "reassign": True,
        }
        response = client.post(url_for("sup.edit_supplier", supplier=sup.name),
                            data=data, follow_redirects=True)
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("sup.reassign_supplier", supplier=sup.name)
        assert b"Reassign all products for supplier" in response.data
        assert bytes(sup.name, "UTF-8") in response.data


def test_reassign_supplier(client: FlaskClient, admin_logged_in):
    # for testing create a new supplier
    # that has all products responsable_id to 1 - user1
    RESP_ID = 1
    NEW_RESP_ID = 2
    with dbSession() as db_session:
        new_sup = Supplier("new_supplier")
        db_session.add(new_sup)
        db_session.commit()
        for ind in range(5):
            new_product = Product(
                name=f"new_product_{ind}",
                description="Some description",
                responsable=db_session.get(User, RESP_ID),
                category=db_session.get(Category, RESP_ID),
                supplier=new_sup,
                meas_unit="pc",
                min_stock=0,
                ord_qty=1)
            db_session.add(new_product)
        db_session.commit()

        products = db_session.scalars(
            select(Product)
            .filter_by(supplier_id=new_sup.id)
            ).all()
        for product in products:
            assert product.responsable_id == RESP_ID
        with client:
            client.get("/")
            response = client.get(url_for("sup.reassign_supplier", supplier=new_sup.name))
            assert len(response.history) == 0
            assert response.status_code == 200
            assert bytes(new_sup.name, "UTF-8") in response.data
            data = {
                "csrf_token": g.csrf_token,
                "responsable_id": str(NEW_RESP_ID),
                "submit": True,
                }
            response = client.post(url_for("sup.reassign_supplier", supplier=new_sup.name), 
                                    data=data, follow_redirects=True)
            assert len(response.history) == 1
            assert response.history[0].status_code == 302
            assert response.status_code == 200
            assert quote(response.request.path) == url_for("sup.reassign_supplier", supplier=new_sup.name)
            assert b"Supplier responsable updated" in response.data
            assert b"You have to select a new responsible first" not in response.data
        # check and teardown
        for product in products:
            db_session.refresh(product)
            assert product.responsable_id == NEW_RESP_ID
            db_session.delete(product)
        db_session.delete(new_sup)
        db_session.commit()


def test_failed_reassign_supplier(client: FlaskClient, admin_logged_in):
    SUP_ID = 3
    NEW_RESP_ID = 0
    with dbSession() as db_session:
        sup = db_session.get(Supplier, SUP_ID)
        with client:
            client.get("/")
            response = client.get(url_for("sup.reassign_supplier", supplier=sup.name))
            assert len(response.history) == 0
            assert response.status_code == 200
            assert bytes(sup.name, "UTF-8") in response.data
            data = {
                "csrf_token": g.csrf_token,
                "responsable_id": str(NEW_RESP_ID),
                "submit": True,
                }
            response = client.post(url_for("sup.reassign_supplier", supplier=sup.name), 
                                    data=data, follow_redirects=True)
            assert len(response.history) == 1
            assert response.history[0].status_code == 302
            assert response.status_code == 200
            assert quote(response.request.path) == url_for("sup.reassign_supplier", supplier=sup.name)
            assert b"Supplier responsable updated" not in response.data
            assert b"You have to select a new responsible first" in response.data


def test_failed_reassign_supplier_bad_choice(client: FlaskClient, admin_logged_in):
    SUP_ID = 2
    NEW_RESP_ID = 15
    with dbSession() as db_session:
        sup = db_session.get(Supplier, SUP_ID)
        with client:
            client.get("/")
            response = client.get(url_for("sup.reassign_supplier", supplier=sup.name))
            assert len(response.history) == 0
            assert response.status_code == 200
            assert bytes(sup.name, "UTF-8") in response.data
            data = {
                "csrf_token": g.csrf_token,
                "responsable_id": str(NEW_RESP_ID),
                "submit": True,
                }
            response = client.post(url_for("sup.reassign_supplier", supplier=sup.name), 
                                    data=data, follow_redirects=True)
            assert len(response.history) == 0
            assert response.status_code == 200
            assert b"Supplier responsable updated" not in response.data
            assert b"Not a valid choice." in response.data


def test_failed_reassign_supplier_bad_name(client: FlaskClient, admin_logged_in):
    with client:
        client.get("/")
        response = client.get(url_for("sup.reassign_supplier", supplier="not_existing_supplier"), follow_redirects=True)
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("sup.suppliers")
        assert b"not_existing_supplier does not exist!" in response.data
# endregion
