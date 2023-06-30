"""Test SQLAlchemy tables mapping."""

import pytest
from sqlalchemy import insert, select
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from database import dbSession, User, Category, Supplier, Product
from tests import create_test_db


pytestmark = pytest.mark.db


# region: test "users" table
def test_user_creation(create_test_db):
    """Test default user creation and database insertion."""
    user = User("user11", generate_password_hash("P@ssw0rd"))
    with dbSession() as db_session:
        db_session.add(user)
        db_session.commit()
        assert user.id is not None
        db_user = db_session.get(User, user.id)
        assert db_user.products == []
    assert db_user.name == user.name
    assert check_password_hash(db_user.password, "P@ssw0rd")
    assert db_user.admin is False
    assert db_user.in_use is True
    assert db_user.done_inv is True
    assert db_user.reg_req is True
    assert db_user.req_inv is False
    assert db_user.details is None


def test_change_username(create_test_db):
    with dbSession() as db_session:
        user = db_session.scalar(
            select(User).filter_by(name="user11"))
        user.name = "user1"
        assert user in db_session.dirty
        db_session.commit()
        db_user = db_session.get(User, user.id)
    assert db_user.name == "user1"


def test_change_password(create_test_db):
    with dbSession() as db_session:
        user = db_session.scalar(
            select(User).filter_by(name="user1"))
        user.password = generate_password_hash("P@ssw0rd1")
        assert user in db_session.dirty
        db_session.commit()
        db_user = db_session.get(User, user.id)
    assert check_password_hash(db_user.password, "P@ssw0rd1")


@pytest.mark.xfail(raises=IntegrityError)
def test_no_name(create_test_db):
    with dbSession() as db_session:
        try:
            db_session.add(User(None, "password"))
            db_session.commit()
        except IntegrityError:
            db_session.rollback()


@pytest.mark.xfail(raises=IntegrityError)
def test_no_password(create_test_db):
    with dbSession() as db_session:
        try:
            db_session.add(User("name", None))
            db_session.commit()
        except IntegrityError:
            db_session.rollback()


@pytest.mark.xfail(raises=IntegrityError)
def test_username_duplicate(create_test_db):
    with dbSession() as db_session:
        try:
            db_session.add(User("user1", "passw"))
            db_session.commit()
        except IntegrityError:
            db_session.rollback()


def test_bulk_user_insertion(create_test_db):
    values = [{"name": f"user{no}", 
               "password": generate_password_hash(f"P@ssw0rd{no}")}
              for no in range(2,7)]
    with dbSession() as db_session:
        db_session.execute(insert(User), values)
        db_session.commit()
        users = db_session.scalars(
            select(User).where(User.name.like("user%"))).all()
        assert len(users) == 6
        for user in users:
            assert check_password_hash(user.password, f"P@ssw0rd{user.id}")
            assert user.products == []
            assert user.admin is False
            assert user.in_use is True
            assert user.done_inv is True
            assert user.reg_req is True
            assert user.req_inv is False
            assert user.details is None


def test_admin_creation(create_test_db):
    """Test user creation with admin credentials (admin: True)"""
    user = User(
        "admin1",
        generate_password_hash("P@ssw0rd"),
        admin=True)
    with dbSession() as db_session:
        db_session.add(user)
        db_session.commit()
        assert db_session.get(User, user.id).admin is True


def test_delete_user(create_test_db):
    with dbSession() as db_session:
        user = db_session.scalar(
            select(User).filter_by(name="user6"))
        db_session.delete(user)
        db_session.commit()
        db_user = db_session.get(User, user.id)
        assert db_user is None
# endregion


# region: test "categories" table
def test_category_creation(create_test_db):
    category = Category(
        "category11",
        description="Some description")
    with dbSession() as db_session:
        db_session.add(category)
        db_session.commit()
        assert category.id is not None
        db_category = db_session.get(Category, category.id)
        assert db_category.name == category.name
        assert db_category.products == []
        assert db_category.in_use is True
        assert db_category.description == category.description


def test_change_category_name(create_test_db):
    with dbSession() as db_session:
        category = db_session.scalar(
            select(Category).filter_by(name="category11"))
        category.name = "category1"
        assert category in db_session.dirty
        db_session.commit()
        db_category = db_session.get(Category, category.id)
        assert db_category.name == "category1"
        

@pytest.mark.xfail(raises=IntegrityError)
def test_category_duplicate(create_test_db):
    with dbSession() as db_session:
        try:
            db_session.add(Category("category1"))
            db_session.commit()
        except IntegrityError:
            db_session.rollback()


@pytest.mark.xfail(raises=IntegrityError)
def test_category_no_name(create_test_db):
    with dbSession() as db_session:
        try:
            db_session.add(Category(None))
            db_session.commit()
        except IntegrityError:
            db_session.rollback()


def test_bulk_category_insertion(create_test_db):
    values = [{"name": f"category{no}"} for no in range(2,7)]
    with dbSession() as db_session:
        db_session.execute(insert(Category), values)
        db_session.commit()
        categories = db_session.scalars(
            select(Category).where(Category.name.like("category%"))).all()
        assert len(categories) == 6
        for category in categories:
            assert category.products == []
            assert category.in_use is True
            if category.id == 1:
                continue
            assert category.description is None


def test_delete_category(create_test_db):
    with dbSession() as db_session:
        category = db_session.scalar(
            select(Category).filter_by(name="category6"))
        db_session.delete(category)
        db_session.commit()
        db_category = db_session.scalar(
            select(Category).filter_by(name="category6"))
    assert db_category is None
# endregion


# region: test "suppliers" table
def test_supplier_creation(create_test_db):
    supplier = Supplier("supplier11", details="Some description")
    with dbSession() as db_session:
        db_session.add(supplier)
        db_session.commit()
        assert supplier.id is not None
        db_supplier = db_session.get(Supplier, supplier.id)
        assert db_supplier.name == supplier.name
        assert db_supplier.products == []
        assert db_supplier.in_use is True
        assert db_supplier.details == supplier.details


def test_change_supplier_name(create_test_db):
    with dbSession() as db_session:
        supplier = db_session.scalar(
            select(Supplier).filter_by(name="supplier11"))
        supplier.name = "supplier1"
        assert supplier in db_session.dirty
        db_session.commit()
        db_supplier = db_session.get(Supplier, supplier.id)
        assert db_supplier.name == "supplier1"


@pytest.mark.xfail(raises=IntegrityError)
def test_supplier_duplicate(create_test_db):
    with dbSession() as db_session:
        try:
            db_session.add(Supplier("supplier1"))
            db_session.commit()
        except IntegrityError:
            db_session.rollback()


@pytest.mark.xfail(raises=IntegrityError)
def test_supplier_no_name(create_test_db):
    with dbSession() as db_session:
        try:
            db_session.add(Supplier(None))
            db_session.commit()
        except IntegrityError:
            db_session.rollback()


def test_bulk_supplier_insertion(create_test_db):
    values = [{"name": f"supplier{no}"} for no in range(2,7)]
    with dbSession() as db_session:
        db_session.execute(insert(Supplier), values)
        db_session.commit()
        suppliers = db_session.scalars(
            select(Supplier).where(Supplier.name.like("supplier%"))).all()
        assert len(suppliers) == 6
        for supplier in suppliers:
            assert supplier.products == []
            assert supplier.in_use is True
            if supplier.id == 1:
                continue
            assert supplier.details is None


def test_delete_supplier(create_test_db):
    with dbSession() as db_session:
        supplier = db_session.scalar(
            select(Supplier).filter_by(name="supplier6"))
        db_session.delete(supplier)
        db_session.commit()
        db_supplier = db_session.scalar(
            select(Supplier).filter_by(name="supplier6"))
    assert db_supplier is None
# endregion


# region: test "products" table
def test_product_creation(create_test_db):
    with dbSession() as db_session:
        product = Product(
            name="product11",
            description="Some description1",
            responsable=db_session.get(User, 1),
            category=db_session.get(Category, 1),
            supplier=db_session.get(Supplier, 1),
            meas_unit="measunit",
            min_stock=10,
            ord_qty=20,
            critical=False)
        db_session.add(product)
        db_session.commit()
        assert product.id is not None
        db_product = db_session.get(Product, product.id)
        assert db_product.name == "product11"
        assert db_product.description == "Some description1"
        assert db_product.responsable.name == "user1"
        assert db_product.category.name == "category1"
        assert db_product.supplier.name == "supplier1"
        assert db_product.meas_unit == "measunit"
        assert db_product.min_stock == 10
        assert db_product.ord_qty == 20
        assert db_product.to_order is False
        assert db_product.critical is False
        assert db_product.in_use is True


def test_change_product_name(create_test_db):
    with dbSession() as db_session:
        product = db_session.scalar(
            select(Product).filter_by(name="product11"))
        product.name = "product1"
        assert product in db_session.dirty
        db_session.commit()
        db_product = db_session.get(Product, product.id)
        assert db_product.name == "product1"


@pytest.mark.xfail(raises=IntegrityError)
def test_product_duplicate_name(create_test_db):
    with dbSession() as db_session:
        product = Product(
            name="product1",
            description="Some description",
            responsable=db_session.get(User, 1),
            category=db_session.get(Category, 1),
            supplier=db_session.get(Supplier, 1),
            meas_unit="measunit",
            min_stock=1,
            ord_qty=1
        )
        try:
            db_session.add(product)
            db_session.commit()
        except IntegrityError:
            db_session.rollback()


@pytest.mark.xfail(raises=IntegrityError)
def test_product_no_name(create_test_db):
    with dbSession() as db_session:
        product = Product(
            name=None,
            description="Some description",
            responsable=db_session.get(User, 1),
            category=db_session.get(Category, 1),
            supplier=db_session.get(Supplier, 1),
            meas_unit="measunit",
            min_stock=2,
            ord_qty=2
        )
        try:
            db_session.add(product)
            db_session.commit()
        except IntegrityError:
            db_session.rollback()


@pytest.mark.xfail(raises=IntegrityError)
def test_product_no_description(create_test_db):
    with dbSession() as db_session:
        product = Product(
            name="__test__producttt__",
            description=None,
            responsable=db_session.get(User, 1),
            category=db_session.get(Category, 1),
            supplier=db_session.get(Supplier, 1),
            meas_unit="measunit",
            min_stock=3,
            ord_qty=3
        )
        try:
            db_session.add(product)
            db_session.commit()
        except IntegrityError:
            db_session.rollback()


@pytest.mark.xfail(raises=IntegrityError)
def test_product_no_responsable(create_test_db):
    with dbSession() as db_session:
        product = Product(
            name="__test__producttt__",
            description="Some description",
            responsable=None,
            category=db_session.get(Category, 1),
            supplier=db_session.get(Supplier, 1),
            meas_unit="measunit",
            min_stock=4,
            ord_qty=4
        )
        try:
            db_session.add(product)
            db_session.commit()
        except IntegrityError:
            db_session.rollback()


@pytest.mark.xfail(raises=IntegrityError)
def test_product_no_category(create_test_db):
    with dbSession() as db_session:
        product = Product(
            name="__test__producttt__",
            description="Some description",
            responsable=db_session.get(User, 1),
            category=None,
            supplier=db_session.get(Supplier, 1),
            meas_unit="measunit",
            min_stock=5,
            ord_qty=5,
        )
        try:
            db_session.add(product)
            db_session.commit()
        except IntegrityError:
            db_session.rollback()


@pytest.mark.xfail(raises=IntegrityError)
def test_product_no_supplier(create_test_db):
    with dbSession() as db_session:
        product = Product(
            name="__test__producttt__",
            description="Some description",
            responsable=db_session.get(User, 1),
            category=db_session.get(Category, 1),
            supplier=None,
            meas_unit="measunit",
            min_stock=6,
            ord_qty=6
        )
        try:
            db_session.add(product)
            db_session.commit()
        except IntegrityError:
            db_session.rollback()


@pytest.mark.xfail(raises=IntegrityError)
def test_product_no_meas_unit(create_test_db):
    with dbSession() as db_session:
        product = Product(
            name="__test__producttt__",
            description="Some description",
            responsable=db_session.get(User, 1),
            category=db_session.get(Category, 1),
            supplier=db_session.get(Supplier, 1),
            meas_unit=None,
            min_stock=7,
            ord_qty=7
        )
        try:
            db_session.add(product)
            db_session.commit()
        except IntegrityError:
            db_session.rollback()


@pytest.mark.xfail(raises=IntegrityError)
def test_product_no_min_stock(create_test_db):
    with dbSession() as db_session:
        product = Product(
            name="__test__producttt__",
            description="Some description",
            responsable=db_session.get(User, 1),
            category=db_session.get(Category, 1),
            supplier=db_session.get(Supplier, 1),
            meas_unit="measunit",
            min_stock=None,
            ord_qty=8,
        )
        try:
            db_session.add(product)
            db_session.commit()
        except IntegrityError:
            db_session.rollback()


@pytest.mark.xfail(raises=IntegrityError)
def test_product_no_ord_qty(create_test_db):
    with dbSession() as db_session:
        product = Product(
            name="__test__producttt__",
            description="Some description",
            responsable=db_session.get(User, 1),
            category=db_session.get(Category, 1),
            supplier=db_session.get(Supplier, 1),
            meas_unit="measunit",
            min_stock=9,
            ord_qty=None,
        )
        try:
            db_session.add(product)
            db_session.commit()
        except IntegrityError:
            db_session.rollback()


def test_bulk_product_insertion(create_test_db):
    with dbSession() as db_session:
        values_user1 = [
            {"name": f"product{no}",
                "description": f"Some description{no}",
                "responsable_id": 1,
                "category_id": 1,
                "supplier_id": 1,
                "meas_unit": "measunit",
                "min_stock": 10,
                "ord_qty": 20} for no in range(2,7)
            ]
        db_session.execute(insert(Product), values_user1)
        db_session.commit()
        products = db_session.scalars(
            select(Product).where(Product.name.like("product%"))).all()
        assert len(products) == 6
        for product in products:
            assert product.description == f"Some description{product.id}"
            assert product.responsable.name == "user1"
            assert product.category.name == "category1"
            assert product.supplier.name == "supplier1"
            assert product.meas_unit == "measunit"
            assert product.min_stock == 10
            assert product.ord_qty == 20
            assert product.to_order is False
            assert product.critical is False
            assert product.in_use is True


def test_delete_product(create_test_db):
    with dbSession() as db_session:
        product = db_session.scalar(
            select(Product).filter_by(name="product6"))
        db_session.delete(product)
        db_session.commit()
        db_product = db_session.scalar(
            select(Product).filter_by(name="product6"))
        assert db_product is None
# endregion
