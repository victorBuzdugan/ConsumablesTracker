"""Users blueprint tests."""

from html import unescape

import pytest
from flask import g, session, url_for
from flask.testing import FlaskClient
from sqlalchemy import select
from werkzeug.security import check_password_hash

from blueprints.auth.auth import msg, PASSW_SYMB
from database import User, dbSession
from tests import (admin_logged_in, client, create_test_categories,
                   create_test_db, create_test_products, create_test_suppliers,
                   create_test_users, user_logged_in)

pytestmark = pytest.mark.users

def test_approve_registration(client: FlaskClient, admin_logged_in):
    with client:
        response = client.get("/")
        assert session.get("admin")
        assert b"requested registration" in response.data
        response = client.get(url_for("users.approve_reg", username="user5"), follow_redirects=True)
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("main.index")
        assert b"user5 has been approved" in response.data
        with dbSession() as db_session:
            assert not db_session.get(User, 5).reg_req
            db_session.get(User, 5).reg_req = True
            db_session.commit()


def test_failed_approve_registration_bad_username(client: FlaskClient, admin_logged_in):
    with client:
        response = client.get("/")
        assert session.get("admin")
        assert b"requested registration" in response.data
        response = client.get(url_for("users.approve_reg", username="not_existing_user"), follow_redirects=True)
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("main.index")
        assert b"not_existing_user does not exist!" in response.data


def test_failed_approve_registration_user_logged_in(client: FlaskClient, user_logged_in):
    with client:
        response = client.get("/")
        assert not session.get("admin")
        assert b"requested registration" not in response.data
        response = client.get(url_for("users.approve_reg", username="user5"), follow_redirects=True)
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("auth.login")
        assert b"You have to be an admin..." in response.data
        assert session.get("user_id")
        with dbSession() as db_session:
            assert db_session.get(User, 5).reg_req


def test_approve_check_inventory(client: FlaskClient, admin_logged_in):
    with dbSession() as db_session:
        user = db_session.get(User, 4)
        user.req_inv = True
        db_session.commit()
        with client:
            response = client.get("/")
            assert session.get("admin")
            assert b"requested inventory" in response.data
            response = client.get(url_for("users.approve_check_inv", username=user.name), follow_redirects=True)
            assert len(response.history) == 1
            assert response.history[0].status_code == 302
            assert response.status_code == 200
            assert response.request.path == url_for("main.index")
            assert b"requested inventory" not in response.data
            assert b"check inventory" in response.data
        db_session.refresh(user)
        assert not user.done_inv
        assert not user.req_inv
        user.done_inv = True
        db_session.commit()


@pytest.mark.parametrize(("id", "username", "flash_message"), (
    ("6", "user6", "'Retired' user can't check inventory"),
    ("5", "user5", "User with pending registration can't check inventory"),
    ("7", "user7", "User without products attached can't check inventory"),
    # id 7 because id 8 doesn't exist
    ("7", "user8", "user8 does not exist!"),
))
def test_failed_approve_check_inventory(client: FlaskClient, admin_logged_in, id, username, flash_message):
    with client:
        response = client.get("/")
        assert session.get("admin")
        response = client.get(url_for("users.approve_check_inv", username=username), follow_redirects=True)
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("main.index")
        assert flash_message in unescape(response.text)
        with dbSession() as db_session:
            assert db_session.get(User, id).done_inv


def test_failed_approve_check_inventory_user_logged_in(client: FlaskClient, user_logged_in):
    with dbSession() as db_session:
        user = db_session.get(User, 4)
        user.req_inv = True
        db_session.commit()
        with client:
            response = client.get("/")
            assert not session.get("admin")
            assert b"requested inventory" not in response.data
            response = client.get(url_for("users.approve_check_inv", username=user.name), follow_redirects=True)
            assert len(response.history) == 1
            assert response.history[0].status_code == 302
            assert response.status_code == 200
            assert response.request.path == url_for("auth.login")
            assert b"You have to be an admin..." in response.data
            assert session.get("user_id")
        db_session.refresh(user)
        assert user.done_inv
        assert user.req_inv


def test_approve_all_check_inventory(client: FlaskClient, admin_logged_in):
    with dbSession() as db_session:
        user = db_session.get(User, 4)
        user.req_inv = True
        db_session.commit()
        with client:
            response = client.get("/")
            assert session.get("admin")
            assert b"requested inventory" in response.data
            response = client.get(url_for("users.approve_check_inv_all"), follow_redirects=True)
            assert len(response.history) == 1
            assert response.history[0].status_code == 302
            assert response.status_code == 200
            assert response.request.path == url_for("main.index")
            assert b"requested inventory" not in response.data
            assert b"check inventory" in response.data
        assert not db_session.get(User, 1).done_inv
        assert not db_session.get(User, 2).done_inv
        assert not db_session.get(User, 3).done_inv
        db_session.refresh(user)
        assert not user.done_inv
        assert not user.req_inv
        db_session.get(User, 1).done_inv = True
        db_session.get(User, 2).done_inv = True
        db_session.get(User, 3).done_inv = True
        user.done_inv = True
        db_session.commit()


@pytest.mark.parametrize(("details", "admin"), (
    ("", ""),
    ("some details", ""),
    ("", "on"),
    ("some details", "on"),
))
def test_new_user(client: FlaskClient, admin_logged_in, details, admin):
    name = "new_user"
    password = "Q!111111"
    with client:
        client.get("/")
        response = client.get(url_for("users.new_user"))
        assert b"Create user" in response.data
        data = {
            "csrf_token": g.csrf_token,
            "name": name,
            "password": password,
            "details": details,
            "admin": admin,
            }
        response = client.post(
            url_for("users.new_user"), data=data, follow_redirects=True)
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("main.index")
        assert "User 'new_user' created" in unescape(response.text)
        assert name in response.text
    with dbSession() as db_session:
        user = db_session.scalar(select(User).filter_by(name=name))
        assert check_password_hash(user.password, password)
        assert user.admin == bool(admin)
        assert user.in_use
        assert user.done_inv
        assert not user.reg_req
        assert not user.req_inv
        assert user.details == details
        db_session.delete(user)
        db_session.commit()


@pytest.mark.parametrize(("name", "password", "flash_message"), (
    ("", "Q!111111", msg["usr_req"]),
    ("us", "Q!111111", msg["usr_len"]),
    ("useruseruseruser", "Q!111111", msg["usr_len"]),
    ("new_user", "", msg["psw_req"]),
    ("new_user", "Q!1", msg["psw_len"]),
    ("new_user", "aaaaaaaa", f"Password must have 1 big letter, 1 number, 1 special char ({PASSW_SYMB})!"),
    ("new_user", "#1aaaaaa", f"Password must have 1 big letter, 1 number, 1 special char ({PASSW_SYMB})!"),
    ("new_user", "#Aaaaaaa", f"Password must have 1 big letter, 1 number, 1 special char ({PASSW_SYMB})!"),
    ("new_user", "1Aaaaaaa", f"Password must have 1 big letter, 1 number, 1 special char ({PASSW_SYMB})!"),
    ("user1", "Q!111111", "User user1 allready exists"),
))
def test_failed_new_user(client: FlaskClient, admin_logged_in, name, password, flash_message):
    with client:
        client.get("/")
        response = client.get(url_for("users.new_user"))
        assert b"Create user" in response.data
        data = {
            "csrf_token": g.csrf_token,
            "name": name,
            "password": password,
            }
        response = client.post(
            url_for("users.new_user"), data=data, follow_redirects=True)
        assert len(response.history) == 0
        assert response.status_code == 200
        assert b"Create user" in response.data
        assert flash_message in unescape(response.text)
        assert f"User '{name}' created" not in unescape(response.text)
    with dbSession() as db_session:
        if name != "user1":
            assert not db_session.scalar(select(User).filter_by(name=name))



