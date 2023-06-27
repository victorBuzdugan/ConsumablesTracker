"""Test with rollbacks SQLAlchemy table mapping."""

import pytest
from sqlalchemy import insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from werkzeug.security import check_password_hash, generate_password_hash

from database import User, Category, Supplier, Product
from tests import db_session, default_user_category_supplier


pytestmark = pytest.mark.db


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
    test_user = User("__test__user__", "test_password")
    db_session.add(test_user)
    db_session.commit()
    assert test_user.id is not None, "test_user should have an id after commit"
    db_user = db_session.get(User, test_user.id)
    assert db_user.name == "__test__user__", "Wrong name"
    assert db_user.password == "test_password"
    assert db_user.password != "some_other_password"
    assert db_user.products == [], "User shouldn't have products assigned"
    assert db_user.admin is False
    assert db_user.in_use is True
    assert db_user.done_inv is True
    assert db_user.reg_req is True
    assert db_user.details is None


def test_admin_creation(db_session: Session):
    """Test user creation with admin credentials (admin: True)"""
    test_user = User("__test__adminn__", "test_password", admin=True)
    db_session.add(test_user)
    db_session.commit()
    assert db_session.get(User, test_user.id).admin is True


def test_bulk_user_insertion(db_session: Session):
    values = [{"name": f"test__user{no}", 
               "password": generate_password_hash("some_password")}
              for no in range(6)]
    db_session.execute(insert(User), values)
    db_session.commit()
    users = db_session.scalars(
        select(User).where(User.name.like("test__user%"))).all()
    assert len(users) == 6
    for user in users:
        assert check_password_hash(user.password, "some_password")
        assert user.products == []
        assert user.admin is False
        assert user.in_use is True
        assert user.done_inv is True
        assert user.reg_req is True
        assert user.details is None


@pytest.mark.xfail(raises=IntegrityError)
def test_username_duplicate(db_session: Session):
    try:
        db_session.add(User("__test__user__", "passw"))
        db_session.commit()
    except IntegrityError:
        db_session.rollback()


@pytest.mark.xfail(raises=IntegrityError)
def test_no_name(db_session: Session):
    try:
        db_session.add(User(None, "password"))
        db_session.commit()
    except IntegrityError:
        db_session.rollback()


@pytest.mark.xfail(raises=IntegrityError)
def test_no_password(db_session: Session):
    try:
        db_session.add(User("name", None))
        db_session.commit()
    except IntegrityError:
        db_session.rollback()
# endregion


# region CRUD: read and update
def test_change_username(db_session: Session):
    test_user = db_session.execute(
        select(User).filter_by(name="__test__adminn__")).scalar_one()
    test_user.name = "__test__admin__"
    assert test_user in db_session.dirty
    # autoflush after select(get) statement
    db_user = db_session.get(User, test_user.id)
    assert db_user.name == "__test__admin__"


def test_change_password(db_session: Session):
    test_user = db_session.execute(
        select(User).filter_by(name="__test__user__")).scalar_one()
    test_user.password = generate_password_hash("other_test_password")
    assert test_user in db_session.dirty
    # autoflush after select(get) statement
    db_user = db_session.get(User, test_user.id)
    assert check_password_hash(db_user.password, "other_test_password")
# endregion


# region CRUD: read and delete
def test_delete_user(db_session: Session):
    test_user = db_session.execute(
        select(User).filter_by(name="test__user0")).scalar_one()
    db_session.delete(test_user)
    db_user = db_session.execute(
        select(User).filter_by(name="test__user0")).scalar()
    assert db_user is None
# endregion
# endregion


# region: test "categories" table
def test_category_creation(db_session: Session):
    test_category = Category("__test__categoryy__",
                             description="Some description")
    db_session.add(test_category)
    db_session.commit()
    assert test_category.id is not None, \
            "test_category should have an id after commit"
    db_category = db_session.get(Category, test_category.id)
    assert db_category.name == "__test__categoryy__"
    assert db_category.products == []
    assert db_category.in_use is True
    assert db_category.description == "Some description"


def test_bulk_category_insertion(db_session: Session):
    values = [{"name": f"test__category{no}"} for no in range(6)]
    db_session.execute(insert(Category), values)
    db_session.commit()
    categories = db_session.scalars(
        select(Category).where(Category.name.like("test__category%"))).all()
    assert len(categories) == 6
    for category in categories:
        assert category.products == []
        assert category.in_use is True
        assert category.description is None


@pytest.mark.xfail(raises=IntegrityError)
def test_category_duplicate(db_session: Session):
    try:
        db_session.add(Category("__test__categoryy__"))
        db_session.commit()
    except IntegrityError:
        db_session.rollback()


@pytest.mark.xfail(raises=IntegrityError)
def test_category_no_name(db_session: Session):
    try:
        db_session.add(Category(None))
        db_session.commit()
    except IntegrityError:
        db_session.rollback()


def test_change_category_name(db_session: Session):
    test_category = db_session.execute(
        select(Category).filter_by(name="__test__categoryy__")).scalar_one()
    test_category.name = "__test__category__"
    assert test_category in db_session.dirty
    # autoflush after select(get) statement
    db_category = db_session.get(Category, test_category.id)
    assert db_category.name == "__test__category__"


def test_delete_category(db_session: Session):
    test_category = db_session.execute(
        select(Category).filter_by(name="test__category0")).scalar_one()
    db_session.delete(test_category)
    db_category = db_session.execute(
        select(Category).filter_by(name="test__category0")).scalar()
    assert db_category is None
# endregion


# region: test "suppliers" table
def test_supplier_creation(db_session: Session):
    test_supplier = Supplier("__test__supplierr__", details="Some description")
    db_session.add(test_supplier)
    db_session.commit()
    assert test_supplier.id is not None,\
            "__test__supplierr__ should have an id after commit"
    db_supplier = db_session.get(Supplier, test_supplier.id)
    assert db_supplier.name == "__test__supplierr__"
    assert db_supplier.products == []
    assert db_supplier.in_use is True
    assert db_supplier.details == "Some description"


def test_bulk_supplier_insertion(db_session: Session):
    values = [{"name": f"test__supplier{no}"} for no in range(6)]
    db_session.execute(insert(Supplier), values)
    db_session.commit()
    suppliers = db_session.scalars(
        select(Supplier).where(Supplier.name.like("test__supplier%"))).all()
    assert len(suppliers) == 6
    for supplier in suppliers:
        assert supplier.products == []
        assert supplier.in_use is True
        assert supplier.details is None


@pytest.mark.xfail(raises=IntegrityError)
def test_supplier_duplicate(db_session: Session):
    try:
        db_session.add(Supplier("__test__supplierr__"))
        db_session.commit()
    except IntegrityError:
        db_session.rollback()


@pytest.mark.xfail(raises=IntegrityError)
def test_supplier_no_name(db_session: Session):
    try:
        db_session.add(Supplier(None))
        db_session.commit()
    except IntegrityError:
        db_session.rollback()


def test_change_supplier_name(db_session: Session):
    test_supplier = db_session.execute(
        select(Supplier).filter_by(name="__test__supplierr__")).scalar_one()
    test_supplier.name = "__test__supplier__"
    assert test_supplier in db_session.dirty
    # autoflush after select(get) statement
    db_supplier = db_session.get(Supplier, test_supplier.id)
    assert db_supplier.name == "__test__supplier__"


def test_delete_supplier(db_session: Session):
    test_supplier = db_session.execute(
        select(Supplier).filter_by(name="test__supplier0")).scalar_one()
    db_session.delete(test_supplier)
    db_supplier = db_session.execute(
        select(Supplier).filter_by(name="test__supplier0")).scalar()
    assert db_supplier is None
# endregion


# region: test "products" table
def test_product_creation(db_session: Session, default_user_category_supplier):
    test_product = Product(
        name="__test__productt__",
        description="Some description",
        responsable=default_user_category_supplier[0],
        category=default_user_category_supplier[1],
        supplier=default_user_category_supplier[2],
        meas_unit="measunit",
        min_stock=10,
        ord_qty=20,
        critical=True
    )
    db_session.add(test_product)
    db_session.commit()
    assert test_product.id is not None,\
            "__test__productt__ should have an id after commit"
    db_product = db_session.get(Product, test_product.id)
    assert db_product.name == "__test__productt__"
    assert db_product.description == "Some description"
    assert db_product.responsable.name == "__test__user__"
    assert db_product.category.name == "__test__category__"
    assert db_product.supplier.name == "__test__supplier__"
    assert db_product.meas_unit == "measunit"
    assert db_product.min_stock == 10
    assert db_product.ord_qty == 20
    assert db_product.to_order is False
    assert db_product.critical is True
    assert db_product.in_use is True


def test_bulk_product_insertion(db_session: Session,
                                default_user_category_supplier):
    values = [
        {"name": f"test__product{no}",
            "description": "Some description",
            "responsable_id": default_user_category_supplier[0].id,
            "category_id": default_user_category_supplier[1].id,
            "supplier_id": default_user_category_supplier[2].id,
            "meas_unit": "measunit",
            "min_stock": 10,
            "ord_qty": 20} for no in range(6)
        ]
    db_session.execute(insert(Product), values)
    db_session.commit()
    products = db_session.scalars(
        select(Product).where(Product.name.like("test__product%"))).all()
    assert len(products) == 6
    for product in products:
        assert product.description == "Some description"
        assert product.responsable.name == "__test__user__"
        assert product.category.name == "__test__category__"
        assert product.supplier.name == "__test__supplier__"
        assert product.meas_unit == "measunit"
        assert product.min_stock == 10
        assert product.ord_qty == 20
        assert product.to_order is False
        assert product.critical is False
        assert product.in_use is True


@pytest.mark.xfail(raises=IntegrityError)
def test_product_duplicate_name(db_session: Session,
                                default_user_category_supplier):
    test_product = Product(
        name="__test__productt__",
        description="Some description",
        responsable=default_user_category_supplier[0],
        category=default_user_category_supplier[1],
        supplier=default_user_category_supplier[2],
        meas_unit="measunit",
        min_stock=1,
        ord_qty=1
    )
    try:
        db_session.add(test_product)
        db_session.commit()
    except IntegrityError:
        db_session.rollback()


@pytest.mark.xfail(raises=IntegrityError)
def test_product_no_name(db_session: Session,
                         default_user_category_supplier):
    test_product = Product(
        name=None,
        description="Some description",
        responsable=default_user_category_supplier[0],
        category=default_user_category_supplier[1],
        supplier=default_user_category_supplier[2],
        meas_unit="measunit",
        min_stock=2,
        ord_qty=2
    )
    try:
        db_session.add(test_product)
        db_session.commit()
    except IntegrityError:
        db_session.rollback()


@pytest.mark.xfail(raises=IntegrityError)
def test_product_no_description(db_session: Session,
                                default_user_category_supplier):
    test_product = Product(
        name="__test__producttt__",
        description=None,
        responsable=default_user_category_supplier[0],
        category=default_user_category_supplier[1],
        supplier=default_user_category_supplier[2],
        meas_unit="measunit",
        min_stock=3,
        ord_qty=3
    )
    try:
        db_session.add(test_product)
        db_session.commit()
    except IntegrityError:
        db_session.rollback()


@pytest.mark.xfail(raises=IntegrityError)
def test_product_no_responsable(db_session: Session,
                                default_user_category_supplier):
    test_product = Product(
        name="__test__producttt__",
        description="Some description",
        responsable=None,
        category=default_user_category_supplier[1],
        supplier=default_user_category_supplier[2],
        meas_unit="measunit",
        min_stock=4,
        ord_qty=4
    )
    try:
        db_session.add(test_product)
        db_session.commit()
    except IntegrityError:
        db_session.rollback()


@pytest.mark.xfail(raises=IntegrityError)
def test_product_no_category(db_session: Session,
                             default_user_category_supplier):
    test_product = Product(
        name="__test__producttt__",
        description="Some description",
        responsable=default_user_category_supplier[0],
        category=None,
        supplier=default_user_category_supplier[2],
        meas_unit="measunit",
        min_stock=5,
        ord_qty=5,
    )
    try:
        db_session.add(test_product)
        db_session.commit()
    except IntegrityError:
        db_session.rollback()


@pytest.mark.xfail(raises=IntegrityError)
def test_product_no_supplier(db_session: Session,
                             default_user_category_supplier):
    test_product = Product(
        name="__test__producttt__",
        description="Some description",
        responsable=default_user_category_supplier[0],
        category=default_user_category_supplier[1],
        supplier=None,
        meas_unit="measunit",
        min_stock=6,
        ord_qty=6
    )
    try:
        db_session.add(test_product)
        db_session.commit()
    except IntegrityError:
        db_session.rollback()


@pytest.mark.xfail(raises=IntegrityError)
def test_product_no_meas_unit(db_session: Session,
                              default_user_category_supplier):
    test_product = Product(
        name="__test__producttt__",
        description="Some description",
        responsable=default_user_category_supplier[0],
        category=default_user_category_supplier[1],
        supplier=default_user_category_supplier[2],
        meas_unit=None,
        min_stock=7,
        ord_qty=7
    )
    try:
        db_session.add(test_product)
        db_session.commit()
    except IntegrityError:
        db_session.rollback()


@pytest.mark.xfail(raises=IntegrityError)
def test_product_no_min_stock(db_session: Session,
                              default_user_category_supplier):
    test_product = Product(
        name="__test__producttt__",
        description="Some description",
        responsable=default_user_category_supplier[0],
        category=default_user_category_supplier[1],
        supplier=default_user_category_supplier[2],
        meas_unit="measunit",
        min_stock=None,
        ord_qty=8,
    )
    try:
        db_session.add(test_product)
        db_session.commit()
    except IntegrityError:
        db_session.rollback()


@pytest.mark.xfail(raises=IntegrityError)
def test_product_no_ord_qty(db_session: Session,
                            default_user_category_supplier):
    test_product = Product(
        name="__test__producttt__",
        description="Some description",
        responsable=default_user_category_supplier[0],
        category=default_user_category_supplier[1],
        supplier=default_user_category_supplier[2],
        meas_unit="measunit",
        min_stock=9,
        ord_qty=None,
    )
    try:
        db_session.add(test_product)
        db_session.commit()
    except IntegrityError:
        db_session.rollback()


def test_change_product_name(db_session: Session):
    test_product = db_session.execute(
        select(Product).filter_by(name="__test__productt__")).scalar_one()
    test_product.name = "__test__product__"
    assert test_product in db_session.dirty
    # autoflush after select(get) statement
    db_product = db_session.get(Product, test_product.id)
    assert db_product.name == "__test__product__"


def test_delete_product(db_session: Session):
    test_product = db_session.execute(
        select(Product).filter_by(name="test__product0")).scalar_one()
    db_session.delete(test_product)
    db_product = db_session.execute(
        select(Product).filter_by(name="test__product0")).scalar()
    assert db_product is None
# endregion
