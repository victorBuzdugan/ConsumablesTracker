"""Guide blueprint tests."""

import pytest
from flask import session, url_for
from flask.testing import FlaskClient

from database import User
from messages import Message

pytestmark = pytest.mark.guide

def test_guide_page_not_logged_in(client: FlaskClient):
    """test_guide_page_not_logged_in"""
    with client:
        client.get("/")
        response = client.get(url_for("guide.guide"), follow_redirects=True)
        assert not session.get("user_name")
        assert not session.get("admin")
        assert len(response.history) == 1
        assert response.history[0].status_code == 302
        assert response.status_code == 200
        assert response.request.path == url_for("auth.login")
        assert 'type="submit" value="Log In"' in response.text
        assert str(Message.UI.Auth.LoginReq()) in response.text
        assert "M10" not in response.text
        assert "50 Nm" not in response.text


def test_guide_page_user_logged_in(client: FlaskClient, user_logged_in: User):
    """test_guide_page_user_logged_in"""
    with client:
        client.get("/")
        assert session["user_name"] == user_logged_in.name
        assert not session["admin"]
        response = client.get(url_for("guide.guide"))
        assert response.status_code == 200
        assert "M10" in response.text
        assert "50 Nm" in response.text


def test_guide_page_admin_logged_in(client: FlaskClient, admin_logged_in: User):
    """test_guide_page_admin_logged_in"""
    with client:
        client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        response = client.get(url_for("guide.guide"))
        assert response.status_code == 200
        assert "M10" in response.text
        assert "50 Nm" in response.text
