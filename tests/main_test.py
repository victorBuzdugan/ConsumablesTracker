"""main blueprint tests."""

import pytest
from flask import session
from flask.testing import FlaskClient
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from database import User, dbSession, Category, Supplier, Product
from tests import (admin_logged_in, client, create_test_categories,
                   create_test_db, create_test_suppliers, create_test_users,
                   user_logged_in, create_test_products)

pytestmark = pytest.mark.main


def test_index_user_not_logged_in(client: FlaskClient):
    response = client.get("/", follow_redirects=True)
    assert len(response.history) == 1
    assert response.history[0].status_code == 302
    assert response.status_code == 200
    assert response.request.path == "/auth/login"
    assert b'type="submit" value="Log In"' in response.data


def test_index_user_logged_in(client: FlaskClient, user_logged_in):
    with client:
        response = client.get("/")
        with dbSession() as db_session:
            user = db_session.get(User, session["user_id"])
            user_products = len(user.products)
            assert response.status_code == 200
            assert ('Logged in as <span class="text-secondary">' +
                    f'{session["user_name"]}') in response.text
            assert ('You have <span class="text-secondary">' +
                    f'{user_products} products') in response.text
            assert "Inventory check not required" in response.text
            user.done_inv = False
            db_session.commit()
            response = client.get("/")
            assert "Check inventory" in response.text
            user.req_inv = True
            db_session.commit()
            response = client.get("/")
            assert "You requested a inventory check" in response.text
            user.done_inv = True
            user.req_inv = False
            db_session.commit()
        assert "Admin dashboard" not in response.text
        assert "Statistics" not in response.text


def test_index_admin_logged_in_user_dashboard(client: FlaskClient, admin_logged_in):
    with client:
        response = client.get("/")
        with dbSession() as db_session:
            user = db_session.scalar(select(User).options(
                joinedload(User.products)).filter_by(id=session["user_id"]))
            assert response.status_code == 200
            assert ('Logged in as <span class="text-secondary">' +
                    f'{session["user_name"]}') in response.text
            assert ('You have <span class="text-secondary">' +
                    f'{len(user.products)} products') in response.text
            assert "Inventory check not required" in response.text

            user.done_inv = False
            db_session.commit()
            response = client.get("/")
            assert "Check inventory" in response.text
            user.done_inv = True

            user.req_inv = True
            db_session.commit()
            response = client.get("/")
            assert "You requested a inventory check" in response.text
            user.req_inv = False
            db_session.commit()
            

def test_index_admin_logged_in_admin_dashboard(client: FlaskClient, admin_logged_in):
    with client:
        response = client.get("/")
        with dbSession() as db_session:
            assert "Admin dashboard" in response.text
            assert "No user requested a inventory check" in response.text
            
            db_session.get(User, 3).req_inv = True
            db_session.commit()
            response = client.get("/")
            assert (f"{db_session.get(User, 3).name}" +
                    " requested a inventory check") in response.text
            
            db_session.get(User, 4).req_inv = True
            db_session.commit()
            response = client.get("/")
            assert (f"{db_session.get(User, 3).name}, " +
                    f"{db_session.get(User, 4).name}" +
                    " requested a inventory check") in response.text
            db_session.get(User, 3).req_inv = False
            db_session.get(User, 4).req_inv = False
            db_session.commit()
            
            response = client.get("/")
            assert "No user have to check inventory" in response.text
            
            db_session.get(User, 1).done_inv = False
            db_session.commit()
            response = client.get("/")
            assert (f"{db_session.get(User, 1).name}" +
                    " have to ckeck inventory") in response.text
            
            db_session.get(User, 2).done_inv = False
            db_session.commit()
            response = client.get("/")
            assert (f"{db_session.get(User, 1).name}, " +
                    f"{db_session.get(User, 2).name}" +
                    " have to ckeck inventory") in response.text
            db_session.get(User, 1).done_inv = True
            db_session.get(User, 2).done_inv = True
            db_session.commit()

            response = client.get("/")
            assert (f"{db_session.get(User, 5).name}" +
                    " requested registration") in response.text
            
            db_session.get(User, 4).reg_req = True
            db_session.commit()
            response = client.get("/")
            assert (f"{db_session.get(User, 4).name}, " +
                    f"{db_session.get(User, 5).name}" +
                    " requested registration") in response.text
            
            db_session.get(User, 4).reg_req = False
            db_session.get(User, 5).reg_req = False
            db_session.commit()
            response = client.get("/")
            assert "No user requested registration" in response.text


def test_index_admin_logged_in_statistics(client: FlaskClient, admin_logged_in):
    with client:
        response = client.get("/")
        with dbSession() as db_session:
            assert "Statistics" in response.text
            in_use_users = db_session.query(
                User).filter_by(in_use=True).count()
            in_use_categories = db_session.query(
                Category).filter_by(in_use=True).count()
            in_use_suppliers = db_session.query(
                Supplier).filter_by(in_use=True).count()
            in_use_products = db_session.query(
                Product).filter_by(in_use=True).count()
            critical_products = db_session.query(
                Product).filter_by(in_use=True, critical=True).count()
            assert ('There are <span class="text-secondary">' +
                    f"{in_use_users}" +
                    " users</span> in use") in response.text
            assert ('There are <span class="text-secondary">' +
                    f"{in_use_categories}" +
                    " categories</span> in use") in response.text
            assert ('There are <span class="text-secondary">' +
                    f"{in_use_suppliers}" +
                    " suppliers</span> in use") in response.text
            assert ('There are <span class="text-secondary">' +
                    f"{in_use_products}" +
                    " products</span> in use of which " +
                    '<span class="text-secondary">' +
                    f"{critical_products}" +
                    "</span> are critical.") in response.text
