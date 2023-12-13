"""Test SQLAlchemy tables mapping."""
# pylint: disable=too-many-lines

import re
from datetime import date, timedelta
from typing import Optional

import pytest
from freezegun import freeze_time
from hypothesis import assume, example, given
from hypothesis import strategies as st
from sqlalchemy import insert, select
from werkzeug.security import check_password_hash

from blueprints.sch import clean_sch_info, sat_sch_info
from constants import Constant
from database import Category, Product, Schedule, Supplier, User, dbSession
from messages import Message
from tests import (ValidCategory, ValidProduct, ValidSchedule, ValidSupplier,
                   ValidUser, test_categories, test_products, test_schedules,
                   test_suppliers, test_users)

pytestmark = pytest.mark.db


# region: test "users" table
@pytest.fixture(name="default_user_attr")
def default_user_attr_fixture() -> dict[str]:
    """Default values for user creation."""
    return {
        "products": [],
        "admin": False,
        "in_use": True,
        "done_inv": True,
        "check_inv": False,
        "reg_req": True,
        "req_inv": False,
        "details": "",
        "email": "",
        "sat_group": 1,
        "in_use_products": 0,
        "all_products": 0}


@given(name = st.text(min_size=1)
            .map(lambda x: x.strip())
            .filter(lambda x: len(x)>1)
            .filter(lambda x: x not in [user["name"] for user in test_users]),
       password = st.text(min_size=1),
       admin=st.booleans())
@example(name = ValidUser.name,
         password = ValidUser.password,
         admin=True)
def test_user_creation(
        name: str, password: str, default_user_attr: dict[str], admin: bool):
    """Test user and admin creation."""
    with dbSession() as db_session:
        if admin:
            db_session.add(User(
                name=name, password=password, admin=True, reg_req=False))
        else:
            db_session.add(User(name=name, password=password))
        db_session.commit()
        db_user = db_session.scalar(select(User).filter_by(name=name))
        assert db_user.username == name.strip()
        assert check_password_hash(db_user.password, password)
        for attr, value in default_user_attr.items():
            if admin and attr in {"admin", "reg_req"}:
                assert not db_user.reg_req
                continue
            assert getattr(db_user, attr) == value
        assert db_user.id == test_users[-1]["id"] + 1
        # teardown
        db_session.delete(db_user)
        db_session.commit()
        assert not db_session.scalar(select(User).filter_by(name=name))


@given(users_data = st.dictionaries(
        keys=st.text(min_size=1)
            .map(lambda x: x.strip())
            .filter(lambda x: len(x)>1)
            .filter(lambda x: x not in [user["name"] for user in test_users]),
        values=st.text(min_size=1),
        min_size=10,
        max_size=10))
def test_bulk_user_insertion(
        users_data: dict[str, str], default_user_attr: dict[str]):
    """test_bulk_user_insertion"""
    # setup
    users = []
    for name, password in users_data.items():
        users.append({"name": name, "password": password})
    # run test
    with dbSession() as db_session:
        db_session.execute(insert(User), users)
        db_session.commit()
        for ind, user in enumerate(users):
            db_user = db_session.scalar(
                select(User).filter_by(name=user["name"]))
            assert db_user.password == user["password"]
            for attr, value in default_user_attr.items():
                assert getattr(db_user, attr) == value
            assert db_user.id == test_users[-1]["id"] + 1 + ind
            # teardown
            db_session.delete(db_user)
        db_session.commit()


@given(user = st.sampled_from(test_users),
       new_name = st.text(min_size=1),
       new_password = st.text(min_size=1))
@example(user = test_users[1],
         new_name = ValidUser.name,
         new_password = ValidUser.password)
def test_change_username_and_password(
        user: dict[str], new_name: str, new_password: str):
    """test_change_username_and_password"""
    assume(new_name.strip() and
           new_name not in [user["name"] for user in test_users])
    new_name = new_name.strip()
    with dbSession() as db_session:
        db_session.get(User, user["id"]).name = new_name
        db_session.get(User, user["id"]).password = new_password
        db_session.commit()
        assert db_session.get(User, user["id"]).name == new_name
        assert check_password_hash(
            db_session.get(User, user["id"]).password,
            new_password)
        # teardown
        db_session.get(User, user["id"]).name = user["name"]
        db_session.get(User, user["id"]).password = user["password"]
        db_session.commit()


def _test_failed_user_creation(
        error_message: str,
        name: str = ValidUser.name,
        password: str = ValidUser.password,
        sat_group: int = ValidUser.sat_group):
    """Common logic for failed user creation."""
    with pytest.raises(ValueError, match=re.escape(error_message)):
        User(name=name,
             password=password,
             sat_group=sat_group)


@pytest.mark.parametrize("name", [
    pytest.param("", id="Empty name"),
    pytest.param(" ", id="Empty name after strip"),
    pytest.param(None, id="None name"),
])
def test_failed_user_creation_invalid_name(name: Optional[str]):
    """test_failed_user_creation_invalid_name"""
    error_message = str(Message.User.Name.Required())
    _test_failed_user_creation(
        error_message=error_message,
        name=name
    )


@given(name = st.sampled_from([user["name"] for user in test_users]))
def test_failed_user_creation_duplicate_name(name: str):
    """test_failed_user_creation_duplicate_name"""
    error_message = str(Message.User.Name.Exists(name))
    _test_failed_user_creation(
        error_message=error_message,
        name=name
    )


@pytest.mark.parametrize("password", [
    pytest.param("", id="Empty password"),
    pytest.param(None, id="None password"),
])
def test_failed_user_creation_invalid_password(password: Optional[str]):
    """test_failed_user_creation_invalid_password"""
    error_message = str(Message.User.Password.Required())
    _test_failed_user_creation(
        error_message=error_message,
        password=password
    )


@given(sat_group = st.one_of(
        st.none(),
        st.integers().filter(lambda x: x not in {1, 2}),
        st.booleans(),
        st.text(),
))
@example(sat_group = True)
def test_failed_user_creation_invalid_sat_group(sat_group):
    """test_failed_user_creation_invalid_sat_group"""
    error_message = "Invalid sat_group"
    _test_failed_user_creation(
        error_message=error_message,
        sat_group=sat_group
    )


@given(user = st.sampled_from(
        [user for user in test_users if user["has_products"]]))
def test_user_products(user: dict[str]):
    """Test user in_use_products and all_products properties."""
    with dbSession() as db_session:
        db_user = db_session.get(User, user["id"])
        all_db_user_products = [product for product in test_products
            if product["responsible_id"] == db_user.id]
        all_in_use_db_user_products = [product for product in test_products
            if product["responsible_id"] == db_user.id and product["in_use"]]
        # run test
        assert db_user.all_products == len(all_db_user_products)
        assert db_user.in_use_products == len(all_in_use_db_user_products)
        product = db_session.scalar(select(Product)
            .filter_by(in_use=True, responsible_id = db_user.id))
        product.in_use = False
        db_session.commit()
        db_session.refresh(db_user)
        assert db_user.in_use_products == len(all_in_use_db_user_products) - 1
        # section setup
        new_product = Product(
            name=ValidProduct.name,
            description=ValidProduct.description,
            responsible=db_user,
            category=db_session.get(Category, ValidProduct.category_id),
            supplier=db_session.get(Supplier, ValidProduct.supplier_id),
            meas_unit=ValidProduct.meas_unit,
            min_stock=ValidProduct.min_stock,
            ord_qty=ValidProduct.ord_qty)
        db_session.add(new_product)
        db_session.commit()
        # run test
        db_session.refresh(db_user)
        assert db_user.all_products == len(all_db_user_products) + 1
        assert db_user.in_use_products == len(all_in_use_db_user_products)
        # teardown
        db_session.refresh(product)
        product.in_use = True
        db_session.delete(new_product)
        db_session.commit()


def test_sat_group_this_week_property():
    """test_sat_group_this_week_property"""
    with dbSession() as db_session:
        for user in test_users:
            if user["sat_group"] == 1:
                assert db_session.get(User, user["id"]).sat_group_this_week
            else:
                assert not db_session.get(User, user["id"]).sat_group_this_week
        # force false
        schedule = db_session.scalar(
            select(Schedule)
            .filter_by(
                name=sat_sch_info.en_name,
                elem_id=1))
        schedule.name = "renamed"
        db_session.commit()
        for user in test_users:
            assert not db_session.get(User, user["id"]).sat_group_this_week
        # teardown
        schedule.name = sat_sch_info.en_name
        db_session.commit()


def test_clean_this_week_property():
    """test_clean_this_week_property"""
    users_in_use = [user for user in test_users if user["active"]]
    with dbSession() as db_session:
        assert db_session.get(User, users_in_use[0]["id"]).clean_this_week
        for user in users_in_use[1:]:
            assert not db_session.get(User, user["id"]).clean_this_week
        # force false
        schedule = db_session.scalar(
            select(Schedule)
            .filter_by(
                name=clean_sch_info.en_name,
                elem_id=1))
        schedule.name = "renamed"
        db_session.commit()
        for user in users_in_use:
            assert not db_session.get(User, user["id"]).clean_this_week
        # teardown
        schedule.name = clean_sch_info.en_name
        db_session.commit()


@given(user = st.sampled_from([user for user in test_users
                               if user["has_products"]]))
def test_failed_delete_user_with_products_attached(user: dict[str]):
    """test_failed_delete_user_with_products_attached"""
    with dbSession() as db_session:
        db_user = db_session.get(User, user["id"])
        with pytest.raises(ValueError,
                           match=str(Message.Product.Responsible.Delete())):
            db_session.delete(db_user)
            db_session.commit()
    with dbSession() as db_session:
        assert db_session.get(User, user["id"])


#region: validators
@pytest.mark.parametrize(
    ("user", "err_message"), [
    pytest.param(
        [user for user in test_users if user["reg_req"]][0],
        str(Message.User.Products.PendReg()),
        id="User with pending registration approval"),
    pytest.param(
        [user for user in test_users if not user["in_use"]][0],
        str(Message.User.Products.Retired()),
        id="Retired user"),
    ]
)
def test_validate_user_products(user: dict[str], err_message: str):
    """test_validate_user_products"""
    with dbSession() as db_session:
        product = db_session.get(Product, 1)
        db_user = db_session.get(User, user["id"])
        with pytest.raises(ValueError, match=err_message):
            db_user.products.append(product)
        assert db_session.get(Product, 1).responsible == product.responsible


def test_validate_user_admin():
    """test_validate_admin"""
    user = [user for user in test_users if user["reg_req"]][0]
    with dbSession() as db_session:
        db_user = db_session.get(User, user["id"])
        with pytest.raises(
                ValueError,
                match=str(Message.User.Admin.PendReg())):
            db_user.admin = True
        assert not db_session.get(User, user["id"]).admin


def test_validate_user_last_admin():
    """test_validate_last_admin"""
    admin_users = [user for user in test_users
                   if user["admin"] and user["in_use"]]
    with dbSession() as db_session:
        for admin in admin_users[1:]:
            db_session.get(User, admin["id"]).admin = False
        db_session.commit()
        # run test
        db_user = db_session.get(User, admin_users[0]["id"])
        with pytest.raises(ValueError,
                           match=str(Message.User.Admin.LastAdmin())):
            db_user.admin = False
        db_session.refresh(db_user)
        assert db_user.admin
        # teardown
        for admin in admin_users[1:]:
            db_session.get(User, admin["id"]).admin = True
        db_session.commit()


@given(user = st.sampled_from([user for user in test_users
                               if user["has_products"]]))
def test_validate_user_in_use_failed_retirement(user):
    """Test failed retirement of a user who has products attached."""
    with dbSession() as db_session:
        with pytest.raises(
                ValueError,
                match=str(Message.User.InUse.StillProd())):
            db_session.get(User, user["id"]).in_use = False


def test_validate_user_in_use():
    """Test successful retirement and reset done_inv, reg_req and req_inv."""
    # manually insert into db bypassing validators
    values = [{
        "name": ValidUser.name,
        "password": ValidUser.password,
        "done_inv": False,
        "reg_req": True,
        "req_inv": True,
        }]
    with dbSession() as db_session:
        db_session.execute(insert(User), values)
        db_session.commit()
        db_user = db_session.scalar(
            select(User).filter_by(name=values[0]["name"]))
        assert db_user.in_use
        assert not db_user.done_inv
        assert db_user.check_inv
        assert db_user.reg_req
        assert db_user.req_inv
        # run test
        db_user.in_use = False
        db_session.commit()
        db_session.refresh(db_user)
        assert not db_user.in_use
        assert db_user.done_inv
        assert not db_user.reg_req
        assert not db_user.req_inv
        # teardown
        db_session.delete(db_user)
        db_session.commit()


@pytest.mark.parametrize(
    ("user", "err_message"), [
    pytest.param(
        [user for user in test_users if user["reg_req"]][0],
        str(Message.User.DoneInv.PendReg()),
        id="User with pending registration approval"),
    pytest.param(
        [user for user in test_users if not user["in_use"]][0],
        str(Message.User.DoneInv.Retired()),
        id="Retired user"),
    ]
)
def test_validate_user_done_inv_failed(user, err_message):
    """test_validate_done_inv"""
    with dbSession() as db_session:
        db_user = db_session.get(User, user["id"])
        with pytest.raises(ValueError, match=err_message):
            db_user.done_inv = False
        assert db_user.done_inv


def test_validate_user_done_inv_failed_no_prod():
    """Failed inventorying trigger for a user without products."""
    user = [user for user in test_users
            if user["in_use"] and not user["has_products"]][0]
    with dbSession() as db_session:
        db_user = db_session.get(User, user["id"])
        db_user.reg_req = False
        with pytest.raises(
                ValueError,
                match=str(Message.User.DoneInv.NoProd())):
            db_user.done_inv = False
        assert db_user.done_inv


@given(user = st.sampled_from([user for user in test_users
                               if user["has_products"] and not user["admin"]]))
def test_validate_user_done_inv_ok(user):
    """Successfully trigger inventorying."""
    with dbSession() as db_session:
        db_user = db_session.get(User, user["id"])
        assert db_user.done_inv
        assert not db_user.check_inv
        assert not db_user.req_inv
        db_user.req_inv = True
        db_user.done_inv = False
        assert not db_user.req_inv
        assert db_user.check_inv


@pytest.mark.parametrize(
    ("user", "err_message"),
    [pytest.param(
        [user for user in test_users
         if user["admin"]][0],
        str(Message.User.RegReq.Admin()),
        id="Admin user"),
    pytest.param(
        [user for user in test_users
         if not user["admin"] and user["has_products"]][0],
        str(Message.User.RegReq.WithProd()),
        id="User with products"),
    pytest.param(
        [user for user in test_users
         if not user["in_use"] and not user["admin"]][0],
        str(Message.User.RegReq.Retired()),
        id="Retired user"),
    ]
)
def test_validate_user_reg_req_failed(user, err_message):
    """Failed request registration of admin, user with products or retired."""
    with dbSession() as db_session:
        db_user = db_session.get(User, user["id"])
        assert not db_user.reg_req
        with pytest.raises(ValueError, match=err_message):
            db_user.reg_req = True


@given(user = st.sampled_from([user for user in test_users
                               if user["has_products"] and not user["admin"]]))
def test_validate_user_reg_req_failed_req_inv(user):
    """Failed request registration of a user that requested inventorying."""
    with dbSession() as db_session:
        db_user = db_session.get(User, user["id"])
        assert not db_user.reg_req
        db_user.req_inv = True
        with pytest.raises(
                ValueError,
                match=str(Message.User.RegReq.ReqInv())):
            db_user.reg_req = True


@given(user = st.sampled_from([user for user in test_users
                               if user["has_products"] and not user["admin"]]))
def test_validate_user_reg_req_failed_done_inv(user):
    """Failed request registration of a user that checks the inventory."""
    with dbSession() as db_session:
        db_user = db_session.get(User, user["id"])
        assert not db_user.reg_req
        db_user.done_inv = False
        with pytest.raises(
                ValueError,
                match=str(Message.User.RegReq.CheckInv())):
            db_user.reg_req = True


@pytest.mark.parametrize(
    ("user", "err_message"),
    [pytest.param(
        [user for user in test_users
            if user["admin"]][0],
        str(Message.User.ReqInv.Admin()),
        id="Admin user"),
    pytest.param(
        [user for user in test_users
            if user["reg_req"]][0],
        str(Message.User.ReqInv.PendReg()),
        id="User with pending registration"),
    pytest.param(
        [user for user in test_users
            if not user["in_use"] and not user["admin"]][0],
        str(Message.User.ReqInv.Retired()),
        id="Retired user"),
    ]
)
def test_validate_user_req_inv_failed(user, err_message):
    """Failed req_inv of admin, user with pending registration or retired."""
    with dbSession() as db_session:
        db_user = db_session.get(User, user["id"])
        assert not db_user.req_inv
        with pytest.raises(ValueError, match=err_message):
            db_user.req_inv = True


@given(user = st.sampled_from([user for user in test_users
                               if user["has_products"] and not user["admin"]]))
def test_validate_user_req_inv_failed_check_inv(user):
    """Failed req_inv of a user that is inventorying."""
    with dbSession() as db_session:
        db_user = db_session.get(User, user["id"])
        assert not db_user.req_inv
        db_user.done_inv = False
        with pytest.raises(ValueError,
                           match=str(Message.User.ReqInv.CheckInv())):
            db_user.req_inv = True


@given(user = st.sampled_from([user for user in test_users if user["reg_req"]]))
def test_validate_user_req_inv_failed_no_prod(user):
    """Failed req_inv of a user that has no products."""
    with dbSession() as db_session:
        db_user = db_session.get(User, user["id"])
        assert not db_user.req_inv
        db_user.reg_req = False
        assert not db_user.all_products
        with pytest.raises(
                ValueError,
                match=str(Message.User.ReqInv.NoProd())):
            db_user.req_inv = True
        assert not db_user.req_inv
# endregion
# endregion


# region: test "categories" table
@given(name = st.text(min_size=1)
            .map(lambda x: x.strip())
            .filter(lambda x: len(x)>1)
            .filter(lambda x: x not in [category["name"]
                                        for category in test_categories]),
       details =  st.text())
@example(name = ValidCategory.name,
         details = ValidCategory.details)
def test_category_creation(name, details):
    """test_category_creation"""
    with dbSession() as db_session:
        db_session.add(Category(name=name, details=details))
        db_session.commit()
        db_cat = db_session.scalar(select(Category).filter_by(name=name))
        assert db_cat.products == []
        assert db_cat.in_use
        assert db_cat.details == details
        assert db_cat.id == test_categories[-1]["id"] + 1
        # teardown
        db_session.delete(db_cat)
        db_session.commit()
        assert not db_session.get(Category, db_cat.id)


@given(cats_data = st.lists(
        st.text(min_size=1)
            .map(lambda x: x.strip())
            .filter(lambda x: len(x)>1)
            .filter(lambda x: x not in [category["name"]
                                        for category in test_categories]),
        min_size=10,
        max_size=10,
        unique=True))
def test_bulk_category_insertion(cats_data):
    """test_bulk_category_insertion"""
    cats = [{"name": name} for name in cats_data]
    with dbSession() as db_session:
        db_session.execute(insert(Category), cats)
        db_session.commit()
        for ind, name in enumerate(cats_data):
            db_cat = db_session.scalar(select(Category).filter_by(name=name))
            assert db_cat.products == []
            assert db_cat.in_use_products == 0
            assert db_cat.all_products == 0
            assert db_cat.in_use
            assert db_cat.details == ""
            assert db_cat.id == test_categories[-1]["id"] + 1 + ind
            # teardown
            db_session.delete(db_cat)
        db_session.commit()


@given(cat = st.sampled_from(test_categories),
       new_name = st.text(min_size=1)
            .map(lambda x: x.strip())
            .filter(lambda x: len(x)>1)
            .filter(lambda x: x not in [category["name"]
                                        for category in test_categories]))
def test_change_category_name(cat, new_name):
    """test_change_category_name"""
    with dbSession() as db_session:
        db_cat = db_session.get(Category, cat["id"])
        db_cat.name = new_name
        db_session.commit()
        db_session.refresh(db_cat)
        assert db_cat.name == new_name
        # teardown
        db_cat.name = cat["name"]
        db_session.commit()


def _test_failed_category_creation(name, error_message):
    """Common logic for failed category creation"""
    with pytest.raises(ValueError, match=error_message):
        Category(name=name)


@pytest.mark.parametrize("name", [
    pytest.param("", id="Empty name"),
    pytest.param(" ", id="Empty name after strip"),
    pytest.param(None, id="None name"),
])
def test_failed_category_creation_invalid_name(name):
    """test_failed_category_creation_invalid_name"""
    error_message = str(Message.Category.Name.Required())
    _test_failed_category_creation(
        error_message=error_message,
        name=name
    )


@given(name = st.sampled_from([cat["name"] for cat in test_categories]))
def test_failed_category_creation_duplicate_name(name: str):
    """test_failed_user_creation_duplicate_name"""
    error_message = str(Message.Category.Name.Exists(name))
    _test_failed_category_creation(
        error_message=error_message,
        name=name
    )


@given(cat = st.sampled_from(
        [cat for cat in test_categories if cat["has_products"]]))
def test_category_products(cat: dict[str]):
    """Test category in_use_products and all_products properties."""
    with dbSession() as db_session:
        db_cat = db_session.get(Category, cat["id"])
        all_db_cat_products = [product for product in test_products
            if product["category_id"] == db_cat.id]
        all_in_use_db_cat_products = [product for product in test_products
            if product["category_id"] == db_cat.id and product["in_use"]]
        # run test
        assert db_cat.all_products == len(all_db_cat_products)
        assert db_cat.in_use_products == len(all_in_use_db_cat_products)
        product = db_session.scalar(select(Product)
            .filter_by(in_use=True, category_id = db_cat.id))
        product.in_use = False
        db_session.commit()
        db_session.refresh(db_cat)
        assert db_cat.in_use_products == len(all_in_use_db_cat_products) - 1
        # section setup
        new_product = Product(
            name=ValidProduct.name,
            description=ValidProduct.description,
            responsible=db_session.get(User, ValidProduct.responsible_id),
            category=db_cat,
            supplier=db_session.get(Supplier, ValidProduct.supplier_id),
            meas_unit=ValidProduct.meas_unit,
            min_stock=ValidProduct.min_stock,
            ord_qty=ValidProduct.ord_qty)
        db_session.add(new_product)
        db_session.commit()
        # run test
        db_session.refresh(db_cat)
        assert db_cat.all_products == len(all_db_cat_products) + 1
        assert db_cat.in_use_products == len(all_in_use_db_cat_products)
        # teardown
        db_session.refresh(product)
        product.in_use = True
        db_session.delete(new_product)
        db_session.commit()


@given(cat = st.sampled_from(
        [cat for cat in test_categories if cat["has_products"]]))
def test_failed_delete_or_disable_category_with_products_attached(
        cat: dict[str]):
    """Test restrict deletion or disabling a category with products attached"""
    with dbSession() as db_session:
        db_cat = db_session.get(Category, cat["id"])
        # test delete
        with pytest.raises(
                ValueError,
                match=str(Message.Product.Category.Delete())):
            db_session.delete(db_cat)
            db_session.commit()
    # test disable
    with dbSession() as db_session:
        db_cat = db_session.get(Category, cat["id"])
        assert db_cat.in_use
        with pytest.raises(
                ValueError,
                match=str(Message.Category.InUse.StillProd())):
            db_cat.in_use = False
        db_session.refresh(db_cat)
        assert db_cat.in_use


@given(cat = st.sampled_from(
        [cat for cat in test_categories if not cat["in_use"]]))
def test_validate_category_products(cat: dict[str]):
    """test_validate_category_products"""
    with dbSession() as db_session:
        product = db_session.get(Product, 1)
        db_cat = db_session.get(Category, cat["id"])
        with pytest.raises(
                ValueError,
                match=str(Message.Category.Products.Disabled())):
            db_cat.products.append(product)
        assert db_session.get(Product, 1).category.id == product.category_id
# endregion


# region: test "suppliers" table
@given(name = st.text(min_size=1)
            .map(lambda x: x.strip())
            .filter(lambda x: len(x)>1)
            .filter(lambda x: x not in [supplier["name"]
                                        for supplier in test_suppliers]),
       details =  st.text())
@example(name = ValidSupplier.name,
         details = ValidSupplier.details)
def test_supplier_creation(name, details):
    """test_supplier_creation"""
    with dbSession() as db_session:
        db_session.add(Supplier(name=name, details=details))
        db_session.commit()
        db_sup = db_session.scalar(select(Supplier).filter_by(name=name))
        assert db_sup.products == []
        assert db_sup.in_use
        assert db_sup.details == details
        assert db_sup.id == test_suppliers[-1]["id"] + 1
        # teardown
        db_session.delete(db_sup)
        db_session.commit()
        assert not db_session.get(Supplier, db_sup.id)


@given(sups_data = st.lists(
        st.text(min_size=1)
            .map(lambda x: x.strip())
            .filter(lambda x: len(x)>1)
            .filter(lambda x: x not in [supplier["name"]
                                        for supplier in test_suppliers]),
        min_size=10,
        max_size=10,
        unique=True))
def test_bulk_supplier_insertion(sups_data):
    """test_bulk_supplier_insertion"""
    sups = [{"name": name} for name in sups_data]
    with dbSession() as db_session:
        db_session.execute(insert(Supplier), sups)
        db_session.commit()
        for ind, name in enumerate(sups_data):
            db_sup = db_session.scalar(select(Supplier).filter_by(name=name))
            assert db_sup.products == []
            assert db_sup.in_use_products == 0
            assert db_sup.all_products == 0
            assert db_sup.in_use
            assert db_sup.details == ""
            assert db_sup.id == test_suppliers[-1]["id"] + 1 + ind
            # teardown
            db_session.delete(db_sup)
        db_session.commit()


@given(sup = st.sampled_from(test_suppliers),
       new_name = st.text(min_size=1)
            .map(lambda x: x.strip())
            .filter(lambda x: len(x)>1)
            .filter(lambda x: x not in [supplier["name"]
                                        for supplier in test_suppliers]))
def test_change_supplier_name(sup, new_name):
    """test_change_supplier_name"""
    with dbSession() as db_session:
        db_sup = db_session.get(Supplier, sup["id"])
        db_sup.name = new_name
        db_session.commit()
        db_session.refresh(db_sup)
        assert db_sup.name == new_name
        # teardown
        db_sup.name = sup["name"]
        db_session.commit()


def _test_failed_supplier_creation(name, error_message):
    """Common logic for failed supplier creation"""
    with pytest.raises(ValueError, match=error_message):
        Supplier(name=name)


@pytest.mark.parametrize("name", [
    pytest.param("", id="Empty name"),
    pytest.param(" ", id="Empty name after strip"),
    pytest.param(None, id="None name"),
])
def test_failed_supplier_creation_invalid_name(name):
    """test_failed_supplier_creation_invalid_name"""
    error_message = str(Message.Supplier.Name.Required())
    _test_failed_supplier_creation(
        error_message=error_message,
        name=name
    )


@given(name = st.sampled_from([sup["name"] for sup in test_suppliers]))
def test_failed_supplier_creation_duplicate_name(name: str):
    """test_failed_user_creation_duplicate_name"""
    error_message = str(Message.Supplier.Name.Exists(name))
    _test_failed_supplier_creation(
        error_message=error_message,
        name=name
    )


@given(sup = st.sampled_from(
        [sup for sup in test_suppliers if sup["has_products"]]))
def test_supplier_products(sup: dict[str]):
    """Test supplier in_use_products and all_products properties."""
    with dbSession() as db_session:
        db_sup = db_session.get(Supplier, sup["id"])
        all_db_sup_products = [product for product in test_products
            if product["supplier_id"] == db_sup.id]
        all_in_use_db_sup_products = [product for product in test_products
            if product["supplier_id"] == db_sup.id and product["in_use"]]
        # run test
        assert db_sup.all_products == len(all_db_sup_products)
        assert db_sup.in_use_products == len(all_in_use_db_sup_products)
        product = db_session.scalar(select(Product)
            .filter_by(in_use=True, supplier_id = db_sup.id))
        product.in_use = False
        db_session.commit()
        db_session.refresh(db_sup)
        assert db_sup.in_use_products == len(all_in_use_db_sup_products) - 1
        # section setup
        new_product = Product(
            name=ValidProduct.name,
            description=ValidProduct.description,
            responsible=db_session.get(User, ValidProduct.responsible_id),
            category=db_session.get(Category, ValidProduct.category_id),
            supplier=db_sup,
            meas_unit=ValidProduct.meas_unit,
            min_stock=ValidProduct.min_stock,
            ord_qty=ValidProduct.ord_qty)
        db_session.add(new_product)
        db_session.commit()
        # run test
        db_session.refresh(db_sup)
        assert db_sup.all_products == len(all_db_sup_products) + 1
        assert db_sup.in_use_products == len(all_in_use_db_sup_products)
        # teardown
        db_session.refresh(product)
        product.in_use = True
        db_session.delete(new_product)
        db_session.commit()


@given(sup = st.sampled_from(
        [sup for sup in test_suppliers if sup["has_products"]]))
def test_failed_delete_or_disable_supplier_with_products_attached(
        sup: dict[str]):
    """Test restrict deletion or disabling a supplier with products attached"""
    with dbSession() as db_session:
        db_sup = db_session.get(Supplier, sup["id"])
        # test delete
        with pytest.raises(
                ValueError,
                match=str(Message.Product.Supplier.Delete())):
            db_session.delete(db_sup)
            db_session.commit()
    # test disable
    with dbSession() as db_session:
        db_sup = db_session.get(Supplier, sup["id"])
        assert db_sup.in_use
        with pytest.raises(
                ValueError,
                match=str(Message.Supplier.InUse.StillProd())):
            db_sup.in_use = False
        db_session.refresh(db_sup)
        assert db_sup.in_use


@given(sup = st.sampled_from(
        [sup for sup in test_suppliers if not sup["in_use"]]))
def test_validate_supplier_products(sup: dict[str]):
    """test_validate_supplier_products"""
    with dbSession() as db_session:
        product = db_session.get(Product, 1)
        db_sup = db_session.get(Supplier, sup["id"])
        with pytest.raises(
                ValueError,
                match=str(Message.Supplier.Products.Disabled())):
            db_sup.products.append(product)
        assert db_session.get(Product, 1).supplier.id == product.supplier_id
# endregion


# region: test "products" table
@given(name = st.text(min_size=1)
           .map(lambda x: x.strip())
           .filter(lambda x: len(x)>1)
           .filter(lambda x: x not in [prod["name"] for prod in test_products]),
       description = st.text(min_size=1)
           .map(lambda x: x.strip())
           .filter(lambda x: len(x)>1),
       responsible_id = st.sampled_from(
           [user["id"] for user in test_users if user["active"]]),
       category_id = st.sampled_from(
           [cat["id"] for cat in test_categories if cat["in_use"]]),
       supplier_id = st.sampled_from(
           [sup["id"] for sup in test_suppliers if sup["in_use"]]),
       meas_unit = st.text(min_size=1)
           .map(lambda x: x.strip())
           .filter(lambda x: len(x)>1),
       min_stock = st.integers(
           min_value=Constant.Product.MinStock.min_value,
           max_value=Constant.SQLite.Int.max_value),
       ord_qty = st.integers(
           min_value=Constant.Product.OrdQty.min_value,
           max_value=Constant.SQLite.Int.max_value),
       critical = st.booleans()
)
@example(name = ValidProduct.name,
         description = ValidProduct.description,
         responsible_id = ValidProduct.responsible_id,
         category_id = ValidProduct.category_id,
         supplier_id = ValidProduct.supplier_id,
         meas_unit = ValidProduct.meas_unit,
         min_stock = ValidProduct.min_stock,
         ord_qty = ValidProduct.ord_qty,
         critical = bool(ValidProduct.critical)
)
def test_product_creation(name: str, description: str, responsible_id: int,
                          category_id: int, supplier_id: int, meas_unit: str,
                          min_stock: int, ord_qty: int, critical: bool):
    """test_product_creation"""
    with dbSession() as db_session:
        user = db_session.get(User, responsible_id)
        category = db_session.get(Category, category_id)
        supplier = db_session.get(Supplier, supplier_id)
        db_session.add(Product(
            name=name,
            description=description,
            responsible=user,
            category=category,
            supplier=supplier,
            meas_unit=meas_unit,
            min_stock=min_stock,
            ord_qty=ord_qty,
            critical=critical))
        db_session.commit()
        db_prod = db_session.scalar(select(Product).filter_by(name=name))
        assert db_prod.description == description
        assert db_prod.responsible_id == responsible_id
        assert db_prod.category_id == category_id
        assert db_prod.supplier_id == supplier_id
        assert db_prod.meas_unit == meas_unit
        assert db_prod.min_stock == min_stock
        assert db_prod.ord_qty == ord_qty
        assert not db_prod.to_order
        assert db_prod.critical == critical
        assert db_prod.in_use
        # teardown
        db_session.delete(db_prod)
        db_session.commit()
        assert not db_session.scalar(select(Product).filter_by(name=name))


@given(product_data = st.dictionaries(
        keys=st.text(min_size=1)
           .map(lambda x: x.strip())
           .filter(lambda x: len(x)>1)
           .filter(lambda x: x not in [prod["name"] for prod in test_products]),
        values=st.text(min_size=1)
           .map(lambda x: x.strip())
           .filter(lambda x: len(x)>1),
        min_size=10,
        max_size=10))
def test_bulk_product_insertion(product_data):
    """test_bulk_product_insertion"""
    # setup
    products = []
    for name, description in product_data.items():
        products.append(
            {"name": name,
             "description": description,
             "responsible_id": ValidProduct.responsible_id,
             "category_id": ValidProduct.category_id,
             "supplier_id": ValidProduct.supplier_id,
             "meas_unit": ValidProduct.meas_unit,
             "min_stock": ValidProduct.min_stock,
             "ord_qty": ValidProduct.ord_qty})
    # run test
    with dbSession() as db_session:
        db_session.execute(insert(Product), products)
        db_session.commit()
        for ind, product in enumerate(products):
            db_product = db_session.scalar(
                select(Product).filter_by(name=product["name"]))
            assert db_product.id == test_products[-1]["id"] + 1 + ind
            assert db_product.description == product["description"]
            assert db_product.responsible_id == product["responsible_id"]
            assert db_product.category_id == product["category_id"]
            assert db_product.supplier_id == product["supplier_id"]
            assert db_product.meas_unit == product["meas_unit"]
            assert db_product.min_stock == product["min_stock"]
            assert db_product.ord_qty == product["ord_qty"]
            assert not db_product.to_order
            assert not db_product.critical
            assert db_product.in_use
            # teardown
            db_session.delete(db_product)
        db_session.commit()


@given(product = st.sampled_from(test_products),
       new_name = st.text(min_size=1)
           .map(lambda x: x.strip())
           .filter(lambda x: len(x)>1)
           .filter(lambda x: x not in [prod["name"] for prod in test_products]),
       new_description = st.text(min_size=1)
           .map(lambda x: x.strip())
           .filter(lambda x: len(x)>1),
       new_responsible_id = st.sampled_from(
           [user["id"] for user in test_users if user["active"]]),
       new_category_id = st.sampled_from(
           [cat["id"] for cat in test_categories if cat["in_use"]]),
       new_supplier_id = st.sampled_from(
           [sup["id"] for sup in test_suppliers if sup["in_use"]]),
       new_meas_unit = st.text(min_size=1)
           .map(lambda x: x.strip())
           .filter(lambda x: len(x)>1),
       new_min_stock = st.integers(
           min_value=Constant.Product.MinStock.min_value,
           max_value=Constant.SQLite.Int.max_value),
       new_ord_qty = st.integers(
           min_value=Constant.Product.OrdQty.min_value,
           max_value=Constant.SQLite.Int.max_value),
       new_to_order = st.booleans(),
       new_critical = st.booleans()
)
def test_change_product_attrs(
        product: dict[str], new_name: str, new_description: str,
        new_responsible_id: int, new_category_id: int, new_supplier_id: int,
        new_meas_unit: str, new_min_stock: int, new_ord_qty: int,
        new_to_order: bool, new_critical: bool):
    """test_change_product_attrs"""
    if new_to_order:
        assume(product["in_use"])
    with dbSession() as db_session:
        db_prod = db_session.get(Product, product["id"])
        db_prod.name = new_name
        db_prod.description = new_description
        db_prod.responsible = db_session.get(User, new_responsible_id)
        db_prod.category = db_session.get(Category, new_category_id)
        db_prod.supplier = db_session.get(Supplier, new_supplier_id)
        db_prod.meas_unit = new_meas_unit
        db_prod.min_stock = new_min_stock
        db_prod.ord_qty = new_ord_qty
        db_prod.to_order = new_to_order
        db_prod.critical = new_critical
        db_session.commit()
        db_session.refresh(db_prod)
        assert db_prod.name == new_name
        assert db_prod.description == new_description
        assert db_prod.responsible_id == new_responsible_id
        assert db_prod.category_id == new_category_id
        assert db_prod.supplier_id == new_supplier_id
        assert db_prod.meas_unit == new_meas_unit
        assert db_prod.min_stock == new_min_stock
        assert db_prod.ord_qty == new_ord_qty
        assert db_prod.to_order == new_to_order
        assert db_prod.critical == new_critical
        db_prod.name = product["name"]
        db_prod.description = product["description"]
        db_prod.responsible = db_session.get(User, product["responsible_id"])
        db_prod.category = db_session.get(Category, product["category_id"])
        db_prod.supplier = db_session.get(Supplier, product["supplier_id"])
        db_prod.meas_unit = product["meas_unit"]
        db_prod.min_stock = product["min_stock"]
        db_prod.ord_qty = product["ord_qty"]
        db_prod.to_order = product["to_order"]
        db_prod.critical = product["critical"]
        db_session.commit()


# region: failed product creation
def _test_failed_product_creation(
        error_message: str,
        name: str = ValidProduct.name,
        description: str = ValidProduct.description,
        responsible_id: int = ValidProduct.responsible_id,
        category_id: int = ValidProduct.category_id,
        supplier_id: int = ValidProduct.supplier_id,
        meas_unit: str = ValidProduct.meas_unit,
        min_stock: int = ValidProduct.min_stock,
        ord_qty: int = ValidProduct.ord_qty,
        to_order: bool = False,
        critical: bool = False,
        in_use: bool = True):
    """Common logic for failed product creation"""
    with dbSession() as db_session:
        if isinstance(responsible_id, int):
            user = db_session.get(User, responsible_id)
        else:
            user = responsible_id
        if isinstance(category_id, int):
            category = db_session.get(Category, category_id)
        else:
            category = category_id
        if isinstance(supplier_id, int):
            supplier = db_session.get(Supplier, supplier_id)
        else:
            supplier = supplier_id
        with pytest.raises(ValueError, match=error_message):
            Product(
                name=name,
                description=description,
                responsible=user,
                category=category,
                supplier=supplier,
                meas_unit=meas_unit,
                min_stock=min_stock,
                ord_qty=ord_qty,
                to_order=to_order,
                critical=critical,
                in_use=in_use)


@pytest.mark.parametrize("name", [
    pytest.param("", id="Empty name"),
    pytest.param(" ", id="Empty name after strip"),
    pytest.param(None, id="None name"),
])
def test_failed_product_creation_invalid_name(name: Optional[str]):
    """test_failed_product_creation_invalid_name"""
    error_message = str(Message.Product.Name.Required())
    _test_failed_product_creation(
        error_message=error_message,
        name=name
    )


@given(name = st.sampled_from([product["name"] for product in test_products]))
def test_failed_product_creation_duplicate_name(name: str):
    """test_failed_product_creation_duplicate_name"""
    error_message = str(Message.Product.Name.Exists(name))
    _test_failed_product_creation(
        error_message=error_message,
        name=name
    )


@pytest.mark.parametrize("description", [
    pytest.param("", id="Empty description"),
    pytest.param(" ", id="Empty description after strip"),
    pytest.param(None, id="None description"),
])
def test_failed_product_creation_invalid_description(
        description: Optional[str]):
    """test_failed_product_creation_invalid_description"""
    error_message = str(Message.Product.Description.Required())
    _test_failed_product_creation(
        error_message=error_message,
        description=description
    )


@given(responsible = st.sampled_from(
        [user for user in test_users if not user["active"]]))
@example(responsible = [user for user in test_users if user["reg_req"]][0])
@example(responsible = [user for user in test_users if not user["in_use"]][0])
def test_failed_product_creation_invalid_responsible(
        responsible: dict[str]):
    """test_failed_product_creation_invalid_responsible"""
    if responsible["reg_req"]:
        error_message = str(Message.User.Products.PendReg())
    else:
        error_message = str(Message.User.Products.Retired())
    _test_failed_product_creation(
        error_message=error_message,
        responsible_id=responsible["id"]
    )


@pytest.mark.parametrize("responsible_id", [
    pytest.param("", id="Empty responsible_id"),
    pytest.param(None, id="None responsible_id"),
    pytest.param(test_users[-1]["id"] + 1, id="Not existing responsible_id"),
])
def test_failed_product_creation_invalid_responsible_id(
        responsible_id: Optional[int]):
    """test_failed_product_creation_invalid_responsible_id"""
    error_message = str(Message.User.NotExists(""))
    _test_failed_product_creation(
        error_message=error_message,
        responsible_id=responsible_id
    )


@given(category = st.sampled_from(
        [category for category in test_categories if not category["in_use"]]))
def test_failed_product_creation_invalid_category(
        category: dict[str]):
    """test_failed_product_creation_invalid_category"""
    error_message = str(Message.Category.Products.Disabled())
    _test_failed_product_creation(
        error_message=error_message,
        category_id=category["id"]
    )


@pytest.mark.parametrize("category_id", [
    pytest.param("", id="Empty category_id"),
    pytest.param(None, id="None category_id"),
    pytest.param(test_categories[-1]["id"] + 1, id="Not existing category_id"),
])
def test_failed_product_creation_invalid_category_id(
        category_id: Optional[int]):
    """test_failed_product_creation_invalid_category_id"""
    error_message = str(Message.Category.NotExists(""))
    _test_failed_product_creation(
        error_message=error_message,
        category_id=category_id
    )


@given(supplier = st.sampled_from(
        [supplier for supplier in test_suppliers if not supplier["in_use"]]))
def test_failed_product_creation_invalid_supplier(
        supplier: dict[str]):
    """test_failed_product_creation_invalid_supplier"""
    error_message = str(Message.Supplier.Products.Disabled())
    _test_failed_product_creation(
        error_message=error_message,
        supplier_id=supplier["id"]
    )


@pytest.mark.parametrize("supplier_id", [
    pytest.param("", id="Empty supplier_id"),
    pytest.param(None, id="None supplier_id"),
    pytest.param(test_suppliers[-1]["id"] + 1, id="Not existing supplier_id"),
])
def test_failed_product_creation_invalid_supplier_id(
        supplier_id: Optional[int]):
    """test_failed_product_creation_invalid_supplier_id"""
    error_message = str(Message.Supplier.NotExists(""))
    _test_failed_product_creation(
        error_message=error_message,
        supplier_id=supplier_id
    )


@pytest.mark.parametrize("meas_unit", [
    pytest.param("", id="Empty meas_unit"),
    pytest.param(" ", id="Empty meas_unit after strip"),
    pytest.param(None, id="None meas_unit"),
])
def test_failed_product_creation_invalid_meas_unit(
        meas_unit: Optional[str]):
    """test_failed_product_creation_invalid_meas_unit"""
    error_message = str(Message.Product.MeasUnit.Required())
    _test_failed_product_creation(
        error_message=error_message,
        meas_unit=meas_unit
    )


@pytest.mark.parametrize("min_stock", [
    pytest.param("", id="Empty min_stock"),
    pytest.param(None, id="None min_stock"),
    pytest.param("0", id="String min_stock"),
    pytest.param(Constant.Product.MinStock.min_value - 1,
                 id="Smaller than minimum value"),
    pytest.param(Constant.SQLite.Int.max_value + 1,
                 id="Bigger than maximum value"),
])
def test_failed_product_creation_invalid_min_stock(
        min_stock: Optional[str]):
    """test_failed_product_creation_invalid_min_stock"""
    error_message = str(Message.Product.MinStock.Invalid())
    _test_failed_product_creation(
        error_message=error_message,
        min_stock=min_stock
    )


@pytest.mark.parametrize("ord_qty", [
    pytest.param("", id="Empty ord_qty"),
    pytest.param(None, id="None ord_qty"),
    pytest.param("1", id="String ord_qty"),
    pytest.param(Constant.Product.OrdQty.min_value - 1,
                 id="Smaller than minimum value"),
    pytest.param(Constant.SQLite.Int.max_value + 1,
                 id="Bigger than maximum value"),
])
def test_failed_product_creation_invalid_ord_qty(
        ord_qty: Optional[str]):
    """test_failed_product_creation_invalid_ord_qty"""
    error_message = str(Message.Product.OrdQty.Invalid())
    _test_failed_product_creation(
        error_message=error_message,
        ord_qty=ord_qty
    )
# endregion


#region: validators
def test_validate_product_responsible_last_product():
    """Reset done_inv and req_inv if it is the last product of responsible"""
    product = test_products[0]
    user = [user for user in test_users if user["reg_req"]][0]
    with dbSession() as db_session:
        db_user = db_session.get(User, user["id"])
        db_user.reg_req = False
        db_session.commit()
        db_prod = db_session.get(Product, product["id"])
        # test reset done_inv (using responsible_id validation)
        db_prod.responsible_id = db_user.id
        db_session.commit()
        db_session.refresh(db_user)
        assert db_user.all_products == 1
        assert db_user.done_inv
        db_user.done_inv = False
        db_session.commit()
        db_session.refresh(db_user)
        assert not db_user.done_inv
        db_prod.responsible_id = product["responsible_id"]
        db_session.commit()
        db_session.refresh(db_user)
        assert db_user.done_inv
        # test reset req_inv (using responsible validation)
        db_prod.responsible_id = db_user.id
        db_session.commit()
        db_session.refresh(db_user)
        assert db_user.all_products == 1
        assert not db_user.req_inv
        db_user.req_inv = True
        db_session.commit()
        db_session.refresh(db_user)
        assert db_user.req_inv
        db_prod.responsible = db_session.get(User, product["responsible_id"])
        db_session.refresh(db_user)
        assert not db_user.req_inv
        # teardown
        db_user.reg_req = True
        db_prod.responsible = db_session.get(User, product["responsible_id"])
        db_session.commit()


@given(prod = st.sampled_from(
        [prod for prod in test_products if prod["in_use"]]))
def test_validate_product_to_order_in_use_relation(prod: dict[str]):
    """Test interlock of to_order and in_use."""
    with dbSession() as db_session:
        db_prod = db_session.get(Product, prod["id"])
        db_prod.to_order = True
        db_session.commit()
        with pytest.raises(
                ValueError,
                match=str(Message.Product.InUse.ToOrder())):
            db_prod.in_use = False
        db_session.refresh(db_prod)
        assert db_prod.in_use
        db_prod.to_order = False
        db_prod.in_use = False
        db_session.commit()
        db_session.refresh(db_prod)
        with pytest.raises(
                ValueError,
                match=str(Message.Product.ToOrder.Retired())):
            db_prod.to_order = True
        db_session.refresh(db_prod)
        assert not db_prod.to_order
        # teardown
        db_prod.in_use = True
        db_session.commit()


def _test_failed_product_edit_with_ids(
        error_message: str,
        responsible_id: int = ValidProduct.responsible_id,
        category_id: int = ValidProduct.category_id,
        supplier_id: int = ValidProduct.supplier_id):
    """Common logic for failed product edit when given elements id's."""
    product = test_products[0]
    with dbSession() as db_session:
        db_prod = db_session.get(Product, product["id"])
        with pytest.raises(ValueError, match=error_message):
            db_prod.responsible_id = responsible_id
            db_prod.category_id = category_id
            db_prod.supplier_id = supplier_id
        db_session.rollback()
        assert db_prod.responsible_id == product["responsible_id"]
        assert db_prod.category_id == product["category_id"]
        assert db_prod.supplier_id == product["supplier_id"]


@pytest.mark.parametrize(("responsible_id", "error_message"), [
    pytest.param(test_users[-1]["id"] + 1,
                 str(Message.User.NotExists("")),
                 id="Not existing responsible_id"),
    pytest.param([user for user in test_users if not user["in_use"]][0]["id"],
                 str(Message.User.Products.Retired()),
                 id="Retired user"),
    pytest.param([user for user in test_users if user["reg_req"]][0]["id"],
                 str(Message.User.Products.PendReg()),
                 id="User with pending registration"),
])
def test_validate_product_responsible_id(
        responsible_id: int, error_message: str):
    """test_validate_product_responsible_id"""
    _test_failed_product_edit_with_ids(
        error_message=error_message,
        responsible_id=responsible_id
    )


@pytest.mark.parametrize(("category_id", "error_message"), [
    pytest.param(test_categories[-1]["id"] + 1,
                 str(Message.Category.NotExists("")),
                 id="Not existing category_id"),
    pytest.param([cat for cat in test_categories if not cat["in_use"]][0]["id"],
                 str(Message.Category.Products.Disabled()),
                 id="Disabled category"),
])
def test_validate_product_category_id(
        category_id: int, error_message: str):
    """test_validate_product_category_id"""
    _test_failed_product_edit_with_ids(
        error_message=error_message,
        category_id=category_id
    )


@pytest.mark.parametrize(("supplier_id", "error_message"), [
    pytest.param(test_suppliers[-1]["id"] + 1,
                 str(Message.Supplier.NotExists("")),
                 id="Not existing supplier_id"),
    pytest.param([sup for sup in test_suppliers if not sup["in_use"]][0]["id"],
                 str(Message.Supplier.Products.Disabled()),
                 id="Disabled supplier"),
])
def test_validate_product_supplier_id(
        supplier_id: int, error_message: str):
    """test_validate_product_supplier_id"""
    _test_failed_product_edit_with_ids(
        error_message=error_message,
        supplier_id=supplier_id
    )
# endregion
# endregion


# region: test "schedule" table
@given(name = st.text(min_size=1)
           .map(lambda x: x.strip())
           .filter(lambda x: len(x)>1)
           .filter(lambda x: x not in [sch["name"] for sch in test_schedules]),
       sch_type = st.sampled_from(("group", "individual")),
       elem_id = st.integers(min_value=1,
                             max_value=Constant.SQLite.Int.max_value),
       next_date = st.dates(min_value=date.today()),
       update_date = st.dates(min_value=date.today() + timedelta(days=1)),
       update_interval = st.integers(min_value=1,
                                     max_value=Constant.SQLite.Int.max_value)
)
@example(
    name = ValidSchedule.name,
    sch_type = ValidSchedule.type,
    elem_id = ValidSchedule.elem_id,
    next_date = ValidSchedule.next_date,
    update_date = ValidSchedule.update_date,
    update_interval = ValidSchedule.update_interval,
)
def test_schedule_creation(
        name: str, sch_type: str, elem_id: int,
        next_date: date, update_date: date, update_interval: int):
    """test_schedule_creation"""
    assume(update_date > next_date)
    with dbSession() as db_session:
        db_session.add(
            Schedule(
                name=name,
                type=sch_type,
                elem_id=elem_id,
                next_date=next_date,
                update_date=update_date,
                update_interval=update_interval))
        db_session.commit()
        db_sch = db_session.scalar(select(Schedule).filter_by(name=name))
        assert db_sch.type == sch_type
        assert db_sch.elem_id == elem_id
        assert db_sch.next_date == next_date
        assert db_sch.update_date == update_date
        assert db_sch.update_interval == update_interval
        # teardown
        db_session.delete(db_sch)
        db_session.commit()
        assert not db_session.get(Schedule, db_sch.id)


@freeze_time("2023-10-12")
def test_schedule_creation_next_date_in_the_past():
    """Freeze time on a thursday. Next date - monday."""
    schedule = Schedule(
        name=ValidSchedule.name,
        type=ValidSchedule.type,
        elem_id=ValidSchedule.elem_id,
        # next day in the past (that monday)
        next_date=date(2023, 10, 9),
        update_date=date.today() + timedelta(days=2),
        update_interval=ValidSchedule.update_interval)
    with dbSession() as db_session:
        db_session.add(schedule)
        db_session.commit()
        assert schedule.id is not None
        db_session.refresh(schedule)
        assert schedule.next_date == date(2023, 10, 9)
        assert schedule.update_date == date(2023, 10, 14)
        # teardown
        db_session.delete(schedule)
        db_session.commit()
        assert not db_session.get(Schedule, schedule.id)


# region: failed schedule creation
def _test_failed_schedule_creation(
        error_message: str,
        name: str = ValidSchedule.name,
        sch_type: str = ValidSchedule.type,
        elem_id: int = ValidSchedule.elem_id,
        next_date: date = ValidSchedule.next_date,
        update_date: date = ValidSchedule.update_date,
        update_interval: int = ValidSchedule.update_interval):
    """Common logic for failed schedule creation"""
    with pytest.raises((ValueError, TypeError), match=re.escape(error_message)):
        Schedule(
            name=name,
            type=sch_type,
            elem_id=elem_id,
            next_date=next_date,
            update_date=update_date,
            update_interval=update_interval)


@pytest.mark.parametrize("name", [
    pytest.param("", id="Empty name"),
    pytest.param(" ", id="Empty name after strip"),
    pytest.param(None, id="None name"),
])
def test_failed_schedule_creation_invalid_name(name):
    """test_failed_schedule_creation_invalid_name"""
    error_message = "The schedule must have a name"
    _test_failed_schedule_creation(
        error_message=error_message,
        name=name
    )


@given(sch_type = st.text().filter(lambda x: x not in {"group", "individual"}))
@example(sch_type = "")
@example(sch_type = " ")
@example(sch_type = None)
def test_failed_schedule_creation_invalid_type(sch_type: str):
    """test_failed_schedule_creation_invalid_type"""
    if not sch_type or not sch_type.strip():
        error_message = "The schedule must have a type"
    else:
        error_message = "Schedule type is invalid"
    _test_failed_schedule_creation(
        error_message=error_message,
        sch_type=sch_type
    )


@given(elem_id = st.one_of(
        st.none(),
        st.text(),
        st.integers(max_value=0)
))
def test_failed_schedule_creation_invalid_elem_id(elem_id):
    """test_failed_schedule_creation_invalid_elem_id"""
    error_message = "Schedule elem_id is invalid"
    _test_failed_schedule_creation(
        error_message=error_message,
        elem_id=elem_id
    )


@given(name = st.sampled_from([sch["name"] for sch in test_schedules]),
       elem_id = st.sampled_from([1, 2]))
def test_failed_schedule_creation_invalid_name_elem_id_combination(
        name, elem_id):
    """test_failed_schedule_creation_invalid_name_elem_id_combination"""
    error_message = "Name-Elem_id combination must be unique"
    _test_failed_schedule_creation(
        error_message=error_message,
        name=name,
        elem_id=elem_id
    )

@given(next_date = st.one_of(
        st.none(),
        st.integers(),
        st.text(),
        st.dates(max_value=date.today()-timedelta(days=7))
))
@example(next_date = "")
@example(next_date = date.today()-timedelta(days=7))
def test_failed_schedule_creation_invalid_next_date(next_date):
    """test_failed_schedule_creation_invalid_next_date"""
    if not isinstance(next_date, date):
        error_message = "Schedule's next date is invalid"
    else:
        error_message = ("The schedule's next date cannot be older " +
                         "than this week")
    _test_failed_schedule_creation(
        error_message=error_message,
        next_date=next_date
    )


@given(update_date = st.one_of(
        st.none(),
        st.integers(),
        st.text(),
        st.dates(max_value=date.today()-timedelta(days=1))
))
@example(update_date = "")
@example(update_date = date.today()-timedelta(days=1))
def test_failed_schedule_creation_invalid_update_date(update_date):
    """test_failed_schedule_creation_invalid_update_date"""
    if not isinstance(update_date, date):
        error_message = "Schedule's update date is invalid"
    else:
        error_message = "Schedule's 'update date' cannot be in the past"
    _test_failed_schedule_creation(
        error_message=error_message,
        update_date=update_date
    )


@given(next_date = st.dates(min_value=date.today()),
       update_date = st.dates(min_value=date.today() + timedelta(days=1))
)
def test_failed_schedule_creation_update_date_older_than_next_date(
        next_date, update_date):
    """test_failed_schedule_creation_update_date_older_than_next_date"""
    assume(update_date <= next_date)
    error_message = "Schedule's 'update date' is older than 'next date'"
    _test_failed_schedule_creation(
        error_message=error_message,
        next_date=next_date,
        update_date=update_date
    )


@given(update_interval = st.one_of(
        st.none(),
        st.text(),
        st.integers(max_value=0)
))
def test_failed_schedule_creation_invalid_update_interval(update_interval):
    """test_failed_schedule_creation_invalid_update_interval"""
    error_message = "Schedule's update interval is invalid"
    _test_failed_schedule_creation(
        error_message=error_message,
        update_interval=update_interval
    )
# endregion
# endregion
