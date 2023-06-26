"""Authentification blueprint tests (register, login, logout)."""

import pytest
from flask import session, g
from flask.testing import FlaskClient
from sqlalchemy import select
from werkzeug.security import check_password_hash, generate_password_hash

from tests import client
from database import dbSession, User

pytestmark = pytest.mark.auth


@pytest.fixture(scope="module")
def create_test_users():
    reg_req_user = User(
        name="reg_req_user",
        password=generate_password_hash("P@ssw0rd"))
    not_in_use_user = User(
        name="not_in_use_user",
        password=generate_password_hash("P@ssw0rd"),
        reg_req=False,
        in_use=False)
    ___test___user___ = User(
        name="___test___user___",
        password=generate_password_hash("P@ssw0rd"),
        reg_req=False)
    with dbSession() as db_session:
        db_session.add(reg_req_user)
        db_session.add(not_in_use_user)
        db_session.add(___test___user___)
        db_session.commit()

    yield

    with dbSession() as db_session:
        db_session.delete(reg_req_user)
        db_session.delete(not_in_use_user)
        db_session.delete(___test___user___)
        db_session.commit()

        assert not db_session.get(User, reg_req_user.id)
        assert not db_session.get(User, not_in_use_user.id)


# region: registration page
def test_registration_landing_page(client: FlaskClient):
    response = client.get("/auth/register")
    assert response.status_code == 200
    assert b'type="submit" value="Request registration"' in response.data


def test_clear_session_if_user_logged_in(client: FlaskClient):
    with client.session_transaction() as session:
        assert not session.get("user_id")
        session["user_id"] = 1000
    with client:
        assert session.get("user_id") == 1000
        response = client.get("/auth/register")
        assert response.status_code == 200
        assert b'You have been logged out...' in response.data
    with client.session_transaction() as session:
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
    ("reg_req_user", "P@ssw0rd", "P@ssw0rd", b"Username allready exists..."),
))
def test_failed_registration(
        client: FlaskClient,
        create_test_users,
        name, password, confirm, flash_message):
    with client:
        client.get("/auth/register")
        data = {
            "csrf_token": g.csrf_token,
            "name": name,
            "password": password,
            "confirm": confirm}
        response = client.post("/auth/register", data=data)
    assert response.status_code == 200
    assert flash_message in response.data


def test_successful_registration(client: FlaskClient):
    with client:
        client.get("/auth/register")
        data = {
            "csrf_token": g.csrf_token,
            "name": "__test__user__",
            "password": "P@ssw0rd",
            "confirm": "P@ssw0rd"}
        response = client.post(
            "/auth/register", data=data, follow_redirects=True)
    assert len(response.history) == 1
    assert response.history[0].status_code == 302
    assert response.status_code == 200
    assert response.request.path == "/auth/login"
    assert b"Registration request sent. Please contact an admin." \
        in response.data

    with dbSession() as db_session:
        test_user = db_session.scalar(
            select(User).filter_by(name="__test__user__"))
        assert check_password_hash(test_user.password, "P@ssw0rd")
        assert test_user.reg_req

        db_session.delete(test_user)
        db_session.commit()

        test_user = db_session.scalar(
            select(User).filter_by(name="__test__user__"))
        assert test_user is None
# endregion


# region: login and logout methods
def test_login_landing_page(client: FlaskClient):
    response = client.get("/auth/login")
    assert response.status_code == 200
    assert b'type="submit" value="Log In"' in response.data


@pytest.mark.parametrize(("name", "password", "flash_message"), (
    ("", "", b"Username is required!"),
    ("a", "", b"Password is required!"),
    ("a", "a", b"Wrong username or password!"),
    ("a", "password", b"Wrong username or password!"),
    ("reg_req_user", "a", b"Wrong username or password!"),
    ("not_in_use_user", "P@ssw0rd", b"This user is not in use anymore!"),
    ("reg_req_user", "P@ssw0rd",
        b"Your registration is pending. Contact an admin."),
))
def test_failed_login(
        client: FlaskClient, create_test_users, name, password, flash_message):
    with client:
        client.get("/auth/login")
        data = {
            "csrf_token": g.csrf_token,
            "name": name,
            "password": password}
        response = client.post("/auth/login", data=data)
    assert response.status_code == 200
    assert flash_message in response.data


def test_succesfull_login_and_logout(client: FlaskClient, create_test_users):
    with dbSession() as db_session:
        test_user = db_session.scalar(
                select(User).filter_by(name="___test___user___"))
    with client:
        client.get("/auth/login")
        data = {
            "csrf_token": g.csrf_token,
            "name": "___test___user___",
            "password": "P@ssw0rd"}
        response = client.post("/auth/login", data=data, follow_redirects=True)
        assert session["user_id"] == test_user.id
        assert session["admin"] == test_user.admin
        assert session["user_name"] == test_user.name
    assert len(response.history) == 1
    assert response.history[0].status_code == 302
    assert response.status_code == 200
    assert response.request.path == "/"
    assert b"Welcome ___test___user___" in response.data

    # logout
    with client:
        response = client.get("/auth/logout", follow_redirects=True)
        assert not session.get("user_id")
        assert not session.get("admin")
        assert not session.get("user_name")
    assert len(response.history) == 1
    assert response.history[0].status_code == 302
    assert response.status_code == 200
    assert response.request.path == "/auth/login"


def test_failed_login_no_csrf(client: FlaskClient, create_test_users):
    with client:
        data = {
                "name": "___test___user___",
                "password": "password"}
        response = client.post("/auth/login", data=data)
    assert response.status_code == 200
    assert b"The CSRF token is missing." in response.data


def test_failed_login_bad_csrf(client: FlaskClient, create_test_users):
    with client:
        data = {
            "csrf_token": "some_random_text",
            "name": "___test___user___",
            "password": "password"}
        response = client.post("/auth/login", data=data)
    assert response.status_code == 200
    assert b"The CSRF token is invalid." in response.data
# endregion
