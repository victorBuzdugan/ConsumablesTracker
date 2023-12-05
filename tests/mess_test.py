"""Messages module tests."""

import re

import pytest
from flask.testing import FlaskClient

from messages import Message

pytestmark = pytest.mark.mess

def test_build_grey_link(client: FlaskClient):
    """test_build_grey_link"""
    with client:
        client.get("/")
        message = str(Message.UI.Stats.Global("users", 1, with_link=True))
    assert "link-secondary" in message


def test_build_yellow_link(client: FlaskClient):
    """test_build_yellow_link"""
    with client:
        client.get("/")
        message = str(Message.UI.User.ReqInv("user"))
    assert "link-warning" in message


def test_build_red_link(client: FlaskClient):
    """test_build_red_link"""
    with client:
        client.get("/")
        message = str(Message.UI.User.AwaitsReg("user"))
    assert "link-danger" in message


def test_global_stats(client: FlaskClient):
    """test_global_stats"""
    with client:
        client.get("/")
        with pytest.raises(ValueError,
                           match=re.escape("Invalid arguments")):
            str(Message.UI.Stats.Global("users"))
        with pytest.raises(ValueError,
                           match=re.escape("Invalid element 'element'")):
            str(Message.UI.Stats.Global("element", 1))
        assert "There is" in str(Message.UI.Stats.Global("users", 1))
        assert "There are" in str(Message.UI.Stats.Global("categories", 2))
        message = str(Message.UI.Stats.Global("suppliers", in_use_elements=2))
        assert "in use" in message
        assert "of which" not in message
        message = str(Message.UI.Stats.Global("products", 1, 1))
        assert "and" in message
        assert "is in use" in message
        message = str(Message.UI.Stats.Global("critical_products", 2, 2))
        assert "of which" in message
        assert "are in use" in message


def test_indiv_stats(client: FlaskClient):
    """test_indiv_stats"""
    with client:
        client.get("/")
        with pytest.raises(ValueError,
                           match=re.escape("Invalid arguments")):
            str(Message.UI.Stats.Indiv("user"))
        with pytest.raises(ValueError,
                           match=re.escape("Invalid element 'element'")):
            str(Message.UI.Stats.Indiv("element", 1, 1))
        message = str(Message.UI.Stats.Indiv("user", 1, 1))
        assert "and" in message
        assert "is in use" in message
        message = str(Message.UI.Stats.Indiv("category", 2, 2))
        assert "of which" in message
        assert "are in use" in message
        message = str(Message.UI.Stats.Indiv("supplier", 2, 1))
        assert "of which" in message
        assert "is in use" in message


def test_strikethrough(client: FlaskClient):
    """test_strikethrough"""
    with client:
        client.get("/")
        with pytest.raises(ValueError,
                           match=re.escape("Invalid element 'element'")):
            str(Message.UI.Captions.Strikethrough("element"))
        assert "Strikethrough users" in str(Message.UI.Captions
                                            .Strikethrough("users"))
        assert "Strikethrough categories" in str(Message.UI.Captions
                                                 .Strikethrough("categories"))
        assert "Strikethrough suppliers" in str(Message.UI.Captions
                                                .Strikethrough("suppliers"))
        assert "Strikethrough products" in str(Message.UI.Captions
                                               .Strikethrough("products"))


def test_inv_message(client: FlaskClient):
    """test_inv_message"""
    with client:
        client.get("/")
        assert "You requested inventorying" in str(Message.UI.Main
                                                   .Inv(True, False))
        assert "Inventory check not required" in str(Message.UI.Main
                                                   .Inv(False, True))
        assert "Check inventory" in str(Message.UI.Main
                                        .Inv(False, False))


def test_prod_order(client: FlaskClient):
    """test_prod_order"""
    there_is = re.compile(r"There is.*product.*that needs")
    there_are = re.compile(r"There are.*products.*that need")
    with client:
        client.get("/")
        assert "There are no products that need to be ordered" \
            in str(Message.UI.Main.ProdToOrder(""))
        assert "There are no products that need to be ordered" \
            in str(Message.UI.Main.ProdToOrder(0))
        assert there_is.search(str(Message.UI.Main.ProdToOrder(1)))
        assert there_are.search(str(Message.UI.Main.ProdToOrder(2)))
