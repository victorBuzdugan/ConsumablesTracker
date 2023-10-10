"""Users blueprint tests."""

from html import unescape

import pytest
from flask import g, session, url_for
from flask.testing import FlaskClient
from sqlalchemy import select
from werkzeug.security import check_password_hash

from blueprints.auth.auth import PASSW_SYMB, msg
from database import User, dbSession
from tests import (admin_logged_in, client, create_test_categories,
                   create_test_db, create_test_group_schedule,
                   create_test_products, create_test_suppliers,
                   create_test_users, user_logged_in)

pytestmark = pytest.mark.users


# region: approve registration
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
        assert b"Review the working schedule" in response.data
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
# endregion


# region: approve check inventory
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
# endregion


# region: new user
@pytest.mark.parametrize(("details", "admin", "email", "sat_group"), (
    ("", "", "", "1"),
    ("some details", "", "", "2"),
    ("", "on", "", "1"),
    ("some details", "on", "", "2"),
    ("some details", "on", "some.user@somewebsite.com", "1"),
))
def test_new_user(client: FlaskClient, admin_logged_in, details, admin, email, sat_group):
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
            "email": email,
            "sat_group": sat_group,
            }
        response = client.post(
            url_for("users.new_user"), data=data, follow_redirects=True)
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("main.index")
        assert "User 'new_user' created" in unescape(response.text)
        assert b"Review the working schedule" in response.data
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
        assert user.email == email
        assert user.sat_group == int(sat_group)
        db_session.delete(user)
        db_session.commit()


@pytest.mark.parametrize(("name", "password", "email", "sat_group", "flash_message"), (
    ("", "Q!111111", "", "1", msg["usr_req"]),
    ("us", "Q!111111", "", "1", msg["usr_len"]),
    ("useruseruseruser", "Q!111111", "", "1", msg["usr_len"]),
    ("new_user", "", "", "1", msg["psw_req"]),
    ("new_user", "Q!1", "", "1", msg["psw_len"]),
    ("new_user", "aaaaaaaa", "", "1", f"Password must have 1 big letter, 1 number, 1 special char ({PASSW_SYMB})!"),
    ("new_user", "#1aaaaaa", "", "1", f"Password must have 1 big letter, 1 number, 1 special char ({PASSW_SYMB})!"),
    ("new_user", "#Aaaaaaa", "", "1", f"Password must have 1 big letter, 1 number, 1 special char ({PASSW_SYMB})!"),
    ("new_user", "1Aaaaaaa", "", "1", f"Password must have 1 big letter, 1 number, 1 special char ({PASSW_SYMB})!"),
    ("user1", "Q!111111", "", "1", "The user user1 allready exists"),
    ("Admin", "Q!111111", "", "1", "The user Admin allready exists"),
    ("new_user", "Q!111111", "1", "plainaddress", "Invalid email adress"),
    ("new_user", "Q!111111", "1", "#@%^%#$@#$@#.com", "Invalid email adress"),
    ("new_user", "Q!111111", "1", "@example.com", "Invalid email adress"),
    ("new_user", "Q!111111", "1", "Joe Smith <email@example.com>", "Invalid email adress"),
    ("new_user", "Q!111111", "1", "email@example@example.com", "Invalid email adress"),
    ("new_user", "Q!111111", "1", "email@-example.com", "Invalid email adress"),
    ("new_user", "Q!111111", "3", "email@example.com", "Invalid Choice: could not coerce"),
    ("new_user", "Q!111111", "", "email@example.com", "Invalid Choice: could not coerce"),
    ("new_user", "Q!111111", "a", "email@example.com", "Invalid Choice: could not coerce"),
))
def test_failed_new_user(client: FlaskClient, admin_logged_in, name, password, email, sat_group, flash_message):
    with client:
        client.get("/")
        response = client.get(url_for("users.new_user"))
        assert b"Create user" in response.data
        data = {
            "csrf_token": g.csrf_token,
            "name": name,
            "password": password,
            "email": email,
            "sat_group": sat_group,
            }
        response = client.post(
            url_for("users.new_user"), data=data, follow_redirects=True)
        assert len(response.history) == 0
        assert response.status_code == 200
        assert b"Create user" in response.data
        assert flash_message in unescape(response.text)
        assert f"User '{name}' created" not in unescape(response.text)
    if (name != "user1") and (name != "Admin"):
        with dbSession() as db_session:
            assert not db_session.scalar(select(User).filter_by(name=name))
# endregion


# region: edit user
@pytest.mark.parametrize(("id", "new_name", "orig_password", "new_password", "new_details", "new_check_inv", "new_admin", "new_in_use", "new_email", "new_sat_group"), (
    # 1 element
    ("4", "test_user", "Q!444444", "", "", "", "", "on", "validemail@gmail.com", "1"),
    ("4", "user4", "Q!444444", "Q!111111", "", "", "", "on", "", "1"),
    ("4", "user4", "Q!444444", "", "Some detail", "", "", "on", "", "2"),
    ("4", "user4", "Q!444444", "", "", "on", "", "on", "validemail@gmail.com", "1"),
    ("4", "user4", "Q!444444", "", "", "", "on", "on", "", "1"),
    ("5", "user5", "Q!555555", "", "", "", "", "", "", "1"),
    # 2 elements
    ("3", "test_user", "Q!333333", "Q!111111", "", "", "", "on", "", "1"),
    ("3", "test_user", "Q!333333", "", "Some detail", "", "", "on", "validemail@gmail.com", "1"),
    ("3", "test_user", "Q!333333", "", "", "on", "", "on", "", "2"),
    ("3", "test_user", "Q!333333", "", "", "", "on", "on", "", "1"),
    ("6", "test_user", "Q!666666", "", "", "", "", "on", "", "1"),
    ("2", "user2", "Q!222222", "Q!111111", "Some detail", "", "on", "on", "", "1"),
    ("2", "user2", "Q!222222", "Q!111111", "", "on", "on", "on", "", "1"),
    ("2", "user2", "Q!222222", "Q!111111", "", "", "", "on", "validemail@gmail.com", "2"),
    ("7", "user7", "Q!777777", "Q!111111", "", "", "", "", "", "1"),
    ("1", "user1", "Q!111111", "", "Some detail", "on", "on", "on", "", "1"),
    ("2", "user2", "Q!222222", "", "Some detail", "", "", "on", "", "1"),
    ("5", "user5", "Q!555555", "", "Some detail", "", "", "", "", "1"),
    ("2", "user2", "Q!222222", "", "", "on", "", "on", "", "1"),
    ("6", "user6", "Q!666666", "", "", "", "on", "on", "validemail@gmail.com", "2"),
    # 3 elements
    ("1", "test_user", "Q!111111", "Q!222222", "Some detail", "", "on", "on", "", "1"),
    ("1", "test_user", "Q!111111", "Q!222222", "", "on", "on", "on", "", "1"),
    ("2", "test_user", "Q!222222", "Q!111111", "", "", "", "on", "", "1"),
    ("7", "test_user", "Q!777777", "Q!111111", "", "", "", "", "", "2"),
    ("3", "test_user", "Q!333333", "", "Some detail", "on", "", "on", "validemail@gmail.com", "1"),
    ("3", "test_user", "Q!333333", "", "Some detail", "", "on", "on", "", "1"),
    ("5", "test_user", "Q!555555", "", "Some detail", "", "", "", "", "1"),
    ("3", "test_user", "Q!333333", "", "", "on", "on", "on", "", "1"),
    ("6", "test_user", "Q!666666", "", "", "", "on", "on", "", "2"),
    ("4", "user4", "Q!444444", "Q!111111", "Some detail", "on", "", "on", "", "1"),
    ("4", "user4", "Q!444444", "Q!111111", "Some detail", "", "on", "on", "", "1"),
    ("5", "user5", "Q!555555", "Q!111111", "Some detail", "", "", "", "validemail@gmail.com", "1"),
    ("4", "user4", "Q!444444", "", "Some detail", "on", "on", "on", "", "1"),
    ("7", "user7", "Q!777777", "", "Some detail", "", "on", "", "", "1"),
    # 4 elements
    ("1", "test_user", "Q!111111", "Q!222222", "Some detail", "on", "on", "on", "", "1"),
    ("2", "test_user", "Q!222222", "Q!111111", "Some detail", "", "", "on", "", "2"),
    ("6", "test_user", "Q!666666", "Q!111111", "Some detail", "", "", "on", "", "1"),
    ("2", "user2", "Q!222222", "Q!111111", "Some detail", "on", "", "on", "", "1"),
    ("7", "user7", "Q!777777", "Q!111111", "Some detail", "", "on", "", "validemail@gmail.com", "1"),
    # 5 elements
    ("2", "test_user", "Q!222222", "Q!111111", "Some detail", "on", "", "on", "", "2"),
    ("4", "test_user", "Q!444444", "Q!111111", "Some detail", "on", "on", "on", "", "1"),
    ("7", "test_user", "Q!777777", "Q!111111", "Some detail", "", "on", "", "validemail@gmail.com", "1"),
    ("6", "test_user", "Q!666666", "Q!111111", "Some detail", "", "on", "on", "", "1"),
))
def test_edit_user(client: FlaskClient, admin_logged_in,
        id, new_name, orig_password, new_password, new_details, new_check_inv, new_admin, new_in_use, new_email, new_sat_group):
    with dbSession() as db_session:
        user = db_session.get(User, id)
        orig_in_use = user.in_use
        orig_name = user.name
        orig_details = user.details
        orig_email = user.email
        orig_done_inv = user.done_inv
        orig_admin = user.admin
        orig_reg_req = user.reg_req
        orig_sat_group = user.sat_group
        with client:
            client.get("/")
            response = client.get(url_for("users.edit_user", username=user.name))
            assert len(response.history) == 0
            assert response.status_code == 200
            assert orig_name in response.text
            data = {
                "csrf_token": g.csrf_token,
                "name": new_name,
                "password": new_password,
                "details": new_details,
                "email": new_email,
                "check_inv": new_check_inv,
                "admin": new_admin,
                "in_use": new_in_use,
                "sat_group": new_sat_group,
                "submit": True,
            }
            response = client.post(url_for("users.edit_user", username=orig_name),
                                   data=data, follow_redirects=True)
            assert len(response.history) == 1
            assert response.history[0].status_code == 302
            assert response.status_code == 200
            assert response.request.path == url_for("users.edit_user", username=new_name)
            assert b"User updated" in response.data
            assert bytes(new_name, "UTF-8") in response.data
            assert bytes(new_details, "UTF-8") in response.data
        
        db_session.refresh(user)
        assert user.name == new_name
        if new_password:
            assert check_password_hash(user.password, new_password)
        assert user.details == new_details
        assert user.done_inv != bool(new_check_inv)
        assert user.admin == bool(new_admin)
        assert user.in_use == bool(new_in_use)
        assert user.email == new_email
        assert user.sat_group == int(new_sat_group)
        # teardown
        user.in_use = orig_in_use
        db_session.commit()
        db_session.refresh(user)
        user.name = orig_name
        user.password = orig_password
        user.details = orig_details
        user.email = orig_email
        user.done_inv = orig_done_inv
        user.admin = orig_admin
        user.sat_group = orig_sat_group
        db_session.commit()
        db_session.refresh(user)
        user.reg_req = orig_reg_req
        db_session.commit()


@pytest.mark.parametrize(("id", "new_name", "new_password", "new_check_inv", "new_admin", "new_email", "new_sat_group", "flash_message"), (
    ("4", "", "", "", "", "", "1", msg["usr_req"]),
    ("3", "us", "", "", "", "", "1", msg["usr_len"]),
    ("2", "useruseruseruser", "", "", "on", "", "1", msg["usr_len"]),
    ("2", "new_user", "Q!1", "", "on", "", "1", msg["psw_len"]),
    ("3", "new_user", "aaaaaaaa", "", "", "", "1", f"Password must have 1 big letter, 1 number, 1 special char ({PASSW_SYMB})!"),
    ("4", "new_user", "#1aaaaaa", "", "", "", "1", f"Password must have 1 big letter, 1 number, 1 special char ({PASSW_SYMB})!"),
    ("3", "new_user", "#Aaaaaaa", "", "", "", "1", f"Password must have 1 big letter, 1 number, 1 special char ({PASSW_SYMB})!"),
    ("1", "new_user", "1Aaaaaaa", "", "on", "", "1", f"Password must have 1 big letter, 1 number, 1 special char ({PASSW_SYMB})!"),
    ("1", "new_user", "Q!111112", "", "on", "plainaddress", "1", "Invalid email adress"),
    ("2", "new_user", "Q!111112", "", "on", "#@%^%#$@#$@#.com", "1", "Invalid email adress"),
    ("3", "new_user", "Q!111112", "", "", "@example.com", "1", "Invalid email adress"),
    ("4", "new_user", "Q!111112", "", "", "Joe Smith <email@example.com>", "1", "Invalid email adress"),
    ("1", "new_user", "Q!111112", "", "on", "email@example@example.com", "1", "Invalid email adress"),
    ("3", "new_user", "Q!111112", "", "", "email@-example.com", "1", "Invalid email adress"),
    ("2", "new_user", "Q!111112", "", "on", "email@-example.com", "", "Invalid Choice: could not coerce"),
    ("4", "new_user", "Q!111112", "", "", "email@-example.com", "3", "Not a valid choice"),
    ("1", "new_user", "Q!111112", "", "on", "email@-example.com", "a", "Invalid Choice: could not coerce"),
))
def test_failed_edit_user_form_validators(client: FlaskClient, admin_logged_in,
        id, new_name, new_password, new_check_inv, new_admin, new_email, new_sat_group, flash_message):
    with dbSession() as db_session:
        user = db_session.get(User, id)
        orig_name = user.name
        orig_done_inv = user.done_inv
        orig_admin = user.admin
        orig_in_use = user.in_use
        orig_sat_group = user.sat_group
        with client:
            client.get("/")
            response = client.get(url_for("users.edit_user", username=orig_name))
            assert bytes(user.name, "UTF-8") in response.data
            data = {
                "csrf_token": g.csrf_token,
                "name": new_name,
                "password": new_password,
                "details": "",
                "email": new_email,
                "check_inv": new_check_inv,
                "admin": new_admin,
                "in_use": "on",
                "sat_group": new_sat_group,
                "submit": True,
            }
            response = client.post(url_for("users.edit_user", username=orig_name),
                                   data=data, follow_redirects=True)
            assert len(response.history) == 0
            assert response.status_code == 200
            assert b"User updated" not in response.data
            assert bytes(orig_name, "UTF-8") in response.data
            assert flash_message in unescape(response.text)
        db_session.refresh(user)
        assert user.name != new_name
        assert not check_password_hash(user.password, new_password)
        assert user.done_inv == orig_done_inv
        assert user.admin == orig_admin
        assert user.in_use == orig_in_use
        assert user.sat_group == orig_sat_group


def test_failed_edit_user_name_duplicate(client: FlaskClient, admin_logged_in):
    with dbSession() as db_session:
        user = db_session.get(User, 2)
        orig_name = user.name
        new_name = db_session.get(User, 0).name
        with client:
            client.get("/")
            response = client.get(url_for("users.edit_user", username=orig_name))
            assert bytes(user.name, "UTF-8") in response.data
            data = {
                "csrf_token": g.csrf_token,
                "name": new_name,
                "password": "",
                "details": "",
                "admin": "on",
                "in_use": "on",
                "sat_group": "2",
                "submit": True,
            }
            response = client.post(url_for("users.edit_user", username=orig_name),
                                   data=data, follow_redirects=True)
            assert len(response.history) == 1
            assert response.history[0].status_code == 302
            assert response.status_code == 200
            assert response.request.path == url_for("users.edit_user", username=orig_name)
            assert b"User updated" not in response.data
            assert bytes(orig_name, "UTF-8") in response.data
            assert f"The user {new_name} allready exists" in response.text
        db_session.refresh(user)
        assert user.name != new_name


@pytest.mark.parametrize(("id", "new_check_inv", "new_admin", "new_in_use", "flash_message"), (
    ("7", "on", "", "on", "User without products attached can't check inventory"),
    ("6", "on", "", "", "'Retired' user can't check inventory"),
    ("5", "on", "", "on", "User with pending registration can't check inventory"),
    ("5", "", "on", "on", "User with pending registration can't be admin"),
    ("3", "", "", "", "Can't 'retire' a user if he is still responsible for products"),
))
def test_failed_edit_user_db_validators(client: FlaskClient, admin_logged_in,
        id, new_check_inv, new_admin, new_in_use, flash_message):
    with dbSession() as db_session:
        user = db_session.get(User, id)
        orig_done_inv = user.done_inv
        orig_admin = user.admin
        orig_in_use = user.in_use
        with client:
            client.get("/")
            response = client.get(url_for("users.edit_user", username=user.name))
            assert bytes(user.name, "UTF-8") in response.data
            data = {
                "csrf_token": g.csrf_token,
                "name": user.name,
                "password": "",
                "details": "",
                "email": "",
                "check_inv": new_check_inv,
                "admin": new_admin,
                "in_use": new_in_use,
                "submit": True,
            }
            response = client.post(url_for("users.edit_user", username=user.name),
                                   data=data, follow_redirects=True)
            assert len(response.history) == 1
            assert response.history[0].status_code == 302
            assert response.status_code == 200
            assert response.request.path == url_for("users.edit_user", username=user.name)
            assert b"User updated" not in response.data
            assert bytes(user.name, "UTF-8") in response.data
            assert flash_message in unescape(response.text)
        db_session.refresh(user)
        assert user.done_inv == orig_done_inv
        assert user.admin == orig_admin
        assert user.in_use == orig_in_use


def test_failed_edit_user_bad_username(client: FlaskClient, admin_logged_in):
    USERNAME = "not_existing_user"
    with client:
        client.get("/")
        response = client.get(url_for("users.edit_user", username=USERNAME), follow_redirects=True)
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("main.index")
        assert f"{USERNAME} does not exist!" in response.text


def test_failed_edit_user_hidden_admin_bad_username(client: FlaskClient, admin_logged_in):
    USERNAME = "Admin"
    with client:
        client.get("/")
        response = client.get(url_for("users.edit_user", username=USERNAME), follow_redirects=True)
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("main.index")
        assert f"{USERNAME} does not exist!" in response.text


def test_edit_user_last_admin(client: FlaskClient, admin_logged_in):
    with dbSession() as db_session:
        db_session.get(User, 2).admin = False
        db_session.commit()
    with client:
        client.get("/")
        username = session.get("user_name")
        response = client.get(url_for("users.edit_user", username=username))
        data = {
                "csrf_token": g.csrf_token,
                "name": username,
                "details": "",
                "admin": "",
                "in_use": "on",
                "submit": True,
            }
        response = client.post(url_for("users.edit_user", username=username),
                               data=data, follow_redirects=True)
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("users.edit_user", username=username)
        assert b"User updated" not in response.data
        assert bytes(username, "UTF-8") in response.data
        assert b"You are the last admin!" in response.data
    with dbSession() as db_session:
        assert db_session.get(User, 1).admin
        db_session.get(User, 2).admin = True
        db_session.commit()


def test_edit_user_change_admin_name(client: FlaskClient, admin_logged_in):
    with client:
        client.get("/")
        old_name = session.get("user_name")
        new_name = "new_name"
        client.get(url_for("users.edit_user", username=old_name))
        data = {
                "csrf_token": g.csrf_token,
                "name": new_name,
                "details": "",
                "admin": "on",
                "in_use": "on",
                "submit": True,
            }
        response = client.post(url_for("users.edit_user", username=old_name),
                               data=data, follow_redirects=True)
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("users.edit_user", username=new_name)
        assert b"User updated" in response.data
        assert bytes(new_name, "UTF-8") in response.data
        assert session.get("user_name") == new_name
        data = {
                "csrf_token": g.csrf_token,
                "name": old_name,
                "details": "",
                "admin": "on",
                "in_use": "on",
                "submit": True,
            }
        response = client.post(url_for("users.edit_user", username=new_name),
                               data=data, follow_redirects=True)
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("users.edit_user", username=old_name)
        assert b"User updated" in response.data
        assert bytes(old_name, "UTF-8") in response.data
        assert session.get("user_name") == old_name


def test_edit_user_change_admin_logged_in_admin_status(client: FlaskClient, admin_logged_in):
    with client:
        client.get("/")
        username = session.get("user_name")
        client.get(url_for("users.edit_user", username=username))
        data = {
                "csrf_token": g.csrf_token,
                "name": username,
                "details": "",
                "admin": "",
                "in_use": "on",
                "submit": True,
            }
        response = client.post(url_for("users.edit_user", username=username),
                               data=data, follow_redirects=True)
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("main.index")
        assert b"User updated" in response.data
        assert bytes(username, "UTF-8") in response.data
        assert b"Admin dashboard" not in response.data
        assert not session.get("admin")
    with dbSession() as db_session:
        assert not db_session.get(User, 1).admin
        db_session.get(User, 1).admin = True
        db_session.commit()
# endregion


# region: delete user
def test_delete_user(client: FlaskClient, admin_logged_in):
    with dbSession() as db_session:
        user = User("new_user", "Q!111111")
        db_session.add(user)
        db_session.commit()
        assert user.id
    with client:
        client.get("/")
        response = client.get(url_for("users.edit_user", username=user.name))
        assert bytes(user.name, "UTF-8") in response.data
        data = {
            "csrf_token": g.csrf_token,
            "name": user.name,
            "delete": True,
        }
        response = client.post(url_for("users.edit_user", username=user.name),
                            data=data, follow_redirects=True)
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("main.index")
        assert f"User '{user.name}' has been deleted" in unescape(response.text)
    with dbSession() as db_session:
        assert not db_session.get(User, user.id)


def test_delete_user_admin_log_out(client: FlaskClient):
    with dbSession() as db_session:
        user = User("new_user", "Q!111111", admin=True, reg_req=False)
        db_session.add(user)
        db_session.commit()
        assert user.id
    with client.session_transaction() as session:
        session["user_id"] = user.id
        session["admin"] = user.admin
        session["user_name"] = user.name
    with client:
        client.get("/")
        response = client.get(url_for("users.edit_user", username=user.name))
        assert bytes(user.name, "UTF-8") in response.data
        data = {
            "csrf_token": g.csrf_token,
            "name": user.name,
            "delete": True,
        }
        response = client.post(url_for("users.edit_user", username=user.name),
                            data=data, follow_redirects=True)
        assert len(response.history) == 2
        assert response.history[0].status_code == 302
        assert response.history[1].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("auth.login")
        assert b"Succesfully logged out..." in response.data


@pytest.mark.parametrize(("user_id", ), (
    ("1",),
    ("2",),
    ("3",),
    ("4",),
))
def test_failed_delete_user(client: FlaskClient, admin_logged_in, user_id):
    with dbSession() as db_session:
        user = db_session.get(User, user_id)
    with client:
        client.get("/")
        response = client.get(url_for("users.edit_user", username=user.name))
        assert bytes(user.name, "UTF-8") in response.data
        data = {
            "csrf_token": g.csrf_token,
            "name": user.name,
            "delete": True,
        }
        response = client.post(url_for("users.edit_user", username=user.name),
                            data=data, follow_redirects=True)
        assert len(response.history) == 0
        assert response.status_code == 200
        assert f"Can't delete user! He is still responsible for some products!" in unescape(response.text)
    with dbSession() as db_session:
        assert db_session.get(User, user.id)
# endregion
