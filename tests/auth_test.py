"""Authentification blueprint tests."""

from html import unescape
from os import getenv

import pytest
from flask import g, session, url_for
from flask.testing import FlaskClient
from sqlalchemy import select
from werkzeug.security import check_password_hash

from blueprints.auth.auth import (PASSW_MIN_LENGTH, USER_MAX_LENGTH,
                                  USER_MIN_LENGTH, msg)
from database import User, dbSession
from tests import (admin_logged_in, client, create_test_categories,
                   create_test_db, create_test_products, create_test_suppliers,
                   create_test_users, user_logged_in)

pytestmark = pytest.mark.auth


# region: registration page
def test_registration_landing_page(client: FlaskClient):
    with client:
        client.get("/")
        response = client.get(url_for("auth.register"))
        assert response.status_code == 200
        assert b'type="submit" value="Request registration"' in response.data


def test_clear_session_if_user_logged_in(client: FlaskClient, user_logged_in):
    with client:
        client.get("/")
        assert session.get("user_id")
        response = client.get(url_for("auth.register"))
        assert response.status_code == 200
        assert b'You have been logged out...' in response.data
        assert not session.get("user_id")


@pytest.mark.parametrize(("name", "password", "confirm", "email", "flash_message"), (
    ("", "a", "a", "", msg["usr_req"]),
    ("aa", "a", "a", "", msg["usr_len"]),
    ("aaaaaaaaaaaaaaaa", "a", "a", "", msg["usr_len"]),
    ("aaa", "", "a", "", msg["psw_req"]),
    ("aaa", "aaaaaaa", "a", "", msg["psw_len"]),
    ("aaa", "aaaaaaaa", "", "", msg["psw_req"]),
    ("aaa", "aaaaaaaa", "aaaaaaa", "", msg["psw_len"]),
    ("aaa", "aaaaaaaa", "aaaaaaab", "", msg["psw_eq"]),
    ("aaa", "aaaaaaaa", "aaaaaaaa", "", msg["psw_rules"]),
    ("aaa", "#1aaaaaa", "#1aaaaaa", "", msg["psw_rules"]),
    ("aaa", "#Aaaaaaa", "#Aaaaaaa", "", msg["psw_rules"]),
    ("aaa", "1Aaaaaaa", "1Aaaaaaa", "", msg["psw_rules"]),
    ("user5", "P@ssw0rd", "P@ssw0rd", "", f"The user user5 allready exists"),
    ("__testt_userr_", "P@ssw0rd", "P@ssw0rd", "plainaddress", "Invalid email adress"),
    ("__testt_userr_", "P@ssw0rd", "P@ssw0rd", "#@%^%#$@#$@#.com", "Invalid email adress"),
    ("__testt_userr_", "P@ssw0rd", "P@ssw0rd", "@example.com", "Invalid email adress"),
    ("__testt_userr_", "P@ssw0rd", "P@ssw0rd", "Joe Smith <email@example.com>", "Invalid email adress"),
    ("__testt_userr_", "P@ssw0rd", "P@ssw0rd", "email@example@example.com", "Invalid email adress"),
    ("__testt_userr_", "P@ssw0rd", "P@ssw0rd", "email@-example.com", "Invalid email adress"),
))
def test_failed_registration(
        client: FlaskClient,
        name, password, confirm, email, flash_message):
    with client:
        client.get("/")
        client.get(url_for("auth.register"))
        data = {
            "csrf_token": g.csrf_token,
            "name": name,
            "password": password,
            "confirm": confirm,
            "email": email}
        response = client.post("/auth/register", data=data)
    assert response.status_code == 200
    assert flash_message in unescape(response.text)


def test_successful_registration(client: FlaskClient):
    user = User(
        name="__testt_userr_",
        password="P@ssw0rd"
    )
    with client:
        client.get("/")
        client.get(url_for("auth.register"))
        data = {
            "csrf_token": g.csrf_token,
            "name": user.name,
            "password": user.password,
            "confirm": user.password}
        response = client.post(
            "/auth/register", data=data, follow_redirects=True)
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("auth.login")
        assert b"Registration request sent. Please contact an admin." \
            in response.data

    with dbSession() as db_session:
        test_user = db_session.scalar(
            select(User).filter_by(name=user.name))
        assert check_password_hash(test_user.password, user.password)
        assert test_user.reg_req

        db_session.delete(test_user)
        db_session.commit()

        test_user = db_session.scalar(
            select(User).filter_by(name=user.name))
        assert test_user is None
# endregion


# region: login and logout methods
def test_login_landing_page(client: FlaskClient):
    with client:
        client.get("/")
        response = client.get(url_for("auth.login"))
        assert response.status_code == 200
        assert b'type="submit" value="Log In"' in response.data
        client.get(url_for("set_language", language="ro"))
        response = client.get(url_for("auth.login"))
        assert b'Language changed' not in response.data
        assert b'Username' not in response.data
        assert b'Password' not in response.data
        assert u'Limba a fost schimbată' in response.text
        assert u'Nume' in response.text
        assert u'Parolă' in response.text
        client.get(url_for("set_language", language="en"))
        response = client.get(url_for("auth.login"))
        assert b'Language changed' in response.data
        assert b'Username' in response.data
        assert b'Password' in response.data
        assert u'Limba a fost schimbată' not in response.text
        assert u'Nume' not in response.text
        assert u'Parolă' not in response.text


@pytest.mark.parametrize(("name", "password", "flash_message"), (
    ("", "", msg["usr_req"]),
    ("a", "", msg["psw_req"]),
    ("a", "a", "Wrong username or password!"),
    ("a", "password", "Wrong username or password!"),
    ("user5", "a", "Wrong username or password!"),
    ("user6", "Q!666666", "This user is not in use anymore!"),
    ("user5", "Q!555555",
        "Your registration is pending. Contact an admin."),
))
def test_failed_login(
        client: FlaskClient, name, password, flash_message):
    with client:
        client.get("/")
        client.get(url_for("auth.login"))
        data = {
            "csrf_token": g.csrf_token,
            "name": name,
            "password": password}
        response = client.post("/auth/login", data=data)
    assert response.status_code == 200
    assert flash_message in response.text


def test_succesfull_login_and_logout(client: FlaskClient):
    with dbSession() as db_session:
        test_user = db_session.scalar(
                select(User).filter_by(name="user4"))
    with client:
        client.get("/")
        client.get(url_for("auth.login"))
        data = {
            "csrf_token": g.csrf_token,
            "name": test_user.name,
            "password": "Q!444444"}
        response = client.post("/auth/login", data=data, follow_redirects=True)
        assert session["user_id"] == test_user.id
        assert session["admin"] == test_user.admin
        assert session["user_name"] == test_user.name
        assert f"Welcome {test_user.name}" in response.text
    assert len(response.history) == 1
    assert response.history[0].status_code == 302
    assert response.status_code == 200
    assert response.request.path == "/"
    # logout
    with client:
        client.get("/")
        response = client.get(url_for("auth.logout"), follow_redirects=True)
        assert not session.get("user_id")
        assert not session.get("admin")
        assert not session.get("user_name")
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("auth.login")


def test_succesfull_hidden_admin_login_and_logout(client: FlaskClient):
    with dbSession() as db_session:
        test_user = db_session.scalar(
                select(User).filter_by(name="Admin"))
    with client:
        client.get("/")
        client.get(url_for("auth.login"))
        data = {
            "csrf_token": g.csrf_token,
            "name": test_user.name,
            "password": getenv('ADMIN_PASSW')}
        response = client.post("/auth/login", data=data, follow_redirects=True)
        assert session["user_id"] == test_user.id
        assert session["admin"] == test_user.admin
        assert session["user_name"] == test_user.name
        assert f"Welcome {test_user.name}" in response.text
    assert len(response.history) == 1
    assert response.history[0].status_code == 302
    assert response.status_code == 200
    assert response.request.path == "/"
    # logout
    with client:
        client.get("/")
        response = client.get(url_for("auth.logout"), follow_redirects=True)
        assert not session.get("user_id")
        assert not session.get("admin")
        assert not session.get("user_name")
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("auth.login")


def test_failed_login_no_csrf(client: FlaskClient):
    with client:
        data = {
                "name": "user4",
                "password": "P@ssw0rd"}
        response = client.post("/auth/login", data=data)
    assert response.status_code == 200
    assert b"The CSRF token is missing." in response.data


def test_failed_login_bad_csrf(client: FlaskClient):
    with client:
        data = {
            "csrf_token": "some_random_text",
            "name": "user4",
            "password": "P@ssw0rd"}
        response = client.post("/auth/login", data=data)
    assert response.status_code == 200
    assert b"The CSRF token is invalid." in response.data
# endregion


# region: change password
# also tests @login_required
def test_change_password_landing_page_if_not_logged_in(client: FlaskClient):
    with client:
        client.get("/")
        assert not session.get("user_id")
        assert not session.get("admin")
        assert not session.get("user_name")
        response = client.get(url_for("auth.change_password"), follow_redirects=True)
        assert not session.get("user_id")
        assert not session.get("admin")
        assert not session.get("user_name")
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("auth.login")
        assert b'type="submit" value="Log In"' in response.data
        assert b"You have to be logged in..." in response.data

# also tests @login_required
def test_change_password_landing_page_if_user_logged_in(
        client: FlaskClient, user_logged_in):
    with client:
        client.get("/")
        response = client.get(url_for("auth.change_password"))
        assert session.get("user_id")
        assert session.get("admin") is False
        assert session.get("user_name")
    assert response.status_code == 200
    assert b'type="submit" value="Change password"' in response.data


# also tests @login_required if admin
def test_change_password_landing_page_if_admin_logged_in(
        client: FlaskClient, admin_logged_in):
    with client:
        client.get("/")
        response = client.get(url_for("auth.change_password"))
        assert session.get("user_id")
        assert session.get("admin")
        assert session.get("user_name")
    assert response.status_code == 200
    assert b'type="submit" value="Change password"' in response.data


@pytest.mark.parametrize(
    ("old_password", "password", "confirm", "flash_message"), (
    ("", "P@ssw0rdd", "P@ssw0rdd", msg["psw_req"]),
    ("P@ssw0r", "P@ssw0rdd", "P@ssw0rdd", msg["psw_len"]),
    ("P@ssw0rd", "", "P@ssw0rdd", msg["psw_req"]),
    ("P@ssw0rd", "P@ssw0r", "P@ssw0rdd", msg["psw_len"]),
    ("P@ssw0rd", "aaaaaaaa", "aaaaaaaa", msg["psw_rules"]),
    ("P@ssw0rd", "#1aaaaaa", "#1aaaaaa", msg["psw_rules"]),
    ("P@ssw0rd", "#Aaaaaaa", "#Aaaaaaa", msg["psw_rules"]),
    ("P@ssw0rd", "1Aaaaaaa", "1Aaaaaaa", msg["psw_rules"]),
    ("P@ssw0rd", "P@ssw0rdd", "", msg["psw_req"]),
    ("P@ssw0rd", "P@ssw0rdd", "P@ssw0r", msg["psw_len"]),
    ("P@ssw0rd", "P@ssw0rdd", "P@ssw0rddd", msg["psw_eq"]),
    ("P@ssw0rdd", "P@ssw0rdd", "P@ssw0rdd", "Wrong old password!"),
))
def test_failed_change_password(
        client: FlaskClient,
        user_logged_in,
        old_password, password, confirm, flash_message):
    with client:
        client.get("/")
        client.get(url_for("auth.change_password"))
        data = {
            "csrf_token": g.csrf_token,
            "old_password": old_password,
            "password": password,
            "confirm": confirm}
        response = client.post(url_for("auth.change_password"), data=data)
    assert response.status_code == 200
    assert flash_message in unescape(response.text)


def test_successful_change_password(client: FlaskClient, user_logged_in):
    user_name = "user4"
    old_password = "Q!444444"
    new_password = "Q!4444444"
    with client:
        client.get("/")
        client.get(url_for("auth.change_password"))
        data = {
            "csrf_token": g.csrf_token,
            "old_password": old_password,
            "password": new_password,
            "confirm": new_password}
        response = client.post(
            url_for("auth.change_password"), data=data, follow_redirects=True)
        assert not session.get("user_id")
        assert not session.get("admin")
        assert not session.get("user_name")
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("auth.login")
        assert b"Password changed." in response.data

    with dbSession() as db_session:
        test_user = db_session.scalar(
            select(User).filter_by(name=user_name))
        assert check_password_hash(test_user.password, new_password)
        test_user.password = old_password
        db_session.commit()
        test_user = db_session.scalar(
            select(User).filter_by(name=user_name))
        assert check_password_hash(test_user.password, old_password)
# endregion
