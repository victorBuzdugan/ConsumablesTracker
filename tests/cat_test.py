"""Categories blueprint tests."""

from html import unescape
from urllib.parse import quote

import pytest
from flask import g, session, url_for
from flask.testing import FlaskClient
from hypothesis import HealthCheck, assume, example, given, settings
from hypothesis import strategies as st
from sqlalchemy import select

from constants import Constant
from database import Category, Product, User, dbSession
from tests import InvalidCategory, ValidCategory, test_categories, test_users

pytestmark = pytest.mark.cat


# region: categories page
def test_categories_page_user_logged_in(
        client: FlaskClient, user_logged_in: User):
    """test_categories_page_user_logged_in"""
    assert not user_logged_in.admin
    with client:
        client.get("/")
        response = client.get(url_for("cat.categories"), follow_redirects=True)
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("auth.login")
        assert "You have to be an admin..." in response.text


def test_categories_page_admin_logged_in(
        client: FlaskClient, admin_logged_in: User):
    """test_categories_page_admin_logged_in"""
    assert admin_logged_in.admin
    with client:
        client.get("/")
        response = client.get(url_for("cat.categories"), follow_redirects=True)
        assert len(response.history) == 0
        assert response.status_code == 200
        assert "You have to be an admin..." not in response.text
        assert "Categories" in response.text
        assert "Strikethrough categories are no longer in use" \
            in response.text
        for category in test_categories:
            assert category["name"] in response.text
        assert ("link-dark link-offset-2 link-underline-opacity-50 " +
                "link-underline-opacity-100-hover" in response.text)
        assert "text-decoration-line-through" in response.text
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
            assert "text-decoration-line-through" not in response.text
            for cat in categories_not_in_use:
                db_session.scalar(
                    select(Category)
                    .filter_by(name=cat["name"])
                    ).in_use = False
            db_session.commit()
# endregion


# region: new category
@settings(max_examples=10,
          suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(name=st.text(min_size=Constant.Category.Name.min_length),
       description=st.text())
@example(name=ValidCategory.name,
         description=ValidCategory.description)
def test_new_category(
        client: FlaskClient, admin_logged_in: User,
        name: str, description: str):
    """test_new_category"""
    name = name.strip()
    assume(len(name) > 2)
    assume(name not in [cat["name"] for cat in test_categories])
    with client:
        client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        response = client.get(url_for("cat.new_category"))
        assert "Create category" in response.text
        data = {
            "csrf_token": g.csrf_token,
            "name": name,
            "description": description,
            }
        response = client.post(
            url_for("cat.new_category"), data=data, follow_redirects=True)
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("cat.categories")
        assert f"Category '{name}' created" in unescape(response.text)
        assert name in unescape(response.text)
    with dbSession() as db_session:
        cat = db_session.scalar(select(Category).filter_by(name=name))
        assert cat.in_use
        assert cat.description == description
        db_session.delete(cat)
        db_session.commit()
        assert not db_session.get(Category, cat.id)


def _test_failed_new_category(
        request: pytest.FixtureRequest,
        name: str, flash_message: str, check_db: bool = True):
    """Common logic for failed new category."""

    client: FlaskClient = request.getfixturevalue("client")
    admin_logged_in: User = request.getfixturevalue("admin_logged_in")
    with client:
        client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        response = client.get(url_for("cat.new_category"))
        assert "Create category" in response.text
        data = {
            "csrf_token": g.csrf_token,
            "name": name,
            "description": "",
            }
        response = client.post(
            url_for("cat.new_category"), data=data, follow_redirects=True)
        assert len(response.history) == 0
        assert response.status_code == 200
        assert "Create category" in response.text
        assert flash_message in unescape(response.text)
        assert f"Category '{name}' created" not in unescape(response.text)
    if check_db:
        with dbSession() as db_session:
            assert not db_session.scalar(select(Category).filter_by(name=name))


@settings(max_examples=5)
@given(name=st.text(min_size=1, max_size=2))
@example("")
@example(InvalidCategory.short_name)
def test_failed_new_category_invalid_name(request, name: str):
    """Invalid or no name"""
    name = name.strip()
    if name:
        flash_message = ("Category name must have at least " +
                         f"{Constant.Category.Name.min_length} characters")
    else:
        flash_message = "Category name is required"
    _test_failed_new_category(request=request,
                              name=name,
                              flash_message=flash_message)


@settings(max_examples=5)
@given(category=st.sampled_from(test_categories))
def test_failed_new_category_duplicate_name(request, category):
    """Duplicate category name."""
    flash_message = f"The category {category['name']} allready exists"
    _test_failed_new_category(request=request,
                              name=category['name'],
                              flash_message=flash_message,
                              check_db=False)
# endregion


# region: edit category
@settings(max_examples=10,
          suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(category=st.sampled_from(test_categories),
       new_name=st.text(min_size=Constant.Category.Name.min_length),
       new_description=st.text())
@example(category=test_categories[0],
       new_name=ValidCategory.name,
       new_description=ValidCategory.description)
def test_edit_category(
        client: FlaskClient, admin_logged_in: User,
        category: dict, new_name: str, new_description: str):
    """test_edit_category"""
    new_name = new_name.strip()
    assume(len(new_name) >= Constant.Category.Name.min_length)
    with client:
        client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        client.get(url_for("cat.categories"))
        response = client.get(url_for("cat.edit_category",
                                        category=category["name"]))
        assert len(response.history) == 0
        assert response.status_code == 200
        assert category["name"] in response.text
        data = {
            "csrf_token": g.csrf_token,
            "name": new_name,
            "description": new_description,
            "in_use": "on",
            "submit": True,
        }
        response = client.post(
            url_for("cat.edit_category", category=category["name"]),
            data=data,
            follow_redirects=True)
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert quote(response.request.path) == url_for("cat.categories")
        assert "Category updated" in response.text
        assert new_name in unescape(response.text)
        assert new_description in unescape(response.text)
    with dbSession() as db_session:
        cat = db_session.get(Category, category["id"])
        assert cat.description == new_description
        assert cat.in_use
        # teardown
        cat.name = category["name"]
        cat.description = category["description"]
        cat.in_use = category["in_use"]
        db_session.commit()


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
            "description": category["description"],
            "in_use": new_in_use,
            "submit": True,
        }
        response = client.post(
            url_for("cat.edit_category", category=category["name"]),
            data=data,
            follow_redirects=True)
        assert len(response.history) == 0
        assert response.status_code == 200
        assert "Category updated" not in response.text
        assert category["name"] in response.text
        assert flash_message in unescape(response.text)
    with dbSession() as db_session:
        cat = db_session.scalar(
            select(Category)
            .filter_by(name=category["name"]))
        assert cat.in_use == category["in_use"]


@settings(max_examples=5)
@given(category=st.sampled_from(test_categories),
       new_name=st.text(min_size=1, max_size=2))
@example(category=test_categories[0],
         new_name="")
@example(category=test_categories[0],
         new_name=InvalidCategory.short_name)
def test_failed_edit_category_invalid_name(
        request, category: dict, new_name: str):
    """Invalid or no name"""
    new_name = new_name.strip()
    if new_name:
        flash_message = ("Category name must have at least " +
                         f"{Constant.Category.Name.min_length} characters")
    else:
        flash_message = "Category name is required"
    _test_failed_edit_category(request=request,
                               category=category,
                               new_name=new_name,
                               flash_message=flash_message)


@settings(max_examples=5)
@given(category=st.sampled_from(test_categories),
       name=st.sampled_from([category["name"] for category in test_categories]))
def test_failed_edit_category_duplicate_name(
        request, category: dict, name: str):
    """Duplicate name"""
    assume(category["name"] != name)
    flash_message = f"The category {name} allready exists"
    _test_failed_edit_category(request=request,
                               category=category,
                               new_name=name,
                               flash_message=flash_message)


@settings(max_examples=5)
@given(category=st.sampled_from([category for category in test_categories
                                 if category["has_products"]]))
def test_failed_edit_category_with_products_not_in_use(
        request, category: dict):
    """Retire categories that still have products attached"""
    flash_message = "Not in use category can't have products attached"
    _test_failed_edit_category(request=request,
                               category=category,
                               new_in_use="",
                               flash_message=flash_message)


def test_failed_edit_category_not_existing_category(
        client: FlaskClient, admin_logged_in: User):
    """test_failed_edit_category_not_existing_category"""
    with client:
        client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        response = client.get(
            url_for("cat.edit_category", category="not_existing_category"),
            follow_redirects=True)
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("cat.categories")
        assert "not_existing_category does not exist!" in response.text
# endregion


# region: delete category
def test_delete_category(client: FlaskClient, admin_logged_in: User):
    """test_delete_category"""
    with dbSession() as db_session:
        cat = Category(name=ValidCategory.name)
        db_session.add(cat)
        db_session.commit()
        assert cat.id
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
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("cat.categories")
        assert f"Category '{cat.name}' has been deleted" \
            in unescape(response.text)
    with dbSession() as db_session:
        assert not db_session.get(Category, cat.id)


@settings(max_examples=5,
          suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(category=st.sampled_from([category for category in test_categories
                                 if category["has_products"]]))
def test_failed_delete_category_with_products(
        client: FlaskClient, admin_logged_in: User,
        category: dict):
    """Delete categories that still have products attached"""
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
            data=data,
            follow_redirects=True)
        assert len(response.history) == 0
        assert response.status_code == 200
        assert "Can't delete category! There are still products attached!" \
            in unescape(response.text)
    with dbSession() as db_session:
        assert db_session.get(Category, category["id"])
# endregion


# region: reassign category
def test_landing_page_from_category_edit(
        client: FlaskClient, admin_logged_in: User):
    """test_landing_page_from_category_edit"""
    cat = test_categories[3]
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
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("cat.reassign_category",
                                                category=cat["name"])
        assert "Reassign all products for category" in response.text
        assert cat["name"] in response.text


def test_reassign_category(client: FlaskClient, admin_logged_in: User):
    """Testing Electronics that has all products responsible_id to user1"""
    category = test_categories[2]
    assert category["name"] == "Electronics"
    responsible = test_users[1]
    assert responsible["name"] == "user1"
    new_responsible = test_users[2]
    assert new_responsible["name"] == "user2"

    with dbSession() as db_session:
        cat = db_session.scalar(
            select(Category).filter_by(name=category["name"]))
        resp = db_session.scalar(
            select(User).filter_by(name=responsible["name"]))
        new_resp = db_session.scalar(
            select(User).filter_by(name=new_responsible["name"]))
        products = db_session.scalars(
            select(Product)
            .filter_by(category=cat)).all()
        for product in products:
            assert product.responsible == resp
        with client:
            client.get("/")
            assert session["user_name"] == admin_logged_in.name
            assert session["admin"]
            response = client.get(url_for("cat.reassign_category",
                                          category=cat.name))
            assert len(response.history) == 0
            assert response.status_code == 200
            assert cat.name in response.text
            data = {
                "csrf_token": g.csrf_token,
                "responsible_id": str(new_resp.id),
                "submit": True,
                }
            response = client.post(
                url_for("cat.reassign_category", category=cat.name),
                data=data,
                follow_redirects=True)
            assert len(response.history) == 1
            assert response.history[0].status_code == 302
            assert response.status_code == 200
            assert quote(response.request.path) == \
                url_for("cat.reassign_category", category=cat.name)
            assert "Category responsible updated" in response.text
            assert "You have to select a new responsible first" \
                not in response.text
        # check and teardown
        for product in products:
            db_session.refresh(product)
            assert product.responsible == new_resp
            product.responsible = resp
        db_session.commit()


@settings(max_examples=5,
          suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(new_resp_id=st.integers(min_value=len(test_users)))
@example(new_resp_id=0)
@example(new_resp_id=test_users.index(
    [user for user in test_users if not user["in_use"]][1]))
@example(new_resp_id=test_users.index(
    [user for user in test_users if user["reg_req"]][0]))
def test_failed_reassign_category(
        client: FlaskClient, admin_logged_in, new_resp_id):
    """test_failed_reassign_category"""
    category = test_categories[2]
    assert category["name"] == "Electronics"
    responsible = test_users[1]
    assert responsible["name"] == "user1"
    with dbSession() as db_session:
        cat = db_session.scalar(
            select(Category).filter_by(name=category["name"]))
        resp = db_session.scalar(
            select(User).filter_by(name=responsible["name"]))
        products = db_session.scalars(
            select(Product)
            .filter_by(category=cat)).all()
        for product in products:
            assert product.responsible == resp
        with client:
            client.get("/")
            assert session["user_name"] == admin_logged_in.name
            assert session["admin"]
            client.get(url_for("cat.reassign_category", category=cat.name))
            data = {
                "csrf_token": g.csrf_token,
                "responsible_id": str(new_resp_id),
                "submit": True,
                }
            response = client.post(
                url_for("cat.reassign_category", category=cat.name),
                data=data,
                follow_redirects=True)
            assert "Category responsible updated" not in response.text
            if new_resp_id == 0:
                assert "You have to select a new responsible first" \
                    in response.text
            else:
                assert "Not a valid choice." in response.text
        # database check
        for product in products:
            db_session.refresh(product)
            assert product.responsible == resp


def test_failed_reassign_category_bad_name(
        client: FlaskClient, admin_logged_in: User):
    """test_failed_reassign_category_bad_name"""
    with client:
        client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        response = client.get(
            url_for("cat.reassign_category", category="not_existing_category"),
            follow_redirects=True)
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("cat.categories")
        assert "not_existing_category does not exist!" in response.text
# endregion
