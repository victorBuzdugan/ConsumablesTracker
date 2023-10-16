"""Authentification blueprint tests."""

from html import unescape
from os import getenv

import pytest
from flask import g, session, url_for
from flask.testing import FlaskClient
from sqlalchemy import select
from werkzeug.security import check_password_hash

from app import app, babel, get_locale
from blueprints.auth.auth import (PASSW_MIN_LENGTH, USER_MAX_LENGTH,
                                  USER_MIN_LENGTH)
from database import User, dbSession

pytestmark = pytest.mark.auth


# region: registration page
def test_registration_landing_page(client: FlaskClient):
    """test_registration_landing_page"""
    with client:
        client.get("/")
        response = client.get(url_for("auth.register"))
        assert response.status_code == 200
        assert 'type="submit" value="Request registration"' in response.text


def test_clear_session_if_user_logged_in(
        client: FlaskClient, user_logged_in: User):
    """test_clear_session_if_user_logged_in"""
    with client:
        client.get("/")
        assert session.get("user_id") == user_logged_in.id
        response = client.get(url_for("auth.register"))
        assert response.status_code == 200
        assert 'You have been logged out...' in response.text
        assert not session.get("user_id")


@pytest.mark.parametrize(
    ("name", "password", "confirm", "email", "flash_message"), (
        ("", "a", "a", "",
            "Username is required!"),
        ("aa", "a", "a", "",
            f"Username must be between {USER_MIN_LENGTH} and " +
            f"{USER_MAX_LENGTH} characters!"),
        ("aaaaaaaaaaaaaaaa", "a", "a", "",
            f"Username must be between {USER_MIN_LENGTH} and " +
            f"{USER_MAX_LENGTH} characters!"),
        ("aaa", "", "a", "",
            "Password is required!"),
        ("aaa", "aaaaaaa", "a", "",
            f"Password should have at least {PASSW_MIN_LENGTH} characters!"),
        ("aaa", "aaaaaaaa", "", "",
            "Password is required!"),
        ("aaa", "aaaaaaaa", "aaaaaaa", "",
            f"Password should have at least {PASSW_MIN_LENGTH} characters!"),
        ("aaa", "aaaaaaaa", "aaaaaaa", "",
            "Passwords don't match!"),
        ("aaa", "aaaaaaaa", "aaaaaaaa", "",
            "Check password rules!"),
        ("aaa", "#1aaaaaa", "#1aaaaaa", "",
            "Check password rules!"),
        ("aaa", "#Aaaaaaa", "#Aaaaaaa", "",
            "Check password rules!"),
        ("aaa", "1Aaaaaaa", "1Aaaaaaa", "",
            "Check password rules!"),
        ("user5", "P@ssw0rd", "P@ssw0rd", "",
            "The user user5 allready exists"),
        ("__testt_userr_", "P@ssw0rd", "P@ssw0rd",
            "plainaddress", "Invalid email adress"),
        ("__testt_userr_", "P@ssw0rd", "P@ssw0rd", "#@%^%#$@#$@#.com",
            "Invalid email adress"),
        ("__testt_userr_", "P@ssw0rd", "P@ssw0rd", "@example.com",
            "Invalid email adress"),
        ("__testt_userr_", "P@ssw0rd", "P@ssw0rd", "Joe Smith <joe@smith.com>",
            "Invalid email adress"),
        ("__testt_userr_", "P@ssw0rd", "P@ssw0rd", "email@example@example.com",
            "Invalid email adress"),
        ("__testt_userr_", "P@ssw0rd", "P@ssw0rd", "email@-example.com",
            "Invalid email adress"),
    ))
def test_failed_registration(
        client: FlaskClient,
        name, password, confirm, email, flash_message):
    """test_failed_registration"""
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
    """test_successful_registration"""
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
        assert "Registration request sent. Please contact an admin." \
            in response.text

    with dbSession() as db_session:
        db_user = db_session.scalar(
            select(User).filter_by(name=user.name))
        assert check_password_hash(db_user.password, user.password)
        assert db_user.reg_req

        db_session.delete(db_user)
        db_session.commit()
        assert not db_session.get(User, db_user.id)
# endregion


# region: login and logout methods
def test_login_landing_page(client: FlaskClient):
    """test_login_landing_page"""
    with client:
        client.get("/")
        babel.init_app(app=app, locale_selector=get_locale)
        response = client.get(url_for("auth.login"))
        assert response.status_code == 200
        assert 'type="submit" value="Log In"' in response.text
        client.get(url_for("set_language", language="ro"))
        assert session["language"] == "ro"
        response = client.get(url_for("auth.login"))
        assert 'Language changed' not in response.text
        assert 'Username' not in response.text
        assert 'Password' not in response.text
        assert "Limba a fost schimbată" in response.text
        assert "Nume" in response.text
        assert "Parolă" in response.text
        client.get(url_for("set_language", language="en"))
        assert session["language"] == "en"
        response = client.get(url_for("auth.login"))
        assert "Language changed" in response.text
        assert "Username" in response.text
        assert "Password" in response.text
        assert "Limba a fost schimbată" not in response.text
        assert "Nume" not in response.text
        assert "Parolă" not in response.text
        babel.init_app(app=app, locale_selector=lambda: "en")


@pytest.mark.parametrize(("name", "password", "flash_message"), (
    ("", "",
        "Username is required!"),
    ("a", "",
        "Password is required!"),
    ("a", "a",
        "Wrong username or password!"),
    ("a", "password",
        "Wrong username or password!"),
    ("user5", "a",
        "Wrong username or password!"),
    ("user6", "Q!666666",
        "This user is not in use anymore!"),
    ("user5", "Q!555555",
        "Your registration is pending. Contact an admin."),
))
def test_failed_login(
        client: FlaskClient,
        name, password, flash_message):
    """test_failed_login"""
    with client:
        client.get("/")
        client.get(url_for("auth.login"))
        data = {
            "csrf_token": g.csrf_token,
            "name": name,
            "password": password}
        response = client.post(url_for("auth.login"), data=data,
                               follow_redirects=True)
        assert response.request.path == url_for("auth.login")
    assert len(response.history) == 1
    assert response.history[0].status_code == 302
    assert response.status_code == 200
    assert flash_message in response.text


@pytest.mark.parametrize(("name", "password"), (
    ("Admin", getenv('ADMIN_PASSW')),
    ("user1", "Q!111111"),
    ("user2", "Q!222222"),
    ("user3", "Q!333333"),
    ("user4", "Q!444444"),
))
def test_succesfull_login_and_logout(client: FlaskClient, name, password):
    """test_succesfull_login_and_logout"""
    with dbSession() as db_session:
        test_user = db_session.scalar(
                select(User).filter_by(name=name))
    with client:
        client.get("/")
        client.get(url_for("auth.login"))
        data = {
            "csrf_token": g.csrf_token,
            "name": test_user.name,
            "password": password}
        response = client.post("/auth/login", data=data, follow_redirects=True)
        assert session["user_id"] == test_user.id
        assert session["admin"] == test_user.admin
        assert session["user_name"] == name
        assert f"Welcome {name}" in response.text
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("main.index")
        # logout
        response = client.get(url_for("auth.logout"), follow_redirects=True)
        assert not session.get("user_id")
        assert not session.get("admin")
        assert not session.get("user_name")
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("auth.login")


@pytest.mark.parametrize(("csrf", "flash_message"),(
        (None, "The CSRF token is missing"),
        ("", "The CSRF token is missing"),
        (" ", "The CSRF token is invalid"),
        ("some_random_text", "The CSRF token is invalid"),
))
def test_failed_login_csrf(client: FlaskClient, csrf, flash_message):
    """test_failed_login_csrf"""
    with client:
        client.get("/")
        client.get(url_for("auth.login"))
        data = {
            "csrf_token": csrf,
            "name": "user4",
            "password": "P@ssw0rd"}
        response = client.post(url_for("auth.login"), data=data,
                               follow_redirects=True)
        assert response.request.path == url_for("auth.login")
    assert len(response.history) == 1
    assert response.history[0].status_code == 302
    assert response.status_code == 200
    assert flash_message in response.text
# endregion


# region: change password
# also tests @login_required
def test_change_password_landing_page_if_not_logged_in(client: FlaskClient):
    """test_change_password_landing_page_if_not_logged_in"""
    with client:
        client.get("/")
        assert not session.get("user_id")
        assert not session.get("admin")
        assert not session.get("user_name")
        response = client.get(url_for("auth.change_password"),
                              follow_redirects=True)
        assert not session.get("user_id")
        assert not session.get("admin")
        assert not session.get("user_name")
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("auth.login")
        assert 'type="submit" value="Log In"' in response.text
        assert "You have to be logged in..." in response.text

# also tests @login_required
def test_change_password_landing_page_if_user_logged_in(
        client: FlaskClient, user_logged_in: User):
    """test_change_password_landing_page_if_user_logged_in"""
    with client:
        client.get("/")
        response = client.get(url_for("auth.change_password"))
        assert session.get("user_id") == user_logged_in.id
        assert session.get("admin") == user_logged_in.admin
        assert not session.get("admin")
        assert session.get("user_name") == user_logged_in.name
    assert response.status_code == 200
    assert 'type="submit" value="Change password"' in response.text


# also tests @login_required if admin
def test_change_password_landing_page_if_admin_logged_in(
        client: FlaskClient, admin_logged_in: User):
    """test_change_password_landing_page_if_admin_logged_in"""
    with client:
        client.get("/")
        response = client.get(url_for("auth.change_password"))
        assert session.get("user_id") == admin_logged_in.id
        assert session.get("admin") == admin_logged_in.admin
        assert session.get("admin")
        assert session.get("user_name") == admin_logged_in.username
    assert response.status_code == 200
    assert 'type="submit" value="Change password"' in response.text


@pytest.mark.parametrize(
    ("old_password", "password", "confirm",
     "flash_message"), (
        ("", "P@ssw0rdd", "P@ssw0rdd",
        "Password is required!"),
        ("P@ssw0r", "P@ssw0rdd", "P@ssw0rdd",
        f"Password should have at least {PASSW_MIN_LENGTH} characters!"),
        ("P@ssw0rd", "", "P@ssw0rdd",
        "Password is required!"),
        ("P@ssw0rd", "P@ssw0r", "P@ssw0rdd",
        f"Password should have at least {PASSW_MIN_LENGTH} characters!"),
        ("P@ssw0rd", "aaaaaaaa", "aaaaaaaa",
         "Check password rules!"),
        ("P@ssw0rd", "#1aaaaaa", "#1aaaaaa",
         "Check password rules!"),
        ("P@ssw0rd", "#Aaaaaaa", "#Aaaaaaa",
         "Check password rules!"),
        ("P@ssw0rd", "1Aaaaaaa", "1Aaaaaaa",
         "Check password rules!"),
        ("P@ssw0rd", "P@ssw0rdd", "",
         "Password is required!"),
        ("P@ssw0rd", "P@ssw0rdd", "P@ssw0r",
        f"Password should have at least {PASSW_MIN_LENGTH} characters!"),
        ("P@ssw0rd", "P@ssw0rdd", "P@ssw0rddd",
         "Passwords don't match!"),
        ("P@ssw0rdd", "P@ssw0rdd", "P@ssw0rdd",
         "Wrong old password!"),
))
def test_failed_change_password(
        client: FlaskClient, user_logged_in: User,
        old_password, password, confirm, flash_message):
    """test_failed_change_password"""
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
    with dbSession() as db_session:
        user_logged_in = db_session.get(User, user_logged_in.id)
        assert not check_password_hash(user_logged_in.password, password)


def test_successful_change_password(client: FlaskClient, user_logged_in: User):
    """test_successful_change_password"""
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
        assert "Password changed." in response.text

    with dbSession() as db_session:
        user_logged_in = db_session.get(User, user_logged_in.id)
        assert check_password_hash(user_logged_in.password, new_password)
        user_logged_in.password = old_password
        db_session.commit()
        db_session.refresh(user_logged_in)
        assert check_password_hash(user_logged_in.password, old_password)
# endregion
