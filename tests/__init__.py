"""Pytest app fixtures."""

import pytest
from flask.testing import FlaskClient
from sqlalchemy import select
from werkzeug.security import generate_password_hash

from app import app
from database import User, dbSession, Category, Supplier


@pytest.fixture(scope="session")
def client() -> FlaskClient:
    """Yield a test client."""
    app.testing = True
    app.secret_key = 'testing'
    yield app.test_client()


@pytest.fixture(scope="session")
def create_test_users():
    """Create 3 users for tests."""
    reg_req_user = User(
        name="reg_req_user",
        password=generate_password_hash("P@ssw0rd"))
    not_in_use_user = User(
        name="not_in_use_user",
        password=generate_password_hash("P@ssw0rd"),
        reg_req=False,
        in_use=False)
    __test__user__ = User(
        name="__test__user__",
        password=generate_password_hash("P@ssw0rd"),
        reg_req=False)
    __test__admin__ = User(
        name="__test__admin__",
        password=generate_password_hash("P@ssw0rd"),
        admin=True,
        reg_req=False)
    with dbSession() as db_session:
        db_session.add(reg_req_user)
        db_session.add(not_in_use_user)
        db_session.add(__test__user__)
        db_session.add(__test__admin__)
        db_session.commit()

    yield

    with dbSession() as db_session:
        db_session.delete(reg_req_user)
        db_session.delete(not_in_use_user)
        db_session.delete(__test__user__)
        db_session.delete(__test__admin__)
        db_session.commit()

        assert not db_session.get(User, reg_req_user.id)
        assert not db_session.get(User, not_in_use_user.id)


@pytest.fixture(scope="function")
def user_logged_in(client: FlaskClient, create_test_users):
    """Log in __test__user__."""
    with dbSession() as db_session:
        test_user = db_session.scalar(
                select(User).filter_by(name="__test__user__"))
    # 'log in' test user
    with client.session_transaction() as session:
        session["user_id"] = test_user.id
        session["admin"] = test_user.admin
        session["user_name"] = test_user.name
    
    yield

    client.get("/auth/logout")


@pytest.fixture(scope="function")
def admin_logged_in(client: FlaskClient, create_test_users):
    """Log in __test__admin__."""
    with dbSession() as db_session:
        test_admin = db_session.scalar(
                select(User).filter_by(name="__test__admin__"))
    # 'log in' test admin
    with client.session_transaction() as session:
        session["user_id"] = test_admin.id
        session["admin"] = test_admin.admin
        session["user_name"] = test_admin.name
    
    yield

    client.get("/auth/logout")