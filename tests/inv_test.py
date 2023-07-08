"""Inventory blueprint tests."""

import pytest
from flask import session, url_for, g
from flask.testing import FlaskClient
from sqlalchemy import select

from database import User, dbSession, Category, Supplier, Product
from tests import (admin_logged_in, client, create_test_categories,
                   create_test_db, create_test_suppliers, create_test_users,
                   user_logged_in, create_test_products)

pytestmark = pytest.mark.inv


# region: inventory tests for current user
def test_inv_user_not_logged_in(client: FlaskClient):
    """Try to access the inventory page but not logged in."""
    response = client.get("/inventory", follow_redirects=True)
    assert len(response.history) == 1
    assert response.history[0].status_code == 302
    assert response.status_code == 200
    assert response.request.path == "/auth/login"
    assert b"You have to be logged in..." in response.data
    assert b'type="submit" value="Log In"' in response.data


def test_inv_user_logged_in_no_check_inventory(client: FlaskClient, user_logged_in):
    """Access inventory page with a user, no trigger for inventory check."""
    with client:
        response = client.get("/inventory")
        assert b"checked" not in response.data
        assert b"Inventory check not required" in response.data
        assert b'Inventory check' in response.data
        assert f'<span class="text-secondary">{session.get("user_name")}</span>' in response.text
        assert b'input class="btn btn-primary" type="submit" value="Inventory check not required" disabled' in response.data
        assert b'input class="btn btn-primary" type="submit" value="Submit inventory"' not in response.data
        assert b"Critical products are highlighted in red" not in response.data
        with dbSession() as db_session:
            product =  db_session.scalar(
                select(Product)\
                .filter_by(responsable_id=session.get("user_id"), in_use=True))
            assert f"{product.name}" in response.text
            assert f"{product.description}" in response.text
            assert f"{product.min_stock} {product.meas_unit}" in response.text
            
            # red color of a critical product
            product_crit =  db_session.scalar(
                select(Product)\
                .filter_by(responsable_id=session.get("user_id"), in_use=True, critical=True))
            assert f"{product_crit.name}" in response.text
            assert f"{product_crit.description}" in response.text
            assert ('<td class="text-danger">' +
                    f"{product_crit.min_stock} {product_crit.meas_unit}") in response.text
            
            # disabled and checked tags for a to_order product
            product.to_order = True
            db_session.commit()
            response = client.get("/inventory")
            assert (f"id={product.id}" +
                    f" name={product.id}" +
                    " disabled checked") in response.text
            product.to_order = False
            db_session.commit()
            

def test_inv_admin_logged_in_no_check_inventory(client: FlaskClient, admin_logged_in):
    """Access inventory page with an admin, no trigger for inventory check."""
    with client:
        response = client.get("/inventory")
        assert b"checked" not in response.data
        assert b"Inventory check not required" in response.data
        assert b'Inventory check' in response.data
        assert f'<span class="text-secondary">{session.get("user_name")}</span>' in response.text
        assert b'input class="btn btn-primary" type="submit" value="Inventory check not required" disabled' in response.data
        assert b'input class="btn btn-primary" type="submit" value="Submit inventory"' not in response.data
        assert b"Critical products are highlighted in red" not in response.data
        with dbSession() as db_session:
            product =  db_session.scalar(
                select(Product)\
                .filter_by(responsable_id=session.get("user_id"), in_use=True))
            assert f"{product.name}" in response.text
            assert f"{product.description}" in response.text
            assert f"{product.min_stock} {product.meas_unit}" in response.text
            
            product_crit =  db_session.scalar(
                select(Product)\
                .filter_by(responsable_id=session.get("user_id"), in_use=True, critical=True))
            assert f"{product_crit.name}" in response.text
            assert f"{product_crit.description}" in response.text
            assert ('<td class="text-danger">' +
                    f"{product_crit.min_stock} {product_crit.meas_unit}") in response.text
            
            product.to_order = True
            db_session.commit()
            response = client.get("/inventory")
            assert (f"id={product.id}" +
                    f" name={product.id}" +
                    " disabled checked") in response.text
            product.to_order = False
            db_session.commit()

            products_len = db_session.query(Product)\
                .filter_by(responsable_id=session.get("user_id"), in_use=True)\
                .count()
            product.in_use = False
            db_session.commit()
            response = client.get("/inventory")
            assert (f"id={product.id}" +
                    f" name={product.id}" +
                    " disabled checked") not in response.text
            assert db_session.query(Product)\
                .filter_by(responsable_id=session.get("user_id"), in_use=True)\
                .count() == products_len - 1
            product.in_use = True
            db_session.commit()


def test_inv_user_logged_in_yes_check_inventory(client: FlaskClient, user_logged_in):
    """Access inventory page with a user, trigger for inventory check."""
    with client:
        response = client.get("/")
        with dbSession() as db_session:
            db_session.get(User, session.get("user_id")).done_inv = False
            db_session.commit()
        response = client.get("/inventory")
        assert b"checked" not in response.data
        assert b"Inventory check not required" not in response.data
        assert b'input class="btn btn-primary" type="submit" value="Inventory check not required" disabled' not in response.data
        assert b'input class="btn btn-primary" type="submit" value="Submit inventory"' in response.data
        assert b"Critical products are highlighted in red" in response.data
        with dbSession() as db_session:
            product =  db_session.scalar(
                select(Product)\
                .filter_by(responsable_id=session.get("user_id"), in_use=True))
            assert f"{product.name}" in response.text
            assert f"{product.description}" in response.text
            assert f"{product.min_stock} {product.meas_unit}" in response.text
            
            product_crit =  db_session.scalar(
                select(Product)\
                .filter_by(responsable_id=session.get("user_id"), in_use=True, critical=True))
            assert f"{product_crit.name}" in response.text
            assert f"{product_crit.description}" in response.text
            assert ('<td class="text-danger">' +
                    f"{product_crit.min_stock} {product_crit.meas_unit}") in response.text
            
            product.to_order = True
            db_session.commit()
            response = client.get("/inventory")
            assert (f"id={product.id}" +
                    f" name={product.id}" +
                    "  checked") in response.text
            product.to_order = False
            db_session.get(User, session.get("user_id")).done_inv = True
            db_session.commit()


def test_send_inventory_yes_check_inventory(client: FlaskClient, user_logged_in):
    """Send inventory, trigger for inventory check."""
    with client:
        response = client.get("/inventory")
        assert b"Inventory check not required" in response.data
        # trigger inventory check  
        with dbSession() as db_session:
            db_session.get(User, session.get("user_id")).done_inv = False
            db_session.commit()
        
        response = client.get("/inventory")
        assert b"Inventory check not required" not in response.data
        assert b'input class="btn btn-primary" type="submit" value="Submit inventory"' in response.data

        # 22 is not assigned to this user
        data = {
            "csrf_token": g.csrf_token,
            "20": "on",
            "22": "on",
            "34": "on"}
        response = client.post(
            "/inventory", data=data, follow_redirects=True)
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == "/"
        assert b"Inventory has been submitted" in response.data

        # check to_order status in database and teardown
        with dbSession() as db_session:
            assert db_session.get(Product, 20).to_order
            assert not db_session.get(Product, 22).to_order
            assert db_session.get(Product, 34).to_order
            assert db_session.get(User, session.get("user_id")).done_inv
            db_session.get(Product, 20).to_order = False
            db_session.get(Product, 34).to_order = False
            db_session.commit()


def test_send_inventory_yes_check_inventory_no_csrf(client: FlaskClient, user_logged_in):
    """Send inventory, trigger for inventory check, post without csrf."""
    with client:
        response = client.get("/inventory")
        assert b"Inventory check not required" in response.data
        # trigger inventory check  
        with dbSession() as db_session:
            db_session.get(User, session.get("user_id")).done_inv = False
            db_session.commit()
        
        response = client.get("/inventory")
        assert b"Inventory check not required" not in response.data
        assert b'input class="btn btn-primary" type="submit" value="Submit inventory"' in response.data

        data = {
            "20": "on",
            "34": "on"}
        response = client.post(
            "/inventory", data=data, follow_redirects=True)
        assert len(response.history) == 0
        assert response.status_code == 200
        assert b"The CSRF token is missing." in response.data

        # check to_order status in database and teardown
        with dbSession() as db_session:
            assert not db_session.get(Product, 20).to_order
            assert not db_session.get(Product, 34).to_order
            assert not db_session.get(User, session.get("user_id")).done_inv
            db_session.get(User, session.get("user_id")).done_inv = True
            db_session.commit()


def test_send_inventory_no_check_inventory(client: FlaskClient, user_logged_in):
    """Try to force send inventory, no trigger for inventory check."""
    with client:
        response = client.get("/inventory")
        assert b"Inventory check not required" in response.data
        assert b'input class="btn btn-primary" type="submit" value="Submit inventory"' not in response.data
        
        data = {
            "csrf_token": g.csrf_token,
            "20": "on",
            "34": "on"}
        response = client.post(
            "/inventory", data=data, follow_redirects=True)
        assert len(response.history) == 0
        assert response.status_code == 200
        assert b"Inventory check not required" in response.data

        # check to_order status in database and teardown
        with dbSession() as db_session:
            assert not db_session.get(Product, 20).to_order
            assert not db_session.get(Product, 34).to_order
            assert db_session.get(User, session.get("user_id")).done_inv
# endregion


# region: inventory tests for other user
def test_oth_user_not_logged_in(client: FlaskClient):
    """Try to access the inventory page of other user but not logged in."""
    with client:
        client.get("/")
        response = client.get(
            f"{url_for('inv.inventory_user', username='user1')}", follow_redirects=True)
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == "/auth/login"
        assert b"You have to be an admin..." in response.data
        assert b'type="submit" value="Log In"' in response.data


def test_oth_user_user_logged_in(client: FlaskClient, user_logged_in):
    """Try to access the inventory page of other user, logged in as user."""
    with client:
        client.get("/")
        assert session.get("user_id")
        response = client.get(
            f"{url_for('inv.inventory_user', username='user1')}", follow_redirects=True)
    assert len(response.history) == 1
    assert response.history[0].status_code == 302
    assert response.status_code == 200
    assert response.request.path == "/auth/login"
    assert b"You have to be an admin..." in response.data
    assert b'type="submit" value="Log In"' in response.data

@pytest.mark.parametrize(("oth_user",), (("user2",), ("user3",), ("user4",)))
def test_oth_user_admin_logged_in_no_check_inventory(
        client: FlaskClient,
        admin_logged_in,
        oth_user):
    """Access the inventory page of other users, logged in as admin,
    no trigger for inventory check.."""
    with dbSession() as db_session:
        oth_user = db_session.scalar(select(User).filter_by(name=oth_user))
    with client:
        client.get("/")
        response = client.get(
            f"{url_for('inv.inventory_user', username=oth_user.name)}", follow_redirects=True)
        assert session.get("admin")
    assert len(response.history) == 0
    assert response.status_code == 200
    assert b"You have to be an admin..." not in response.data
    assert b'type="submit" value="Log In"' not in response.data
    assert b'Inventory check' in response.data
    assert f'<span class="text-secondary">{oth_user.name}</span>' in response.text

    # check if a random product and critical product from this user is on the page
    with dbSession() as db_session:
        product =  db_session.scalar(
            select(Product)\
            .filter_by(responsable_id=oth_user.id, in_use=True))
        product_crit =  db_session.scalar(
            select(Product)\
            .filter_by(responsable_id=oth_user.id, in_use=True, critical=True))
    assert f"{product.name}" in response.text
    assert f"{product.description}" in response.text
    assert f"{product.min_stock} {product.meas_unit}" in response.text

    # red color of a critical product
    assert f"{product_crit.name}" in response.text
    assert f"{product_crit.description}" in response.text
    assert ('<td class="text-danger">' +
            f"{product_crit.min_stock} {product_crit.meas_unit}") in response.text

    # disabled and checked tags for a to_order product
    with dbSession() as db_session:
        db_session.get(Product, product.id).to_order = True
        db_session.commit()
        response = client.get(f"/{oth_user.name}_inventory")
        assert (f"id={product.id}" +
                f" name={product.id}" +
                " disabled checked") in response.text
        db_session.get(Product, product.id).to_order = False
        db_session.commit()


@pytest.mark.parametrize(
    ("oth_user", "flash_message"), (
    ("nonexistent", "User nonexistent does not exist!"),
    ("user5", "User user5 awaits registration aproval!"),
    ("user6", "User user6 is not in use anymore!")
))
def test_oth_user_admin_logged_in_special_users(
        client: FlaskClient,
        admin_logged_in,
        oth_user,
        flash_message):
    """Fail to access the inventory of other users , logged in as admin"""
    with dbSession() as db_session:
        db_session.get(User, 5).reg_req = True
        db_session.commit()
    with client:
        client.get("/")
        assert session.get("admin")
        response = client.get(
            f"{url_for('inv.inventory_user', username=oth_user)}", follow_redirects=True)
    assert len(response.history) == 1
    assert response.history[0].status_code == 302
    assert response.status_code == 200
    assert response.request.path == "/"
    assert flash_message in response.text
    assert b"Admin dashboard" in response.data


def test_oth_user_admin_logged_in_yes_check_inventory(client: FlaskClient, admin_logged_in):
    """Access the inventory page of other user, trigger for inventory check.."""
    with dbSession() as db_session:
        oth_user = db_session.get(User, 4)
    assert oth_user.done_inv

    # before triggering inventory check
    with client:
        client.get("/")
        assert session.get("admin")
        response = client.get(
            f"{url_for('inv.inventory_user', username=oth_user.name)}")
    assert b"Inventory check" in response.data
    assert f'<span class="text-secondary">{oth_user.name}</span>' in response.text
    assert b"checked" not in response.data
    assert b"disabled" in response.data
    assert b"Inventory check not required" in response.data
    assert b'input class="btn btn-primary" type="submit" value="Inventory check not required" disabled' in response.data
    assert b'input class="btn btn-primary" type="submit" value="Submit inventory"' not in response.data
    assert b"Critical products are highlighted in red" not in response.data
    
    # trigger inventory check
    with dbSession() as db_session:
        db_session.get(User, oth_user.id).done_inv = False
        db_session.commit()
        product =  db_session.scalar(
            select(Product).
            filter_by(responsable_id=oth_user.id, in_use=True))
    with client:
        client.get("/")
        response = client.get(
            f"{url_for('inv.inventory_user', username=oth_user.name)}")
    assert b"Inventory check" in response.data
    assert f'<span class="text-secondary">{oth_user.name}</span>' in response.text
    assert b"checked" not in response.data
    assert b"disabled" not in response.data
    assert b"Inventory check not required" not in response.data
    assert b'input class="btn btn-primary" type="submit" value="Inventory check not required" disabled' not in response.data
    assert b'input class="btn btn-primary" type="submit" value="Submit inventory"' in response.data
    assert b"Critical products are highlighted in red" in response.data
    assert f"{product.name}" in response.text
    assert f"{product.description}" in response.text
    assert f"{product.min_stock} {product.meas_unit}" in response.text

    # teardown
    with dbSession() as db_session:
        db_session.get(User, oth_user.id).done_inv = True
        db_session.commit()


def test_oth_user_send_inventory_yes_check_inventory(client: FlaskClient, admin_logged_in):
    """Send inventory for other user, trigger for inventory check."""
    with dbSession() as db_session:
        db_session.get(User, 4).done_inv = False
        db_session.commit()
        oth_user = db_session.get(User, 4)
    with client:
        client.get("/")
        assert session.get("admin")
        response = client.get(
            f"{url_for('inv.inventory_user', username=oth_user.name)}")
    assert b"Inventory check not required" not in response.data
    assert b'Inventory check' in response.data
    assert f'<span class="text-secondary">{oth_user.name}</span>' in response.text
    assert b'input class="btn btn-primary" type="submit" value="Submit inventory"' in response.data

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
            data=data, follow_redirects=True)
    assert len(response.history) == 1
    assert response.history[0].status_code == 302
    assert response.status_code == 200
    assert response.request.path == "/"
    assert b"Inventory has been submitted" in response.data

    # check to_order status in database and teardown
    with dbSession() as db_session:
            assert db_session.get(Product, 20).to_order
            assert not db_session.get(Product, 22).to_order
            assert db_session.get(Product, 34).to_order
            assert db_session.get(User, oth_user.id).done_inv
            db_session.get(Product, 20).to_order = False
            db_session.get(Product, 34).to_order = False
            db_session.commit()

def test_oth_user_send_inventory_yes_check_inventory_no_csrf(client: FlaskClient, admin_logged_in):
    """Try to send inventory for other user without csrf token, trigger for inventory check."""
    with dbSession() as db_session:
        db_session.get(User, 4).done_inv = False
        db_session.commit()
        oth_user = db_session.get(User, 4)
    with client:
        client.get("/")
        assert session.get("admin")
        response = client.get(
            f"{url_for('inv.inventory_user', username=oth_user.name)}")
    assert b"Inventory check not required" not in response.data
    assert b'Inventory check' in response.data
    assert f'<span class="text-secondary">{oth_user.name}</span>' in response.text
    assert b'input class="btn btn-primary" type="submit" value="Submit inventory"' in response.data

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
    assert b"The CSRF token is missing." in response.data

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
    assert response.request.path == "/auth/login"
    assert b"You have to be logged in..." in response.data
    assert b'type="submit" value="Log In"' in response.data


def test_inventory_request_admin_logged_in(client: FlaskClient, admin_logged_in):
    """Try to request inventory with admin."""
    with client:
        client.get("/")
        assert session.get("admin")
        response = client.get(
            f"{url_for('inv.inventory_request')}", follow_redirects=True)
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == "/"
        assert b"You are an admin! You don&#39;t need to request inventory checks" in response.data
        assert b"check inventory" not in response.data
        with dbSession() as db_session:
            assert not db_session.get(User, session.get("user_id")).req_inv

def test_inventory_request_user_logged_in(client: FlaskClient, user_logged_in):
    """Request inventory with user."""
    with client:
        client.get("/")
        assert session.get("user_name")
        assert not session.get("admin")
        response = client.get(
            f"{url_for('inv.inventory_request')}", follow_redirects=True)
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == "/"
        assert b"Inventory check request sent" in response.data
        assert b"You requested a inventory check" in response.data
        with dbSession() as db_session:
            assert db_session.get(User, session.get("user_id")).req_inv
            db_session.get(User, session.get("user_id")).req_inv = False
            db_session.commit()


def test_inventory_request_user_logged_in_yes_check_inventory(client: FlaskClient, user_logged_in):
    """Request inventory with user, trigger for inventory check."""
    with client:
        # set check inventory
        client.get("/")
        assert session.get("user_name")
        with dbSession() as db_session:
            db_session.get(User, session.get("user_id")).done_inv = False
            db_session.commit()
        response = client.get(
            f"{url_for('inv.inventory_request')}", follow_redirects=True)
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for('inv.inventory')
        assert b"You allready can check the inventory!" in response.data
        assert b"Critical products are highlighted in red" in response.data
        with dbSession() as db_session:
            assert not db_session.get(User, session.get("user_id")).req_inv
            db_session.get(User, session.get("user_id")).done_inv = True
            db_session.commit()
# endregion
