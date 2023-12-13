"""Users blueprint tests."""

import random
import re
import string
from html import unescape

import pytest
from flask import g, session, url_for
from flask.testing import FlaskClient
from hypothesis import assume, example, given
from hypothesis import strategies as st
from pytest import LogCaptureFixture
from sqlalchemy import select
from werkzeug.security import check_password_hash

from blueprints.sch.sch import cleaning_sch, saturday_sch
from constants import Constant
from database import User, dbSession
from messages import Message
from tests import InvalidUser, ValidUser, redirected_to, test_users

pytestmark = pytest.mark.users


# region: approve registration
@given(user = st.sampled_from([user for user in test_users if user["reg_req"]]))
def test_approve_registration(
        client: FlaskClient, admin_logged_in: User, caplog: LogCaptureFixture,
        user: dict[str]):
    """Successfully approve registration"""
    with client:
        response = client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        approve_reg_link = re.compile(
            r'<a.*link-danger.*href="' +
            url_for("users.approve_reg", username=user["name"]) +
            r'">requested registration</a>',
            re.S)
        assert approve_reg_link.search(response.text)
        response = client.get(url_for("sch.schedules"))
        assert user["name"] not in response.text
        client.get(url_for("main.index"))
        # approve registration
        response = client.get(
            url_for("users.approve_reg", username=user["name"]),
            follow_redirects=True)
        assert redirected_to(url_for("main.index"), response)
        assert not approve_reg_link.search(response.text)
        assert str(Message.User.Approved(user["name"])) in response.text
        assert str(Message.Schedule.Review()) in response.text
        response = client.get(url_for("sch.schedules"))
    assert user["name"] in response.text
    assert f"Schedule '{cleaning_sch.name}' added '{user['name']}'" \
        in caplog.messages
    with dbSession() as db_session:
        assert not db_session.get(User, user["id"]).reg_req
        # teardown
        db_session.get(User, user["id"]).reg_req = True
        db_session.commit()
        cleaning_sch.remove_user(user["id"])


def test_failed_approve_registration_bad_username(
        client: FlaskClient, admin_logged_in: User):
    """test_failed_approve_registration_bad_username"""
    ne_user = "not_existing_user"
    with client:
        response = client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        response = client.get(
            url_for("users.approve_reg", username=ne_user),
            follow_redirects=True)
        assert redirected_to(url_for("main.index"), response)
        assert str(Message.User.NotExists(ne_user)) in response.text


def test_failed_approve_registration_user_logged_in(
        client: FlaskClient, user_logged_in: User):
    """test_failed_approve_registration_user_logged_in"""
    user = [user for user in test_users if user["reg_req"]][0]
    with client:
        response = client.get("/")
        assert session["user_name"] == user_logged_in.name
        assert not session["admin"]
        response = client.get(
            url_for("users.approve_reg", username=user["name"]),
            follow_redirects=True)
        assert redirected_to(url_for("auth.login"), response)
        assert str(Message.UI.Auth.AdminReq()) in response.text
        assert session.get("user_id")
        with dbSession() as db_session:
            assert db_session.get(User, user["id"]).reg_req
# endregion


# region: approve check inventory
@given(user = st.sampled_from([user for user in test_users
                               if user["has_products"] and not user["admin"]]))
def test_approve_check_inventory(
        client: FlaskClient, admin_logged_in: User, user: dict[str]):
    """test_approve_check_inventory"""
    with dbSession() as db_session:
        db_session.get(User, user["id"]).req_inv = True
        db_session.commit()
    with client:
        response = client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        approve_inv_link = re.compile(
            r'<a.*link-warning.*href="' +
            url_for("users.approve_check_inv", username=user["name"]) +
            r'">requested inventory</a>',
            re.S)
        check_inv_link = re.compile(
            r'<a.*link-info.*href="' +
            url_for("inv.inventory_user", username=user["name"]) +
            r'">check inventory</a>',
            re.S)
        assert approve_inv_link.search(response.text)
        assert not check_inv_link.search(response.text)
        # approve inventorying
        response = client.get(
            url_for("users.approve_check_inv", username=user["name"]),
            follow_redirects=True)
        assert redirected_to(url_for("main.index"), response)
        assert not approve_inv_link.search(response.text)
        assert check_inv_link.search(response.text)
    with dbSession() as db_session:
        db_user = db_session.get(User, user["id"])
        assert not db_user.done_inv
        assert not db_user.req_inv
        db_user.done_inv = True
        db_session.commit()


@given(user = st.one_of(
        st.sampled_from(
            [user for user in test_users if not user["has_products"]]),
        st.dictionaries(keys=st.just("name"),
                        values=st.text(min_size=1,
                                       alphabet=string.ascii_letters),
                        min_size=1)
))
@example(user = [user for user in test_users if not user["in_use"]][0])
@example(user = [user for user in test_users if user["reg_req"]][0])
@example(user = [user for user in test_users
                 if user["active"] and not user["has_products"]][0])
@example(user = {"name": "x"})
def test_failed_approve_check_inventory(
        client: FlaskClient, caplog: LogCaptureFixture, admin_logged_in: User,
        user: dict[str]):
    """test_failed_approve_check_inventory"""
    db_check = True
    if not user.get("in_use", True):
        flash_message = str(Message.User.DoneInv.Retired())
    elif user.get("reg_req", False):
        flash_message = str(Message.User.DoneInv.PendReg())
    elif not user.get("has_products", True):
        flash_message = str(Message.User.DoneInv.NoProd())
    else:
        flash_message = str(Message.User.NotExists(user["name"]))
        db_check = False
    with client:
        response = client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        response = client.get(
            url_for("users.approve_check_inv", username=user["name"]),
            follow_redirects=True)
        assert redirected_to(url_for("main.index"), response)
        assert flash_message in unescape(response.text)
        assert "User inventory check approval error(s)" in caplog.messages
    if db_check:
        with dbSession() as db_session:
            assert db_session.get(User, user["id"]).done_inv


def test_failed_approve_check_inventory_user_logged_in(
        client: FlaskClient, user_logged_in: User):
    """test_failed_approve_check_inventory_user_logged_in"""
    with dbSession() as db_session:
        user = db_session.get(User, user_logged_in.id)
        user.req_inv = True
        db_session.commit()
        with client:
            response = client.get("/")
            assert not session["admin"]
            assert url_for("users.approve_check_inv", username=user.name) \
                not in response.text
            response = client.get(
                url_for("users.approve_check_inv", username=user.name),
                follow_redirects=True)
            assert redirected_to(url_for("auth.login"), response)
            assert str(Message.UI.Auth.AdminReq()) in response.text
            assert session.get("user_id")
        db_session.refresh(user)
        assert user.done_inv
        assert user.req_inv
        user.req_inv = False
        db_session.commit()


def test_approve_all_check_inventory(
        client: FlaskClient, admin_logged_in: User):
    """test_approve_all_check_inventory"""
    def check_inv_link(username: str) -> re.Pattern:
        """Create regex check inventory link pattern from username."""
        return re.compile(
            r'<a.*link-info.*href="' +
            url_for("inv.inventory_user", username=username) +
            r'">check inventory</a>',
            re.S)
    # random user that requests inventorying
    user = random.choice([user for user in test_users
                          if user["has_products"] and not user["admin"]])
    with dbSession() as db_session:
        db_session.get(User, user["id"]).req_inv = True
        db_session.commit()
    with client:
        response = client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        approve_inv_link = re.compile(
            r'<a.*link-warning.*href="' +
            url_for("users.approve_check_inv", username=user["name"]) +
            r'">requested inventory</a>',
            re.S)
        assert approve_inv_link.search(response.text)
        assert not re.search(check_inv_link(user["name"]), response.text)
        # approve inventorying for all
        response = client.get(
            url_for("users.approve_check_inv_all"), follow_redirects=True)
        assert redirected_to(url_for("main.index"), response)
        assert not approve_inv_link.search(response.text)
        for user in [user for user in test_users if user["has_products"]]:
            assert re.search(check_inv_link(user["name"]), response.text)
    # db check and teardown
    with dbSession() as db_session:
        for user in [user for user in test_users if user["has_products"]]:
            db_user =  db_session.get(User, user["id"])
            assert not db_user.done_inv
            assert not db_user.req_inv
            db_user.done_inv = True
        db_session.commit()
# endregion


# region: new user
create_user_button = re.compile(
        r'<input.*type="submit".*value="Create user">')


@pytest.mark.slow
@given(name = st.text(min_size=Constant.User.Name.min_length,
                      max_size=Constant.User.Name.max_length)
            .map(lambda x: x.strip())
            .filter(lambda x: len(x) > Constant.User.Name.min_length)
            .filter(lambda x: x not in [user["name"] for user in test_users]),
       password = st.from_regex(Constant.User.Password.regex, fullmatch=True),
       email = st.one_of(st.text(max_size=0),
                         st.emails()),
       sat_group = st.sampled_from(["1", "2"]),
       details = st.text(),
       admin = st.booleans())
@example(name = ValidUser.name,
         password = ValidUser.password,
         email = ValidUser.email,
         sat_group = ValidUser.sat_group,
         details = ValidUser.details,
         admin = ValidUser.admin)
def test_new_user(
        client: FlaskClient,
        admin_logged_in: User,
        caplog: LogCaptureFixture,
        name: str,
        password: str,
        email: str,
        sat_group: str,
        details: str,
        admin: bool):
    """Successfully create a new user"""
    with client:
        client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        response = client.get(url_for("users.new_user"))
        assert create_user_button.search(response.text)
        data = {
            "csrf_token": g.csrf_token,
            "name": name,
            "password": password,
            "email": email,
            "sat_group": sat_group,
            "details": details,
            "admin": admin,
            }
        response = client.post(
            url_for("users.new_user"), data=data, follow_redirects=True)
        assert redirected_to(url_for("main.index"), response)
        assert str(Message.User.Created(name)) in unescape(response.text)
        assert str(Message.Schedule.Review()) in response.text
        assert name in response.text
        assert f"User '{name}' created" in caplog.messages
        assert f"Schedule '{cleaning_sch.name}' added '{name}'" \
            in caplog.messages
        response = client.get(url_for("sch.schedules"))
        assert name in unescape(response.text)
    # db check and teardown
    with dbSession() as db_session:
        db_user = db_session.scalar(select(User).filter_by(name=name))
        assert check_password_hash(db_user.password, password)
        assert db_user.admin == admin
        assert db_user.in_use
        assert db_user.done_inv
        assert not db_user.reg_req
        assert not db_user.req_inv
        assert db_user.details == details
        assert db_user.email == email
        assert db_user.sat_group == int(sat_group)
        db_session.delete(db_user)
        db_session.commit()
        cleaning_sch.remove_user(db_user.id)


# region: failed user creation
def _test_failed_new_user(
        request: pytest.FixtureRequest,
        flash_message: str,
        name: str = ValidUser.name,
        password: str = ValidUser.password,
        email: str = ValidUser.email,
        sat_group: str = ValidUser.sat_group,
        db_check: bool = True):
    """Common logic for failed creation of a new user"""
    client: FlaskClient = request.getfixturevalue("client")
    admin_logged_in: User = request.getfixturevalue("admin_logged_in")
    with client:
        client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        response = client.get(url_for("users.new_user"))
        assert create_user_button.search(response.text)
        data = {
            "csrf_token": g.csrf_token,
            "name": name,
            "password": password,
            "email": email,
            "sat_group": sat_group,
            "details": ValidUser.details,
            "admin": ValidUser.admin,
            }
        response = client.post(
            url_for("users.new_user"), data=data)
        assert response.status_code == 200
        assert create_user_button.search(response.text)
        assert flash_message in unescape(response.text)
        assert str(Message.User.Created(name)) not in unescape(response.text)
    if db_check:
        with dbSession() as db_session:
            assert not db_session.scalar(select(User).filter_by(name=name))


@given(name = st.one_of(
        st.text(max_size=Constant.User.Name.min_length - 1)
            .map(lambda x: x.strip()),
        st.text(min_size=Constant.User.Name.max_length + 1)
            .map(lambda x: x.strip())
            .filter(lambda x: len(x) > Constant.User.Name.max_length)
))
@example(name = "")
@example(name = InvalidUser.short_name)
@example(name = InvalidUser.long_name)
def test_failed_new_user_invalid_name(request, name):
    """test_failed_new_user_invalid_name"""
    if name:
        flash_message = str(Message.User.Name.LenLimit())
    else:
        flash_message = str(Message.User.Name.Required())
    _test_failed_new_user(
        request=request,
        flash_message=flash_message,
        name=name
    )


@given(name = st.sampled_from([user["name"] for user in test_users]))
@example(name = [user["name"] for user in test_users][0])
def test_failed_new_user_duplicate_name(request, name):
    """test_failed_new_user_duplicate_name"""
    flash_message = str(Message.User.Name.Exists(name))
    _test_failed_new_user(
        request=request,
        flash_message=flash_message,
        name=name,
        db_check=False
    )


@given(password = st.text(max_size=Constant.User.Password.min_length - 1))
@example(password = "")
@example(password = InvalidUser.short_password)
@example(password = InvalidUser.only_lowercase_password)
@example(password = InvalidUser.no_special_char_password)
@example(password = InvalidUser.no_uppercase_password)
@example(password = InvalidUser.no_number_password)
def test_failed_new_user_invalid_password(request, password):
    """Invalid password - thoroughly tested in auth tests"""
    assume(not Constant.User.Password.regex.search(password))
    if not password:
        flash_message = str(Message.User.Password.Required())
    elif len(password) < Constant.User.Password.min_length:
        flash_message = str(Message.User.Password.LenLimit())
    else:
        flash_message = str(Message.User.Password.Rules())
    _test_failed_new_user(
        request=request,
        flash_message=flash_message,
        password=password
    )


@pytest.mark.parametrize("email", [
    pytest.param("plain_address", id="Plain email address"),
    pytest.param("#@%^%#$@#$@#.com", id="Invalid chars"),
    pytest.param("@example.com", id="No local part"),
    pytest.param("Joe Smith <email@example.com>", id="Including name"),
    pytest.param("email@example@example.com", id="Multiple @"),
    pytest.param("email@-example.com", id="Invalid chars in domain part"),
])
def test_failed_new_user_invalid_email(request, email):
    """Invalid email - thoroughly tested in auth tests"""
    flash_message = str(Message.User.Email.Invalid())
    _test_failed_new_user(
        request=request,
        flash_message=flash_message,
        email=email
    )


@given(sat_group = st.one_of(
        st.integers().filter(lambda x: x not in {1, 2}),
        st.text(alphabet=string.ascii_letters)))
@example(sat_group = saturday_sch.num_groups + 1)
@example(sat_group = "a")
def test_failed_new_user_invalid_sat_group(request, sat_group):
    """test_failed_new_user_invalid_sat_group"""
    if isinstance(sat_group, int):
        flash_message = str(Message.User.SatGroup.Invalid())
    else:
        flash_message = "Invalid Choice: could not coerce"
    _test_failed_new_user(
        request=request,
        flash_message=flash_message,
        sat_group=sat_group
    )
# endregion
# endregion


# region: edit user
update_user_button = re.compile(r'<input.*type="submit".*value="Update">')
delete_user_button = re.compile(r'<input.*type="submit".*value="Delete">')


@pytest.mark.slow
@given(user = st.sampled_from([user for user in test_users
                               if user["name"] != "Admin"]),
       new_name = st.text(min_size=Constant.User.Name.min_length,
                          max_size=Constant.User.Name.max_length)
            .map(lambda x: x.strip())
            .filter(lambda x: len(x) > Constant.User.Name.min_length)
            .filter(lambda x: x not in [user["name"] for user in test_users]),
       new_password = st.one_of(
            st.just(""),
            st.from_regex(Constant.User.Password.regex, fullmatch=True)),
       new_email = st.one_of(
            st.just(""),
            st.emails()),
       new_details = st.one_of(
            st.just(""),
            st.text()),
       new_sat_group = st.sampled_from(["1", "2"]),
       new_check_inv = st.booleans(),
       new_admin = st.booleans(),
       new_in_use = st.booleans())
@example(user = [user for user in test_users if user["has_products"]][0],
       new_name = ValidUser.name,
       new_password = "",
       new_email = "",
       new_details = "",
       new_sat_group = ValidUser.sat_group,
       new_check_inv = True,
       new_admin = True,
       new_in_use = True)
@example(user = [user for user in test_users
                 if not user["has_products"] and user["active"]][0],
       new_name = ValidUser.name,
       new_password = "",
       new_email = "",
       new_details = "",
       new_sat_group = ValidUser.sat_group,
       new_check_inv = False,
       new_admin = False,
       new_in_use = False)
def test_edit_user(
        client: FlaskClient,
        hidden_admin_logged_in: User,
        user: dict[str],
        new_name: str,
        new_password: str,
        new_email: str,
        new_details: str,
        new_sat_group: str,
        new_check_inv: bool,
        new_admin: bool,
        new_in_use: bool,
    ):
    """Successfully user edit"""
    # prechecks
    if new_check_inv:
        assume(user["has_products"])
    if new_admin:
        assume(not user["reg_req"])
    if not new_in_use:
        assume(not user["has_products"])
    # edit user
    with client:
        client.get("/")
        assert session["user_name"] == hidden_admin_logged_in.name
        assert session["admin"]
        response = client.get(
            url_for("users.edit_user", username=user["name"]))
        assert response.status_code == 200
        assert update_user_button.search(response.text)
        assert delete_user_button.search(response.text)
        if user["active"]:
            clean_order = str(cleaning_sch.current_order().index(user["id"]))
        else:
            clean_order = ""
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
            "clean_order": clean_order,
        }
        response = client.post(
            url_for("users.edit_user", username=user["name"]),
            data=data,
            follow_redirects=True)
        assert redirected_to(url_for("main.index"), response)
    assert str(Message.User.Updated(new_name)) in unescape(response.text)
    assert new_name in unescape(response.text)
    # db check and teardown
    with dbSession() as db_session:
        db_user = db_session.get(User, user["id"])
        assert db_user.name == new_name
        db_user.name = user["name"]
        if new_password:
            assert check_password_hash(db_user.password, new_password)
        db_user.password = user["password"]
        assert db_user.email == new_email
        db_user.email = user["email"]
        assert db_user.details == new_details
        db_user.details = user["details"]
        assert db_user.sat_group == int(new_sat_group)
        db_user.sat_group = user["sat_group"]
        assert db_user.done_inv != new_check_inv
        db_user.done_inv = user["done_inv"]
        assert db_user.admin == new_admin
        db_user.admin = user["admin"]
        assert db_user.in_use == new_in_use
        db_user.in_use = user["in_use"]
        db_session.commit()
        db_user.reg_req = user["reg_req"]
        db_session.commit()
    # reinit the individual schedule
    cleaning_sch.unregister()
    cleaning_sch.register()


# region: failed user edit
def _test_failed_edit_user(
    request: pytest.FixtureRequest,
    user: dict[str],
    flash_message: str,
    new_name: str = ValidUser.name,
    new_password: str = ValidUser.password,
    new_email: str = ValidUser.email,
    new_sat_group: str = ValidUser.sat_group,
    new_check_inv: bool = False,
    new_admin: bool = False,
    new_in_use: bool = True):
    """Common logic for failed user edit"""
    client: FlaskClient = request.getfixturevalue("client")
    admin_logged_in: User = request.getfixturevalue("admin_logged_in")
    with client:
        client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        response = client.get(
            url_for("users.edit_user", username=user["name"]))
        assert response.status_code == 200
        assert update_user_button.search(response.text)
        assert delete_user_button.search(response.text)
        if user["active"]:
            clean_order = str(cleaning_sch.current_order().index(user["id"]))
        else:
            clean_order = ""
        data = {
            "csrf_token": g.csrf_token,
            "name": new_name,
            "password": new_password,
            "details": "",
            "email": new_email,
            "check_inv": new_check_inv,
            "admin": new_admin,
            "in_use": new_in_use,
            "sat_group": new_sat_group,
            "clean_order": clean_order,
        }
        response = client.post(
            url_for("users.edit_user", username=user["name"]), data=data)
    assert response.status_code == 200
    assert str(Message.User.Updated(new_name)) not in unescape(response.text)
    assert user["name"] in unescape(response.text)
    assert flash_message in unescape(response.text)
    # db check and teardown
    with dbSession() as db_session:
        db_user = db_session.get(User, user["id"])
        assert db_user.name == user["name"]
        assert check_password_hash(db_user.password, user["password"])
        assert db_user.email == user["email"]
        assert db_user.details == user["details"]
        assert db_user.sat_group == user["sat_group"]
        assert db_user.done_inv == user["done_inv"]
        assert db_user.admin == user["admin"]
        assert db_user.in_use == user["in_use"]
        assert db_user.reg_req == user["reg_req"]
        assert db_user.req_inv == user["req_inv"]


@given(user = st.sampled_from([user for user in test_users
                               if user["name"] != "Admin"]),
       name = st.one_of(
        st.text(max_size=Constant.User.Name.min_length - 1)
            .map(lambda x: x.strip()),
        st.text(min_size=Constant.User.Name.max_length + 1)
            .map(lambda x: x.strip())
            .filter(lambda x: len(x) > Constant.User.Name.max_length),
        st.sampled_from([user["name"] for user in test_users])))
@example(user = [user for user in test_users if user["name"] != "Admin"][0],
         name = "")
@example(user = [user for user in test_users if user["name"] != "Admin"][0],
         name = InvalidUser.short_name)
@example(user = [user for user in test_users if user["name"] != "Admin"][0],
         name = InvalidUser.long_name)
@example(user = [user for user in test_users if user["name"] != "Admin"][0],
         name = [user["name"] for user in test_users][0])
def test_failed_edit_user_invalid_name(request, user: dict[str], name: str):
    """test_failed_new_user_invalid_name"""
    assume(user["name"] != name)
    if name in [user["name"] for user in test_users]:
        flash_message = str(Message.User.Name.Exists(name))
    elif name:
        flash_message = str(Message.User.Name.LenLimit())
    else:
        flash_message = str(Message.User.Name.Required())
    _test_failed_edit_user(
        request=request,
        user=user,
        flash_message=flash_message,
        new_name=name
    )


@given(user = st.sampled_from([user for user in test_users
                               if user["name"] != "Admin"]),
       password = st.text(min_size=1,
                          max_size=Constant.User.Password.min_length - 1))
@example(user = [user for user in test_users if user["name"] != "Admin"][0],
         password = InvalidUser.short_password)
@example(user = [user for user in test_users if user["name"] != "Admin"][0],
         password = InvalidUser.only_lowercase_password)
@example(user = [user for user in test_users if user["name"] != "Admin"][0],
         password = InvalidUser.no_special_char_password)
@example(user = [user for user in test_users if user["name"] != "Admin"][0],
         password = InvalidUser.no_uppercase_password)
@example(user = [user for user in test_users if user["name"] != "Admin"][0],
         password = InvalidUser.no_number_password)
def test_failed_edit_user_invalid_password(
        request, user: dict[str], password: str):
    """test_failed_edit_user_invalid_password"""
    assume(not Constant.User.Password.regex.search(password))
    if len(password) < Constant.User.Password.min_length:
        flash_message = str(Message.User.Password.LenLimit())
    else:
        flash_message = str(Message.User.Password.Rules())
    _test_failed_edit_user(
        request=request,
        user=user,
        flash_message=flash_message,
        new_password=password
    )


@pytest.mark.parametrize("email", [
    pytest.param("plain_address", id="Plain email address"),
    pytest.param("#@%^%#$@#$@#.com", id="Invalid chars"),
    pytest.param("@example.com", id="No local part"),
    pytest.param("Joe Smith <email@example.com>", id="Including name"),
    pytest.param("email@example@example.com", id="Multiple @"),
    pytest.param("email@-example.com", id="Invalid chars in domain part"),
])
def test_failed_edit_user_invalid_email(request, email: str):
    """test_failed_edit_user_invalid_email"""
    user = [user for user in test_users if user["name"] != "Admin"][0]
    flash_message = str(Message.User.Email.Invalid())
    _test_failed_edit_user(
        request=request,
        user=user,
        flash_message=flash_message,
        new_email=email
    )


@given(user = st.sampled_from([user for user in test_users
                               if user["name"] != "Admin"]),
       sat_group = st.one_of(
        st.integers().filter(lambda x: x not in {1, 2}),
        st.text(alphabet=string.ascii_letters)))
@example(user = [user for user in test_users if user["name"] != "Admin"][0],
         sat_group = saturday_sch.num_groups + 1)
@example(user = [user for user in test_users if user["name"] != "Admin"][0],
         sat_group = "a")
def test_failed_edit_user_invalid_sat_group(
        request, user: dict[str], sat_group: str):
    """test_failed_edit_user_invalid_sat_group"""
    if isinstance(sat_group, int):
        flash_message = str(Message.User.SatGroup.Invalid())
    else:
        flash_message = "Invalid Choice: could not coerce"
    _test_failed_edit_user(
        request=request,
        user=user,
        flash_message=flash_message,
        new_sat_group=sat_group
    )


@pytest.mark.parametrize(("user", "flash_message"), [
    pytest.param(
        [user for user in test_users
            if user["name"] != "Admin" and not user["in_use"]][0],
        str(Message.User.DoneInv.Retired()),
        id="Retired user"),
    pytest.param(
        [user for user in test_users
            if user["reg_req"]][0],
        str(Message.User.DoneInv.PendReg()),
        id="User with pending registration"),
    pytest.param(
        [user for user in test_users
            if user["active"] and not user["has_products"]][0],
        str(Message.User.DoneInv.NoProd()),
        id="User without products"),
    ]
)
def test_failed_edit_user_invalid_check_inv(
        request, user: dict[str], flash_message: str):
    """test_failed_edit_user_invalid_sat_group"""
    _test_failed_edit_user(
        request=request,
        user=user,
        flash_message=flash_message,
        new_check_inv=True
    )


@given(user = st.sampled_from([user for user in test_users if user["reg_req"]]))
def test_failed_edit_user_invalid_admin(
        request, user: dict[str]):
    """test_failed_edit_user_invalid_admin"""
    flash_message = str(Message.User.Admin.PendReg())
    _test_failed_edit_user(
        request=request,
        user=user,
        flash_message=flash_message,
        new_admin=True
    )


@given(user = st.sampled_from([user for user in test_users
                               if user["has_products"]]))
def test_failed_edit_user_invalid_in_use(
        request, user: dict[str]):
    """test_failed_edit_user_invalid_in_use"""
    flash_message = str(Message.User.InUse.StillProd())
    _test_failed_edit_user(
        request=request,
        user=user,
        flash_message=flash_message,
        new_in_use=False
    )
# endregion


@pytest.mark.parametrize("name", [
    pytest.param("not_existing_user", id="Non existing user"),
    pytest.param("Admin", id="Hidden admin"),
])
def test_failed_edit_user_bad_username(
        client: FlaskClient, admin_logged_in: User, name: str):
    """Bad or hidden admin name"""
    with client:
        client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        response = client.get(
            url_for("users.edit_user", username=name),
            follow_redirects=True)
        assert redirected_to(url_for("main.index"), response)
        assert str(Message.User.NotExists(name)) in response.text


def test_edit_user_last_admin(client: FlaskClient, admin_logged_in: User):
    """Test error message when there are no more admins"""
    # make all other admins regular users
    admin = [user for user in test_users
             if user["name"] == admin_logged_in.name][0]
    other_admins = [user for user in test_users
                    if user["admin"] and
                    user["in_use"] and
                    user["name"] != admin_logged_in.name]
    with dbSession() as db_session:
        for oth_admin in other_admins:
            db_session.get(User, oth_admin["id"]).admin = False
        db_session.commit()
    # try to change admin attribute
    with client:
        client.get("/")
        response = client.get(
            url_for("users.edit_user", username=admin["name"]))
        orig_clean_order = str(cleaning_sch.current_order().index(admin["id"]))
        data = {
                "csrf_token": g.csrf_token,
                "name": admin["name"],
                "details": admin["details"],
                "email": admin["email"],
                "check_inv": False,
                "admin": False,
                "in_use": True,
                "sat_group": admin["sat_group"],
                "clean_order": orig_clean_order,
            }
        response = client.post(
            url_for("users.edit_user", username=admin["name"]), data=data)
        assert response.status_code == 200
        assert str(Message.User.Updated(admin["name"])) \
            not in unescape(response.text)
        assert update_user_button.search(response.text)
        assert delete_user_button.search(response.text)
        assert str(Message.User.Admin.LastAdmin()) in response.text
    # db check and teardown
    with dbSession() as db_session:
        assert db_session.get(User, admin["id"]).admin
        for oth_admin in other_admins:
            db_session.get(User, oth_admin["id"]).admin = True
        db_session.commit()


@given(admin = st.sampled_from([user for user in test_users
                                if user["admin"] and user["in_use"]]))
def test_edit_user_change_session_name_and_admin_status(
        client: FlaskClient, admin: dict[str]):
    """Test session name change and admin status"""
    orig_clean_order = str(cleaning_sch.current_order().index(admin["id"]))
    new_name = ValidUser.name
    # log in admin
    with client.session_transaction() as this_session:
        this_session["user_id"] = admin["id"]
        this_session["admin"] = admin["admin"]
        this_session["user_name"] = admin["name"]
    # change logged in user name and admin status
    with client:
        response = client.get("/")
        start_inv_button = re.compile(r'<a.*href="' +
                                      url_for("users.approve_check_inv_all") +
                                      r'">Start Inventorying</a>')
        assert session["user_name"] == admin["name"]
        assert session["admin"]
        assert start_inv_button.search(response.text)
        client.get(url_for("users.edit_user", username=admin["name"]))
        data = {
                "csrf_token": g.csrf_token,
                "name": new_name,
                "details": admin["details"],
                "email": admin["email"],
                "check_inv": not admin["done_inv"],
                "admin": False,
                "in_use": True,
                "sat_group": str(admin["sat_group"]),
                "clean_order": orig_clean_order,
            }
        response = client.post(
            url_for("users.edit_user", username=admin["name"]),
            data=data,
            follow_redirects=True)
        assert session["user_name"] == new_name
        assert not session["admin"]
        assert redirected_to(url_for("main.index"), response)
        assert not start_inv_button.search(response.text)
    assert str(Message.User.Updated(new_name)) in unescape(response.text)
    assert new_name in response.text
    # db check and teardown
    with dbSession() as db_session:
        db_user = db_session.get(User, admin["id"])
        assert db_user.name == new_name
        db_user.name = admin["name"]
        assert not db_user.admin
        db_user.admin = True
        db_session.commit()


@given(user = st.sampled_from([user for user in test_users
                               if user["name"] != "Admin"]))
@example(user = [user for user in test_users if user["active"]][0])
@example(user = [user for user in test_users
                 if user["name"] != "Admin" and not user["active"]][0])
def test_edit_user_clean_schedule_order_choices(
        client: FlaskClient, admin_logged_in: User, user: dict[str]):
    """test_edit_user_clean_schedule_order_choices"""
    if user["active"]:
        clean_order = str(cleaning_sch.current_order().index(user["id"]))
    active_users = [user for user in test_users if user["active"]]
    clean_sch_options = [re.compile(r'<option.*value="0">This week</option>'),
                         re.compile(r'<option.*value="1">In 1 week</option>')]
    for num in range(2, len(active_users)):
        clean_sch_options.append(
            re.compile(fr'<option.*value="{num}">In {num} weeks</option>'))
    # check user options
    with client:
        client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        response = client.get(
            url_for("users.edit_user", username=user["name"]))
        if user["active"]:
            assert cleaning_sch.name in response.text
            for option in clean_sch_options:
                assert option.search(response.text)
            assert f'<option selected value="{clean_order}">' in response.text
        else:
            assert cleaning_sch.name not in response.text
            for option in clean_sch_options:
                assert not option.search(response.text)


@given(user = st.sampled_from([user for user in test_users if user["active"]]),
       h_data = st.data())
def test_edit_user_change_clean_schedule_order(
        client: FlaskClient, admin_logged_in: User,
        user: dict[str], h_data: st.DataObject):
    """test_edit_user_change_clean_schedule_order"""
    current_order = [user["id"] for user in test_users if user["active"]]
    assert current_order == cleaning_sch.current_order()
    curr_user_pos = current_order.index(user["id"])
    # change user position
    for _ in range(3):
        new_pos = h_data.draw(st.integers(min_value=0,
                                          max_value=len(current_order) - 1))
        with client:
            client.get("/")
            assert session["user_name"] == admin_logged_in.name
            assert session["admin"]
            response = client.get(
                url_for("users.edit_user", username=user["name"]))
            assert cleaning_sch.name in response.text
            data = {
                "csrf_token": g.csrf_token,
                "name": user["name"],
                "email": user["email"],
                "details": user["details"],
                "check_inv": not user["done_inv"],
                "admin": user["admin"],
                "in_use": user["in_use"],
                "sat_group": user["sat_group"],
                "clean_order": str(new_pos),
            }
            response = client.post(
                url_for("users.edit_user", username=user["name"]),
                data=data,
                follow_redirects=True)
            assert str(Message.User.Updated(user["name"])) \
                not in unescape(response.text)
            # check new order
            if new_pos == curr_user_pos:
                assert len(response.history) == 0
                assert response.status_code == 200
                assert str(Message.Schedule.Updated()) not in response.text
            else:
                assert redirected_to(url_for("main.index"), response)
                assert str(Message.Schedule.Updated()) in response.text
                current_order.pop(curr_user_pos)
                current_order.insert(new_pos, user["id"])
                assert current_order == cleaning_sch.current_order()
                curr_user_pos = new_pos
    # teardown
    cleaning_sch.unregister()
    cleaning_sch.register()


@given(user = st.sampled_from([user for user in test_users if user["active"]]),
       new_pos = st.one_of(
           st.none(),
           st.text(alphabet=string.ascii_letters),
           st.integers(max_value=-1),
           st.integers(min_value=len([user for user in test_users
                                      if user["active"]]))))
def test_edit_user_failed_change_clean_schedule_order(
        client: FlaskClient, admin_logged_in: User,
        user: dict[str], new_pos):
    """test_edit_user_failed_change_clean_schedule_order"""
    current_order = [user["id"] for user in test_users if user["active"]]
    assert current_order == cleaning_sch.current_order()
    if isinstance(new_pos, int):
        new_pos = str(new_pos)
    # try to change user position
    with client:
        client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        response = client.get(
            url_for("users.edit_user", username=user["name"]))
        assert cleaning_sch.name in response.text
        data = {
            "csrf_token": g.csrf_token,
            "name": user["name"],
            "email": user["email"],
            "details": user["details"],
            "check_inv": not user["done_inv"],
            "admin": user["admin"],
            "in_use": user["in_use"],
            "sat_group": user["sat_group"],
            "clean_order": new_pos,
        }
        response = client.post(
                url_for("users.edit_user", username=user["name"]),
                data=data)
    assert response.status_code == 200
    assert str(Message.Schedule.Updated()) not in response.text
    assert str(Message.User.Updated(user["name"])) \
            not in unescape(response.text)
    assert "Not a valid choice" in response.text
    assert current_order == cleaning_sch.current_order()
# endregion


# region: delete user
def test_delete_user(
        client: FlaskClient, admin_logged_in: User, caplog: LogCaptureFixture):
    """test_delete_user"""
    # add a user
    with dbSession() as db_session:
        user = User(name=ValidUser.name,
                    password=ValidUser.password,
                    reg_req=False)
        db_session.add(user)
        db_session.commit()
        cleaning_sch.add_user(user.id)
        assert f"Schedule '{cleaning_sch.name}' added '{user.name}'" \
            in caplog.messages
    # delete user
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
        response = client.post(url_for("users.edit_user", username=user.name),
                               data=data,
                               follow_redirects=True)
        assert redirected_to(url_for("sch.schedules"), response)
        assert str(Message.User.Deleted(user.name)) in response.text
        response = client.get(url_for("sch.schedules"))
        assert user.name not in response.text
        assert (f"Schedule '{cleaning_sch.name}' removed user with id " +
                f"'{user.id}'") in caplog.messages
    with dbSession() as db_session:
        assert not db_session.get(User, user.id)


def test_delete_user_admin_log_out(
        client: FlaskClient, caplog: LogCaptureFixture):
    """Test logout after self deletion of a logged in admin"""
    # add an admin
    with dbSession() as db_session:
        user = User(
            name=ValidUser.name,
            password=ValidUser.password,
            admin=True,
            reg_req=False)
        db_session.add(user)
        db_session.commit()
        cleaning_sch.add_user(user.id)
    # login
    with client.session_transaction() as this_session:
        this_session["user_id"] = user.id
        this_session["admin"] = user.admin
        this_session["user_name"] = user.name
    # self delete
    with client:
        client.get("/")
        response = client.get(url_for("users.edit_user", username=user.name))
        assert user.name in response.text
        data = {
            "csrf_token": g.csrf_token,
            "name": user.name,
            "delete": True,
        }
        response = client.post(url_for("users.edit_user", username=user.name),
                               data=data,
                               follow_redirects=True)
        assert redirected_to(url_for("auth.login"), response, 2)
        assert not session.get("user_id")
        assert not session.get("admin")
        assert not session.get("user_name")
    assert (f"Schedule '{cleaning_sch.name}' removed user with id " +
            f"'{user.id}'") in caplog.messages
    assert str(Message.User.Logout()) in response.text
    with dbSession() as db_session:
        assert not db_session.get(User, user.id)


@given(user = st.sampled_from(
        [user for user in test_users if user["has_products"]]))
def test_failed_delete_user(
        client: FlaskClient, admin_logged_in: User, user: dict[str]):
    """test_failed_delete_user"""
    with client:
        client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        response = client.get(url_for("users.edit_user", username=user["name"]))
        assert user["name"] in response.text
        data = {
            "csrf_token": g.csrf_token,
            "name": user["name"],
            "delete": True,
        }
        response = client.post(
            url_for("users.edit_user", username=user["name"]),
            data=data)
        assert response.status_code == 200
        assert str(Message.User.NoDelete()) in response.text
    with dbSession() as db_session:
        assert db_session.get(User, user["id"])
# endregion
