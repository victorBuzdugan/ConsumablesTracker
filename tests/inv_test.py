"""Inventory blueprint tests."""

import re
import string

import pytest
from flask import g, session, url_for
from flask.testing import FlaskClient
from hypothesis import example, given
from hypothesis import strategies as st
from sqlalchemy import select

from database import Product, User, dbSession
from messages import Message
from tests import redirected_to, test_products, test_users

pytestmark = pytest.mark.inv

# region: regex html elements
log_in_button = re.compile(r'<input.*type="submit".*value="Log In">')
inv_not_req_button = re.compile(
    r'input.*type="submit".*value="Inventory check not required".*disabled')
submit_inv_button = re.compile(
    r'<input.*type="submit".*value="Submit inventory"')
prod_edit_link = re.compile(
    r'<a.*href="/product/edit/.*</a>')
checkbox_checked = re.compile(
    r'<input.*type="checkbox".*role="switch".*checked')
checkbox_checked_disabled = re.compile(
    r'<input.*type="checkbox".*role="switch".*disabled.*checked')
checkbox_disabled = re.compile(
    r'<input.*type="checkbox".*role="switch".*disabled')
# endregion


# region: inventory tests for current user
def test_inv_user_not_logged_in(client: FlaskClient):
    """Try to access the inventory page but not logged in."""
    with client:
        client.get("/")
        response = client.get(url_for("inv.inventory"), follow_redirects=True)
        assert redirected_to(url_for("auth.login"), response)
        assert str(Message.UI.Auth.LoginReq()) in response.text
        assert log_in_button.search(response.text)


def test_inv_user_logged_in_no_check_inventory(
        client: FlaskClient, user_logged_in: User):
    """Access inventory page with a user, no trigger for inventory check."""
    with client:
        client.get("/")
        response = client.get(url_for("inv.inventory"))
    # flash message
    assert str(Message.UI.Inv.NotReq()) in response.text
    # html elements
    assert inv_not_req_button.search(response.text)
    assert not submit_inv_button.search(response.text)
    assert not checkbox_checked.search(response.text)
    assert not checkbox_checked_disabled.search(response.text)
    assert checkbox_disabled.search(response.text)
    assert not prod_edit_link.search(response.text)
    # table captions
    assert str(Message.UI.Captions.InvOrder()) not in response.text
    assert str(Message.UI.Captions.CriticalProducts()) not in response.text
    # all user products present in the table
    with dbSession() as db_session:
        products =  db_session.scalars(select(Product)
            .filter_by(responsible_id=user_logged_in.id, in_use=True)).all()
        for product in products:
            assert product.name in response.text
            assert product.description in response.text
            assert f"{product.min_stock} {product.meas_unit}" in response.text
        # red color of a critical product
        crit_product =  db_session.scalar(select(Product)
            .filter_by(responsible_id=user_logged_in.id,
                       in_use=True,
                       critical=True))
        assert ('<td class="text-danger">' +
                f"{crit_product.min_stock} {crit_product.meas_unit}") \
                    in response.text
        # disabled and checked tags for a to_order product
        product =  db_session.scalar(select(Product)
            .filter_by(responsible_id=user_logged_in.id, in_use=True))
        product.to_order = True
        db_session.commit()
        with client:
            client.get("/")
            response = client.get(url_for("inv.inventory"))
            assert checkbox_checked.search(response.text)
            assert checkbox_checked_disabled.search(response.text)
        # teardown
        product.to_order = False
        db_session.commit()


def test_inv_admin_logged_in_no_check_inventory(
        client: FlaskClient, admin_logged_in: User):
    """Access inventory page with an admin, no trigger for inventory check."""
    with client:
        response = client.get("/")
        response = client.get(url_for("inv.inventory"))
    # flash message
    assert str(Message.UI.Inv.NotReq()) in response.text
    # html elements
    assert inv_not_req_button.search(response.text)
    assert not submit_inv_button.search(response.text)
    assert not checkbox_checked.search(response.text)
    assert not checkbox_checked_disabled.search(response.text)
    assert checkbox_disabled.search(response.text)
    assert prod_edit_link.search(response.text)
    # table captions
    assert str(Message.UI.Captions.InvOrder()) not in response.text
    assert str(Message.UI.Captions.CriticalProducts()) not in response.text
    # all user products present in the table
    with dbSession() as db_session:
        products =  db_session.scalars(select(Product)
            .filter_by(responsible_id=admin_logged_in.id, in_use=True)).all()
        for product in products:
            assert f">{product.name}</a>" in response.text
            assert product.description in response.text
            assert f"{product.min_stock} {product.meas_unit}" in response.text
        # red color of a critical product
        crit_product =  db_session.scalar(select(Product)
            .filter_by(responsible_id=admin_logged_in.id,
                       in_use=True,
                       critical=True))
        assert ('<td class="text-danger">' +
                f"{crit_product.min_stock} {crit_product.meas_unit}") \
                    in response.text
        # checked and disabled tags for a to_order product
        product =  db_session.scalar(select(Product)
            .filter_by(responsible_id=admin_logged_in.id, in_use=True))
        product.to_order = True
        db_session.commit()
        with client:
            client.get("/")
            response = client.get(url_for("inv.inventory"))
        assert checkbox_checked.search(response.text)
        assert checkbox_checked_disabled.search(response.text)
        product.to_order = False
        # disabled product is not in the inventory page
        product.in_use = False
        db_session.commit()
        with client:
            client.get("/")
            response = client.get(url_for("inv.inventory"))
        assert f">{product.name}</a>" not in response.text
        assert product.description not in response.text
        # teardown
        product.in_use = True
        db_session.commit()


def test_inv_user_logged_in_yes_check_inventory(
        client: FlaskClient, user_logged_in: User):
    """Access inventory page with a user, trigger for inventory check."""
    with dbSession() as db_session:
        db_session.get(User, user_logged_in.id).done_inv = False
        db_session.commit()
    with client:
        response = client.get("/")
        response = client.get(url_for("inv.inventory"))
    # flash message
    assert str(Message.UI.Inv.NotReq()) not in response.text
    # html elements
    assert not inv_not_req_button.search(response.text)
    assert submit_inv_button.search(response.text)
    assert not checkbox_checked.search(response.text)
    assert not checkbox_checked_disabled.search(response.text)
    assert not checkbox_disabled.search(response.text)
    assert not prod_edit_link.search(response.text)
    # table captions
    assert str(Message.UI.Captions.InvOrder()) in response.text
    assert str(Message.UI.Captions.CriticalProducts()) in response.text
    # teardown
    with dbSession() as db_session:
        db_session.get(User, user_logged_in.id).done_inv = True
        db_session.commit()


def test_send_inventory(client: FlaskClient, user_logged_in: User):
    """Send inventory, trigger for inventory check."""
    # trigger inventory check
    with dbSession() as db_session:
        db_session.get(User, user_logged_in.id).done_inv = False
        db_session.commit()
    with client:
        client.get("/")
        response = client.get(url_for("inv.inventory"))
        assert str(Message.UI.Inv.NotReq()) not in response.text
        assert submit_inv_button.search(response.text)
        # add products to data
        data = {}
        users_products = [product for product in test_products
                          if product["responsible_id"] == user_logged_in.id]
        not_user_product = [product for product in test_products
                          if product["responsible_id"] != user_logged_in.id][0]
        users_to_order_products = users_products[::2]
        for product in users_to_order_products:
            data[str(product["id"])] = "on"
        data[str(not_user_product["id"])] = "on"
        # failed submit (no csrf)
        response = client.post(url_for("inv.inventory"), data=data)
        assert response.status_code == 200
        assert "The CSRF token is missing." in response.text
        # submit inventory
        data["csrf_token"] = g.csrf_token
        response = client.post(
            url_for("inv.inventory"), data=data, follow_redirects=True)
        assert redirected_to(url_for("main.index"), response)
    assert str(Message.UI.Inv.Submitted()) in response.text
    # check to_order status in database and teardown
    with dbSession() as db_session:
        assert db_session.get(User, user_logged_in.id).done_inv
        assert not db_session.get(Product, not_user_product["id"]).to_order
        for product in users_products:
            if product in users_to_order_products:
                assert db_session.get(Product, product["id"]).to_order
                db_session.get(Product, product["id"]).to_order = False
            else:
                assert not db_session.get(Product, product["id"]).to_order
        db_session.commit()


def test_failed_send_inventory_no_check_inventory(
        client: FlaskClient, user_logged_in: User):
    """Try to force send inventory, no trigger for inventory check."""
    assert user_logged_in.done_inv
    with client:
        client.get("/")
        response = client.get(url_for("inv.inventory"))
        assert str(Message.UI.Inv.NotReq()) in response.text
        assert not submit_inv_button.search(response.text)
        users_products = [product for product in test_products
                          if product["responsible_id"] == user_logged_in.id]
        # add products to data
        data = {"csrf_token": g.csrf_token}
        for product in users_products[::2]:
            data[str(product["id"])] = "on"
        # failed submit
        response = client.post(url_for("inv.inventory"), data=data)
    assert response.status_code == 200
    assert str(Message.UI.Inv.Submitted()) not in response.text
    # check to_order status in database
    with dbSession() as db_session:
        assert db_session.get(User, user_logged_in.id).done_inv
        for product in users_products[::2]:
            assert not db_session.get(Product, product["id"]).to_order
# endregion


# region: inventory tests for other user
@given(username = st.sampled_from([user["name"] for user in test_users
                                   if user["has_products"]]))
def test_inv_oth_user_not_logged_in(client: FlaskClient, username: str):
    """Try to access the inventory page of other user but not logged in."""
    with client:
        client.get("/")
        response = client.get(
            url_for("inv.inventory_user", username=username),
            follow_redirects=True)
        assert redirected_to(url_for("auth.login"), response)
        assert str(Message.UI.Auth.LoginReq()) in response.text
        assert log_in_button.search(response.text)


@given(username = st.sampled_from([user["name"] for user in test_users
                                   if user["has_products"]]))
def test_inv_oth_user_user_logged_in(
        client: FlaskClient, user_logged_in: User, username: str):
    """Try to access the inventory page of other user, logged in as user."""
    with client:
        client.get("/")
        assert session["user_name"] == user_logged_in.name
        assert not session["admin"]
        response = client.get(
            url_for("inv.inventory_user", username=username),
            follow_redirects=True)
        assert redirected_to(url_for("auth.login"), response)
        assert str(Message.UI.Auth.AdminReq()) in response.text
        assert log_in_button.search(response.text)


@given(user = st.sampled_from([user for user in test_users
                               if user["has_products"]]))
def test_inv_oth_user_no_check_inventory(
        client: FlaskClient, admin_logged_in: User, user: dict[str]):
    """Access the inventory page of other users, logged in as admin,
    no trigger for inventory check."""
    with client:
        client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        response = client.get(
            url_for("inv.inventory_user", username=user["name"]))
    assert response.status_code == 200
    assert user["name"] in response.text
    assert str(Message.UI.Auth.AdminReq()) not in response.text
    assert str(Message.UI.Inv.NotReq()) in response.text
    assert not log_in_button.search(response.text)
    assert inv_not_req_button.search(response.text)
    # all user products present in the table
    with dbSession() as db_session:
        products =  db_session.scalars(select(Product)
            .filter_by(responsible_id=user["id"], in_use=True)).all()
    for product in products:
        assert product.name in response.text
        assert product.description in response.text
        assert f"{product.min_stock} {product.meas_unit}" in response.text


@given(user = st.sampled_from(
    [user for user in test_users if not user["active"]]))
@example(user = [user for user in test_users if not user["in_use"]][0])
@example(user = [user for user in test_users if user["reg_req"]][0])
def test_failed_inv_oth_user_special_users(
        client: FlaskClient, admin_logged_in: User, user: dict[str]):
    """Fail to access the inventory of special users"""
    if not user["in_use"]:
        flash_message = str(Message.User.Retired(user["name"]))
    else:
        flash_message = str(Message.User.RegPending(user["name"]))
    with client:
        client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        response = client.get(
            url_for("inv.inventory_user", username=user["name"]),
            follow_redirects=True)
        assert redirected_to(url_for("main.index"), response)
        assert flash_message in response.text


@given(username = st.text(min_size=1, alphabet=string.ascii_lowercase).filter(
        lambda x: x not in [user["name"] for user in test_users]))
def test_failed_inv_oth_user_not_existing_user(
        client: FlaskClient, admin_logged_in: User, username: str):
    """Fail to access the inventory of non existing user"""
    flash_message = str(Message.User.NotExists(username))
    with client:
        client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        response = client.get(
            url_for("inv.inventory_user", username=username),
            follow_redirects=True)
        assert redirected_to(url_for("main.index"), response)
        assert flash_message in response.text


@given(user = st.sampled_from([user for user in test_users
                               if user["has_products"]]))
def test_send_inventory_for_other_user(
        client: FlaskClient, admin_logged_in: User, user: dict[str]):
    """Send inventory for other user, trigger for inventory check."""
    with dbSession() as db_session:
        db_session.get(User, user["id"]).done_inv = False
        db_session.commit()
    with client:
        client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        response = client.get(
            url_for("inv.inventory_user", username=user["name"]))
        assert response.status_code == 200
        assert user["name"] in response.text
        assert str(Message.UI.Inv.NotReq()) not in response.text
        assert submit_inv_button.search(response.text)
        assert not inv_not_req_button.search(response.text)
        # add products to data
        data = {}
        users_products = [product for product in test_products
                          if product["responsible_id"] == user["id"]]
        not_user_product = [product for product in test_products
                            if product["responsible_id"] != user["id"]][0]
        users_to_order_products = users_products[::2]
        for product in users_to_order_products:
            data[str(product["id"])] = "on"
        data[str(not_user_product["id"])] = "on"
        # failed submit (no csrf)
        response = client.post(
            url_for("inv.inventory_user", username=user["name"]),
            data=data)
        assert response.status_code == 200
        assert "The CSRF token is missing." in response.text
        # submit inventory
        data["csrf_token"] = g.csrf_token
        response = client.post(
            url_for("inv.inventory_user", username=user["name"]),
            data=data,
            follow_redirects=True)
        assert redirected_to(url_for("main.index"), response)
    assert str(Message.UI.Inv.Submitted()) in response.text
    # check to_order status in database and teardown
    with dbSession() as db_session:
        assert db_session.get(User, user["id"]).done_inv
        assert not db_session.get(Product, not_user_product["id"]).to_order
        for product in users_products:
            if product in users_to_order_products:
                assert db_session.get(Product, product["id"]).to_order
                db_session.get(Product, product["id"]).to_order = False
            else:
                assert not db_session.get(Product, product["id"]).to_order
        db_session.commit()
# endregion


# region: inventory request
def test_inventory_request_not_logged_in(client: FlaskClient):
    """Try to request inventory but not logged in."""
    with client:
        client.get("/")
        assert not session.get("user_name")
        response = client.get(url_for("inv.inventory_request"),
                              follow_redirects=True)
        assert redirected_to(url_for("auth.login"), response)
        assert str(Message.UI.Auth.LoginReq()) in response.text
        assert log_in_button.search(response.text)


@given(admin = st.sampled_from([user for user in test_users
                                if user["admin"] and user["has_products"]]))
def test_failed_inventory_request_admin(
        client: FlaskClient, admin: dict[str]):
    """Try to request inventory with an admin"""
    with client.session_transaction() as this_session:
        this_session["user_id"] = admin["id"]
        this_session["admin"] = True
        this_session["user_name"] = admin["name"]
    with client:
        client.get("/")
        assert session["admin"]
        response = client.get(url_for("inv.inventory_request"),
                              follow_redirects=True)
        assert redirected_to(url_for("main.index"), response)
        assert str(Message.User.ReqInv.Admin()) in response.text
        assert str(Message.User.ReqInv.Sent()) not in response.text
        client.get("/auth/logout")
    with dbSession() as db_session:
        assert not db_session.get(User, admin["id"]).req_inv


@given(user = st.sampled_from([user for user in test_users
                               if not user["admin"] and user["has_products"]]))
def test_inventory_request_user(
        client: FlaskClient, user: dict[str]):
    """Request inventory with user"""
    with client.session_transaction() as this_session:
        this_session["user_id"] = user["id"]
        this_session["admin"] = False
        this_session["user_name"] = user["name"]
    with client:
        client.get("/")
        assert not session["admin"]
        response = client.get(url_for("inv.inventory_request"),
                              follow_redirects=True)
        assert redirected_to(url_for("main.index"), response)
        assert str(Message.User.ReqInv.Admin()) not in response.text
        assert str(Message.User.ReqInv.Sent()) in response.text
        client.get("/auth/logout")
    with dbSession() as db_session:
        assert db_session.get(User, user["id"]).req_inv
        db_session.get(User, user["id"]).req_inv = False
        db_session.commit()


@given(user = st.sampled_from([user for user in test_users
                               if not user["admin"] and user["has_products"]]))
def test_inventory_request_user_logged_in_yes_check_inventory(
        client: FlaskClient, user: dict[str]):
    """Request inventorying with a user that can already check inventory"""
    with dbSession() as db_session:
        db_session.get(User, user["id"]).done_inv = False
        db_session.commit()
    with client.session_transaction() as this_session:
        this_session["user_id"] = user["id"]
        this_session["admin"] = False
        this_session["user_name"] = user["name"]
    with client:
        client.get("/")
        assert not session["admin"]
        response = client.get(url_for("inv.inventory_request"),
                              follow_redirects=True)
        assert redirected_to(url_for("inv.inventory"), response)
        assert str(Message.User.ReqInv.Sent()) not in response.text
        assert str(Message.User.ReqInv.CheckInv()) in response.text
        assert submit_inv_button.search(response.text)
        client.get("/auth/logout")
    with dbSession() as db_session:
        assert not db_session.get(User, user["id"]).req_inv
        db_session.get(User, user["id"]).done_inv = True
        db_session.commit()
# endregion
