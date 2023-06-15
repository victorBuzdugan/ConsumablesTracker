from typing import Generator
from werkzeug.security import check_password_hash, generate_password_hash

import pytest
from sqlalchemy import event, select, insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from database import User, engine


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

# Database connection fixture
@pytest.fixture(scope="module")
def db_session() -> Generator[Session, None, None]:
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

# region: test "users" table
# region CRUD: create/insert and read
def test_user_creation(db_session: Session):
    """Test default user creation and database insertion.
    
    It's expected that a user should be created with the default parameters:
    products: empty list
    admin: false
    in_use: True
    done_inv: True
    details: None
    """
    test_user = User("__test__user__", generate_password_hash("test_password"))
    db_session.add(test_user)
    db_session.commit()
    assert test_user.id != None, "test_user should have an id after commit"
    db_user = db_session.get(User, test_user.id)
    assert db_user.username == "__test__user__", "Wrong username"
    assert check_password_hash(db_user.password, "test_password"), "Password check failed"
    assert check_password_hash(db_user.password, "some_other_password") == False, "Password check should fail"
    assert db_user.products == [], "User shouldn't have products assigned"
    assert db_user.admin == False
    assert db_user.in_use == True
    assert db_user.done_inv == True
    assert db_user.details == None

def test_admin_creation(db_session: Session):
    """Test user creation with admin credentials (admin: True)"""
    test_user = User("__test__adminn__", "test_password", admin=True)
    db_session.add(test_user)
    db_session.commit()
    assert db_session.get(User, test_user.id).admin == True

def test_bulk_insertion(db_session: Session):
    values = [{"username": f"test__user{no}", "password": "some_password"}
              for no in range(6)]
    db_session.execute(insert(User), values)
    db_session.commit()
    users = db_session.scalars(select(User).where(User.username.like("test__user%"))).all()
    assert len(users) == 6
    for user in users:
        print(user)
        assert user.password == "some_password"
        assert user.products == []
        assert user.admin == False
        assert user.in_use == True
        assert user.done_inv == True
        assert user.details == None

@pytest.mark.xfail(raises=IntegrityError)
def test_username_duplicate(db_session: Session):
    try:
        db_session.add(User("__test__user__", "passw"))
    except IntegrityError:
        db_session.rollback()

@pytest.mark.xfail(raises=TypeError)
def test_no_username_or_no_password(db_session: Session):
    try:
        db_session.add(User("only_username_or_password"))
    except TypeError:
        db_session.rollback()
# endregion

# region CRUD: read and update
def test_change_username(db_session: Session):
    test_user = db_session.execute(select(User).filter_by(username="__test__adminn__")).scalar_one()
    assert test_user != None
    test_user.username = "__test__admin__"
    assert test_user in db_session.dirty
    # autoflush after select(get) statement
    db_user = db_session.get(User, test_user.id)
    assert db_user.username == "__test__admin__"

def test_change_password(db_session: Session):
    test_user = db_session.execute(select(User).filter_by(username="__test__user__")).scalar_one()
    assert test_user != None
    test_user.password = generate_password_hash("other_test_password")
    assert test_user in db_session.dirty
    # autoflush after select(get) statement
    db_user = db_session.get(User, test_user.id)
    assert check_password_hash(db_user.password, "other_test_password"), "Password check failed"
# endregion

# region CRUD: read and delete
def test_delete_user(db_session: Session):
    test_user = db_session.execute(select(User).filter_by(username="test__user0")).scalar_one()
    db_session.delete(test_user)
    db_user = db_session.execute(select(User).filter_by(username="test__user0")).scalar()
    assert db_user == None
# endregion
# endregion


# region: test "categories" table
pass
# endregion


# region: test "suppliers" table
pass
# endregion


# region: test "products" table
pass
# endregion
