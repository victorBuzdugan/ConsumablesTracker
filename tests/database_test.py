"""Test SQLAlchemy tables mapping."""

import re

import pytest
from sqlalchemy import func, insert, select
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from database import Category, Product, Supplier, User, dbSession
from tests import (admin_logged_in, client, create_test_categories,
                   create_test_db, create_test_products, create_test_suppliers,
                   create_test_users, user_logged_in)

pytestmark = pytest.mark.db


# region: test "users" table
def test_user_creation(client):
    """Test default user creation and database insertion."""
    user = User("user11", "P@ssw0rd")
    with dbSession() as db_session:
        db_session.add(user)
        db_session.commit()
        assert user.id is not None
        db_user = db_session.get(User, user.id)
        assert db_user
        assert db_user.name == user.name
        assert check_password_hash(db_user.password, "P@ssw0rd")
        assert not db_user.admin
        assert db_user.in_use
        assert db_user.done_inv
        assert not db_user.check_inv
        assert db_user.reg_req
        assert not db_user.req_inv
        assert not db_user.details
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
        user.password = "P@ssw0rd"
        assert user in db_session.dirty
        db_session.commit()
        db_user = db_session.get(User, user.id)
        assert check_password_hash(db_user.password, "P@ssw0rd")

        # teardown
        db_user.password = "Q!111111"
        assert db_user in db_session.dirty
        db_session.commit()
        assert check_password_hash(db_session.get(User, user.id).password, "Q!111111")


@pytest.mark.parametrize(("name", "password", "error_msg"), (
    # name
    ("", "password", "The user must have a name"),
    (" ", "password", "The user must have a name"),
    (None, "password", "The user must have a name"),
    ("Admin", "password", "The user Admin allready exists"),
    ("user1", "password", "The user user1 allready exists"),
    # password
    ("test_user", "", "User must have a password"),
    ("test_user", None, "User must have a password"),
))
def test_failed_user_creation(client, name, password, error_msg):
    with pytest.raises(ValueError, match=re.escape(error_msg)):
        User(
            name=name,
            password=password,
            admin=0,
            in_use=1,
            done_inv=1,
            reg_req=0,
            req_inv=0,
        )


def test_bulk_user_insertion(client):
    with dbSession() as db_session:
        last_id = db_session.scalar(
            select(User).order_by(User.id.desc())).id
        values = [{"name": f"user__{no}",
                "password": generate_password_hash(f"P@ssw0rd{no}")}
                for no in range(last_id + 1, last_id + 4)]
        db_session.execute(insert(User), values)
        db_session.commit()
        users = db_session.scalars(
            select(User).where(User.name.like("user__%%"))).all()
        assert len(users) == 3
        for user in users:
            assert check_password_hash(user.password, f"P@ssw0rd{user.id}")
            assert user.products == []
            assert not user.admin
            assert user.in_use
            assert user.done_inv
            assert user.reg_req
            assert not user.req_inv
            assert not user.details
            # teardown
            db_session.delete(user)
        db_session.commit()


def test_admin_creation(client):
    """Test user creation with admin credentials (admin: True)"""
    user = User(
        "admin1",
        "P@ssw0rd",
        admin=True,
        reg_req=False)
    with dbSession() as db_session:
        db_session.add(user)
        db_session.commit()
        assert db_session.get(User, user.id).admin is True
        # teardown
        db_session.delete(db_session.get(User, user.id))
        db_session.commit()


def test_user_in_use_products_property(client):
    with dbSession() as db_session:
        user = db_session.get(User, 2)
        assert user.all_products == len(user.products)
        product = db_session.scalar(
            select(Product).
            filter_by(in_use=True, responsable_id = user.id))
        product.in_use = False
        db_session.commit()
        assert db_session.get(User, user.id).in_use_products == user.all_products - 1
        db_session.get(Product, product.id).in_use = True
        db_session.commit()


def test_user_all_products_property(client):
    with dbSession() as db_session:
        user = db_session.get(User, 3)
        assert user.all_products == len(user.products)
        all_products = user.all_products
        product = db_session.scalar(
            select(Product).
            filter_by(responsable_id = user.id))
        product.responsable_id = 2
        db_session.commit()
        assert db_session.get(User, user.id).all_products == all_products - 1
        db_session.get(Product, product.id).responsable_id = user.id
        db_session.commit()
        assert user.all_products == all_products


def test_failed_delete_user_with_products_attached(client):
    with dbSession() as db_session:
        user = db_session.get(User, 1)
        with pytest.raises(ValueError, match="User can't be deleted or does not exist"):
            db_session.delete(user)
            db_session.commit()
    with dbSession() as db_session:
        assert db_session.get(User, 1)


#region: validators
@pytest.mark.parametrize(
    ("user_id", "err_message"), (
    (5, "User with pending registration can't have products attached"),
    (6, "'Retired' users can't have products attached"),
    ))
def test_validate_user_products(client, user_id, err_message):
    with dbSession() as db_session:
        product = db_session.get(Product, 1)
        user = db_session.get(User, user_id)
        with pytest.raises(ValueError, match=err_message):
            user.products.append(product)
        assert db_session.get(Product, 1).responsable == product.responsable


def test_validate_admin(client):
    with dbSession() as db_session:
        user = db_session.get(User, 5)
        assert user.reg_req
        with pytest.raises(ValueError, match="User with pending registration can't be admin"):
            user.admin = True
        assert not user.admin


def test_validate_last_admin(client):
    with dbSession() as db_session:
        db_session.get(User, 1).admin = False
        db_session.commit()
        assert db_session.scalar(select(func.count(User.id)).filter_by(admin=True, in_use=True)) == 1
        user = db_session.get(User, 2)
        assert user.admin
        with pytest.raises(ValueError, match="You are the last admin!"):
            user.admin = False
        assert user.admin
        db_session.get(User, 1).admin = True
        db_session.commit()


def test_validate_user_in_use(client):
    with dbSession() as db_session:
        user = db_session.get(User, 1)
        assert user.in_use
        with pytest.raises(ValueError, match="Can't 'retire' a user if he is still responsible for products"):
            user.in_use = False
        assert user.in_use


def test_validate_ok_in_use(client):
    with dbSession() as db_session:
        values = [{
            "name": "temp_user",
            "password": "P@ssw0rd",
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
        assert user.check_inv
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


@pytest.mark.parametrize(
    ("user_id", "err_message"), (
    (5, "User with pending registration can't check inventory"),
    (6, "'Retired' user can't check inventory"),
    ))
def test_validate_done_inv(client, user_id, err_message):
    with dbSession() as db_session:
        user = db_session.get(User, user_id)
        with pytest.raises(ValueError, match=err_message):
            user.done_inv = False
        assert user.done_inv


def test_validate_done_inv_no_prod(client):
    with dbSession() as db_session:
        user = db_session.get(User, 5)
        user.reg_req = False
        with pytest.raises(ValueError, match="User without products attached can't check inventory"):
            user.done_inv = False
        assert user.done_inv


def test_validate_ok_done_inv(client):
    with dbSession() as db_session:
        user = db_session.get(User, 3)
        assert user.done_inv
        assert not user.check_inv
        assert not user.req_inv
        user.req_inv = True

        user.done_inv = False
        assert not user.req_inv
        assert user.check_inv


@pytest.mark.parametrize(
    ("user_id", "err_message"), (
    (1, "Admin users can't request registration"),
    (3, "Users with products attached can't request registration"),
    (6, "'Retired' users can't request registration"),
    ))
def test_validate_reg_req(client, user_id, err_message):
    with dbSession() as db_session:
        user = db_session.get(User, user_id)
        assert not user.reg_req
        with pytest.raises(ValueError, match=err_message):
            user.reg_req = True
        assert not user.reg_req


def test_validate_reg_req_req_inv(client):
    with dbSession() as db_session:
        user = db_session.get(User, 4)
        assert not user.reg_req
        user.req_inv = True
        with pytest.raises(ValueError, match="User that requested inventory can't request registration"):
            user.reg_req = True
        assert not user.reg_req


def test_validate_reg_req_done_inv(client):
    with dbSession() as db_session:
        user = db_session.get(User, 4)
        assert not user.reg_req
        user.done_inv = False
        with pytest.raises(ValueError, match="User that checks inventory can't request registration"):
            user.reg_req = True
        assert not user.reg_req


@pytest.mark.parametrize(
    ("user_id", "err_message"), (
    (1, "Admins don't need to request inventorying"),
    (6, "'Retired' users can't request inventorying"),
    (5, "User with pending registration can't request inventorying"),
    ))
def test_validate_req_inv(client, user_id, err_message):
    with dbSession() as db_session:
        user = db_session.get(User, user_id)
        assert not user.req_inv
        with pytest.raises(ValueError, match=err_message):
            user.req_inv = True
        assert not user.req_inv


def test_validate_req_inv_check_inv(client):
    with dbSession() as db_session:
        user = db_session.get(User, 3)
        assert not user.req_inv
        user.done_inv = False
        with pytest.raises(ValueError, match="User can allready check inventory"):
            user.req_inv = True
        assert not user.req_inv


def test_validate_req_inv_prod(client):
    with dbSession() as db_session:
        user = db_session.get(User, 5)
        assert not user.req_inv
        user.reg_req = False
        assert not user.all_products
        with pytest.raises(ValueError, match="Users without products can't request inventorying"):
            user.req_inv = True
        assert not user.req_inv


def test_admin_request_inventory(client):
    with dbSession() as db_session:
        user = db_session.get(User, 1)
        assert user.admin
        with pytest.raises(ValueError, match="Admins don't need to request inventorying"):
            user.req_inv = True
        assert not user.req_inv
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
    with dbSession() as db_session:
        category = db_session.get(Category, 1)
        old_name = category.name
        new_name = "category1"
        category.name = new_name
        assert category in db_session.dirty
        db_session.commit()
        db_category = db_session.get(Category, category.id)
        assert db_category.name == new_name
        # teardown
        db_category.name = old_name
        db_session.commit()
        assert db_session.get(Category, category.id).name == old_name


@pytest.mark.parametrize(("name", "error_msg"), (
    ("", "The category must have a name"),
    (" ", "The category must have a name"),
    (None, "The category must have a name"),
    ("Household", "The category (.)* allready exists"),
    ("Groceries", "The category (.)* allready exists"),
))
def test_failed_category_creation(client, name, error_msg):
    with dbSession() as db_session:
        with pytest.raises(ValueError, match=error_msg):
            Category(name)


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
            assert category.in_use
            assert not category.description
            # teardown
            db_session.delete(category)
        db_session.commit()


def test_failed_delete_category_with_products_attached(client):
    with dbSession() as db_session:
        category = db_session.get(Category, 1)
        with pytest.raises(ValueError, match="Category can't be deleted or does not exist"):
            db_session.delete(category)
            db_session.commit()
    with dbSession() as db_session:
        assert db_session.get(Category, 1)


def test_category_in_use_products_property(client):
    with dbSession() as db_session:
        category = db_session.get(Category, 2)
        assert category.all_products == len(category.products)
        product = db_session.scalar(
            select(Product).
            filter_by(in_use=True, category_id = category.id))
        product.in_use = False
        db_session.commit()
        assert db_session.get(Category, category.id).in_use_products == category.all_products - 1
        db_session.get(Product, product.id).in_use = True
        db_session.commit()


def test_category_all_products_property(client):
    with dbSession() as db_session:
        category = db_session.get(Category, 3)
        assert category.all_products == len(category.products)
        all_products = category.all_products
        product = db_session.scalar(
            select(Product).
            filter_by(category_id = category.id))
        product.category_id = 2
        db_session.commit()
        assert db_session.get(Category, category.id).all_products == all_products - 1
        db_session.get(Product, product.id).category_id = category.id
        db_session.commit()
        assert category.all_products == all_products


def test_validate_category_products(client):
    with dbSession() as db_session:
        product = db_session.get(Product, 1)
        category = db_session.get(Category, 8)
        with pytest.raises(ValueError, match="Not in use category can't have products attached"):
            category.products.append(product)
        assert db_session.get(Product, 1).category == product.category


def test_validate_category_not_in_use(client):
    with dbSession() as db_session:
        category = db_session.get(Category, 1)
        assert category.in_use
        with pytest.raises(ValueError, match="Not in use category can't have products attached"):
            category.in_use = False
        assert category.in_use
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
    with dbSession() as db_session:
        supplier = db_session.get(Supplier, 1)
        old_name = supplier.name
        new_name = "supplier1"
        supplier.name = new_name
        assert supplier in db_session.dirty
        db_session.commit()
        db_supplier = db_session.get(Supplier, supplier.id)
        assert db_supplier.name == new_name
        # teardown
        db_supplier.name = old_name
        db_session.commit()
        assert db_session.get(Supplier, db_supplier.id).name == old_name


@pytest.mark.parametrize(("name", "error_msg"), (
    ("", "The supplier must have a name"),
    (" ", "The supplier must have a name"),
    (None, "The supplier must have a name"),
    ("Amazon", "The supplier (.)* allready exists"),
    ("Carrefour", "The supplier (.)* allready exists"),
))
def test_failed_supplier_creation(client, name, error_msg):
    with dbSession() as db_session:
        with pytest.raises(ValueError, match=error_msg):
            Supplier(name)


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
            assert supplier.in_use
            assert not supplier.details
            # teardown
            db_session.delete(supplier)
        db_session.commit()


def test_delete_supplier_with_products_attached(client):
    with dbSession() as db_session:
        supplier = db_session.get(Supplier, 1)
        with pytest.raises(ValueError, match="Supplier can't be deleted or does not exist"):
            db_session.delete(supplier)
            db_session.commit()
    with dbSession() as db_session:
        assert db_session.get(Supplier, 1)


def test_supplier_in_use_products_property(client):
    with dbSession() as db_session:
        supplier = db_session.get(Supplier, 1)
        assert supplier.all_products == len(supplier.products)
        product = db_session.scalar(
            select(Product).
            filter_by(in_use=True, supplier_id = supplier.id))
        product.in_use = False
        db_session.commit()
        assert db_session.get(Supplier, supplier.id).in_use_products == supplier.all_products - 1
        db_session.get(Product, product.id).in_use = True
        db_session.commit()


def test_supplier_all_products_property(client):
    with dbSession() as db_session:
        supplier = db_session.get(Supplier, 3)
        assert supplier.all_products == len(supplier.products)
        all_products = supplier.all_products
        product = db_session.scalar(
            select(Product).
            filter_by(supplier_id = supplier.id))
        product.supplier_id = 2
        db_session.commit()
        assert db_session.get(Supplier, supplier.id).all_products == all_products - 1
        db_session.get(Product, product.id).supplier_id = supplier.id
        db_session.commit()
        assert supplier.all_products == all_products


def test_validate_supplier_products(client):
    with dbSession() as db_session:
        product = db_session.get(Product, 1)
        supplier = db_session.get(Supplier, 5)
        with pytest.raises(ValueError, match="Not in use supplier can't have products attached"):
            supplier.products.append(product)
        assert db_session.get(Product, 1).supplier == product.supplier


def test_validate_supplier_not_in_use(client):
    with dbSession() as db_session:
        supplier = db_session.get(Supplier, 1)
        assert supplier.in_use
        with pytest.raises(ValueError, match="Not in use supplier can't have products attached"):
            supplier.in_use = False
        assert supplier.in_use
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
    with dbSession() as db_session:
        product = db_session.get(Product, 1)
        old_name = product.name
        new_name = "product1"
        product.name = new_name
        assert product in db_session.dirty
        db_session.commit()
        db_product = db_session.get(Product, product.id)
        assert db_product.name == new_name
        # teardown
        db_product.name = old_name
        db_session.commit()
        assert db_session.get(Product, db_product.id).name == old_name


@pytest.mark.parametrize(("name", "description", "user", "category", "supplier", "meas_unit", "min_stock", "ord_qty", "error_msg"), (
    # name
    ("", "Some description", 1, 1, 1, "measunit", 1, 2, "The product must have a name"),
    (" ", "Some description", 1, 1, 1, "measunit", 1, 2, "The product must have a name"),
    (None, "Some description", 1, 1, 1, "measunit", 1, 2, "The product must have a name"),
    ("Toilet paper", "Some description", 1, 1, 1, "measunit", 1, 2, "The product (.)* allready exists"),
    ("   Toilet paper   ", "Some description", 1, 1, 1, "measunit", 1, 2, "The product (.)* allready exists"),
    # description
    ("__test__producttt__", "", 1, 1, 1, "measunit", 1, 2, "Product must have a description"),
    ("__test__producttt__", " ", 1, 1, 1, "measunit", 1, 2, "Product must have a description"),
    ("__test__producttt__", None, 1, 1, 1, "measunit", 1, 2, "Product must have a description"),
    # responsible
    ("__test__producttt__", "Some description", "", 1, 1, "measunit", 1, 2, "User does not exist"),
    ("__test__producttt__", "Some description", None, 1, 1, "measunit", 1, 2, "User does not exist"),
    ("__test__producttt__", "Some description", 5, 1, 1, "measunit", 1, 2, "User with pending registration can't have products attached"),
    ("__test__producttt__", "Some description", 6, 1, 1, "measunit", 1, 2, "'Retired' users can't have products attached"),
    ("__test__producttt__", "Some description", 8, 1, 1, "measunit", 1, 2, "User does not exist"),
    # category
    ("__test__producttt__", "Some description", 1, "", 1, "measunit", 1, 2, "Category does not exist"),
    ("__test__producttt__", "Some description", 1, None, 1, "measunit", 1, 2, "Category does not exist"),
    ("__test__producttt__", "Some description", 1, 8, 1, "measunit", 1, 2, "Not in use category can't have products attached"),
    ("__test__producttt__", "Some description", 1, 9, 1, "measunit", 1, 2, "Category does not exist"),
    # supplier
    ("__test__producttt__", "Some description", 1, 1, "", "measunit", 1, 2, "Supplier does not exist"),
    ("__test__producttt__", "Some description", 1, 1, None, "measunit", 1, 2, "Supplier does not exist"),
    ("__test__producttt__", "Some description", 1, 1, 5, "measunit", 1, 2, "Not in use supplier can't have products attached"),
    ("__test__producttt__", "Some description", 1, 1, 6, "measunit", 1, 2, "Supplier does not exist"),
    # meas unit
    ("__test__producttt__", "Some description", 1, 1, 1, "", 1, 2, "Product must have a measuring unit"),
    ("__test__producttt__", "Some description", 1, 1, 1, " ", 1, 2, "Product must have a measuring unit"),
    ("__test__producttt__", "Some description", 1, 1, 1, None, 1, 2, "Product must have a measuring unit"),
    # min stock
    ("__test__producttt__", "Some description", 1, 1, 1, "measunit", "", 2, "Minimum stock must be ≥ 0"),
    ("__test__producttt__", "Some description", 1, 1, 1, "measunit", None, 2, "Minimum stock must be ≥ 0"),
    ("__test__producttt__", "Some description", 1, 1, 1, "measunit", "0", 2, "Minimum stock must be ≥ 0"),
    ("__test__producttt__", "Some description", 1, 1, 1, "measunit", -3, 2, "Minimum stock must be ≥ 0"),
    # ord quantity
    ("__test__producttt__", "Some description", 1, 1, 1, "measunit", 1, "", "Order quantity must be ≥ 1"),
    ("__test__producttt__", "Some description", 1, 1, 1, "measunit", 1, None, "Order quantity must be ≥ 1"),
    ("__test__producttt__", "Some description", 1, 1, 1, "measunit", 1, "1", "Order quantity must be ≥ 1"),
    ("__test__producttt__", "Some description", 1, 1, 1, "measunit", 1, 0, "Order quantity must be ≥ 1"),
    ("__test__producttt__", "Some description", 1, 1, 1, "measunit", 1, -3, "Order quantity must be ≥ 1"),
))
def test_failed_product_creation(client, name, description, user, category, supplier, meas_unit, min_stock, ord_qty, error_msg):
    with dbSession() as db_session:
        if user:
            user = db_session.get(User, user)
        if category:
            category = db_session.get(Category, category)
        if supplier:
            supplier = db_session.get(Supplier, supplier)
        with pytest.raises(ValueError, match=error_msg):
            Product(
                name,
                description,
                user,
                category,
                supplier,
                meas_unit,
                min_stock,
                ord_qty
            )


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


def test_product_change_responsable(client):
    with dbSession() as db_session:
        product = db_session.get(Product, 1)
        old_user = product.responsable
        assert old_user.id == 2
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
        assert old_category.id == 1
        new_category = db_session.get(Category, 2)
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
        assert old_supplier.id == 3
        new_supplier = db_session.get(Supplier, 1)
        product.supplier = new_supplier
        db_session.commit()
        db_product = db_session.get(Product, product.id)
        assert db_product.supplier == db_session.get(Supplier, new_supplier.id)
        db_product.supplier = db_session.get(Supplier, old_supplier.id)
        db_session.commit()
        assert db_session.get(Product, product.id).supplier == db_session.get(Supplier, old_supplier.id)


#region: validators
@pytest.mark.parametrize(
    ("user_id", "err_message"), (
    (5, "User with pending registration can't have products attached"),
    (6, "'Retired' users can't have products attached"),
    (8, "User does not exist")
    ))
def test_validate_product_responsable_id(client, user_id, err_message):
    with dbSession() as db_session:
        product = db_session.get(Product, 1)
        with pytest.raises(ValueError, match=err_message):
            product.responsable_id = user_id
        assert db_session.get(Product, 1).responsable_id == product.responsable_id


def test_validate_product_responsable_id_last_product(client):
    with dbSession() as db_session:
        product = db_session.get(Product, 1)
        orig_resp_id = product.responsable_id
        user = db_session.get(User, 5)
        user.reg_req = False
        db_session.commit()

        product.responsable_id = user.id
        db_session.commit()
        assert user.all_products == 1
        assert user.done_inv
        assert not user.req_inv
        assert product.responsable_id == user.id
        user.done_inv = False
        db_session.commit()
        product.responsable_id = orig_resp_id
        db_session.refresh(user)
        assert user.done_inv
        
        product.responsable_id = user.id
        db_session.commit()
        assert user.all_products == 1
        assert user.done_inv
        assert not user.req_inv
        assert product.responsable_id == user.id
        user.req_inv = True
        db_session.commit()
        product.responsable_id = orig_resp_id
        db_session.refresh(user)
        assert not user.req_inv

        # teardown
        product.responsable_id = orig_resp_id
        user.reg_req = True
        db_session.commit()


def test_validate_product_responsable_last_product(client):
    with dbSession() as db_session:
        product = db_session.get(Product, 1)
        orig_resp = product.responsable
        user = db_session.get(User, 5)
        user.reg_req = False
        db_session.commit()

        product.responsable = user
        db_session.commit()
        assert user.all_products == 1
        assert user.done_inv
        assert not user.req_inv
        assert product.responsable == user
        user.done_inv = False
        db_session.commit()
        product.responsable = orig_resp
        db_session.refresh(user)
        assert user.done_inv
        
        product.responsable = user
        db_session.commit()
        assert user.all_products == 1
        assert user.done_inv
        assert not user.req_inv
        assert product.responsable == user
        user.req_inv = True
        db_session.commit()
        product.responsable = orig_resp
        db_session.refresh(user)
        assert not user.req_inv

        # teardown
        product.responsable = orig_resp
        user.reg_req = True
        db_session.commit()


@pytest.mark.parametrize(
    ("category_id", "err_message"), (
    (8, "Not in use category can't have products attached"),
    (9, "Category does not exist")
    ))
def test_validate_product_category_id(client, category_id, err_message):
    with dbSession() as db_session:
        product = db_session.get(Product, 1)
        with pytest.raises(ValueError, match=err_message):
            product.category_id = category_id
        assert db_session.get(Product, 1).category_id == product.category_id


@pytest.mark.parametrize(
    ("supplier_id", "err_message"), (
    (5, "Not in use supplier can't have products attached"),
    (6, "Supplier does not exist")
    ))
def test_validate_product_supplier_id(client, supplier_id, err_message):
    with dbSession() as db_session:
        product = db_session.get(Product, 1)
        with pytest.raises(ValueError, match=err_message):
            product.supplier_id = supplier_id
        assert db_session.get(Product, 1).supplier_id == product.supplier_id


def test_validate_to_order(client):
    with dbSession() as db_session:
        with pytest.raises(ValueError, match="Can't order not in use products"):
            db_session.get(Product, 43).to_order = True
        assert not db_session.get(Product, 43).to_order


def test_validate_product_in_use(client):
    with dbSession() as db_session:
        product = db_session.get(Product, 1)
        product.to_order = True
        with pytest.raises(ValueError, match="Can't 'retire' a product that needs to be ordered"):
            product.in_use = False
        assert product.in_use
# endregion
# endregion
