"""Users blueprint tests."""

from html import unescape

import pytest
from flask import g, session, url_for
from flask.testing import FlaskClient
from pytest import LogCaptureFixture
from sqlalchemy import select
from werkzeug.security import check_password_hash

from blueprints.sch.sch import cleaning_sch
from constants import Constant
from database import User, dbSession
from messages import Message

pytestmark = pytest.mark.users


# region: approve registration
def test_approve_registration(
        client: FlaskClient, admin_logged_in: User, caplog: LogCaptureFixture):
    """test_approve_registration"""
    unreg_user = "user5"
    with client:
        response = client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        assert "requested registration" in response.text
        response = client.get(url_for("sch.schedules"))
        assert unreg_user not in response.text
        client.get(url_for("main.index"))
        response = client.get(
            url_for("users.approve_reg", username=unreg_user),
            follow_redirects=True)
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("main.index")
        assert str(Message.User.Approved(unreg_user)) in response.text
        assert "Review the schedules" in response.text
        response = client.get(url_for("sch.schedules"))
        assert unreg_user in response.text
        assert f"Schedule '{cleaning_sch.name}' added '{unreg_user}'" \
            in caplog.messages
        with dbSession() as db_session:
            assert not db_session.get(User, 5).reg_req
            # teardown
            db_session.get(User, 5).reg_req = True
            db_session.commit()
            cleaning_sch.remove_user(5)


def test_failed_approve_registration_bad_username(
        client: FlaskClient, admin_logged_in: User):
    """test_failed_approve_registration_bad_username"""
    ne_user = "not_existing_user"
    with client:
        response = client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        assert "requested registration" in response.text
        response = client.get(
            url_for("users.approve_reg", username=ne_user),
            follow_redirects=True)
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("main.index")
        assert str(Message.User.NotExists(ne_user)) in response.text


def test_failed_approve_registration_user_logged_in(
        client: FlaskClient, user_logged_in: User):
    """test_failed_approve_registration_user_logged_in"""
    unreg_user = "user5"
    with client:
        response = client.get("/")
        assert session["user_name"] == user_logged_in.name
        assert not session["admin"]
        assert "requested registration" not in response.text
        response = client.get(
            url_for("users.approve_reg", username=unreg_user),
            follow_redirects=True)
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("auth.login")
        assert "You have to be an admin..." in response.text
        assert session.get("user_id")
        with dbSession() as db_session:
            assert db_session.get(User, 5).reg_req
# endregion


# region: approve check inventory
def test_approve_check_inventory(client: FlaskClient, admin_logged_in: User):
    """test_approve_check_inventory"""
    with dbSession() as db_session:
        user = db_session.get(User, 4)
        user.req_inv = True
        db_session.commit()
        with client:
            response = client.get("/")
            assert session["user_name"] == admin_logged_in.name
            assert session["admin"]
            assert "requested inventory" in response.text
            response = client.get(
                url_for("users.approve_check_inv", username=user.name),
                follow_redirects=True)
            assert len(response.history) == 1
            assert response.history[0].status_code == 302
            assert response.status_code == 200
            assert response.request.path == url_for("main.index")
            assert "requested inventory" not in response.text
            assert "check inventory" in response.text
        db_session.refresh(user)
        assert not user.done_inv
        assert not user.req_inv
        user.done_inv = True
        db_session.commit()


@pytest.mark.parametrize(("user_id", "username", "flash_message"), (
    ("6", "user6", "'Retired' user can't check inventory"),
    ("5", "user5", "User with pending registration can't check inventory"),
    ("7", "user7", "User without products attached can't check inventory"),
    # id 7 because id 8 doesn't exist
    ("7", "user8", str(Message.User.NotExists("user8"))),
))
def test_failed_approve_check_inventory(
        client: FlaskClient, admin_logged_in: User,
        user_id, username, flash_message):
    """test_failed_approve_check_inventory"""
    with client:
        response = client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        response = client.get(
            url_for("users.approve_check_inv", username=username),
            follow_redirects=True)
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("main.index")
        assert flash_message in unescape(response.text)
        with dbSession() as db_session:
            assert db_session.get(User, user_id).done_inv


def test_failed_approve_check_inventory_user_logged_in(
        client: FlaskClient, user_logged_in: User):
    """test_failed_approve_check_inventory_user_logged_in"""
    with dbSession() as db_session:
        user = db_session.get(User, 4)
        user.req_inv = True
        db_session.commit()
        with client:
            response = client.get("/")
            assert session["user_name"] == user_logged_in.name
            assert not session["admin"]
            assert "requested inventory" not in response.text
            response = client.get(
                url_for("users.approve_check_inv", username=user.name),
                follow_redirects=True)
            assert len(response.history) == 1
            assert response.history[0].status_code == 302
            assert response.status_code == 200
            assert response.request.path == url_for("auth.login")
            assert "You have to be an admin..." in response.text
            assert session.get("user_id")
        db_session.refresh(user)
        assert user.done_inv
        assert user.req_inv


def test_approve_all_check_inventory(
        client: FlaskClient, admin_logged_in: User):
    """test_approve_all_check_inventory"""
    with dbSession() as db_session:
        user = db_session.get(User, 4)
        user.req_inv = True
        db_session.commit()
        with client:
            response = client.get("/")
            assert session["user_name"] == admin_logged_in.name
            assert session["admin"]
            assert "requested inventory" in response.text
            response = client.get(
                url_for("users.approve_check_inv_all"), follow_redirects=True)
            assert len(response.history) == 1
            assert response.history[0].status_code == 302
            assert response.status_code == 200
            assert response.request.path == url_for("main.index")
            assert "requested inventory" not in response.text
            assert "check inventory" in response.text
        for user_id in range(1, 4):
            assert not db_session.get(User, user_id).done_inv
        db_session.refresh(user)
        assert not user.done_inv
        assert not user.req_inv
        for user_id in range(1, 5):
            db_session.get(User, user_id).done_inv = True
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
def test_new_user(
        client: FlaskClient, admin_logged_in: User, caplog: LogCaptureFixture,
        details, admin, email, sat_group):
    """test_new_user"""
    name = "new_user"
    password = "Q!111111"
    with client:
        client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        response = client.get(url_for("sch.schedules"))
        assert name not in response.text
        response = client.get(url_for("users.new_user"))
        assert "Create user" in response.text
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
        assert f"User '{name}' created" in unescape(response.text)
        assert "Review the schedules" in response.text
        response = client.get(url_for("sch.schedules"))
        assert name in response.text
        assert f"Schedule '{cleaning_sch.name}' added '{name}'" \
            in caplog.messages
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
        # teardown
        db_session.delete(user)
        db_session.commit()
        cleaning_sch.remove_user(user.id)


@pytest.mark.parametrize(
    ("name", "password", "email", "sat_group",
     "flash_message"), (
        ("", "Q!111111", "", "1",
         str(Message.User.Name.Req())),
        ("us", "Q!111111", "", "1",
         f"Username must be between {Constant.User.Name.min_length} and " +
         f"{Constant.User.Name.max_length} characters!"),
        ("useruseruseruser", "Q!111111", "", "1",
         f"Username must be between {Constant.User.Name.min_length} and " +
         f"{Constant.User.Name.max_length} characters!"),
        ("new_user", "", "", "1",
         str(Message.User.Password.Req())),
        ("new_user", "Q!1", "", "1",
         ("Password should have at least " +
          f"{Constant.User.Password.min_length} characters!")),
        ("new_user", "aaaaaaaa", "", "1",
         "Password must have 1 big letter, 1 number, 1 special char (" +
         f"{Constant.User.Password.symbols})!"),
        ("new_user", "#1aaaaaa", "", "1",
         "Password must have 1 big letter, 1 number, 1 special char (" +
         f"{Constant.User.Password.symbols})!"),
        ("new_user", "#Aaaaaaa", "", "1",
         "Password must have 1 big letter, 1 number, 1 special char (" +
         f"{Constant.User.Password.symbols})!"),
        ("new_user", "1Aaaaaaa", "", "1",
         "Password must have 1 big letter, 1 number, 1 special char (" +
         f"{Constant.User.Password.symbols})!"),
        ("user1", "Q!111111", "", "1",
         str(Message.User.Name.Exists("user1"))),
        ("Admin", "Q!111111", "", "1",
         str(Message.User.Name.Exists("Admin"))),
        ("new_user", "Q!111111", "1", "plainaddress",
         "Invalid email adress"),
        ("new_user", "Q!111111", "1", "#@%^%#$@#$@#.com",
         "Invalid email adress"),
        ("new_user", "Q!111111", "1", "@example.com",
         "Invalid email adress"),
        ("new_user", "Q!111111", "1", "Joe Smith <email@example.com>",
         "Invalid email adress"),
        ("new_user", "Q!111111", "1", "email@example@example.com",
         "Invalid email adress"),
        ("new_user", "Q!111111", "1", "email@-example.com",
         "Invalid email adress"),
        ("new_user", "Q!111111", "3", "email@example.com",
         "Invalid Choice: could not coerce"),
        ("new_user", "Q!111111", "", "email@example.com",
         "Invalid Choice: could not coerce"),
        ("new_user", "Q!111111", "a", "email@example.com",
         "Invalid Choice: could not coerce"),
))
def test_failed_new_user(
        client: FlaskClient, admin_logged_in: User,
        name, password, email, sat_group, flash_message):
    """test_failed_new_user"""
    with client:
        client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        response = client.get(url_for("users.new_user"))
        assert "Create user" in response.text
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
        assert "Create user" in response.text
        assert flash_message in unescape(response.text)
        assert f"User '{name}' created" not in unescape(response.text)
    if name not in {"user1", "Admin"}:
        with dbSession() as db_session:
            assert not db_session.scalar(select(User).filter_by(name=name))
# endregion


# region: edit user
@pytest.mark.parametrize(
    ("user_id", "new_name", "orig_password", "new_password", "new_details",
     "new_check_inv", "new_admin", "new_in_use",
     "new_email", "new_sat_group"), (
        # 1 element
        ("4", "test_user", "Q!444444", "", "",
         "", "", "on",
         "validemail@gmail.com", "1"),
        ("4", "user4", "Q!444444", "Q!111111", "",
         "", "", "on",
         "", "1"),
        ("4", "user4", "Q!444444", "", "Some detail",
         "", "", "on",
         "", "2"),
        ("4", "user4", "Q!444444", "", "",
         "on", "", "on",
         "validemail@gmail.com", "1"),
        ("4", "user4", "Q!444444", "", "",
         "", "on", "on",
         "", "1"),
        ("5", "user5", "Q!555555", "", "",
         "", "", "",
         "", "1"),
        # 2 elements
        ("3", "test_user", "Q!333333", "Q!111111", "",
         "", "", "on",
         "", "1"),
        ("3", "test_user", "Q!333333", "", "Some detail",
         "", "", "on",
         "validemail@gmail.com", "1"),
        ("3", "test_user", "Q!333333", "", "",
         "on", "", "on",
         "", "2"),
        ("3", "test_user", "Q!333333", "", "",
         "", "on", "on",
         "", "1"),
        ("6", "test_user", "Q!666666", "", "",
         "", "", "on",
         "", "1"),
        ("2", "user2", "Q!222222", "Q!111111", "Some detail",
         "", "on", "on",
         "", "1"),
        ("2", "user2", "Q!222222", "Q!111111", "",
         "on", "on", "on",
         "", "1"),
        ("2", "user2", "Q!222222", "Q!111111", "",
         "", "", "on",
         "validemail@gmail.com", "2"),
        ("7", "user7", "Q!777777", "Q!111111", "",
         "", "", "",
         "", "1"),
        ("1", "user1", "Q!111111", "", "Some detail",
         "on", "on", "on",
         "", "1"),
        ("2", "user2", "Q!222222", "", "Some detail",
         "", "", "on",
         "", "1"),
        ("5", "user5", "Q!555555", "", "Some detail",
         "", "", "",
         "", "1"),
        ("2", "user2", "Q!222222", "", "",
         "on", "", "on",
         "", "1"),
        ("6", "user6", "Q!666666", "", "",
         "", "on", "on",
         "validemail@gmail.com", "2"),
        # 3 elements
        ("1", "test_user", "Q!111111", "Q!222222", "Some detail",
         "", "on", "on",
         "", "1"),
        ("1", "test_user", "Q!111111", "Q!222222", "",
         "on", "on", "on",
         "", "1"),
        ("2", "test_user", "Q!222222", "Q!111111", "",
         "", "", "on",
         "", "1"),
        ("7", "test_user", "Q!777777", "Q!111111", "",
         "", "", "",
         "", "2"),
        ("3", "test_user", "Q!333333", "", "Some detail",
         "on", "", "on",
         "validemail@gmail.com", "1"),
        ("3", "test_user", "Q!333333", "", "Some detail",
         "", "on", "on",
         "", "1"),
        ("5", "test_user", "Q!555555", "", "Some detail",
         "", "", "",
         "", "1"),
        ("3", "test_user", "Q!333333", "", "",
         "on", "on", "on",
         "", "1"),
        ("6", "test_user", "Q!666666", "", "",
         "", "on", "on",
         "", "2"),
        ("4", "user4", "Q!444444", "Q!111111", "Some detail",
         "on", "", "on",
         "", "1"),
        ("4", "user4", "Q!444444", "Q!111111", "Some detail",
         "", "on", "on",
         "", "1"),
        ("5", "user5", "Q!555555", "Q!111111", "Some detail",
         "", "", "",
         "validemail@gmail.com", "1"),
        ("4", "user4", "Q!444444", "", "Some detail",
         "on", "on", "on",
         "", "1"),
        ("7", "user7", "Q!777777", "", "Some detail",
         "", "on", "",
         "", "1"),
        # 4 elements
        ("1", "test_user", "Q!111111", "Q!222222", "Some detail",
         "on", "on", "on",
         "", "1"),
        ("2", "test_user", "Q!222222", "Q!111111", "Some detail",
         "", "", "on",
         "", "2"),
        ("6", "test_user", "Q!666666", "Q!111111", "Some detail",
         "", "", "on",
         "", "1"),
        ("2", "user2", "Q!222222", "Q!111111", "Some detail",
         "on", "", "on",
         "", "1"),
        ("7", "user7", "Q!777777", "Q!111111", "Some detail",
         "", "on", "",
         "validemail@gmail.com", "1"),
        # 5 elements
        ("2", "test_user", "Q!222222", "Q!111111", "Some detail",
         "on", "", "on",
         "", "2"),
        ("4", "test_user", "Q!444444", "Q!111111", "Some detail",
         "on", "on", "on",
         "", "1"),
        ("7", "test_user", "Q!777777", "Q!111111", "Some detail",
         "", "on", "",
         "validemail@gmail.com", "1"),
        ("6", "test_user", "Q!666666", "Q!111111", "Some detail",
         "", "on", "on",
         "", "1"),
))
def test_edit_user(
        client: FlaskClient, admin_logged_in: User,
        user_id, new_name, orig_password, new_password, new_details,
        new_check_inv, new_admin, new_in_use,
        new_email, new_sat_group):
    """Test user editing"""
    with dbSession() as db_session:
        user = db_session.get(User, user_id)
        orig_in_use = user.in_use
        orig_name = user.name
        orig_details = user.details
        orig_email = user.email
        orig_done_inv = user.done_inv
        orig_admin = user.admin
        orig_reg_req = user.reg_req
        orig_sat_group = user.sat_group
        if user.id in cleaning_sch.current_order():
            orig_clean_order = str(cleaning_sch.current_order().index(user.id))
        else:
            orig_clean_order = ""
        with client:
            client.get("/")
            assert session["user_name"] == admin_logged_in.name
            assert session["admin"]
            response = client.get(url_for("sch.schedules"))
            if user.reg_req or not user.in_use:
                assert user.name not in response.text
            else:
                assert user.name in response.text
            client.get(url_for("main.index"))
            response = client.get(
                url_for("users.edit_user", username=user.name))
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
                "clean_order": orig_clean_order,
                "submit": True,
            }
            response = client.post(
                url_for("users.edit_user", username=orig_name),
                data=data,
                follow_redirects=True)
            assert len(response.history) == 1
            assert response.history[0].status_code == 302
            assert response.status_code == 200
            assert response.request.path == url_for("main.index")
            assert "User updated" in response.text
            assert new_name in response.text
            db_session.refresh(user)
            response = client.get(url_for("sch.schedules"))
            if user.reg_req or not user.in_use:
                assert user.name not in response.text
            else:
                assert user.name in response.text

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
        cleaning_sch.unregister()
        cleaning_sch.register()


@pytest.mark.parametrize(
    ("user_id", "new_name", "new_password", "new_check_inv", "new_admin",
     "new_email", "new_sat_group",
     "flash_message"), (
        # name
        ("4", "", "", "", "",
         "", "1",
         str(Message.User.Name.Req())),
        ("3", "us", "", "", "",
         "", "1",
         f"Username must be between {Constant.User.Name.min_length} and " +
         f"{Constant.User.Name.max_length} characters!"),
        ("2", "useruseruseruser", "", "", "on",
         "", "1",
         f"Username must be between {Constant.User.Name.min_length} and " +
         f"{Constant.User.Name.max_length} characters!"),
        ("2", "new_user", "Q!1", "", "on",
         "", "1",
         ("Password should have at least " +
          f"{Constant.User.Password.min_length} characters!")),
        # password
        ("3", "new_user", "aaaaaaaa", "", "",
         "", "1",
         "Password must have 1 big letter, 1 number, 1 special char (" +
         f"{Constant.User.Password.symbols})!"),
        ("4", "new_user", "#1aaaaaa", "", "",
         "", "1",
         "Password must have 1 big letter, 1 number, 1 special char (" +
         f"{Constant.User.Password.symbols})!"),
        ("3", "new_user", "#Aaaaaaa", "", "",
         "", "1",
         "Password must have 1 big letter, 1 number, 1 special char (" +
         f"{Constant.User.Password.symbols})!"),
        ("1", "new_user", "1Aaaaaaa", "", "on",
         "", "1",
         "Password must have 1 big letter, 1 number, 1 special char (" +
         f"{Constant.User.Password.symbols})!"),
        # email
        ("1", "new_user", "Q!111112", "", "on",
         "plainaddress", "1",
         "Invalid email adress"),
        ("2", "new_user", "Q!111112", "", "on",
         "#@%^%#$@#$@#.com", "1",
         "Invalid email adress"),
        ("3", "new_user", "Q!111112", "", "",
         "@example.com", "1",
         "Invalid email adress"),
        ("4", "new_user", "Q!111112", "", "",
         "Joe Smith <email@example.com>", "1",
         "Invalid email adress"),
        ("1", "new_user", "Q!111112", "", "on",
         "email@example@example.com", "1",
         "Invalid email adress"),
        ("3", "new_user", "Q!111112", "", "",
         "email@-example.com", "1",
         "Invalid email adress"),
        # sat_group
        ("2", "new_user", "Q!111112", "", "on",
         "email@-example.com", "",
         "Invalid Choice: could not coerce"),
        ("4", "new_user", "Q!111112", "", "",
         "email@-example.com", "3",
         "Not a valid choice"),
        ("1", "new_user", "Q!111112", "", "on",
         "email@-example.com", "a",
         "Invalid Choice: could not coerce"),
))
def test_failed_edit_user_form_validators(
        client: FlaskClient, admin_logged_in: User,
        user_id, new_name, new_password, new_check_inv, new_admin,
        new_email, new_sat_group, flash_message):
    """test_failed_edit_user_form_validators"""
    with dbSession() as db_session:
        user = db_session.get(User, user_id)
        orig_name = user.name
        orig_done_inv = user.done_inv
        orig_admin = user.admin
        orig_in_use = user.in_use
        orig_sat_group = user.sat_group
        if user.id in cleaning_sch.current_order():
            orig_clean_order = str(cleaning_sch.current_order().index(user.id))
        else:
            orig_clean_order = ""
        with client:
            client.get("/")
            assert session["user_name"] == admin_logged_in.name
            assert session["admin"]
            response = client.get(url_for("users.edit_user",
                                          username=orig_name))
            assert user.name in response.text
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
                "clean_order": orig_clean_order,
                "submit": True,
            }
            response = client.post(
                url_for("users.edit_user", username=orig_name),
                data=data,
                follow_redirects=True)
            assert len(response.history) == 0
            assert response.status_code == 200
            assert "User updated" not in response.text
            assert orig_name in response.text
            assert flash_message in unescape(response.text)
        db_session.refresh(user)
        assert user.name != new_name
        assert not check_password_hash(user.password, new_password)
        assert user.done_inv == orig_done_inv
        assert user.admin == orig_admin
        assert user.in_use == orig_in_use
        assert user.sat_group == orig_sat_group


def test_failed_edit_user_name_duplicate(
        client: FlaskClient, admin_logged_in: User):
    """test_failed_edit_user_name_duplicate"""
    with dbSession() as db_session:
        user = db_session.get(User, 2)
        orig_name = user.name
        new_name = db_session.get(User, 0).name
        if user.id in cleaning_sch.current_order():
            orig_clean_order = str(cleaning_sch.current_order().index(user.id))
        else:
            orig_clean_order = ""
        with client:
            client.get("/")
            assert session["user_name"] == admin_logged_in.name
            assert session["admin"]
            client.get(url_for("sch.schedules"))
            response = client.get(url_for("users.edit_user",
                                          username=orig_name))
            assert user.name in response.text
            data = {
                "csrf_token": g.csrf_token,
                "name": new_name,
                "password": "",
                "details": user.details,
                "email": user.email,
                "admin": "on",
                "in_use": "on",
                "sat_group": user.sat_group,
                "clean_order": orig_clean_order,
                "submit": True,
            }
            response = client.post(
                url_for("users.edit_user", username=orig_name),
                data=data,
                follow_redirects=True)
            assert len(response.history) == 0
            assert response.status_code == 200
            assert "User updated" not in response.text
            assert orig_name in response.text
            assert str(Message.User.Name.Exists(new_name)) in response.text
        db_session.refresh(user)
        assert user.name != new_name


@pytest.mark.parametrize(
    ("user_id", "new_check_inv", "new_admin", "new_in_use",
     "flash_message"), (
        ("7", "on", "", "on",
         "User without products attached can't check inventory"),
        ("6", "on", "", "",
         "'Retired' user can't check inventory"),
        ("5", "on", "", "on",
         "User with pending registration can't check inventory"),
        ("5", "", "on", "on",
         "User with pending registration can't be admin"),
        ("3", "", "", "",
         "Can't 'retire' a user if he is still responsible for products"),
))
def test_failed_edit_user_db_validators(
        client: FlaskClient, admin_logged_in: User,
        user_id, new_check_inv, new_admin, new_in_use, flash_message):
    """test_failed_edit_user_db_validators"""
    with dbSession() as db_session:
        user = db_session.get(User, user_id)
        orig_done_inv = user.done_inv
        orig_admin = user.admin
        orig_in_use = user.in_use
        if user.id in cleaning_sch.current_order():
            orig_clean_order = str(cleaning_sch.current_order().index(user.id))
        else:
            orig_clean_order = ""
        with client:
            client.get("/")
            assert session["user_name"] == admin_logged_in.name
            assert session["admin"]
            response = client.get(url_for("users.edit_user",
                                          username=user.name))
            assert user.name in response.text
            data = {
                "csrf_token": g.csrf_token,
                "name": user.name,
                "password": "",
                "details": user.details,
                "email": user.email,
                "check_inv": new_check_inv,
                "admin": new_admin,
                "in_use": new_in_use,
                "sat_group": user.sat_group,
                "clean_order": orig_clean_order,
                "submit": True,
            }
            response = client.post(
                url_for("users.edit_user", username=user.name),
                data=data,
                follow_redirects=True)
            assert len(response.history) == 0
            assert response.status_code == 200
            assert "User updated" not in response.text
            assert user.name in response.text
            assert flash_message in unescape(response.text)
        db_session.refresh(user)
        assert user.done_inv == orig_done_inv
        assert user.admin == orig_admin
        assert user.in_use == orig_in_use


def test_failed_edit_user_bad_username(
        client: FlaskClient, admin_logged_in: User):
    """test_failed_edit_user_bad_username"""
    bad_name = "not_existing_user"
    with client:
        client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        response = client.get(
            url_for("users.edit_user", username=bad_name),
            follow_redirects=True)
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("main.index")
        assert str(Message.User.NotExists(bad_name)) in response.text


def test_failed_edit_user_hidden_admin_bad_username(
        client: FlaskClient, admin_logged_in: User):
    """test_failed_edit_user_hidden_admin_bad_username"""
    admin_name = "Admin"
    with client:
        client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        response = client.get(
            url_for("users.edit_user", username=admin_name),
            follow_redirects=True)
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("main.index")
        assert str(Message.User.NotExists(admin_name)) in response.text


def test_edit_user_last_admin(client: FlaskClient, admin_logged_in: User):
    """test_edit_user_last_admin"""
    with dbSession() as db_session:
        db_session.get(User, 2).admin = False
        db_session.commit()
        user = db_session.get(User, admin_logged_in.id)
        if user.id in cleaning_sch.current_order():
            orig_clean_order = str(cleaning_sch.current_order().index(user.id))
        else:
            orig_clean_order = ""
        with client:
            client.get("/")
            assert session["user_name"] == admin_logged_in.name
            assert session["admin"]
            response = client.get(
                url_for("users.edit_user", username=admin_logged_in.name))
            data = {
                    "csrf_token": g.csrf_token,
                    "name": admin_logged_in.name,
                    "password": "",
                    "details": admin_logged_in.details,
                    "email": admin_logged_in.email,
                    "check_inv": "",
                    "admin": "",
                    "in_use": "on",
                    "sat_group": user.sat_group,
                    "clean_order": orig_clean_order,
                    "submit": True,
                }
            response = client.post(
                url_for("users.edit_user", username=admin_logged_in.name),
                data=data, follow_redirects=True)
            assert len(response.history) == 0
            assert response.status_code == 200
            assert "User updated" not in response.text
            assert admin_logged_in.name in response.text
            assert "You are the last admin!" in response.text
        db_session.refresh(user)
        assert user.admin
        db_session.get(User, 2).admin = True
        db_session.commit()


def test_edit_user_change_admin_name(
        client: FlaskClient, admin_logged_in: User):
    """test_edit_user_change_admin_name"""
    old_name = admin_logged_in.name
    new_name = "new_name"
    if admin_logged_in.id in cleaning_sch.current_order():
        orig_clean_order = str(
            cleaning_sch.current_order().index(admin_logged_in.id))
    else:
        orig_clean_order = ""
    with client:
        client.get("/")
        client.get(url_for("users.edit_user", username=old_name))
        data = {
                "csrf_token": g.csrf_token,
                "name": new_name,
                "password": "",
                "details": admin_logged_in.details,
                "email": admin_logged_in.email,
                "check_inv": "",
                "admin": "on",
                "in_use": "on",
                "sat_group": str(admin_logged_in.sat_group),
                "clean_order": orig_clean_order,
                "submit": True,
            }
        response = client.post(
            url_for("users.edit_user", username=old_name),
            data=data,
            follow_redirects=True)
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("main.index")
        assert "User updated" in response.text
        assert new_name in response.text
        assert session.get("user_name") == new_name
        data = {
                "csrf_token": g.csrf_token,
                "name": old_name,
                "password": "",
                "details": admin_logged_in.details,
                "email": admin_logged_in.email,
                "check_inv": "",
                "admin": "on",
                "in_use": "on",
                "sat_group": str(admin_logged_in.sat_group),
                "clean_order": orig_clean_order,
                "submit": True,
            }
        response = client.post(
            url_for("users.edit_user", username=new_name),
            data=data,
            follow_redirects=True)
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("main.index")
        assert "User updated" in response.text
        assert old_name in response.text
        assert session.get("user_name") == old_name


def test_edit_user_change_admin_logged_in_admin_status(
        client: FlaskClient, admin_logged_in: User):
    """test_edit_user_change_admin_logged_in_admin_status"""
    username = admin_logged_in.name
    if admin_logged_in.id in cleaning_sch.current_order():
        orig_clean_order = str(
            cleaning_sch.current_order().index(admin_logged_in.id))
    else:
        orig_clean_order = ""
    with client:
        client.get("/")
        client.get(url_for("users.edit_user", username=username))
        data = {
                "csrf_token": g.csrf_token,
                "name": username,
                "password": "",
                "details": admin_logged_in.details,
                "email": admin_logged_in.email,
                "check_inv": "",
                "admin": "",
                "in_use": "on",
                "sat_group": str(admin_logged_in.sat_group),
                "clean_order": orig_clean_order,
                "submit": True,
            }
        response = client.post(
            url_for("users.edit_user", username=username),
            data=data,
            follow_redirects=True)
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("main.index")
        assert "User updated" in response.text
        assert username in response.text
        assert "Admin dashboard" not in response.text
        assert not session.get("admin")
    with dbSession() as db_session:
        assert not db_session.get(User, 1).admin
        db_session.get(User, 1).admin = True
        db_session.commit()


@pytest.mark.parametrize(
    ("name", "order"), (
        ("user1", 0),
        ("user2", 1),
        ("user3", 2),
        ("user4", 3),
        ("user5", None),
        ("user6", None),
        ("user7", 4),
))
def test_edit_user_clean_order_choices(
        client: FlaskClient, admin_logged_in: User,
        name, order):
    """test_edit_user_clean_order_choices"""
    with client:
        client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        assert cleaning_sch.current_order() == [1, 2, 3, 4, 7]
        response = client.get(
            url_for("users.edit_user", username=name))
    if order is not None:
        assert cleaning_sch.name in response.text
        assert 'value="0">This week</option>' in response.text
        assert 'value="1">In 1 week</option>' in response.text
        assert 'value="2">In 2 weeks</option>' in response.text
        assert 'value="3">In 3 weeks</option>' in response.text
        assert 'value="4">In 4 weeks</option>' in response.text
        assert f'<option selected value="{order}">' in response.text
    else:
        assert cleaning_sch.name not in response.text
        assert 'value="0">This week</option>' not in response.text
        assert 'value="1">In 1 week</option>' not in response.text
        assert 'value="2">In 2 weeks</option>' not in response.text
        assert 'value="3">In 3 weeks</option>' not in response.text
        assert 'value="4">In 4 weeks</option>' not in response.text


def test_edit_user_clean_order(client: FlaskClient, admin_logged_in: User):
    """test_edit_user_clean_order"""
    with client:
        client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        assert cleaning_sch.current_order() == [1, 2, 3, 4, 7]

        with dbSession() as db_session:
            user = db_session.get(User, 1)
        response = client.get(
            url_for("users.edit_user", username=user.name))
        assert user.name in response.text
        data = {
            "csrf_token": g.csrf_token,
            "name": user.name,
            "details": user.details,
            "email": user.email,
            "check_inv": user.check_inv,
            "admin": user.admin,
            "in_use": user.in_use,
            "sat_group": user.sat_group,
            "clean_order": "2",
            "submit": True,
            }
        response = client.post(
            url_for("users.edit_user", username=user.name),
            data=data,
            follow_redirects=True)
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("main.index")
        assert "Schedule updated" in response.text
        assert "User updated" not in response.text
        assert cleaning_sch.current_order() == [2, 3, 1, 4, 7]

        assert session["admin"]
        with dbSession() as db_session:
            user = db_session.get(User, 4)
        response = client.get(
            url_for("users.edit_user", username=user.name))
        assert user.name in response.text
        data = {
            "csrf_token": g.csrf_token,
            "name": user.name,
            "details": user.details,
            "email": user.email,
            "check_inv": user.check_inv,
            "admin": user.admin,
            "in_use": user.in_use,
            "sat_group": user.sat_group,
            "clean_order": "4",
            "submit": True,
            }
        response = client.post(
            url_for("users.edit_user", username=user.name),
            data=data,
            follow_redirects=True)
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("main.index")
        assert "Schedule updated" in response.text
        assert "User updated" not in response.text
        assert cleaning_sch.current_order() == [2, 3, 1, 7, 4]

        assert session["admin"]
        with dbSession() as db_session:
            user = db_session.get(User, 7)
        response = client.get(
            url_for("users.edit_user", username=user.name))
        assert user.name in response.text
        data = {
            "csrf_token": g.csrf_token,
            "name": user.name,
            "details": user.details,
            "email": user.email,
            "check_inv": user.check_inv,
            "admin": user.admin,
            "in_use": user.in_use,
            "sat_group": user.sat_group,
            "clean_order": "0",
            "submit": True,
            }
        response = client.post(
            url_for("users.edit_user", username=user.name),
            data=data,
            follow_redirects=True)
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("main.index")
        assert "Schedule updated" in response.text
        assert "User updated" not in response.text
        assert cleaning_sch.current_order() == [7, 2, 3, 1, 4]
        # teardown
        cleaning_sch.unregister()
        cleaning_sch.register()


@pytest.mark.parametrize(
        ("user_id", "clean_order", "flash_err"), (
            (1, "", "Not a valid choice"),
            (2, " ", "Not a valid choice"),
            (3, None, "Not a valid choice"),
            (4, "-2", "Not a valid choice"),
            (2, "5", "Not a valid choice"),
))
def test_failed_edit_user_clean_order(
        client: FlaskClient, admin_logged_in: User,
        user_id, clean_order, flash_err):
    """test_failed_edit_user_clean_order"""
    with client:
        client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        assert cleaning_sch.current_order() == [1, 2, 3, 4, 7]

        with dbSession() as db_session:
            user = db_session.get(User, user_id)
        response = client.get(
            url_for("users.edit_user", username=user.name))
        assert user.name in response.text
        data = {
            "csrf_token": g.csrf_token,
            "name": user.name,
            "details": user.details,
            "email": user.email,
            "check_inv": user.check_inv,
            "admin": user.admin,
            "in_use": user.in_use,
            "sat_group": user.sat_group,
            "clean_order": clean_order,
            "submit": True,
            }
        response = client.post(
            url_for("users.edit_user", username=user.name),
            data=data,
            follow_redirects=True)
        assert "Schedule updated" not in response.text
        assert "User updated" not in response.text
        assert flash_err in unescape(response.text)
        assert cleaning_sch.current_order() == [1, 2, 3, 4, 7]
# endregion


# region: delete user
def test_delete_user(
        client: FlaskClient, admin_logged_in: User, caplog: LogCaptureFixture):
    """test_delete_user"""
    with dbSession() as db_session:
        user = User(name="new_user", password="Q!111111", reg_req=False)
        db_session.add(user)
        db_session.commit()
        cleaning_sch.add_user(user.id)
        assert f"Schedule '{cleaning_sch.name}' added '{user.name}'" \
            in caplog.messages
    with client:
        client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        response = client.get(url_for("sch.schedules"))
        assert user.name in response.text
        response = client.get(url_for("users.edit_user", username=user.name))
        assert user.name in response.text
        data = {
            "csrf_token": g.csrf_token,
            "name": user.name,
            "delete": True,
        }
        response = client.post(
            url_for("users.edit_user", username=user.name),
            data=data,
            follow_redirects=True)
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("sch.schedules")
        assert f"User '{user.name}' has been deleted" \
            in unescape(response.text)
        response = client.get(url_for("sch.schedules"))
        assert user.name not in response.text
        assert (f"Schedule '{cleaning_sch.name}' removed user with id " +
                f"'{user.id}'") in caplog.messages
    with dbSession() as db_session:
        assert not db_session.get(User, user.id)


def test_delete_user_admin_log_out(
        client: FlaskClient, caplog: LogCaptureFixture):
    """test_delete_user_admin_log_out"""
    with dbSession() as db_session:
        user = User(
            name="new_user",
            password="Q!111111",
            admin=True,
            reg_req=False)
        db_session.add(user)
        db_session.commit()
        cleaning_sch.add_user(user.id)
        assert user.id
    with client:
        client.get("/")
        client.get(url_for("auth.login"))
        data = {
            "csrf_token": g.csrf_token,
            "name": user.name,
            "password": "Q!111111"}
        client.post(url_for("auth.login"), data=data)
        response = client.get(url_for("users.edit_user", username=user.name))
        assert user.name in response.text
        data = {
            "csrf_token": g.csrf_token,
            "name": user.name,
            "delete": True,
        }
        response = client.post(
            url_for("users.edit_user", username=user.name),
            data=data,
            follow_redirects=True)
        assert len(response.history) == 2
        assert response.history[0].status_code == 302
        assert response.history[1].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("auth.login")
        assert (f"Schedule '{cleaning_sch.name}' removed user with id " +
                f"'{user.id}'") in caplog.messages
        assert str(Message.User.Logout()) in response.text


@pytest.mark.parametrize(("user_id", ), (
    ("1",),
    ("2",),
    ("3",),
    ("4",),
))
def test_failed_delete_user(
        client: FlaskClient, admin_logged_in: User,
        user_id):
    """test_failed_delete_user"""
    with dbSession() as db_session:
        user = db_session.get(User, user_id)
    with client:
        client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        response = client.get(url_for("users.edit_user", username=user.name))
        assert user.name in response.text
        data = {
            "csrf_token": g.csrf_token,
            "name": user.name,
            "delete": True,
        }
        response = client.post(
            url_for("users.edit_user", username=user.name),
            data=data,
            follow_redirects=True)
        assert len(response.history) == 0
        assert response.status_code == 200
        assert "Can't delete user! He is still responsible for some products" \
              in unescape(response.text)
    with dbSession() as db_session:
        assert db_session.get(User, user.id)
# endregion
