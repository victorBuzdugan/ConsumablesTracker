"""Categories blueprint tests."""

import re
from html import unescape

import pytest
from flask import g, session, url_for
from flask.testing import FlaskClient
from hypothesis import assume, example, given
from hypothesis import strategies as st
from sqlalchemy import select

from constants import Constant
from database import Category, Product, Supplier, User, dbSession
from messages import Message
from tests import (InvalidCategory, ValidCategory, ValidProduct, redirected_to,
                   test_categories, test_products, test_users)

pytestmark = pytest.mark.cat


# region: categories page
def test_categories_page_user_logged_in(
        client: FlaskClient, user_logged_in: User):
    """test_categories_page_user_logged_in"""
    with client:
        client.get("/")
        assert session["user_id"] == user_logged_in.id
        assert not session["admin"]
        response = client.get(url_for("cat.categories"), follow_redirects=True)
        assert redirected_to(url_for("auth.login"), response)
        assert str(Message.UI.Auth.AdminReq()) in response.text


def test_categories_page_admin_logged_in(
        client: FlaskClient, admin_logged_in: User):
    """test_categories_page_admin_logged_in"""
    strikethrough_decoration = '<span class="text-decoration-line-through">'
    with client:
        client.get("/")
        assert session["user_id"] == admin_logged_in.id
        assert session["admin"]
        response = client.get(url_for("cat.categories"))
        assert response.status_code == 200
        assert str(Message.UI.Auth.AdminReq()) not in response.text
        assert str(Message.UI.Captions.Strikethrough("categories")) \
            in response.text
        for category in test_categories:
            assert category["name"] in response.text
        # not in use category
        assert strikethrough_decoration in response.text
        categories_not_in_use = [cat for cat in test_categories
                                 if not cat["in_use"]]
        with dbSession() as db_session:
            for cat in categories_not_in_use:
                db_session.scalar(
                    select(Category)
                    .filter_by(name=cat["name"])
                    ).in_use = True
            db_session.commit()
            response = client.get(url_for("cat.categories"))
            assert strikethrough_decoration not in response.text
            for cat in categories_not_in_use:
                db_session.scalar(
                    select(Category)
                    .filter_by(name=cat["name"])
                    ).in_use = False
            db_session.commit()
# endregion


# region: new category
@given(name=st.text(min_size=Constant.Category.Name.min_length)
           .map(lambda x: x.strip())
           .filter(lambda x: len(x) > Constant.Category.Name.min_length)
           .filter(lambda x: x not in [cat["name"] for cat in test_categories]),
       details=st.text())
@example(name=ValidCategory.name,
         details=ValidCategory.details)
def test_new_category(
        client: FlaskClient, admin_logged_in: User,
        name: str, details: str):
    """test_new_category"""
    create_cat_btn = re.compile(
        r'<input.*type="submit".*value="Create category">')
    with client:
        client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        response = client.get(url_for("cat.new_category"))
        assert create_cat_btn.search(response.text)
        data = {
            "csrf_token": g.csrf_token,
            "name": name,
            "details": details,
            }
        response = client.post(
            url_for("cat.new_category"), data=data, follow_redirects=True)
        assert redirected_to(url_for("cat.categories"), response)
        assert str(Message.Category.Created(name)) in response.text
        assert name in unescape(response.text)
    with dbSession() as db_session:
        cat = db_session.scalar(select(Category).filter_by(name=name))
        assert cat.in_use
        assert cat.details == details
        db_session.delete(cat)
        db_session.commit()
        assert not db_session.get(Category, cat.id)


def _test_failed_new_category(
        request: pytest.FixtureRequest,
        name: str, flash_message: str, check_db: bool = True):
    """Common logic for failed new category."""
    client: FlaskClient = request.getfixturevalue("client")
    admin_logged_in: User = request.getfixturevalue("admin_logged_in")
    create_cat_btn = re.compile(
        r'<input.*type="submit".*value="Create category">')
    with client:
        client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        response = client.get(url_for("cat.new_category"))
        assert "Create category" in response.text
        data = {
            "csrf_token": g.csrf_token,
            "name": name,
            "details": "",
            }
        response = client.post(
            url_for("cat.new_category"), data=data)
        assert response.status_code == 200
        assert create_cat_btn.search(response.text)
        assert flash_message in unescape(response.text)
        assert str(Message.Category.Created(name)) not in response.text
    if check_db:
        with dbSession() as db_session:
            assert not db_session.scalar(select(Category).filter_by(name=name))


@given(name=st.text(min_size=1,
                    max_size=Constant.Category.Name.min_length - 1))
@example("")
@example(InvalidCategory.short_name)
def test_failed_new_category_invalid_name(request, name: str):
    """Invalid or no name"""
    name = name.strip()
    if name:
        flash_message = str(Message.Category.Name.LenLimit())
    else:
        flash_message = str(Message.Category.Name.Required())
    _test_failed_new_category(request=request,
                              name=name,
                              flash_message=flash_message)


@given(category=st.sampled_from(test_categories))
def test_failed_new_category_duplicate_name(request, category):
    """Duplicate category name."""
    flash_message = str(Message.Category.Name.Exists(category['name']))
    _test_failed_new_category(request=request,
                              name=category['name'],
                              flash_message=flash_message,
                              check_db=False)
# endregion


# region: edit category
@given(category=st.sampled_from(test_categories),
       new_name=st.text(min_size=Constant.Category.Name.min_length)
           .map(lambda x: x.strip())
           .filter(lambda x: len(x) > Constant.Category.Name.min_length)
           .filter(lambda x: x not in [cat["name"] for cat in test_categories]),
       new_details=st.text())
@example(category=test_categories[0],
       new_name=ValidCategory.name,
       new_details=ValidCategory.details)
def test_edit_category(
        client: FlaskClient, admin_logged_in: User,
        category: dict, new_name: str, new_details: str):
    """Test successfully edit category"""
    with client:
        client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        client.get(url_for("cat.categories"))
        response = client.get(
            url_for("cat.edit_category", category=category["name"]))
        assert response.status_code == 200
        assert category["name"] in response.text
        data = {
            "csrf_token": g.csrf_token,
            "name": new_name,
            "details": new_details,
            "in_use": "on",
            "submit": True,
        }
        response = client.post(
            url_for("cat.edit_category", category=category["name"]),
            data=data,
            follow_redirects=True)
        assert redirected_to(url_for("cat.categories"), response)
        assert str(Message.Category.Updated(new_name)) \
            in unescape(response.text)
        assert new_name in unescape(response.text)
        assert new_details in unescape(response.text)
    with dbSession() as db_session:
        cat = db_session.get(Category, category["id"])
        assert cat.name == new_name
        assert cat.details == new_details
        assert cat.in_use
        # teardown
        cat.name = category["name"]
        cat.details = category["details"]
        cat.in_use = category["in_use"]
        db_session.commit()


# region: failed edit category
def _test_failed_edit_category(
        request: pytest.FixtureRequest,
        category: dict,
        flash_message: str,
        new_name: str = ValidCategory.name,
        new_in_use: str = ValidCategory.in_use):
    """Common logic for failed edit category"""
    client: FlaskClient = request.getfixturevalue("client")
    admin_logged_in: User = request.getfixturevalue("admin_logged_in")
    with client:
        client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        response = client.get(url_for("cat.edit_category",
                                        category=category["name"]))
        assert category["name"] in response.text
        data = {
            "csrf_token": g.csrf_token,
            "name": new_name,
            "details": category["details"],
            "in_use": new_in_use,
            "submit": True,
        }
        response = client.post(
            url_for("cat.edit_category", category=category["name"]),
            data=data)
        assert response.status_code == 200
        assert str(Message.Category.Updated(new_name)) \
            not in unescape(response.text)
        assert category["name"] in response.text
        assert flash_message in unescape(response.text)
    with dbSession() as db_session:
        cat = db_session.scalar(
            select(Category)
            .filter_by(name=category["name"]))
        assert cat.in_use == category["in_use"]


@given(category=st.sampled_from(test_categories),
       new_name=st.text(min_size=1,
                        max_size=Constant.Category.Name.min_length - 1))
@example(category=test_categories[0],
         new_name="")
@example(category=test_categories[0],
         new_name=InvalidCategory.short_name)
def test_failed_edit_category_invalid_name(
        request, category: dict, new_name: str):
    """Invalid or no name"""
    new_name = new_name.strip()
    if new_name:
        flash_message = str(Message.Category.Name.LenLimit())
    else:
        flash_message = str(Message.Category.Name.Required())
    _test_failed_edit_category(request=request,
                               category=category,
                               new_name=new_name,
                               flash_message=flash_message)


@given(category=st.sampled_from(test_categories),
       name=st.sampled_from([category["name"] for category in test_categories]))
def test_failed_edit_category_duplicate_name(
        request, category: dict, name: str):
    """Duplicate name"""
    assume(category["name"] != name)
    flash_message = str(Message.Category.Name.Exists(name))
    _test_failed_edit_category(request=request,
                               category=category,
                               new_name=name,
                               flash_message=flash_message)


@given(category=st.sampled_from([category for category in test_categories
                                 if category["has_products"]]))
def test_failed_edit_category_with_products_not_in_use(
        request, category: dict):
    """Retire a category that still has products attached"""
    flash_message = str(Message.Category.InUse.StillProd())
    _test_failed_edit_category(request=request,
                               category=category,
                               new_in_use="",
                               flash_message=flash_message)


def test_failed_edit_category_not_existing_category(
        client: FlaskClient, admin_logged_in: User):
    """test_failed_edit_category_not_existing_category"""
    cat_name = "not_existing_category"
    with client:
        client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        response = client.get(
            url_for("cat.edit_category", category=cat_name),
            follow_redirects=True)
        assert redirected_to(url_for("cat.categories"), response)
        assert str(Message.Category.NotExists(cat_name)) in response.text
# endregion
# endregion


# region: delete category
def test_delete_category(client: FlaskClient, admin_logged_in: User):
    """Test successfully delete category"""
    # setup
    with dbSession() as db_session:
        cat = Category(name=ValidCategory.name)
        db_session.add(cat)
        db_session.commit()
        assert cat.id
    # delete cat
    with client:
        client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        client.get(url_for("cat.categories"))
        response = client.get(url_for("cat.edit_category", category=cat.name))
        assert cat.name in response.text
        data = {
            "csrf_token": g.csrf_token,
            "name": cat.name,
            "delete": True,
        }
        response = client.post(
            url_for("cat.edit_category", category=cat.name),
            data=data,
            follow_redirects=True)
        assert redirected_to(url_for("cat.categories"), response)
        assert str(Message.Category.Deleted(cat.name)) in response.text
    # db check
    with dbSession() as db_session:
        assert not db_session.get(Category, cat.id)


@given(category=st.sampled_from([category for category in test_categories
                                 if category["has_products"]]))
def test_failed_delete_category_with_products(
        client: FlaskClient, admin_logged_in: User,
        category: dict):
    """Failed delete categories that still have products attached"""
    with client:
        client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        response = client.get(url_for("cat.edit_category",
                                      category=category["name"]))
        assert category["name"] in response.text
        data = {
            "csrf_token": g.csrf_token,
            "name": category["name"],
            "delete": True,
        }
        response = client.post(
            url_for("cat.edit_category", category=category["name"]),
            data=data)
        assert response.status_code == 200
        assert str(Message.Category.NoDelete()) in response.text
    with dbSession() as db_session:
        assert db_session.get(Category, category["id"])
# endregion


# region: reassign category
@given(cat = st.sampled_from(test_categories))
def test_landing_page_from_category_edit(
        client: FlaskClient, admin_logged_in: User, cat: dict[str]):
    """test_landing_page_from_category_edit"""
    with client:
        client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        response = client.get(url_for("cat.edit_category",
                                      category=cat["name"]))
        assert cat["name"] in response.text
        data = {
            "csrf_token": g.csrf_token,
            "name": cat["name"],
            "reassign": True,
        }
        response = client.post(
            url_for("cat.edit_category", category=cat["name"]),
            data=data,
            follow_redirects=True)
        assert redirected_to(
            url_for("cat.reassign_category", category=cat["name"]),
            response)
        assert "Reassign all products for category" in response.text
        assert cat["name"] in response.text


def test_reassign_category(client: FlaskClient, admin_logged_in: User):
    """test_reassign_category"""
    resp_id = [user["id"] for user in test_users if user["active"]][0]
    new_resp_id = [user["id"] for user in test_users if user["active"]][1]
    with dbSession() as db_session:
        # create category
        new_cat = Category(name=ValidCategory.name)
        db_session.add(new_cat)
        db_session.commit()
        # create 5 products for to this category
        for ind in range(5):
            new_product = Product(
                name="_".join([ValidProduct.name, str(ind)]),
                description=ValidProduct.description,
                responsible=db_session.get(User, resp_id),
                category=new_cat,
                supplier=db_session.get(Supplier, ValidProduct.supplier_id),
                meas_unit=ValidProduct.meas_unit,
                min_stock=ValidProduct.min_stock,
                ord_qty=ValidProduct.ord_qty)
            db_session.add(new_product)
        db_session.commit()
        products = db_session.scalars(
            select(Product)
            .filter_by(category_id=new_cat.id)).all()
        assert products
        # reassign all products
        with client:
            client.get("/")
            assert session["user_name"] == admin_logged_in.name
            assert session["admin"]
            response = client.get(
                url_for("cat.reassign_category", category=new_cat.name))
            assert response.status_code == 200
            assert new_cat.name in response.text
            data = {
                "csrf_token": g.csrf_token,
                "responsible_id": str(new_resp_id),
                "submit": True,
                }
            response = client.post(
                url_for("cat.reassign_category", category=new_cat.name),
                data=data,
                follow_redirects=True)
            assert redirected_to(
                url_for("cat.reassign_category", category=new_cat.name),
                response)
            assert str(Message.Category.Responsible.Updated(new_cat.name)) \
                in unescape(response.text)
            assert str(Message.Category.Responsible.Invalid()) \
                not in response.text
        # check and teardown
        for product in products:
            db_session.refresh(product)
            assert product.responsible_id == new_resp_id
            db_session.delete(product)
        db_session.delete(new_cat)
        db_session.commit()


@given(category_id = st.sampled_from(
            [cat["id"] for cat in test_categories if cat["has_products"]]),
       new_responsible_id=st.integers(min_value=len(test_users)))
@example(category_id=ValidProduct.category_id,
         new_responsible_id=0)
@example(category_id=ValidProduct.category_id,
         new_responsible_id=test_users.index(
             [user for user in test_users if not user["in_use"]][1]))
@example(category_id=ValidProduct.category_id,
         new_responsible_id=test_users.index(
             [user for user in test_users if user["reg_req"]][0]))
def test_failed_reassign_category(
        client: FlaskClient, admin_logged_in, category_id, new_responsible_id):
    """Test failed reassign category invalid new_responsible"""
    with dbSession() as db_session:
        cat = db_session.get(Category, category_id)
        with client:
            client.get("/")
            assert session["user_name"] == admin_logged_in.name
            assert session["admin"]
            response = client.get(
                url_for("cat.reassign_category", category=cat.name))
            assert response.status_code == 200
            assert cat.name in response.text
            # try to reassign
            data = {
                "csrf_token": g.csrf_token,
                "responsible_id": str(new_responsible_id),
                "submit": True,
                }
            response = client.post(
                url_for("cat.reassign_category", category=cat.name),
                data=data,
                follow_redirects=True)
            assert str(Message.Category.Responsible.Updated(cat.name)) \
                not in unescape(response.text)
            if new_responsible_id == 0:
                assert redirected_to(
                    url_for("cat.reassign_category", category=cat.name),
                    response)
                assert str(Message.Category.Responsible.Invalid()) \
                    in response.text
            else:
                assert len(response.history) == 0
                assert response.status_code == 200
                assert "Not a valid choice." in response.text
        # database check
        products = db_session.scalars(select(Product)
                                      .filter_by(category_id=category_id)).all()
        for product in products:
            assert product.responsible_id == \
                [prod["responsible_id"] for prod in test_products
                 if prod["name"] == product.name][0]


def test_failed_reassign_category_bad_name(
        client: FlaskClient, admin_logged_in: User):
    """test_failed_reassign_category_bad_name"""
    cat_name = "not_existing_category"
    with client:
        client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        response = client.get(
            url_for("cat.reassign_category", category=cat_name),
            follow_redirects=True)
        assert redirected_to(url_for("cat.categories"), response)
        assert str(Message.Category.NotExists(cat_name)) in response.text
# endregion
