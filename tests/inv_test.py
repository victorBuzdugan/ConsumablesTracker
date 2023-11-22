"""Inventory blueprint tests."""

from html import unescape
from typing import Callable

import pytest
from flask import g, session, url_for
from flask.testing import FlaskClient
from sqlalchemy import func, select

from database import Product, User, dbSession
from messages import Message

func: Callable

pytestmark = pytest.mark.inv


# region: inventory tests for current user
def test_inv_user_not_logged_in(client: FlaskClient):
    """Try to access the inventory page but not logged in."""
    with client:
        response = client.get("/")
        response = client.get(url_for("inv.inventory"), follow_redirects=True)
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("auth.login")
        assert str(Message.UI.Auth.LoginReq()) in response.text
        assert 'type="submit" value="Log In"' in response.text


def test_inv_user_logged_in_no_check_inventory(
        client: FlaskClient, user_logged_in: User):
    """Access inventory page with a user, no trigger for inventory check."""
    with client:
        client.get("/")
        response = client.get(url_for("inv.inventory"))
        assert "checked" not in response.text
        assert str(Message.UI.Inv.NotReq()) in response.text
        assert 'Inventory check' in response.text
        assert 'href="/product/edit/' not in response.text
        assert f'<span class="text-secondary">{user_logged_in.name}</span>' \
            in response.text
        assert 'value="Inventory check not required" disabled' in response.text
        assert 'value="Submit inventory"' not in response.text
        assert "Critical products are highlighted in red" not in response.text
        with dbSession() as db_session:
            product =  db_session.scalar(
                select(Product)\
                .filter_by(responsible_id=user_logged_in.id, in_use=True))
            assert f"{product.name}" in response.text
            assert f"{product.description}" in response.text
            assert f"{product.min_stock} {product.meas_unit}" in response.text

            # red color of a critical product
            product_crit =  db_session.scalar(
                select(Product)\
                .filter_by(
                    responsible_id=user_logged_in.id,
                    in_use=True,
                    critical=True))
            assert f"{product_crit.name}" in response.text
            assert f"{product_crit.description}" in response.text
            assert ('<td class="text-danger">' +
                    f"{product_crit.min_stock} {product_crit.meas_unit}") \
                        in response.text

            # disabled and checked tags for a to_order product
            product.to_order = True
            db_session.commit()
            response = client.get(url_for("inv.inventory"))
            assert f'id="{product.id}" name="{product.id}" disabled checked' \
                in response.text
            product.to_order = False
            db_session.commit()


def test_inv_admin_logged_in_no_check_inventory(
        client: FlaskClient, admin_logged_in: User):
    """Access inventory page with an admin, no trigger for inventory check."""
    with client:
        response = client.get("/")
        response = client.get(url_for("inv.inventory"))
        assert "checked" not in response.text
        assert str(Message.UI.Inv.NotReq()) in response.text
        assert "Inventory check" in response.text
        assert 'href="/product/edit/' in response.text
        assert f'<span class="text-secondary">{admin_logged_in.name}</span>' \
            in response.text
        assert 'value="Inventory check not required" disabled' in response.text
        assert 'value="Submit inventory"' not in response.text
        assert "Critical products are highlighted in red" not in response.text
        with dbSession() as db_session:
            product =  db_session.scalar(
                select(Product)\
                .filter_by(responsible_id=admin_logged_in.id, in_use=True))
            assert f"{product.name}" in response.text
            assert f"{product.description}" in response.text
            assert f"{product.min_stock} {product.meas_unit}" in response.text

            product_crit =  db_session.scalar(
                select(Product)\
                .filter_by(
                    responsible_id=admin_logged_in.id,
                    in_use=True,
                    critical=True))
            assert f"{product_crit.name}" in response.text
            assert f"{product_crit.description}" in response.text
            assert ('<td class="text-danger">' +
                    f"{product_crit.min_stock} {product_crit.meas_unit}") \
                        in response.text

            product.to_order = True
            db_session.commit()
            response = client.get(url_for("inv.inventory"))
            assert f'id="{product.id}" name="{product.id}" disabled checked' \
                in response.text
            product.to_order = False
            db_session.commit()

            products_len = db_session.scalar(select(func.count(Product.id)).
                filter_by(responsible_id=session.get("user_id"), in_use=True))
            product.in_use = False
            db_session.commit()
            response = client.get(url_for("inv.inventory"))
            assert (f'id="{product.id}" name="{product.id}" disabled checked')\
                not in response.text
            assert db_session.scalar(select(func.count(Product.id)).
                filter_by(
                    responsible_id=admin_logged_in.id,
                    in_use=True)) == products_len - 1
            product.in_use = True
            db_session.commit()


def test_inv_user_logged_in_yes_check_inventory(
        client: FlaskClient, user_logged_in: User):
    """Access inventory page with a user, trigger for inventory check."""
    with client:
        response = client.get("/")
        with dbSession() as db_session:
            db_session.get(User, user_logged_in.id).done_inv = False
            db_session.commit()
        response = client.get(url_for("inv.inventory"))
        assert "checked" not in response.text
        assert str(Message.UI.Inv.NotReq()) not in response.text
        assert 'href="/product/edit/' not in response.text
        assert 'value="Inventory check not required" disabled' \
            not in response.text
        assert 'value="Submit inventory"' in response.text
        assert "Critical products are highlighted in red" in response.text
        with dbSession() as db_session:
            product =  db_session.scalar(
                select(Product)
                .filter_by(responsible_id=user_logged_in.id, in_use=True))
            assert f"{product.name}" in response.text
            assert f"{product.description}" in response.text
            assert f"{product.min_stock} {product.meas_unit}" in response.text

            product_crit =  db_session.scalar(
                select(Product)
                .filter_by(
                    responsible_id=user_logged_in.id,
                    in_use=True,
                    critical=True))
            assert f"{product_crit.name}" in response.text
            assert f"{product_crit.description}" in response.text
            assert ('<td class="text-danger">' +
                    f"{product_crit.min_stock} {product_crit.meas_unit}") \
                        in response.text

            product.to_order = True
            db_session.commit()
            response = client.get(url_for("inv.inventory"))
            assert f'id="{product.id}" name="{product.id}"  checked' \
                in response.text
            product.to_order = False
            db_session.get(User, user_logged_in.id).done_inv = True
            db_session.commit()


def test_send_inventory_yes_check_inventory(
        client: FlaskClient, user_logged_in: User):
    """Send inventory, trigger for inventory check."""
    with client:
        client.get("/")
        response = client.get(url_for("inv.inventory"))
        assert str(Message.UI.Inv.NotReq()) in response.text
        # trigger inventory check
        with dbSession() as db_session:
            db_session.get(User, user_logged_in.id).done_inv = False
            db_session.commit()

        response = client.get(url_for("inv.inventory"))
        assert str(Message.UI.Inv.NotReq()) not in response.text
        assert 'value="Submit inventory"' in response.text

        # 22 is not assigned to this user
        data = {
            "csrf_token": g.csrf_token,
            "20": "on",
            "22": "on",
            "34": "on"}
        response = client.post(url_for("inv.inventory"),
                               data=data,
                               follow_redirects=True)
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == "/"
        assert str(Message.UI.Inv.Submitted()) in response.text

        # check to_order status in database and teardown
        with dbSession() as db_session:
            assert db_session.get(Product, 20).to_order
            assert not db_session.get(Product, 22).to_order
            assert db_session.get(Product, 34).to_order
            assert db_session.get(User, session.get("user_id")).done_inv
            db_session.get(Product, 20).to_order = False
            db_session.get(Product, 34).to_order = False
            db_session.commit()


def test_send_inventory_yes_check_inventory_no_csrf(
        client: FlaskClient, user_logged_in: User):
    """Send inventory, trigger for inventory check, post without csrf."""
    with client:
        client.get("/")
        response = client.get(url_for("inv.inventory"))
        assert str(Message.UI.Inv.NotReq()) in response.text
        # trigger inventory check
        with dbSession() as db_session:
            db_session.get(User, user_logged_in.id).done_inv = False
            db_session.commit()

        response = client.get(url_for("inv.inventory"))
        assert str(Message.UI.Inv.NotReq()) not in response.text
        assert 'value="Submit inventory"' in response.text

        data = {
            "20": "on",
            "34": "on"}
        response = client.post(
            url_for("inv.inventory"), data=data, follow_redirects=True)
        assert len(response.history) == 0
        assert response.status_code == 200
        assert "The CSRF token is missing." in response.text

        # check to_order status in database and teardown
        with dbSession() as db_session:
            assert not db_session.get(Product, 20).to_order
            assert not db_session.get(Product, 34).to_order
            assert not db_session.get(User, user_logged_in.id).done_inv
            db_session.get(User, user_logged_in.id).done_inv = True
            db_session.commit()


def test_send_inventory_no_check_inventory(client: FlaskClient, user_logged_in):
    """Try to force send inventory, no trigger for inventory check."""
    with client:
        client.get("/")
        response = client.get(url_for("inv.inventory"))
        assert str(Message.UI.Inv.NotReq()) in response.text
        assert 'value="Submit inventory"' not in response.text

        data = {
            "csrf_token": g.csrf_token,
            "20": "on",
            "34": "on"}
        response = client.post(
            url_for("inv.inventory"), data=data, follow_redirects=True)
        assert len(response.history) == 0
        assert response.status_code == 200
        assert str(Message.UI.Inv.NotReq()) in response.text

        # check to_order status in database and teardown
        with dbSession() as db_session:
            assert not db_session.get(Product, 20).to_order
            assert not db_session.get(Product, 34).to_order
            assert db_session.get(User, user_logged_in.id).done_inv
# endregion


# region: inventory tests for other user
def test_oth_user_not_logged_in(client: FlaskClient):
    """Try to access the inventory page of other user but not logged in."""
    with client:
        client.get("/")
        response = client.get(
            f"{url_for('inv.inventory_user', username='user1')}",
            follow_redirects=True)
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("auth.login")
        assert str(Message.UI.Auth.AdminReq()) in response.text
        assert 'type="submit" value="Log In"' in response.text


def test_oth_user_user_logged_in(
        client: FlaskClient, user_logged_in: User):
    """Try to access the inventory page of other user, logged in as user."""
    with client:
        client.get("/")
        assert session["user_name"] == user_logged_in.name
        assert not session["admin"]
        assert session.get("user_id")
        response = client.get(
            f"{url_for('inv.inventory_user', username='user1')}",
            follow_redirects=True)
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("auth.login")
        assert str(Message.UI.Auth.AdminReq()) in response.text
        assert 'type="submit" value="Log In"' in response.text


@pytest.mark.parametrize(("oth_user",), (("user2",), ("user3",), ("user4",)))
def test_oth_user_admin_logged_in_no_check_inventory(
        client: FlaskClient, admin_logged_in: User,
        oth_user):
    """Access the inventory page of other users, logged in as admin,
    no trigger for inventory check.."""
    with dbSession() as db_session:
        oth_user = db_session.scalar(select(User).filter_by(name=oth_user))
    with client:
        client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        response = client.get(
            f"{url_for('inv.inventory_user', username=oth_user.name)}",
            follow_redirects=True)
        assert session.get("admin")
    assert len(response.history) == 0
    assert response.status_code == 200
    assert str(Message.UI.Auth.AdminReq()) not in response.text
    assert 'type="submit" value="Log In"' not in response.text
    assert "Inventory check" in response.text
    assert f'<span class="text-secondary">{oth_user.name}</span>' \
        in response.text

    # check if a random and a critical product from this user is on the page
    with dbSession() as db_session:
        product =  db_session.scalar(
            select(Product)
            .filter_by(responsible_id=oth_user.id, in_use=True))
        product_crit =  db_session.scalar(
            select(Product)
            .filter_by(responsible_id=oth_user.id, in_use=True, critical=True))
    assert f"{product.name}" in response.text
    assert f"{product.description}" in response.text
    assert f"{product.min_stock} {product.meas_unit}" in response.text

    # red color of a critical product
    assert f"{product_crit.name}" in response.text
    assert f"{product_crit.description}" in response.text
    assert ('<td class="text-danger">' +
            f"{product_crit.min_stock} {product_crit.meas_unit}") \
                in response.text

    # disabled and checked tags for a to_order product
    with client:
        with dbSession() as db_session:
            db_session.get(Product, product.id).to_order = True
            db_session.commit()
            client.get("/")
            response = client.get(
                url_for("inv.inventory_user", username=oth_user.name))
            assert f'id="{product.id}" name="{product.id}" disabled checked' \
                in response.text
            db_session.get(Product, product.id).to_order = False
            db_session.commit()


@pytest.mark.parametrize(
    ("oth_user", "flash_message"), (
    ("nonexistent", str(Message.User.NotExists("nonexistent"))),
    ("user5", str(Message.User.RegPending("user5"))),
    ("user6", str(Message.User.Retired("user6")))
))
def test_oth_user_admin_logged_in_special_users(
        client: FlaskClient, admin_logged_in: User,
        oth_user, flash_message):
    """Fail to access the inventory of other users , logged in as admin"""
    with dbSession() as db_session:
        db_session.get(User, 5).reg_req = True
        db_session.commit()
    with client:
        client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        response = client.get(
            f"{url_for('inv.inventory_user', username=oth_user)}",
            follow_redirects=True)
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("main.index")
        assert flash_message in response.text
        assert "Admin dashboard" in response.text


def test_oth_user_admin_logged_in_yes_check_inventory(
        client: FlaskClient, admin_logged_in: User):
    """Access the inventory page of other user, trigger for inventory check.."""
    with dbSession() as db_session:
        oth_user = db_session.get(User, 4)
    assert oth_user.done_inv

    # before triggering inventory check
    with client:
        client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        response = client.get(
            f"{url_for('inv.inventory_user', username=oth_user.name)}")
    assert "Inventory check" in response.text
    assert f'<span class="text-secondary">{oth_user.name}</span>' \
        in response.text
    assert "checked" not in response.text
    assert "disabled" in response.text
    assert str(Message.UI.Inv.NotReq()) in response.text
    assert 'value="Inventory check not required" disabled' in response.text
    assert 'value="Submit inventory"' not in response.text
    assert "Critical products are highlighted in red" not in response.text

    # trigger inventory check
    with dbSession() as db_session:
        db_session.get(User, oth_user.id).done_inv = False
        db_session.commit()
        product =  db_session.scalar(
            select(Product)
            .filter_by(responsible_id=oth_user.id, in_use=True))
    with client:
        client.get("/")
        response = client.get(
            f"{url_for('inv.inventory_user', username=oth_user.name)}")
    assert "Inventory check" in response.text
    assert f'<span class="text-secondary">{oth_user.name}</span>' \
        in response.text
    assert "checked" not in response.text
    assert "disabled" not in response.text
    assert str(Message.UI.Inv.NotReq()) not in response.text
    assert 'value="Inventory check not required" disabled' not in response.text
    assert 'value="Submit inventory"' in response.text
    assert "Critical products are highlighted in red" in response.text
    assert f"{product.name}" in response.text
    assert f"{product.description}" in response.text
    assert f"{product.min_stock} {product.meas_unit}" in response.text

    # teardown
    with dbSession() as db_session:
        db_session.get(User, oth_user.id).done_inv = True
        db_session.commit()


def test_oth_user_send_inventory_yes_check_inventory(
        client: FlaskClient, admin_logged_in: User):
    """Send inventory for other user, trigger for inventory check."""
    with dbSession() as db_session:
        oth_user = db_session.get(User, 4)
        oth_user.done_inv = False
        db_session.commit()
        db_session.refresh(oth_user)
    with client:
        client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        assert session.get("admin")
        response = client.get(
            f"{url_for('inv.inventory_user', username=oth_user.name)}")
    assert str(Message.UI.Inv.NotReq()) not in response.text
    assert "Inventory check" in response.text
    assert f'<span class="text-secondary">{oth_user.name}</span>' \
        in response.text
    assert 'value="Submit inventory"' in response.text

    # 22 is not assigned to this user
    with client:
        client.get("/")
        client.get(
            f"{url_for('inv.inventory_user', username=oth_user.name)}")
        data = {
            "csrf_token": g.csrf_token,
            "20": "on",
            "22": "on",
            "34": "on"}
        response = client.post(
            f"{url_for('inv.inventory_user', username=oth_user.name)}",
            data=data,
            follow_redirects=True)
    assert len(response.history) == 1
    assert response.history[0].status_code == 302
    assert response.status_code == 200
    assert response.request.path == "/"
    assert str(Message.UI.Inv.Submitted()) in response.text

    # check to_order status in database and teardown
    with dbSession() as db_session:
        assert db_session.get(Product, 20).to_order
        assert not db_session.get(Product, 22).to_order
        assert db_session.get(Product, 34).to_order
        assert db_session.get(User, oth_user.id).done_inv
        db_session.get(Product, 20).to_order = False
        db_session.get(Product, 34).to_order = False
        db_session.commit()


def test_oth_user_send_inventory_yes_check_inventory_no_csrf(
        client: FlaskClient, admin_logged_in: User):
    """Try to send inventory for other user without csrf token,
    trigger for inventory check."""
    with dbSession() as db_session:
        oth_user = db_session.get(User, 4)
        oth_user.done_inv = False
        db_session.commit()
        db_session.refresh(oth_user)
    with client:
        client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        response = client.get(
            f"{url_for('inv.inventory_user', username=oth_user.name)}")
    assert str(Message.UI.Inv.NotReq()) not in response.text
    assert 'Inventory check' in response.text
    assert f'<span class="text-secondary">{oth_user.name}</span>' \
        in response.text
    assert 'value="Submit inventory"' in response.text

    with client:
        client.get("/")
        client.get(
            f"{url_for('inv.inventory_user', username=oth_user.name)}")
        data = {
            "20": "on",
            "34": "on"}
        response = client.post(
            f"{url_for('inv.inventory_user', username=oth_user.name)}",
            data=data, follow_redirects=True)
    assert len(response.history) == 0
    assert response.status_code == 200
    assert "The CSRF token is missing." in response.text

    # check to_order status in database and teardown
    with dbSession() as db_session:
        assert not db_session.get(Product, 20).to_order
        assert not db_session.get(Product, 34).to_order
        assert not db_session.get(User, oth_user.id).done_inv
        db_session.get(User, oth_user.id).done_inv = True
        db_session.commit()
# endregion


# region: inventory request
def test_inventory_request_not_logged_in(client: FlaskClient):
    """Try to request inventory but not logged in."""
    with client:
        client.get("/")
        assert not session.get("user_name")
        response = client.get(
            f"{url_for('inv.inventory_request')}", follow_redirects=True)
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("auth.login")
        assert str(Message.UI.Auth.LoginReq()) in response.text
        assert 'type="submit" value="Log In"' in response.text


def test_inventory_request_admin_logged_in(
        client: FlaskClient, admin_logged_in: User):
    """Try to request inventory with admin."""
    with client:
        client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        response = client.get(
            f"{url_for('inv.inventory_request')}", follow_redirects=True)
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("main.index")
        assert str(Message.User.ReqInv.Admin()) in unescape(response.text)
        assert "check inventory" not in response.text
        with dbSession() as db_session:
            assert not db_session.get(User, session.get("user_id")).req_inv


def test_inventory_request_user_logged_in(
        client: FlaskClient, user_logged_in: User):
    """Request inventory with user."""
    with client:
        client.get("/")
        assert session["user_name"] == user_logged_in.name
        assert not session["admin"]
        response = client.get(
            f"{url_for('inv.inventory_request')}", follow_redirects=True)
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("main.index")
        assert str(Message.User.ReqInv.Sent()) in response.text
        assert "You requested a inventory check" in response.text
        with dbSession() as db_session:
            assert db_session.get(User, user_logged_in.id).req_inv
            db_session.get(User, user_logged_in.id).req_inv = False
            db_session.commit()


def test_inventory_request_user_logged_in_yes_check_inventory(
        client: FlaskClient, user_logged_in: User):
    """Request inventory with user, trigger for inventory check."""
    with client:
        # set check inventory
        client.get("/")
        assert session["user_name"] == user_logged_in.name
        assert not session["admin"]
        with dbSession() as db_session:
            db_session.get(User, user_logged_in.id).done_inv = False
            db_session.commit()
        response = client.get(
            f"{url_for('inv.inventory_request')}", follow_redirects=True)
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for('inv.inventory')
        assert "User can allready check inventory" in response.text
        assert "Critical products are highlighted in red" in response.text
        with dbSession() as db_session:
            assert not db_session.get(User, user_logged_in.id).req_inv
            db_session.get(User, user_logged_in.id).done_inv = True
            db_session.commit()
# endregion
