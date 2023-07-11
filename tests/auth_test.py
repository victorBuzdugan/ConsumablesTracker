"""Authentification blueprint tests."""

import pytest
from flask import g, session, url_for
from flask.testing import FlaskClient
from sqlalchemy import select
from werkzeug.security import check_password_hash, generate_password_hash

from database import User, dbSession
from tests import (admin_logged_in, client, create_test_categories,
                   create_test_db, create_test_suppliers, create_test_users,
                   user_logged_in, create_test_products)

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


@pytest.mark.parametrize(("name", "password", "confirm", "flash_message"), (
    ("", "a", "a", b"Username is required!"),
    ("aa", "a", "a", b"Username must be between 3 and 15 characters!"),
    ("aaaaaaaaaaaaaaaa", "a", "a",
        b"Username must be between 3 and 15 characters!"),
    ("aaa", "", "a", b"Password is required!"),
    ("aaa", "aaaaaaa", "a", b"Password should have at least 8 characters!"),
    ("aaa", "aaaaaaaa", "", b"Confirmation password is required!"),
    ("aaa", "aaaaaaaa", "aaaaaaa",
        b"Password should have at least 8 characters!"),
    ("aaa", "aaaaaaaa", "aaaaaaab", b"Passwords don&#39;t match!"),
    ("aaa", "aaaaaaaa", "aaaaaaaa", b"Check password rules!"),
    ("aaa", "#1aaaaaa", "#1aaaaaa", b"Check password rules!"),
    ("aaa", "#Aaaaaaa", "#Aaaaaaa", b"Check password rules!"),
    ("aaa", "1Aaaaaaa", "1Aaaaaaa", b"Check password rules!"),
    ("user5", "P@ssw0rd", "P@ssw0rd", b"Username allready exists..."),
))
def test_failed_registration(
        client: FlaskClient,
        name, password, confirm, flash_message):
    with client:
        client.get("/")
        client.get(url_for("auth.register"))
        data = {
            "csrf_token": g.csrf_token,
            "name": name,
            "password": password,
            "confirm": confirm}
        response = client.post("/auth/register", data=data)
    assert response.status_code == 200
    assert flash_message in response.data


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


@pytest.mark.parametrize(("name", "password", "flash_message"), (
    ("", "", b"Username is required!"),
    ("a", "", b"Password is required!"),
    ("a", "a", b"Wrong username or password!"),
    ("a", "password", b"Wrong username or password!"),
    ("user5", "a", b"Wrong username or password!"),
    ("user6", "Q!666666", b"This user is not in use anymore!"),
    ("user5", "Q!555555",
        b"Your registration is pending. Contact an admin."),
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
    assert flash_message in response.data


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
    assert len(response.history) == 1
    assert response.history[0].status_code == 302
    assert response.status_code == 200
    assert response.request.path == "/"
    assert b"Welcome user4" in response.data

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
    ("", "P@ssw0rdd", "P@ssw0rdd", b"Old password is required!"),
    ("P@ssw0r", "P@ssw0rdd", "P@ssw0rdd",
        b"Password should have at least 8 characters!"),
    ("P@ssw0rd", "", "P@ssw0rdd", b"New password is required!"),
    ("P@ssw0rd", "P@ssw0r", "P@ssw0rdd",
        b"Password should have at least 8 characters!"),
    ("P@ssw0rd", "aaaaaaaa", "aaaaaaaa", b"Check password rules!"),
    ("P@ssw0rd", "#1aaaaaa", "#1aaaaaa", b"Check password rules!"),
    ("P@ssw0rd", "#Aaaaaaa", "#Aaaaaaa", b"Check password rules!"),
    ("P@ssw0rd", "1Aaaaaaa", "1Aaaaaaa", b"Check password rules!"),
    ("P@ssw0rd", "P@ssw0rdd", "", b"Confirmation password is required!"),
    ("P@ssw0rd", "P@ssw0rdd", "P@ssw0r",
        b"Password should have at least 8 characters!"),
    ("P@ssw0rd", "P@ssw0rdd", "P@ssw0rddd", b"Passwords don&#39;t match!"),
    ("P@ssw0rdd", "P@ssw0rdd", "P@ssw0rdd", b"Wrong old password!"),
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
    assert flash_message in response.data


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
        test_user.password = generate_password_hash(old_password)
        db_session.commit()
        test_user = db_session.scalar(
            select(User).filter_by(name=user_name))
        assert check_password_hash(test_user.password, old_password)
# endregion
