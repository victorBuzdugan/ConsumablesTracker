"""Test SQLAlchemy tables mapping."""

import pytest
from sqlalchemy import insert, select
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from database import dbSession, User, Category, Supplier, Product
from tests import (admin_logged_in, client, create_test_categories,
                   create_test_db, create_test_suppliers, create_test_users,
                   user_logged_in, create_test_products)


pytestmark = pytest.mark.db


# region: test "users" table
def test_user_creation(client):
    """Test default user creation and database insertion."""
    user = User("user11", generate_password_hash("P@ssw0rd"))
    with dbSession() as db_session:
        db_session.add(user)
        db_session.commit()
        assert user.id is not None
        db_user = db_session.get(User, user.id)
        assert db_user
        assert db_user.name == user.name
        assert check_password_hash(db_user.password, "P@ssw0rd")
        assert db_user.admin is False
        assert db_user.in_use is True
        assert db_user.done_inv is True
        assert db_user.reg_req is True
        assert db_user.req_inv is False
        assert db_user.details is None
        # teardown
        db_session.delete(db_user)
        db_session.commit()
        assert not db_session.get(User, user.id)


def test_change_username(client):
    old_name = "user1"
    new_name = "user11"
    with dbSession() as db_session:
        user = db_session.scalar(
            select(User).filter_by(name=old_name))
        user.name = new_name
        assert user in db_session.dirty
        db_session.commit()
        db_user = db_session.get(User, user.id)
        assert db_user.name == new_name
        # teardown and test username
        db_user.username = old_name
        db_session.commit()
        assert db_session.get(User, db_user.id).name == old_name


def test_change_password(client):
    with dbSession() as db_session:
        user = db_session.scalar(
            select(User).filter_by(name="user1"))
        user.password = generate_password_hash("P@ssw0rd")
        assert user in db_session.dirty
        db_session.commit()
        db_user = db_session.get(User, user.id)
        assert check_password_hash(db_user.password, "P@ssw0rd")

        # teardown
        db_user.password = generate_password_hash("Q!111111")
        assert db_user in db_session.dirty
        db_session.commit()
        assert check_password_hash(db_session.get(User, user.id).password, "Q!111111")


@pytest.mark.xfail(raises=IntegrityError)
def test_no_name(client):
    with dbSession() as db_session:
        try:
            db_session.add(User(None, "password"))
            db_session.commit()
        except IntegrityError:
            db_session.rollback()


@pytest.mark.xfail(raises=IntegrityError)
def test_no_password(client):
    with dbSession() as db_session:
        try:
            db_session.add(User("name", None))
            db_session.commit()
        except IntegrityError:
            db_session.rollback()


@pytest.mark.xfail(raises=IntegrityError)
def test_username_duplicate(client):
    with dbSession() as db_session:
        try:
            db_session.add(User("user1", "passw"))
            db_session.commit()
        except IntegrityError:
            db_session.rollback()


def test_bulk_user_insertion(client):
    values = [{"name": f"user__{no}",
               "password": generate_password_hash(f"P@ssw0rd{no}")}
              for no in range(7,10)]
    with dbSession() as db_session:
        db_session.execute(insert(User), values)
        db_session.commit()
        users = db_session.scalars(
            select(User).where(User.name.like("user__%"))).all()
        assert len(users) == 3
        for user in users:
            assert check_password_hash(user.password, f"P@ssw0rd{user.id}")
            assert user.products == []
            assert user.admin is False
            assert user.in_use is True
            assert user.done_inv is True
            assert user.reg_req is True
            assert user.req_inv is False
            assert user.details is None
            # teardown
            db_session.delete(user)
        db_session.commit()


def test_admin_creation(client):
    """Test user creation with admin credentials (admin: True)"""
    user = User(
        "admin1",
        generate_password_hash("P@ssw0rd"),
        admin=True,
        reg_req=False)
    with dbSession() as db_session:
        db_session.add(user)
        db_session.commit()
        assert db_session.get(User, user.id).admin is True
        # teardown
        db_session.delete(db_session.get(User, user.id))
        db_session.commit()


def test_inv_status_property(client):
    with dbSession() as db_session:
        user = db_session.get(User, 1)
        assert user.inv_status == "sent"
        user.done_inv = False
        db_session.commit()
        db_user = db_session.get(User, 1)
        assert db_user.inv_status == "not sent"
        db_user.done_inv = True
        db_session.commit()


@pytest.mark.xfail(raises=ValueError)
def test_delete_user_with_products_attached(client):
    with dbSession() as db_session:
        user = db_session.get(User, 1)
        try:
            db_session.delete(user)
            db_session.commit()
        except ValueError as err:
            db_session.rollback()
            assert "user can't be deleted or does not exist" in err.args
            assert db_session.get(User, user.id)


#region: validators
@pytest.mark.xfail(raises=ValueError)
@pytest.mark.parametrize(
    ("user_id", "err_message"), (
    (5, "user with pending registration can't have products attached"),
    (6, "'retired' users can't have products attached"),
    ))
def test_validate_user_products(client, user_id, err_message):
    with dbSession() as db_session:
        product = db_session.get(Product, 1)
        user = db_session.get(User, user_id)
        try:
            user.products.append(product)
            # product.responsable_id = user_id
        except ValueError as err:
            db_session.rollback()
            assert err_message in err.args
            assert db_session.get(Product, 1).responsable == product.responsable


@pytest.mark.xfail(raises=ValueError)
def test_validate_admin(client):
    with dbSession() as db_session:
        user = db_session.get(User, 5)
        assert user.reg_req
        try:
            user.admin = True
        except ValueError as err:
            db_session.rollback()
            assert "user with pending registration can't be admin" in err.args
            assert not user.admin


@pytest.mark.xfail(raises=ValueError)
def test_validate_in_use(client):
    with dbSession() as db_session:
        user = db_session.get(User, 1)
        assert user.in_use
        try:
            user.in_use = False
        except ValueError as err:
            db_session.rollback()
            assert "user can't 'retire' if is responsible for products" in err.args
            assert user.in_use


def test_validate_ok_in_use(client):
    with dbSession() as db_session:
        values = [{
            "name": "temp_user",
            "password": generate_password_hash("P@ssw0rd"),
            "done_inv": False,
            "reg_req": True,
            "req_inv": True,
            }]
    with dbSession() as db_session:
        db_session.execute(insert(User), values)
        db_session.commit()
        user = db_session.scalar(select(User).filter_by(name="temp_user"))
        assert user.in_use
        assert not user.done_inv
        assert user.reg_req
        assert user.req_inv
        user.in_use = False
        db_session.commit()
        user = db_session.scalar(select(User).filter_by(name="temp_user"))
        assert not user.in_use
        assert user.done_inv
        assert not user.reg_req
        assert not user.req_inv
        db_session.delete(user)
        db_session.commit()
        assert not db_session.scalar(select(User).filter_by(name="temp_user"))


@pytest.mark.xfail(raises=ValueError)
@pytest.mark.parametrize(
    ("user_id", "err_message"), (
    (5, "user with pending registration can't check inventory"),
    (6, "'retired' user can't check inventory"),
    (5, "user without products attached can't check inventory"),
    ))
def test_validate_done_inv(client, user_id, err_message):
    with dbSession() as db_session:
        user = db_session.get(User, user_id)
        try:
            user.done_inv = False
        except ValueError as err:
            db_session.rollback()
            assert err_message in err.args
            if user.id == 5 and user.reg_req:
                user.reg_req = False
            elif user.id == 5:
                user.reg_req = True
            db_session.commit()


def test_validate_ok_done_inv(client):
    with dbSession() as db_session:
        user = db_session.get(User, 3)
        assert user.done_inv == True
        assert user.req_inv == False
        user.req_inv = True

        user.done_inv = False
        assert user.req_inv == False


@pytest.mark.xfail(raises=ValueError)
@pytest.mark.parametrize(
    ("user_id", "err_message"), (
    (1, "admin users can't request registration"),
    (3, "users with products attached can't request registration"),
    (6, "'retired' users can't request registration"),
    ))
def test_validate_reg_req(client, user_id, err_message):
    with dbSession() as db_session:
        user = db_session.get(User, user_id)
        assert not user.reg_req
        try:
            user.reg_req = True
        except ValueError as err:
            db_session.rollback()
            assert err_message in err.args


@pytest.mark.xfail(raises=ValueError)
@pytest.mark.parametrize(
    ("user_id", "err_message"), (
    (1, "admins don't need to request inventorying"),
    (6, "'retired' users can't request inventorying"),
    (5, "user with pending registration can't request inventorying"),
    (3, "user can allready check inventory"),
    (5, "users without products can't request inventorying"),
    ))
def test_validate_req_inv(client, user_id, err_message):
    with dbSession() as db_session:
        user = db_session.get(User, user_id)
        assert not user.req_inv
        try:
            user.req_inv = True
        except ValueError as err:
            db_session.rollback()
            assert err_message in err.args

            if user.id == 5 and user.reg_req:
                user.reg_req = False
                db_session.get(User, 3).done_inv = False
            elif user.id == 5:
                user.reg_req = True
                db_session.get(User, 3).done_inv = True
            db_session.commit()


@pytest.mark.xfail(raises=ValueError)
def test_admin_request_inventory(client):
    with dbSession() as db_session:
        user = db_session.get(User, 1)
        assert user.admin
        try:
            user.req_inv = True
        except ValueError:
            assert not db_session.get(User, 1).req_inv
# endregion
# endregion


# region: test "categories" table
def test_category_creation(client):
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
        # teardown
        db_session.delete(db_category)
        db_session.commit()
        assert not db_session.get(Category, db_category.id)


def test_change_category_name(client):
    old_name = "Household"
    new_name = "category1"
    with dbSession() as db_session:
        category = db_session.scalar(
            select(Category).filter_by(name=old_name))
        category.name = new_name
        assert category in db_session.dirty
        db_session.commit()
        db_category = db_session.get(Category, category.id)
        assert db_category.name == new_name
        # teardown
        db_category.name = old_name
        db_session.commit()
        assert db_session.get(Category, category.id).name == old_name


@pytest.mark.xfail(raises=IntegrityError)
def test_category_duplicate(client):
    with dbSession() as db_session:
        try:
            db_session.add(Category("Household"))
            db_session.commit()
        except IntegrityError:
            db_session.rollback()


@pytest.mark.xfail(raises=IntegrityError)
def test_category_no_name(client):
    with dbSession() as db_session:
        try:
            db_session.add(Category(None))
            db_session.commit()
        except IntegrityError:
            db_session.rollback()


def test_bulk_category_insertion(client):
    values = [{"name": f"category{no}"} for no in range(1,4)]
    with dbSession() as db_session:
        db_session.execute(insert(Category), values)
        db_session.commit()
        categories = db_session.scalars(
            select(Category).where(Category.name.like("category%"))).all()
        assert len(categories) == 3
        for category in categories:
            assert category.products == []
            assert category.in_use is True
            assert category.description is None
            # teardown
            db_session.delete(category)
        db_session.commit()


@pytest.mark.xfail(raises=ValueError)
def test_delete_category_with_products_attached(client):
    with dbSession() as db_session:
        category = db_session.get(Category, 1)
        try:
            db_session.delete(category)
            db_session.commit()
        except ValueError as err:
            db_session.rollback()
            assert "category can't be deleted or does not exist" in err.args
            assert db_session.get(Category, category.id)
# endregion


# region: test "suppliers" table
def test_supplier_creation(client):
    supplier = Supplier("supplier1", details="Some description")
    with dbSession() as db_session:
        db_session.add(supplier)
        db_session.commit()
        assert supplier.id is not None
        db_supplier = db_session.get(Supplier, supplier.id)
        assert db_supplier.name == supplier.name
        assert db_supplier.products == []
        assert db_supplier.in_use is True
        assert db_supplier.details == supplier.details
        # teardown
        db_session.delete(db_supplier)
        db_session.commit()
        assert not db_session.get(Supplier, db_supplier.id)


def test_change_supplier_name(client):
    old_name = "Amazon"
    new_name = "supplier1"
    with dbSession() as db_session:
        supplier = db_session.scalar(
            select(Supplier).filter_by(name=old_name))
        supplier.name = new_name
        assert supplier in db_session.dirty
        db_session.commit()
        db_supplier = db_session.get(Supplier, supplier.id)
        assert db_supplier.name == new_name
        # teardown
        db_supplier.name = old_name
        db_session.commit()
        assert db_session.get(Supplier, db_supplier.id).name == old_name


@pytest.mark.xfail(raises=IntegrityError)
def test_supplier_duplicate(client):
    with dbSession() as db_session:
        try:
            db_session.add(Supplier("Amazon"))
            db_session.commit()
        except IntegrityError:
            db_session.rollback()


@pytest.mark.xfail(raises=IntegrityError)
def test_supplier_no_name(client):
    with dbSession() as db_session:
        try:
            db_session.add(Supplier(None))
            db_session.commit()
        except IntegrityError:
            db_session.rollback()


def test_bulk_supplier_insertion(client):
    values = [{"name": f"supplier{no}"} for no in range(1,4)]
    with dbSession() as db_session:
        db_session.execute(insert(Supplier), values)
        db_session.commit()
        suppliers = db_session.scalars(
            select(Supplier).where(Supplier.name.like("supplier%"))).all()
        assert len(suppliers) == 3
        for supplier in suppliers:
            assert supplier.products == []
            assert supplier.in_use is True
            if supplier.id == 1:
                continue
            assert supplier.details is None
            # teardown
            db_session.delete(supplier)
        db_session.commit()


@pytest.mark.xfail(raises=ValueError)
def test_delete_supplier_with_products_attached(client):
    with dbSession() as db_session:
        supplier = db_session.get(Supplier, 1)
        try:
            db_session.delete(supplier)
            db_session.commit()
        except ValueError as err:
            db_session.rollback()
            assert "supplier can't be deleted or does not exist" in err.args
            assert db_session.get(Supplier, supplier.id)
# endregion


# region: test "products" table
def test_product_creation(client):
    with dbSession() as db_session:
        user = db_session.get(User, 1)
        category = db_session.get(Category, 1)
        supplier = db_session.get(Supplier, 1)
        product = Product(
            name="product11",
            description="Some description1",
            responsable=user,
            category=category,
            supplier=supplier,
            meas_unit="measunit",
            min_stock=10,
            ord_qty=20,
            critical=False)
        db_session.add(product)
        db_session.commit()
        assert product.id is not None
        db_product = db_session.get(Product, product.id)
        assert db_product.name == product.name
        assert db_product.description == product.description
        assert db_product.responsable.name == user.name
        assert db_product.category.name == category.name
        assert db_product.supplier.name == supplier.name
        assert db_product.meas_unit == product.meas_unit
        assert db_product.min_stock == product.min_stock
        assert db_product.ord_qty == product.ord_qty
        assert db_product.to_order == product.to_order
        assert db_product.critical == product.critical
        assert db_product.in_use == product.in_use
        # teardown
        db_session.delete(db_product)
        db_session.commit()
        assert not db_session.get(Product, db_product.id)


def test_change_product_name(client):
    old_name = "Toilet paper"
    new_name = "product1"
    with dbSession() as db_session:
        product = db_session.scalar(
            select(Product).filter_by(name=old_name))
        product.name = new_name
        assert product in db_session.dirty
        db_session.commit()
        db_product = db_session.get(Product, product.id)
        assert db_product.name == new_name
        # teardown
        db_product.name = old_name
        db_session.commit()
        assert db_session.get(Product, db_product.id).name == old_name


@pytest.mark.xfail(raises=IntegrityError)
def test_product_duplicate_name(client):
    with dbSession() as db_session:
        product = Product(
            name="Toilet paper",
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
def test_product_no_name(client):
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
def test_product_no_description(client):
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


@pytest.mark.xfail(raises=ValueError)
def test_product_no_responsable(client):
    with dbSession() as db_session:
        try:
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
        except ValueError as err:
            db_session.rollback()
            assert "user does not exist" in err.args


@pytest.mark.xfail(raises=ValueError)
def test_product_no_category(client):
    with dbSession() as db_session:
        try:
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
        except ValueError as err:
            db_session.rollback()
            assert "category does not exist" in err.args


@pytest.mark.xfail(raises=ValueError)
def test_product_no_supplier(client):
    with dbSession() as db_session:
        try:
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
        except ValueError as err:
            db_session.rollback()
            assert "supplier does not exist" in err.args


@pytest.mark.xfail(raises=IntegrityError)
def test_product_no_meas_unit(client):
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
def test_product_no_min_stock(client):
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
def test_product_no_ord_qty(client):
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


def test_bulk_product_insertion(client):
    with dbSession() as db_session:
        last_id = db_session.scalar(
            select(Product).order_by(Product.id.desc())).id
        user = db_session.get(User, 1)
        category = db_session.get(Category, 1)
        supplier = db_session.get(Supplier, 1)
        values = [
            {"name": f"product{no}",
                "description": f"Some description{no}",
                "responsable_id": 1,
                "category_id": 1,
                "supplier_id": 1,
                "meas_unit": "measunit",
                "min_stock": 10,
                "ord_qty": 20} for no in range(last_id + 1, last_id + 4)
            ]
        db_session.execute(insert(Product), values)
        db_session.commit()
        products = db_session.scalars(
            select(Product).where(Product.name.like("product%"))).all()
        assert len(products) == 3
        for product in products:
            assert product.description == f"Some description{product.id}"
            assert product.responsable.name == user.name
            assert product.category.name == category.name
            assert product.supplier.name == supplier.name
            assert product.meas_unit == values[0].get("meas_unit")
            assert product.min_stock == values[0].get("min_stock")
            assert product.ord_qty == values[0].get("ord_qty")
            assert product.to_order is False
            assert product.critical is False
            assert product.in_use is True
            # teardown
            db_session.delete(product)
        db_session.commit()


def test_product_change_responsible(client):
    with dbSession() as db_session:
        product = db_session.get(Product, 1)
        old_user = product.responsable
        if old_user.id == 1:
            new_user = db_session.get(User, 2)
        else:
            new_user = db_session.get(User, 1)
        product.responsable = new_user
        db_session.commit()
        db_product = db_session.get(Product, product.id)
        assert db_product.responsable == db_session.get(User, new_user.id)
        db_product.responsable = db_session.get(User, old_user.id)
        db_session.commit()
        assert db_session.get(Product, product.id).responsable == db_session.get(User, old_user.id)


def test_product_change_category(client):
    with dbSession() as db_session:
        product = db_session.get(Product, 1)
        old_category = product.category
        if old_category.id == 1:
            new_category = db_session.get(Category, 2)
        else:
            new_category = db_session.get(Category, 1)
        product.category = new_category
        db_session.commit()
        db_product = db_session.get(Product, product.id)
        assert db_product.category == db_session.get(Category, new_category.id)
        db_product.category = db_session.get(Category, old_category.id)
        db_session.commit()
        assert db_session.get(Product, product.id).category == db_session.get(Category, old_category.id)


def test_product_change_supplier(client):
    with dbSession() as db_session:
        product = db_session.get(Product, 1)
        old_supplier = product.supplier
        if old_supplier.id == 1:
            new_supplier = db_session.get(Supplier, 2)
        else:
            new_supplier = db_session.get(Supplier, 1)
        product.supplier = new_supplier
        db_session.commit()
        db_product = db_session.get(Product, product.id)
        assert db_product.supplier == db_session.get(Supplier, new_supplier.id)
        db_product.supplier = db_session.get(Supplier, old_supplier.id)
        db_session.commit()
        assert db_session.get(Product, product.id).supplier == db_session.get(Supplier, old_supplier.id)


#region: validators
@pytest.mark.xfail(raises=ValueError)
@pytest.mark.parametrize(
    ("user_id", "err_message"), (
    (5, "user with pending registration can't have products attached"),
    (6, "'retired' users can't have products attached"),
    (7, "user does not exist")
    ))
def test_validate_product_responsable_id(client, user_id, err_message):
    with dbSession() as db_session:
        product = db_session.get(Product, 1)
        try:
            product.responsable_id = user_id
        except ValueError as err:
            db_session.rollback()
            assert err_message in err.args
            assert db_session.get(Product, 1).responsable_id == product.responsable_id


@pytest.mark.xfail(raises=ValueError)
@pytest.mark.parametrize(
    ("user_id", "err_message"), (
    (5, "user with pending registration can't have products attached"),
    (6, "'retired' users can't have products attached"),
    (7, "user does not exist")
    ))
def test_validate_product_responsable(client, user_id, err_message):
    with dbSession() as db_session:
        product = db_session.get(Product, 1)
        user = db_session.get(User, user_id)
        try:
            product.responsable = user
        except ValueError as err:
            db_session.rollback()
            assert err_message in err.args
            assert db_session.get(Product, 1).responsable_id == product.responsable_id


@pytest.mark.xfail(raises=ValueError)
@pytest.mark.parametrize(
    ("category_id", "err_message"), (
    (8, "not in use category can't have products attached"),
    (9, "category does not exist")
    ))
def test_validate_product_category_id(client, category_id, err_message):
    with dbSession() as db_session:
        product = db_session.get(Product, 1)
        try:
            product.category_id = category_id
        except ValueError as err:
            db_session.rollback()
            assert err_message in err.args
            assert db_session.get(Product, 1).category_id == product.category_id


@pytest.mark.xfail(raises=ValueError)
@pytest.mark.parametrize(
    ("category_id", "err_message"), (
    (8, "not in use category can't have products attached"),
    (9, "category does not exist")
    ))
def test_validate_product_category(client, category_id, err_message):
    with dbSession() as db_session:
        product = db_session.get(Product, 1)
        category = db_session.get(Category, category_id)
        try:
            product.category = category
        except ValueError as err:
            db_session.rollback()
            assert err_message in err.args
            assert db_session.get(Product, 1).category_id == product.category_id


@pytest.mark.xfail(raises=ValueError)
@pytest.mark.parametrize(
    ("supplier_id", "err_message"), (
    (5, "not in use supplier can't have products attached"),
    (6, "supplier does not exist")
    ))
def test_validate_product_supplier_id(client, supplier_id, err_message):
    with dbSession() as db_session:
        product = db_session.get(Product, 1)
        try:
            product.supplier_id = supplier_id
        except ValueError as err:
            db_session.rollback()
            assert err_message in err.args
            assert db_session.get(Product, 1).supplier_id == product.supplier_id


@pytest.mark.xfail(raises=ValueError)
@pytest.mark.parametrize(
    ("supplier_id", "err_message"), (
    (5, "not in use supplier can't have products attached"),
    (6, "supplier does not exist")
    ))
def test_validate_product_supplier(client, supplier_id, err_message):
    with dbSession() as db_session:
        product = db_session.get(Product, 1)
        supplier = db_session.get(Supplier, supplier_id)
        try:
            product.supplier = supplier
        except ValueError as err:
            db_session.rollback()
            assert err_message in err.args
            assert db_session.get(Product, 1).supplier_id == product.supplier_id




# endregion
# endregion
