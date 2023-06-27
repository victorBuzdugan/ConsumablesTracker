"""Pytest fixtures."""

from typing import Generator

import pytest
from flask.testing import FlaskClient
from sqlalchemy import event, select
from sqlalchemy.orm import Session, sessionmaker
from werkzeug.security import generate_password_hash

from app import app
from database import User, dbSession, engine, Category, Supplier


# region: required for SQLite to handle SAVEPOINTs for rollback after tests
@event.listens_for(engine, "connect")
def do_connect(dbapi_connection, connection_record):
    # disable pysqlite's emitting of the BEGIN statement entirely.
    # also stops it from emitting COMMIT before any DDL.
    dbapi_connection.isolation_level = None


@event.listens_for(engine, "begin")
def do_begin(conn):
    # emit our own BEGIN
    conn.exec_driver_sql("BEGIN")
# endregion


@pytest.fixture(scope="session")
def db_session() -> Generator[Session, None, None]:
    """Database connection fixture for testing (with rollback)."""
    TestSession = sessionmaker()
    # connect to the database using the database.py engine
    connection = engine.connect()
    # begin a non-ORM transaction
    transaction = connection.begin()
    # bind an individual Session to the connection, selecting
    # "create_savepoint" join_transaction_mode
    session = TestSession(
        bind=connection, join_transaction_mode="create_savepoint")
    yield session
    session.close()
    # rollback - everything that happened with the
    # Session above (including calls to commit())
    # is rolled back.
    transaction.rollback()
    # return connection to the Engine
    connection.close()


@pytest.fixture(scope="session")
def default_user_category_supplier(db_session: Session):
    """Create a default user, category and supplier."""
    test_user = db_session.execute(
        select(User).filter_by(name="__test__user__")).scalar_one()
    test_category = db_session.execute(
        select(Category).filter_by(name="__test__category__")).scalar_one()
    test_supplier = db_session.execute(
        select(Supplier).filter_by(name="__test__supplier__")).scalar_one()
    return test_user, test_category, test_supplier


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


