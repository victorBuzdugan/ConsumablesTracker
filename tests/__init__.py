import pytest
from app import app
from flask.testing import FlaskClient

@pytest.fixture()
def client() -> FlaskClient:
    app.testing = True
    app.secret_key = 'testing'
    # with app.test_client() as client:
    yield app.test_client()