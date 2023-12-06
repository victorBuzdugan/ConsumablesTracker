"""Main blueprint tests."""

import re

import pytest
from flask import session, url_for
from flask.testing import FlaskClient

from app import app, babel, get_locale
from blueprints.sch import clean_sch_info, sat_sch_info
from database import Product, User, dbSession
from messages import Message
from tests import (redirected_to, test_categories, test_products,
                   test_suppliers, test_users)

pytestmark = pytest.mark.main

# region: regex html elements
menu_register = re.compile(r'<a.*href="/auth/register">Register</a>')
menu_login = re.compile(r'<a.*href="/auth/login">Log In</a>')
menu_inventory = re.compile(r'<a.*href="/inventory">Inventory</a>')
menu_schedule = re.compile(r'<a.*href="/schedule">Schedule</a>')
menu_guide = re.compile(r'<a.*href="/guide">Guide</a>')
menu_categories = re.compile(r'<a.*href="/category/categories">Categories</a>')
menu_suppliers = re.compile(r'<a.*href="/supplier/suppliers">Suppliers</a>')
menu_products = re.compile(
    r'<a.*href="/product/products-sorted-by-code">Products</a>')
menu_order = re.compile(r'<a.*href="/product/products-to-order">Order</a>')
menu_new_user = re.compile(r'<a.*href="/user/new">User</a>')
menu_new_category = re.compile(r'<a.*href="/category/new">Category</a>')
menu_new_supplier = re.compile(r'<a.*href="/supplier/new">Supplier</a>')
menu_new_product = re.compile(r'<a.*href="/product/new">Product</a>')
menu_change_pass = re.compile(
    r'<a.*href="/auth/change-password">Change password</a>')
menu_logout = re.compile(r'<a.*href="/auth/logout">Log Out</a>')
no_login_menu_items = {menu_register, menu_login}
user_menu_items = {menu_inventory, menu_schedule, menu_guide, menu_change_pass,
                   menu_logout}
admin_menu_items = {menu_inventory, menu_schedule, menu_guide, menu_change_pass,
                   menu_logout, menu_categories, menu_suppliers, menu_products,
                   menu_order, menu_new_user, menu_new_category,
                   menu_new_supplier, menu_new_product}

log_in_button = re.compile(r'<input.*type="submit".*value="Log In">')
req_inv_button = re.compile(
    r'<a.*href="/inventory/request">Request inventory</a>')
# endregion

def test_index_user_not_logged_in(client: FlaskClient):
    """test_index_user_not_logged_in"""
    with client:
        response = client.get("/", follow_redirects=True)
        assert redirected_to(url_for("auth.login"), response)
    # html elements
    assert str(Message.UI.Auth.LoginReq()) in response.text
    assert log_in_button.search(response.text)
    # menu items
    for menu_item in no_login_menu_items:
        assert re.search(menu_item, response.text)
    for menu_item in (user_menu_items
                      .union(admin_menu_items)
                      .difference(no_login_menu_items)):
        assert not re.search(menu_item, response.text)


def test_index_user_logged_in(client: FlaskClient, user_logged_in: User):
    """test_index_user_logged_in"""
    user = [user for user in test_users
            if user["id"] == user_logged_in.id][0]
    user_products = [product for product in test_products
                     if product["responsible_id"] == user["id"]
                     and product["in_use"]]
    with client:
        response = client.get("/")
        assert not session["admin"]
        assert response.status_code == 200
    # html elements
    assert str(Message.UI.Auth.LoginReq()) not in response.text
    assert not log_in_button.search(response.text)
    # menu items
    for menu_item in user_menu_items:
        assert re.search(menu_item, response.text)
    for menu_item in (no_login_menu_items
                      .union(admin_menu_items)
                      .difference(user_menu_items)):
        assert not re.search(menu_item, response.text)
    # user dashboard
    assert "User dashboard" in response.text
    assert str(Message.UI.Main.LoggedInAs(user["name"]))
    assert str(Message.UI.Main.YouHave(len(user_products)))
    assert str(Message.UI.Main.Inv(False, True))
    assert user["sat_group"] == 2
    assert str(sat_sch_info.negative) in response.text
    assert str(clean_sch_info.negative) in response.text
    assert req_inv_button.search(response.text)
    # admin dashboard
    assert "Admin dashboard" not in response.text
    # statistics
    assert "Statistics" not in response.text


def test_index_admin_logged_in_user_dashboard(
        client: FlaskClient, admin_logged_in: User):
    """Test index user dashboard and language change"""
    user = [user for user in test_users
            if user["id"] == admin_logged_in.id][0]
    user_products = [product for product in test_products
                     if product["responsible_id"] == user["id"]
                     and product["in_use"]]
    with client:
        response = client.get("/")
        assert session["admin"]
        assert response.status_code == 200
    # html elements
    assert str(Message.UI.Auth.LoginReq()) not in response.text
    assert not log_in_button.search(response.text)
    # menu items
    for menu_item in admin_menu_items:
        assert re.search(menu_item, response.text)
    for menu_item in (no_login_menu_items
                      .union(user_menu_items)
                      .difference(admin_menu_items)):
        assert not re.search(menu_item, response.text)
    # user dashboard
    assert "User dashboard" in response.text
    assert str(Message.UI.Main.LoggedInAs(user["name"]))
    assert str(Message.UI.Main.YouHave(len(user_products)))
    assert str(Message.UI.Main.Inv(False, True))
    assert user["sat_group"] == 1
    assert str(sat_sch_info.positive) in response.text
    assert str(clean_sch_info.positive) in response.text
    assert not req_inv_button.search(response.text)
    # translation
    en_texts = ("User dashboard", "Admin dashboard", "Statistics")
    ro_texts = ("Panou de bord utilizator", "Panou de bord administrator",
                "Statistici")
    for text in en_texts:
        assert text in response.text
    for text in ro_texts:
        assert text not in response.text
    with client:
        client.get("/")
        babel.init_app(app=app, locale_selector=get_locale)
        # change language to 'ro'
        client.get(url_for("set_language", language="ro"))
        assert session["language"] == "ro"
        response = client.get(url_for("main.index"))
        assert "The language was changed" not in response.text
        assert "Limba a fost schimbată" in response.text
        for text in en_texts:
            assert text not in response.text
        for text in ro_texts:
            assert text in response.text
        # change language to 'en'
        client.get(url_for("set_language", language="en"))
        assert session["language"] == "en"
        response = client.get(url_for("main.index"))
        assert "The language was changed" in response.text
        assert "Limba a fost schimbată" not in response.text
        for text in en_texts:
            assert text in response.text
        for text in ro_texts:
            assert text not in response.text
        # change language to 'ro' with referer
        response = client.get(
            url_for("set_language", language="ro"),
            headers={"Referer": url_for("cat.categories")},
            follow_redirects=True)
        assert redirected_to(url_for("cat.categories"), response)
        assert session["language"] == "ro"
        assert "Limba a fost schimbată" in response.text
        # teardown
        babel.init_app(app=app, locale_selector=lambda: "en")


def test_index_hidden_admin_logged_in(
        client: FlaskClient, hidden_admin_logged_in: User):
    """test_index_hidden_admin_logged_in"""
    user = [user for user in test_users
            if user["id"] == hidden_admin_logged_in.id][0]
    with client:
        response = client.get("/")
        assert session["admin"]
        assert response.status_code == 200
    # html elements
    assert str(Message.UI.Auth.LoginReq()) not in response.text
    assert not log_in_button.search(response.text)
    # menu items
    for menu_item in admin_menu_items:
        assert re.search(menu_item, response.text)
    for menu_item in (no_login_menu_items
                      .union(user_menu_items)
                      .difference(admin_menu_items)):
        assert not re.search(menu_item, response.text)
    # user dashboard
    assert "User dashboard" in response.text
    assert str(Message.UI.Main.LoggedInAs(user["name"]))
    assert str(Message.UI.Main.YouHave(0))
    assert str(Message.UI.Main.Inv(False, True))
    assert str(sat_sch_info.positive) not in response.text
    assert str(clean_sch_info.positive) not in response.text
    assert not req_inv_button.search(response.text)
    # admin dashboard
    assert "Admin dashboard" in response.text
    # statistics
    assert "Statistics" in response.text


def test_index_admin_logged_in_admin_dashboard_table(
        client: FlaskClient, admin_logged_in: User):
    """test_index_admin_logged_in_admin_dashboard_table"""
    with client:
        response = client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        assert response.status_code == 200
        # html elements
        assert str(Message.UI.Captions.BoldUsers()) in response.text
        assert str(Message.UI.Captions.Strikethrough("users")) in response.text
        # user names
        for user in test_users:
            name_on_page = re.compile(
                r'<span.*<a.*href="' +
                fr'{url_for("users.edit_user", username=user["name"])}')
            name_bolded = re.compile(
                r'<span.*fw-bolder.*<a.*href="' +
                fr'{url_for("users.edit_user", username=user["name"])}')
            name_strikethrough = re.compile(
                r'<span.*text-decoration-line-through.*<a.*href="' +
                fr'{url_for("users.edit_user", username=user["name"])}')
            if user["name"] == "Admin":
                assert not name_on_page.search(response.text)
                continue
            assert name_on_page.search(response.text)
            if not user["in_use"]:
                assert name_strikethrough.search(response.text)
            else:
                assert not name_strikethrough.search(response.text)
            if user["admin"]:
                assert name_bolded.search(response.text)
            else:
                assert not name_bolded.search(response.text)
        # assigned products
        for user in [user for user in test_users if user["has_products"]]:
            user_products = [product for product in test_products
                            if product["responsible_id"] == user["id"]
                            and product["in_use"]]
            assert f"<td>{len(user_products)}</td>" in response.text
        # status
        assert not [user for user in test_users if not user["done_inv"]]
        assert not re.search(
            r'<a.*link-info.*href=.*check inventory',
            response.text, flags=re.S)
        assert not [user for user in test_users if user["req_inv"]]
        assert not re.search(
            r'<a.*link-warning.*href=.*requested inventory',
            response.text, flags=re.S)
        users_req_reg = [user for user in test_users if user["reg_req"]]
        assert users_req_reg
        for user in users_req_reg:
            assert re.search(
                r'<a.*link-danger.*href="' +
                url_for("users.approve_reg", username=user["name"]) +
                r'.*requested registration',
                response.text, flags=re.S)
        # modify the status of users
        temp_user_check_inv = [user for user in test_users
                               if user["has_products"] and user["admin"]][0]
        temp_user_req_inv = [user for user in test_users
                             if user["has_products"] and not user["admin"]][0]
        assert temp_user_check_inv and temp_user_req_inv
        with dbSession() as db_session:
            db_session.get(User, temp_user_check_inv["id"]).done_inv = False
            db_session.get(User, temp_user_req_inv["id"]).req_inv = True
            for user in users_req_reg:
                db_session.get(User, user["id"]).reg_req = False
            db_session.commit()
        # recheck status
        response = client.get(url_for("main.index"))
        assert re.search(
            r'<a.*link-info.*href="' +
            url_for("inv.inventory_user",
                    username=temp_user_check_inv["name"]) +
            r'.*check inventory',
            response.text, flags=re.S)
        assert re.search(
            r'<a.*link-warning.*href="' +
            url_for("users.approve_check_inv",
                    username=temp_user_req_inv["name"]) +
            r'.*requested inventory',
            response.text, flags=re.S)
        assert not re.search(
            r'<a.*link-danger.*href=.*requested registration',
            response.text, flags=re.S)
    # teardown
    with dbSession() as db_session:
        db_session.get(User, temp_user_check_inv["id"]).done_inv = True
        db_session.get(User, temp_user_req_inv["id"]).req_inv = False
        for user in users_req_reg:
            db_session.get(User, user["id"]).reg_req = True
        db_session.commit()


def test_index_admin_logged_in_admin_dashboard_product_need_to_be_ordered(
        client: FlaskClient, admin_logged_in: User):
    """test_index_admin_logged_in_admin_dashboard_product_need_to_be_ordered"""
    products_to_order = [product for product in test_products
                         if product["in_use"]][::5]
    with client:
        response = client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        assert response.status_code == 200
        # no products need to be ordered
        assert not [product for product in test_products
                    if product["to_order"]]
        assert str(Message.UI.Main.ProdToOrder(0)) in response.text
        # add some products to order list
        with dbSession() as db_session:
            for product in products_to_order:
                db_session.get(Product, product["id"]).to_order = True
            db_session.commit()
            # recheck
            response = client.get(url_for("main.index"))
            assert str(Message.UI.Main.ProdToOrder(len(products_to_order))) \
                in response.text
            # 'order' one product
            db_session.get(Product, products_to_order[0]["id"]).to_order = False
            db_session.commit()
            # recheck
            response = client.get(url_for("main.index"))
            assert str(Message.UI.Main.ProdToOrder(len(products_to_order) - 1))\
                in response.text
            # teardown
            for product in products_to_order:
                db_session.get(Product, product["id"]).to_order = False
            db_session.commit()
            # no products need to be ordered
            response = client.get(url_for("main.index"))
            assert str(Message.UI.Main.ProdToOrder(0)) in response.text


def test_index_admin_logged_in_statistics(
        client: FlaskClient, admin_logged_in: User):
    """test_index_admin_logged_in_statistics"""
    in_use_users = [user for user in test_users if user["in_use"]]
    in_use_categories = [cat for cat in test_categories if cat["in_use"]]
    in_use_suppliers = [sup for sup in test_suppliers if sup["in_use"]]
    in_use_products = [prod for prod in test_products if prod["in_use"]]
    crit_products = [prod for prod in test_products
                     if prod["in_use"] and prod["critical"]]
    with client:
        response = client.get("/")
        assert session["user_name"] == admin_logged_in.name
        assert session["admin"]
        assert Message.UI.Stats.Global(
                "users", in_use_elements=len(in_use_users)) \
            in response.text
        assert Message.UI.Stats.Global(
                "categories", in_use_elements=len(in_use_categories),
                with_link = True) \
            in response.text
        assert Message.UI.Stats.Global(
                "suppliers", in_use_elements=len(in_use_suppliers),
                with_link = True) \
            in response.text
        assert Message.UI.Stats.Global(
                "products", in_use_elements=len(in_use_products),
                with_link = True) \
            in response.text
        assert Message.UI.Stats.Global(
                "critical_products", in_use_elements=len(crit_products),
                with_link = True) \
            in response.text
    # disable one critical product
    with dbSession() as db_session:
        db_session.get(Product, crit_products[0]["id"]).in_use = False
        db_session.commit()
    # recheck
    with client:
        response = client.get("/")
        assert Message.UI.Stats.Global(
                "products", in_use_elements=len(in_use_products) - 1,
                with_link = True) \
            in response.text
        assert Message.UI.Stats.Global(
                "critical_products", in_use_elements=len(crit_products) - 1,
                with_link = True) \
            in response.text
    # teardown
    with dbSession() as db_session:
        db_session.get(Product, crit_products[0]["id"]).in_use = True
        db_session.commit()
