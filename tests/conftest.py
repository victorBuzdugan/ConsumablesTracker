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
from database import Base, Category, Product, Supplier, User, dbSession
from helpers import Constants, log_handler
from tests import (BACKUP_DB, ORIG_DB, PROD_DB, TEMP_DB, TEST_DB_NAME,
                   test_categories, test_users)

mail.state.suppress = True
hypothesis.settings.register_profile("default", deadline=3000)
hypothesis.settings.load_profile("default")


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
        database=path.join(Constants.Basic.current_dir, TEST_DB_NAME))
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
    app.secret_key = 'testing'
    # make sure to allways display en messages for testing purposes
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
    with dbSession() as db_session:
        for category_dict in test_categories:
            category = Category(**category_dict)
            db_session.add(category)
        db_session.commit()
# endregion


# region: suppliers fixtures
@pytest.fixture(scope="session")
def create_test_suppliers():
    """Insert into db a set of test suppliers."""
    print("\nCreate test suppliers")
    suppliers = []
    suppliers.append(Supplier(name="Amazon", details="www.amazon.com"))
    suppliers.append(Supplier(name="eBay", details="www.ebay.com"))
    suppliers.append(Supplier(name="Kaufland"))
    suppliers.append(Supplier(name="Carrefour"))
    suppliers.append(Supplier(name="Other", in_use=False))
    with dbSession() as db_session:
        db_session.add_all(suppliers)
        db_session.commit()
# endregion


# region: products fixtures
@pytest.fixture(scope="session")
def create_test_products():
    """Insert into db a set of test products."""
    print("\nCreate test products")
    with dbSession() as db_session:
        db_session.add(Product(
            name="Toilet paper",
            description="Toilet paper 3-Ply",
            responsible=db_session.get(User, 2),
            category=db_session.get(Category, 1),
            supplier=db_session.get(Supplier, 3),
            meas_unit="roll",
            min_stock=5,
            ord_qty=20,
            to_order=False,
            critical=True))
        db_session.add(Product(
            name="Paper towels",
            description="Kitchen paper towels",
            responsible=db_session.get(User, 2),
            category=db_session.get(Category, 1),
            supplier=db_session.get(Supplier, 4),
            meas_unit="roll",
            min_stock=2,
            ord_qty=4,
            to_order=False,
            critical=False))
        db_session.add(Product(
            name="Trash bag small",
            description="Trash bag 35l",
            responsible=db_session.get(User, 2),
            category=db_session.get(Category, 1),
            supplier=db_session.get(Supplier, 4),
            meas_unit="bag",
            min_stock=3,
            ord_qty=10,
            to_order=False,
            critical=True))
        db_session.add(Product(
            name="Trash bag large",
            description="Trash bag 70l",
            responsible=db_session.get(User, 2),
            category=db_session.get(Category, 1),
            supplier=db_session.get(Supplier, 4),
            meas_unit="bag",
            min_stock=3,
            ord_qty=10,
            to_order=False,
            critical=False))
        db_session.add(Product(
            name="Glass cleaner",
            description="Glass cleaner",
            responsible=db_session.get(User, 2),
            category=db_session.get(Category, 1),
            supplier=db_session.get(Supplier, 1),
            meas_unit="bottle",
            min_stock=0,
            ord_qty=1,
            to_order=False,
            critical=False))
        db_session.add(Product(
            name="Bathroom cleaner",
            description="Bathroom cleaner",
            responsible=db_session.get(User, 2),
            category=db_session.get(Category, 1),
            supplier=db_session.get(Supplier, 1),
            meas_unit="bottle",
            min_stock=0,
            ord_qty=1,
            to_order=False,
            critical=False))
        db_session.add(Product(
            name="Wood cleaner",
            description="Pronto wood cleaner",
            responsible=db_session.get(User, 2),
            category=db_session.get(Category, 1),
            supplier=db_session.get(Supplier, 1),
            meas_unit="spray",
            min_stock=0,
            ord_qty=1,
            to_order=False,
            critical=False))
        db_session.add(Product(
            name="Kitchen cleaner",
            description="Kitchen cleaner",
            responsible=db_session.get(User, 2),
            category=db_session.get(Category, 1),
            supplier=db_session.get(Supplier, 1),
            meas_unit="spray",
            min_stock=0,
            ord_qty=1,
            to_order=False,
            critical=False))
        db_session.add(Product(
            name="Kitchen sponge",
            description="Kitchen scrub sponge",
            responsible=db_session.get(User, 2),
            category=db_session.get(Category, 1),
            supplier=db_session.get(Supplier, 4),
            meas_unit="pc",
            min_stock=2,
            ord_qty=8,
            to_order=False,
            critical=False))
        db_session.add(Product(
            name="Cleaning Cloth",
            description="Microfiber Cleaning Cloth",
            responsible=db_session.get(User, 2),
            category=db_session.get(Category, 1),
            supplier=db_session.get(Supplier, 3),
            meas_unit="pc",
            min_stock=1,
            ord_qty=6,
            to_order=False,
            critical=False))
        db_session.add(Product(
            name="AA Batteries",
            description="Ultra AA Batteries",
            responsible=db_session.get(User, 1),
            category=db_session.get(Category, 3),
            supplier=db_session.get(Supplier, 2),
            meas_unit="pc",
            min_stock=2,
            ord_qty=8,
            to_order=False,
            critical=True))
        db_session.add(Product(
            name="AAA Batteries",
            description="Ultra AAA Batteries",
            responsible=db_session.get(User, 1),
            category=db_session.get(Category, 3),
            supplier=db_session.get(Supplier, 2),
            meas_unit="pc",
            min_stock=2,
            ord_qty=6,
            to_order=False,
            critical=False))
        db_session.add(Product(
            name="Laundry Detergent",
            description="Powder Laundry Detergent",
            responsible=db_session.get(User, 2),
            category=db_session.get(Category, 1),
            supplier=db_session.get(Supplier, 4),
            meas_unit="bag",
            min_stock=0,
            ord_qty=1,
            to_order=False,
            critical=False))
        db_session.add(Product(
            name="Matches",
            description="Matches",
            responsible=db_session.get(User, 1),
            category=db_session.get(Category, 1),
            supplier=db_session.get(Supplier, 4),
            meas_unit="box",
            min_stock=1,
            ord_qty=3,
            to_order=False,
            critical=False))
        db_session.add(Product(
            name="Facial tissues",
            description="Facial tissues",
            responsible=db_session.get(User, 3),
            category=db_session.get(Category, 2),
            supplier=db_session.get(Supplier, 1),
            meas_unit="pack",
            min_stock=2,
            ord_qty=10,
            to_order=False,
            critical=False))
        db_session.add(Product(
            name="Personal wipes",
            description="Personal cleansing wipes",
            responsible=db_session.get(User, 3),
            category=db_session.get(Category, 2),
            supplier=db_session.get(Supplier, 1),
            meas_unit="pack",
            min_stock=1,
            ord_qty=6,
            to_order=False,
            critical=True))
        db_session.add(Product(
            name="Eyeglass wipes",
            description="Eyeglass wipes",
            responsible=db_session.get(User, 1),
            category=db_session.get(Category, 2),
            supplier=db_session.get(Supplier, 1),
            meas_unit="pack",
            min_stock=0,
            ord_qty=2,
            to_order=False,
            critical=False))
        db_session.add(Product(
            name="Photo printer cartridge",
            description="Photo printer ink cartridge",
            responsible=db_session.get(User, 1),
            category=db_session.get(Category, 3),
            supplier=db_session.get(Supplier, 1),
            meas_unit="pc",
            min_stock=1,
            ord_qty=1,
            to_order=False,
            critical=False))
        db_session.add(Product(
            name="Photo printer paper",
            description="Photo printer paper",
            responsible=db_session.get(User, 1),
            category=db_session.get(Category, 3),
            supplier=db_session.get(Supplier, 1),
            meas_unit="pc",
            min_stock=10,
            ord_qty=20,
            to_order=False,
            critical=False))
        db_session.add(Product(
            name="Drawing paper",
            description="Drawing paper",
            responsible=db_session.get(User, 4),
            category=db_session.get(Category, 4),
            supplier=db_session.get(Supplier, 1),
            meas_unit="pc",
            min_stock=10,
            ord_qty=20,
            to_order=False,
            critical=False))
        db_session.add(Product(
            name="Drawing crayons",
            description="Drawing crayons",
            responsible=db_session.get(User, 4),
            category=db_session.get(Category, 4),
            supplier=db_session.get(Supplier, 1),
            meas_unit="pc",
            min_stock=0,
            ord_qty=1,
            to_order=False,
            critical=False))
        db_session.add(Product(
            name="Car cleaner",
            description="Car plastics cleaner",
            responsible=db_session.get(User, 1),
            category=db_session.get(Category, 1),
            supplier=db_session.get(Supplier, 4),
            meas_unit="spray",
            min_stock=0,
            ord_qty=1,
            to_order=False,
            critical=False))
        db_session.add(Product(
            name="Face cream",
            description="Face cream",
            responsible=db_session.get(User, 2),
            category=db_session.get(Category, 2),
            supplier=db_session.get(Supplier, 4),
            meas_unit="pc",
            min_stock=0,
            ord_qty=1,
            to_order=False,
            critical=False))
        db_session.add(Product(
            name="Toothpaste",
            description="Toothpaste",
            responsible=db_session.get(User, 3),
            category=db_session.get(Category, 2),
            supplier=db_session.get(Supplier, 4),
            meas_unit="pc",
            min_stock=1,
            ord_qty=1,
            to_order=False,
            critical=True))
        db_session.add(Product(
            name="Vitamins",
            description="Multi-vitamins",
            responsible=db_session.get(User, 1),
            category=db_session.get(Category, 5),
            supplier=db_session.get(Supplier, 3),
            meas_unit="pc",
            min_stock=10,
            ord_qty=30,
            to_order=False,
            critical=True))
        db_session.add(Product(
            name="Bandages",
            description="Mixed bandages",
            responsible=db_session.get(User, 3),
            category=db_session.get(Category, 5),
            supplier=db_session.get(Supplier, 4),
            meas_unit="pack",
            min_stock=0,
            ord_qty=1,
            to_order=False,
            critical=True))
        db_session.add(Product(
            name="Cat food",
            description="Cat food",
            responsible=db_session.get(User, 3),
            category=db_session.get(Category, 7),
            supplier=db_session.get(Supplier, 2),
            meas_unit="bag",
            min_stock=0,
            ord_qty=1,
            to_order=False,
            critical=True))
        db_session.add(Product(
            name="Cat litter",
            description="Cat litter",
            responsible=db_session.get(User, 3),
            category=db_session.get(Category, 7),
            supplier=db_session.get(Supplier, 2),
            meas_unit="bag",
            min_stock=0,
            ord_qty=1,
            to_order=False,
            critical=True))
        db_session.add(Product(
            name="Playdough",
            description="Playdough",
            responsible=db_session.get(User, 3),
            category=db_session.get(Category, 4),
            supplier=db_session.get(Supplier, 2),
            meas_unit="set",
            min_stock=0,
            ord_qty=1,
            to_order=False,
            critical=False))
        db_session.add(Product(
            name="Bread",
            description="Sliced bread",
            responsible=db_session.get(User, 1),
            category=db_session.get(Category, 6),
            supplier=db_session.get(Supplier, 3),
            meas_unit="pc",
            min_stock=1,
            ord_qty=1,
            to_order=False,
            critical=True))
        db_session.add(Product(
            name="Oranges",
            description="Oranges",
            responsible=db_session.get(User, 3),
            category=db_session.get(Category, 6),
            supplier=db_session.get(Supplier, 4),
            meas_unit="bag",
            min_stock=0,
            ord_qty=1,
            to_order=False,
            critical=False))
        db_session.add(Product(
            name="Bananas",
            description="Bananas",
            responsible=db_session.get(User, 3),
            category=db_session.get(Category, 6),
            supplier=db_session.get(Supplier, 4),
            meas_unit="pc",
            min_stock=3,
            ord_qty=10,
            to_order=False,
            critical=False))
        db_session.add(Product(
            name="Milk",
            description="Milk",
            responsible=db_session.get(User, 1),
            category=db_session.get(Category, 6),
            supplier=db_session.get(Supplier, 3),
            meas_unit="bottle",
            min_stock=0,
            ord_qty=1,
            to_order=False,
            critical=True))
        db_session.add(Product(
            name="Cereals",
            description="Cereals",
            responsible=db_session.get(User, 4),
            category=db_session.get(Category, 6),
            supplier=db_session.get(Supplier, 3),
            meas_unit="bag",
            min_stock=1,
            ord_qty=1,
            to_order=False,
            critical=True))
        db_session.add(Product(
            name="Chocolate",
            description="Chocolate",
            responsible=db_session.get(User, 4),
            category=db_session.get(Category, 6),
            supplier=db_session.get(Supplier, 3),
            meas_unit="pc",
            min_stock=1,
            ord_qty=2,
            to_order=False,
            critical=True))
        db_session.add(Product(
            name="Eggs",
            description="Eggs",
            responsible=db_session.get(User, 2),
            category=db_session.get(Category, 6),
            supplier=db_session.get(Supplier, 4),
            meas_unit="pc",
            min_stock=5,
            ord_qty=10,
            to_order=False,
            critical=True))
        db_session.add(Product(
            name="Pasta",
            description="Pasta",
            responsible=db_session.get(User, 2),
            category=db_session.get(Category, 6),
            supplier=db_session.get(Supplier, 4),
            meas_unit="pack",
            min_stock=0,
            ord_qty=1,
            to_order=False,
            critical=True))
        db_session.add(Product(
            name="Coffee",
            description="Coffee",
            responsible=db_session.get(User, 1),
            category=db_session.get(Category, 6),
            supplier=db_session.get(Supplier, 4),
            meas_unit="bag",
            min_stock=0,
            ord_qty=1,
            to_order=False,
            critical=True))
        db_session.add(Product(
            name="Cheese",
            description="Cheese",
            responsible=db_session.get(User, 2),
            category=db_session.get(Category, 6),
            supplier=db_session.get(Supplier, 3),
            meas_unit="pc",
            min_stock=0,
            ord_qty=1,
            to_order=False,
            critical=False))
        db_session.add(Product(
            name="Mustard",
            description="Mustard",
            responsible=db_session.get(User, 1),
            category=db_session.get(Category, 6),
            supplier=db_session.get(Supplier, 3),
            meas_unit="bottle",
            min_stock=0,
            ord_qty=1,
            to_order=False,
            critical=False))
        db_session.add(Product(
            name="Ketchup",
            description="Ketchup",
            responsible=db_session.get(User, 1),
            category=db_session.get(Category, 6),
            supplier=db_session.get(Supplier, 3),
            meas_unit="bottle",
            min_stock=0,
            ord_qty=1,
            to_order=False,
            critical=False))
        db_session.add(Product(
            name="Sunflower oil",
            description="Sunflower oil",
            responsible=db_session.get(User, 2),
            category=db_session.get(Category, 6),
            supplier=db_session.get(Supplier, 4),
            meas_unit="bottle",
            min_stock=0,
            ord_qty=1,
            to_order=False,
            critical=False))
        db_session.add(Product(
            name="Other",
            description="Other",
            responsible=db_session.get(User, 1),
            category=db_session.get(Category, 3),
            supplier=db_session.get(Supplier, 2),
            meas_unit="pc",
            min_stock=1,
            ord_qty=2,
            to_order=False,
            critical=False,
            in_use=False))
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
