"""Categories blueprint tests."""

from html import unescape
from urllib.parse import quote

import pytest
from flask import g, url_for
from flask.testing import FlaskClient
from sqlalchemy import select

from database import Category, Product, dbSession
from tests import (admin_logged_in, client, create_test_categories,
                   create_test_db, create_test_group_schedule,
                   create_test_products, create_test_suppliers,
                   create_test_users, user_logged_in)

pytestmark = pytest.mark.cat


# region: categories page
def test_categories_page_user_logged_in(client: FlaskClient, user_logged_in):
    with client:
        client.get("/")
        response = client.get(url_for("cat.categories"), follow_redirects=True)
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("auth.login")
        assert b"You have to be an admin..." in response.data


def test_categories_page_admin_logged_in(client: FlaskClient, admin_logged_in):
    with client:
        client.get("/")
        response = client.get(url_for("cat.categories"), follow_redirects=True)
        assert len(response.history) == 0
        assert response.status_code == 200
        assert b"You have to be an admin..." not in response.data
        assert b"Categories" in response.data
        assert b"Strikethrough categories are no longer in use" in response.data
        assert b"Electronics" in response.data
        assert b"Groceries" in response.data
        assert b"link-dark link-offset-2 link-underline-opacity-50 link-underline-opacity-100-hover" in response.data
        assert b"text-decoration-line-through" in response.data
        with dbSession() as db_session:
            db_session.get(Category, 8).in_use = True
            db_session.commit()
            response = client.get(url_for("cat.categories"))
            assert b"text-decoration-line-through" not in response.data
            db_session.get(Category, 8).in_use = False
            db_session.commit()
# endregion

# region: new category
@pytest.mark.parametrize(("name", "description"), (
    ("new", ""),
    ("new_category", "some description"),
    ("a_long_long_long_new_category", "some really long long long description, even a double long long description"),
))
def test_new_category(client: FlaskClient, admin_logged_in, name, description):
    with client:
        client.get("/")
        response = client.get(url_for("cat.new_category"))
        assert b"Create category" in response.data
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
        assert bytes(name, "UTF-8") in response.data
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
def test_failed_new_category(client: FlaskClient, admin_logged_in, name, flash_message):
    with client:
        client.get("/")
        response = client.get(url_for("cat.new_category"))
        assert b"Create category" in response.data
        data = {
            "csrf_token": g.csrf_token,
            "name": name,
            "description": "",
            }
        response = client.post(
            url_for("cat.new_category"), data=data, follow_redirects=True)
        assert len(response.history) == 0
        assert response.status_code == 200
        assert b"Create category" in response.data
        assert flash_message in unescape(response.text)
        assert f"Category '{name}' created" not in unescape(response.text)
    with dbSession() as db_session:
        if name != "Electronics":
            assert not db_session.scalar(select(Category).filter_by(name=name))
# endregion


# region: edit category
@pytest.mark.parametrize(("id", "new_name", "new_description", "new_in_use"), (
    ("1", "Household renamed", "", "on"),
    ("1", "Household", "Some description", "on"),
    ("2", "Other name", "Some description", "on"),
    ("4", "Other_name", "Some description", "on"),
    ("8", "Other_name", "Some description", "on"),
))
def test_edit_category(client: FlaskClient, admin_logged_in,
        id, new_name, new_description, new_in_use):
    with dbSession() as db_session:
        cat = db_session.get(Category, id)
        orig_in_use = cat.in_use
        orig_name = cat.name
        orig_description = cat.description
        with client:
            client.get("/")
            response = client.get(url_for("cat.edit_category", category=cat.name))
            assert len(response.history) == 0
            assert response.status_code == 200
            assert bytes(orig_name, "UTF-8") in response.data
            data = {
                "csrf_token": g.csrf_token,
                "name": new_name,
                "description": new_description,
                "in_use": new_in_use,
                "submit": True,
            }
            response = client.post(url_for("cat.edit_category", category=orig_name),
                                   data=data, follow_redirects=True)
            assert len(response.history) == 1
            assert response.history[0].status_code == 302
            assert response.status_code == 200
            assert quote(response.request.path) == url_for("cat.edit_category", category=new_name)
            assert b"Category updated" in response.data
            assert bytes(new_name, "UTF-8") in response.data
            assert bytes(new_description, "UTF-8") in response.data

        db_session.refresh(cat)
        assert cat.name == new_name
        assert cat.description == new_description
        assert cat.in_use == bool(new_in_use)
        # teardown
        cat.name = orig_name
        cat.description = orig_description
        cat.in_use = orig_in_use
        db_session.commit()


@pytest.mark.parametrize(("id", "new_name", "new_in_use", "flash_message"), (
    ("1", "", "on", "Category name is required"),
    ("4", "", "on", "Category name is required"),
    ("3", "ca", "on", "Category name must have at least 3 characters"),
    ("8", "ca", "", "Category name must have at least 3 characters"),
))
def test_failed_edit_category_form_validators(client: FlaskClient, admin_logged_in,
        id, new_name, new_in_use, flash_message):
    with dbSession() as db_session:
        cat = db_session.get(Category, id)
        orig_name = cat.name
        orig_in_use = cat.in_use
        orig_description = cat.description
        with client:
            client.get("/")
            response = client.get(url_for("cat.edit_category", category=cat.name))
            assert bytes(orig_name, "UTF-8") in response.data
            data = {
                "csrf_token": g.csrf_token,
                "name": new_name,
                "description": cat.description,
                "in_use": new_in_use,
                "submit": True,
            }
            response = client.post(url_for("cat.edit_category", category=orig_name),
                                   data=data, follow_redirects=True)
            assert len(response.history) == 0
            assert response.status_code == 200
            assert b"Category updated" not in response.data
            assert bytes(orig_name, "UTF-8") in response.data
            assert flash_message in unescape(response.text)
        db_session.refresh(cat)
        assert cat.name == orig_name
        assert cat.in_use == orig_in_use
        assert cat.description == orig_description


def test_failed_edit_category_name_duplicate(client: FlaskClient, admin_logged_in):
    with dbSession() as db_session:
        cat = db_session.get(Category, 2)
        orig_name = cat.name
        new_name = db_session.get(Category, 1).name
        with client:
            client.get("/")
            response = client.get(url_for("cat.edit_category", category=orig_name))
            assert bytes(cat.name, "UTF-8") in response.data
            data = {
                "csrf_token": g.csrf_token,
                "name": new_name,
                "description": cat.description,
                "in_use": "on",
                "submit": True,
            }
            response = client.post(url_for("cat.edit_category", category=orig_name),
                                   data=data, follow_redirects=True)
            assert len(response.history) == 1
            assert response.history[0].status_code == 302
            assert response.status_code == 200
            assert response.request.path == url_for("cat.edit_category", category=orig_name)
            assert b"Category updated" not in response.data
            assert bytes(orig_name, "UTF-8") in response.data
            assert f"The category {new_name} allready exists" in response.text
        db_session.refresh(cat)
        assert cat.name != new_name


def test_failed_edit_category_in_use(client: FlaskClient, admin_logged_in):
    with dbSession() as db_session:
        cat = db_session.get(Category, 3)
        with client:
            client.get("/")
            response = client.get(url_for("cat.edit_category", category=cat.name))
            assert bytes(cat.name, "UTF-8") in response.data
            data = {
                "csrf_token": g.csrf_token,
                "name": cat.name,
                "description": cat.description,
                "in_use": "",
                "submit": True,
            }
            response = client.post(url_for("cat.edit_category", category=cat.name),
                                   data=data, follow_redirects=True)
            assert len(response.history) == 1
            assert response.history[0].status_code == 302
            assert response.status_code == 200
            assert response.request.path == url_for("cat.edit_category", category=cat.name)
            assert b"Category updated" not in response.data
            assert bytes(cat.name, "UTF-8") in response.data
            assert "Not in use category can't have products attached" in unescape(response.text)
        db_session.refresh(cat)
        assert cat.in_use


def test_failed_edit_category_bad_name(client: FlaskClient, admin_logged_in):
    with client:
        client.get("/")
        response = client.get(url_for("cat.edit_category", category="not_existing_category"), follow_redirects=True)
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("cat.categories")
        assert b"not_existing_category does not exist!" in response.data
# endregion


# region: delete category
def test_delete_category(client: FlaskClient, admin_logged_in):
    with dbSession() as db_session:
        cat = Category("new_category")
        db_session.add(cat)
        db_session.commit()
        assert cat.id
    with client:
        client.get("/")
        response = client.get(url_for("cat.edit_category", category=cat.name))
        assert bytes(cat.name, "UTF-8") in response.data
        data = {
            "csrf_token": g.csrf_token,
            "name": cat.name,
            "delete": True,
        }
        response = client.post(url_for("cat.edit_category", category=cat.name),
                            data=data, follow_redirects=True)
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("cat.categories")
        assert f"Category '{cat.name}' has been deleted" in unescape(response.text)
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
def test_failed_delete_category(client: FlaskClient, admin_logged_in, cat_id):
    with dbSession() as db_session:
        cat = db_session.get(Category, cat_id)
    with client:
        client.get("/")
        response = client.get(url_for("cat.edit_category", category=cat.name))
        assert bytes(cat.name, "UTF-8") in response.data
        data = {
            "csrf_token": g.csrf_token,
            "name": cat.name,
            "delete": True,
        }
        response = client.post(url_for("cat.edit_category", category=cat.name),
                            data=data, follow_redirects=True)
        assert len(response.history) == 0
        assert response.status_code == 200
        assert f"Can't delete category! There are still products attached!" in unescape(response.text)
    with dbSession() as db_session:
        assert db_session.get(Category, cat.id)
# endregion

# region: reassign category
def test_landing_page_from_category_edit(client: FlaskClient, admin_logged_in):
    CAT_ID = 3
    with dbSession() as db_session:
        cat = db_session.get(Category, CAT_ID)
    with client:
        client.get("/")
        response = client.get(url_for("cat.edit_category", category=cat.name))
        assert bytes(cat.name, "UTF-8") in response.data
        data = {
            "csrf_token": g.csrf_token,
            "name": cat.name,
            "reassign": True,
        }
        response = client.post(url_for("cat.edit_category", category=cat.name),
                            data=data, follow_redirects=True)
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("cat.reassign_category", category=cat.name)
        assert b"Reassign all products for category" in response.data
        assert bytes(cat.name, "UTF-8") in response.data


def test_reassign_category(client: FlaskClient, admin_logged_in):
    # for testing get category id 3 - Electronics
    # that has all products responsable_id to 1 - user1
    CAT_ID = 3
    RESP_ID = 1
    NEW_RESP_ID = 2
    with dbSession() as db_session:
        cat = db_session.get(Category, CAT_ID)
        products = db_session.scalars(
            select(Product)
            .filter_by(category_id=cat.id)
            ).all()
        for product in products:
            assert product.responsable_id == RESP_ID
        with client:
            client.get("/")
            response = client.get(url_for("cat.reassign_category", category=cat.name))
            assert len(response.history) == 0
            assert response.status_code == 200
            assert bytes(cat.name, "UTF-8") in response.data
            data = {
                "csrf_token": g.csrf_token,
                "responsable_id": str(NEW_RESP_ID),
                "submit": True,
                }
            response = client.post(url_for("cat.reassign_category", category=cat.name), 
                                    data=data, follow_redirects=True)
            assert len(response.history) == 1
            assert response.history[0].status_code == 302
            assert response.status_code == 200
            assert quote(response.request.path) == url_for("cat.reassign_category", category=cat.name)
            assert b"Category responsable updated" in response.data
            assert b"You have to select a new responsible first" not in response.data
        # check and teardown
        for product in products:
            db_session.refresh(product)
            assert product.responsable_id == NEW_RESP_ID
            product.responsable_id = RESP_ID
        db_session.commit()


def test_failed_reassign_category(client: FlaskClient, admin_logged_in):
    CAT_ID = 3
    RESP_ID = 1
    NEW_RESP_ID = 0
    with dbSession() as db_session:
        cat = db_session.get(Category, CAT_ID)
        products = db_session.scalars(
            select(Product)
            .filter_by(category_id=cat.id)
            ).all()
        for product in products:
            assert product.responsable_id == RESP_ID
        with client:
            client.get("/")
            response = client.get(url_for("cat.reassign_category", category=cat.name))
            assert len(response.history) == 0
            assert response.status_code == 200
            assert bytes(cat.name, "UTF-8") in response.data
            data = {
                "csrf_token": g.csrf_token,
                "responsable_id": str(NEW_RESP_ID),
                "submit": True,
                }
            response = client.post(url_for("cat.reassign_category", category=cat.name), 
                                    data=data, follow_redirects=True)
            assert len(response.history) == 1
            assert response.history[0].status_code == 302
            assert response.status_code == 200
            assert quote(response.request.path) == url_for("cat.reassign_category", category=cat.name)
            assert b"Category responsable updated" not in response.data
            assert b"You have to select a new responsible first" in response.data
        # check and teardown
        for product in products:
            db_session.refresh(product)
            assert product.responsable_id == RESP_ID


def test_failed_reassign_category_bad_choice(client: FlaskClient, admin_logged_in):
    CAT_ID = 3
    RESP_ID = 1
    NEW_RESP_ID = 15
    with dbSession() as db_session:
        cat = db_session.get(Category, CAT_ID)
        products = db_session.scalars(
            select(Product)
            .filter_by(category_id=cat.id)
            ).all()
        for product in products:
            assert product.responsable_id == RESP_ID
        with client:
            client.get("/")
            response = client.get(url_for("cat.reassign_category", category=cat.name))
            assert len(response.history) == 0
            assert response.status_code == 200
            assert bytes(cat.name, "UTF-8") in response.data
            data = {
                "csrf_token": g.csrf_token,
                "responsable_id": str(NEW_RESP_ID),
                "submit": True,
                }
            response = client.post(url_for("cat.reassign_category", category=cat.name), 
                                    data=data, follow_redirects=True)
            assert len(response.history) == 0
            assert response.status_code == 200
            assert b"Category responsable updated" not in response.data
            assert b"Not a valid choice." in response.data
        # check and teardown
        for product in products:
            db_session.refresh(product)
            assert product.responsable_id == RESP_ID


def test_failed_reassign_category_bad_name(client: FlaskClient, admin_logged_in):
    with client:
        client.get("/")
        response = client.get(url_for("cat.reassign_category", category="not_existing_category"), follow_redirects=True)
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("cat.categories")
        assert b"not_existing_category does not exist!" in response.data
# endregion
