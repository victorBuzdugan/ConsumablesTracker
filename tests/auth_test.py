"""Authentification blueprint tests."""

import re
from html import unescape

import pytest
from flask import g, session, url_for
from flask.testing import FlaskClient
from hypothesis import assume, example, given, settings
from hypothesis import strategies as st
from pytest import LogCaptureFixture
from sqlalchemy import select
from werkzeug.security import check_password_hash

from app import app, babel, get_locale
from constants import Constant
from database import User, dbSession
from messages import Message
from tests import InvalidUser, ValidUser, redirected_to, test_users

pytestmark = pytest.mark.auth


# region: registration page
def test_registration_landing_page_user_not_logged_in(client: FlaskClient):
    """test_registration_landing_page_user_not_logged_in"""
    retype_passw_field = re.compile(r'<input .* placeholder="Retype password"')
    req_reg_button = re.compile(r'<input .* value="Request registration">')
    with client:
        client.get("/")
        response = client.get(url_for("auth.register"))
        assert response.status_code == 200
        assert retype_passw_field.search(response.text)
        assert req_reg_button.search(response.text)


def test_clear_session_if_user_logged_in(
        client: FlaskClient, user_logged_in: User):
    """test_clear_session_if_user_logged_in"""
    with client:
        client.get("/")
        assert session.get("user_id") == user_logged_in.id
        response = client.get(url_for("auth.register"))
        assert response.status_code == 200
        assert str(Message.User.Logout()) in response.text
        assert not session.get("user_id")


# region: failed registration
def _test_failed_registration(
        client: FlaskClient,
        flash_message,
        name=ValidUser.name,
        password=ValidUser.password,
        confirm=ValidUser.password,
        email=ValidUser.email
    ):
    """Common logic for testing failed registration."""
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
    assert str(Message.User.Registered()) not in response.text


@settings(max_examples=3)
@given(name=st.text(min_size=1, max_size=Constant.User.Name.min_length - 1))
@example(name="")
@example(name=InvalidUser.short_name)
def test_failed_registration_short_name(client: FlaskClient, name):
    """test_failed_registration_short_name"""
    if not name:
        flash_message = str(Message.User.Name.Required())
    else:
        flash_message = str(Message.User.Name.LenLimit())
    _test_failed_registration(client=client,
                              name=name,
                              flash_message=flash_message)


@settings(max_examples=3)
@given(name=st.text(min_size=Constant.User.Name.max_length + 1))
@example(name=InvalidUser.long_name)
def test_failed_registration_long_name(client: FlaskClient, name):
    """test_failed_registration_long_name"""
    flash_message = str(Message.User.Name.LenLimit())
    _test_failed_registration(client=client,
                              name=name,
                              flash_message=flash_message)


@settings(max_examples=3)
@given(password=st.text(min_size=1,
                        max_size=Constant.User.Password.min_length - 1))
@example(password="")
@example(password=InvalidUser.short_password)
def test_failed_registration_short_password(client: FlaskClient, password):
    """test_failed_registration_short_password"""
    if not password:
        flash_message = str(Message.User.Password.Required())
    else:
        flash_message = str(Message.User.Password.LenLimit())
    _test_failed_registration(client=client,
                              password=password,
                              flash_message=flash_message)


@settings(max_examples=3)
@given(confirm=st.text(min_size=1,
                       max_size=Constant.User.Password.min_length - 1))
@example(confirm="")
def test_failed_registration_short_confirmation(client: FlaskClient, confirm):
    """test_failed_registration_short_confirmation"""
    if not confirm:
        flash_message = str(Message.User.Password.Required())
    else:
        flash_message = str(Message.User.Password.LenLimit())
    _test_failed_registration(client=client,
                              confirm=confirm,
                              flash_message=flash_message)


@settings(max_examples=3)
@given(password=st.text(min_size=8), confirm=st.text(min_size=8))
def test_failed_registration_confirmation_not_matching(
        client: FlaskClient, password, confirm):
    """test_failed_registration_confirmation_not_matching"""
    assume(password != confirm)
    flash_message = str(Message.User.Password.NotMatching())
    _test_failed_registration(client=client,
                              password=password,
                              confirm=confirm,
                              flash_message=flash_message)


def _test_failed_registration_password_rules(
        client: FlaskClient, password):
    """Common logic for testing password characters rules."""
    flash_message = str(Message.User.Password.CheckRules())
    _test_failed_registration(client=client,
                              password=password,
                              confirm=password,
                              flash_message=flash_message)


@settings(max_examples=5)
@given(password=st.from_regex(r"[A-Z]+[!@#$%^&*_=+]+[^\d]{6,}",
                              fullmatch=True))
@example(password=InvalidUser.no_number_password)
def test_failed_registration_no_digit_in_password(
        client: FlaskClient, password):
    """test_failed_registration_no_digit_in_password"""
    _test_failed_registration_password_rules(client=client,
                                             password=password)


@settings(max_examples=5)
@given(password=st.from_regex(r"[A-Z]+[0-9]+[^!@#$%^&*_=+]{6,}",
                              fullmatch=True))
@example(password=InvalidUser.no_special_char_password)
def test_failed_registration_no_special_character_in_password(
        client: FlaskClient, password):
    """test_failed_registration_no_special_character_in_password"""
    _test_failed_registration_password_rules(client=client,
                                             password=password)


@settings(max_examples=5)
@given(password=st.from_regex(r"[0-9]+[!@#$%^&*_=+]+[^A-Z]{6,}",
                              fullmatch=True))
@example(password=InvalidUser.no_uppercase_password)
def test_failed_registration_no_big_letter_in_password(
        client: FlaskClient, password):
    """test_failed_registration_no_big_letter_in_password"""
    _test_failed_registration_password_rules(client=client,
                                             password=password)


@settings(max_examples=5)
@given(name=st.sampled_from([user["name"] for user in test_users]))
def test_failed_registration_existing_username(
        client: FlaskClient, name):
    """test_failed_registration_existing_username"""
    flash_message = str(Message.User.Name.Exists(name))
    _test_failed_registration(client=client,
                              name=name,
                              flash_message=flash_message)


@settings(max_examples=30)
@given(valid_email=st.emails(), st_random = st.randoms())
def test_failed_registration_invalid_email(
        client: FlaskClient, valid_email, st_random):
    """test_failed_registration_invalid_email"""
    invalid_chars = " @()[]:;\"\\,"
    def remove_local(email: str) -> str:
        """Remove the local part from email"""
        return "@" + email.split("@")[1]
    def remove_at_symbol(email: str) -> str:
        """Remove the @ symbol from email"""
        return email.replace("@", "")
    def remove_domain(email: str) -> str:
        """Remove the domain part from email"""
        return email.split("@")[0] + "@"
    def remove_top_level_domain(email: str) -> str:
        """Remove the top level domain (.com) from the email"""
        return email.rsplit(".")[0]
    def add_invalid_char_local(email: str) -> str:
        """Add an invalid character to the local part"""
        return (email.split("@")[0] +
                st_random.choice(invalid_chars) +
                "@" +
                email.split("@")[1])
    def add_invalid_char_domain(email: str) -> str:
        """Add an invalid character to the domain part"""
        return (email.split("@")[0] +
                "@" +
                st_random.choice(invalid_chars) +
                email.split("@")[1])
    def exceed_local_max_length(email: str) -> str:
        """Add chars in order to exceed 64 octets local part limit"""
        return "x" * 65 + "@" + email.split("@")[1]
    def exceed_domain_max_length(email: str) -> str:
        """Add chars in order to exceed 255 octets domain part limit"""
        return (email.split("@")[0] + "@" +
                "x" * 256 +
                "." + email.rsplit(".")[1])
    flash_message = str(Message.User.Email.Invalid())
    invalidate_email = st_random.choice([remove_local,
                                      remove_at_symbol,
                                      remove_domain,
                                      remove_top_level_domain,
                                      add_invalid_char_local,
                                      add_invalid_char_domain,
                                      exceed_local_max_length,
                                      exceed_domain_max_length])
    _test_failed_registration(client=client,
                              email=invalidate_email(valid_email),
                              flash_message=flash_message)
# endregion


@pytest.mark.slow
@settings(max_examples=3)
@given(name = st.text(min_size=Constant.User.Name.min_length,
                      max_size=Constant.User.Name.max_length),
       password = st.from_regex(Constant.User.Password.regex, fullmatch=True),
       email = st.emails())
@example(name=ValidUser.name,
         password=ValidUser.password,
         email=ValidUser.email)
@example(name=ValidUser.name,
         password=ValidUser.password,
         email="")
@example(name=ValidUser.name + " ",
         password=ValidUser.password,
         email="")
def test_registration(
        client: FlaskClient, name: str, password: str, email: str):
    """Test successful registration"""
    name = name.strip()
    raw_password = repr(password)
    assume(Constant.User.Name.min_length <= len(name))
    assume(Constant.User.Name.max_length >= len(name))
    assume(name not in [user["name"] for user in test_users])
    with client:
        client.get("/")
        client.get(url_for("auth.register"))
        data = {
            "csrf_token": g.csrf_token,
            "name": name,
            "password": raw_password,
            "confirm": raw_password,
            "email": email}
        response = client.post(
            "/auth/register", data=data, follow_redirects=True)
        assert redirected_to(url_for("auth.login"), response)
        assert str(Message.User.Registered()) in response.text

    with dbSession() as db_session:
        db_user = db_session.scalar(
            select(User).filter_by(name=name))
        assert check_password_hash(db_user.password, raw_password)
        assert db_user.email == email
        assert db_user.reg_req

        db_session.delete(db_user)
        db_session.commit()
        assert not db_session.get(User, db_user.id)
# endregion


# region: login and logout pages
def test_login_landing_page(client: FlaskClient, caplog: LogCaptureFixture):
    """Test login landing page, babel get_locale and language change"""
    log_in_button = re.compile(r'<input.*type="submit".*value="Log In">')
    en_texts = ("The language was changed", "Username", "Password")
    ro_texts = ("Limba a fost schimbată", "Nume", "Parolă")
    with client:
        client.get("/")
        # test get locale 'en'
        babel.init_app(app=app, locale_selector=get_locale)
        response = client.get(url_for("auth.login"),
                              headers={"Accept-Language": "en-GB,en;q=0.9"})
        assert response.status_code == 200
        assert log_in_button.search(response.text)
        assert "Got locale language 'en'" in caplog.messages
        caplog.clear()
        # change language to 'ro'
        response = client.get(url_for("set_language", language="ro"),
                              headers={"Referer": url_for("auth.login")},
                              follow_redirects=True)
        assert redirected_to(url_for("auth.login"), response)
        assert session["language"] == "ro"
        for text in en_texts:
            assert text not in response.text
        for text in ro_texts:
            assert text in response.text
        assert "Language changed to 'ro'" in caplog.messages
        caplog.clear()
        # change language to 'en'
        response = client.get(url_for("set_language", language="en"),
                              headers={"Referer": url_for("auth.login")},
                              follow_redirects=True)
        assert redirected_to(url_for("auth.login"), response)
        assert session["language"] == "en"
        for text in en_texts:
            assert text in response.text
        for text in ro_texts:
            assert text not in response.text
        assert "Language changed to 'en'" in caplog.messages
        caplog.clear()
        # test language None and no referer(first redirects to main page)
        client.get(url_for("auth.register"))
        response = client.get(url_for("set_language", language="None"),
                              follow_redirects=True)
        assert response.history[1].request.path == url_for("main.index")
        assert redirected_to(url_for("auth.login"), response, 2)
        assert session["language"] == "en"
        assert "Language changed to 'en'" in caplog.messages
        # teardown
        babel.init_app(app=app, locale_selector=lambda: "en")


def test_could_not__get_locale(client: FlaskClient, caplog: LogCaptureFixture):
    """test_could_not__get_locale"""
    # clear language from session
    with client.session_transaction() as this_session:
        this_session.clear()
    with client:
        # configure babel to get_locale
        babel.init_app(app=app, locale_selector=get_locale)
        client.get("/")
        assert "Could not get locale language" in caplog.messages
        # teardown
        babel.init_app(app=app, locale_selector=lambda: "en")


def _test_failed_login(client: FlaskClient, name, password, flash_message):
    """Common logic for failed login"""
    with client:
        client.get("/")
        client.get(url_for("auth.login"))
        data = {
            "csrf_token": g.csrf_token,
            "name": name,
            "password": password}
        response = client.post(url_for("auth.login"), data=data,
                               follow_redirects=True)
        assert redirected_to(url_for("auth.login"), response)
    assert flash_message in response.text


@settings(max_examples=3)
@given(name=st.text())
@example(name="")
def test_failed_login_username(client: FlaskClient, name):
    """Failed login bad username or no username"""
    if not name:
        flash_message = str(Message.User.Name.Required())
    else:
        flash_message = str(Message.UI.Auth.Wrong())
    _test_failed_login(client=client,
                       name=name,
                       password=ValidUser.password,
                       flash_message=flash_message)


def test_failed_login_password(client: FlaskClient):
    """Failed login bad password or no password"""
    for user in test_users:
        password = user["password"]
        if user == test_users[0]:
            password = ""
            flash_message = str(Message.User.Password.Required())
        elif not user["in_use"]:
            flash_message = str(Message.User.Retired(user["name"]))
        elif user["reg_req"]:
            flash_message = str(Message.User.RegPending(user["name"]))
        else:
            password = "bad_password"
            flash_message = str(Message.UI.Auth.Wrong())
        _test_failed_login(client=client,
                        name=user["name"],
                        password=password,
                        flash_message=flash_message)


@settings(max_examples=3)
@given(user=st.sampled_from(test_users))
def test_login_and_logout(client: FlaskClient, user: dict):
    """Login and then logout"""
    assume(user["in_use"] and not user["reg_req"])
    with client:
        client.get("/")
        client.get(url_for("auth.login"))
        data = {
            "csrf_token": g.csrf_token,
            "name": user["name"],
            "password": user["password"]}
        response = client.post("/auth/login", data=data, follow_redirects=True)
        assert redirected_to(url_for("main.index"), response)
        assert str(Message.User.Login(user['name'])) in response.text
        assert session["user_id"] == user["id"]
        assert session["admin"] == user["admin"]
        assert session["user_name"] == user["name"]
        # logout
        response = client.get(url_for("auth.logout"), follow_redirects=True)
        assert redirected_to(url_for("auth.login"), response)
        assert not session.get("user_id")
        assert not session.get("admin")
        assert not session.get("user_name")


@settings(max_examples=3)
@given(csrf=st.text(min_size=1))
@example(None)
@example("")
def test_failed_login_wrong_csrf(client: FlaskClient, csrf):
    """Failed login because missing or wrong csrf"""
    if csrf is None or csrf == "":
        flash_message = "The CSRF token is missing"
    else:
        flash_message = "The CSRF token is invalid"
    with client:
        client.get("/")
        client.get(url_for("auth.login"))
        data = {
            "csrf_token": csrf,
            "name": "doesnt_matter",
            "password": "doesnt_matter"}
        response = client.post(url_for("auth.login"), data=data,
                               follow_redirects=True)
        assert redirected_to(url_for("auth.login"), response)
    assert flash_message in response.text
# endregion


# region: change password
def test_change_password_landing_page_if_not_logged_in(client: FlaskClient):
    """test_change_password_landing_page_if_not_logged_in"""
    log_in_btn = re.compile(
        r'<input.*type="submit".*value="Log In">')
    change_passw_btn = re.compile(
        r'<input.*type="submit".*value="Change password">')
    session_elements = ("user_id", "admin", "user_name")
    with client:
        client.get("/")
        for elem in session_elements:
            assert not session.get(elem)
        response = client.get(
            url_for("auth.change_password"), follow_redirects=True)
        for elem in session_elements:
            assert not session.get(elem)
        assert redirected_to(url_for("auth.login"), response)
        assert str(Message.UI.Auth.LoginReq()) in response.text
        assert log_in_btn.search(response.text)
        assert not change_passw_btn.search(response.text)


@settings(max_examples=3)
@given(user=st.sampled_from(test_users))
def test_change_password_landing_page_if_user_logged_in(
        client: FlaskClient, user: dict):
    """test_change_password_landing_page_if_user_logged_in"""
    assume(user["in_use"] and not user["reg_req"])
    change_passw_btn = re.compile(
        r'<input.*type="submit".*value="Change password">')
    with client.session_transaction() as this_session:
        this_session["user_id"] = user["id"]
        this_session["admin"] = user["admin"]
        this_session["user_name"] = user["name"]
    with client:
        client.get("/")
        assert session.get("user_id") == user["id"]
        response = client.get(url_for("auth.change_password"))
    assert response.status_code == 200
    assert change_passw_btn.search(response.text)


@pytest.mark.parametrize(
    ("old_password", "new_password", "confirm", "flash_message"),
    [pytest.param(
        "",
        ValidUser.password,
        ValidUser.password,
        str(Message.User.Password.Required()),
        id="Missing old password"),
    pytest.param(
        InvalidUser.short_password,
        ValidUser.password,
        ValidUser.password,
        str(Message.User.Password.LenLimit()),
        id="Short old password"),
    pytest.param(
        ValidUser.password,
        "",
        ValidUser.password,
        str(Message.User.Password.Required()),
        id="Missing new password"),
    pytest.param(
        ValidUser.password,
        InvalidUser.short_password,
        ValidUser.password,
        str(Message.User.Password.LenLimit()),
        id="Short new password"),
    pytest.param(
        ValidUser.password,
        InvalidUser.only_lowercase_password,
        InvalidUser.only_lowercase_password,
        str(Message.User.Password.CheckRules()),
        id="Only lowercase new password"),
    pytest.param(
        ValidUser.password,
        InvalidUser.no_uppercase_password,
        InvalidUser.no_uppercase_password,
        str(Message.User.Password.CheckRules()),
        id="No uppercase char in new password"),
    pytest.param(
        ValidUser.password,
        InvalidUser.no_number_password,
        InvalidUser.no_number_password,
        str(Message.User.Password.CheckRules()),
        id="No number in new password"),
    pytest.param(
        ValidUser.password,
        InvalidUser.no_special_char_password,
        InvalidUser.no_special_char_password,
        str(Message.User.Password.CheckRules()),
        id="No special char in new password"),
    pytest.param(
        ValidUser.password,
        ValidUser.password,
        "",
        str(Message.User.Password.Required()),
        id="Missing confirmation password"),
    pytest.param(
        ValidUser.password,
        ValidUser.password,
        InvalidUser.short_password,
        str(Message.User.Password.LenLimit()),
        id="Short confirmation password"),
    pytest.param(
        ValidUser.password,
        ValidUser.password,
        ValidUser.password + "x",
        str(Message.User.Password.NotMatching()),
        id="Confirmation not mathcing new password"),
    pytest.param(
        ValidUser.password,
        ValidUser.password,
        ValidUser.password,
        str(Message.User.Password.WrongOld()),
        id="Wrong old password"),
    ]
)
def test_failed_change_password(
        client: FlaskClient, user_logged_in: User,
        old_password, new_password, confirm, flash_message):
    """test_failed_change_password"""
    with client:
        client.get("/")
        client.get(url_for("auth.change_password"))
        data = {
            "csrf_token": g.csrf_token,
            "old_password": old_password,
            "password": new_password,
            "confirm": confirm}
        response = client.post(url_for("auth.change_password"), data=data)
    assert response.status_code == 200
    assert flash_message in response.text
    with dbSession() as db_session:
        user_logged_in = db_session.get(User, user_logged_in.id)
        assert not check_password_hash(user_logged_in.password, new_password)


def test_change_password(client: FlaskClient, user_logged_in: User):
    """test_successful_change_password"""
    old_password = test_users[user_logged_in.id]["password"]
    new_password = ValidUser.password
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
        assert redirected_to(url_for("auth.login"), response)
        assert str(Message.User.Password.Changed()) in response.text
        assert not session.get("user_id")
        assert not session.get("admin")
        assert not session.get("user_name")

    with dbSession() as db_session:
        user_logged_in = db_session.get(User, user_logged_in.id)
        assert check_password_hash(user_logged_in.password, new_password)
        # teardown
        user_logged_in.password = old_password
        db_session.commit()
        db_session.refresh(user_logged_in)
        assert check_password_hash(user_logged_in.password, old_password)
# endregion
