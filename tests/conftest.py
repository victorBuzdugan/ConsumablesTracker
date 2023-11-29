"""Pytest app fixtures and configuration."""

import pathlib
from datetime import date, timedelta
from os import path

import hypothesis
import pytest
from flask.testing import FlaskClient
from sqlalchemy import URL, create_engine

from app import app, babel, mail
from blueprints.sch.sch import cleaning_sch, saturday_sch
from constants import Constant
from database import Base, Category, Product, Supplier, User, dbSession
from helpers import log_handler
from tests import (BACKUP_DB, ORIG_DB, PROD_DB, TEMP_DB, TEST_DB_NAME,
                   test_categories, test_products, test_suppliers, test_users)

mail.state.suppress = True
hypothesis.settings.register_profile(
    "default",
    max_examples=3,
    deadline=3000,
    suppress_health_check=[hypothesis.HealthCheck.function_scoped_fixture])
hypothesis.settings.register_profile(
    name="long",
    parent=hypothesis.settings.get_profile("default"),
    max_examples=200)
hypothesis.settings.load_profile("default")
# hypothesis.settings.load_profile("long")


@pytest.fixture(scope="session")
def create_test_db():
    """Configure dbSession to a test database. """
    # run with pytest -s
    print("\nCreate test db")
    pathlib.Path.unlink(log_handler.baseFilename, missing_ok=True)
    pathlib.Path.unlink(PROD_DB, missing_ok=True)
    pathlib.Path.unlink(BACKUP_DB, missing_ok=True)
    pathlib.Path.unlink(ORIG_DB, missing_ok=True)
    pathlib.Path.unlink(TEMP_DB, missing_ok=True)
    db_url = URL.create(
        drivername="sqlite",
        database=path.join(Constant.Basic.current_dir, TEST_DB_NAME))
    test_engine = create_engine(
        url=db_url,
        echo=False,
        pool_size=25,
        max_overflow=35)
    dbSession.configure(bind=test_engine)
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)


@pytest.fixture(scope="session", name="client", autouse=True)
def fixture_client() -> FlaskClient:
    """Yield a flask test client."""
    print("\nYield client")
    app.testing = True
    app.secret_key = "testing"
    # make sure to always display en messages for testing purposes
    babel.init_app(app=app, locale_selector=lambda: "en")
    yield app.test_client()
    # teardown
    # delete log file and test database
    pathlib.Path.unlink(log_handler.baseFilename, missing_ok=True)
    pathlib.Path.unlink(PROD_DB, missing_ok=True)
    pathlib.Path.unlink(BACKUP_DB, missing_ok=True)
    pathlib.Path.unlink(ORIG_DB, missing_ok=True)
    pathlib.Path.unlink(TEMP_DB, missing_ok=True)


# region: users fixtures
@pytest.fixture(scope="session")
def create_test_users():
    """Insert into db a set of test users."""
    print("\nCreate test users")
    valid_ordered_attrs = ("reg_req", "admin", "in_use", "done_inv", "req_inv",
                           "details", "email", "sat_group", "id")
    with dbSession() as db_session:
        for user_dict in test_users:
            user = User(name=user_dict["name"],
                        password=user_dict["password"])
            for attr in valid_ordered_attrs:
                setattr(user, attr, user_dict[attr])
            db_session.add(user)
        db_session.commit()


@pytest.fixture(scope="function")
def user_logged_in(client: FlaskClient) -> User:
    """Log in not admin user4."""
    with dbSession() as db_session:
        test_user = db_session.get(User, 4)
    # 'log in' test user
    with client.session_transaction() as session:
        session["user_id"] = test_user.id
        session["admin"] = test_user.admin
        session["user_name"] = test_user.name
    yield test_user
    client.get("/auth/logout")


@pytest.fixture(scope="function")
def admin_logged_in(client: FlaskClient) -> User:
    """Log in admin user1."""
    with dbSession() as db_session:
        test_admin = db_session.get(User, 1)
    # 'log in' test admin
    with client.session_transaction() as session:
        session["user_id"] = test_admin.id
        session["admin"] = test_admin.admin
        session["user_name"] = test_admin.name
    yield test_admin
    client.get("/auth/logout")


@pytest.fixture(scope="function")
def hidden_admin_logged_in(client: FlaskClient):
    """Log in admin Admin."""
    with dbSession() as db_session:
        hidden_admin = db_session.get(User, 0)
    # 'log in' hidden admin
    with client.session_transaction() as session:
        session["user_id"] = hidden_admin.id
        session["admin"] = hidden_admin.admin
        session["user_name"] = hidden_admin.name
    yield hidden_admin
    client.get("/auth/logout")
# endregion


# region: categories fixtures
@pytest.fixture(scope="session")
def create_test_categories():
    """Insert into db a set of test categories."""
    print("\nCreate test categories")
    valid_attrs = ("in_use", "details", "id")
    with dbSession() as db_session:
        for category_dict in test_categories:
            category = Category(name=category_dict["name"])
            for attr in valid_attrs:
                setattr(category, attr, category_dict[attr])
            db_session.add(category)
        db_session.commit()
# endregion


# region: suppliers fixtures
@pytest.fixture(scope="session")
def create_test_suppliers():
    """Insert into db a set of test suppliers."""
    print("\nCreate test suppliers")
    valid_attrs = ("in_use", "details", "id")
    with dbSession() as db_session:
        for supplier_dict in test_suppliers:
            supplier = Supplier(name=supplier_dict["name"])
            for attr in valid_attrs:
                setattr(supplier, attr, supplier_dict[attr])
            db_session.add(supplier)
        db_session.commit()
# endregion


# region: products fixtures
@pytest.fixture(scope="session")
def create_test_products():
    """Insert into db a set of test products."""
    print("\nCreate test products")
    valid_attrs = ("to_order", "critical", "in_use", "id")
    with dbSession() as db_session:
        for product_dict in test_products:
            product = Product(
                name=product_dict["name"],
                description=product_dict["description"],
                responsible=db_session.get(
                    User, product_dict["responsible_id"]),
                category=db_session.get(
                    Category, product_dict["category_id"]),
                supplier=db_session.get(
                    Supplier, product_dict["supplier_id"]),
                meas_unit=product_dict["meas_unit"],
                min_stock=product_dict["min_stock"],
                ord_qty=product_dict["ord_qty"],
            )
            for attr in valid_attrs:
                setattr(product, attr, product_dict[attr])
            db_session.add(product)
        db_session.commit()
# endregion


# region: schedules fixtures
@pytest.fixture(scope="session")
def create_test_group_schedule():
    """Mock into db a 2 group 1 week interval schedule."""
    print("\nCreate test group schedule")
    saturday_sch.sch_day = (date.today()
                            .isocalendar()[2])
    saturday_sch.sch_day_update = ((date.today() + timedelta(days=1))
                                   .isocalendar()[2])
    saturday_sch.switch_interval = timedelta(weeks=1)
    saturday_sch.register()


@pytest.fixture(scope="session")
def create_test_individual_schedule():
    """Mock into db a 1 week interval individual schedule."""
    print("\nCreate test individual schedule")
    cleaning_sch.sch_day = (date.today()
                            .isocalendar()[2])
    cleaning_sch.sch_day_update = ((date.today() + timedelta(days=1))
                                   .isocalendar()[2])
    cleaning_sch.register()
# endregion
