"""Pytest app fixtures."""

import pathlib
from datetime import date, timedelta

import pytest
from flask.testing import FlaskClient
from sqlalchemy import URL, create_engine

from app import app, babel
from blueprints.sch import SAT_GROUP_SCH
from blueprints.sch.sch import cleaning_schedule
from blueprints.sch.sch import GroupSchedule
from database import Base, Category, Product, Supplier, User, dbSession
from helpers import DB_NAME, log_handler

TEST_DB_NAME = "." + DB_NAME

@pytest.fixture(scope="session")
def create_test_db():
    """Configure dbSession to a test database. """
    # run with pytest -s
    print("\nCreate test db")
    db_url = URL.create(
        drivername="sqlite",
        database=TEST_DB_NAME)
    test_engine = create_engine(
        url=db_url,
        echo=False,
        pool_size=15,
        max_overflow=25)
    dbSession.configure(bind=test_engine)
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)


@pytest.fixture(scope="session", name="client")
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
    pathlib.Path.unlink(TEST_DB_NAME, missing_ok=True)


# region: users fixtures
@pytest.fixture(scope="session")
def create_test_users():
    """Insert into db a set of test users."""
    print("\nCreate test users")
    users = []
    users.append("dummy value for index 0")
    users.append(User(
        name="user1",
        password="Q!111111",
        admin=True,
        reg_req=False))
    users.append(User(
        name="user2",
        password="Q!222222",
        admin=True,
        reg_req=False,
        sat_group=2))
    users.append(User(
        name="user3",
        password="Q!333333",
        reg_req=False))
    users.append(User(
        name="user4",
        password="Q!444444",
        reg_req=False,
        sat_group=2))
    users.append(User(
        name="user5",
        password="Q!555555"))
    users.append(User(
        name="user6",
        password="Q!666666",
        reg_req=False,
        in_use=False))
    users.append(User(
        name="user7",
        password="Q!777777",
        reg_req=False))
    with dbSession() as db_session:
        db_session.add_all(users[1:])
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
        test_admin = db_session.get(User, 0)
    # 'log in' test admin
    with client.session_transaction() as session:
        session["user_id"] = test_admin.id
        session["admin"] = test_admin.admin
        session["user_name"] = test_admin.name
    yield test_admin
    client.get("/auth/logout")
# endregion


# region: categories fixtures
@pytest.fixture(scope="session")
def create_test_categories():
    """Insert into db a set of test categories."""
    print("\nCreate test categories")
    categories = []
    categories.append(Category(name="Household",
                               description="Household consumables"))
    categories.append(Category(name="Personal",
                               description="Personal consumables"))
    categories.append(Category(name="Electronics"))
    categories.append(Category(name="Kids"))
    categories.append(Category(name="Health"))
    categories.append(Category(name="Groceries"))
    categories.append(Category(name="Pets"))
    categories.append(Category(name="Others", in_use=False))
    with dbSession() as db_session:
        db_session.add_all(categories)
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
            responsable=db_session.get(User, 2),
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
            responsable=db_session.get(User, 2),
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
            responsable=db_session.get(User, 2),
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
            responsable=db_session.get(User, 2),
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
            responsable=db_session.get(User, 2),
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
            responsable=db_session.get(User, 2),
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
            responsable=db_session.get(User, 2),
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
            responsable=db_session.get(User, 2),
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
            responsable=db_session.get(User, 2),
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
            responsable=db_session.get(User, 2),
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
            responsable=db_session.get(User, 1),
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
            responsable=db_session.get(User, 1),
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
            responsable=db_session.get(User, 2),
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
            responsable=db_session.get(User, 1),
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
            responsable=db_session.get(User, 3),
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
            responsable=db_session.get(User, 3),
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
            responsable=db_session.get(User, 1),
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
            responsable=db_session.get(User, 1),
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
            responsable=db_session.get(User, 1),
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
            responsable=db_session.get(User, 4),
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
            responsable=db_session.get(User, 4),
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
            responsable=db_session.get(User, 1),
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
            responsable=db_session.get(User, 2),
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
            responsable=db_session.get(User, 3),
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
            responsable=db_session.get(User, 1),
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
            responsable=db_session.get(User, 3),
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
            responsable=db_session.get(User, 3),
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
            responsable=db_session.get(User, 3),
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
            responsable=db_session.get(User, 3),
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
            responsable=db_session.get(User, 1),
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
            responsable=db_session.get(User, 3),
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
            responsable=db_session.get(User, 3),
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
            responsable=db_session.get(User, 1),
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
            responsable=db_session.get(User, 4),
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
            responsable=db_session.get(User, 4),
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
            responsable=db_session.get(User, 2),
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
            responsable=db_session.get(User, 2),
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
            responsable=db_session.get(User, 1),
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
            responsable=db_session.get(User, 2),
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
            responsable=db_session.get(User, 1),
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
            responsable=db_session.get(User, 1),
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
            responsable=db_session.get(User, 2),
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
            responsable=db_session.get(User, 1),
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
    GroupSchedule(
        name=SAT_GROUP_SCH["db_name"],
        user_attr=User.sat_group.name,
        num_groups=2,
        first_group=1,
        sch_day=date.today().isocalendar()[2],
        sch_day_update=(date.today() + timedelta(days=1)).isocalendar()[2],
        switch_interval=timedelta(weeks=1),
        start_date=date.today()).register()


@pytest.fixture(scope="session")
def create_test_individual_schedule():
    """Mock into db a 1 week interval individual schedule."""
    print("\nCreate test individual schedule")
    cleaning_schedule.register()
# endregion
