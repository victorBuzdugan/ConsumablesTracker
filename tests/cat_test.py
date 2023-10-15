"""Categories blueprint tests."""

from html import unescape
from urllib.parse import quote

import pytest
from flask import g, session, url_for
from flask.testing import FlaskClient
from sqlalchemy import select

from database import Category, Product, User, dbSession

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
        assert "Electronics" in response.text
        assert "Groceries" in response.text
        assert ("link-dark link-offset-2 link-underline-opacity-50 " +
                "link-underline-opacity-100-hover" in response.text)
        assert "text-decoration-line-through" in response.text
        with dbSession() as db_session:
            db_session.get(Category, 8).in_use = True
            db_session.commit()
            response = client.get(url_for("cat.categories"))
            assert "text-decoration-line-through" not in response.text
            db_session.get(Category, 8).in_use = False
            db_session.commit()
# endregion

# region: new category
@pytest.mark.parametrize(("name", "description"), (
    ("new", ""),
    ("new_category", "some description"),
    ("a_long_long_long_new_category",
     "some really long long long description, even a double long description"),
))
def test_new_category(
    client: FlaskClient, admin_logged_in: User,
    name, description):
    """test_new_category"""
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
        assert name in response.text
    with dbSession() as db_session:
        cat = db_session.scalar(select(Category).filter_by(name=name))
        assert cat.in_use
        assert cat.description == description
        db_session.delete(cat)
        db_session.commit()


@pytest.mark.parametrize(("name", "flash_message"), (
    ("", "Category name is required"),
    ("ca", "Category name must have at least 3 characters"),
    ("Electronics", "The category Electronics allready exists"),
))
def test_failed_new_category(
    client: FlaskClient, admin_logged_in: User,
    name, flash_message):
    """test_failed_new_category"""
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
    with dbSession() as db_session:
        if name != "Electronics":
            assert not db_session.scalar(select(Category).filter_by(name=name))
# endregion


# region: edit category
@pytest.mark.parametrize(
    ("cat_id", "new_name", "new_description", "new_in_use"), (
        ("1", "Household renamed", "", "on"),
        ("1", "Household", "Some description", "on"),
        ("2", "Other name", "Some description", "on"),
        ("4", "Other_name", "Some description", "on"),
        ("8", "Other_name", "Some description", "on"),
))
def test_edit_category(
    client: FlaskClient, admin_logged_in: User,
    cat_id, new_name, new_description, new_in_use):
    """test_edit_category"""
    with dbSession() as db_session:
        cat = db_session.get(Category, cat_id)
        orig_in_use = cat.in_use
        orig_name = cat.name
        orig_description = cat.description
        with client:
            client.get("/")
            assert session["user_name"] == admin_logged_in.name
            assert session["admin"]
            client.get(url_for("cat.categories"))
            response = client.get(url_for("cat.edit_category",
                                          category=cat.name))
            assert len(response.history) == 0
            assert response.status_code == 200
            assert orig_name in response.text
            data = {
                "csrf_token": g.csrf_token,
                "name": new_name,
                "description": new_description,
                "in_use": new_in_use,
                "submit": True,
            }
            response = client.post(
                url_for("cat.edit_category", category=orig_name),
                data=data,
                follow_redirects=True)
            assert len(response.history) == 1
            assert response.history[0].status_code == 302
            assert response.status_code == 200
            assert quote(response.request.path) == url_for("cat.categories")
            assert "Category updated" in response.text
            assert new_name in response.text
            assert new_description in response.text

        db_session.refresh(cat)
        assert cat.name == new_name
        assert cat.description == new_description
        assert cat.in_use == bool(new_in_use)
        # teardown
        cat.name = orig_name
        cat.description = orig_description
        cat.in_use = orig_in_use
        db_session.commit()


@pytest.mark.parametrize(
    ("cat_id", "new_name", "new_in_use", "flash_message"), (
        ("1", "", "on", "Category name is required"),
        ("4", "", "on", "Category name is required"),
        ("3", "ca", "on", "Category name must have at least 3 characters"),
        ("8", "ca", "", "Category name must have at least 3 characters"),
))
def test_failed_edit_category_form_validators(
        client: FlaskClient, admin_logged_in: User,
        cat_id, new_name, new_in_use, flash_message):
    """test_failed_edit_category_form_validators"""
    with dbSession() as db_session:
        cat = db_session.get(Category, cat_id)
        orig_name = cat.name
        orig_in_use = cat.in_use
        orig_description = cat.description
        with client:
            client.get("/")
            assert session["user_name"] == admin_logged_in.name
            assert session["admin"]
            response = client.get(url_for("cat.edit_category",
                                          category=cat.name))
            assert orig_name in response.text
            data = {
                "csrf_token": g.csrf_token,
                "name": new_name,
                "description": cat.description,
                "in_use": new_in_use,
                "submit": True,
            }
            response = client.post(
                url_for("cat.edit_category", category=orig_name),
                data=data,
                follow_redirects=True)
            assert len(response.history) == 0
            assert response.status_code == 200
            assert "Category updated" not in response.text
            assert orig_name in response.text
            assert flash_message in unescape(response.text)
        db_session.refresh(cat)
        assert cat.name == orig_name
        assert cat.in_use == orig_in_use
        assert cat.description == orig_description


def test_failed_edit_category_name_duplicate(
        client: FlaskClient, admin_logged_in: User):
    """test_failed_edit_category_name_duplicate"""
    with dbSession() as db_session:
        cat = db_session.get(Category, 2)
        orig_name = cat.name
        new_name = db_session.get(Category, 1).name
        with client:
            client.get("/")
            assert session["user_name"] == admin_logged_in.name
            assert session["admin"]
            client.get(url_for("cat.categories"))
            response = client.get(
                url_for("cat.edit_category", category=orig_name))
            assert cat.name in response.text
            data = {
                "csrf_token": g.csrf_token,
                "name": new_name,
                "description": cat.description,
                "in_use": "on",
                "submit": True,
            }
            response = client.post(
                url_for("cat.edit_category", category=orig_name),
                data=data, follow_redirects=True)
            assert len(response.history) == 1
            assert response.history[0].status_code == 302
            assert response.status_code == 200
            assert response.request.path == url_for("cat.categories")
            assert "Category updated" not in response.text
            assert orig_name in response.text
            assert f"The category {new_name} allready exists" in response.text
        db_session.refresh(cat)
        assert cat.name != new_name


def test_failed_edit_category_in_use(
        client: FlaskClient, admin_logged_in: User):
    """test_failed_edit_category_in_use"""
    with dbSession() as db_session:
        cat = db_session.get(Category, 3)
        with client:
            client.get("/")
            assert session["user_name"] == admin_logged_in.name
            assert session["admin"]
            response = client.get(
                url_for("cat.edit_category", category=cat.name))
            assert cat.name in response.text
            data = {
                "csrf_token": g.csrf_token,
                "name": cat.name,
                "description": cat.description,
                "in_use": "",
                "submit": True,
            }
            response = client.post(
                url_for("cat.edit_category", category=cat.name),
                data=data,
                follow_redirects=True)
            assert len(response.history) == 1
            assert response.history[0].status_code == 302
            assert response.status_code == 200
            assert response.request.path == url_for("main.index")
            assert "Category updated" not in response.text
            assert "Not in use category can't have products attached" \
                in unescape(response.text)
        db_session.refresh(cat)
        assert cat.in_use


def test_failed_edit_category_bad_name(
        client: FlaskClient, admin_logged_in: User):
    """test_failed_edit_category_bad_name"""
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
        cat = Category(name="new_category")
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


@pytest.mark.parametrize(("cat_id", ), (
    ("1",),
    ("2",),
    ("3",),
    ("4",),
    ("5",),
    ("6",),
    ("7",),
))
def test_failed_delete_category(
    client: FlaskClient, admin_logged_in: User,
    cat_id):
    """test_failed_delete_category"""
    with dbSession() as db_session:
        cat = db_session.get(Category, cat_id)
    with client:
        client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
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
        assert len(response.history) == 0
        assert response.status_code == 200
        assert "Can't delete category! There are still products attached!" \
            in unescape(response.text)
    with dbSession() as db_session:
        assert db_session.get(Category, cat.id)
# endregion

# region: reassign category
def test_landing_page_from_category_edit(
        client: FlaskClient, admin_logged_in: User):
    """test_landing_page_from_category_edit"""
    with dbSession() as db_session:
        cat = db_session.get(Category, 3)
    with client:
        client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        response = client.get(url_for("cat.edit_category", category=cat.name))
        assert cat.name in response.text
        data = {
            "csrf_token": g.csrf_token,
            "name": cat.name,
            "reassign": True,
        }
        response = client.post(
            url_for("cat.edit_category", category=cat.name),
            data=data,
            follow_redirects=True)
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("cat.reassign_category",
                                                category=cat.name)
        assert "Reassign all products for category" in response.text
        assert cat.name in response.text


def test_reassign_category(client: FlaskClient, admin_logged_in: User):
    """Testing Electronics(id=3) that has all products responsable_id to 1"""
    cat_id = 3
    resp_id = 1
    new_resp_id = 2
    with dbSession() as db_session:
        cat = db_session.get(Category, cat_id)
        products = db_session.scalars(
            select(Product)
            .filter_by(category_id=cat.id)).all()
        for product in products:
            assert product.responsable_id == resp_id
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
                "responsable_id": str(new_resp_id),
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
            assert "Category responsable updated" in response.text
            assert "You have to select a new responsible first" \
                not in response.text
        # check and teardown
        for product in products:
            db_session.refresh(product)
            assert product.responsable_id == new_resp_id
            product.responsable_id = resp_id
        db_session.commit()


def test_failed_reassign_category(client: FlaskClient, admin_logged_in):
    """test_failed_reassign_category"""
    cat_id = 3
    resp_id = 1
    new_resp_id = 0
    with dbSession() as db_session:
        cat = db_session.get(Category, cat_id)
        products = db_session.scalars(
            select(Product)
            .filter_by(category_id=cat.id)).all()
        for product in products:
            assert product.responsable_id == resp_id
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
                "responsable_id": str(new_resp_id),
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
            assert "Category responsable updated" not in response.text
            assert "You have to select a new responsible first" \
                in response.text
        # check and teardown
        for product in products:
            db_session.refresh(product)
            assert product.responsable_id == resp_id


def test_failed_reassign_category_bad_choice(
        client: FlaskClient, admin_logged_in:User):
    """test_failed_reassign_category_bad_choice"""
    cat_id = 3
    resp_id = 1
    new_resp_id = 15
    with dbSession() as db_session:
        cat = db_session.get(Category, cat_id)
        products = db_session.scalars(
            select(Product)
            .filter_by(category_id=cat.id)).all()
        for product in products:
            assert product.responsable_id == resp_id
        with client:
            client.get("/")
            assert session["user_name"] == admin_logged_in.name
            assert session["admin"]
            response = client.get(
                url_for("cat.reassign_category", category=cat.name))
            assert len(response.history) == 0
            assert response.status_code == 200
            assert cat.name in response.text
            data = {
                "csrf_token": g.csrf_token,
                "responsable_id": str(new_resp_id),
                "submit": True,
                }
            response = client.post(
                url_for("cat.reassign_category", category=cat.name),
                data=data,
                follow_redirects=True)
            assert len(response.history) == 0
            assert response.status_code == 200
            assert "Category responsable updated" not in response.text
            assert "Not a valid choice." in response.text
        # check and teardown
        for product in products:
            db_session.refresh(product)
            assert product.responsable_id == resp_id


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
