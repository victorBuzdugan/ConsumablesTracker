"""Pytest app fixtures."""

import pytest
from flask.testing import FlaskClient
from sqlalchemy import select, create_engine
from werkzeug.security import generate_password_hash

from app import app
from database import dbSession, Base, User, Category, Supplier, Product


@pytest.fixture(scope="session")
def create_test_db():
    """Configure session to a test database. """
    testEngine = create_engine("sqlite:///.inventory.db", echo=True)
    dbSession.configure(bind=testEngine)
    Base.metadata.drop_all(bind=testEngine)
    Base.metadata.create_all(bind=testEngine)


@pytest.fixture(scope="session")
def client(
    create_test_db,
    create_test_users,
    create_test_categories,
    create_test_suppliers,
    create_test_products
    ) -> FlaskClient:
    """Yield a test client."""
    app.testing = True
    app.secret_key = 'testing'
    yield app.test_client()


# region: users fixtures
@pytest.fixture(scope="session")
def create_test_users(create_test_db):
    """Insert into db a set of test users."""
    users = []
    users.append(User(
        "user1",
        generate_password_hash("Q!111111"),
        admin=True,
        reg_req=False))
    users.append(User(
        "user2",
        generate_password_hash("Q!222222"),
        admin=True,
        reg_req=False))
    users.append(User(
        "user3",
        generate_password_hash("Q!333333"),
        reg_req=False))
    users.append(User(
        "user4",
        generate_password_hash("Q!444444"),
        reg_req=False))
    users.append(User(
        "user5",
        generate_password_hash("Q!555555")))
    users.append(User(
        "user6",
        generate_password_hash("Q!666666"),
        reg_req=False,
        in_use=False))
    with dbSession() as db_session:
        db_session.add_all(users)
        db_session.commit()


@pytest.fixture(scope="function")
def user_logged_in(client: FlaskClient):
    """Log in not admin user4."""
    with dbSession() as db_session:
        test_user = db_session.scalar(
                select(User).filter_by(name="user4"))
    # 'log in' test user
    with client.session_transaction() as session:
        session["user_id"] = test_user.id
        session["admin"] = test_user.admin
        session["user_name"] = test_user.name
    
    yield

    client.get("/auth/logout")


@pytest.fixture(scope="function")
def admin_logged_in(client: FlaskClient):
    """Log in admin user1."""
    with dbSession() as db_session:
        test_admin = db_session.scalar(
                select(User).filter_by(name="user1"))
    # 'log in' test admin
    with client.session_transaction() as session:
        session["user_id"] = test_admin.id
        session["admin"] = test_admin.admin
        session["user_name"] = test_admin.name
    
    yield

    client.get("/auth/logout")
# endregion


# region: categories fixtures
@pytest.fixture(scope="session")
def create_test_categories():
    """Insert into db a set of test categories."""
    categories = []
    categories.append(Category("Household",
                               description="Household consumables"))
    categories.append(Category("Personal",
                               description="Personal consumables"))
    categories.append(Category("Electonics"))
    categories.append(Category("Kids"))
    categories.append(Category("Health"))
    categories.append(Category("Groceries"))
    categories.append(Category("Pets"))
    categories.append(Category("Others", in_use=False))
    with dbSession() as db_session:
        db_session.add_all(categories)
        db_session.commit()
# endregion


# region: suppliers fixtures
@pytest.fixture(scope="session")
def create_test_suppliers():
    """Insert into db a set of test suppliers."""
    suppliers = []
    suppliers.append(Supplier("Amazon", details="www.amazon.com"))
    suppliers.append(Supplier("eBay", details="www.ebay.com"))
    suppliers.append(Supplier("Kaufland"))
    suppliers.append(Supplier("Carrefour"))
    suppliers.append(Supplier("Other", in_use=False))
    with dbSession() as db_session:
        db_session.add_all(suppliers)
        db_session.commit()
# endregion


# region: products fixtures
@pytest.fixture(scope="session")
def create_test_products():
    """Insert into db a set of test products."""
    with dbSession() as db_session:
        users = db_session.scalars(select(User)).all()
        categories = db_session.scalars(select(User)).all()
        suppliers = db_session.scalars(select(User)).all()
        db_session.add(Product("Toilet paper", "Toilet paper 3-Ply",
            db_session.get(User, 2), db_session.get(Category, 1),
            db_session.get(Supplier, 3), "roll", 5, 20, False, True))
        db_session.add(Product("Paper towels", "Kitchen paper towels",
            db_session.get(User, 2), db_session.get(Category, 1),
            db_session.get(Supplier, 4), "roll", 2, 4, False, False))
        db_session.add(Product("Trash bag small", "Trash bag 35l",
            db_session.get(User, 2), db_session.get(Category, 1),
            db_session.get(Supplier, 4), "bag", 3, 10, False, True))
        db_session.add(Product("Trash bag large", "Trash bag 70l",
            db_session.get(User, 2), db_session.get(Category, 1),
            db_session.get(Supplier, 4), "bag", 3, 10, False, False))
        db_session.add(Product("Glass cleaner", "Glass cleaner",
            db_session.get(User, 2), db_session.get(Category, 1),
            db_session.get(Supplier, 1), "bottle", 0, 1, False, False))
        db_session.add(Product("Bathroom cleaner", "Bathroom cleaner",
            db_session.get(User, 2), db_session.get(Category, 1),
            db_session.get(Supplier, 1), "bottle", 0, 1, False, False))
        db_session.add(Product("Wood cleaner", "Pronto wood cleaner",
            db_session.get(User, 2), db_session.get(Category, 1),
            db_session.get(Supplier, 1), "spray", 0, 1, False, False))
        db_session.add(Product("Kitchen cleaner", "Kitchen cleaner",
            db_session.get(User, 2), db_session.get(Category, 1),
            db_session.get(Supplier, 1), "spray", 0, 1, False, False))
        db_session.add(Product("Kitchen sponge", "Kitchen scrub sponge",
            db_session.get(User, 2), db_session.get(Category, 1),
            db_session.get(Supplier, 4), "pc", 2, 8, False, False))
        db_session.add(Product("Cleaning Cloth", "Microfiber Cleaning Cloth",
            db_session.get(User, 2), db_session.get(Category, 1),
            db_session.get(Supplier, 3), "pc", 1, 6, False, False))
        db_session.add(Product("AA Batteries", "Ultra AA Batteries",
            db_session.get(User, 1), db_session.get(Category, 3),
            db_session.get(Supplier, 2), "pc", 2, 8, False, True))
        db_session.add(Product("AAA Batteries", "Ultra AAA Batteries",
            db_session.get(User, 1), db_session.get(Category, 3),
            db_session.get(Supplier, 2), "pc", 2, 6, False, False))
        db_session.add(Product("Laundry Detergent", "Powder Laundry Detergent",
            db_session.get(User, 2), db_session.get(Category, 1),
            db_session.get(Supplier, 4), "bag", 0, 1, False, False))
        db_session.add(Product("Matches", "Matches",
            db_session.get(User, 1), db_session.get(Category, 1),
            db_session.get(Supplier, 4), "box", 1, 3, False, False))
        db_session.add(Product("Facial tissues", "Facial tissues",
            db_session.get(User, 3), db_session.get(Category, 2),
            db_session.get(Supplier, 1), "pack", 2, 10, False, False))
        db_session.add(Product("Personal wipes", "Personal cleansing wipes",
            db_session.get(User, 3), db_session.get(Category, 2),
            db_session.get(Supplier, 1), "pack", 1, 6, False, True))
        db_session.add(Product("Eyeglass wipes", "Eyeglass wipes",
            db_session.get(User, 1), db_session.get(Category, 2),
            db_session.get(Supplier, 1), "pack", 0, 2, False, False))
        db_session.add(Product(
            "Photo printer cartridge", "Photo printer ink cartridge",
            db_session.get(User, 1), db_session.get(Category, 3),
            db_session.get(Supplier, 1), "pc", 1, 1, False, False))
        db_session.add(Product("Photo printer paper", "Photo printer paper",
            db_session.get(User, 1), db_session.get(Category, 3),
            db_session.get(Supplier, 1), "pc", 10, 20, False, False))
        db_session.add(Product("Drawing paper", "Drawing paper",
            db_session.get(User, 4), db_session.get(Category, 4),
            db_session.get(Supplier, 1), "pc", 10, 20, False, False))
        db_session.add(Product("Drawing crayons", "Drawing crayons",
            db_session.get(User, 4), db_session.get(Category, 4),
            db_session.get(Supplier, 1), "pc", 0, 1, False, False))
        db_session.add(Product("Car cleaner", "Car plastics cleaner",
            db_session.get(User, 1), db_session.get(Category, 1),
            db_session.get(Supplier, 4), "spray", 0, 1, False, False))
        db_session.add(Product("Face cream", "Face cream",
            db_session.get(User, 2), db_session.get(Category, 2),
            db_session.get(Supplier, 4), "pc", 0, 1, False, False))
        db_session.add(Product("Toothpaste", "Toothpaste",
            db_session.get(User, 3), db_session.get(Category, 2),
            db_session.get(Supplier, 4), "pc", 1, 1, False, True))
        db_session.add(Product("Vitamins", "Multi-vitamins",
            db_session.get(User, 1), db_session.get(Category, 5),
            db_session.get(Supplier, 3), "pc", 10, 30, False, True))
        db_session.add(Product("Bandages", "Mixed bandages",
            db_session.get(User, 3), db_session.get(Category, 5),
            db_session.get(Supplier, 4), "pack", 0, 1, False, True))
        db_session.add(Product("Cat food", "Cat food",
            db_session.get(User, 3), db_session.get(Category, 7),
            db_session.get(Supplier, 2), "bag", 0, 1, False, True))
        db_session.add(Product("Cat litter", "Cat litter",
            db_session.get(User, 3), db_session.get(Category, 7),
            db_session.get(Supplier, 2), "bag", 0, 1, False, True))
        db_session.add(Product("Playdough", "Playdough",
            db_session.get(User, 3), db_session.get(Category, 4),
            db_session.get(Supplier, 2), "set", 0, 1, False, False))
        db_session.add(Product("Bread", "Sliced bread",
            db_session.get(User, 1), db_session.get(Category, 6),
            db_session.get(Supplier, 3), "pc", 1, 1, False, True))
        db_session.add(Product("Oranges", "Oranges",
            db_session.get(User, 3), db_session.get(Category, 6),
            db_session.get(Supplier, 4), "bag", 0, 1, False, False))
        db_session.add(Product("Bananas", "Bananas",
            db_session.get(User, 3), db_session.get(Category, 6),
            db_session.get(Supplier, 4), "pc", 3, 10, False, False))
        db_session.add(Product("Milk", "Milk",
            db_session.get(User, 1), db_session.get(Category, 6),
            db_session.get(Supplier, 3), "bottle", 0, 1, False, True))
        db_session.add(Product("Cereals", "Cereals",
            db_session.get(User, 4), db_session.get(Category, 6),
            db_session.get(Supplier, 3), "bag", 1, 1, False, True))
        db_session.add(Product("Chocolate", "Chocolate",
            db_session.get(User, 4), db_session.get(Category, 6),
            db_session.get(Supplier, 3), "pc", 1, 2, False, True))
        db_session.add(Product("Eggs", "Eggs",
            db_session.get(User, 2), db_session.get(Category, 6),
            db_session.get(Supplier, 4), "pc", 5, 10, False, True))
        db_session.add(Product("Pasta", "Pasta",
            db_session.get(User, 2), db_session.get(Category, 6),
            db_session.get(Supplier, 4), "pack", 0, 1, False, True))
        db_session.add(Product("Coffee", "Coffee",
            db_session.get(User, 1), db_session.get(Category, 6),
            db_session.get(Supplier, 4), "bag", 0, 1, False, True))
        db_session.add(Product("Cheese", "Cheese",
            db_session.get(User, 2), db_session.get(Category, 6),
            db_session.get(Supplier, 3), "pc", 0, 1, False, False))
        db_session.add(Product("Mustard", "Mustard",
            db_session.get(User, 1), db_session.get(Category, 6),
            db_session.get(Supplier, 3), "bottle", 0, 1, False, False))
        db_session.add(Product("Ketchup", "Ketchup",
            db_session.get(User, 1), db_session.get(Category, 6),
            db_session.get(Supplier, 3), "bottle", 0, 1, False, False))
        db_session.add(Product("Sunflower oil", "Sunflower oil",
            db_session.get(User, 2), db_session.get(Category, 6),
            db_session.get(Supplier, 4), "bottle", 0, 1, False, False))
        db_session.add(Product("Other", "Other",
            db_session.get(User, 1), db_session.get(Category, 3),
            db_session.get(Supplier, 2), "pc", 1, 2, False, False,
            False))
        db_session.commit()
# endregion


